from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ClothingSlot, str_enum
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ClothingCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clothing_categories"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    slot: Mapped[ClothingSlot] = mapped_column(str_enum(ClothingSlot), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))

    items: Mapped[list[ClothingItem]] = relationship(back_populates="category")


class ClothingItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clothing_items"

    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clothing_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    price_coins: Mapped[int] = mapped_column(Integer, nullable=False)
    asset_key: Mapped[str] = mapped_column(String(256), nullable=False)
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    category: Mapped[ClothingCategory] = relationship(back_populates="items")
    wardrobe_items: Mapped[list[WardrobeItem]] = relationship(back_populates="clothing_item")
    equipped_items: Mapped[list[EquippedItem]] = relationship(back_populates="clothing_item")


class WardrobeItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "wardrobe_items"
    __table_args__ = (
        UniqueConstraint("user_id", "clothing_item_id", name="uq_wardrobe_items_user_item"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clothing_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clothing_items.id", ondelete="RESTRICT"), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="wardrobe_items")
    clothing_item: Mapped[ClothingItem] = relationship(back_populates="wardrobe_items")


class EquippedItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "equipped_items"
    __table_args__ = (
        UniqueConstraint("user_id", "slot", name="uq_equipped_items_user_slot"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slot: Mapped[ClothingSlot] = mapped_column(str_enum(ClothingSlot), nullable=False)
    clothing_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clothing_items.id", ondelete="RESTRICT"), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="equipped_items")
    clothing_item: Mapped[ClothingItem] = relationship(back_populates="equipped_items")
