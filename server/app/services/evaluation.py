"""Evaluation worker logic (spec §13, §15).

Flow: submit enqueues -> worker calls the provider -> output is validated -> a single
transaction writes feedback, skill ledger, aggregate skills, XP ledger and profile.
If validation fails twice the attempt is marked feedback_failed and preserved.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.ai.base import EvaluationRequest, ProviderError
from app.ai.prompt import build_user_prompt, prompt_version, system_prompt
from app.ai.registry import get_provider
from app.ai.validation import Evaluation, InvalidEvaluation, parse_evaluation
from app.config import settings
from app import tree_content
from app.i18n import Language
from app.models import (
    ChallengeAttempt,
    EvidenceInteraction,
    FeedbackEvaluation,
    UserProfile,
    XpLedgerEntry,
    utcnow,
)
from app.services import skills as skills_service
from app.services import tree as tree_service
from app.services.scoring import build_breakdown, evidence_points, level_for_xp, xp_for_score

logger = logging.getLogger("pmcoach.evaluation")


class RateLimited(RuntimeError):
    pass


def scenario_for_attempt(db: Session, attempt: ChallengeAttempt) -> dict:
    scenario = tree_content.scenario(attempt.scenario_id)
    if scenario is None:
        raise LookupError(f"gate scenario {attempt.scenario_id} not found")
    return scenario


def reviewed_evidence_ids(db: Session, attempt_id: str) -> list[str]:
    rows = (
        db.query(EvidenceInteraction)
        .filter(EvidenceInteraction.attempt_id == attempt_id)
        .order_by(EvidenceInteraction.opened_at.asc())
        .all()
    )
    return [row.evidence_card_id for row in rows]


def check_daily_quota(db: Session, user_id: str) -> None:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    count = (
        db.query(FeedbackEvaluation)
        .filter(
            FeedbackEvaluation.user_id == user_id,
            FeedbackEvaluation.created_at >= since,
        )
        .count()
    )
    if count >= settings.evaluations_per_user_per_day:
        raise RateLimited("daily_evaluation_limit_reached")


def enqueue(db: Session, attempt: ChallengeAttempt, consequence: str, option_label: str) -> FeedbackEvaluation:
    """Create or re-arm the evaluation record for an attempt. One per attempt."""
    evaluation = db.get(FeedbackEvaluation, attempt.id)
    if evaluation is None:
        evaluation = FeedbackEvaluation(
            attempt_id=attempt.id,
            user_id=attempt.user_id,
            status="queued",
            consequence_snapshot=consequence,
            option_label_snapshot=option_label,
        )
        db.add(evaluation)
    else:
        evaluation.status = "queued"
        evaluation.error_code = None
        evaluation.provider_attempts = 0
        evaluation.updated_at = utcnow()
    return evaluation


def claim_next(db: Session) -> FeedbackEvaluation | None:
    """Claim one queued evaluation. Safe under a single worker; see README for scale-out."""
    evaluation = (
        db.query(FeedbackEvaluation)
        .filter(FeedbackEvaluation.status == "queued")
        .order_by(FeedbackEvaluation.created_at.asc())
        .first()
    )
    if evaluation is None:
        return None
    evaluation.status = "running"
    evaluation.updated_at = utcnow()
    db.commit()
    return evaluation


def _call_provider(request: EvaluationRequest) -> tuple[Evaluation, str, str, float]:
    provider = get_provider()
    last_code = "provider_unknown_error"
    started = time.perf_counter()
    for attempt_index in range(settings.evaluator_max_attempts):
        try:
            response = provider.evaluate(request)
            evaluation = parse_evaluation(response.raw_text)
            elapsed = (time.perf_counter() - started) * 1000
            return evaluation, provider.name, response.model_id, elapsed
        except ProviderError as exc:
            last_code = exc.code
            logger.warning("provider error (%s): %s", exc.code, exc)
            if not exc.retryable:
                break
        except InvalidEvaluation as exc:
            last_code = f"invalid_output_{exc.code}"
            logger.warning("provider returned invalid output: %s", exc.code)
        if attempt_index < settings.evaluator_max_attempts - 1:
            time.sleep(settings.evaluator_backoff_seconds * (2**attempt_index))
    raise ProviderError(last_code, retryable=False)


def process_evaluation(db: Session, evaluation: FeedbackEvaluation) -> str:
    """Run one evaluation to completion. Returns the resulting status."""
    attempt = db.get(ChallengeAttempt, evaluation.attempt_id)
    if attempt is None:
        evaluation.status = "failed"
        evaluation.error_code = "attempt_missing"
        db.commit()
        return "failed"

    try:
        scenario = scenario_for_attempt(db, attempt)
    except LookupError:
        evaluation.status = "failed"
        evaluation.error_code = "scenario_missing"
        db.commit()
        return "failed"

    # The worker runs after the request that queued it, so the language comes from the
    # stored profile. The model is shown the same wording the learner read, so a Russian
    # rationale is evaluated against Russian evidence rather than against a translation
    # the learner never saw.
    profile = db.get(UserProfile, attempt.user_id)
    language = Language.coerce(profile.language if profile else None)
    content = scenario
    reviewed = reviewed_evidence_ids(db, attempt.id)
    selected_option = next(
        (o for o in content["decisionOptions"] if o["id"] == attempt.selected_option_id),
        None,
    )

    request = EvaluationRequest(
        scenario_id=content["id"],
        scenario_version=content["version"],
        system_prompt=system_prompt(language),
        user_prompt=build_user_prompt(
            scenario=content,
            selected_option_id=attempt.selected_option_id or "",
            reviewed_evidence_ids=reviewed,
            rationale=attempt.rationale or "",
            language=language,
            lessons=tree_content.lessons_for_block(attempt.block_id),
        ),
        context={
            "rationale": attempt.rationale or "",
            "reviewed_evidence_ids": reviewed,
            "total_evidence_cards": len(content["evidenceCards"]),
            "decision_points": (selected_option or {}).get("decisionPoints", 0),
            "primary_skill": content["primarySkill"],
            "secondary_skills": content.get("secondarySkills", []),
            "language": language.value,
        },
    )

    try:
        result, provider_name, model_id, latency_ms = _call_provider(request)
    except ProviderError as exc:
        evaluation.status = "failed"
        evaluation.error_code = exc.code
        evaluation.provider_attempts = settings.evaluator_max_attempts
        evaluation.updated_at = utcnow()
        attempt.status = "feedback_failed"
        db.commit()
        logger.error("evaluation failed for attempt %s: %s", attempt.id, exc.code)
        return "failed"

    _commit_success(
        db,
        attempt=attempt,
        evaluation=evaluation,
        scenario=scenario,
        result=result,
        reviewed_count=len(reviewed),
        provider_name=provider_name,
        model_id=model_id,
        latency_ms=latency_ms,
    )
    return "complete"


def _commit_success(
    db: Session,
    *,
    attempt: ChallengeAttempt,
    evaluation: FeedbackEvaluation,
    scenario: dict,
    result: Evaluation,
    reviewed_count: int,
    provider_name: str,
    model_id: str,
    latency_ms: float,
) -> None:
    """Single transaction: feedback + skills + XP + profile (spec §15)."""
    content = scenario
    breakdown = build_breakdown(
        evidence=evidence_points(reviewed_count, len(content["evidenceCards"])),
        decision=next(
            (
                int(o["decisionPoints"])
                for o in content["decisionOptions"]
                if o["id"] == attempt.selected_option_id
            ),
            0,
        ),
        rationale=result.rationale_score,
        communication=result.communication_score,
    )

    attempt.evidence_points = breakdown.evidence
    attempt.decision_points = breakdown.decision
    attempt.rationale_points = breakdown.rationale
    attempt.communication_points = breakdown.communication
    attempt.final_score = breakdown.total
    attempt.status = "complete"
    attempt.completed_at = utcnow()

    evaluation.status = "complete"
    evaluation.ai_json = result.as_dict()
    evaluation.prompt_version = prompt_version()
    evaluation.model_id = model_id
    evaluation.provider = provider_name
    evaluation.error_code = None
    evaluation.needs_retry = result.needs_retry
    evaluation.latency_ms = latency_ms
    evaluation.evaluated_at = utcnow()
    evaluation.updated_at = utcnow()

    skills_service.apply_deltas(
        db,
        user_id=attempt.user_id,
        attempt_id=attempt.id,
        scenario_id=content["id"],
        deltas=result.skill_deltas,
    )

    # Pass/fail and the resulting unlock are written in this same transaction, so a
    # block can never be open without the score that opened it (spec v0.2 §9, §11).
    tree_service.record_gate_result(db, attempt, breakdown.total)

    awarded = 0
    if attempt.passed:
        base_xp, bonus_xp = xp_for_score(breakdown.total)
        for amount, reason in (
            (base_xp, "gate_passed"),
            (bonus_xp, "gate_quality_bonus"),
        ):
            awarded += tree_service.award_xp(
                db,
                user_id=attempt.user_id,
                amount=amount,
                reason=reason,
                ref_id=attempt.block_id,
                attempt_id=attempt.id,
            )
    attempt.xp_awarded = awarded

    tree_service.refresh_totals(db, attempt.user_id)
    db.commit()
