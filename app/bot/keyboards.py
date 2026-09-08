"""
Inline keyboards the bot attaches to its messages.

Its own module because both the command handlers and the notification
delivery loop need the same button, and importing it from handlers into
delivery would make the two import each other.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.core.config import settings
from app.services.i18n import t


def webapp_keyboard(
    key: str = "bot.open_app", language: str | None = None
) -> InlineKeyboardMarkup | None:
    """The button that opens the Mini App, or None if no URL is configured.

    Telegram rejects a web_app button whose URL is not https and fails the
    whole message with it — so a missing or http URL means no button rather
    than an undelivered notification.
    """
    url = settings.telegram_webapp_url.strip()
    if not url.startswith("https://"):
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(key, language), web_app=WebAppInfo(url=url))]
        ]
    )
