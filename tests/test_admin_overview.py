"""
End-to-end checks of GET /admin/overview — the dashboard's live numbers.

Run from the backend/ directory:
    venv/Scripts/python -m tests.test_admin_overview

Covers:
  - Authorization: unauthenticated -> 401, a normal user -> 403, an admin -> 200.
  - Every field present with the right shape.
  - Each aggregation actually aggregates: creating one fixture of each kind
    (a new user, a Telegram-linked user, a coin ledger entry, an ACTIVE and
    a REDEEMED QR code, an AVAILABLE clothing item, an ACTIVE competition
    with one vote cast, one undelivered notification) moves the matching
    counter by exactly the expected delta — snapshotting before/after rather
    than asserting absolute values, since this reads the whole live table
    and other data may already exist.

All fixture rows are removed afterwards.
"""
import time
import uuid
import warnings
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core.database import SessionLocal
from app.main import app
from app.models import (
    ClothingAvailability,
    ClothingCategory,
    ClothingItem,
    CoinTransaction,
    CoinTransactionType,
    Competition,
    CompetitionRequest,
    Notification,
    NotificationType,
    Product,
    QRCode,
    QRStatus,
    User,
    Vote,
)

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

client = TestClient(app)

RUN_ID = f"{int(time.time())}{uuid.uuid4().hex[:6]}"
PASSWORD = "SuperSecret123!"
ADMIN_USERNAME = f"ovadmin_{RUN_ID}"
USER_A = f"ova_{RUN_ID}"
USER_B = f"ovb_{RUN_ID}"
USER_C = f"ovc_{RUN_ID}"
ALL_USERS = [ADMIN_USERNAME, USER_A, USER_B, USER_C]

results = []


