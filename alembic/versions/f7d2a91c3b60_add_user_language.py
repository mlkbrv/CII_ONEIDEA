"""add users.language

Revision ID: f7d2a91c3b60
Revises: e5c81d2f6a94
Create Date: 2026-09-08

The Mini App can pick its own language from what Telegram tells the client,
but the bot cannot: it composes "your battle ends in 10 minutes" from a
sweeper thread, hours after the player last opened anything. The only thing
available at that moment is the recipient's row, so the language has to live
there.

Default 'ru' rather than NULL: every existing account predates this column and
was being written to in Russian already, so 'ru' describes them accurately.
It also keeps the column NOT NULL, which means no caller has to decide what a
missing language means.

Two characters, not five: regional variants are normalised away on the way in
(app/services/i18n.py), because "az-AZ" and "az" get identical text and
storing both would invite code that compares them.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7d2a91c3b60"
down_revision: Union[str, Sequence[str], None] = "e5c81d2f6a94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "language",
            sa.String(length=2),
            nullable=False,
            server_default=sa.text("'ru'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "language")
