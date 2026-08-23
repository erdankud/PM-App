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

SKILL_KEYS: tuple[str, ...] = (
    "product_sense",
    "analytics",
    "user_research",
    "prioritization",
    "execution",
    "communication",
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
    # signed_in -> goal_set -> assessed -> complete
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
    goal: Mapped[str | None] = mapped_column(String(48))
    starting_level: Mapped[str | None] = mapped_column(String(16))
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
    source: Mapped[str] = mapped_column(String(32))  # onboarding_assessment | attempt
    scenario_id: Mapped[str | None] = mapped_column(String(64))
    attempt_id: Mapped[str | None] = mapped_column(String(36), index=True)
    skill_key: Mapped[str] = mapped_column(String(32))
    delta: Mapped[int] = mapped_column(Integer)
    reason_code: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Scenario(Base):
    """Published scenario content, immutable per (id, version) (spec §11, §14)."""

    __tablename__ = "scenarios"
    __table_args__ = (
        UniqueConstraint("scenario_id", "version", name="uq_scenario_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="published", index=True)
    title: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(16), index=True)
    primary_skill: Mapped[str] = mapped_column(String(32), index=True)
    secondary_skills: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    content: Mapped[dict] = mapped_column(JSON)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_assessment_user_item"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[str] = mapped_column(String(64))
    choice_id: Mapped[str] = mapped_column(String(64))
    rationale: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LearningPathAssignment(Base):
    __tablename__ = "learning_path_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_assignment_user_date"),
        Index("ix_assignment_user_status", "user_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    local_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD, device-local
    day_index: Mapped[int] = mapped_column(Integer, default=0)
    scenario_id: Mapped[str] = mapped_column(String(64))
    scenario_version: Mapped[int] = mapped_column(Integer)
    path_version: Mapped[int] = mapped_column(Integer, default=1)
    # assigned -> started -> submitted -> evaluated | feedback_failed
    status: Mapped[str] = mapped_column(String(24), default="assigned")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChallengeAttempt(Base):
    __tablename__ = "challenge_attempts"
    __table_args__ = (
        UniqueConstraint("assignment_id", name="uq_attempt_assignment"),
        Index("ix_attempt_user_status", "user_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("learning_path_assignments.id", ondelete="CASCADE")
    )
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


class XpLedgerEntry(Base):
    """Append-only. One award per (attempt, reason) enforced by the database."""

    __tablename__ = "xp_ledger_entries"
    __table_args__ = (
        UniqueConstraint("attempt_id", "reason", name="uq_xp_attempt_reason"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
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
