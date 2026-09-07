"""
Bot commands.

The bot is deliberately thin (TZ section 17: "the bot handles communication
and notifications, the Mini App contains the game"). It opens the app, and it
handles the two things a player might reasonably want to do from a chat
without opening anything: redeem a code and check their balance.

Every handler reuses the same service layer the HTTP API uses — redemption
goes through the identical locked transaction as POST /qr/redeem — so a code
redeemed in chat and one redeemed in the app cannot behave differently.

DB work runs through asyncio.to_thread: the ORM is synchronous, and calling it
directly from a handler would block the event loop, stalling every other
update the bot is processing.
"""
import asyncio
import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.telegram import TelegramUser
from app.routers.qr import redeem_qr
from app.services.telegram_auth import get_or_create_telegram_user

logger = logging.getLogger("cci.bot")

router = Router()


def webapp_keyboard(text: str = "Открыть Cola Fest") -> InlineKeyboardMarkup | None:
    """The button that opens the Mini App, or None if no URL is configured.

    Telegram rejects a web_app button whose URL is not https, and it would
    take the whole message down with it — so a missing or http URL means no
    button rather than a failed send.
    """
    url = settings.telegram_webapp_url.strip()
    if not url.startswith("https://"):
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))]]
    )


def _telegram_user(message: Message) -> TelegramUser | None:
    """The sender as our own identity type.

    Nothing is verified here and nothing needs to be: this update arrived over
    the bot's authenticated connection to Telegram, so `from_user` is
    Telegram's own word for who sent it — the same guarantee initData's
    signature provides on the Mini App side.
    """
    sender = message.from_user
    if sender is None:
        return None
    return TelegramUser(
        id=sender.id,
        first_name=sender.first_name or "Игрок",
        last_name=sender.last_name,
        username=sender.username,
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    sender = _telegram_user(message)
    if sender is not None:
        # Create the account now, so the first notification the player earns
        # has somewhere to go even if they never open the Mini App.
        await asyncio.to_thread(_ensure_account, sender)

    await message.answer(
        "🐻‍❄️ <b>Cola Fest</b>\n\n"
        "Покупай Coca-Cola, вводи код с крышки и получай монеты.\n"
        "Одевай своего медведя, вызывай друзей на баттл образов "
        "и забирай призовой фонд.\n\n"
        "Открой приложение или отправь код прямо сюда:\n"
        "<code>/redeem КОД</code>",
        reply_markup=webapp_keyboard(),
    )


@router.message(Command("redeem"))
async def cmd_redeem(message: Message, command: CommandObject) -> None:
    code = (command.args or "").strip()
    if not code:
        await message.answer("Использование: <code>/redeem КОД</code>")
        return

    sender = _telegram_user(message)
    if sender is None:
        await message.answer("Не удалось определить пользователя.")
        return

    try:
        result = await asyncio.to_thread(_redeem, sender, code)
    except HTTPException as exc:
        # The shared redemption service speaks HTTP status codes because it is
        # also an endpoint. Translating them here keeps ONE implementation of
        # the redemption rules instead of a second, drifting copy for chat.
        await message.answer(
            {
                404: "Код не найден. Проверь, что ввёл его правильно.",
                409: "Этот код уже использован.",
                410: "Срок действия кода истёк.",
            }.get(exc.status_code, "Не удалось активировать код. Попробуй позже."),
        )
        return
    except Exception:
        logger.exception("Redemption failed for telegram id %s", sender.id)
        await message.answer("Что-то пошло не так. Попробуй ещё раз через минуту.")
        return

    await message.answer(
        f"✅ Код активирован!\n"
        f"+{result['coins_earned']} монет\n"
        f"Баланс: <b>{result['balance']}</b>",
        reply_markup=webapp_keyboard("Потратить монеты"),
    )


@router.message(Command("me"))
async def cmd_me(message: Message) -> None:
    sender = _telegram_user(message)
    if sender is None:
        await message.answer("Не удалось определить пользователя.")
        return

    profile = await asyncio.to_thread(_profile, sender)
    await message.answer(
        f"👤 <b>{profile['username']}</b>\n"
        f"💰 Монет: {profile['coins']}\n"
        f"🔥 Серия побед: {profile['streak']}",
        reply_markup=webapp_keyboard(),
    )


@router.message()
async def fallback(message: Message) -> None:
    """Anything else — a code pasted on its own is the common case.

    People paste the code without the command far more often than they get the
    command right, so a bare token that looks like a code is treated as one
    rather than answered with a menu.
    """
    text = (message.text or "").strip()
    if text and len(text.split()) == 1 and 4 <= len(text) <= 64:
        await cmd_redeem(message, CommandObject(command="redeem", args=text))
        return

    await message.answer(
        "Открой приложение, чтобы играть, или отправь код с крышки.",
        reply_markup=webapp_keyboard(),
    )


# --- Synchronous bits, run in a worker thread ------------------------------


def _ensure_account(sender: TelegramUser) -> None:
    with SessionLocal() as db:
        get_or_create_telegram_user(db, sender)


def _redeem(sender: TelegramUser, code: str) -> dict:
    with SessionLocal() as db:
        user = get_or_create_telegram_user(db, sender)
        result = redeem_qr(db, code, user)
        return {"coins_earned": result.coins_earned, "balance": result.balance}


def _profile(sender: TelegramUser) -> dict:
    with SessionLocal() as db:
        user = get_or_create_telegram_user(db, sender)
        return {
            "username": user.username,
            "coins": user.coin_balance,
            "streak": user.winning_streak,
        }
