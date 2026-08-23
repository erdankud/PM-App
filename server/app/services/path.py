"""Deterministic learning-path assignment (spec §12, P0-04).

No AI planning is involved. Given the same user state the same scenario is always
chosen, which makes assignment auditable and testable.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    ChallengeAttempt,
    LearningPathAssignment,
    Scenario,
    User,
    UserProfile,
)
from app.services import skills as skills_service

LEVEL_ORDER = ["foundation", "developing", "advanced"]


class NoEligibleScenario(RuntimeError):
    """Raised when the content library cannot serve this user (spec §18)."""


def resolve_timezone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def local_date_for(user: User, now: datetime | None = None) -> str:
    """The user's device-local calendar date, computed server-side (spec §16)."""
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(resolve_timezone(user.timezone)).date().isoformat()


def _published_scenarios(db: Session) -> list[Scenario]:
    return (
        db.query(Scenario)
        .filter(Scenario.status == "published")
        .order_by(Scenario.scenario_id.asc(), Scenario.version.desc())
        .all()
    )


def _latest_versions(scenarios: list[Scenario]) -> list[Scenario]:
    seen: set[str] = set()
    latest: list[Scenario] = []
    for scenario in scenarios:
        if scenario.scenario_id in seen:
            continue
        seen.add(scenario.scenario_id)
        latest.append(scenario)
    return latest


def _assigned_scenario_ids(db: Session, user_id: str) -> set[str]:
    rows = (
        db.query(LearningPathAssignment.scenario_id)
        .filter(LearningPathAssignment.user_id == user_id)
        .all()
    )
    return {row[0] for row in rows}


def _recent_completed_tags(db: Session, user_id: str, count: int = 3) -> set[str]:
    attempts = (
        db.query(ChallengeAttempt)
        .filter(
            ChallengeAttempt.user_id == user_id,
            ChallengeAttempt.status == "complete",
        )
        .order_by(ChallengeAttempt.completed_at.desc())
        .limit(count)
        .all()
    )
    if not attempts:
        return set()
    ids = [a.scenario_id for a in attempts]
    scenarios = (
        db.query(Scenario).filter(Scenario.scenario_id.in_(ids)).all() if ids else []
    )
    tags: set[str] = set()
    for scenario in scenarios:
        tags.update(scenario.tags or [])
    return tags


def _tag_last_seen(db: Session, user_id: str) -> dict[str, int]:
    """Map tag -> index of the most recent assignment that used it (0 = oldest)."""
    assignments = (
        db.query(LearningPathAssignment)
        .filter(LearningPathAssignment.user_id == user_id)
        .order_by(LearningPathAssignment.local_date.asc())
        .all()
    )
    if not assignments:
        return {}
    ids = [a.scenario_id for a in assignments]
    by_id = {
        s.scenario_id: s for s in db.query(Scenario).filter(Scenario.scenario_id.in_(ids))
    }
    last_seen: dict[str, int] = {}
    for index, assignment in enumerate(assignments):
        scenario = by_id.get(assignment.scenario_id)
        if scenario is None:
            continue
        for tag in scenario.tags or []:
            last_seen[tag] = index
    return last_seen


def _level_fallback_order(level: str) -> list[str]:
    if level not in LEVEL_ORDER:
        return LEVEL_ORDER
    index = LEVEL_ORDER.index(level)
    order = [level]
    for offset in range(1, len(LEVEL_ORDER)):
        for candidate in (index - offset, index + offset):
            if 0 <= candidate < len(LEVEL_ORDER):
                order.append(LEVEL_ORDER[candidate])
    return order


def _least_recently_seen(
    scenarios: list[Scenario], tag_last_seen: dict[str, int]
) -> Scenario:
    def key(scenario: Scenario) -> tuple:
        seen = [tag_last_seen.get(tag, -1) for tag in (scenario.tags or [])]
        recency = max(seen) if seen else -1
        return (recency, scenario.scenario_id)

    return sorted(scenarios, key=key)[0]


