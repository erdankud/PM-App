"""Progress dashboard and gate history (spec v0.2 §10).

There is no calendar here any more. Progress is measured in blocks passed and lessons
read, because that is what the learner is actually moving through (spec v0.2 §1).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app import tree_content
from app.deps import ContentLanguage, CurrentUser, DbSession
from app.models import ChallengeAttempt, FeedbackEvaluation, UserProfile
from app.schemas import HistoryItem, HistoryResponse, ProgressResponse
from app.services import tree as tree_service
from app.services.scoring import xp_for_next_level
from app.views import progress_footnote, skill_views

router = APIRouter(tags=["progress"])


@router.get("/progress", response_model=ProgressResponse)
def get_progress(
    user: CurrentUser, db: DbSession, language: ContentLanguage
) -> ProgressResponse:
    profile = db.get(UserProfile, user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"code": "profile_missing"}
        )

    content = tree_content.tree_content()
    rows = tree_service.recompute(db, user.id)
    db.commit()
    completed = tree_service.completed_lesson_ids(db, user.id)

    gates_attempted = (
        db.query(ChallengeAttempt)
        .filter(
            ChallengeAttempt.user_id == user.id,
            ChallengeAttempt.status != "draft",
        )
        .count()
    )

    return ProgressResponse(
        level=profile.level,
        total_xp=profile.total_xp,
        xp_for_next_level=xp_for_next_level(profile.total_xp),
        blocks_passed=sum(1 for row in rows.values() if row.status == tree_service.PASSED),
        blocks_total=len(content["tree"]["blocks"]),
        lessons_completed=len(completed & set(content["lessons"])),
        lessons_total=len(content["lessons"]),
        gates_attempted=gates_attempted,
        skills=skill_views(db, user.id, language=language),
        footnote=progress_footnote(language),
    )


@router.get("/history", response_model=HistoryResponse)
def get_history(
    user: CurrentUser,
    db: DbSession,
    language: ContentLanguage,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> HistoryResponse:
    rows = (
        db.query(ChallengeAttempt)
        .filter(
            ChallengeAttempt.user_id == user.id,
            ChallengeAttempt.status.in_(
                ["awaiting_feedback", "complete", "feedback_failed"]
            ),
        )
        .order_by(ChallengeAttempt.submitted_at.desc())
        .offset(offset)
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    rows = rows[:limit]

    attempt_ids = [attempt.id for attempt in rows]
    evaluations = (
        {
            row.attempt_id: row
            for row in db.query(FeedbackEvaluation).filter(
                FeedbackEvaluation.attempt_id.in_(attempt_ids)
            )
        }
        if attempt_ids
        else {}
    )
    scenarios = tree_content.all_content()["scenarios"]

    items: list[HistoryItem] = []
    for attempt in rows:
        scenario = scenarios.get(attempt.scenario_id)
        block = tree_content.block(attempt.block_id)
        evaluation = evaluations.get(attempt.id)
        if evaluation is None:
            feedback_status = "pending"
        elif evaluation.status in {"complete", "failed"}:
            feedback_status = evaluation.status
        else:
            feedback_status = "pending"
        items.append(
            HistoryItem(
                attempt_id=attempt.id,
                gate_id=attempt.gate_id,
                block_id=attempt.block_id,
                block_title=block["title"] if block else attempt.block_id,
                scenario_id=attempt.scenario_id,
                title=scenario["title"] if scenario else attempt.scenario_id,
                attempt_index=attempt.attempt_index,
                submitted_at=attempt.submitted_at.isoformat()
                if attempt.submitted_at
                else None,
                score=attempt.final_score,
                passed=attempt.passed,
                feedback_status=feedback_status,
            )
        )

    return HistoryResponse(
        items=items, next_offset=(offset + limit) if has_more else None
    )
