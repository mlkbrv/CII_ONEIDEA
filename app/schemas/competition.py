"""
Pydantic schema for the `competitions` table (Phase 6, Part 2).

CompetitionRead is the safe response shape for GET /competitions/{id}. It
embeds UserPublic for both participants and the lookup table's status_name
("active" / "completed") — never password_hash, email, coin_balance, or any
other account field. winner_id is exposed only when a winner exists (null
until competition completion is implemented).
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.avatar import AvatarRead
from app.schemas.user import UserPublic


class CompetitionRead(BaseModel):
    competition_id: UUID
    request_id: UUID
    challenger: UserPublic
    opponent: UserPublic
    status: str
    prize_pool: int
    total_votes: int

    # The score, split per participant. total_votes alone cannot render a
    # battle card: "123 votes" says nothing about who is winning, and the
    # whole screen is "Uzeir 72 VS 51 Ali". Counted from the votes table
    # rather than stored, so it can never drift from the rows that decide
    # the winner at completion time.
    challenger_votes: int = 0
    opponent_votes: int = 0

    winner_id: UUID | None = None
    duration_minutes: int
    start_time: datetime
    end_time: datetime
    created_at: datetime


class CompetitionDetail(CompetitionRead):
    """Response of GET /competitions/{id} — everything the battle screen needs.

    Adds the two outfits to the list shape, because the battle screen IS the
    two avatars side by side, and the caller's own vote so the UI can show
    which side they backed instead of offering to charge them a second coin.
    """

    challenger_avatar: AvatarRead | None = None
    opponent_avatar: AvatarRead | None = None

    # Who the caller voted for in this battle, or null if they have not voted.
    # One vote per user per competition is enforced by a UNIQUE constraint, so
    # this is single-valued by construction.
    my_vote_for: UUID | None = None


class CompetitionDiscoverResult(BaseModel):
    """Envelope for GET /competitions/discover.

    `items` reuses the same safe CompetitionRead item shape as everywhere else
    in the app; `total`/`limit`/`offset` mirror the established envelope of
    the wardrobe and clothing feeds.
    """

    items: list[CompetitionRead]
    total: int
    limit: int
    offset: int