"""Attempt lifecycle: draft, evidence, submit, feedback (spec §10.7-§10.10, §14)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app import tree_content
from app.deps import ContentLanguage, CurrentUser, DbSession, IdempotencyKey
from app.models import (
    ChallengeAttempt,
    EvidenceInteraction,
    FeedbackEvaluation,
    FeedbackRating,
    IdempotencyRecord,
    SkillAssessment,
    User,
    utcnow,
)
from app.schemas import (
    ConsequenceView,
    RemediationLink,
    DraftRequest,
    DraftResponse,
    EvidenceRequest,
    EvidenceResponse,
    FeedbackBody,
    FeedbackPoint,
    FeedbackResponse,
    RatingRequest,
    ScoreBreakdownView,
    SimpleOk,
    SkillImpact,
    SubmitRequest,
    SubmitResponse,
)
from app.i18n import Language
from app.services import evaluation as evaluation_service
from app.services import tree as tree_service
from app.services import skills as skills_service
from app.services.scoring import (
    COMMUNICATION_MAX,
    DECISION_MAX,
    EVIDENCE_MAX,
    RATIONALE_MAX,
    score_band,
)

router = APIRouter(prefix="/attempts", tags=["attempts"])

RATIONALE_MIN = 30
RATIONALE_MAX_CHARS = 600


def _attempt(db: DbSession, attempt_id: str, user: User) -> ChallengeAttempt:
    attempt = db.get(ChallengeAttempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "attempt_not_found"}
        )
    return attempt


def _scenario(
    db: DbSession, attempt: ChallengeAttempt, language: Language = Language.RU
) -> dict:
    scenario = tree_content.scenario(attempt.scenario_id, language.value)
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "scenario_content_unavailable"},
        )
    return scenario


def _reviewed_ids(db: DbSession, attempt_id: str) -> list[str]:
    return [
        row.evidence_card_id
        for row in db.query(EvidenceInteraction)
        .filter(EvidenceInteraction.attempt_id == attempt_id)
        .order_by(EvidenceInteraction.opened_at.asc())
        .all()
    ]


def _consequence_view(
    evaluation: FeedbackEvaluation,
    attempt: ChallengeAttempt,
    content: dict | None = None,
) -> ConsequenceView:
    """The authored consequence, in the reader's current language.

    The snapshot taken at submit time stays the durable record — it is what survives a
    scenario being unpublished or re-versioned — but when the content is still available
    the localised text wins, so switching language also translates results a learner
    submitted earlier. Neither path involves a model, so this stays independent of
    provider availability (spec §10.9).
    """
    option = None
    if content is not None:
        option = next(
            (
                o
                for o in content["decisionOptions"]
                if o["id"] == attempt.selected_option_id
            ),
            None,
        )
    return ConsequenceView(
        option_id=attempt.selected_option_id or "",
        option_label=(option or {}).get("label") or evaluation.option_label_snapshot,
        text=(option or {}).get("consequence") or evaluation.consequence_snapshot,
    )


@router.put("/{attempt_id}/draft", response_model=DraftResponse)
def save_draft(
    attempt_id: str, payload: DraftRequest, user: CurrentUser, db: DbSession
) -> DraftResponse:
    attempt = _attempt(db, attempt_id, user)
    if attempt.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": "attempt_immutable"}
        )

    if payload.selected_option_id is not None:
        scenario = _scenario(db, attempt)
        valid = {o["id"] for o in scenario["decisionOptions"]}
        if payload.selected_option_id not in valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "unknown_option"},
            )
        attempt.selected_option_id = payload.selected_option_id

    if payload.rationale is not None:
        attempt.rationale = payload.rationale[:RATIONALE_MAX_CHARS]

    attempt.draft_updated_at = utcnow()
    db.commit()
    return DraftResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        selected_option_id=attempt.selected_option_id,
        rationale_length=len((attempt.rationale or "").strip()),
        saved_at=attempt.draft_updated_at.isoformat(),
    )


@router.post("/{attempt_id}/evidence", response_model=EvidenceResponse)
def record_evidence(
    attempt_id: str, payload: EvidenceRequest, user: CurrentUser, db: DbSession
) -> EvidenceResponse:
    attempt = _attempt(db, attempt_id, user)
    scenario = _scenario(db, attempt)
    cards = scenario["evidenceCards"]
    if payload.evidence_card_id not in {c["id"] for c in cards}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "unknown_evidence_card"}
        )

    if attempt.status == "draft":
        record = EvidenceInteraction(
            attempt_id=attempt.id, evidence_card_id=payload.evidence_card_id
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            # Already recorded; opening a card twice is a no-op (spec §15).
            db.rollback()

    reviewed = _reviewed_ids(db, attempt.id)
    return EvidenceResponse(
        attempt_id=attempt.id,
        reviewed_evidence_ids=reviewed,
        reviewed_count=len(reviewed),
        total_count=len(cards),
    )


@router.post("/{attempt_id}/submit", response_model=SubmitResponse)
def submit_attempt(
    attempt_id: str,
    payload: SubmitRequest,
    user: CurrentUser,
    db: DbSession,
    language: ContentLanguage,
    idempotency_key: IdempotencyKey = None,
) -> SubmitResponse:
    attempt = _attempt(db, attempt_id, user)
    content = _scenario(db, attempt)

    # Repeat submissions return the original result rather than creating a second
    # attempt or awarding XP twice (spec §14, §18).
    if attempt.status != "draft":
        evaluation = db.get(FeedbackEvaluation, attempt.id)
        if evaluation is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "attempt_already_submitted"},
            )
        return SubmitResponse(
            attempt_id=attempt.id,
            status=attempt.status,
            consequence=_consequence_view(evaluation, attempt, content),
            feedback_status=_feedback_status(evaluation),
        )

    option = next(
        (o for o in content["decisionOptions"] if o["id"] == payload.selected_option_id),
        None,
    )
    if option is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "unknown_option"}
        )

    rationale = payload.rationale.strip()
    if not RATIONALE_MIN <= len(rationale) <= RATIONALE_MAX_CHARS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "rationale_length_invalid"},
        )

    reviewed = _reviewed_ids(db, attempt.id)
    if not reviewed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "no_evidence_reviewed"},
        )

    try:
        evaluation_service.check_daily_quota(db, user.id)
    except evaluation_service.RateLimited as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "daily_evaluation_limit_reached"},
        ) from exc

    if idempotency_key:
        db.add(
            IdempotencyRecord(
                user_id=user.id,
                endpoint="attempts.submit",
                key=idempotency_key,
                target_id=attempt.id,
            )
        )
        try:
            db.flush()
        except IntegrityError:
            db.rollback()

    attempt.selected_option_id = option["id"]
    attempt.rationale = rationale
    attempt.status = "awaiting_feedback"
    attempt.submitted_at = utcnow()

    evaluation = evaluation_service.enqueue(
        db, attempt, consequence=option["consequence"], option_label=option["label"]
    )
    db.commit()

    return SubmitResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        consequence=_consequence_view(evaluation, attempt, content),
        feedback_status="pending",
    )


def _feedback_status(evaluation: FeedbackEvaluation) -> str:
    if evaluation.status == "complete":
        return "complete"
    if evaluation.status == "failed":
        return "failed"
    return "pending"


def _feedback_body(
    db: DbSession,
    attempt: ChallengeAttempt,
    evaluation: FeedbackEvaluation,
    language: Language,
) -> FeedbackBody | None:
    if evaluation.status != "complete" or not evaluation.ai_json:
        return None
    ai = evaluation.ai_json
    ledger = (
        db.query(SkillAssessment)
        .filter(
            SkillAssessment.attempt_id == attempt.id,
            SkillAssessment.source == "attempt",
        )
        .all()
    )
    current = skills_service.get_scores(db, attempt.user_id)
    impact = [
        SkillImpact(
            key=row.skill_key,
            label=skills_service.label(row.skill_key, language),
            delta=row.delta,
            score=current.get(row.skill_key, 50),
        )
        for row in sorted(ledger, key=lambda r: (-r.delta, r.skill_key))
    ]
    score = attempt.final_score or 0
    return FeedbackBody(
        score=score,
        band=score_band(score, language),
        breakdown=ScoreBreakdownView(
            evidence=attempt.evidence_points or 0,
            evidence_max=EVIDENCE_MAX,
            decision=attempt.decision_points or 0,
            decision_max=DECISION_MAX,
            rationale=attempt.rationale_points or 0,
            rationale_max=RATIONALE_MAX,
            communication=attempt.communication_points or 0,
            communication_max=COMMUNICATION_MAX,
        ),
        strengths=[FeedbackPoint(**item) for item in ai.get("strengths", [])],
        improvements=[FeedbackPoint(**item) for item in ai.get("improvements", [])],
        sharper_approach=ai.get("sharper_approach", ""),
        skill_impact=impact,
        xp_awarded=attempt.xp_awarded or 0,
        needs_retry=bool(ai.get("needs_retry", False)),
    )


@router.get("/{attempt_id}/feedback", response_model=FeedbackResponse)
def get_feedback(
    attempt_id: str, user: CurrentUser, db: DbSession, language: ContentLanguage
) -> FeedbackResponse:
    attempt = _attempt(db, attempt_id, user)
    evaluation = db.get(FeedbackEvaluation, attempt.id)
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": "attempt_not_submitted"}
        )
    content = _scenario(db, attempt, language)
    rating = db.get(FeedbackRating, attempt.id)
    body = _feedback_body(db, attempt, evaluation, language)
    gate = tree_content.gate(attempt.gate_id)
    block = tree_content.block(attempt.block_id, language.value)
    threshold = tree_service.pass_threshold(gate) if gate else None

    # A failed gate is only useful if it points at the lesson that would have helped.
    # Sending someone back to "the block" is the same as sending them nowhere.
    remediation: list[RemediationLink] = []
    if attempt.passed is False:
        for entry in content["rubric"]["remediation"]:
            lesson = tree_content.lesson(entry["lessonId"], language.value)
            if lesson is None:
                continue
            remediation.append(
                RemediationLink(
                    gap=entry["gap"],
                    lesson_id=entry["lessonId"],
                    lesson_title=lesson["title"],
                )
            )

    unlocked: list[str] = []
    if attempt.passed:
        rows = tree_service.recompute(db, user.id)
        db.commit()
        unlocked = [
            candidate
            for candidate in tree_content.dependents(attempt.block_id)
            if rows[candidate].status != tree_service.LOCKED
        ]

    return FeedbackResponse(
        attempt_id=attempt.id,
        status=_feedback_status(evaluation),
        consequence=_consequence_view(evaluation, attempt, content),
        feedback=body,
        rating=rating.rating if rating else None,
        retry_available=evaluation.status == "failed",
        scenario_title=content["title"],
        learn_takeaway_title=(content.get("learnTakeaway") or {}).get("title"),
        gate_id=attempt.gate_id,
        block_id=attempt.block_id,
        block_title=block["title"] if block else attempt.block_id,
        passed=attempt.passed,
        pass_threshold=threshold,
        attempt_index=attempt.attempt_index,
        unlocked_block_ids=unlocked,
        remediation=remediation,
    )


@router.post("/{attempt_id}/feedback/retry", response_model=FeedbackResponse)
def retry_feedback(
    attempt_id: str, user: CurrentUser, db: DbSession, language: ContentLanguage
) -> FeedbackResponse:
    attempt = _attempt(db, attempt_id, user)
    evaluation = db.get(FeedbackEvaluation, attempt.id)
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": "attempt_not_submitted"}
        )
    if evaluation.status == "complete":
        return get_feedback(attempt_id, user, db, language)
    if evaluation.status == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": "evaluation_in_progress"}
        )

    try:
        evaluation_service.check_daily_quota(db, user.id)
    except evaluation_service.RateLimited as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "daily_evaluation_limit_reached"},
        ) from exc

    evaluation.status = "queued"
    evaluation.error_code = None
    evaluation.updated_at = utcnow()
    attempt.status = "awaiting_feedback"
    db.commit()
    return get_feedback(attempt_id, user, db, language)


@router.post("/{attempt_id}/feedback-rating", response_model=SimpleOk)
def rate_feedback(
    attempt_id: str, payload: RatingRequest, user: CurrentUser, db: DbSession
) -> SimpleOk:
    attempt = _attempt(db, attempt_id, user)
    existing = db.get(FeedbackRating, attempt.id)
    if existing is None:
        db.add(
            FeedbackRating(
                attempt_id=attempt.id, user_id=user.id, rating=payload.rating
            )
        )
    else:
        existing.rating = payload.rating
    db.commit()
    return SimpleOk()
