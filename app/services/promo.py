import hashlib
import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.promo import PromoCode

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 10


def normalize_promo_code(code: str) -> str:
    return code.strip().upper().replace("-", "").replace(" ", "")


def hash_promo_code(code: str, pepper: str | None = None) -> str:
    normalized = normalize_promo_code(code)
    secret = get_settings().promo_code_pepper if pepper is None else pepper
    payload = f"{secret}:{normalized}" if secret else normalized
    return hashlib.sha256(payload.encode()).hexdigest()


def generate_plain_code(length: int = CODE_LENGTH) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


async def create_promo_code_batch(
    session: AsyncSession,
    *,
    count: int,
    coin_reward: int,
    expires_at: datetime | None = None,
    code_length: int = CODE_LENGTH,
) -> list[str]:
    if count < 1:
        raise ValueError("count must be >= 1")
    if coin_reward < 1:
        raise ValueError("coin_reward must be >= 1")
    if code_length < 6:
        raise ValueError("code_length must be >= 6")

    plain_codes: list[str] = []
    hash_to_code: dict[str, str] = {}
    while len(hash_to_code) < count:
        code = generate_plain_code(code_length)
        code_hash = hash_promo_code(code)
        if code_hash in hash_to_code:
            continue
        hash_to_code[code_hash] = code

    existing = (
        await session.scalars(
            select(PromoCode.code_hash).where(PromoCode.code_hash.in_(list(hash_to_code)))
        )
    ).all()
    for code_hash in existing:
        hash_to_code.pop(code_hash, None)

    while len(hash_to_code) < count:
        code = generate_plain_code(code_length)
        code_hash = hash_promo_code(code)
        if code_hash in hash_to_code:
            continue
        exists = await session.scalar(select(PromoCode.id).where(PromoCode.code_hash == code_hash))
        if exists is not None:
            continue
        hash_to_code[code_hash] = code

    rows = [
        PromoCode(code_hash=code_hash, coin_reward=coin_reward, expires_at=expires_at)
        for code_hash in hash_to_code
    ]
    session.add_all(rows)
    await session.commit()
    for code_hash, code in hash_to_code.items():
        plain_codes.append(code)
    return plain_codes
