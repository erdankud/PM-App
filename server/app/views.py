"""Builders that turn database rows into API payloads."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    ChallengeAttempt,
    LearningPathAssignment,
    Scenario,
    User,
    UserProfile,
)
from app.schemas import (
    MeResponse,
    PathPreviewDay,
    SkillView,
)
from app.services import path as path_service
from app.services import skills as skills_service
from app.services.scoring import xp_for_next_level

WHAT_GOOD_LOOKS_LIKE = "Use the evidence, make a trade-off, and explain your choice."

PROGRESS_FOOTNOTE = (
    "Skill scores are practice signals based on your in-app work, not an assessment "
    "of job readiness."
)

PATH_DISCLAIMER = (
    "This is a starting point based on three short questions, not a validated "
    "assessment. It only affects which scenarios you see first."
)


def skill_views(db: Session, user_id: str, keys: list[str] | None = None) -> list[SkillView]:
    scores = skills_service.get_scores(db, user_id)
    trend_map = skills_service.trends(db, user_id)
    selected = keys if keys is not None else list(scores.keys())
    return [
        SkillView(
            key=key,
            label=skills_service.SKILL_LABELS.get(key, key),
            score=scores.get(key, 50),
            trend=trend_map.get(key, "steady"),
        )
        for key in selected
    ]


def me_response(db: Session, user: User, profile: UserProfile) -> MeResponse:
    return MeResponse(
        user_id=user.id,
        onboarding_status=user.onboarding_status,
        goal=profile.goal,
        timezone=user.timezone,
        starting_level=profile.starting_level,
        current_level=profile.current_level,
        level=profile.level,
        total_xp=profile.total_xp,
        xp_for_next_level=xp_for_next_level(profile.total_xp),
        streak_count=profile.streak_count,
        entitlement=profile.entitlement,
        focus_skills=list(profile.focus_skills or []),
        skills=skill_views(db, user.id),
    )


def attempt_state(
    attempt: ChallengeAttempt | None, assignment: LearningPathAssignment
) -> str:
    if attempt is None:
        return "not_started"
    if attempt.status == "draft":
        has_progress = bool(attempt.selected_option_id or attempt.rationale)
        return "in_progress" if has_progress else "not_started"
    if attempt.status == "submitted":
        return "submitted"
    if attempt.status == "awaiting_feedback":
        return "awaiting_feedback"
    if attempt.status == "feedback_failed":
        return "feedback_failed"
    if attempt.status == "complete":
        return "complete"
    return "not_started"


def scenario_map(db: Session, scenario_ids: list[str]) -> dict[str, Scenario]:
    if not scenario_ids:
        return {}
    rows = db.query(Scenario).filter(Scenario.scenario_id.in_(scenario_ids)).all()
    latest: dict[str, Scenario] = {}
    for row in rows:
        current = latest.get(row.scenario_id)
        if current is None or row.version > current.version:
            latest[row.scenario_id] = row
    return latest


def path_preview(
    db: Session, user: User, assignments: list[LearningPathAssignment]
) -> list[PathPreviewDay]:
    today = path_service.local_date_for(user)
    scenarios = scenario_map(db, [a.scenario_id for a in assignments])
    days: list[PathPreviewDay] = []
    for assignment in assignments:
        scenario = scenarios.get(assignment.scenario_id)
        if scenario is None:
            continue
        days.append(
            PathPreviewDay(
                local_date=assignment.local_date,
                day_index=assignment.day_index,
                scenario_id=scenario.scenario_id,
                title=scenario.title,
                primary_skill=scenario.primary_skill,
                primary_skill_label=skills_service.SKILL_LABELS.get(
                    scenario.primary_skill, scenario.primary_skill
                ),
                level=scenario.level,
                estimated_minutes=scenario.estimated_minutes,
                is_today=assignment.local_date == today,
            )
        )
    return days
