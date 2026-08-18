import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.bot.handlers import router
from app.core.config import get_settings

_polling_task: asyncio.Task[None] | None = None
_bot: Bot | None = None


async def run_polling() -> None:
    global _bot
    settings = get_settings()
    _bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)
    if settings.telegram_webapp_url:
        await _bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="CCI",
                web_app=WebAppInfo(url=settings.telegram_webapp_url),
            )
        )
    try:
        await dp.start_polling(_bot, handle_signals=False)
    finally:
        await _bot.session.close()
        _bot = None


async def start_polling_task() -> None:
    global _polling_task
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.bot_polling:
        return
    _polling_task = asyncio.create_task(run_polling())


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
