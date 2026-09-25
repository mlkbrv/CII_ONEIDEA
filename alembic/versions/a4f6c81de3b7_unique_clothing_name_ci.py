"""unique index on lower(clothing_items.name)

Revision ID: a4f6c81de3b7
Revises: f7d2a91c3b60
Create Date: 2026-09-25

POST /catalog/items checks name uniqueness with an application-level SELECT
(_name_taken() in app/routers/catalog.py) before writing artwork and
inserting the row. That check is not a lock: two concurrent submissions with
the same name can both run it before either has committed, both pass, and
both insert — landing two ClothingItem rows with the same name, one of them
pointing at art the other one's file write just clobbered.

Every other unique-by-application-rule column in this schema already backs
its check with a real constraint (qr_codes.code, users.username /
CITEXT, the votes and user_wardrobe composite uniques) — the application
check is there to fail fast and readably, the database is what actually
decides. This index closes that gap for clothing_items.name.

Functional, on lower(name), to match _name_taken()'s
`func.lower(ClothingItem.name) == name.lower()` exactly — a plain unique
index on `name` would allow "Fest Tee" and "fest tee" to coexist, which the
application already treats as the same name.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4f6c81de3b7"
down_revision: Union[str, Sequence[str], None] = "f7d2a91c3b60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ux_clothing_items_name_ci",
        "clothing_items",
        [sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_clothing_items_name_ci", table_name="clothing_items")