def build_path(
    db: Session,
    user: User,
    profile: UserProfile,
    start_date: str,
    days: int | None = None,
    preserve_dates: set[str] | None = None,
) -> list[LearningPathAssignment]:
    """Create or replace assignments from `start_date` forward.

    Existing assignments on or before today, and any date in `preserve_dates`, are
    never rewritten — historical assignments are immutable (spec §12 rule 6).
    """
    days = days or settings.path_days
    preserve = preserve_dates or set()

    stale = (
        db.query(LearningPathAssignment)
        .filter(
            LearningPathAssignment.user_id == user.id,
            LearningPathAssignment.local_date >= start_date,
            LearningPathAssignment.status == "assigned",
        )
        .all()
    )
    for assignment in stale:
        if assignment.local_date not in preserve:
            db.delete(assignment)
    db.flush()

    scores = skills_service.get_scores(db, user.id)
    focus = skills_service.focus_skills(scores)
    if not focus:
        focus = ["product_sense", "analytics"]
    level = profile.current_level or profile.starting_level or "foundation"

    exclude = _assigned_scenario_ids(db, user.id)
    avoid_tags = _recent_completed_tags(db, user.id)
    tag_last_seen = _tag_last_seen(db, user.id)

    base = date.fromisoformat(start_date)
    existing_dates = {
        row.local_date
        for row in db.query(LearningPathAssignment)
        .filter(LearningPathAssignment.user_id == user.id)
        .all()
    }

    profile.path_version = (profile.path_version or 0) + 1
    profile.focus_skills = focus

    created: list[LearningPathAssignment] = []
    for offset in range(days):
        day = (base + timedelta(days=offset)).isoformat()
        if day in existing_dates:
            continue
        # Rule 4: alternate focus skills across days.
        focus_skill = focus[offset % len(focus)]
        scenario = _select_with_recency(
            db,
            level=level,
            focus_skill=focus_skill,
            exclude_scenario_ids=exclude,
            avoid_tags=avoid_tags if offset == 0 else set(),
            tag_last_seen=tag_last_seen,
        )
        assignment = LearningPathAssignment(
            user_id=user.id,
            local_date=day,
            day_index=offset,
            scenario_id=scenario.scenario_id,
            scenario_version=scenario.version,
            path_version=profile.path_version,
            status="assigned",
        )
        db.add(assignment)
        created.append(assignment)
        exclude.add(scenario.scenario_id)
        for tag in scenario.tags or []:
            tag_last_seen[tag] = 10_000 + offset
    db.flush()
    return created


def _select_with_recency(
    db: Session,
    *,
    level: str,
    focus_skill: str,
    exclude_scenario_ids: set[str],
    avoid_tags: set[str],
    tag_last_seen: dict[str, int],
) -> Scenario:
    catalogue = _latest_versions(_published_scenarios(db))
    available = [s for s in catalogue if s.scenario_id not in exclude_scenario_ids]
    if not available:
        available = catalogue
    if not available:
        raise NoEligibleScenario("no published scenarios")

    def stable(scenario: Scenario) -> tuple:
        return (scenario.scenario_id,)

    exact = [s for s in available if s.level == level and s.primary_skill == focus_skill]
    fresh = [s for s in exact if not (set(s.tags or []) & avoid_tags)]
    if fresh:
        return sorted(fresh, key=stable)[0]
    if exact:
        return sorted(exact, key=stable)[0]

    secondary = [
        s
        for s in available
        if s.level == level and focus_skill in (s.secondary_skills or [])
    ]
    fresh = [s for s in secondary if not (set(s.tags or []) & avoid_tags)]
    if fresh:
        return sorted(fresh, key=stable)[0]
    if secondary:
        return sorted(secondary, key=stable)[0]

    same_level = [s for s in available if s.level == level]
    if same_level:
        return _least_recently_seen(same_level, tag_last_seen)

    for fallback_level in _level_fallback_order(level)[1:]:
        candidates = [s for s in available if s.level == fallback_level]
        if candidates:
            return _least_recently_seen(candidates, tag_last_seen)

    raise NoEligibleScenario(f"no scenario for level={level} skill={focus_skill}")


def ensure_assignment_for_today(
    db: Session, user: User, profile: UserProfile
) -> LearningPathAssignment:
    """Guarantee exactly one assignment for the user's current local date."""
    today = local_date_for(user)
    existing = (
        db.query(LearningPathAssignment)
        .filter(
            LearningPathAssignment.user_id == user.id,
            LearningPathAssignment.local_date == today,
        )
        .first()
    )
    if existing is not None:
        return existing

    build_path(db, user, profile, start_date=today)
    db.flush()
    assignment = (
        db.query(LearningPathAssignment)
        .filter(
            LearningPathAssignment.user_id == user.id,
            LearningPathAssignment.local_date == today,
        )
        .first()
    )
    if assignment is None:
        raise NoEligibleScenario("assignment resolver produced no assignment")
    return assignment


def upcoming_assignments(
    db: Session, user_id: str, from_date: str, limit: int = 7
) -> list[LearningPathAssignment]:
    return (
        db.query(LearningPathAssignment)
        .filter(
            LearningPathAssignment.user_id == user_id,
            LearningPathAssignment.local_date >= from_date,
        )
        .order_by(LearningPathAssignment.local_date.asc())
        .limit(limit)
        .all()
    )


def recalculate_future(db: Session, user: User, profile: UserProfile) -> None:
    """Rebuild future assignments after an evaluated attempt (spec §12 rule 6)."""
    today = local_date_for(user)
    tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
    build_path(db, user, profile, start_date=tomorrow, days=settings.path_days - 1)
