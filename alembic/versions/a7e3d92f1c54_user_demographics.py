"""add users.gender, users.birth_year, users.demographics_status

Revision ID: a7e3d92f1c54
Revises: a4f6c81de3b7
Create Date: 2026-10-18

Optional, self-reported demographics for the operators' statistics. Telegram
does not tell a Mini App a user's gender or age, so the app asks once and the
player may skip. All three columns are nullable: every existing account simply
has not been asked yet.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7e3d92f1c54"
down_revision: Union[str, Sequence[str], None] = "a4f6c81de3b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gender", sa.String(length=12), nullable=True))
    op.add_column("users", sa.Column("birth_year", sa.SmallInteger(), nullable=True))
    op.add_column("users", sa.Column("demographics_status", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "demographics_status")
    op.drop_column("users", "birth_year")
    op.drop_column("users", "gender")
