"""skill tree: blocks, lessons, gates

Spec v0.2 §11. Progress stops being gated by the calendar and starts being gated by
knowledge, so the daily-assignment machinery and the onboarding diagnostic go away and
lesson/block progress arrives. Scenario content moves out of the database into
validated files alongside the lessons, so `scenarios` is dropped too.

This is destructive to v0.1 learner data by design: an attempt tied to a daily
assignment has no gate to belong to.

Revision ID: b7d2e4915c08
Revises: 9c1f4a2b7d31
Create Date: 2026-08-23 22:40:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'b7d2e4915c08'
down_revision = '9c1f4a2b7d31'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Attempts referenced assignments; clear the dependent rows before the tables go.
    op.execute("DELETE FROM feedback_ratings")
    op.execute("DELETE FROM feedback_evaluations")
    op.execute("DELETE FROM evidence_interactions")
    op.execute("DELETE FROM skill_assessments")
    op.execute("DELETE FROM xp_ledger_entries")
    op.execute("DELETE FROM challenge_attempts")

    with op.batch_alter_table('challenge_attempts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('gate_id', sa.String(length=64), nullable=False,
                                      server_default=''))
        batch_op.add_column(sa.Column('block_id', sa.String(length=8), nullable=False,
                                      server_default=''))
        batch_op.add_column(sa.Column('attempt_index', sa.Integer(), nullable=False,
                                      server_default='1'))
        batch_op.add_column(sa.Column('passed', sa.Boolean(), nullable=True))
        batch_op.drop_constraint('uq_attempt_assignment', type_='unique')
        batch_op.drop_column('assignment_id')
        batch_op.create_index('ix_challenge_attempts_gate_id', ['gate_id'])
        batch_op.create_index('ix_challenge_attempts_block_id', ['block_id'])

    op.drop_table('assessment_responses')
    op.drop_table('learning_path_assignments')
    op.drop_table('scenarios')

    op.create_table(
        'lesson_progress',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('lesson_id', sa.String(length=64), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'lesson_id', name='uq_lesson_progress'),
    )
    op.create_index('ix_lesson_progress_user_id', 'lesson_progress', ['user_id'])

    op.create_table(
        'block_progress',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('block_id', sa.String(length=8), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('unlocked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('passed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'block_id', name='uq_block_progress'),
    )
    op.create_index('ix_block_progress_user_id', 'block_progress', ['user_id'])

    # XP is keyed by what it was awarded for, so a re-read lesson or a re-passed block
    # awards nothing (spec v0.2 §9).
    with op.batch_alter_table('xp_ledger_entries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ref_id', sa.String(length=64), nullable=False,
                                      server_default=''))
        batch_op.drop_constraint('uq_xp_attempt_reason', type_='unique')
        batch_op.create_unique_constraint(
            'uq_xp_user_reason_ref', ['user_id', 'reason', 'ref_id']
        )

    with op.batch_alter_table('user_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('target_role', sa.String(length=48), nullable=True))
        batch_op.drop_column('goal')
        batch_op.drop_column('starting_level')
        batch_op.alter_column('language', server_default='ru')

    # Six abstract skills become the six domains of the map plus communication.
    op.execute("DELETE FROM skill_scores")
    op.execute("UPDATE user_profiles SET focus_skills = '[]', current_level = NULL")
    op.execute("UPDATE users SET onboarding_status = 'complete' "
               "WHERE onboarding_status IN ('goal_set', 'assessed')")


def downgrade() -> None:
    raise NotImplementedError(
        "v0.2 restructures learner progress; restore from a backup instead."
    )
