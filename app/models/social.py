from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserFollow(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "user_follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "followee_id", name="uq_user_follows_pair"),
        CheckConstraint("follower_id != followee_id", name="ck_user_follows_not_self"),
        Index("ix_user_follows_followee_id", "followee_id"),
    )

    follower_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    followee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    follower: Mapped[User] = relationship(
        back_populates="following",
        foreign_keys=[follower_id],
    )
    followee: Mapped[User] = relationship(
        back_populates="followers",
        foreign_keys=[followee_id],
    )
