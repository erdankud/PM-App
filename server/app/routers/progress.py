"""Progress dashboard and history (spec §10.11, §10.12, P0-10, P0-11)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import CurrentUser, DbSession
from app.models import (
    ChallengeAttempt,
    FeedbackEvaluation,
    LearningPathAssignment,
    User,
    UserProfile,
)
from app.schemas import (
    ActivityDay,
    HistoryItem,
    HistoryResponse,
    ProgressResponse,
)
from app.services import path as path_service
from app.services import skills as skills_service
from app.services.scoring import xp_for_next_level
from app.views import PROGRESS_FOOTNOTE, scenario_map, skill_views

router = APIRouter(tags=["progress"])


def _completed_dates(db: DbSession, user_id: str) -> dict[str, str]:
    """local_date -> attempt status, for attempts that reached a terminal state."""
    rows = (
        db.query(LearningPathAssignment, ChallengeAttempt)
        .join(
            ChallengeAttempt,
            ChallengeAttempt.assignment_id == LearningPathAssignment.id,
        )
        .filter(LearningPathAssignment.user_id == user_id)
        .all()
    )
    return {
        assignment.local_date: attempt.status
        for assignment, attempt in rows
    }


def compute_streak(db: DbSession, user: User) -> int:
    """Consecutive days ending today (or yesterday) with a completed challenge."""
    statuses = _completed_dates(db, user.id)
    today = date.fromisoformat(path_service.local_date_for(user))
    if statuses.get(today.isoformat()) == "complete":
        cursor = today
    elif statuses.get((today - timedelta(days=1)).isoformat()) == "complete":
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while statuses.get(cursor.isoformat()) == "complete":
        streak += 1
        cursor -= timedelta(days=1)
    return streak


@router.get("/progress", response_model=ProgressResponse)
def get_progress(user: CurrentUser, db: DbSession) -> ProgressResponse:
    profile = db.get(UserProfile, user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "profile_missing"}
        )

    statuses = _completed_dates(db, user.id)
    today_str = path_service.local_date_for(user)
    today = date.fromisoformat(today_str)

    assigned_dates = {
        row.local_date
        for row in db.query(LearningPathAssignment)
        .filter(LearningPathAssignment.user_id == user.id)
        .all()
    }

    activity: list[ActivityDay] = []
    for offset in range(6, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        if statuses.get(day) == "complete":
            state = "completed"
        elif day == today_str:
            state = "today"
        elif day > today_str:
            state = "upcoming"
        elif day in assigned_dates:
            state = "missed"
        else:
            state = "missed"
        activity.append(ActivityDay(local_date=day, state=state))

    completed_count = (
        db.query(ChallengeAttempt)
        .filter(
            ChallengeAttempt.user_id == user.id,
            ChallengeAttempt.status == "complete",
        )
        .count()
    )

    streak = compute_streak(db, user)
    if profile.streak_count != streak:
        profile.streak_count = streak
        db.commit()

    return ProgressResponse(
        level=profile.level,
        total_xp=profile.total_xp,
        xp_for_next_level=xp_for_next_level(profile.total_xp),
        completed_count=completed_count,
        streak_count=streak,
        activity=activity,
        skills=skill_views(db, user.id),
        footnote=PROGRESS_FOOTNOTE,
    )


@router.get("/history", response_model=HistoryResponse)
def get_history(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> HistoryResponse:
    rows = (
        db.query(ChallengeAttempt, LearningPathAssignment)
        .join(
            LearningPathAssignment,
            LearningPathAssignment.id == ChallengeAttempt.assignment_id,
        )
        .filter(
            ChallengeAttempt.user_id == user.id,
            ChallengeAttempt.status.in_(
                ["awaiting_feedback", "complete", "feedback_failed"]
            ),
        )
        .order_by(LearningPathAssignment.local_date.desc())
        .offset(offset)
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    rows = rows[:limit]

    scenarios = scenario_map(db, [attempt.scenario_id for attempt, _ in rows])
    attempt_ids = [attempt.id for attempt, _ in rows]
    evaluations = {
        row.attempt_id: row
        for row in db.query(FeedbackEvaluation).filter(
            FeedbackEvaluation.attempt_id.in_(attempt_ids)
        )
    } if attempt_ids else {}

    items: list[HistoryItem] = []
    for attempt, assignment in rows:
        scenario = scenarios.get(attempt.scenario_id)
        if scenario is None:
            continue
        evaluation = evaluations.get(attempt.id)
        if evaluation is None:
            feedback_status = "pending"
        elif evaluation.status == "complete":
            feedback_status = "complete"
        elif evaluation.status == "failed":
            feedback_status = "failed"
        else:
            feedback_status = "pending"
        items.append(
            HistoryItem(
                attempt_id=attempt.id,
                scenario_id=scenario.scenario_id,
                title=scenario.title,
                local_date=assignment.local_date,
                primary_skill=scenario.primary_skill,
                primary_skill_label=skills_service.SKILL_LABELS.get(
                    scenario.primary_skill, scenario.primary_skill
                ),
                level=scenario.level,
                score=attempt.final_score,
                feedback_status=feedback_status,
            )
        )

    return HistoryResponse(
        items=items, next_offset=(offset + limit) if has_more else None
    )
