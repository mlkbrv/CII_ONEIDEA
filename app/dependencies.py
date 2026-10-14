"""
Reusable auth dependencies.

get_current_user is the gatekeeper for protected endpoints. It reads the
Authorization: Bearer <token> header, validates the JWT, and loads the
user. Any endpoint that needs a logged-in user just declares:

    current_user: User = Depends(get_current_user)
"""
import uuid

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.jwt import decode_access_token
from app.core.telegram import TelegramAuthError, validate_init_data
from app.models import User
from app.services.telegram_auth import get_or_create_telegram_user

# Extracts the Bearer token from the request's Authorization header, and
# powers Swagger's "Authorize" button (tokenUrl points at the login endpoint).
# auto_error=False because a missing Bearer token is not necessarily an
# error here — it may be a Mini App request using the "tma" scheme below.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

# Authorization scheme the Telegram Mini App uses to send raw initData
# instead of a JWT (`Authorization: tma <initData>`).
TELEGRAM_SCHEME = "tma"


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the caller, from either a JWT or raw Telegram initData.

    Two credentials are accepted on the same header:

        Authorization: Bearer <jwt>       normal, after any /auth/* login
        Authorization: tma <initData>     Telegram Mini App, no login round-trip

    The `tma` path exists because initData is already a signed, short-lived
    credential; making the Mini App exchange it for a JWT before every cold
    start would add a round-trip and buy nothing. It creates the account on
    first contact, exactly like POST /auth/telegram.
    """
    if token is not None:
        return _user_from_jwt(db, token)

    if authorization:
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() == TELEGRAM_SCHEME and credentials:
            return _user_from_init_data(db, credentials)

    raise _credentials_exception()


def _user_from_jwt(db: Session, token: str) -> User:
    try:
        user_id = uuid.UUID(decode_access_token(token))
    except (jwt.InvalidTokenError, ValueError):
        raise _credentials_exception()

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _credentials_exception()

    return user


def _user_from_init_data(db: Session, init_data: str) -> User:
    try:
        telegram_user = validate_init_data(init_data)
    except TelegramAuthError:
        # Includes "the server has no bot token": from the caller's side an
        # unverifiable credential is an unusable one either way, and the
        # dedicated /auth/telegram endpoint reports the 503 for operators.
        raise _credentials_exception()

    user = get_or_create_telegram_user(db, telegram_user)
    if not user.is_active:
        raise _credentials_exception()

    return user


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Admin gate. Every /admin/* endpoint depends on this, AFTER
    get_current_user(), so the chain is exactly:

        JWT -> get_current_user() -> 401 if bad
                                   -> is_admin? -> 403 if not

    'is_admin' comes from the users table — the JWT carries only the user
    id, so there is nothing a client can put in a token to bypass this.
    Normal authenticated users get HTTP 403 Forbidden; unauthenticated
    (or bad-token) requests already got 401 from get_current_user().
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform administrative actions",
        )
    return current_user