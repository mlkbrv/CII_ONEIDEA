"""
Competitions — Phase 6, Parts 2–4. Competition creation happens inside
acceptance (see routers/competition_requests.py); this router owns
retrieval and discovery.

  GET /competitions/{competition_id}   retrieve one competition (200, participant-only)
  GET /competitions                    list the caller's competitions (200)
  GET /competitions/discover           public feed of OTHER users' ACTIVE competitions (200)
  POST /competitions/{id}/complete     manual completion trigger (200, participant-only)

The detail endpoint only lets the challenger or the opponent in (other
authenticated users get 403, unauthenticated get 401). GET /competitions is
participant-scoped too — the caller only ever sees competitions they are in.

GET /competitions/discover is the vote-stage discovery feed: ACTIVE
competitions between two OTHER ACTIVE users, so the authenticated caller can
open (and, in Part 4B, vote on) competitions without being a participant. It
excludes the caller's own competitions (challenger OR opponent — a
participant cannot vote in their own competition), completed competitions,
and competitions whose challenger or opponent account is inactive. Response
uses the wardrobe/clothing-style envelope {items, total, limit, offset},
ordered by end_time ASC (ending soonest first) with a competition_id tiebreak.

The payload is the safe CompetitionRead shape: both participants embed
UserPublic (never password_hash/email/coin_balance/streak/account fields),
status comes from the competition_status lookup row's status_name
("active"/"completed"), winner_id is null until completion is implemented.

Route ordering note: /discover is a STATIC path and MUST be declared before
/{competition_id}, otherwise FastAPI would treat "discover" as a UUID and
reject it with 422.
"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Competition, Follow, User, Vote
from app.schemas.competition import (
    CompetitionDetail,
    CompetitionDiscoverResult,
    CompetitionRead,
)
from app.schemas.user import UserPublic
from app.services.profiles import load_avatar
from app.services.competition_expiration import (
    CompletionOutcome,
    complete_expired_competition,
    resolve_status_id,
)

router = APIRouter(prefix="/competitions", tags=["competitions"])

CompetitionStatusFilter = Literal["active", "completed"]


@router.get("", response_model=list[CompetitionRead])
def list_competitions(
    status: CompetitionStatusFilter | None = Query(
        default=None,
        description="Only return competitions in this status ('active' or 'completed')",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
        description="How many competitions to return (1-50)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="How many competitions to skip before returning results",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CompetitionRead]:
    # Participant-scoped: the caller only ever sees competitions they are in.
    # The user_id comes ONLY from the JWT; there is no client-supplied id.
    query = (
        select(Competition)
        .where(
            or_(
                Competition.challenger_id == current_user.user_id,
                Competition.opponent_id == current_user.user_id,
            )
        )
        .options(
            joinedload(Competition.challenger),
            joinedload(Competition.opponent),
            joinedload(Competition.status),
        )
    )

    if status == "active":
        query = (
            query.where(Competition.status_id == resolve_status_id(db, "active"))
            .order_by(Competition.end_time.asc(), Competition.competition_id.asc())
        )
    elif status == "completed":
        query = (
            query.where(Competition.status_id == resolve_status_id(db, "completed"))
            .order_by(Competition.end_time.desc(), Competition.competition_id.desc())
        )
    else:
        query = query.order_by(
            Competition.created_at.desc(), Competition.competition_id.desc()
        )

    rows = db.execute(query.limit(limit).offset(offset)).scalars().all()
    breakdown = _vote_breakdown(db, [c.competition_id for c in rows])
    return [_to_competition_read(c, breakdown) for c in rows]


CompetitionScope = Literal["all", "following"]


@router.get("/discover", response_model=CompetitionDiscoverResult)
def discover_competitions(
    scope: CompetitionScope = Query(
        default="all",
        description=(
            "'following' limits the feed to battles involving people the "
            "caller follows (the 'Other battles' tab); 'all' shows every "
            "active battle between other users."
        ),
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
        description="How many competitions to return (1-50)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="How many competitions to skip before returning results",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompetitionDiscoverResult:
    # The public feed: ACTIVE competitions between OTHER active users, so the
    # caller has something to open (and later vote on) without being a
    # participant. Excludes the caller's own competitions (own challenger OR
    # opponent — a participant can never vote themselves) and competitions
    # whose challenger or opponent account is inactive. status/participant
    # filters are applied on FK/filter columns (challenger_id/opponent_id),
    # never on anything the client controls.
    active_id = resolve_status_id(db, "active")
    conditions = [
        Competition.status_id == active_id,
        Competition.challenger_id != current_user.user_id,
        Competition.opponent_id != current_user.user_id,
        Competition.challenger.has(User.is_active.is_(True)),
        Competition.opponent.has(User.is_active.is_(True)),
    ]

    if scope == "following":
        # TZ section 14: the "Other competitions" tab shows battles from the
        # caller's social network. Deliberately no recommendation algorithm —
        # a battle qualifies if EITHER side is someone the caller follows.
        followees = select(Follow.followee_id).where(
            Follow.follower_id == current_user.user_id
        )
        conditions.append(
            or_(
                Competition.challenger_id.in_(followees),
                Competition.opponent_id.in_(followees),
            )
        )

    total = db.scalar(select(func.count()).select_from(Competition).where(*conditions))
    rows = db.execute(
        select(Competition)
        .where(*conditions)
        .options(
            joinedload(Competition.challenger),
            joinedload(Competition.opponent),
            joinedload(Competition.status),
        )
        # Ending soonest first — the most time-sensitive to vote on — with a
        # deterministic competition_id tiebreak.
        .order_by(Competition.end_time.asc(), Competition.competition_id.asc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    breakdown = _vote_breakdown(db, [c.competition_id for c in rows])
    return CompetitionDiscoverResult(
        items=[_to_competition_read(c, breakdown) for c in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{competition_id}", response_model=CompetitionDetail)
def get_competition(
    competition_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompetitionDetail:
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )

    # Viewable by any authenticated user, not just the participants. That is
    # the whole point of a public outfit battle: /competitions/discover offers
    # other people's battles precisely so the caller can open one and vote on
    # it, and voting requires seeing the two outfits first. Restricting this to
    # participants made the discover feed lead to a 403. Nothing private is
    # exposed — both participants are already public profiles, and the score is
    # what the battle is for.
    breakdown = _vote_breakdown(db, [competition.competition_id])
    base = _to_competition_read(competition, breakdown)

    my_vote_for = db.execute(
        select(Vote.voted_for_user_id).where(
            Vote.competition_id == competition_id,
            Vote.voter_id == current_user.user_id,
        )
    ).scalar_one_or_none()

    return CompetitionDetail(
        **base.model_dump(),
        challenger_avatar=load_avatar(db, competition.challenger_id),
        opponent_avatar=load_avatar(db, competition.opponent_id),
        my_vote_for=my_vote_for,
    )


@router.post("/{competition_id}/complete", response_model=CompetitionRead)
def complete_competition(
    competition_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompetitionRead:
    """Manually finalize an expired competition and calculate its winner.

    This is an administrative/manual completion trigger. In normal operation
    the backend's automatic expiration sweeper (services/competition_expiration
    .run_expiration_sweeper) completes competitions once end_time passes, so
    the mobile client does not need to call this endpoint. Both paths share the
    same complete_expired_competition service, so winner/draw determination and
    the ACTIVE/end_time/status guards are identical.

    Requires authentication; only the two participants may trigger it (403 for
    anyone else). Completion does NOT distribute the prize pool or touch coins.
    """
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition not found",
        )
    if (
        competition.challenger_id != current_user.user_id
        and competition.opponent_id != current_user.user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this competition",
        )

    outcome, _ = complete_expired_competition(db, competition_id)
    if outcome == CompletionOutcome.ALREADY_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Competition is already completed",
        )
    if outcome == CompletionOutcome.NOT_ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Competition is not active",
        )
    if outcome == CompletionOutcome.NOT_EXPIRED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Competition has not finished yet",
        )

    completed = db.execute(
        select(Competition)
        .where(Competition.competition_id == competition_id)
        .options(
            joinedload(Competition.challenger),
            joinedload(Competition.opponent),
            joinedload(Competition.status),
        )
    ).scalar_one()
    return _to_competition_read(completed)


def _vote_breakdown(
    db: Session, competition_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[uuid.UUID, int]]:
    """Votes per participant, for a whole page of competitions at once.

    One grouped query for the page rather than two per competition: a list of
    20 battles would otherwise cost 40 extra round trips to render 40 numbers.
    Returns {competition_id: {voted_for_user_id: count}}; a competition with
    no votes is simply absent, and callers treat a miss as zero.
    """
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


def _to_competition_read(
    competition: Competition,
    breakdown: dict[uuid.UUID, dict[uuid.UUID, int]] | None = None,
) -> CompetitionRead:
    scores = (breakdown or {}).get(competition.competition_id, {})
    return CompetitionRead(
        competition_id=competition.competition_id,
        request_id=competition.request_id,
        challenger=UserPublic.model_validate(competition.challenger),
        opponent=UserPublic.model_validate(competition.opponent),
        status=competition.status.status_name,
        prize_pool=competition.prize_pool,
        total_votes=competition.total_votes,
        challenger_votes=scores.get(competition.challenger_id, 0),
        opponent_votes=scores.get(competition.opponent_id, 0),
        winner_id=competition.winner_id,
        duration_minutes=competition.duration_minutes,
        start_time=competition.start_time,
        end_time=competition.end_time,
        created_at=competition.created_at,
    )