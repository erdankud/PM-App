"""Today's challenge and the challenge payload (spec §10.5, §10.6, P0-05)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.models import (
    ChallengeAttempt,
    EvidenceInteraction,
    LearningPathAssignment,
    Scenario,
    User,
    UserProfile,
    utcnow,
)
from app.schemas import (
    AttemptView,
    BriefView,
    ChallengeResponse,
    DecisionOptionView,
    EvidenceCardView,
    ScenarioView,
    TodayAssignment,
    TodayResponse,
)
from app.services import path as path_service
from app.services import skills as skills_service
from app.views import WHAT_GOOD_LOOKS_LIKE, attempt_state, path_preview, skill_views

router = APIRouter(tags=["today"])


def _profile(db: DbSession, user_id: str) -> UserProfile:
    profile = db.get(UserProfile, user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "profile_missing"}
        )
    return profile


def _require_onboarded(user: User) -> None:
    if user.onboarding_status in {"signed_in", "goal_set"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "onboarding_incomplete"},
        )


def _scenario_for(db: DbSession, assignment: LearningPathAssignment) -> Scenario:
    scenario = (
        db.query(Scenario)
        .filter(
            Scenario.scenario_id == assignment.scenario_id,
            Scenario.version == assignment.scenario_version,
        )
        .first()
    )
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "scenario_content_unavailable"},
        )
    return scenario


def _attempt_for(db: DbSession, assignment_id: str) -> ChallengeAttempt | None:
    return (
        db.query(ChallengeAttempt)
        .filter(ChallengeAttempt.assignment_id == assignment_id)
        .first()
    )


@router.get("/today", response_model=TodayResponse)
def get_today(user: CurrentUser, db: DbSession) -> TodayResponse:
    _require_onboarded(user)
    profile = _profile(db, user.id)

    try:
        assignment = path_service.ensure_assignment_for_today(db, user, profile)
        db.commit()
    except path_service.NoEligibleScenario as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "no_scenario_available"},
        ) from exc

    scenario = _scenario_for(db, assignment)
    attempt = _attempt_for(db, assignment.id)
    today = path_service.local_date_for(user)
    upcoming = path_service.upcoming_assignments(db, user.id, today, limit=7)

    return TodayResponse(
        local_date=today,
        assignment=TodayAssignment(
            assignment_id=assignment.id,
            local_date=assignment.local_date,
            scenario_id=scenario.scenario_id,
            title=scenario.title,
            summary=scenario.summary,
            estimated_minutes=scenario.estimated_minutes,
            level=scenario.level,
            primary_skill=scenario.primary_skill,
            primary_skill_label=skills_service.SKILL_LABELS.get(
                scenario.primary_skill, scenario.primary_skill
            ),
            context_label=(scenario.tags or ["product"])[0].replace("-", " ").title(),
            state=attempt_state(attempt, assignment),
            attempt_id=attempt.id if attempt else None,
            score=attempt.final_score if attempt else None,
        ),
        upcoming=path_preview(db, user, upcoming),
        level=profile.level,
        total_xp=profile.total_xp,
        streak_count=profile.streak_count,
        focus_skills=skill_views(db, user.id, list(profile.focus_skills or [])),
    )


@router.get("/challenges/{assignment_id}", response_model=ChallengeResponse)
def get_challenge(
    assignment_id: str, user: CurrentUser, db: DbSession
) -> ChallengeResponse:
    assignment = db.get(LearningPathAssignment, assignment_id)
    # Ownership is enforced from the token, never from a client-supplied user id.
    if assignment is None or assignment.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "assignment_not_found"}
        )

    scenario = _scenario_for(db, assignment)
    attempt = _attempt_for(db, assignment.id)
    if attempt is None:
        attempt = ChallengeAttempt(
            user_id=user.id,
            assignment_id=assignment.id,
            scenario_id=assignment.scenario_id,
            scenario_version=assignment.scenario_version,
            status="draft",
        )
        db.add(attempt)
        if assignment.status == "assigned":
            assignment.status = "started"
        db.commit()

    reviewed = [
        row.evidence_card_id
        for row in db.query(EvidenceInteraction)
        .filter(EvidenceInteraction.attempt_id == attempt.id)
        .order_by(EvidenceInteraction.opened_at.asc())
        .all()
    ]

    content = scenario.content
    return ChallengeResponse(
        assignment_id=assignment.id,
        local_date=assignment.local_date,
        state=attempt_state(attempt, assignment),
        scenario=ScenarioView(
            id=scenario.scenario_id,
            version=scenario.version,
            title=scenario.title,
            summary=scenario.summary,
            estimated_minutes=scenario.estimated_minutes,
            level=scenario.level,
            primary_skill=scenario.primary_skill,
            primary_skill_label=skills_service.SKILL_LABELS.get(
                scenario.primary_skill, scenario.primary_skill
            ),
            tags=list(scenario.tags or []),
            brief=BriefView(
                **content["brief"], what_good_looks_like=WHAT_GOOD_LOOKS_LIKE
            ),
            evidence_cards=[
                EvidenceCardView(**card)
                for card in sorted(content["evidenceCards"], key=lambda c: c["order"])
            ],
            decision_prompt=content["decisionPrompt"],
            # Consequence text and the authored rubric are deliberately withheld
            # until the attempt is submitted (spec §10.8, §10.9).
            decision_options=[
                DecisionOptionView(
                    id=option["id"],
                    label=option["label"],
                    description=option["description"],
                )
                for option in content["decisionOptions"]
            ],
        ),
        attempt=AttemptView(
            attempt_id=attempt.id,
            status=attempt.status,
            selected_option_id=attempt.selected_option_id,
            rationale=attempt.rationale,
            reviewed_evidence_ids=reviewed,
        ),
    )
