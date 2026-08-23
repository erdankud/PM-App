"""Path assignment is deterministic and one-per-day (spec §12, §14)."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import (
    SKILL_KEYS,
    LearningPathAssignment,
    SkillScore,
    User,
    UserProfile,
)
from app.services import path as path_service
from app.services import skills as skills_service


def _make_user(db, scores: dict[str, int], level: str = "foundation") -> tuple[User, UserProfile]:
    user = User(dev_subject=f"path-{uuid.uuid4()}", timezone="Europe/London")
    db.add(user)
    db.flush()
    profile = UserProfile(
        user_id=user.id, starting_level=level, current_level=level
    )
    db.add(profile)
    for key in SKILL_KEYS:
        db.add(SkillScore(user_id=user.id, skill_key=key, score=scores.get(key, 50)))
    db.flush()
    return user, profile


def test_focus_skills_are_the_two_lowest():
    scores = {
        "product_sense": 60,
        "analytics": 41,
        "user_research": 55,
        "prioritization": 38,
        "execution": 62,
        "communication": 50,
    }
    assert skills_service.focus_skills(scores) == ["prioritization", "analytics"]


def test_focus_skills_tie_break_is_stable():
    scores = {key: 50 for key in SKILL_KEYS}
    assert skills_service.focus_skills(scores) == skills_service.focus_skills(scores)


def test_same_state_produces_the_same_path():
    db = SessionLocal()
    try:
        scores = {
            "product_sense": 60,
            "analytics": 40,
            "user_research": 55,
            "prioritization": 38,
            "execution": 62,
            "communication": 50,
        }
        user_a, profile_a = _make_user(db, scores)
        user_b, profile_b = _make_user(db, scores)
        today = "2026-08-23"
        path_a = path_service.build_path(db, user_a, profile_a, start_date=today)
        path_b = path_service.build_path(db, user_b, profile_b, start_date=today)
        db.commit()
        assert [a.scenario_id for a in path_a] == [b.scenario_id for b in path_b]
        assert len(path_a) == 7
    finally:
        db.rollback()
        db.close()


def test_path_alternates_focus_skills_and_avoids_repeats():
    db = SessionLocal()
    try:
        scores = {key: 50 for key in SKILL_KEYS}
        scores["analytics"] = 35
        scores["communication"] = 36
        user, profile = _make_user(db, scores, level="developing")
        assignments = path_service.build_path(db, user, profile, start_date="2026-09-01")
        db.commit()
        scenario_ids = [a.scenario_id for a in assignments]
        assert len(scenario_ids) == len(set(scenario_ids)), "no repeated scenarios"
        assert profile.focus_skills == ["analytics", "communication"]
    finally:
        db.rollback()
        db.close()


def test_one_assignment_per_user_per_local_date():
    db = SessionLocal()
    try:
        user, profile = _make_user(db, {key: 50 for key in SKILL_KEYS})
        db.add(
            LearningPathAssignment(
                user_id=user.id,
                local_date="2026-10-01",
                scenario_id="onboarding-retention-drop",
                scenario_version=1,
            )
        )
        db.flush()
        db.add(
            LearningPathAssignment(
                user_id=user.id,
                local_date="2026-10-01",
                scenario_id="mobile-signup-dropoff",
                scenario_version=1,
            )
        )
        raised = False
        try:
            db.flush()
        except IntegrityError:
            raised = True
        assert raised, "database must reject a second assignment for the same day"
    finally:
        db.rollback()
        db.close()


def test_rebuilding_the_path_preserves_today():
    db = SessionLocal()
    try:
        user, profile = _make_user(db, {key: 50 for key in SKILL_KEYS})
        today = path_service.local_date_for(user)
        first = path_service.ensure_assignment_for_today(db, user, profile)
        db.commit()
        original_id = first.id
        original_scenario = first.scenario_id

        path_service.recalculate_future(db, user, profile)
        db.commit()

        again = path_service.ensure_assignment_for_today(db, user, profile)
        assert again.id == original_id
        assert again.scenario_id == original_scenario
        assert again.local_date == today
    finally:
        db.rollback()
        db.close()


def test_local_date_uses_the_declared_timezone():
    from datetime import datetime, timezone

    user = User(dev_subject="tz-test", timezone="Pacific/Kiritimati")  # UTC+14
    moment = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)
    assert path_service.local_date_for(user, moment) == "2026-08-24"

    user.timezone = "Pacific/Midway"  # UTC-11
    assert path_service.local_date_for(user, moment) == "2026-08-23"

    user.timezone = "Not/AZone"
    assert path_service.local_date_for(user, moment) == "2026-08-23"
