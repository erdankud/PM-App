"""English is the default interface and content language

`9c1f4a2b7d31` created the column with `en`; `b7d2e4915c08` flipped the default to
`ru` when the authored corpus became Russian. Those are two different questions:
the corpus is authored in Russian, but the product's own language is English —
Practice is conducted in English at any UI language, and the map, the lessons and
the interface all ship with an English overlay.

The back-fill matters as much as the default. Rows holding `ru` today were not
choices: no client sends a language at signup, so every profile ever created took
whatever the column handed it. There is no flag separating those from a deliberate
pick in Profile, so this resets both — a one-time flip a learner undoes with one
control on a screen they already know.

Revision ID: e2c7a4f81b60
Revises: d5f18c3a90b2
Create Date: 2026-09-09 00:00:00.000000
"""
from __future__ import annotations

from alembic import op


revision = "e2c7a4f81b60"
down_revision = "d5f18c3a90b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_profiles", schema=None) as batch_op:
        batch_op.alter_column("language", server_default="en")
    op.execute("UPDATE user_profiles SET language = 'en' WHERE language = 'ru'")


def downgrade() -> None:
    # Только умолчание: какой язык выбрал человек после апгрейда, мы не знаем,
    # и перекрашивать его строки обратно в русский было бы второй порчей данных.
    with op.batch_alter_table("user_profiles", schema=None) as batch_op:
        batch_op.alter_column("language", server_default="ru")
