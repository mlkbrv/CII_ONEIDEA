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
from aiogram.types import Message
from fastapi import HTTPException

from app.bot.keyboards import webapp_keyboard
from app.core.database import SessionLocal
from app.core.telegram import TelegramUser
from app.routers.qr import redeem_qr
from app.services.i18n import normalise_language, t
from app.services.telegram_auth import get_or_create_telegram_user

logger = logging.getLogger("cci.bot")

router = Router()


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
        first_name=sender.first_name or "Player",
        last_name=sender.last_name,
        username=sender.username,
        language_code=sender.language_code,
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    sender = _telegram_user(message)
    language = _language(sender)
    if sender is not None:
        # Create the account now, so the first notification the player earns
        # has somewhere to go even if they never open the Mini App. The stored
        # language comes back, because an existing account may have chosen a
        # different one in the app than its Telegram client uses.
        language = await asyncio.to_thread(_ensure_account, sender)

    await message.answer(
        t("bot.start", language),
        reply_markup=webapp_keyboard(language=language),
    )


@router.message(Command("redeem"))
async def cmd_redeem(message: Message, command: CommandObject) -> None:
    sender = _telegram_user(message)
    language = _language(sender)

    code = (command.args or "").strip()
    if not code:
        await message.answer(t("bot.redeem_usage", language))
        return

    if sender is None:
        await message.answer(t("bot.no_user", language))
        return

    try:
        result = await asyncio.to_thread(_redeem, sender, code)
    except HTTPException as exc:
        # The shared redemption service speaks HTTP status codes because it is
        # also an endpoint. Translating them here keeps ONE implementation of
        # the redemption rules instead of a second, drifting copy for chat.
        key = {
            404: "bot.code_not_found",
            409: "bot.code_used",
            410: "bot.code_expired",
        }.get(exc.status_code, "bot.code_failed")
        await message.answer(t(key, language))
        return
    except Exception:
        logger.exception("Redemption failed for telegram id %s", sender.id)
        await message.answer(t("bot.error", language))
        return

    await message.answer(
        t(
            "bot.redeemed",
            result["language"],
            coins=result["coins_earned"],
            balance=result["balance"],
        ),
        reply_markup=webapp_keyboard("bot.spend_coins", result["language"]),
    )


@router.message(Command("me"))
async def cmd_me(message: Message) -> None:
    sender = _telegram_user(message)
    if sender is None:
        await message.answer(t("bot.no_user", _language(None)))
        return

    profile = await asyncio.to_thread(_profile, sender)
    await message.answer(
        t(
            "bot.profile",
            profile["language"],
            username=profile["username"],
            coins=profile["coins"],
            streak=profile["streak"],
        ),
        reply_markup=webapp_keyboard(language=profile["language"]),
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

    language = _language(_telegram_user(message))
    await message.answer(
        t("bot.fallback", language),
        reply_markup=webapp_keyboard(language=language),
    )


# --- Synchronous bits, run in a worker thread ------------------------------


def _language(sender: TelegramUser | None) -> str:
    """The language to answer in before the account has been loaded.

    Telegram's client language is the best guess available at that moment.
    Once a handler has the account it uses the stored preference instead —
    the user may have picked a different language inside the app.
    """
    return normalise_language(sender.language_code if sender else None)


def _ensure_account(sender: TelegramUser) -> str:
    """Create the account if it is new; return the language it reads."""
    with SessionLocal() as db:
        return get_or_create_telegram_user(db, sender).language


def _redeem(sender: TelegramUser, code: str) -> dict:
    with SessionLocal() as db:
        user = get_or_create_telegram_user(db, sender)
        result = redeem_qr(db, code, user)
        return {
            "coins_earned": result.coins_earned,
            "balance": result.balance,
            "language": user.language,
        }


def _profile(sender: TelegramUser) -> dict:
    with SessionLocal() as db:
        user = get_or_create_telegram_user(db, sender)
        return {
            "username": user.username,
            "coins": user.coin_balance,
            "streak": user.winning_streak,
            "language": user.language,
        }
