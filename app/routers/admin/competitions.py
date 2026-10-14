"""
Admin battle monitoring — every competition, not just the caller's own.

Covers:
  GET /admin/competitions           paginated list, newest first, with
                                    status filter + participant username search
  GET /admin/competitions/{id}      detail, including both outfits

Read-only by design. Competitions are created by the challenge/accept flow
(routers/competition_requests.py) and finished by the sweeper or the
participants' own /complete call (routers/competitions.py); an admin
override to force-start, force-finish, or delete one would duplicate that
state machine here and risk disagreeing with it. What an operator actually
needs is visibility — is a battle stuck, is the prize pool what it should
be, does the vote count match what a player is reporting — which this gives
without adding a second way to mutate the same rows.

Deliberately its own small AdminCompetitionRead/_vote_breakdown rather than
importing the public router's (app/routers/competitions.py) versions: those
carry an underscore-prefixed "private to this module" convention, and the
admin shape needs a username on each side (for a search/link target) that
the public UserPublic-embedding shape does not.
"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased, joinedload

from app.core.database import get_db
from app.dependencies import get_current_admin
from app.models import Competition, CompetitionStatus, User, Vote
from app.routers.users import escape_like
from app.schemas.admin_competition import (
    AdminCompetitionDetail,
    AdminCompetitionList,
    AdminCompetitionParticipant,
    AdminCompetitionRead,
)
from app.services.profiles import load_avatar

router = APIRouter(tags=["admin"])

AdminCompetitionStatusFilter = Literal["active", "completed"]


@router.get("", response_model=AdminCompetitionList)
def list_competitions(
    status_filter: AdminCompetitionStatusFilter | None = Query(
        default=None,
        alias="status",
        description="Only return competitions in this status",
    ),
    q: str | None = Query(
        default=None,
        max_length=50,
        description="Search fragment for either participant's username",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> AdminCompetitionList:
    Challenger = aliased(User)
    Opponent = aliased(User)

    query = (
        select(Competition)
        .join(Challenger, Competition.challenger_id == Challenger.user_id)
        .join(Opponent, Competition.opponent_id == Opponent.user_id)
        .options(
            joinedload(Competition.challenger),
            joinedload(Competition.opponent),
            joinedload(Competition.status),
        )
    )

    if status_filter is not None:
        query = query.join(CompetitionStatus).where(
            CompetitionStatus.status_name == status_filter
        )
    if q:
        pattern = f"%{escape_like(q.strip())}%"
        query = query.where(
            or_(
                Challenger.username.ilike(pattern, escape="\\"),
                Opponent.username.ilike(pattern, escape="\\"),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery()))

    rows = db.execute(
        query.order_by(Competition.created_at.desc(), Competition.competition_id.desc())
        .limit(limit)
        .offset(offset)
    ).unique().scalars().all()

    breakdown = _vote_breakdown(db, [c.competition_id for c in rows])
    return AdminCompetitionList(
        items=[_to_admin_read(c, breakdown) for c in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{competition_id}", response_model=AdminCompetitionDetail)
def get_competition(
    competition_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> AdminCompetitionDetail:
    competition = db.execute(
        select(Competition)
        .where(Competition.competition_id == competition_id)
        .options(
            joinedload(Competition.challenger),
            joinedload(Competition.opponent),
            joinedload(Competition.status),
        )
    ).scalar_one_or_none()
    if competition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Competition not found"
        )

    breakdown = _vote_breakdown(db, [competition.competition_id])
    base = _to_admin_read(competition, breakdown)
    return AdminCompetitionDetail(
        **base.model_dump(),
        challenger_avatar=load_avatar(db, competition.challenger_id),
        opponent_avatar=load_avatar(db, competition.opponent_id),
    )


def _vote_breakdown(
    db: Session, competition_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[uuid.UUID, int]]:
    """Votes per participant, for a whole page of competitions at once —
    same shape and same reasoning as the public router's version: one
    grouped query beats one round trip per row on a page."""
    if not competition_ids:
        return {}
    rows = db.execute(
        select(Vote.competition_id, Vote.voted_for_user_id, func.count())
        .where(Vote.competition_id.in_(competition_ids))
        .group_by(Vote.competition_id, Vote.voted_for_user_id)
    ).all()
    breakdown: dict[uuid.UUID, dict[uuid.UUID, int]] = {}
    for competition_id, voted_for, count in rows:
        breakdown.setdefault(competition_id, {})[voted_for] = count
    return breakdown


def _to_admin_read(
    competition: Competition,
    breakdown: dict[uuid.UUID, dict[uuid.UUID, int]],
) -> AdminCompetitionRead:
    scores = breakdown.get(competition.competition_id, {})
    return AdminCompetitionRead(
        competition_id=competition.competition_id,
        status=competition.status.status_name,
        challenger=AdminCompetitionParticipant(
            user_id=competition.challenger_id,
            username=competition.challenger.username,
            votes=scores.get(competition.challenger_id, 0),
        ),
        opponent=AdminCompetitionParticipant(
            user_id=competition.opponent_id,
            username=competition.opponent.username,
            votes=scores.get(competition.opponent_id, 0),
        ),
        winner_id=competition.winner_id,
        prize_pool=competition.prize_pool,
        total_votes=competition.total_votes,
        duration_minutes=competition.duration_minutes,
        start_time=competition.start_time,
        end_time=competition.end_time,
        created_at=competition.created_at,
    )
