"""
Schemas for looking at OTHER people: profiles, follower lists, leaderboard.

The rule these all follow: a profile is public, an account is not. Username,
biography, picture, outfit, follower counts and winning streak describe the
character someone plays in the game and are meant to be seen. Email, coin
balance, admin flag and Telegram id describe the account behind it and never
appear here — not even for the account owner, who reads those from
GET /users/me instead.
"""
import uuid

from pydantic import BaseModel

from app.schemas.avatar import AvatarRead


class PublicProfile(BaseModel):
    """Response of GET /users/{user_id} — one screen's worth of profile.

    Deliberately assembled server-side rather than left to four client
    requests: opening a profile shows the avatar, the counts, the follow
    button state and any live battle at once, and on a phone over mobile data
    those round trips are the whole latency budget.
    """

    user_id: uuid.UUID
    username: str
    biography: str | None = None
    profile_picture_url: str | None = None
    winning_streak: int

    followers_count: int
    following_count: int

    # Whether the CALLER follows this user — the state of the follow button.
    # Always false when looking at your own profile.
    is_following: bool
    is_self: bool

    # Null when the user has never been given an avatar row. Every account
    # created through registration or Telegram sign-in has one.
    avatar: AvatarRead | None = None

    # TZ section 8: the wardrobe is visible only if its owner allows it. The
    # flag is published so the client can hide the tab instead of offering a
    # link that will 403.
    wardrobe_public: bool

    # Set while this user is in a live battle, so the profile can link
    # straight to it. Null otherwise.
    active_competition_id: uuid.UUID | None = None


class FollowUser(BaseModel):
    """One row of a follower/following list."""

    user_id: uuid.UUID
    username: str
    profile_picture_url: str | None = None
    biography: str | None = None
    winning_streak: int

    # Whether the CALLER follows this row's user, so a follower list doubles
    # as a place to follow back without a second request per row.
    is_following: bool


class FollowList(BaseModel):
    items: list[FollowUser]
    total: int
    limit: int
    offset: int


class LeaderboardEntry(BaseModel):
    """One row of the leaderboard (TZ section 17)."""

    rank: int
    user_id: uuid.UUID
    username: str
    profile_picture_url: str | None = None
    winning_streak: int
    competitions_won: int
    is_self: bool


class Leaderboard(BaseModel):
    """Response of GET /leaderboard.

    `me` is the caller's own row even when they are outside the returned
    page — a leaderboard you cannot find yourself on is not motivating. It is
    null only if the caller has never competed and so has no standing.
    """

    metric: str
    items: list[LeaderboardEntry]
    total: int
    limit: int
    offset: int
    me: LeaderboardEntry | None = None
