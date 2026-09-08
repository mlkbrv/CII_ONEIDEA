"""
Pushing pending notifications to Telegram.

The API writes notification rows; this loop sends them. That split is the
whole design (see the d3b6f1c47a28 migration): a request must never hold a
database transaction open across a call to Telegram's servers, and a
notification must not be lost because Telegram happened to be slow at the
moment somebody accepted a challenge.

Delivery is at-least-once, biased towards not losing anything: the row is
stamped `delivered_at` only after Telegram accepts the message. A crash
between send and stamp re-sends on the next pass, which is a duplicate
message — annoying, and much better than a player never hearing that their
battle ended.

Failures are handled by outcome, not by exception type:
  * the user blocked the bot, or never started it — permanent, so the row is
    stamped and never retried. It is not a fault, and retrying it forever
    would eventually starve the queue.
  * rate limited — back off for as long as Telegram asks, then retry.
  * anything else — leave the row alone; the next pass tries again.
"""
import asyncio
import logging
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.exceptions import (
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import SessionLocal
from app.models import Notification, User
from app.bot.keyboards import webapp_keyboard
from app.services.notifications import render

logger = logging.getLogger("cci.bot.delivery")

# How many notifications one pass sends. Small enough that a backlog is worked
# through gradually rather than in a burst Telegram would rate-limit anyway.
BATCH_SIZE = 25


async def deliver_pending(bot: Bot) -> int:
    """Send one batch of undelivered notifications. Returns how many were sent."""
    pending = await asyncio.to_thread(_load_pending)
    if not pending:
        return 0

    sent = 0
    for notification_id, chat_id, text, language in pending:
        try:
            # The button is built per message rather than once per batch: its
            # label is words too, and a Russian button under an Azerbaijani
            # notification is exactly the kind of half-translated app this
            # feature exists to avoid.
            await bot.send_message(
                chat_id, text, reply_markup=webapp_keyboard(language=language)
            )
        except TelegramRetryAfter as exc:
            # Telegram tells us exactly how long to wait. Stop the batch here;
            # what is left stays undelivered and goes out on the next pass.
            logger.warning("Rate limited by Telegram, backing off %ss", exc.retry_after)
            await asyncio.sleep(exc.retry_after)
            break
        except TelegramForbiddenError:
            # Bot blocked, or the user never pressed Start. Permanent — mark it
            # delivered so it stops occupying the queue.
            logger.info("Chat %s is unreachable; dropping notification", chat_id)
            await asyncio.to_thread(_mark_delivered, notification_id)
            continue
        except Exception:
            # Transient or unknown. Leave the row for the next pass rather than
            # silently swallowing a notification the user is waiting for.
            logger.exception("Failed to deliver notification %s", notification_id)
            continue

        await asyncio.to_thread(_mark_delivered, notification_id)
        sent += 1

    return sent


def _load_pending() -> list[tuple]:
    """(notification_id, chat id, rendered text, language) for the next batch.

    Rendered here rather than in the sending loop so the DB session — and the
    ORM objects that belong to it — never outlive this function.

    Notifications for users with no telegram_id are stamped rather than sent:
    an account created through /auth/register has no Telegram chat to push to,
    and it would otherwise sit at the head of the queue forever.
    """
    with SessionLocal() as db:
        rows = db.execute(
            select(Notification)
            .where(Notification.delivered_at.is_(None))
            .options(
                joinedload(Notification.type),
                joinedload(Notification.actor),
                joinedload(Notification.user),
            )
            .order_by(Notification.created_at)
            .limit(BATCH_SIZE)
        ).scalars().all()

        deliverable = []
        undeliverable = []
        for row in rows:
            recipient: User = row.user
            if recipient is None or recipient.telegram_id is None:
                undeliverable.append(row.notification_id)
                continue
            deliverable.append(
                (
                    row.notification_id,
                    recipient.telegram_id,
                    render(
                        row.type.type_name,
                        row.actor.username if row.actor else None,
                        row.payload,
                        # The RECIPIENT's language, not the actor's: the
                        # person reading this is the one being notified.
                        recipient.language,
                    ),
                    recipient.language,
                )
            )

        if undeliverable:
            _stamp(db, undeliverable)
            db.commit()

        return deliverable


def _mark_delivered(notification_id) -> None:
    with SessionLocal() as db:
        _stamp(db, [notification_id])
        db.commit()


def _stamp(db: Session, notification_ids: list) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    for notification_id in notification_ids:
        notification = db.get(Notification, notification_id)
        if notification is not None and notification.delivered_at is None:
            notification.delivered_at = now


async def run_delivery_loop(bot: Bot, interval_seconds: int) -> None:
    """Deliver forever, pausing between passes when the queue runs dry.

    A pass that sent a full batch does not sleep — a backlog should drain at
    Telegram's pace, not at the poll interval's.
    """
    logger.info("Notification delivery loop started (every %ss)", interval_seconds)
    while True:
        try:
            sent = await deliver_pending(bot)
        except Exception:
            # A failure here must not kill the loop; the next pass retries.
            logger.exception("Notification delivery pass failed")
            sent = 0

        if sent < BATCH_SIZE:
            await asyncio.sleep(interval_seconds)
