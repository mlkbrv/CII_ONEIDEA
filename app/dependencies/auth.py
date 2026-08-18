from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import (
    AuthError,
    ExpiredInitDataError,
    InvalidInitDataError,
    parse_access_token,
    validate_telegram_init_data,
)
from app.models.user import User
from app.services.auth import get_or_create_telegram_user

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    x_telegram_init_data: Annotated[str | None, Header()] = None,
) -> User:
    if authorization:
        scheme, _, credentials = authorization.partition(" ")
        scheme_l = scheme.lower()
        if not credentials:
            raise _unauthorized("Not authenticated")
        if scheme_l == "bearer":
            try:
                user_id: UUID = parse_access_token(credentials)
            except AuthError as exc:
                raise _unauthorized("Invalid access token") from exc
            user = await session.get(User, user_id)
            if user is None:
                raise _unauthorized("Invalid access token")
            return user
        if scheme_l == "tma":
            return await _user_from_init_data(session, credentials)
        raise _unauthorized("Unsupported authorization scheme")
    if x_telegram_init_data:
        return await _user_from_init_data(session, x_telegram_init_data)
    raise _unauthorized("Not authenticated")


async def _user_from_init_data(session: AsyncSession, init_data: str) -> User:
    try:
        telegram_user = validate_telegram_init_data(init_data)
    except ExpiredInitDataError as exc:
        raise _unauthorized("Telegram initData expired") from exc
    except InvalidInitDataError as exc:
        raise _unauthorized("Invalid Telegram initData") from exc
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram auth is not configured",
        ) from exc
    return await get_or_create_telegram_user(session, telegram_user)


CurrentUser = Annotated[User, Depends(get_current_user)]
