"""practice sessions

Модуль Practice: одна таблица на все шесть направлений. Задача, ответ и разбор
лежат в JSON, потому что форма у направлений разная — канва из шести полей у
Product Sense, диалог с данными у аналитики — и колонка на каждое поле означала бы
миграцию на каждое новое направление.

Revision ID: d5f18c3a90b2
Revises: 9a824463b717
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d5f18c3a90b2"
down_revision = "9a824463b717"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("track", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("brief", sa.JSON(), nullable=True),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("feedback", sa.JSON(), nullable=True),
        sa.Column("asked", sa.JSON(), nullable=True),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=True),
        sa.Column("brief_model_id", sa.String(length=64), nullable=True),
        sa.Column("feedback_model_id", sa.String(length=64), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_practice_sessions_user_id", "practice_sessions", ["user_id"], unique=False
    )
    op.create_index(
        "ix_practice_sessions_track", "practice_sessions", ["track"], unique=False
    )
    op.create_index(
        "ix_practice_user_track",
        "practice_sessions",
        ["user_id", "track", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_practice_user_track", table_name="practice_sessions")
    op.drop_index("ix_practice_sessions_track", table_name="practice_sessions")
    op.drop_index("ix_practice_sessions_user_id", table_name="practice_sessions")
    op.drop_table("practice_sessions")
