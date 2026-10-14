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

**The text is chosen here, not in the bot.** `render` below is the single
answer to "what does a competition_accepted say", so the wording cannot drift
between the in-app feed and the Telegram message. The words themselves live in
app/services/i18n.py, where all three languages sit side by side.
"""
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification, NotificationType, User
from app.services.i18n import human_duration, t

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
# What the user actually reads, in the app feed and in Telegram alike. The
# wording lives in app/services/i18n.py so a message and its entry in the feed
# cannot drift apart, and so all three languages sit side by side.


def render(
    type_name: str,
    actor_name: str | None,
    payload: dict | None,
    language: str | None = None,
) -> str:
    """The message text for one notification, in the recipient's language.

    Falls back to a generic line for an unknown type rather than failing: a
    notification the worker cannot phrase should still reach the user as
    something, and the type name is logged by the translator.
    """
    who = actor_name or t("notification.someone", language)
    data = payload or {}

    if type_name == COMPETITION_REQUEST:
        minutes = data.get("duration_minutes")
        duration = (
            t(
                "notification.competition_request.duration",
                language,
                duration=human_duration(minutes, language),
            )
            if minutes
            else ""
        )
        return t("notification.competition_request", language, actor=who, duration=duration)

    if type_name == COMPETITION_ENDING_SOON:
        return t(
            "notification.competition_ending_soon",
            language,
            minutes=data.get("minutes_left", 10),
        )

    if type_name == COMPETITION_WON:
        streak_value = data.get("winning_streak")
        streak = (
            t("notification.competition_won.streak", language, streak=streak_value)
            if streak_value
            else ""
        )
        return t(
            "notification.competition_won",
            language,
            prize=data.get("prize_pool", 0),
            streak=streak,
        )

    if type_name == COMPETITION_DRAW:
        return t("notification.competition_draw", language, prize=data.get("prize_pool", 0))

    # The rest are a plain lookup keyed by type, with the actor substituted.
    if type_name in {
        NEW_FOLLOWER,
        COMPETITION_ACCEPTED,
        COMPETITION_DECLINED,
        COMPETITION_LOST,
    }:
        return t(f"notification.{type_name}", language, actor=who)

    logger.warning("No message template for notification type %r", type_name)
    return t("notification.unknown", language)
