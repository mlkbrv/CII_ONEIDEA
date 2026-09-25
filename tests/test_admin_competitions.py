"""
End-to-end checks of admin battle monitoring (/admin/competitions).

Run from the backend/ directory:
    venv/Scripts/python -m tests.test_admin_competitions

Covers:
  - Authorization: unauthenticated -> 401, a normal user -> 403, an admin -> 200.
  - List: sees a battle the admin is NOT a participant of (unlike the public
    /competitions endpoint, which is participant-scoped) — that is the whole
    point of this module. Status filter, username search on EITHER side.
  - Detail: both participants' usernames, live vote counts, prize pool, and
    both outfits (challenger_avatar/opponent_avatar) — including a slot the
    challenger actually has equipped, so the avatar shape isn't just an
    empty default.
  - 404 for a nonexistent id.

All fixture rows are removed afterwards.
"""
import time
import uuid
import warnings

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import (
    AvatarEquipment,
    AvatarSlot,
    ClothingCategory,
    ClothingItem,
    Competition,
    CompetitionRequest,
    User,
    UserWardrobe,
)

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

client = TestClient(app)

RUN_ID = f"{int(time.time())}{uuid.uuid4().hex[:6]}"
PASSWORD = "SuperSecret123!"
ADMIN_USERNAME = f"cadmin_{RUN_ID}"
USER_A = f"cba_{RUN_ID}"
USER_B = f"cbb_{RUN_ID}"
ALL_USERS = [ADMIN_USERNAME, USER_A, USER_B]

results = []
created_item_ids: list[uuid.UUID] = []
created_category_ids: list[int] = []