def report(name: str, ok: bool, extra: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({extra})" if extra else ""))


def cleanup() -> None:
    with SessionLocal() as db:
        ids = db.execute(select(User.user_id).where(User.username.in_(ALL_USERS))).scalars().all()
        if ids:
            # coin_transactions references votes/competitions with RESTRICT
            # FKs (vote_id, competition_id) — it has to go first, or deleting
            # the vote/competition it references fails exactly like the app
            # itself would refuse to lose that audit trail.
            for tx in db.execute(
                select(CoinTransaction).where(CoinTransaction.user_id.in_(ids))
            ).scalars().all():
                db.delete(tx)
            db.commit()

            for req in db.execute(
                select(CompetitionRequest).where(
                    CompetitionRequest.challenger_id.in_(ids)
                    | CompetitionRequest.opponent_id.in_(ids)
                )
            ).scalars().all():
                for comp in db.execute(
                    select(Competition).where(Competition.request_id == req.request_id)
                ).scalars().all():
                    for vote in db.execute(
                        select(Vote).where(Vote.competition_id == comp.competition_id)
                    ).scalars().all():
                        db.delete(vote)
                    db.delete(comp)
                db.delete(req)
            db.commit()

            for notif in db.execute(
                select(Notification).where(
                    Notification.user_id.in_(ids) | Notification.actor_user_id.in_(ids)
                )
            ).scalars().all():
                db.delete(notif)
            db.commit()

        # QR codes (and the redemption reference they hold to a user) go
        # before the users themselves. db.delete(user) does not rely on the
        # column's ON DELETE RESTRICT — the ORM's own relationship cascade
        # runs first and NULLs qr_codes.redeemed_by_user_id via an UPDATE,
        # which then fails the same REDEEMED-implies-not-null CHECK
        # constraint the fixture had to work around when creating it.
        # Deleting the row outright leaves nothing to null.
        for qr in db.execute(select(QRCode).where(QRCode.code.like(f"OV-{RUN_ID}%"))).scalars().all():
            db.delete(qr)
        db.commit()

        for row in db.execute(select(User).where(User.username.in_(ALL_USERS))).scalars().all():
            db.delete(row)
        db.commit()
        for item in db.execute(
            select(ClothingItem).where(ClothingItem.name.like(f"%{RUN_ID}%"))
        ).scalars().all():
            db.delete(item)
        for category in db.execute(
            select(ClothingCategory).where(ClothingCategory.category_name.like(f"%{RUN_ID}%"))
        ).scalars().all():
            db.delete(category)
        for product in db.execute(
            select(Product).where(Product.sku == f"OV-SKU-{RUN_ID}")
        ).scalars().all():
            db.delete(product)
        db.commit()
    print(f"\nCleaned up overview fixtures for run {RUN_ID}.")


try:
    # The admin account is registered (and only the admin account) before the
    # "before" snapshot below, because reaching the endpoint at all needs an
    # admin token — there is no way around that one user existing first.
    # USER_A/B/C register AFTER "before", so the whole delta section is free
    # to attribute exactly 3 new users to itself rather than 4.
    client.post(
        "/auth/register",
        json={"username": ADMIN_USERNAME, "email": f"{ADMIN_USERNAME}@example.com", "password": PASSWORD},
    )
    with SessionLocal() as db:
        admin_id = db.execute(select(User.user_id).where(User.username == ADMIN_USERNAME)).scalar_one()
        db.get(User, admin_id).is_admin = True
        db.commit()

    admin_token = client.post(
        "/auth/login", json={"username": ADMIN_USERNAME, "password": PASSWORD}
    ).json().get("access_token", "")
    ADMIN_AUTH = {"Authorization": f"Bearer {admin_token}"}

    # --- Authorization, using the one account that exists so far -----------
    results.append(("unauthenticated -> 401", client.get("/admin/overview").status_code == 401, ""))

    before = client.get("/admin/overview", headers=ADMIN_AUTH).json()
    results.append(("admin -> 200", bool(before), ""))

    for username in [USER_A, USER_B, USER_C]:
        client.post(
            "/auth/register",
            json={"username": username, "email": f"{username}@example.com", "password": PASSWORD},
        )
    user_token = client.post(
        "/auth/login", json={"username": USER_A, "password": PASSWORD}
    ).json().get("access_token", "")
    USER_AUTH = {"Authorization": f"Bearer {user_token}"}
    results.append(
        ("non-admin -> 403", client.get("/admin/overview", headers=USER_AUTH).status_code == 403, "")
    )
    for field in [
        "users_total", "users_active", "users_via_telegram", "users_new_24h",
        "coins_in_circulation", "coins_issued_total", "coins_spent_total",
        "qr_codes_active", "qr_codes_redeemed", "qr_codes_expired",
        "catalog_items_total", "catalog_items_available",
        "competitions_active", "competitions_completed", "votes_cast_total",
        "notifications_pending", "generated_at",
    ]:
        results.append((f"field {field} present", field in before, str(before.get(field))))

    # --- Fixtures, one of each kind -----------------------------------------
    # Bare ids (select(User.user_id), not a loaded User instance) throughout —
    # matching tests/test_admin_qr.py's fixture pattern — so nothing here
    # depends on an ORM instance's relationship/backref sync, which is not
    # what this endpoint is testing anyway.
    with SessionLocal() as db:
        user_a_id = db.execute(select(User.user_id).where(User.username == USER_A)).scalar_one()
        user_b_id = db.execute(select(User.user_id).where(User.username == USER_B)).scalar_one()
        user_c_id = db.execute(select(User.user_id).where(User.username == USER_C)).scalar_one()

        # Telegram-linked account, with a credited coin balance matching a
        # ledger entry.
        credit_type = db.execute(
            select(CoinTransactionType).where(CoinTransactionType.type_name == "admin_adjustment")
        ).scalar_one_or_none() or db.execute(select(CoinTransactionType)).scalars().first()
        db.execute(
            update(User)
            .where(User.user_id == user_a_id)
            .values(telegram_id=int(f"9{int(time.time())}"), coin_balance=100)
        )
        db.add(
            CoinTransaction(
                user_id=user_a_id, type_id=credit_type.type_id,
                amount=100, balance_after=100,
            )
        )

        # One product, one ACTIVE and one REDEEMED QR code. Both start ACTIVE
        # and the second is moved to REDEEMED by a Core UPDATE afterwards —
        # not because that is how POST /qr/redeem itself works (it also does
        # a plain UPDATE, for the row-locking reasons in qr_code.py's
        # docstring), but because QRCode.redeemed_by is a relationship() on
        # this same FK column, and constructing an object with the FK column
        # set directly, alongside OTHER pending User-relationship changes in
        # the same flush (the CoinTransaction/Notification rows below), lets
        # SQLAlchemy's dependency processor resync that unset relationship
        # over the raw column — silently NULLing it back out right after
        # insert. A Core UPDATE has no relationship state to resync from.
        product = Product(name=f"Overview Test {RUN_ID}", sku=f"OV-SKU-{RUN_ID}")
        db.add(product)
        db.flush()
        db.add_all(
            [
                QRCode(code=f"OV-{RUN_ID}-A", product_id=product.product_id, coin_value=50, status=QRStatus.ACTIVE),
                QRCode(code=f"OV-{RUN_ID}-B", product_id=product.product_id, coin_value=50, status=QRStatus.ACTIVE),
            ]
        )
        db.flush()
        db.execute(
            update(QRCode)
            .where(QRCode.code == f"OV-{RUN_ID}-B")
            .values(
                status=QRStatus.REDEEMED,
                redeemed_by_user_id=user_b_id,
                redeemed_at=datetime.now(timezone.utc),
            )
        )

        # One AVAILABLE clothing item.
        category = ClothingCategory(category_name=f"OV Cat {RUN_ID}", slot="top")
        db.add(category)
        db.flush()
        db.add(
            ClothingItem(
                name=f"OV Item {RUN_ID}", category_id=category.category_id,
                price=100, image_url="/media/uploads/top/ov.svg",
                availability_status=ClothingAvailability.AVAILABLE,
            )
        )

        # One undelivered notification.
        notif_type = db.execute(select(NotificationType)).scalars().first()
        db.add(Notification(user_id=user_c_id, type_id=notif_type.type_id))

        db.commit()

    # An ACTIVE competition with one vote, through the real accept/vote flow
    # (not inserted directly) so total_votes/prize_pool stay consistent with
    # what the service layer actually writes.
    request_id = client.post(
        "/competition-requests",
        headers=USER_AUTH,
        json={"opponent_id": str(user_b_id), "duration_minutes": 60},
    ).json()["request_id"]
    b_token = client.post(
        "/auth/login", json={"username": USER_B, "password": PASSWORD}
    ).json().get("access_token", "")
    client.post(
        f"/competition-requests/{request_id}/accept",
        headers={"Authorization": f"Bearer {b_token}"},
    )
    with SessionLocal() as db:
        user_c_row = db.execute(select(User).where(User.username == USER_C)).scalar_one()
        user_c_row.coin_balance = 10
        db.commit()
    c_token = client.post(
        "/auth/login", json={"username": USER_C, "password": PASSWORD}
    ).json().get("access_token", "")
    with SessionLocal() as db:
        comp = db.execute(
            select(Competition).where(Competition.request_id == request_id)
        ).scalar_one()
        comp_id = str(comp.competition_id)
    client.post(
        f"/competitions/{comp_id}/votes",
        headers={"Authorization": f"Bearer {c_token}"},
        json={"voted_for_user_id": str(user_a_id)},
    )

    after = client.get("/admin/overview", headers=ADMIN_AUTH).json()

    def delta(field: str) -> int:
        return after.get(field, 0) - before.get(field, 0)

    results.append(("users_total grew by the 3 registered accounts", delta("users_total") == 3, str(delta("users_total"))))
    results.append(("users_via_telegram grew by 1", delta("users_via_telegram") == 1, str(delta("users_via_telegram"))))
    results.append(("users_new_24h grew by at least 3", delta("users_new_24h") >= 3, str(delta("users_new_24h"))))
    results.append(("coins_in_circulation reflects the credited balance", delta("coins_in_circulation") >= 100, str(delta("coins_in_circulation"))))
    results.append(("coins_issued_total grew by at least the 100-coin credit", delta("coins_issued_total") >= 100, str(delta("coins_issued_total"))))
    results.append(("qr_codes_active grew by 1", delta("qr_codes_active") == 1, str(delta("qr_codes_active"))))
    results.append(("qr_codes_redeemed grew by 1", delta("qr_codes_redeemed") == 1, str(delta("qr_codes_redeemed"))))
    results.append(("catalog_items_total grew by 1", delta("catalog_items_total") == 1, str(delta("catalog_items_total"))))
    results.append(("catalog_items_available grew by 1", delta("catalog_items_available") == 1, str(delta("catalog_items_available"))))
    results.append(("competitions_active grew by 1", delta("competitions_active") == 1, str(delta("competitions_active"))))
    results.append(("votes_cast_total grew by 1", delta("votes_cast_total") == 1, str(delta("votes_cast_total"))))
    results.append(("notifications_pending grew (nothing delivers in tests)", delta("notifications_pending") >= 1, str(delta("notifications_pending"))))

finally:
    cleanup()

failed = 0
for name, ok, extra in results:
    report(name, ok, extra)
    failed += 0 if ok else 1
print(f"\n{len(results) - failed}/{len(results)} checks passed.")
if failed:
    raise SystemExit(1)
