import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl
from uuid import UUID

import jwt

from app.core.config import get_settings


class AuthError(Exception):
    pass


class InvalidInitDataError(AuthError):
    pass


class ExpiredInitDataError(AuthError):
    pass


@dataclass(frozen=True)
class TelegramWebAppUser:
    id: int
    username: str | None
    first_name: str
    last_name: str | None


def create_access_token(user_id: UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def parse_access_token(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise AuthError("Invalid access token") from exc


def validate_telegram_init_data(init_data: str) -> TelegramWebAppUser:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise AuthError("Telegram auth is not configured")
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    except ValueError as exc:
        raise InvalidInitDataError("Malformed Telegram initData") from exc
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise InvalidInitDataError("Malformed Telegram initData")
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed.items()))
    secret_key = hmac.new(
        b"WebAppData",
        settings.telegram_bot_token.encode(),
        hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise InvalidInitDataError("Invalid Telegram initData")
    try:
        auth_date = int(parsed["auth_date"])
    except (KeyError, ValueError) as exc:
        raise InvalidInitDataError("Malformed Telegram initData") from exc
    now_ts = int(datetime.now(UTC).timestamp())
    if now_ts - auth_date > settings.telegram_init_data_max_age_seconds:
        raise ExpiredInitDataError("Telegram initData expired")
    if now_ts + 60 < auth_date:
        raise InvalidInitDataError("Invalid Telegram initData")
    try:
        raw_user: dict[str, Any] = json.loads(parsed["user"])
        return TelegramWebAppUser(
            id=int(raw_user["id"]),
            username=raw_user.get("username"),
            first_name=str(raw_user["first_name"]),
            last_name=raw_user.get("last_name"),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InvalidInitDataError("Malformed Telegram initData") from exc
