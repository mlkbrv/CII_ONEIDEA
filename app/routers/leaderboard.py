"""
Leaderboard — TZ section 17.

The point of a leaderboard here is motivational, not statistical: the winning
streak is what the game asks people to protect (TZ section 13), so it is the
default ranking. Total wins is offered alongside it because a streak rewards
being hot right now, while wins reward having been good all along.

Ranking is done in SQL with row_number(), not in Python, so a caller's rank
is computed against every user rather than only the page that was fetched.
The caller's own row is returned alongside the page (`me`) even when they are
nowhere near the top — a leaderboard you cannot find yourself on gives a new
player nothing to aim at.

Scale note: this is a fest-sized deployment (hundreds of users), so the
ranking runs over the whole users table on each request. If that ever becomes
hot, the fix is a materialised view refreshed on competition completion, not
an index — row_number() has to see every row either way.
"""
import enum
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Competition, User
from app.schemas.profile import Leaderboard, LeaderboardEntry

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


class LeaderboardMetric(str, enum.Enum):
    """What the ranking is by.

    A closed set, so the client cannot pass a column name and order the board
    by something that was never meant to be public — coin balance in
    particular is nobody else's business.
    """

    STREAK = "streak"
    WINS = "wins"


@router.get("", response_model=Leaderboard)
def get_leaderboard(
    metric: LeaderboardMetric = Query(
        default=LeaderboardMetric.STREAK,
        description="streak = current winning streak, wins = competitions won",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Leaderboard:
    ranked = _ranked_users(metric).subquery()

    total = db.execute(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    ).scalar_one()

    page = db.execute(
        select(ranked).order_by(ranked.c.rank).limit(limit).offset(offset)
    ).all()

    # The caller's row comes from the SAME ranking, so their rank is their
    # true position among all users and not an artefact of the page size.
    my_row = db.execute(
        select(ranked).where(ranked.c.user_id == current_user.user_id)
    ).one_or_none()

    return Leaderboard(
        metric=metric.value,
        items=[_to_entry(row, current_user.user_id) for row in page],
        total=total,
        limit=limit,
        offset=offset,
        me=_to_entry(my_row, current_user.user_id) if my_row is not None else None,
    )


def _ranked_users(metric: LeaderboardMetric) -> Select:
    """Every active user with their win count and their rank under `metric`."""
    # Competitions won, counted once here and reused as both a sortable column
    # and a displayed value. LEFT JOIN so someone who has never won still
    # appears, with 0, instead of vanishing from the board.
    wins = (
        select(
            Competition.winner_id.label("user_id"),
            func.count().label("wins"),
        )
        .where(Competition.winner_id.is_not(None))
        .group_by(Competition.winner_id)
        .subquery()
    )

    wins_column = func.coalesce(wins.c.wins, 0)
    order_by = {
        LeaderboardMetric.STREAK: (desc(User.winning_streak), desc(wins_column)),
        LeaderboardMetric.WINS: (desc(wins_column), desc(User.winning_streak)),
    }[metric]

    # username is the final tiebreak so the ordering is total: without it,
    # equally-ranked users could swap places between two requests and paging
    # would show the same person twice or skip someone.
    ordering = (*order_by, User.username)

    return (
        select(
            func.row_number().over(order_by=ordering).label("rank"),
            User.user_id.label("user_id"),
            User.username.label("username"),
            User.profile_picture_url.label("profile_picture_url"),
            User.winning_streak.label("winning_streak"),
            wins_column.label("competitions_won"),
        )
        .select_from(User)
        .outerjoin(wins, wins.c.user_id == User.user_id)
        .where(User.is_active.is_(True))
    )


def _to_entry(row, caller_id: uuid.UUID) -> LeaderboardEntry:
    return LeaderboardEntry(
        rank=row.rank,
        user_id=row.user_id,
        username=row.username,
        profile_picture_url=row.profile_picture_url,
        winning_streak=row.winning_streak,
        competitions_won=row.competitions_won,
        is_self=row.user_id == caller_id,
    )
