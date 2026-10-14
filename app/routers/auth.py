"""
Authentication routes.

Registration and login. Access tokens are returned on login and then used
by protected endpoints through get_current_user(). Refresh tokens, Google/
Apple login, logout/session revocation, and MFA are deliberately not part
of the MVP and are not implemented here.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.jwt import create_access_token
from app.core.security import hash_password, verify_password
from app.core.telegram import (
    ExpiredInitDataError,
    TelegramAuthError,
    TelegramNotConfiguredError,
    validate_init_data,
    validate_login_widget_data,
)
from app.models import Avatar, User
from app.schemas.telegram import TelegramInitDataLogin, TelegramWidgetLogin
from app.schemas.token import LoginRequest, Token
from app.schemas.user import UserRead, UserRegister
from app.services.telegram_auth import get_or_create_telegram_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> User:
    existing_username = db.execute(
        select(User.user_id).where(User.username == payload.username)
    ).scalar()
    if existing_username is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered",
        )

    existing_email = db.execute(
        select(User.user_id).where(User.email == payload.email)
    ).scalar()
    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )

    # Every registered user owns exactly one avatar (avatars.user_id is
    # UNIQUE). The avatar is created in the SAME transaction as the user:
    # one commit makes both permanent, and any failure rolls BOTH back —
    # this flow can never leave a committed user without an avatar.
    # Linking through the relationship (Avatar(user=user)) lets SQLAlchemy
    # resolve the FK after the user INSERT; no id is generated client-side.
    avatar = Avatar(user=user)

    try:
        db.add(user)
        db.add(avatar)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _duplicate_http_exception(exc) from exc

    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.execute(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.username)
        )
    ).scalar_one_or_none()

    # One message for both "bad user" and "bad password" so an attacker
    # can't tell from the error whether an account exists (no enumeration).
    if (
        user is None
        or user.password_hash is None
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=create_access_token(user.user_id))


def _duplicate_http_exception(exc: IntegrityError) -> HTTPException:
    """Map a DB unique-violation to a 409. Covers the race between our
    check and the insert, without relying on Postgres error strings."""
    constraint = getattr(exc.orig, "diag", None)
    constraint_name = getattr(constraint, "constraint_name", None)

    if constraint_name == "ix_users_username":
        detail = "Username is already registered"
    elif constraint_name == "ix_users_email":
        detail = "Email is already registered"
    else:
        detail = "Email or username is already registered"

    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

# --- Telegram sign-in ------------------------------------------------------
# There is no password here and no registration step. Telegram already
# authenticated the person; a valid signature over their initData is the
# credential, and the account is created on first contact. Both endpoints
# return the same Token as /auth/login, so the client stores one JWT
# regardless of which door it came through.


@router.post("/telegram", response_model=Token)
def login_with_telegram(
    payload: TelegramInitDataLogin, db: Session = Depends(get_db)
) -> Token:
    """Mini App sign-in. Body carries the raw Telegram.WebApp.initData."""
    telegram_user = _verify(validate_init_data, payload.init_data)
    user = get_or_create_telegram_user(db, telegram_user)
    return _token_for(user)


@router.post("/telegram-login", response_model=Token)
def login_with_telegram_widget(
    payload: TelegramWidgetLogin, db: Session = Depends(get_db)
) -> Token:
    """Browser / PWA sign-in via the Telegram Login Widget."""
    telegram_user = _verify(validate_login_widget_data, payload.data)
    user = get_or_create_telegram_user(db, telegram_user)
    return _token_for(user)


def _verify(validator, payload):
    """Run a Telegram validator, mapping its failures onto HTTP status codes.

    The distinction that matters to a client: 401 means "these credentials
    are no good, get fresh ones" (the Mini App can simply re-read initData),
    while 503 means the SERVER is misconfigured and retrying will not help
    until an operator sets TELEGRAM_BOT_TOKEN.
    """
    try:
        return validator(payload)
    except TelegramNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram authentication is not configured on this server",
        ) from exc
    except ExpiredInitDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram session has expired, please reopen the app",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except TelegramAuthError as exc:
        # Covers a bad signature and every malformed-payload case. The
        # message is deliberately the same for all of them: telling a caller
        # WHICH part of a forged payload failed just helps them forge better.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _token_for(user: User) -> Token:
    if not user.is_active:
        # A deactivated account keeps its Telegram link, so sign-in would
        # otherwise hand out a working token for a banned user.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )
    return Token(access_token=create_access_token(user.user_id))
