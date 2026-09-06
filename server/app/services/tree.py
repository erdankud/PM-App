"""Block unlocking, lesson progress and gate lifecycle (spec v0.2 §4, §9).

Every status here is computed on the server and handed to the client finished. The
client never derives availability: `POST /gates/{id}/start` re-checks it, so a UI bug
or a crafted request cannot open a block early (spec v0.2 §12).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import tree_content
from app.config import settings
from app.models import (
    BlockProgress,
    ChallengeAttempt,
    LessonProgress,
    UserProfile,
    XpLedgerEntry,
    utcnow,
)
from app.services.scoring import level_for_xp

LOCKED = "locked"
AVAILABLE = "available"
IN_PROGRESS = "in_progress"
GATE_READY = "gate_ready"
PASSED = "passed"


class BlockNotReady(RuntimeError):
    """The learner has not earned access to this gate yet."""


# --- Progress rows -----------------------------------------------------------


def _progress_rows(db: Session, user_id: str) -> dict[str, BlockProgress]:
    return {
        row.block_id: row
        for row in db.query(BlockProgress).filter(BlockProgress.user_id == user_id)
    }


def completed_lesson_ids(db: Session, user_id: str) -> set[str]:
    return {
        row.lesson_id
        for row in db.query(LessonProgress).filter(LessonProgress.user_id == user_id)
    }


def _ensure_rows(db: Session, user_id: str) -> dict[str, BlockProgress]:
    """Заводит недостающие строки прогресса, переживая гонку двух запросов.

    Первое чтение карты у нового аккаунта идёт двумя запросами сразу — `/tree` и
    `/trees`, — и оба видят пустой прогресс. Без этого второй падал с нарушением
    уникальности, то есть карта не открывалась с первого раза.
    """
    rows = _progress_rows(db, user_id)
    missing = [
        block["id"] for block in tree_content.all_blocks() if block["id"] not in rows
    ]
    if not missing:
        return rows

    for block_id in missing:
        db.add(BlockProgress(user_id=user_id, block_id=block_id, status=LOCKED))
    try:
        db.flush()
    except IntegrityError:
        # Строки создал соседний запрос — это и есть нужный результат.
        db.rollback()
    return _progress_rows(db, user_id)


def recompute(db: Session, user_id: str) -> dict[str, BlockProgress]:
    """Bring every block's status in line with lessons read and gates passed.

    Idempotent and cheap: 36 blocks across two trees, one query for lessons, one for
    progress. Called
    after anything that could change availability, and on first read so a new account
    starts with the root open.
    """
    rows = _ensure_rows(db, user_id)
    completed = completed_lesson_ids(db, user_id)
    now = utcnow()

    # Обе карты сразу: у System Design свой корень, и он открыт с первого дня
    # (спека SD §2.3), поэтому пересчёт идёт по объединённому списку блоков.
    for block in tree_content.all_blocks():
        row = rows[block["id"]]

        if row.status == PASSED:
            continue

        prerequisites = block["prerequisiteBlockIds"]
        unlocked = all(
            rows.get(p) is not None and rows[p].status == PASSED for p in prerequisites
        )
        if not unlocked:
            row.status = LOCKED
            continue

        if row.unlocked_at is None:
            row.unlocked_at = now

        lessons = tree_content.lessons_for_block(block["id"])
        done = sum(1 for lesson in lessons if lesson["id"] in completed)
        if lessons and done == len(lessons):
            row.status = GATE_READY
        elif done > 0:
            row.status = IN_PROGRESS
        else:
            row.status = AVAILABLE

    return rows


def block_progress(db: Session, user_id: str, block_id: str) -> BlockProgress:
    rows = recompute(db, user_id)
    return rows[block_id]


# --- Lessons -----------------------------------------------------------------


def complete_lesson(db: Session, user_id: str, lesson_id: str) -> tuple[bool, int]:
    """Mark a lesson read. Returns (was_new, xp_awarded). Safe to call repeatedly."""
    existing = (
        db.query(LessonProgress)
        .filter(
            LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id
        )
        .first()
    )
    if existing is not None:
        return False, 0

    db.add(LessonProgress(user_id=user_id, lesson_id=lesson_id))
    try:
        db.flush()
    except IntegrityError:
        # Two taps racing each other. The row exists; that is the whole contract.
        db.rollback()
        return False, 0

    awarded = award_xp(
        db,
        user_id=user_id,
        amount=settings.xp_lesson_completed,
        reason="lesson_completed",
        ref_id=lesson_id,
    )
    refresh_totals(db, user_id)
    return True, awarded


def refresh_totals(db: Session, user_id: str) -> None:
    """Recompute the profile total from the ledger.

    The ledger is the record and the profile column is a cache, so it is always
    derived rather than incremented — a duplicate award can never inflate it.
    """
    profile = db.get(UserProfile, user_id)
    if profile is None:
        return
    rows = (
        db.query(XpLedgerEntry)
        .filter(XpLedgerEntry.user_id == user_id)
        .with_entities(XpLedgerEntry.amount)
        .all()
    )
    profile.total_xp = sum(row[0] for row in rows)
    profile.level = level_for_xp(profile.total_xp)
    profile.updated_at = utcnow()


def award_xp(
    db: Session,
    *,
    user_id: str,
    amount: int,
    reason: str,
    ref_id: str,
    attempt_id: str | None = None,
) -> int:
    """Append-only and idempotent by (user, reason, ref). Returns XP actually added."""
    if amount <= 0:
        return 0
    db.add(
        XpLedgerEntry(
            user_id=user_id,
            ref_id=ref_id,
            attempt_id=attempt_id,
            amount=amount,
            reason=reason,
        )
    )
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return 0
    return amount


# --- Gates -------------------------------------------------------------------


def choose_scenario(db: Session, user_id: str, gate: dict) -> str:
    """Least recently seen scenario for this gate.

    A retake must not be the same situation, or the second attempt measures memory of
    which option was right rather than judgment (spec v0.2 §8, §9).
    """
    seen: dict[str, datetime] = {}
    for attempt in (
        db.query(ChallengeAttempt)
        .filter(
            ChallengeAttempt.user_id == user_id,
            ChallengeAttempt.gate_id == gate["id"],
        )
        .order_by(ChallengeAttempt.started_at.asc())
    ):
        started = attempt.started_at
        if started is not None and started.tzinfo is None:
            # SQLite returns naive datetimes; everything here is UTC by construction.
            started = started.replace(tzinfo=timezone.utc)
        seen[attempt.scenario_id] = started

    epoch = datetime.min.replace(tzinfo=timezone.utc)
    return min(gate["scenarioIds"], key=lambda sid: seen.get(sid) or epoch)


def start_gate(db: Session, user_id: str, gate_id: str) -> ChallengeAttempt:
    """Create the attempt for a gate sitting, or return the one already open."""
    gate = tree_content.gate(gate_id)
    if gate is None:
        raise LookupError(gate_id)

    progress = block_progress(db, user_id, gate["blockId"])
    if progress.status not in {GATE_READY, PASSED}:
        raise BlockNotReady(progress.status)

    open_attempt = (
        db.query(ChallengeAttempt)
        .filter(
            ChallengeAttempt.user_id == user_id,
            ChallengeAttempt.gate_id == gate_id,
            ChallengeAttempt.status == "draft",
        )
        .first()
    )
    if open_attempt is not None:
        return open_attempt

    previous = (
        db.query(ChallengeAttempt)
        .filter(
            ChallengeAttempt.user_id == user_id, ChallengeAttempt.gate_id == gate_id
        )
        .count()
    )
    scenario_id = choose_scenario(db, user_id, gate)
    scenario = tree_content.scenario(scenario_id)
    attempt = ChallengeAttempt(
        user_id=user_id,
        gate_id=gate_id,
        block_id=gate["blockId"],
        attempt_index=previous + 1,
        scenario_id=scenario_id,
        scenario_version=scenario["version"],
        status="draft",
    )
    db.add(attempt)
    progress.attempt_count = previous + 1
    db.flush()
    return attempt


def pass_threshold(gate: dict) -> int:
    return int(gate.get("passThreshold") or settings.gate_pass_threshold)


def record_gate_result(db: Session, attempt: ChallengeAttempt, score: int) -> bool:
    """Write pass/fail and reopen the graph. Caller commits; this must run inside the
    same transaction as the score and the skill deltas (spec v0.2 §9, §11)."""
    gate = tree_content.gate(attempt.gate_id)
    threshold = pass_threshold(gate) if gate else settings.gate_pass_threshold
    passed = score >= threshold
    attempt.passed = passed

    progress = (
        db.query(BlockProgress)
        .filter(
            BlockProgress.user_id == attempt.user_id,
            BlockProgress.block_id == attempt.block_id,
        )
        .first()
    )
    if passed and progress is not None and progress.status != PASSED:
        progress.status = PASSED
        progress.passed_at = utcnow()
        db.flush()
        recompute(db, attempt.user_id)
    return passed
