from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import TelegramWebAppUser
from app.models.enums import AuthProviderType
from app.models.user import AuthProvider, User


def _display_name(telegram_user: TelegramWebAppUser) -> str:
    parts = [telegram_user.first_name]
    if telegram_user.last_name:
        parts.append(telegram_user.last_name)
    return " ".join(parts)[:128]


async def _allocate_username(session: AsyncSession, telegram_user: TelegramWebAppUser) -> str:
    candidates: list[str] = []
    if telegram_user.username:
        candidates.append(telegram_user.username[:64])
    candidates.append(f"tg{telegram_user.id}"[:64])
    for username in candidates:
        taken = await session.scalar(select(User.id).where(User.username == username))
        if taken is None:
            return username
    return f"tg{telegram_user.id}"[:64]


async def get_or_create_telegram_user(
    session: AsyncSession,
    telegram_user: TelegramWebAppUser,
) -> User:
    provider = await session.scalar(
        select(AuthProvider)
        .where(
            AuthProvider.provider == AuthProviderType.TELEGRAM,
            AuthProvider.provider_user_id == str(telegram_user.id),
        )
        .options(selectinload(AuthProvider.user))
    )
    if provider is not None:
        user = provider.user
        user.display_name = _display_name(telegram_user)
        return user
    user = User(
        username=await _allocate_username(session, telegram_user),
        display_name=_display_name(telegram_user),
    )
    session.add(user)
    await session.flush()
    session.add(
        AuthProvider(
            user_id=user.id,
            provider=AuthProviderType.TELEGRAM,
            provider_user_id=str(telegram_user.id),
        )
    )
    await session.flush()
    return user
