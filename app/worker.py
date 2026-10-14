"""
The background process: `python -m app.worker`.

Everything that happens on a clock rather than in response to a request lives
here — finishing expired battles, warning players that theirs is about to end,
running the Telegram bot, and pushing queued notifications.

Why a separate process and not the API's lifespan:

  * The sweeper and the reminder sweep must run exactly once per interval.
    Inside the API they would run once per uvicorn worker, so scaling the API
    past one process would finalise every battle two or three times over —
    the completion transaction is guarded and would not pay twice, but the
    reminders and the wasted contention are real.
  * aiogram long-polls a single connection. Two API workers would mean two
    bots fighting over the same updates, and Telegram hands each update to
    whoever asks first.
  * The API stays a request/response service that can be restarted, scaled or
    rolled without dropping a battle mid-completion.

Threading: the ORM is synchronous, so the two sweeps run in daemon threads
while the bot owns the event loop. Nothing is shared between them but the
database, and every unit of work is its own transaction.
"""
import asyncio
import logging
import signal
import threading

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo

from app.bot.delivery import run_delivery_loop
from app.bot.handlers import router as bot_router
from app.core.config import settings
from app.services.competition_expiration import run_expiration_sweeper
from app.services.reminders import sweep_ending_soon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("cci.worker")

# The command list Telegram shows in the chat's menu, per language. Telegram
# stores one list per language_code and falls back to the default (None) for
# anything not listed, which is why the Russian set is registered twice.
COMMANDS = {
    None: [
        ("start", "Открыть Cola Fest"),
        ("redeem", "Активировать код с крышки"),
        ("me", "Баланс и серия побед"),
    ],
    "ru": [
        ("start", "Открыть Cola Fest"),
        ("redeem", "Активировать код с крышки"),
        ("me", "Баланс и серия побед"),
    ],
    "en": [
        ("start", "Open Cola Fest"),
        ("redeem", "Redeem a code from a cap"),
        ("me", "Balance and winning streak"),
    ],
    "az": [
        ("start", "Cola Fest-i aç"),
        ("redeem", "Qapaqdakı kodu aktivləşdir"),
        ("me", "Balans və qalibiyyət seriyası"),
    ],
}


async def _register_commands(bot: Bot) -> None:
    """Publish the command menu in every language we speak."""
    for language_code, commands in COMMANDS.items():
        await bot.set_my_commands(
            [BotCommand(command=name, description=text) for name, text in commands],
            language_code=language_code,
        )
    logger.info("Command menu published in %d language(s)", len(COMMANDS) - 1)


def run_reminder_sweeper(stop_event: threading.Event, interval_seconds: int) -> None:
    """Queue "ending soon" notifications until asked to stop.

    Mirrors run_expiration_sweeper's shape: a failed pass is logged and the
    loop continues, because one bad sweep must not stop every future reminder.
    """
    logger.info("Reminder sweeper started (every %ss)", interval_seconds)
    while not stop_event.is_set():
        try:
            sent = sweep_ending_soon(settings.competition_reminder_minutes)
            if sent:
                logger.info("Queued %d ending-soon reminder(s)", sent)
        except Exception:
            logger.exception("Reminder sweep failed")
        stop_event.wait(interval_seconds)
    logger.info("Reminder sweeper stopped")


async def run_bot(stop_event: threading.Event) -> None:
    """Long-poll Telegram and drain the notification queue alongside it."""
    token = settings.telegram_bot_token.strip()
    if not token:
        # A worker with no bot token is still useful: it finalises battles and
        # queues notifications, which simply wait in the database until a
        # token is configured and it restarts.
        logger.warning("TELEGRAM_BOT_TOKEN is empty — running without the bot")
        while not stop_event.is_set():
            await asyncio.sleep(1)
        return

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        me = await bot.get_me()
        logger.info("Telegram bot authorised as @%s", me.username)

        await _register_commands(bot)
        await _configure_menu_button(bot)

        # Drop anything queued while the worker was down: a stale "your battle
        # ends in 10 minutes" for a battle that finished an hour ago is worse
        # than no message. Real notifications live in the database and are
        # delivered by the loop below, not by this update queue.
        await bot.delete_webhook(drop_pending_updates=True)

        dispatcher = Dispatcher()
        dispatcher.include_router(bot_router)

        delivery = asyncio.create_task(
            run_delivery_loop(bot, settings.notification_poll_interval_seconds)
        )
        try:
            await dispatcher.start_polling(bot, handle_signals=False)
        finally:
            delivery.cancel()
            await asyncio.gather(delivery, return_exceptions=True)
    finally:
        await bot.session.close()


async def _configure_menu_button(bot: Bot) -> None:
    """Point the chat's menu button at the Mini App.

    Done on every start so the deployed URL is always the one Telegram opens —
    otherwise changing the domain means silently sending players to the old one
    until somebody remembers to update BotFather by hand.
    """
    url = settings.telegram_webapp_url.strip()
    if not url:
        logger.warning("TELEGRAM_WEBAPP_URL is empty — no Mini App button will appear")
        return
    if not url.startswith("https://"):
        logger.warning("TELEGRAM_WEBAPP_URL must be https, got %s", url)
        return

    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Cola Fest", web_app=WebAppInfo(url=url))
        )
        logger.info("Menu button points at %s", url)
    except TelegramBadRequest:
        # Telegram rejects URLs it cannot resolve. Not fatal: the bot still
        # works, and the inline button in /start covers the same ground.
        logger.warning("Telegram rejected the Mini App URL: %s", url)


async def main() -> None:
    stop_event = threading.Event()

    threads = [
        threading.Thread(
            target=run_expiration_sweeper,
            args=(stop_event, settings.auto_complete_interval_seconds),
            name="competition-expiration",
            daemon=True,
        ),
        threading.Thread(
            target=run_reminder_sweeper,
            args=(stop_event, settings.auto_complete_interval_seconds),
            name="competition-reminders",
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    loop = asyncio.get_running_loop()
    shutdown = asyncio.Event()

    def request_shutdown() -> None:
        logger.info("Shutdown requested")
        stop_event.set()
        shutdown.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_shutdown)
        except NotImplementedError:
            # Windows has no add_signal_handler; the container runs Linux, and
            # locally Ctrl+C still raises KeyboardInterrupt below.
            signal.signal(sig, lambda *_: request_shutdown())

    bot_task = asyncio.create_task(run_bot(stop_event))
    await asyncio.wait(
        [bot_task, asyncio.create_task(shutdown.wait())],
        return_when=asyncio.FIRST_COMPLETED,
    )

    stop_event.set()
    bot_task.cancel()
    await asyncio.gather(bot_task, return_exceptions=True)
    for thread in threads:
        thread.join(timeout=settings.auto_complete_interval_seconds + 5)
    logger.info("Worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
