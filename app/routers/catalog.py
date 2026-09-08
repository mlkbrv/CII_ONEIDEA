"""
Catalog submission — a way to fill the shop over HTTP alone.

The admin panel already manages clothing, but it assumes a browser, a human
session, and artwork that has already been put on disk somehow. Filling a
catalog is none of those things: it is a hundred small drawings produced by
someone (or something) that can send JSON and nothing else. This router is
that door.

    GET    /catalog/spec              the canvas, slots, anchors, palette, rules
    GET    /catalog/items             what already exists, so nothing is duplicated
    POST   /catalog/items             add one item, artwork included
    PATCH  /catalog/items/{item_id}   fix one, keeping its id
    DELETE /catalog/items/{item_id}   remove one nobody owns yet

## About "open"

Reading is open: the spec and the item list are public anyway (the shop shows
both) and a contributor should be able to look before submitting. Writing
needs `X-Catalog-Key`. That is not bureaucracy — an unauthenticated write
endpoint that stores files and rows is an open invitation to fill the disk
with junk that then renders inside a Telegram app carrying Coca-Cola's name.
One shared key hands the whole capability to whoever needs it in a single line
of configuration, with none of the account/session machinery a contributor
would otherwise have to implement. When no key is configured the write
endpoints report 503 rather than silently accepting anonymous writes.
"""
import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.models import (
    AvatarEquipment,
    AvatarSlot,
    ClothingCategory,
    ClothingItem,
    UserWardrobe,
)
from app.schemas.catalog import (
    CatalogAnchor,
    CatalogItemCreate,
    CatalogItemList,
    CatalogItemRead,
    CatalogItemUpdate,
    CatalogSlotSpec,
    CatalogSpec,
)
from app.services import catalog_art

router = APIRouter(prefix="/catalog", tags=["catalog"])

# Spelled as a number because Starlette renamed its constant
# (HTTP_422_UNPROCESSABLE_ENTITY -> ..._CONTENT) and both spellings warn on
# one version or the other. The status code itself has not changed.
UNPROCESSABLE = 422

# Painting order, back to front. Must match SLOT_ORDER in
# miniapp/src/components/AvatarView.jsx — a garment's layer is decided here
# and drawn there, and the two disagreeing is how a hat ends up behind hair.
LAYER_ORDER = ["bottom", "top", "shoes", "hair", "hat", "accessory"]

PALETTE = {
    "red": "#E4002B",
    "red_deep": "#A5001F",
    "white": "#FFFFFF",
    "fur": "#F4EFE6",
    "fur_shade": "#DCD3C4",
    "ink": "#1A1A1A",
    "gold": "#F2C230",
    "gold_deep": "#E0A81E",
    "denim": "#4A6FA5",
    "denim_deep": "#33527E",
    "slate": "#3C4652",
    "slate_deep": "#2A323C",
    "ice": "#BFE3F2",
    "ice_deep": "#8CC4DC",
    "mint": "#37C2A6",
    "mint_deep": "#28A48C",
    "olive": "#6E7A4F",
    "olive_deep": "#57603D",
}

# One bottle cap is 50 coins, and that single number sets the whole economy:
# a price is really a statement about how many drinks an item costs.
PRICE_GUIDANCE = {
    "coins_per_cap": 50,
    "cheap": 150,
    "mid": 350,
    "expensive": 600,
    "trophy": 900,
}

RULES = [
    'Root element <svg> with viewBox="0 0 512 768" and nothing else on it.',
    "Draw the garment where it belongs on the bear, inside its slot's anchor box. "
    "There is no positioning step later — the file IS the position.",
    "Flat vector: two tones per shape (base plus shadow), no gradients, no outlines, "
    "no filters. The set has to look like one set.",
    "Shapes and paths only. No <script>, <image>, <foreignObject>, no event "
    "attributes, no references to any other address.",
    "Transparent background. The bear is drawn underneath by the app.",
    "Do not submit a thumbnail — it is derived from your drawing, so it can "
    "never disagree with what the avatar wears.",
    "Names are shown untranslated in every language. Keep them short and in English.",
]


