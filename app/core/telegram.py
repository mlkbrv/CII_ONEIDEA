"""
Telegram identity verification.

Telegram does not give us a token to introspect — it gives us a blob of
key=value pairs signed with a key derived from the bot token. Because only
Telegram and we know that token, a valid signature IS the proof of identity:
there is no callback to Telegram and no network request in this module.

Two blobs, two derivations, same idea:

  Mini App (`initData`, WebApp)
      secret = HMAC_SHA256(key="WebAppData", msg=bot_token)
      the user object arrives as a JSON string under the "user" key

  Login Widget (browser / PWA mode)
      secret = SHA256(bot_token)
      the user fields arrive flat: id, first_name, last_name, username

In both cases the signature covers a "data check string": every field
except `hash`, sorted by key, joined with newlines. Sorting matters — the
sender and the verifier must build the identical string or the HMAC differs.

`auth_date` is checked against the clock as well as the signature. A
signature stays valid forever, so without a freshness check a leaked
initData string would be a permanent credential.
"""
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl

from app.core.config import settings

# Clock skew we tolerate on auth_date being in the future. Telegram's clock
# and ours are both NTP-synced, so anything beyond this is not skew.
_FUTURE_SKEW_SECONDS = 60


class TelegramAuthError(Exception):
    """Base for every rejection in this module."""


class InvalidInitDataError(TelegramAuthError):
    """Signature did not verify, or the payload was malformed."""


class ExpiredInitDataError(TelegramAuthError):
    """Signature verified, but the data is older than the allowed age."""


class TelegramNotConfiguredError(TelegramAuthError):
    """No bot token on this deployment, so nothing can be verified."""


@dataclass(frozen=True)
class TelegramUser:
    """The subset of Telegram's user object we actually store."""

    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None


def validate_init_data(init_data: str) -> TelegramUser:
    """Verify a Telegram Mini App `initData` string. Raises on any problem."""
    parsed = _parse_and_verify(
        init_data,
        secret_key=hmac.new(
            b"WebAppData", _bot_token().encode(), hashlib.sha256
        ).digest(),
    )

    # The Mini App nests the user in a JSON string; the Login Widget does not.
    try:
        raw_user: dict[str, Any] = json.loads(parsed["user"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidInitDataError("initData carries no usable user object") from exc

    return _to_user(raw_user)


def validate_login_widget_data(fields: dict[str, str]) -> TelegramUser:
    """Verify a Telegram Login Widget payload (browser / PWA mode).

    Same signature scheme as initData with a different secret derivation,
    and the user fields are flat rather than nested under "user".
    """
    parsed = _parse_and_verify(
        fields,
        secret_key=hashlib.sha256(_bot_token().encode()).digest(),
    )
    return _to_user(parsed)


def _bot_token() -> str:
    token = settings.telegram_bot_token.strip()
    if not token:
        raise TelegramNotConfiguredError("TELEGRAM_BOT_TOKEN is not set")
    return token


def _parse_and_verify(
    payload: str | dict[str, str], secret_key: bytes
) -> dict[str, str]:
    """Shared path: split off `hash`, rebuild the data check string, compare,
    then check freshness. Returns the verified fields without `hash`."""
    if isinstance(payload, str):
        try:
            fields = dict(parse_qsl(payload, keep_blank_values=True))
        except ValueError as exc:
            raise InvalidInitDataError("Malformed Telegram payload") from exc
    else:
        fields = dict(payload)

    received_hash = fields.pop("hash", None)
    if not received_hash:
        raise InvalidInitDataError("Telegram payload carries no hash")

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(fields.items())
    )
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    # compare_digest, not ==, so a wrong hash always costs the same time and
    # cannot be guessed byte by byte from timing.
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise InvalidInitDataError("Telegram signature does not verify")

    _check_freshness(fields)
    return fields


def _check_freshness(fields: dict[str, str]) -> None:
    try:
        auth_date = int(fields["auth_date"])
    except (KeyError, ValueError) as exc:
        raise InvalidInitDataError("Telegram payload carries no auth_date") from exc

    now = int(datetime.now(UTC).timestamp())
    if now - auth_date > settings.telegram_init_data_max_age_seconds:
        raise ExpiredInitDataError("Telegram payload has expired")
    if auth_date - now > _FUTURE_SKEW_SECONDS:
        raise InvalidInitDataError("Telegram payload is dated in the future")


def _to_user(raw: dict[str, Any]) -> TelegramUser:
    try:
        telegram_id = int(raw["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidInitDataError("Telegram user has no usable id") from exc

    # first_name is the only name Telegram guarantees; username is optional
    # (plenty of accounts have none) and must never be treated as an id.
    first_name = str(raw.get("first_name") or "").strip()
    if not first_name:
        raise InvalidInitDataError("Telegram user has no first_name")

    return TelegramUser(
        id=telegram_id,
        first_name=first_name,
        last_name=_optional_str(raw.get("last_name")),
        username=_optional_str(raw.get("username")),
        photo_url=_optional_str(raw.get("photo_url")),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
