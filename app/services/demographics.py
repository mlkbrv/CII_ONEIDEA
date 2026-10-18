from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CoinTransaction, CoinTransactionType, User

GENDERS = ("male", "female", "undisclosed")
ANSWERED = "answered"
SKIPPED = "skipped"
BONUS_TYPE_NAME = "admin_adjustment"

MAX_AGE = 100
MIN_AGE = 5

AGE_GROUPS = (
    ("under_18", 0, 17),
    ("18_24", 18, 24),
    ("25_34", 25, 34),
    ("35_44", 35, 44),
    ("45_plus", 45, 200),
)


def current_year() -> int:
    return datetime.now(timezone.utc).year


def valid_birth_years() -> range:
    year = current_year()
    return range(year - MAX_AGE, year - MIN_AGE + 1)


def age_of(birth_year: int | None) -> int | None:
    if birth_year is None:
        return None
    return current_year() - birth_year


def age_group(birth_year: int | None) -> str | None:
    age = age_of(birth_year)
    if age is None:
        return None
    for name, low, high in AGE_GROUPS:
        if low <= age <= high:
            return name
    return None


def stats(db: Session) -> dict:
    """Gender, age-group and answer counts over every user, for the dashboard."""
    statuses = dict(db.execute(select(User.demographics_status, func.count()).group_by(User.demographics_status)).all())

    gender = {name: 0 for name in (*GENDERS, "unknown")}
    for value, count in db.execute(select(User.gender, func.count()).group_by(User.gender)).all():
        gender[value if value in GENDERS else "unknown"] += count

    groups = {name: 0 for name, _, _ in AGE_GROUPS}
    groups["unknown"] = 0
    for birth_year, count in db.execute(select(User.birth_year, func.count()).group_by(User.birth_year)).all():
        groups[age_group(birth_year) or "unknown"] += count

    average_birth_year = db.scalar(select(func.avg(User.birth_year)))
    return {
        "answered": statuses.get(ANSWERED, 0),
        "skipped": statuses.get(SKIPPED, 0),
        "not_asked": statuses.get(None, 0),
        "gender": gender,
        "age_groups": groups,
        "average_age": None if average_birth_year is None else round(current_year() - float(average_birth_year), 1),
    }


def skip(db: Session, user: User) -> None:
    if user.demographics_status is None:
        user.demographics_status = SKIPPED
        db.commit()


def submit(db: Session, user: User, gender: str | None, birth_year: int | None) -> int:
    """Store the answers and return the bonus paid (0 when already paid)."""
    if gender is not None:
        user.gender = gender
    if birth_year is not None:
        user.birth_year = birth_year

    first_time = user.demographics_status != ANSWERED
    user.demographics_status = ANSWERED

    bonus = settings.demographics_bonus_coins if first_time else 0
    if bonus > 0:
        _pay_bonus(db, user, bonus)
    db.commit()
    return bonus


def _pay_bonus(db: Session, user: User, amount: int) -> None:
    type_id = db.execute(
        select(CoinTransactionType.type_id).where(
            CoinTransactionType.type_name == BONUS_TYPE_NAME
        )
    ).scalar_one_or_none()
    if type_id is None:
        return
    user.coin_balance = user.coin_balance + amount
    db.add(
        CoinTransaction(
            user_id=user.user_id,
            type_id=type_id,
            amount=amount,
            balance_after=user.coin_balance,
        )
    )
