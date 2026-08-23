"""Profile, onboarding state and account deletion."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.models import (
    AssessmentResponse,
    ChallengeAttempt,
    EvidenceInteraction,
    FeedbackEvaluation,
    FeedbackRating,
    UserProfile,
    utcnow,
)
from app.schemas import MeResponse, ProfileUpdateRequest, SimpleOk
from app.security import revoke_all_refresh_tokens
from app.services.path import resolve_timezone
from app.views import me_response

router = APIRouter(tags=["me"])


def _profile_or_404(db: DbSession, user_id: str) -> UserProfile:
    profile = db.get(UserProfile, user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "profile_missing"}
        )
    return profile


@router.get("/me", response_model=MeResponse)
def get_me(user: CurrentUser, db: DbSession) -> MeResponse:
    profile = _profile_or_404(db, user.id)
    return me_response(db, user, profile)


@router.patch("/me/profile", response_model=MeResponse)
def update_profile(
    payload: ProfileUpdateRequest, user: CurrentUser, db: DbSession
) -> MeResponse:
    profile = _profile_or_404(db, user.id)

    if payload.timezone:
        user.timezone = str(resolve_timezone(payload.timezone))

    if payload.goal is not None:
        profile.goal = payload.goal
        if user.onboarding_status == "signed_in":
            user.onboarding_status = "goal_set"

    if payload.complete_onboarding:
        if user.onboarding_status != "assessed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "assessment_incomplete"},
            )
        user.onboarding_status = "complete"

    profile.updated_at = utcnow()
    db.commit()
    return me_response(db, user, profile)


@router.delete("/me", response_model=SimpleOk)
def delete_account(user: CurrentUser, db: DbSession) -> SimpleOk:
    """Irreversibly anonymise the account and delete personal content (spec §17).

    Free-text rationales, AI feedback payloads and identity links are removed. The
    account row is retained in tombstone form so foreign keys stay valid.
    """
    attempts = (
        db.query(ChallengeAttempt).filter(ChallengeAttempt.user_id == user.id).all()
    )
    attempt_ids = [attempt.id for attempt in attempts]

    if attempt_ids:
        (
            db.query(EvidenceInteraction)
            .filter(EvidenceInteraction.attempt_id.in_(attempt_ids))
            .delete(synchronize_session=False)
        )
        (
            db.query(FeedbackEvaluation)
            .filter(FeedbackEvaluation.attempt_id.in_(attempt_ids))
            .delete(synchronize_session=False)
        )
        (
            db.query(FeedbackRating)
            .filter(FeedbackRating.attempt_id.in_(attempt_ids))
            .delete(synchronize_session=False)
        )
    for attempt in attempts:
        attempt.rationale = None

    (
        db.query(AssessmentResponse)
        .filter(AssessmentResponse.user_id == user.id)
        .delete(synchronize_session=False)
    )

    revoke_all_refresh_tokens(db, user.id)

    user.apple_subject = None
    user.dev_subject = None
    user.timezone = "UTC"
    user.onboarding_status = "deleted"
    user.deleted_at = utcnow()
    db.commit()
    return SimpleOk()
