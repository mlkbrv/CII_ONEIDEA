"""notification delivery + the types the battle flow needs

Revision ID: d3b6f1c47a28
Revises: c2f4e8a90b13
Create Date: 2026-09-07

Three things, all in service of TZ section 16 (the bot is the notification
channel, and battles are time-boxed so a late notification is a useless one).

1. notifications.delivered_at — the API writes a notification row inside the
   same transaction as the thing that caused it, and a separate worker sends
   it to Telegram. This column is what makes that handoff durable: an
   undelivered row survives a worker restart and gets sent late rather than
   never. Sending from inside the request instead would mean either holding
   an HTTP transaction open across a call to Telegram's API, or losing the
   notification whenever that call fails.

   Indexed on (delivered_at, created_at) WHERE delivered_at IS NULL: the
   worker's only query is "oldest undelivered", and a partial index over
   just those rows stays small forever while the table grows.

2. Three notification types the seeded set is missing. competition_declined
   and competition_ending_soon are both explicitly in the TZ; competition_draw
   exists because the completion service already treats an exact tie as a
   distinct outcome, and telling both players they "lost" would be wrong.

3. competitions.reminder_sent_at — the "ending soon" reminder must go out
   exactly once per battle. Storing when it was sent makes the worker's sweep
   a plain WHERE clause and makes double-sending impossible even if two
   workers ever run at once.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d3b6f1c47a28"
down_revision: Union[str, Sequence[str], None] = "c2f4e8a90b13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_TYPES = [
    "competition_declined",
    "competition_ending_soon",
    "competition_draw",
]


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_notifications_undelivered",
        "notifications",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("delivered_at IS NULL"),
    )

    op.add_column(
        "competitions",
        sa.Column("reminder_sent_at", sa.DateTime(), nullable=True),
    )

    # ON CONFLICT so re-running against a database that already has them (or a
    # future migration that adds one of them) is not an error.
    for type_name in NEW_TYPES:
        op.execute(
            sa.text(
                "INSERT INTO notification_types (type_name) VALUES (:name) "
                "ON CONFLICT (type_name) DO NOTHING"
            ).bindparams(name=type_name)
        )


def downgrade() -> None:
    for type_name in NEW_TYPES:
        op.execute(
            sa.text(
                "DELETE FROM notifications WHERE type_id IN "
                "(SELECT type_id FROM notification_types WHERE type_name = :name)"
            ).bindparams(name=type_name)
        )
        op.execute(
            sa.text("DELETE FROM notification_types WHERE type_name = :name").bindparams(
                name=type_name
            )
        )

    op.drop_column("competitions", "reminder_sent_at")
    op.drop_index("ix_notifications_undelivered", table_name="notifications")
    op.drop_column("notifications", "delivered_at")
