"""
Notification feed — the in-app half of TZ section 16.

The bot pushes; this is what the Mini App shows when the user opens the bell.
Both read the same rows and the same wording (app/services/notifications.py
renders the text), so a message in Telegram and its entry in the feed can
never say different things.

Every path here is fixed to the caller: the user_id comes from the JWT and
never from the client, so there is no request shape that reads or clears
somebody else's notifications.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Notification, User
from app.schemas.notification import (
    NotificationList,
    NotificationRead,
    UnreadCount,
)
from app.services.notifications import render

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationList)
def list_notifications(
    unread_only: bool = Query(
        default=False,
        description="Return only notifications the user has not read yet",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationList:
    conditions = [Notification.user_id == current_user.user_id]
    if unread_only:
        conditions.append(Notification.is_read.is_(False))

    total = db.execute(
        select(func.count()).select_from(Notification).where(*conditions)
    ).scalar_one()

    # The unread count is returned on every page, not only on the unread
    # filter: the bell badge is on screen while the user reads the list, and
    # it should not need a second request to stay right.
    unread = db.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == current_user.user_id,
            Notification.is_read.is_(False),
        )
    ).scalar_one()

    rows = db.execute(
        select(Notification)
        .where(*conditions)
        .options(
            joinedload(Notification.type),
            joinedload(Notification.actor),
        )
        # (user_id, is_read, created_at) is indexed for exactly this shape.
        .order_by(Notification.created_at.desc(), Notification.notification_id.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    return NotificationList(
        items=[_to_read(row) for row in rows],
        total=total,
        unread=unread,
        limit=limit,
        offset=offset,
    )


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnreadCount:
    """Just the badge number — cheap enough to poll."""
    count = db.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == current_user.user_id,
            Notification.is_read.is_(False),
        )
    ).scalar_one()
    return UnreadCount(unread=count)


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationRead:
    notification = db.execute(
        select(Notification)
        .where(
            Notification.notification_id == notification_id,
            # Ownership is part of the WHERE clause, not a check afterwards:
            # someone else's notification is simply not found, which is also
            # the honest answer to give — its existence is not their business.
            Notification.user_id == current_user.user_id,
        )
        .options(joinedload(Notification.type), joinedload(Notification.actor))
    ).scalar_one_or_none()

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    # Idempotent: marking an already-read notification read again is a no-op
    # rather than an error. Clients retry on flaky mobile connections.
    if not notification.is_read:
        notification.is_read = True
        db.commit()
        db.refresh(notification)

    return _to_read(notification)


@router.post("/read-all", response_model=UnreadCount)
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnreadCount:
    """Clear the badge in one request — what the bell screen does on open."""
    db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    db.commit()
    return UnreadCount(unread=0)


def _to_read(notification: Notification) -> NotificationRead:
    return NotificationRead(
        notification_id=notification.notification_id,
        type=notification.type.type_name,
        message=render(
            notification.type.type_name,
            notification.actor.username if notification.actor else None,
            notification.payload,
        ),
        actor_id=notification.actor_user_id,
        actor_username=notification.actor.username if notification.actor else None,
        payload=notification.payload,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )
