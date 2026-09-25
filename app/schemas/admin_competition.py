"""
Schemas for GET /admin/competitions and GET /admin/competitions/{id} — the
admin's read-only view of every battle, not just the caller's own the way
the public /competitions endpoints scope it.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.avatar import AvatarRead


class AdminCompetitionParticipant(BaseModel):
    """Enough to identify a side of the battle and find them elsewhere in
    the admin panel — a link target, not a full user record."""

    user_id: uuid.UUID
    username: str
    votes: int


class AdminCompetitionRead(BaseModel):
    competition_id: uuid.UUID
    status: str
    challenger: AdminCompetitionParticipant
    opponent: AdminCompetitionParticipant
    winner_id: uuid.UUID | None
    prize_pool: int
    total_votes: int
    duration_minutes: int
    start_time: datetime
    end_time: datetime
    created_at: datetime


class AdminCompetitionList(BaseModel):
    items: list[AdminCompetitionRead]
    total: int
    limit: int
    offset: int


class AdminCompetitionDetail(AdminCompetitionRead):
    """The list shape plus both outfits, for the one place an operator
    actually needs to see what the battle looks like."""

    challenger_avatar: AvatarRead | None
    opponent_avatar: AvatarRead | None
