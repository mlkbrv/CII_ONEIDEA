"""
Reading a user's public face: avatar, wardrobe, follower counts.

These queries were written once for "me" (GET /avatar, GET /wardrobe) and are
now needed for "them" as well (TZ section 8: open someone's profile, see their
outfit, and their wardrobe if they allow it). Rather than copy them into the
users router with the owner filter swapped, the shared shape lives here and
both callers pass in whose id they mean.

Everything in this module takes a user_id as an argument, so the CALLER decides
whose data is being read — the endpoints that serve "me" keep passing
current_user.user_id and remain incapable of reading anyone else.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Avatar,
    AvatarEquipment,
    ClothingItem,
    Competition,
    CompetitionStatus,
    Follow,
    UserWardrobe,
)
from app.schemas.avatar import AvatarEquipmentMap, AvatarRead, AvatarSlotEquipment
from app.schemas.clothing import ClothingCategoryRef, ClothingItemRead
from app.schemas.wardrobe import WardrobeEntryRead, WardrobeList


def load_avatar(db: Session, user_id: uuid.UUID) -> AvatarRead | None:
    """The avatar of `user_id` with its full equipment state, or None."""
    avatar = db.execute(
        select(Avatar)
        .where(Avatar.user_id == user_id)
        .options(
            joinedload(Avatar.equipment)
            .joinedload(AvatarEquipment.item)
            .joinedload(ClothingItem.category)
        )
    ).unique().scalar_one_or_none()
    if avatar is None:
        return None

    # Fold the equipment rows into the slot-keyed map. Empty slots keep their
    # schema default (None); an item-less equipment row (possible at the schema
    # level, never written by the equip flow) counts as empty too.
    occupied: dict[str, AvatarSlotEquipment] = {}
    for entry in avatar.equipment:
        if entry.item is None:
            continue
        occupied[entry.slot.value] = AvatarSlotEquipment(
            equipped_at=entry.equipped_at,
            item=to_item_read(entry.item),
        )

    return AvatarRead(
        avatar_id=avatar.avatar_id,
        equipment=AvatarEquipmentMap(**occupied),
    )


def load_wardrobe(
    db: Session, user_id: uuid.UUID, limit: int, offset: int
) -> WardrobeList:
    """One page of `user_id`'s owned clothing, newest purchase first."""
    total = db.execute(
        select(func.count(UserWardrobe.wardrobe_id)).where(
            UserWardrobe.user_id == user_id
        )
    ).scalar_one()

    rows = db.execute(
        select(UserWardrobe)
        .where(UserWardrobe.user_id == user_id)
        .options(joinedload(UserWardrobe.item).joinedload(ClothingItem.category))
        .order_by(UserWardrobe.purchased_at.desc(), UserWardrobe.wardrobe_id.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    return WardrobeList(
        items=[
            WardrobeEntryRead(
                wardrobe_id=entry.wardrobe_id,
                purchased_at=entry.purchased_at,
                item=to_item_read(entry.item),
            )
            for entry in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


def follow_counts(db: Session, user_id: uuid.UUID) -> tuple[int, int]:
    """(followers, following) for one user, in a single round trip.

    Two scalar subqueries rather than two statements: the profile screen shows
    both numbers together and there is no reason to pay two round trips for it.
    """
    followers = (
        select(func.count())
        .select_from(Follow)
        .where(Follow.followee_id == user_id)
        .scalar_subquery()
    )
    following = (
        select(func.count())
        .select_from(Follow)
        .where(Follow.follower_id == user_id)
        .scalar_subquery()
    )
    row = db.execute(select(followers, following)).one()
    return int(row[0]), int(row[1])


def active_competition_id(db: Session, user_id: uuid.UUID) -> uuid.UUID | None:
    """The id of the user's currently ACTIVE competition, if any.

    A user may hold only one at a time (TZ section 11), so at most one row
    comes back; limit(1) keeps that true even if the invariant is ever
    violated rather than raising in the middle of rendering a profile.
    """
    return db.execute(
        select(Competition.competition_id)
        .join(CompetitionStatus, Competition.status_id == CompetitionStatus.status_id)
        .where(
            CompetitionStatus.status_name == "active",
            (Competition.challenger_id == user_id)
            | (Competition.opponent_id == user_id),
        )
        .order_by(Competition.start_time.desc())
        .limit(1)
    ).scalar_one_or_none()


def to_item_read(item: ClothingItem) -> ClothingItemRead:
    """The canonical catalog shape, identical everywhere an item appears."""
    return ClothingItemRead(
        item_id=item.item_id,
        name=item.name,
        description=item.description,
        category=ClothingCategoryRef(
            category_id=item.category.category_id,
            category_name=item.category.category_name,
            slot=item.category.slot,
        ),
        price=item.price,
        image_url=item.image_url,
        availability_status=item.availability_status,
        collection_id=item.collection_id,
    )
