from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import CompetitionRequestStatus, CompetitionStatus, str_enum
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class CompetitionRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competition_requests"
    __table_args__ = (
        CheckConstraint("challenger_id != opponent_id", name="ck_competition_requests_not_self"),
        Index("ix_competition_requests_opponent_id", "opponent_id"),
        Index("ix_competition_requests_challenger_id", "challenger_id"),
    )

    challenger_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    opponent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CompetitionRequestStatus] = mapped_column(
        str_enum(CompetitionRequestStatus), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    challenger: Mapped[User] = relationship(
        back_populates="competition_requests_sent",
        foreign_keys=[challenger_id],
    )
    opponent: Mapped[User] = relationship(
        back_populates="competition_requests_received",
        foreign_keys=[opponent_id],
    )
    competition: Mapped[Competition | None] = relationship(
        back_populates="request",
        uselist=False,
    )


class Competition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "competitions"
    __table_args__ = (
        CheckConstraint("challenger_id != opponent_id", name="ck_competitions_not_self"),
        Index(
            "uq_competitions_active_challenger",
            "challenger_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "uq_competitions_active_opponent",
            "opponent_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competition_requests.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    challenger_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    opponent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CompetitionStatus] = mapped_column(str_enum(CompetitionStatus), nullable=False)
    prize_pool: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    total_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    winner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    request: Mapped[CompetitionRequest] = relationship(
        back_populates="competition",
        foreign_keys=[request_id],
    )
    challenger: Mapped[User] = relationship(
        back_populates="competitions_as_challenger",
        foreign_keys=[challenger_id],
    )
    opponent: Mapped[User] = relationship(
        back_populates="competitions_as_opponent",
        foreign_keys=[opponent_id],
    )
    winner: Mapped[User | None] = relationship(
        back_populates="competitions_won",
        foreign_keys=[winner_id],
    )
    votes: Mapped[list[Vote]] = relationship(back_populates="competition")


class Vote(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "votes"
    __table_args__ = (
        Index("ix_votes_competition_participant", "competition_id", "participant_id"),
    )

    competition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    voter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    competition: Mapped[Competition] = relationship(back_populates="votes")
    voter: Mapped[User] = relationship(back_populates="votes", foreign_keys=[voter_id])
    participant: Mapped[User] = relationship(foreign_keys=[participant_id])
