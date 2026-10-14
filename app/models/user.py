"""
users — core identity record. Design doc section 2.1.

IMPORTANT: coin_balance is a CACHE, not a source of truth. Once the
coin_transactions ledger exists (a later batch), nothing should ever
write to coin_balance directly except the transaction service layer
that also inserts the corresponding ledger row in the same DB
transaction. Treat it as read-only from anywhere else in the codebase.

"Profile" fields (username, bio, profile picture, etc.) live directly
on this table by design — see the discussion in chat: a separate
`profiles` table isn't warranted unless the field count explodes or
auth data needs access-control separation from profile data. Neither
applies here.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, String, text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .auth_provider import AuthProvider
    from .avatar import Avatar
    from .coin_transaction import CoinTransaction
    from .competition import Competition
    from .competition_request import CompetitionRequest
    from .device_token import DeviceToken
    from .follow import Follow
    from .notification import Notification
    from .qr_code import QRCode
    from .user_wardrobe import UserWardrobe
    from .vote import Vote


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("coin_balance >= 0", name="ck_users_coin_balance_non_negative"),
        CheckConstraint("winning_streak >= 0", name="ck_users_winning_streak_non_negative"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    # CITEXT requires `CREATE EXTENSION IF NOT EXISTS citext;` — see design
    # doc section 2.1 for why (case-insensitive uniqueness on username/email).
    username: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False, index=True)

    # Nullable since the Telegram MVP: an account created from a Mini App
    # session has no email address to record. Still UNIQUE — Postgres does
    # not consider two NULLs equal, so any number of Telegram-only accounts
    # coexist while real addresses stay unique.
    email: Mapped[str | None] = mapped_column(
        CITEXT(), unique=True, nullable=True, index=True
    )

    # Nullable because OAuth-only accounts (future Google/Apple login) and
    # Telegram accounts have no local password.
    password_hash: Mapped[str | None] = mapped_column(nullable=True)

    # --- Telegram identity ------------------------------------------------
    # Denormalised from auth_providers on purpose: every Mini App request
    # that is not carrying a JWT resolves the account by telegram_id, so it
    # is the hottest lookup in the system and deserves its own index rather
    # than a join. The auth_providers row is still written, so the generic
    # "which providers is this account linked to" question keeps one answer.
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, nullable=True, index=True
    )
    # Telegram's own @handle. Kept separate from `username` because ours is
    # editable by the user and must stay unique in CITEXT, while Telegram's
    # can change under us at any time and is only used for display.
    telegram_username: Mapped[str | None] = mapped_column(nullable=True)
    first_name: Mapped[str | None] = mapped_column(nullable=True)
    last_name: Mapped[str | None] = mapped_column(nullable=True)

    # Which language this account reads. Seeded from Telegram on first
    # contact and changeable in the app afterwards; the bot needs it because
    # it composes messages server-side, long after any request context is
    # gone. Two letters, lowercase — see app/services/i18n.py.
    language: Mapped[str] = mapped_column(
        String(2), nullable=False, server_default=text("'ru'")
    )

    profile_picture_url: Mapped[str | None] = mapped_column(nullable=True)
    biography: Mapped[str | None] = mapped_column(nullable=True)

    coin_balance: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    winning_streak: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))

    # Soft delete flag — see design doc section 5 on why users are
    # deactivated, not hard-deleted (the coin ledger and competition
    # history both depend on the user row still existing).
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    # TZ section 8: other users may view your wardrobe "if you allow it".
    # Default open — the wardrobe is a showcase and hiding it is the
    # deliberate choice, not the other way round.
    wardrobe_public: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )

    # Administration flag. True only for internal operators; gates every
    # /admin/* endpoint through get_current_admin(). Promoted via SQL
    # (UPDATE users SET is_admin = true WHERE ...) — never by the app, so
    # there is no endpoint a normal user could call to self-promote.
    is_admin: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))

    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), onupdate=text("now()"), nullable=False
    )

    # Relationships populated as later batches add the referencing tables
    # (avatars, wardrobe, competitions, etc. aren't declared yet).
    auth_providers: Mapped[list["AuthProvider"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    device_tokens: Mapped[list["DeviceToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    avatar: Mapped["Avatar | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    wardrobe: Mapped[list["UserWardrobe"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    qr_codes_redeemed: Mapped[list["QRCode"]] = relationship(back_populates="redeemed_by")
    coin_transactions: Mapped[list["CoinTransaction"]] = relationship(back_populates="user")

    sent_competition_requests: Mapped[list["CompetitionRequest"]] = relationship(
        foreign_keys="CompetitionRequest.challenger_id", back_populates="challenger"
    )
    received_competition_requests: Mapped[list["CompetitionRequest"]] = relationship(
        foreign_keys="CompetitionRequest.opponent_id", back_populates="opponent"
    )
    competitions_as_challenger: Mapped[list["Competition"]] = relationship(
        foreign_keys="Competition.challenger_id", back_populates="challenger"
    )
    competitions_as_opponent: Mapped[list["Competition"]] = relationship(
        foreign_keys="Competition.opponent_id", back_populates="opponent"
    )
    competitions_won: Mapped[list["Competition"]] = relationship(
        foreign_keys="Competition.winner_id", back_populates="winner"
    )
    votes_cast: Mapped[list["Vote"]] = relationship(
        foreign_keys="Vote.voter_id", back_populates="voter"
    )
    votes_received: Mapped[list["Vote"]] = relationship(
        foreign_keys="Vote.voted_for_user_id", back_populates="voted_for"
    )
    notifications_received: Mapped[list["Notification"]] = relationship(
        foreign_keys="Notification.user_id", back_populates="user", cascade="all, delete-orphan"
    )
    notifications_triggered: Mapped[list["Notification"]] = relationship(
        foreign_keys="Notification.actor_user_id", back_populates="actor"
    )

    # Self-referential through Follow — two distinct relationships
    # because a user shows up in both the follower_id and followee_id
    # columns across different rows.
    following: Mapped[list["Follow"]] = relationship(
        foreign_keys="Follow.follower_id", back_populates="follower", cascade="all, delete-orphan"
    )
    followers: Mapped[list["Follow"]] = relationship(
        foreign_keys="Follow.followee_id", back_populates="followee", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"