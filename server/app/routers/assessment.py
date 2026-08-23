"""Onboarding assessment and path reveal (spec §10.3, §10.4, P0-03, P0-04).

Assessment scoring uses author-defined option weights only. No AI call is made.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.content import assessment_content
from app.deps import CurrentUser, DbSession
from app.models import AssessmentResponse, User, UserProfile, utcnow
from app.schemas import (
    AssessmentAnswerRequest,
    AssessmentAnswerResponse,
    AssessmentItem,
    AssessmentOption,
    AssessmentResultResponse,
    AssessmentStateResponse,
)
from app.services import path as path_service
from app.services import skills as skills_service
from app.views import PATH_DISCLAIMER, path_preview, skill_views

router = APIRouter(prefix="/assessment", tags=["assessment"])


def _answered(db: DbSession, user_id: str) -> dict[str, str]:
    rows = (
        db.query(AssessmentResponse)
        .filter(AssessmentResponse.user_id == user_id)
        .all()
    )
    return {row.item_id: row.choice_id for row in rows}


def _item_view(item: dict, total: int) -> AssessmentItem:
    return AssessmentItem(
        id=item["id"],
        index=item["index"],
        total=total,
        prompt=item["prompt"],
        context=item["context"],
        question=item["question"],
        options=[
            AssessmentOption(id=option["id"], label=option["label"])
            for option in item["options"]
        ],
    )


def _next_item(content: dict, answered: dict[str, str]) -> AssessmentItem | None:
    items = sorted(content["items"], key=lambda i: i["index"])
    for item in items:
        if item["id"] not in answered:
            return _item_view(item, len(items))
    return None


def _build_result(
    db: DbSession, user: User, profile: UserProfile
) -> AssessmentResultResponse:
    scores = skills_service.get_scores(db, user.id)
    focus = skills_service.focus_skills(scores)
    today = path_service.local_date_for(user)
    assignments = path_service.upcoming_assignments(db, user.id, today)
    return AssessmentResultResponse(
        starting_level=profile.starting_level or "foundation",
        focus_skills=skill_views(db, user.id, focus),
        skills=skill_views(db, user.id),
        path=path_preview(db, user, assignments),
        disclaimer=PATH_DISCLAIMER,
    )


@router.get("", response_model=AssessmentStateResponse)
def get_assessment(user: CurrentUser, db: DbSession) -> AssessmentStateResponse:
    content = assessment_content()
    answered = _answered(db, user.id)
    next_item = _next_item(content, answered)
    return AssessmentStateResponse(
        notice=content["notice"],
        total_items=len(content["items"]),
        completed_items=len(answered),
        completed=next_item is None,
        next_item=next_item,
    )


@router.post("/responses", response_model=AssessmentAnswerResponse)
def submit_response(
    payload: AssessmentAnswerRequest, user: CurrentUser, db: DbSession
) -> AssessmentAnswerResponse:
    content = assessment_content()
    item = next((i for i in content["items"] if i["id"] == payload.item_id), None)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "unknown_item"}
        )
    if not any(o["id"] == payload.choice_id for o in item["options"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "unknown_choice"}
        )

    existing = (
        db.query(AssessmentResponse)
        .filter(
            AssessmentResponse.user_id == user.id,
            AssessmentResponse.item_id == payload.item_id,
        )
        .first()
    )
    if existing is None:
        db.add(
            AssessmentResponse(
                user_id=user.id,
                item_id=payload.item_id,
                choice_id=payload.choice_id,
                rationale=payload.rationale,
            )
        )
    else:
        existing.choice_id = payload.choice_id
        existing.rationale = payload.rationale
    db.flush()

    answered = _answered(db, user.id)
    next_item = _next_item(content, answered)
    if next_item is not None:
        db.commit()
        return AssessmentAnswerResponse(completed=False, next_item=next_item, result=None)

    profile = db.get(UserProfile, user.id)
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    baselines = skills_service.initialise_from_assessment(db, user.id, answered)
    level = skills_service.starting_level(baselines)
    profile.starting_level = level
    profile.current_level = level
    profile.focus_skills = skills_service.focus_skills(baselines)
    profile.updated_at = utcnow()
    if user.onboarding_status in {"signed_in", "goal_set"}:
        user.onboarding_status = "assessed"
    db.flush()

    today = path_service.local_date_for(user)
    try:
        path_service.build_path(db, user, profile, start_date=today)
    except path_service.NoEligibleScenario as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "no_scenario_available"},
        ) from exc

    db.commit()
    return AssessmentAnswerResponse(
        completed=True, next_item=None, result=_build_result(db, user, profile)
    )


@router.get("/result", response_model=AssessmentResultResponse)
def get_result(user: CurrentUser, db: DbSession) -> AssessmentResultResponse:
    profile = db.get(UserProfile, user.id)
    if profile is None or profile.starting_level is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail={"code": "assessment_incomplete"}
        )
    return _build_result(db, user, profile)
