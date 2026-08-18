"""create initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-08-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("coins", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("winning_streak", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("wardrobe_is_public", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "auth_providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_user_id", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_auth_providers_provider_user"),
    )
    op.create_index("ix_auth_providers_user_id", "auth_providers", ["user_id"])

    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_device_tokens_user_id", "device_tokens", ["user_id"])

    op.create_table(
        "avatars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "user_follows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("follower_id", sa.Uuid(), nullable=False),
        sa.Column("followee_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("follower_id != followee_id", name="ck_user_follows_not_self"),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["followee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("follower_id", "followee_id", name="uq_user_follows_pair"),
    )
    op.create_index("ix_user_follows_followee_id", "user_follows", ["followee_id"])

    op.create_table(
        "clothing_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("slot", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "clothing_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("price_coins", sa.Integer(), nullable=False),
        sa.Column("asset_key", sa.String(length=256), nullable=False),
        sa.Column("is_available", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["clothing_categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_clothing_items_category_id", "clothing_items", ["category_id"])

    op.create_table(
        "wardrobe_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("clothing_item_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clothing_item_id"], ["clothing_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "clothing_item_id", name="uq_wardrobe_items_user_item"),
    )
    op.create_index("ix_wardrobe_items_user_id", "wardrobe_items", ["user_id"])

    op.create_table(
        "equipped_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("slot", sa.String(length=32), nullable=False),
        sa.Column("clothing_item_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clothing_item_id"], ["clothing_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "slot", name="uq_equipped_items_user_slot"),
    )
    op.create_index("ix_equipped_items_user_id", "equipped_items", ["user_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=False),
        sa.Column("coin_reward", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barcode"),
    )

    op.create_table(
        "product_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("is_redeemed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("redeemed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(is_redeemed = false AND redeemed_by_user_id IS NULL AND redeemed_at IS NULL) OR "
            "(is_redeemed = true AND redeemed_by_user_id IS NOT NULL AND redeemed_at IS NOT NULL)",
            name="ck_product_codes_redeem_state",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["redeemed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_product_codes_product_id", "product_codes", ["product_id"])
    op.create_index("ix_product_codes_redeemed_by_user_id", "product_codes", ["redeemed_by_user_id"])

    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("coin_reward", sa.Integer(), nullable=False),
        sa.Column("is_redeemed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("redeemed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("coin_reward > 0", name="ck_promo_codes_coin_reward_positive"),
        sa.CheckConstraint(
            "(is_redeemed = false AND redeemed_by_user_id IS NULL AND redeemed_at IS NULL) OR "
            "(is_redeemed = true AND redeemed_by_user_id IS NOT NULL AND redeemed_at IS NOT NULL)",
            name="ck_promo_codes_redeem_state",
        ),
        sa.ForeignKeyConstraint(["redeemed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_promo_codes_redeemed_by_user_id", "promo_codes", ["redeemed_by_user_id"])

    op.create_table(
        "coin_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(length=32), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coin_transactions_user_created", "coin_transactions", ["user_id", "created_at"])

    op.create_table(
        "competition_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("challenger_id", sa.Uuid(), nullable=False),
        sa.Column("opponent_id", sa.Uuid(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("challenger_id != opponent_id", name="ck_competition_requests_not_self"),
        sa.ForeignKeyConstraint(["challenger_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["opponent_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_competition_requests_challenger_id", "competition_requests", ["challenger_id"])
    op.create_index("ix_competition_requests_opponent_id", "competition_requests", ["opponent_id"])

    op.create_table(
        "competitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("challenger_id", sa.Uuid(), nullable=False),
        sa.Column("opponent_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("prize_pool", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_votes", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("winner_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("challenger_id != opponent_id", name="ck_competitions_not_self"),
        sa.ForeignKeyConstraint(["request_id"], ["competition_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["challenger_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["opponent_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["winner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_competitions_challenger_id", "competitions", ["challenger_id"])
    op.create_index("ix_competitions_opponent_id", "competitions", ["opponent_id"])
    op.create_index(
        "uq_competitions_active_challenger",
        "competitions",
        ["challenger_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "uq_competitions_active_opponent",
        "competitions",
        ["opponent_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "votes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("competition_id", sa.Uuid(), nullable=False),
        sa.Column("voter_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voter_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["participant_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_votes_competition_id", "votes", ["competition_id"])
    op.create_index("ix_votes_voter_id", "votes", ["voter_id"])
    op.create_index("ix_votes_competition_participant", "votes", ["competition_id", "participant_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_votes_competition_participant", table_name="votes")
    op.drop_index("ix_votes_voter_id", table_name="votes")
    op.drop_index("ix_votes_competition_id", table_name="votes")
    op.drop_table("votes")
    op.drop_index("uq_competitions_active_opponent", table_name="competitions")
    op.drop_index("uq_competitions_active_challenger", table_name="competitions")
    op.drop_index("ix_competitions_opponent_id", table_name="competitions")
    op.drop_index("ix_competitions_challenger_id", table_name="competitions")
    op.drop_table("competitions")
    op.drop_index("ix_competition_requests_opponent_id", table_name="competition_requests")
    op.drop_index("ix_competition_requests_challenger_id", table_name="competition_requests")
    op.drop_table("competition_requests")
    op.drop_index("ix_coin_transactions_user_created", table_name="coin_transactions")
    op.drop_table("coin_transactions")
    op.drop_index("ix_promo_codes_redeemed_by_user_id", table_name="promo_codes")
    op.drop_table("promo_codes")
    op.drop_index("ix_product_codes_redeemed_by_user_id", table_name="product_codes")
    op.drop_index("ix_product_codes_product_id", table_name="product_codes")
    op.drop_table("product_codes")
    op.drop_table("products")
    op.drop_index("ix_equipped_items_user_id", table_name="equipped_items")
    op.drop_table("equipped_items")
    op.drop_index("ix_wardrobe_items_user_id", table_name="wardrobe_items")
    op.drop_table("wardrobe_items")
    op.drop_index("ix_clothing_items_category_id", table_name="clothing_items")
    op.drop_table("clothing_items")
    op.drop_table("clothing_categories")
    op.drop_index("ix_user_follows_followee_id", table_name="user_follows")
    op.drop_table("user_follows")
    op.drop_table("avatars")
    op.drop_index("ix_device_tokens_user_id", table_name="device_tokens")
    op.drop_table("device_tokens")
    op.drop_index("ix_auth_providers_user_id", table_name="auth_providers")
    op.drop_table("auth_providers")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