def require_key(x_catalog_key: str = Header(default="")) -> None:
    """Guard the write endpoints with one shared key."""
    if not settings.catalog_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catalog submission is disabled: CATALOG_API_KEY is not set on the server.",
        )
    # compare_digest rather than ==, so a wrong key cannot be discovered one
    # character at a time by timing the responses.
    if not secrets.compare_digest(x_catalog_key, settings.catalog_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-Catalog-Key header.",
        )


@router.get("/spec", response_model=CatalogSpec)
def get_spec(db: Session = Depends(get_db)) -> CatalogSpec:
    """Everything needed to draw a correct item, read from the live system."""
    categories = db.execute(
        select(ClothingCategory).order_by(ClothingCategory.category_id)
    ).scalars().all()

    counts: dict[int, int] = {
        category_id: total
        for category_id, total in db.execute(
            select(ClothingItem.category_id, func.count(ClothingItem.item_id)).group_by(
                ClothingItem.category_id
            )
        ).all()
    }

    slots = [
        CatalogSlotSpec(
            slot=category.slot,
            category_id=category.category_id,
            category_name=category.category_name,
            anchor=CatalogAnchor(**catalog_art.ANCHORS[category.slot.value]),
            thumb_view_box=catalog_art.THUMB_VIEW_BOX[category.slot.value],
            layer_order=LAYER_ORDER.index(category.slot.value),
            item_count=counts.get(category.category_id, 0),
        )
        for category in categories
        if category.slot.value in catalog_art.ANCHORS
    ]

    return CatalogSpec(
        canvas_view_box=catalog_art.CANVAS,
        max_svg_bytes=catalog_art.MAX_SVG_BYTES,
        palette=PALETTE,
        slots=slots,
        price_guidance=PRICE_GUIDANCE,
        rules=RULES,
    )


@router.get("/items", response_model=CatalogItemList)
def list_items(
    slot: AvatarSlot | None = Query(default=None),
    db: Session = Depends(get_db),
) -> CatalogItemList:
    """The whole catalog, so a contributor can see what is already drawn."""
    query = select(ClothingItem).options(joinedload(ClothingItem.category))
    if slot is not None:
        query = query.join(ClothingCategory).where(ClothingCategory.slot == slot)

    rows = db.execute(
        query.order_by(ClothingItem.created_at.desc(), ClothingItem.item_id.desc())
    ).scalars().all()

    return CatalogItemList(items=[_to_read(item) for item in rows], total=len(rows))


@router.post(
    "/items",
    response_model=CatalogItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_key)],
)
def create_item(
    payload: CatalogItemCreate, db: Session = Depends(get_db)
) -> CatalogItemRead:
    category = _category_for_slot(db, payload.slot)
    svg = _validated(payload.svg)

    name = payload.name.strip()
    if _name_taken(db, name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'An item named "{name}" already exists. Pick another name, '
            "or PATCH the existing one.",
        )

    slug = _free_slug(db, payload.slot.value, catalog_art.slugify(name))
    image_url = catalog_art.write(payload.slot.value, slug, svg)

    item = ClothingItem(
        name=name,
        description=payload.description.strip() if payload.description else None,
        category_id=category.category_id,
        price=payload.price,
        image_url=image_url,
        availability_status=payload.availability_status,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_read(item)


@router.patch(
    "/items/{item_id}",
    response_model=CatalogItemRead,
    dependencies=[Depends(require_key)],
)
def update_item(
    item_id: uuid.UUID, payload: CatalogItemUpdate, db: Session = Depends(get_db)
) -> CatalogItemRead:
    item = _get_item(db, item_id)
    updates = payload.model_dump(exclude_unset=True)

    if "svg" in updates and updates["svg"] is not None:
        svg = _validated(updates.pop("svg"))
        slot = item.category.slot.value
        # Rewritten under the item's EXISTING slug, so the URL does not change
        # and every wardrobe already holding this item picks up the new art.
        slug = _slug_of(item.image_url) or catalog_art.slugify(item.name)
        item.image_url = catalog_art.write(slot, slug, svg)
    else:
        updates.pop("svg", None)

    if "name" in updates:
        name = (updates["name"] or "").strip()
        if not name:
            raise HTTPException(
                status_code=UNPROCESSABLE,
                detail="name must not be empty",
            )
        if _name_taken(db, name, exclude=item.item_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'An item named "{name}" already exists.',
            )
        updates["name"] = name

    for field, value in updates.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return _to_read(item)


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_key)],
)
def delete_item(item_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    item = _get_item(db, item_id)

    owned = db.execute(
        select(func.count(UserWardrobe.wardrobe_id)).where(UserWardrobe.item_id == item_id)
    ).scalar_one()
    worn = db.execute(
        select(func.count(AvatarEquipment.avatar_id)).where(AvatarEquipment.item_id == item_id)
    ).scalar_one()

    if owned or worn:
        # Someone paid coins for this. Taking it out of their wardrobe is a
        # worse outcome than leaving a bad item in the catalog unbought.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Players already own or wear this item. PATCH it to "
            'availability_status="unavailable" instead of deleting it.',
        )

    image_url = item.image_url
    db.delete(item)
    db.commit()
    catalog_art.remove(image_url)


