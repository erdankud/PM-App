"""Attempt lifecycle: draft, evidence, submit, feedback (spec §10.7-§10.10, §14)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.deps import CurrentUser, DbSession, IdempotencyKey
from app.models import (
    ChallengeAttempt,
    EvidenceInteraction,
    FeedbackEvaluation,
    FeedbackRating,
    IdempotencyRecord,
    LearningPathAssignment,
    Scenario,
    SkillAssessment,
    User,
    utcnow,
)
from app.schemas import (
    ConsequenceView,
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
from app.services import evaluation as evaluation_service
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


def _scenario(db: DbSession, attempt: ChallengeAttempt) -> Scenario:
    scenario = (
        db.query(Scenario)
        .filter(
            Scenario.scenario_id == attempt.scenario_id,
            Scenario.version == attempt.scenario_version,
        )
        .first()
    )
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


def _consequence_view(evaluation: FeedbackEvaluation, attempt: ChallengeAttempt) -> ConsequenceView:
    return ConsequenceView(
        option_id=attempt.selected_option_id or "",
        option_label=evaluation.option_label_snapshot,
        text=evaluation.consequence_snapshot,
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
        valid = {o["id"] for o in scenario.content["decisionOptions"]}
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
    cards = scenario.content["evidenceCards"]
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
    idempotency_key: IdempotencyKey = None,
) -> SubmitResponse:
    attempt = _attempt(db, attempt_id, user)
    scenario = _scenario(db, attempt)
    content = scenario.content

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
            consequence=_consequence_view(evaluation, attempt),
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

    assignment = db.get(LearningPathAssignment, attempt.assignment_id)
    if assignment is not None:
        assignment.status = "submitted"

    evaluation = evaluation_service.enqueue(
        db, attempt, consequence=option["consequence"], option_label=option["label"]
    )
    db.commit()

    return SubmitResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        consequence=_consequence_view(evaluation, attempt),
        feedback_status="pending",
    )


def _feedback_status(evaluation: FeedbackEvaluation) -> str:
    if evaluation.status == "complete":
        return "complete"
    if evaluation.status == "failed":
        return "failed"
    return "pending"


def _feedback_body(
    db: DbSession, attempt: ChallengeAttempt, evaluation: FeedbackEvaluation
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
            label=skills_service.SKILL_LABELS.get(row.skill_key, row.skill_key),
            delta=row.delta,
            score=current.get(row.skill_key, 50),
        )
        for row in sorted(ledger, key=lambda r: (-r.delta, r.skill_key))
    ]
    score = attempt.final_score or 0
    return FeedbackBody(
        score=score,
        band=score_band(score),
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
def get_feedback(attempt_id: str, user: CurrentUser, db: DbSession) -> FeedbackResponse:
    attempt = _attempt(db, attempt_id, user)
    evaluation = db.get(FeedbackEvaluation, attempt.id)
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": "attempt_not_submitted"}
        )
    scenario = _scenario(db, attempt)
    rating = db.get(FeedbackRating, attempt.id)
    body = _feedback_body(db, attempt, evaluation)
    return FeedbackResponse(
        attempt_id=attempt.id,
        status=_feedback_status(evaluation),
        consequence=_consequence_view(evaluation, attempt),
        feedback=body,
        rating=rating.rating if rating else None,
        retry_available=evaluation.status == "failed",
        scenario_title=scenario.title,
        learn_takeaway_title=(scenario.content.get("learnTakeaway") or {}).get("title"),
    )


@router.post("/{attempt_id}/feedback/retry", response_model=FeedbackResponse)
def retry_feedback(attempt_id: str, user: CurrentUser, db: DbSession) -> FeedbackResponse:
    attempt = _attempt(db, attempt_id, user)
    evaluation = db.get(FeedbackEvaluation, attempt.id)
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": "attempt_not_submitted"}
        )
    if evaluation.status == "complete":
        return get_feedback(attempt_id, user, db)
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
    assignment = db.get(LearningPathAssignment, attempt.assignment_id)
    if assignment is not None:
        assignment.status = "submitted"
    db.commit()
    return get_feedback(attempt_id, user, db)


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
