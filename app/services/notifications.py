"""
Writing notifications — the only place that inserts into `notifications`.

TZ section 16: battles are time-boxed, so the notification IS part of the
feature. Being challenged, having your challenge accepted, ten minutes left,
and the result are all moments the player has to hear about while they still
matter.

Two rules shape this module.

**Notifications are written, not sent, inside a request.** `create_notification`
only stages a row in the caller's transaction. If the surrounding operation
rolls back — the accept lost a race, the vote failed on insufficient coins —
the notification disappears with it, so nobody is ever told about something
that did not happen. Delivery to Telegram is a separate worker reading
`delivered_at IS NULL`, which is also what makes it survive a Telegram outage.

**The text lives here, not in the bot.** One place decides what a
competition_accepted says, so the wording cannot drift between the in-app feed
and the Telegram message, and a new notification type is one function here
rather than an edit in two files.
"""
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification, NotificationType, User

logger = logging.getLogger(__name__)

# type_name values seeded in the migrations. Referenced by name, never by id,
# because ids come from a sequence and differ between databases.
NEW_FOLLOWER = "new_follower"
COMPETITION_REQUEST = "competition_request"
COMPETITION_ACCEPTED = "competition_accepted"
COMPETITION_DECLINED = "competition_declined"
COMPETITION_ENDING_SOON = "competition_ending_soon"
COMPETITION_WON = "competition_won"
COMPETITION_LOST = "competition_lost"
COMPETITION_DRAW = "competition_draw"


def create_notification(
    db: Session,
    *,
    user_id: uuid.UUID,
    type_name: str,
    actor: User | None = None,
    payload: dict[str, Any] | None = None,
) -> Notification | None:
    """Stage one notification in the CALLER's transaction.

    Deliberately does not commit: the notification must land, or not land,
    with whatever caused it.

    Returns None instead of raising if the type is not seeded. A missing
    lookup row is an operational problem with the deployment, and it must not
    turn a successful battle acceptance into a 500 — the battle is the thing
    the user cares about, the notification is the courtesy.
    """
    type_id = db.execute(
        select(NotificationType.type_id).where(
            NotificationType.type_name == type_name
        )
    ).scalar_one_or_none()

    if type_id is None:
        logger.error(
            "Notification type %r is not configured; dropping notification for %s",
            type_name,
            user_id,
        )
        return None

    notification = Notification(
        user_id=user_id,
        type_id=type_id,
        actor_user_id=actor.user_id if actor is not None else None,
        payload=payload,
    )
    db.add(notification)
    return notification


# --- Rendering -------------------------------------------------------------
# What the user actually reads, in the app feed and in Telegram alike.


def render(type_name: str, actor_name: str | None, payload: dict | None) -> str:
    """The message text for one notification.

    Falls back to a generic line for an unknown type rather than failing:
    a notification the worker cannot phrase should still reach the user as
    something, and the type name is logged elsewhere.
    """
    who = actor_name or "Кто-то"
    data = payload or {}

    if type_name == NEW_FOLLOWER:
        return f"👋 {who} подписался на тебя"

    if type_name == COMPETITION_REQUEST:
        minutes = data.get("duration_minutes")
        duration = f" на {_human_duration(minutes)}" if minutes else ""
        return f"⚔️ {who} вызывает тебя на баттл{duration}!"

    if type_name == COMPETITION_ACCEPTED:
        return f"✅ {who} принял твой вызов. Баттл начался!"

    if type_name == COMPETITION_DECLINED:
        return f"🚫 {who} отклонил твой вызов"

    if type_name == COMPETITION_ENDING_SOON:
        minutes = data.get("minutes_left", 10)
        return f"⏰ Твой баттл заканчивается через {minutes} мин. Зови болельщиков!"

    if type_name == COMPETITION_WON:
        prize = data.get("prize_pool", 0)
        streak = data.get("winning_streak")
        streak_line = f"\nСерия побед: {streak}" if streak else ""
        return f"🏆 Ты выиграл баттл!\nПризовой фонд: {prize} монет{streak_line}"

    if type_name == COMPETITION_LOST:
        return "😔 Ты проиграл баттл. Смени образ и попробуй снова!"

    if type_name == COMPETITION_DRAW:
        prize = data.get("prize_pool", 0)
        return f"🤝 Ничья! Призовой фонд {prize} монет поделён поровну"

    logger.warning("No message template for notification type %r", type_name)
    return "У тебя новое уведомление в Cola Fest"


def _human_duration(minutes: int | None) -> str:
    """"30 минут" / "1 час" / "6 часов" — the presets from TZ section 10."""
    if not minutes:
        return ""
    if minutes < 60:
        return f"{minutes} минут"
    hours = minutes // 60
    if hours == 1:
        return "1 час"
    if hours < 5:
        return f"{hours} часа"
    return f"{hours} часов"