def _validated(svg: str) -> str:
    try:
        return catalog_art.validate(svg)
    except catalog_art.ArtError as exc:
        # 422, not 400: the body parsed fine, the drawing inside it is what
        # needs fixing, and the message says exactly what.
        raise HTTPException(
            status_code=UNPROCESSABLE, detail=str(exc)
        ) from exc


def _category_for_slot(db: Session, slot: AvatarSlot) -> ClothingCategory:
    category = db.execute(
        select(ClothingCategory).where(ClothingCategory.slot == slot).order_by(
            ClothingCategory.category_id
        )
    ).scalars().first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No clothing category exists for slot {slot.value}.",
        )
    return category


def _name_taken(db: Session, name: str, exclude: uuid.UUID | None = None) -> bool:
    query = select(ClothingItem.item_id).where(func.lower(ClothingItem.name) == name.lower())
    if exclude is not None:
        query = query.where(ClothingItem.item_id != exclude)
    return db.execute(query).first() is not None


def _free_slug(db: Session, slot: str, slug: str) -> str:
    """A slug no existing item's image_url already uses.

    Names are unique, but slugs are lossy — "Fest Tee" and "Fest-Tee" fold
    together — so uniqueness is checked where it actually matters: the file.
    """
    taken = {
        _slug_of(url)
        for (url,) in db.execute(
            select(ClothingItem.image_url).where(
                ClothingItem.image_url.like(f"{catalog_art.UPLOAD_URL_PREFIX}/{slot}/%")
            )
        ).all()
    }
    if slug not in taken:
        return slug
    suffix = 2
    while f"{slug}-{suffix}" in taken:
        suffix += 1
    return f"{slug}-{suffix}"


def _slug_of(image_url: str) -> str | None:
    if not image_url.endswith(".svg"):
        return None
    return image_url.rsplit("/", 1)[-1][: -len(".svg")]


def _get_item(db: Session, item_id: uuid.UUID) -> ClothingItem:
    item = db.execute(
        select(ClothingItem)
        .options(joinedload(ClothingItem.category))
        .where(ClothingItem.item_id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Clothing item not found"
        )
    return item


def _to_read(item: ClothingItem) -> CatalogItemRead:
    return CatalogItemRead(
        item_id=item.item_id,
        name=item.name,
        description=item.description,
        slot=item.category.slot,
        category_name=item.category.category_name,
        price=item.price,
        image_url=item.image_url,
        # The convention the Mini App already uses (ItemThumb in
        # AvatarView.jsx), spelled out here so a contributor can check their
        # crop without reading the frontend.
        thumb_url=item.image_url.replace(".svg", ".thumb.svg"),
        availability_status=item.availability_status,
        created_at=item.created_at,
    )
