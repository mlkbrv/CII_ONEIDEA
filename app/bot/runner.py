import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.bot.handlers import router
from app.core.config import get_settings

logger = logging.getLogger("cci.bot")

_polling_task: asyncio.Task[None] | None = None
_bot: Bot | None = None


async def run_polling() -> None:
    global _bot
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    _bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    me = await _bot.get_me()
    logger.info("Telegram bot authorized as @%s", me.username)
    await _bot.delete_webhook(drop_pending_updates=True)
    dp = Dispatcher()
    dp.include_router(router)
    webapp_url = settings.telegram_webapp_url.strip()
    if webapp_url.startswith("https://"):
        try:
            await _bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="CCI",
                    web_app=WebAppInfo(url=webapp_url),
                )
            )
            logger.info("Menu button URL set to %s", webapp_url)
        except TelegramBadRequest:
            logger.warning("Menu button URL rejected by Telegram: %s", webapp_url)
    elif webapp_url:
        logger.warning("TELEGRAM_WEBAPP_URL must be https://..., got %s", webapp_url)
    try:
        logger.info("Starting Telegram polling")
        await dp.start_polling(_bot, handle_signals=False)
    finally:
        await _bot.session.close()
        _bot = None


def _on_polling_done(task: asyncio.Task[None]) -> None:
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        return
    if exc is not None:
        logger.exception("Telegram polling crashed", exc_info=exc)


async def start_polling_task() -> None:
    global _polling_task
    settings = get_settings()
    if not settings.telegram_bot_token.strip() or not settings.bot_polling:
        logger.warning("Telegram bot not started: TELEGRAM_BOT_TOKEN empty or BOT_POLLING=false")
        return
    _polling_task = asyncio.create_task(run_polling())
    _polling_task.add_done_callback(_on_polling_done)


async def stop_polling_task() -> None:
    global _polling_task
    if _polling_task is None:
        return
    _polling_task.cancel()
    try:
        await _polling_task
    except asyncio.CancelledError:
        pass
    _polling_task = None
