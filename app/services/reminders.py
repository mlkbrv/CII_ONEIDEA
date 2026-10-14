"""
"Your battle ends in 10 minutes" — TZ section 16.

This is the notification the whole time-boxed design depends on. A battle
lasts 30 minutes to 24 hours and is decided by how many followers each side
can rally, so a player who forgets it is running loses to one who does not.

Runs in the worker next to the expiration sweeper, because both are periodic
sweeps over the same rows and neither belongs in an HTTP request.

Exactly-once is enforced by `competitions.reminder_sent_at`, set in the same
transaction as the notifications it announces. Two workers running at once
would both see the row, but only one can commit the stamp — the guarded
UPDATE below affects zero rows for the loser, which then rolls its
notifications back rather than sending a second copy.
"""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Competition
from app.services.competition_expiration import end_instant_utc, resolve_status_id
from app.services.notifications import COMPETITION_ENDING_SOON, create_notification

logger = logging.getLogger(__name__)


def sweep_ending_soon(minutes_before: int) -> int:
    """Notify both sides of every battle about to end. Returns how many were sent.

    A battle shorter than the reminder window (the 30-minute preset with a
    10-minute warning is fine, but a hypothetical 5-minute battle would not
    be) still gets exactly one reminder, immediately — better early than not
    at all.
    """
    sent = 0
    with SessionLocal() as db:
        for competition in _candidates(db, minutes_before):
            if _claim(db, competition, minutes_before):
                sent += 1
    return sent


def _candidates(db: Session, minutes_before: int) -> list[Competition]:
    """ACTIVE, unreminded battles whose end is within the window.

    The window is computed in Python from start_time + duration_minutes rather
    than filtered on the generated `end_time` column: that column is computed
    in the database session's timezone, while the app stores naive UTC, so
    comparing against it would shift the reminder by the server's UTC offset.
    end_instant_utc is the same helper the expiration sweeper uses, so both
    agree on when a battle ends.

    Loading the candidates and filtering in Python is fine here: only ACTIVE
    battles without a reminder qualify, which at fest scale is a handful.
    """
    active_id = resolve_status_id(db, "active")
    rows = db.execute(
        select(Competition).where(
            Competition.status_id == active_id,
            Competition.reminder_sent_at.is_(None),
        )
    ).scalars().all()

    threshold = datetime.now(UTC) + timedelta(minutes=minutes_before)
    return [c for c in rows if end_instant_utc(c) <= threshold]


def _claim(db: Session, competition: Competition, minutes_before: int) -> bool:
    """Stamp the reminder and stage both notifications, atomically.

    The UPDATE is guarded on reminder_sent_at still being NULL, so of two
    workers racing on the same battle exactly one commits.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    claimed = db.execute(
        update(Competition)
        .where(
            Competition.competition_id == competition.competition_id,
            Competition.reminder_sent_at.is_(None),
        )
        .values(reminder_sent_at=now)
    )
    if claimed.rowcount == 0:
        db.rollback()
        return False

    minutes_left = max(
        0, int((end_instant_utc(competition) - datetime.now(UTC)).total_seconds() // 60)
    )
    payload = {
        "competition_id": str(competition.competition_id),
        "minutes_left": minutes_left or minutes_before,
    }
    for user_id in (competition.challenger_id, competition.opponent_id):
        create_notification(
            db,
            user_id=user_id,
            type_name=COMPETITION_ENDING_SOON,
            payload=payload,
        )

    db.commit()
    logger.info("Reminder queued for competition %s", competition.competition_id)
    return True
