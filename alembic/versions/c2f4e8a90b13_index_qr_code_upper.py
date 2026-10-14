"""index upper(qr_codes.code) for case-insensitive redemption

Revision ID: c2f4e8a90b13
Revises: b1a7c0de5f01
Create Date: 2026-09-07

POST /qr/redeem matches on upper(code) so a code typed off a bottle cap in
lowercase, or with stray spaces, still redeems. A plain btree index on `code`
cannot serve that predicate — Postgres would sequentially scan every code
printed for the fest on each attempt, while holding a row lock. This
functional index makes it a lookup again.

The original UNIQUE index on `code` stays: it is what guarantees a code is
printed once. This one is a non-unique read path, deliberately, because
uniqueness under case folding is a property of how codes are generated
(A-Z0-9, one case), not something to start enforcing retroactively on
whatever is already in the table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2f4e8a90b13"
down_revision: Union[str, Sequence[str], None] = "b1a7c0de5f01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_qr_codes_code_upper",
        "qr_codes",
        [sa.text("upper(code)")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_qr_codes_code_upper", table_name="qr_codes")