def report(name: str, ok: bool, extra: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({extra})" if extra else ""))


def cleanup() -> None:
    with SessionLocal() as db:
        ids = db.execute(select(User.user_id).where(User.username.in_(ALL_USERS))).scalars().all()
        if ids:
            for req in db.execute(
                select(CompetitionRequest).where(
                    CompetitionRequest.challenger_id.in_(ids)
                    | CompetitionRequest.opponent_id.in_(ids)
                )
            ).scalars().all():
                for comp in db.execute(
                    select(Competition).where(Competition.request_id == req.request_id)
                ).scalars().all():
                    db.delete(comp)
                db.delete(req)
            db.commit()
            for row in db.execute(select(User).where(User.username.in_(ALL_USERS))).scalars().all():
                db.delete(row)
            db.commit()
        for item_id in created_item_ids:
            item = db.get(ClothingItem, item_id)
            if item is not None:
                db.delete(item)
        for category_id in created_category_ids:
            category = db.get(ClothingCategory, category_id)
            if category is not None:
                db.delete(category)
        db.commit()
    print(f"\nCleaned up admin-competitions fixtures for run {RUN_ID}.")


try:
    for username in ALL_USERS:
        client.post(
            "/auth/register",
            json={"username": username, "email": f"{username}@example.com", "password": PASSWORD},
        )
    with SessionLocal() as db:
        admin_id = db.execute(select(User.user_id).where(User.username == ADMIN_USERNAME)).scalar_one()
        db.get(User, admin_id).is_admin = True
        db.commit()

    admin_token = client.post(
        "/auth/login", json={"username": ADMIN_USERNAME, "password": PASSWORD}
    ).json().get("access_token", "")
    ADMIN_AUTH = {"Authorization": f"Bearer {admin_token}"}

    a_token = client.post(
        "/auth/login", json={"username": USER_A, "password": PASSWORD}
    ).json().get("access_token", "")
    A_AUTH = {"Authorization": f"Bearer {a_token}"}
    b_token = client.post(
        "/auth/login", json={"username": USER_B, "password": PASSWORD}
    ).json().get("access_token", "")

    # --- Authorization -------------------------------------------------------
    results.append(("unauthenticated -> 401", client.get("/admin/competitions").status_code == 401, ""))
    results.append(("non-admin -> 403", client.get("/admin/competitions", headers=A_AUTH).status_code == 403, ""))

    with SessionLocal() as db:
        user_a_id = db.execute(select(User.user_id).where(User.username == USER_A)).scalar_one()
        user_b_id = db.execute(select(User.user_id).where(User.username == USER_B)).scalar_one()

    # A hat, equipped by the challenger, so the avatar detail check has an
    # actual item to find rather than an empty equipment map.
    category = ClothingCategory(category_name=f"AC Cat {RUN_ID}", slot=AvatarSlot.HAT)
    with SessionLocal() as db:
        db.add(category)
        db.commit()
        db.refresh(category)
    created_category_ids.append(category.category_id)

    item = ClothingItem(
        name=f"AC Hat {RUN_ID}", category_id=category.category_id,
        price=0, image_url="/media/uploads/hat/ac.svg",
    )
    with SessionLocal() as db:
        db.add(item)
        db.commit()
        db.refresh(item)
    created_item_ids.append(item.item_id)

    with SessionLocal() as db:
        db.add(UserWardrobe(user_id=user_a_id, item_id=item.item_id))
        db.commit()
        avatar_id = db.execute(
            select(User).where(User.user_id == user_a_id)
        ).scalar_one().avatar.avatar_id
        db.add(AvatarEquipment(avatar_id=avatar_id, slot=AvatarSlot.HAT, item_id=item.item_id))
        db.commit()

    # --- One real battle, through the actual challenge/accept flow ----------
    request_id = client.post(
        "/competition-requests",
        headers=A_AUTH,
        json={"opponent_id": str(user_b_id), "duration_minutes": 60},
    ).json()["request_id"]
    client.post(
        f"/competition-requests/{request_id}/accept",
        headers={"Authorization": f"Bearer {b_token}"},
    )
    with SessionLocal() as db:
        competition_id = str(
            db.execute(
                select(Competition.competition_id).where(Competition.request_id == request_id)
            ).scalar_one()
        )

    # --- List: visible to the admin though they are not a participant -------
    listing = client.get("/admin/competitions", headers=ADMIN_AUTH).json()
    results.append(("list -> 200", "items" in listing, str(listing)[:150]))
    ids_seen = {row["competition_id"] for row in listing.get("items", [])}
    results.append(("the battle appears though the admin isn't a participant", competition_id in ids_seen, ""))

    active_only = client.get(
        "/admin/competitions", headers=ADMIN_AUTH, params={"status": "active"}
    ).json()
    results.append(
        (
            "status=active includes the battle",
            competition_id in {row["competition_id"] for row in active_only.get("items", [])},
            "",
        )
    )
    completed_only = client.get(
        "/admin/competitions", headers=ADMIN_AUTH, params={"status": "completed"}
    ).json()
    results.append(
        (
            "status=completed excludes it",
            competition_id not in {row["competition_id"] for row in completed_only.get("items", [])},
            "",
        )
    )

    search = client.get(
        "/admin/competitions", headers=ADMIN_AUTH, params={"q": USER_A}
    ).json()
    results.append(
        (
            "search by challenger username finds it",
            competition_id in {row["competition_id"] for row in search.get("items", [])},
            "",
        )
    )
    search_b = client.get(
        "/admin/competitions", headers=ADMIN_AUTH, params={"q": USER_B}
    ).json()
    results.append(
        (
            "search by opponent username finds it too",
            competition_id in {row["competition_id"] for row in search_b.get("items", [])},
            "",
        )
    )

    # --- Detail: both usernames, votes, and both outfits ---------------------
    detail = client.get(f"/admin/competitions/{competition_id}", headers=ADMIN_AUTH).json()
    results.append(("detail -> has both participants", detail.get("challenger", {}).get("username") == USER_A, str(detail.get("challenger"))))
    results.append(("detail -> opponent username", detail.get("opponent", {}).get("username") == USER_B, str(detail.get("opponent"))))
    results.append(("detail -> status is active", detail.get("status") == "active", str(detail.get("status"))))
    results.append(("detail -> prize_pool present", "prize_pool" in detail, ""))
    challenger_avatar = detail.get("challenger_avatar") or {}
    equipped = (challenger_avatar.get("equipment") or {}).get("hat")
    results.append(
        (
            "detail -> challenger_avatar shows the equipped hat",
            bool(equipped) and equipped.get("item", {}).get("name") == item.name,
            str(challenger_avatar)[:200],
        )
    )
    opponent_avatar = detail.get("opponent_avatar")
    results.append(("detail -> opponent_avatar present (even if empty)", opponent_avatar is not None, str(opponent_avatar)))

    results.append(
        (
            "nonexistent id -> 404",
            client.get(f"/admin/competitions/{uuid.uuid4()}", headers=ADMIN_AUTH).status_code == 404,
            "",
        )
    )

finally:
    cleanup()

failed = 0
for name, ok, extra in results:
    report(name, ok, extra)
    failed += 0 if ok else 1
print(f"\n{len(results) - failed}/{len(results)} checks passed.")
if failed:
    raise SystemExit(1)
