"""google and password identity

Adds the two identity paths that do not need an Apple Developer account: a Google
`sub` and an email/password pair. All three columns are nullable — an existing
account has none of them and keeps signing in exactly as before.

The unique indexes are what stop two accounts from claiming one identity. SQLite
needs `batch_alter_table` to add them, which is why this is not a bare `add_column`.

Revision ID: 9a824463b717
Revises: c3a8f1e260b4
Create Date: 2026-09-04 10:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '9a824463b717'
down_revision = 'c3a8f1e260b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('google_subject', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('email', sa.String(length=320), nullable=True))
        batch_op.add_column(sa.Column('password_hash', sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint('uq_users_google_subject', ['google_subject'])
        batch_op.create_unique_constraint('uq_users_email', ['email'])


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('uq_users_email', type_='unique')
        batch_op.drop_constraint('uq_users_google_subject', type_='unique')
        batch_op.drop_column('password_hash')
        batch_op.drop_column('email')
        batch_op.drop_column('google_subject')
