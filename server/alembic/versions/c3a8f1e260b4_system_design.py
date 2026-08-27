"""system design: exercises and glossary encounters

Спека System Design §4.1. Домен добавляет две пользовательские сущности: попытки
формирующих упражнений и отметки «встречал» у терминов глоссария. Ни та, ни другая
не влияют на прогресс по блокам — упражнения намеренно не связаны с `BlockProgress`.

Восьмая компетенция (`system_design`) миграции не требует: строки `skill_scores`
создаются лениво со значением 50, поэтому существующие пользователи получают
нейтральный старт сами.

Revision ID: c3a8f1e260b4
Revises: b7d2e4915c08
Create Date: 2026-08-25 12:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'c3a8f1e260b4'
down_revision = 'b7d2e4915c08'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exercise_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("exercise_id", sa.String(length=64), nullable=False),
        sa.Column("submitted_values", sa.JSON(), nullable=True),
        sa.Column("viewed_reference_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "exercise_id", name="uq_exercise_user"),
    )
    op.create_index(
        op.f("ix_exercise_attempts_user_id"), "exercise_attempts", ["user_id"]
    )
    op.create_index(
        op.f("ix_exercise_attempts_exercise_id"), "exercise_attempts", ["exercise_id"]
    )

    op.create_table(
        "term_encounters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("term_id", sa.String(length=64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "term_id", name="uq_term_user"),
    )
    op.create_index(op.f("ix_term_encounters_user_id"), "term_encounters", ["user_id"])
    op.create_index(op.f("ix_term_encounters_term_id"), "term_encounters", ["term_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_term_encounters_term_id"), table_name="term_encounters")
    op.drop_index(op.f("ix_term_encounters_user_id"), table_name="term_encounters")
    op.drop_table("term_encounters")
    op.drop_index(op.f("ix_exercise_attempts_exercise_id"), table_name="exercise_attempts")
    op.drop_index(op.f("ix_exercise_attempts_user_id"), table_name="exercise_attempts")
    op.drop_table("exercise_attempts")
