from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CoinTransaction, CoinTransactionType, User

WELCOME_BONUS_TYPE_NAME = "admin_adjustment"


def grant_welcome_bonus(db: Session, user: User) -> None:
    amount = settings.welcome_bonus_coins
    if amount <= 0:
        return
    type_id = db.execute(
        select(CoinTransactionType.type_id).where(
            CoinTransactionType.type_name == WELCOME_BONUS_TYPE_NAME
        )
    ).scalar_one_or_none()
    if type_id is None:
        return
    db.flush()
    user.coin_balance = amount
    db.add(
        CoinTransaction(
            user_id=user.user_id,
            type_id=type_id,
            amount=amount,
            balance_after=amount,
        )
    )
