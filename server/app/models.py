"""Relational model for PM Thinking Coach (spec §14).

Server-owned invariants encoded here:
  * one assignment per (user, local_date)
  * one attempt per assignment (MVP)
  * one evidence interaction per (attempt, card)
  * one XP award per (attempt, reason)
Scores, XP, skill deltas and dates are written by the server only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# The six domains of the skill map plus communication, which every gate rubric scores
# regardless of domain (spec v0.2 §7). The node's domain decides where its delta lands.
SKILL_KEYS: tuple[str, ...] = (
    "discovery",
    "value_design",
    "delivery",
    "marketing",
    "growth",
    "economics",
    "communication",
    # System Design — восьмая компетенция, добавлена вместе с седьмым доменом
    # (спека System Design §2.2). Существующие записи стартуют с нейтральных 50.
    "system_design",
)

LEVELS: tuple[str, ...] = ("foundation", "developing", "advanced")

GOALS: tuple[str, ...] = (
    "break_into_pm",
    "grow_in_first_role",
    "practise_product_thinking",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    apple_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    dev_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    # signed_in -> complete (the onboarding diagnostic is gone, spec v0.2 §10)
    onboarding_status: Mapped[str] = mapped_column(String(32), default="signed_in")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped["UserProfile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Optional, and only a highlight filter over the map in this version (spec §7).
    target_role: Mapped[str | None] = mapped_column(String(48))
    # Content language. Stored rather than read from a request header because the
    # evaluation worker writes coaching long after the request that queued it.
    language: Mapped[str] = mapped_column(String(8), default="ru", server_default="ru")
    current_level: Mapped[str | None] = mapped_column(String(16))
    level: Mapped[int] = mapped_column(Integer, default=1)
    total_xp: Mapped[int] = mapped_column(Integer, default=0)
    streak_count: Mapped[int] = mapped_column(Integer, default=0)
    path_version: Mapped[int] = mapped_column(Integer, default=0)
    focus_skills: Mapped[list] = mapped_column(JSON, default=list)
    # Entitlement interface exists but MVP renders no upgrade CTA (spec §20).
    entitlement: Mapped[str] = mapped_column(String(16), default="free")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(back_populates="profile")


class ExerciseAttempt(Base):
    """Попытка формирующего упражнения (спека SD §3.3).

    Намеренно не связана с `BlockProgress`: упражнения не влияют ни на доступность
    гейта, ни на `final_score`, ни на XP. Хранится только ради того, чтобы человек
    видел свой прошлый ответ рядом с эталоном.
    """

    __tablename__ = "exercise_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "exercise_id", name="uq_exercise_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[str] = mapped_column(String(64), index=True)
    submitted_values: Mapped[dict] = mapped_column(JSON, default=dict)
    viewed_reference_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class TermEncounter(Base):
    """Отметка «встречал» в глоссарии: термин показан в прочитанном уроке."""

    __tablename__ = "term_encounters"
    __table_args__ = (UniqueConstraint("user_id", "term_id", name="uq_term_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    term_id: Mapped[str] = mapped_column(String(64), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SkillScore(Base):
    __tablename__ = "skill_scores"
    __table_args__ = (UniqueConstraint("user_id", "skill_key", name="uq_skill_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    skill_key: Mapped[str] = mapped_column(String(32))
    score: Mapped[int] = mapped_column(Integer, default=50)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class SkillAssessment(Base):
    """Append-only audit ledger of every skill delta ever applied."""

    __tablename__ = "skill_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(32))  # always "gate" in v0.2
    scenario_id: Mapped[str | None] = mapped_column(String(64))
    attempt_id: Mapped[str | None] = mapped_column(String(36), index=True)
    skill_key: Mapped[str] = mapped_column(String(32))
    delta: Mapped[int] = mapped_column(Integer)
    reason_code: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChallengeAttempt(Base):
    """One sitting of a block gate. Immutable once submitted (spec v0.1 §9)."""

    __tablename__ = "challenge_attempts"
    __table_args__ = (Index("ix_attempt_user_status", "user_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    gate_id: Mapped[str] = mapped_column(String(64), index=True)
    block_id: Mapped[str] = mapped_column(String(8), index=True)
    # 1-based, so a rubric can tell a first sitting from a retake.
    attempt_index: Mapped[int] = mapped_column(Integer, default=1)
    # Written by the server together with the score; never sent up by the client.
    passed: Mapped[bool | None] = mapped_column(Boolean)
    scenario_id: Mapped[str] = mapped_column(String(64))
    scenario_version: Mapped[int] = mapped_column(Integer)
    # draft -> submitted -> awaiting_feedback -> complete | feedback_failed
    status: Mapped[str] = mapped_column(String(24), default="draft")
    selected_option_id: Mapped[str | None] = mapped_column(String(64))
    rationale: Mapped[str | None] = mapped_column(Text)
    draft_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_points: Mapped[int | None] = mapped_column(Integer)
    decision_points: Mapped[int | None] = mapped_column(Integer)
    rationale_points: Mapped[int | None] = mapped_column(Integer)
    communication_points: Mapped[int | None] = mapped_column(Integer)
    final_score: Mapped[int | None] = mapped_column(Integer)
    xp_awarded: Mapped[int | None] = mapped_column(Integer)


class EvidenceInteraction(Base):
    __tablename__ = "evidence_interactions"
    __table_args__ = (
        UniqueConstraint("attempt_id", "evidence_card_id", name="uq_evidence_attempt"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    attempt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("challenge_attempts.id", ondelete="CASCADE"), index=True
    )
    evidence_card_id: Mapped[str] = mapped_column(String(64))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FeedbackEvaluation(Base):
    __tablename__ = "feedback_evaluations"

    attempt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("challenge_attempts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    # queued -> running -> complete | failed
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    consequence_snapshot: Mapped[str] = mapped_column(Text)
    option_label_snapshot: Mapped[str] = mapped_column(String(120), default="")
    ai_json: Mapped[dict | None] = mapped_column(JSON)
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    model_id: Mapped[str | None] = mapped_column(String(120))
    provider: Mapped[str | None] = mapped_column(String(32))
    error_code: Mapped[str | None] = mapped_column(String(64))
    provider_attempts: Mapped[int] = mapped_column(Integer, default=0)
    needs_retry: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LessonProgress(Base):
    """A lesson is either read or not. Re-reading changes nothing and awards nothing."""

    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    lesson_id: Mapped[str] = mapped_column(String(64))
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class BlockProgress(Base):
    """Server-owned unlock state. The client renders this and never computes it."""

    __tablename__ = "block_progress"
    __table_args__ = (UniqueConstraint("user_id", "block_id", name="uq_block_progress"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    block_id: Mapped[str] = mapped_column(String(8))
    # locked -> available -> in_progress -> gate_ready -> passed
    status: Mapped[str] = mapped_column(String(16), default="locked")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    passed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class XpLedgerEntry(Base):
    """Append-only. One award per (user, reason, ref) enforced by the database.

    `ref_id` is a lesson id or a block id depending on `reason`, which is what makes
    re-reading a lesson or re-passing a block award nothing (spec v0.2 §9).
    """

    __tablename__ = "xp_ledger_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "reason", "ref_id", name="uq_xp_user_reason_ref"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    ref_id: Mapped[str] = mapped_column(String(64))
    attempt_id: Mapped[str | None] = mapped_column(String(36))
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(48))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FeedbackRating(Base):
    __tablename__ = "feedback_ratings"

    attempt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("challenge_attempts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    rating: Mapped[str] = mapped_column(String(16))  # useful | not_useful
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", "key", name="uq_idempotency"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    endpoint: Mapped[str] = mapped_column(String(120))
    key: Mapped[str] = mapped_column(String(128))
    target_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AnalyticsEvent(Base):
    """Event metadata only. Never contains rationale text or feedback copy (spec §19)."""

    __tablename__ = "analytics_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    app_version: Mapped[str | None] = mapped_column(String(32))
    platform: Mapped[str | None] = mapped_column(String(16))
    client_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
