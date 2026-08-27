"""profile content language

Adds the stored content language. Existing rows default to English, which is the
language every scenario was authored in, so no back-fill is needed.

Revision ID: 9c1f4a2b7d31
Revises: 204863eceb4b
Create Date: 2026-08-23 20:05:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '9c1f4a2b7d31'
down_revision = '204863eceb4b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('user_profiles', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'language',
                sa.String(length=8),
                nullable=False,
                server_default='en',
            )
        )


def downgrade() -> None:
    with op.batch_alter_table('user_profiles', schema=None) as batch_op:
        batch_op.drop_column('language')
