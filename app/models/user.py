from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, false, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AuthProviderType, DevicePlatform, str_enum
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.avatar import Avatar
    from app.models.clothing import EquippedItem, WardrobeItem
    from app.models.coin import CoinTransaction
    from app.models.competition import Competition, CompetitionRequest, Vote
    from app.models.notification import Notification
    from app.models.product import ProductCode
    from app.models.promo import PromoCode
    from app.models.social import UserFollow


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    coins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    winning_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    wardrobe_is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    auth_providers: Mapped[list[AuthProvider]] = relationship(back_populates="user")
    device_tokens: Mapped[list[DeviceToken]] = relationship(back_populates="user")
    avatar: Mapped[Avatar | None] = relationship(back_populates="user", uselist=False)
    following: Mapped[list[UserFollow]] = relationship(
        back_populates="follower",
        foreign_keys="UserFollow.follower_id",
    )
    followers: Mapped[list[UserFollow]] = relationship(
        back_populates="followee",
        foreign_keys="UserFollow.followee_id",
    )
    coin_transactions: Mapped[list[CoinTransaction]] = relationship(back_populates="user")
    redeemed_promo_codes: Mapped[list[PromoCode]] = relationship(back_populates="redeemed_by")
    redeemed_product_codes: Mapped[list[ProductCode]] = relationship(back_populates="redeemed_by")
    wardrobe_items: Mapped[list[WardrobeItem]] = relationship(back_populates="user")
    equipped_items: Mapped[list[EquippedItem]] = relationship(back_populates="user")
    competition_requests_sent: Mapped[list[CompetitionRequest]] = relationship(
        back_populates="challenger",
        foreign_keys="CompetitionRequest.challenger_id",
    )
    competition_requests_received: Mapped[list[CompetitionRequest]] = relationship(
        back_populates="opponent",
        foreign_keys="CompetitionRequest.opponent_id",
    )
    competitions_as_challenger: Mapped[list[Competition]] = relationship(
        back_populates="challenger",
        foreign_keys="Competition.challenger_id",
    )
    competitions_as_opponent: Mapped[list[Competition]] = relationship(
        back_populates="opponent",
        foreign_keys="Competition.opponent_id",
    )
    competitions_won: Mapped[list[Competition]] = relationship(
        back_populates="winner",
        foreign_keys="Competition.winner_id",
    )
    votes: Mapped[list[Vote]] = relationship(
        back_populates="voter",
        foreign_keys="Vote.voter_id",
    )
    notifications: Mapped[list[Notification]] = relationship(back_populates="user")


class AuthProvider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "auth_providers"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_auth_providers_provider_user"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[AuthProviderType] = mapped_column(str_enum(AuthProviderType), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(128), nullable=False)

    user: Mapped[User] = relationship(back_populates="auth_providers")


class DeviceToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "device_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    platform: Mapped[DevicePlatform] = mapped_column(str_enum(DevicePlatform), nullable=False)

    user: Mapped[User] = relationship(back_populates="device_tokens")
