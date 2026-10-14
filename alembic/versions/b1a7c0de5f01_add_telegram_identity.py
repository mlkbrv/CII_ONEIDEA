"""add telegram identity

Revision ID: b1a7c0de5f01
Revises: 5a59fd52b390
Create Date: 2026-09-07

Makes the schema able to hold an account that exists only inside Telegram.

The load-bearing change is `users.email` becoming nullable. A Mini App
session gives us a Telegram id, a first name and maybe an @handle — never
an email address — so with a NOT NULL email there is no way to create the
account at all. UNIQUE stays: Postgres does not treat two NULLs as equal,
so any number of Telegram-only accounts coexist while real addresses
remain unique.

`telegram_id` is BIGINT, not INTEGER: Telegram ids already exceed 2^31 and
Telegram's own docs allow up to 52 significant bits.

Adding TELEGRAM to the auth_provider_type enum is safe inside this
transaction because the value is only declared here, never used — writing
a row with it happens in a later transaction (PostgreSQL 12+ rule).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1a7c0de5f01"
down_revision: Union[str, Sequence[str], None] = "5a59fd52b390"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(), nullable=True)

    op.add_column("users", sa.Column("telegram_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("telegram_username", sa.String(), nullable=True))
    op.add_column("users", sa.Column("first_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(), nullable=True))
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.add_column(
        "users",
        sa.Column(
            "wardrobe_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    op.execute("ALTER TYPE auth_provider_type ADD VALUE IF NOT EXISTS 'TELEGRAM'")


def downgrade() -> None:
    # Rolling back only works while no account depends on the new columns:
    # a Telegram-only user has no email, so restoring NOT NULL would fail.
    # Delete those accounts first if you really need to go back.
    op.execute("DELETE FROM auth_providers WHERE provider = 'TELEGRAM'")

    op.drop_column("users", "wardrobe_public")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
    op.drop_column("users", "telegram_username")
    op.drop_column("users", "telegram_id")

    op.alter_column("users", "email", existing_type=sa.String(), nullable=False)

    # PostgreSQL cannot drop a single enum label, so the type is rebuilt
    # without TELEGRAM and the column is re-pointed at it.
    op.execute("ALTER TYPE auth_provider_type RENAME TO auth_provider_type_old")
    op.execute("CREATE TYPE auth_provider_type AS ENUM ('LOCAL', 'GOOGLE', 'APPLE')")
    op.execute(
        "ALTER TABLE auth_providers ALTER COLUMN provider "
        "TYPE auth_provider_type USING provider::text::auth_provider_type"
    )
    op.execute("DROP TYPE auth_provider_type_old")
