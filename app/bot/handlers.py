from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.core.security import TelegramWebAppUser
from app.services.auth import get_or_create_telegram_user
from app.services.promo_code import (
    PromoCodeAlreadyRedeemedError,
    PromoCodeExpiredError,
    PromoCodeNotFoundError,
    redeem_promo_code,
)

router = Router()


def _webapp_keyboard() -> InlineKeyboardMarkup | None:
    url = get_settings().telegram_webapp_url
    if not url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=url))]
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "CCI Cola Fest\n\n"
        "Открой приложение, чтобы ввести промокод с банки, "
        "или отправь его сюда:\n"
        "/redeem КОД",
        reply_markup=_webapp_keyboard(),
    )


@router.message(Command("redeem"))
async def cmd_redeem(message: Message, command: CommandObject) -> None:
    code = (command.args or "").strip()
    if not code:
        await message.answer("Использование: /redeem КОД")
        return
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return
    telegram_user = TelegramWebAppUser(
        id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name or "User",
        last_name=message.from_user.last_name,
    )
    async with async_session_maker() as session:
        try:
            user = await get_or_create_telegram_user(session, telegram_user)
            result = await redeem_promo_code(session, user, code)
            await session.commit()
        except PromoCodeNotFoundError:
            await session.rollback()
            await message.answer("Промокод не найден.")
            return
        except PromoCodeAlreadyRedeemedError:
            await session.rollback()
            await message.answer("Этот промокод уже использован.")
            return
        except PromoCodeExpiredError:
            await session.rollback()
            await message.answer("Срок действия промокода истёк.")
            return
        except Exception:
            await session.rollback()
            await message.answer("Не удалось активировать код. Попробуй позже.")
            raise
    await message.answer(
        f"Код активирован.\n+{result.coin_reward} монет\nБаланс: {result.balance}"
    )
