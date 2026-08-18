from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coin import CoinTransaction
from app.models.enums import TransactionType
from app.models.promo import PromoCode
from app.models.user import User
from app.services.promo import hash_promo_code, normalize_promo_code


class PromoCodeError(Exception):
    pass


class PromoCodeNotFoundError(PromoCodeError):
    pass


class PromoCodeAlreadyRedeemedError(PromoCodeError):
    pass


class PromoCodeExpiredError(PromoCodeError):
    pass


@dataclass(frozen=True)
class RedeemResult:
    promo_code_id: UUID
    coin_reward: int
    balance: int


async def redeem_promo_code(session: AsyncSession, user: User, code: str) -> RedeemResult:
    code_hash = hash_promo_code(normalize_promo_code(code))
    promo = await session.scalar(
        select(PromoCode).where(PromoCode.code_hash == code_hash).with_for_update()
    )
    if promo is None:
        raise PromoCodeNotFoundError
    if promo.is_redeemed:
        raise PromoCodeAlreadyRedeemedError
    now = datetime.now(UTC)
    expires_at = promo.expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= now:
            raise PromoCodeExpiredError
    locked_user = await session.get(User, user.id, with_for_update=True)
    if locked_user is None:
        raise PromoCodeNotFoundError
    promo.is_redeemed = True
    promo.redeemed_by_user_id = locked_user.id
    promo.redeemed_at = now
    locked_user.coins += promo.coin_reward
    session.add(
        CoinTransaction(
            user_id=locked_user.id,
            amount=promo.coin_reward,
            transaction_type=TransactionType.PROMO_REDEEM,
            reference_id=promo.id,
        )
    )
    await session.flush()
    return RedeemResult(
        promo_code_id=promo.id,
        coin_reward=promo.coin_reward,
        balance=locked_user.coins,
    )
