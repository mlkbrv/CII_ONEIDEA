"""
GET /admin/overview — the dashboard's live numbers.

One endpoint, one round trip, one query per number: every figure here is a
plain COUNT/SUM computed at read time (no rollup table, no cache to go
stale), because the whole point of a dashboard is that what it shows is true
right now. The queries are cheap by construction — every column filtered or
grouped on already carries an index or is a lookup-table join — and this is
a low-traffic admin panel, not a public endpoint under load.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_admin
from app.models import (
    ClothingAvailability,
    ClothingItem,
    CoinTransaction,
    Competition,
    CompetitionStatus,
    Notification,
    QRCode,
    QRStatus,
    User,
    Vote,
)
from app.schemas.admin_overview import AdminOverview
from app.services import demographics

router = APIRouter(tags=["admin"])


@router.get("", response_model=AdminOverview)
def get_overview(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> AdminOverview:
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    users_total = db.scalar(select(func.count()).select_from(User))
    users_active = db.scalar(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    )
    users_via_telegram = db.scalar(
        select(func.count()).select_from(User).where(User.telegram_id.is_not(None))
    )
    users_new_24h = db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= since_24h)
    )

    # users.coin_balance is a cache (see app/models/user.py), but it is
    # exactly the number a dashboard means by "coins in circulation" — the
    # ledger sum would double as an integrity check, which is a job for a
    # test, not a page load.
    coins_in_circulation = db.scalar(select(func.coalesce(func.sum(User.coin_balance), 0)))
    # amount is signed: positive = credit, negative = debit (see
    # app/models/coin_transaction.py). Split by sign rather than by
    # transaction type, so this total needs no maintenance when a new
    # transaction type is added.
    coins_issued_total = db.scalar(
        select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(
            CoinTransaction.amount > 0
        )
    )
    coins_spent_total = db.scalar(
        select(func.coalesce(func.sum(-CoinTransaction.amount), 0)).where(
            CoinTransaction.amount < 0
        )
    )

    qr_status_counts: dict[QRStatus, int] = {
        row_status: count
        for row_status, count in db.execute(
            select(QRCode.status, func.count()).group_by(QRCode.status)
        ).all()
    }

    catalog_items_total = db.scalar(select(func.count()).select_from(ClothingItem))
    catalog_items_available = db.scalar(
        select(func.count())
        .select_from(ClothingItem)
        .where(ClothingItem.availability_status == ClothingAvailability.AVAILABLE)
    )

    competition_status_counts: dict[str, int] = {
        status_name: count
        for status_name, count in db.execute(
            select(CompetitionStatus.status_name, func.count(Competition.competition_id))
            .join(Competition, Competition.status_id == CompetitionStatus.status_id, isouter=True)
            .group_by(CompetitionStatus.status_name)
        ).all()
    }
    votes_cast_total = db.scalar(select(func.count()).select_from(Vote))

    notifications_pending = db.scalar(
        select(func.count()).select_from(Notification).where(Notification.delivered_at.is_(None))
    )

    return AdminOverview(
        users_total=users_total,
        users_active=users_active,
        users_via_telegram=users_via_telegram,
        users_new_24h=users_new_24h,
        coins_in_circulation=coins_in_circulation,
        coins_issued_total=coins_issued_total,
        coins_spent_total=coins_spent_total,
        qr_codes_active=qr_status_counts.get(QRStatus.ACTIVE, 0),
        qr_codes_redeemed=qr_status_counts.get(QRStatus.REDEEMED, 0),
        qr_codes_expired=qr_status_counts.get(QRStatus.EXPIRED, 0),
        catalog_items_total=catalog_items_total,
        catalog_items_available=catalog_items_available,
        competitions_active=competition_status_counts.get("active", 0),
        competitions_completed=competition_status_counts.get("completed", 0),
        votes_cast_total=votes_cast_total,
        notifications_pending=notifications_pending,
        demographics=demographics.stats(db),
        generated_at=datetime.now(timezone.utc),
    )
