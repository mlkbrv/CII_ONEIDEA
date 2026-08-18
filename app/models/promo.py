from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class PromoCode(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "promo_codes"
    __table_args__ = (
        CheckConstraint("coin_reward > 0", name="ck_promo_codes_coin_reward_positive"),
        CheckConstraint(
            "(is_redeemed = false AND redeemed_by_user_id IS NULL AND redeemed_at IS NULL) OR "
            "(is_redeemed = true AND redeemed_by_user_id IS NOT NULL AND redeemed_at IS NOT NULL)",
            name="ck_promo_codes_redeem_state",
        ),
    )

    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    coin_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    is_redeemed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    redeemed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    redeemed_by: Mapped[User | None] = relationship(back_populates="redeemed_promo_codes")
