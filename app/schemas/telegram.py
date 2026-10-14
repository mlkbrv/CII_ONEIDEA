"""
Schemas for the two Telegram sign-in paths.

Both end at the same response (`Token`), so the client stores one JWT and
never has to care which door it came through.
"""
from pydantic import BaseModel, Field


class TelegramInitDataLogin(BaseModel):
    """Body of POST /auth/telegram — the Mini App path.

    `init_data` is the raw, untouched value of `Telegram.WebApp.initData`.
    It must be forwarded byte for byte: the signature covers the exact
    encoding, so re-serialising or re-ordering it invalidates the hash.
    """

    init_data: str = Field(
        min_length=1,
        max_length=8192,
        description="Raw Telegram.WebApp.initData string, unmodified",
    )


class TelegramWidgetLogin(BaseModel):
    """Body of POST /auth/telegram-login — the browser / PWA path.

    The Telegram Login Widget hands JavaScript a flat object (id, first_name,
    auth_date, hash, ...). We take it as-is rather than naming each field,
    because the signature covers every field Telegram chose to send — drop
    one while verifying and the hash no longer matches.
    """

    data: dict[str, str] = Field(
        description="Every field the Telegram Login Widget returned, including hash",
    )
