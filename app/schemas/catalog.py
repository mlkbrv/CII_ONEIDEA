"""
Schemas for the catalog submission API — the surface an outside contributor
(or another model) uses to add clothing without a shell or an admin session.

Deliberately different from app/schemas/clothing_admin.py in two ways:

  slot, not category_id   A contributor knows "this is a hat". They should not
                          have to look up that hats are category 2, and a
                          wrong number there silently puts a hat on someone's
                          feet. The slot is the real constraint; the category
                          is resolved from it server-side.

  svg, not image_url      An image_url assumes the file already exists
                          somewhere, which is exactly the thing a caller with
                          only HTTP cannot arrange. The drawing travels in the
                          body.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import AvatarSlot, ClothingAvailability


class CatalogAnchor(BaseModel):
    """The rectangle a slot's art should stay inside, on the shared canvas."""

    x: int
    y: int
    width: int
    height: int


class CatalogSlotSpec(BaseModel):
    slot: AvatarSlot
    category_id: int
    category_name: str
    anchor: CatalogAnchor
    thumb_view_box: str
    layer_order: int = Field(description="Painting order, back to front")
    item_count: int


class CatalogSpec(BaseModel):
    """Everything needed to draw a correct item, as data rather than prose.

    Served so a contributor can read the real numbers out of the running
    system instead of a document that drifted from it.
    """

    canvas_view_box: str
    max_svg_bytes: int
    palette: dict[str, str]
    slots: list[CatalogSlotSpec]
    price_guidance: dict[str, int]
    rules: list[str]


class CatalogItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: uuid.UUID
    name: str
    description: str | None = None
    slot: AvatarSlot
    category_name: str
    price: int
    image_url: str
    thumb_url: str
    availability_status: ClothingAvailability
    created_at: datetime


class CatalogItemList(BaseModel):
    items: list[CatalogItemRead]
    total: int


class CatalogItemCreate(BaseModel):
    name: str = Field(max_length=255, description="Display name, shown in the shop")
    slot: AvatarSlot = Field(description="Which part of the avatar this replaces")
    price: int = Field(ge=0, le=100000, description="Price in coins")
    svg: str = Field(description='Full SVG source, root viewBox="0 0 512 768"')
    description: str | None = Field(default=None, max_length=1000)
    availability_status: ClothingAvailability = ClothingAvailability.AVAILABLE

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class CatalogItemUpdate(BaseModel):
    """Every field optional. Sending `svg` redraws the item in place, keeping
    its id — so an item somebody already bought can be fixed without taking it
    out of their wardrobe."""

    name: str | None = Field(default=None, max_length=255)
    price: int | None = Field(default=None, ge=0, le=100000)
    svg: str | None = None
    description: str | None = Field(default=None, max_length=1000)
    availability_status: ClothingAvailability | None = None
