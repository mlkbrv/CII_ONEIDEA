"""
Avatar — the authenticated user's current avatar state (Phase 5).

GET /avatar returns the caller's avatar together with its COMPLETE
currently-equipped clothing in ONE response, so the mobile client can
render the avatar without one request per slot. Customization itself is
NOT duplicated here: equipping/unequipping stays with the wardrobe
endpoints (POST|DELETE /wardrobe/{wardrobe_id}/equip), which are the
single writers of avatar_equipment — this endpoint only exposes the
resulting state:

    wardrobe equip/unequip -> avatar_equipment -> GET /avatar

Design notes
------------
- Data isolation: the avatar comes ONLY from the JWT
  (get_current_user() -> current_user.user_id) filtered directly in the
  SQL WHERE clause. The endpoint declares no user_id/avatar_id input, so
  there is no client value that could redirect the query at another
  user's avatar; a smuggled ?user_id=… query param is ignored by FastAPI.
- Missing avatar: avatars.user_id is UNIQUE (0-or-1 per user) and
  registration creates the avatar in the same transaction as the user,
  so a missing avatar is not a state this flow can produce anymore; if
  it is ever seen anyway (e.g. a legacy row predating the backfill), it
  is reported explicitly as 404 "Avatar not found" — the same
  convention the equip/unequip endpoints use — rather than silently
  created inside a read endpoint.
- No N+1: the avatar, its equipment rows, their items and the items'
  categories load in ONE query via
  joinedload(Avatar.equipment) -> joinedload(AvatarEquipment.item)
  -> joinedload(ClothingItem.category). An avatar has at most six
  equipment rows ((avatar_id, slot) PK), so the row-deduplicated join is
  cheap and no per-slot queries exist.
- Slot authority: slots come from avatar_equipment.slot, which the equip
  flow derived from clothing_items.category_id -> clothing_categories.slot
  at equip time; the nested item payload carries the same slot again via
  its category ref. Nothing recomputes or overrides it here.
- Availability independence: NO filter on clothing_items.availability_status.
  If an admin marks an equipped item UNAVAILABLE/UPCOMING, the avatar
  still reports it — availability governs buying, not wearing (mirrors
  the wardrobe rule).
- Empty slots: every one of the six AvatarSlot values is always present
  in the response; an empty slot is an explicit null (see
  AvatarEquipmentMap). A defensive note: avatar_equipment.item_id is
  nullable at the schema level, so an equipment row without an item
  (which the equip flow never writes) is treated as an empty slot too.
- Read-only: this endpoint performs no writes and never touches
  coin_balance or the ledger.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.avatar import AvatarRead
from app.services.profiles import load_avatar

router = APIRouter(prefix="/avatar", tags=["avatar"])


@router.get("", response_model=AvatarRead)
def get_my_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AvatarRead:
    # The owner filter uses ONLY the JWT-derived id; this endpoint accepts no
    # other input, so cross-user reads are impossible here. The same loader
    # serves GET /users/{id}/avatar, which takes its subject from the URL.
    avatar = load_avatar(db, current_user.user_id)
    if avatar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar not found",
        )
    return avatar
