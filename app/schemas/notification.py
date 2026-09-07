"""
Schemas for the notification feed.

`message` is rendered server-side rather than left to the client. The bot has
to produce the same sentence for the same event, and a Telegram message and
its entry in the in-app feed disagreeing about what happened would be worse
than either being slightly less tailored.

`payload` is still exposed alongside it so the client can act on the
notification — open the battle it refers to, or the profile of whoever
followed you — without parsing the sentence.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NotificationRead(BaseModel):
    notification_id: uuid.UUID

    # The lookup table's type_name ("competition_accepted", ...). Clients
    # switch on this for the icon; they must not switch on `message`.
    type: str
    message: str

    # Who caused it, when that makes sense — a challenger, a new follower.
    # Null for notifications nobody triggered, like "your battle ends soon".
    actor_id: uuid.UUID | None = None
    actor_username: str | None = None

    # Type-specific references: competition_id, request_id, prize_pool, and
    # so on. Shape varies by type; see app/services/notifications.py.
    payload: dict[str, Any] | None = None

    is_read: bool
    created_at: datetime


class NotificationList(BaseModel):
    items: list[NotificationRead]
    total: int

    # The badge number, returned on every page so the bell stays right while
    # the user is reading the list.
    unread: int

    limit: int
    offset: int


class UnreadCount(BaseModel):
    unread: int
