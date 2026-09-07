"""
Turning a verified Telegram identity into a local account.

The signature check lives in app/core/telegram.py and answers "is this really
Telegram talking about user 12345?". This module answers the next question:
"which row in `users` is that?" — creating one on first contact.

Account creation mirrors POST /auth/register: the User, the Avatar and the
auth_providers link are inserted in ONE transaction. A committed user without
an avatar would break GET /avatar for that account forever, and avatars.user_id
is UNIQUE so it cannot be repaired by inserting a second one blindly.

Usernames are the awkward part. Ours must satisfy the same rules the register
endpoint enforces (3-30 chars of [A-Za-z0-9_], unique under CITEXT), while
Telegram gives us either an @handle (already in that alphabet), or only a first
name (which is routinely Cyrillic, emoji, or spaces). So we sanitise down to
the allowed alphabet and fall back through: @handle -> first name -> "user".
"""
import logging
import re
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.telegram import TelegramUser
from app.models import AuthProvider, AuthProviderType, Avatar, User

logger = logging.getLogger(__name__)

_USERNAME_MIN = 3
_USERNAME_MAX = 30
_DISALLOWED = re.compile(r"[^A-Za-z0-9_]")

# How many "name_2, name_3, ..." variants to try before giving up on a
# readable username and appending random hex instead.
_SUFFIX_ATTEMPTS = 20

# How many times to retry the whole insert when a concurrent request grabs
# the username (or the same Telegram id) between our check and our commit.
_INSERT_ATTEMPTS = 3


def get_or_create_telegram_user(db: Session, telegram_user: TelegramUser) -> User:
    """Return the account for this Telegram id, creating it on first contact."""
    user = db.execute(
        select(User).where(User.telegram_id == telegram_user.id)
    ).scalar_one_or_none()

    if user is not None:
        _refresh_telegram_profile(db, user, telegram_user)
        return user

    for attempt in range(_INSERT_ATTEMPTS):
        try:
            return _create_telegram_user(db, telegram_user)
        except IntegrityError:
            db.rollback()
            # Someone else won the race. If they created THIS Telegram user,
            # we are done; otherwise they merely took the username we wanted
            # and the next attempt picks a different one.
            existing = db.execute(
                select(User).where(User.telegram_id == telegram_user.id)
            ).scalar_one_or_none()
            if existing is not None:
                return existing
            logger.warning(
                "Retrying Telegram account creation after conflict (attempt %d)",
                attempt + 1,
            )

    raise RuntimeError(
        f"Could not create an account for Telegram id {telegram_user.id}"
    )


def _create_telegram_user(db: Session, telegram_user: TelegramUser) -> User:
    user = User(
        username=_allocate_username(db, telegram_user),
        email=None,
        password_hash=None,
        telegram_id=telegram_user.id,
        telegram_username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
        profile_picture_url=telegram_user.photo_url,
    )
    # Avatar(user=user) lets SQLAlchemy resolve the FK after the users INSERT,
    # so no id is generated client-side and both rows land in one flush.
    avatar = Avatar(user=user)
    provider = AuthProvider(
        user=user,
        provider=AuthProviderType.TELEGRAM,
        provider_user_id=str(telegram_user.id),
    )

    db.add_all([user, avatar, provider])
    db.commit()
    db.refresh(user)
    logger.info("Created account %s from Telegram id %s", user.username, telegram_user.id)
    return user


def _refresh_telegram_profile(
    db: Session, user: User, telegram_user: TelegramUser
) -> None:
    """Keep the mirrored Telegram fields current.

    Deliberately does NOT touch `user.username` — that is ours and the user
    may have renamed themselves in the app; overwriting it whenever they
    change their @handle in Telegram would undo that silently. Same for
    profile_picture_url once the user has set one of their own: we only fill
    it in while it is still empty.
    """
    changed = False

    for field, value in (
        ("telegram_username", telegram_user.username),
        ("first_name", telegram_user.first_name),
        ("last_name", telegram_user.last_name),
    ):
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed = True

    if user.profile_picture_url is None and telegram_user.photo_url:
        user.profile_picture_url = telegram_user.photo_url
        changed = True

    if changed:
        db.commit()
        db.refresh(user)


def _allocate_username(db: Session, telegram_user: TelegramUser) -> str:
    base = (
        _sanitise(telegram_user.username)
        or _sanitise(telegram_user.first_name)
        or "user"
    )

    if not _username_taken(db, base):
        return base

    # Readable variants first: alice, alice_2, alice_3, ...
    for suffix in range(2, _SUFFIX_ATTEMPTS + 2):
        candidate = _with_suffix(base, f"_{suffix}")
        if not _username_taken(db, candidate):
            return candidate

    # Popular base name. Stop guessing and take something collision-proof.
    return _with_suffix(base, f"_{secrets.token_hex(4)}")


def _username_taken(db: Session, username: str) -> bool:
    # CITEXT makes this comparison case-insensitive, exactly like the UNIQUE
    # constraint it is standing in for.
    return (
        db.execute(select(User.user_id).where(User.username == username)).scalar()
        is not None
    )


def _sanitise(value: str | None) -> str | None:
    """Reduce a Telegram name to the alphabet our usernames allow.

    Cyrillic first names sanitise down to nothing, which is why every caller
    has a fallback. Names shorter than the minimum are padded rather than
    rejected — "Ed" is a perfectly good name and should not cost the user a
    random string.
    """
    if not value:
        return None
    cleaned = _DISALLOWED.sub("", value)[:_USERNAME_MAX]
    if not cleaned:
        return None
    if len(cleaned) < _USERNAME_MIN:
        cleaned = f"{cleaned}{'_' * (_USERNAME_MIN - len(cleaned))}"
    return cleaned


def _with_suffix(base: str, suffix: str) -> str:
    """Append a suffix, trimming the base so the result still fits."""
    return f"{base[: _USERNAME_MAX - len(suffix)]}{suffix}"


def user_id_for_telegram_id(db: Session, telegram_id: int) -> uuid.UUID | None:
    """Look up an account id by Telegram id without creating one.

    Used by the bot, which must not conjure accounts for people who merely
    typed a command in a chat without ever opening the Mini App.
    """
    return db.execute(
        select(User.user_id).where(User.telegram_id == telegram_id)
    ).scalar_one_or_none()
