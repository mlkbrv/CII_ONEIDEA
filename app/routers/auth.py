from fastapi import APIRouter, HTTPException, status

from app.core.security import (
    AuthError,
    ExpiredInitDataError,
    InvalidInitDataError,
    create_access_token,
    validate_telegram_init_data,
)
from app.dependencies.auth import SessionDep
from app.schemas.auth import TelegramAuthRequest, TokenResponse
from app.services.auth import get_or_create_telegram_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram", response_model=TokenResponse)
async def login_telegram(payload: TelegramAuthRequest, session: SessionDep) -> TokenResponse:
    try:
        telegram_user = validate_telegram_init_data(payload.init_data)
    except ExpiredInitDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram initData expired",
        ) from exc
    except InvalidInitDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initData",
        ) from exc
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram auth is not configured",
        ) from exc
    user = await get_or_create_telegram_user(session, telegram_user)
    return TokenResponse(access_token=create_access_token(user.id), user_id=user.id)
