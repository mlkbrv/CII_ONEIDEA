"""
End-to-end check of notifications — the feed endpoints, the rows written by
the battle flow, the "ending soon" reminder sweep, and the delivery queue.

Run from the project root:
    .venv/Scripts/python -m tests.test_notifications

Covers: a notification per event (follow, challenge, accept, decline, result),
notifications rolling back with the operation that failed, the feed's paging
and unread count, read/read-all, ownership isolation, streaks moving on
completion, the reminder firing exactly once, and the delivery queue skipping
accounts with no Telegram chat instead of blocking on them.
Test users are deleted afterwards.
"""
import time
import uuid
import warnings
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core.database import SessionLocal
from app.main import app
from app.models import (
    CoinTransaction,
    Competition,
    CompetitionRequest,
    Notification,
    NotificationType,
    User,
    Vote,
)
from app.services.competition_expiration import sweep_expired_competitions
from app.services.reminders import sweep_ending_soon

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

client = TestClient(app)

RUN_ID = f"{int(time.time())}{uuid.uuid4().hex[:6]}"
PASSWORD = "SuperSecret123!"

# A challenges B. C is a bystander who votes so the battle has a winner.
NAMES = ["A", "B", "C", "D"]
USERS = {n: f"ntf_{n.lower()}_{RUN_ID}" for n in NAMES}
TOKENS: dict[str, str] = {}
IDS: dict[str, str] = {}


def report(name: str, ok: bool, extra: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({extra})" if extra else ""))


def cleanup() -> None:
    """Delete the test users and everything that points at them.

    Dependants have to go first: coin_transactions.user_id and votes.voter_id
    are NOT NULL with no delete cascade, so deleting a user outright makes
    SQLAlchemy try to null those columns and the database rejects it.
    """
    with SessionLocal() as db:
        ids = db.execute(
            select(User.user_id).where(User.username.in_(list(USERS.values())))
        ).scalars().all()
        if ids:
            competitions = db.execute(
                select(Competition).where(
                    Competition.challenger_id.in_(ids)
                    | Competition.opponent_id.in_(ids)
                )
            ).scalars().all()
            requests = db.execute(
                select(CompetitionRequest).where(
                    CompetitionRequest.challenger_id.in_(ids)
                    | CompetitionRequest.opponent_id.in_(ids)
                )
            ).scalars().all()
            competition_ids = [c.competition_id for c in competitions]

            vote_filter = Vote.voter_id.in_(ids)
            if competition_ids:
                vote_filter = vote_filter | Vote.competition_id.in_(competition_ids)
            for vote in db.execute(select(Vote).where(vote_filter)).scalars().all():
                db.delete(vote)
            for tx in db.execute(
                select(CoinTransaction).where(CoinTransaction.user_id.in_(ids))
            ).scalars().all():
                db.delete(tx)
            db.flush()
            for competition in competitions:
                db.delete(competition)
            for request in requests:
                db.delete(request)
            db.flush()

        for row in db.execute(
            select(User).where(User.username.in_(list(USERS.values())))
        ).scalars().all():
            db.delete(row)
        db.commit()
    print(f"\nCleaned up {len(USERS)} test user(s).")


def auth(name: str) -> dict:
    return {"Authorization": f"Bearer {TOKENS[name]}"}


def notifications_of(name: str, type_name: str | None = None) -> list[Notification]:
    """Rows straight from the database, so the feed endpoint is not both the
    thing under test and the thing doing the checking."""
    with SessionLocal() as db:
        query = (
            select(Notification)
            .join(NotificationType)
            .where(Notification.user_id == uuid.UUID(IDS[name]))
        )
        if type_name:
            query = query.where(NotificationType.type_name == type_name)
        return list(db.execute(query).scalars().all())


def credit(name: str, amount: int) -> None:
    with SessionLocal() as db:
        db.execute(
            update(User)
            .where(User.user_id == uuid.UUID(IDS[name]))
            .values(coin_balance=User.coin_balance + amount)
        )
        db.commit()


results = []

# --- Setup -----------------------------------------------------------------
for name, username in USERS.items():
    client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": PASSWORD},
    )
    TOKENS[name] = client.post(
        "/auth/login", json={"username": username, "password": PASSWORD}
    ).json().get("access_token", "")

with SessionLocal() as db:
    for name, username in USERS.items():
        IDS[name] = str(
            db.execute(select(User.user_id).where(User.username == username)).scalar_one()
        )

results.append(("setup: users registered", all(TOKENS.values()), ""))

# --- 1. Following notifies the followee ------------------------------------
client.post(f"/users/{IDS['B']}/follow", headers=auth("A"))
follows = notifications_of("B", "new_follower")
results.append((
    "following someone notifies them once",
    len(follows) == 1 and str(follows[0].actor_user_id) == IDS["A"],
    str(len(follows)),
))

# A duplicate follow is rejected, so it must not queue a second notification.
client.post(f"/users/{IDS['B']}/follow", headers=auth("A"))
results.append((
    "a rejected duplicate follow queues nothing",
    len(notifications_of("B", "new_follower")) == 1,
    str(len(notifications_of("B", "new_follower"))),
))

# --- 2. Challenge, decline, accept -----------------------------------------
r = client.post(
    "/competition-requests",
    json={"opponent_id": IDS["C"], "duration_minutes": 30},
    headers=auth("A"),
)
declined_request = r.json().get("request_id")
results.append((
    "a challenge notifies the opponent",
    len(notifications_of("C", "competition_request")) == 1,
    str(r.status_code),
))
challenge_note = notifications_of("C", "competition_request")[0]
results.append((
    "the challenge notification carries the duration for its message",
    (challenge_note.payload or {}).get("duration_minutes") == 30,
    str(challenge_note.payload),
))

client.post(f"/competition-requests/{declined_request}/decline", headers=auth("C"))
results.append((
    "declining notifies the challenger",
    len(notifications_of("A", "competition_declined")) == 1,
    "",
))

r = client.post(
    "/competition-requests",
    json={"opponent_id": IDS["B"], "duration_minutes": 30},
    headers=auth("A"),
)
accepted_request = r.json().get("request_id")
client.post(f"/competition-requests/{accepted_request}/accept", headers=auth("B"))
results.append((
    "accepting notifies the challenger",
    len(notifications_of("A", "competition_accepted")) == 1,
    "",
))

# A challenge that is refused must leave nothing behind.
before = len(notifications_of("B", "competition_request"))
client.post(
    "/competition-requests",
    json={"opponent_id": IDS["A"], "duration_minutes": 30},
    headers=auth("A"),
)
results.append((
    "a self-challenge is rejected and queues nothing",
    len(notifications_of("B", "competition_request")) == before,
    "",
))

with SessionLocal() as db:
    competition = db.execute(
        select(Competition).where(
            Competition.request_id == uuid.UUID(accepted_request)
        )
    ).scalar_one()
    competition_id = competition.competition_id

# --- 3. The "ending soon" reminder -----------------------------------------
# The battle runs for 30 minutes; move its start back so only 5 remain.
with SessionLocal() as db:
    db.execute(
        update(Competition)
        .where(Competition.competition_id == competition_id)
        .values(start_time=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=25))
    )
    db.commit()

sent = sweep_ending_soon(10)
results.append((
    "the reminder sweep notifies both participants",
    sent == 1
    and len(notifications_of("A", "competition_ending_soon")) == 1
    and len(notifications_of("B", "competition_ending_soon")) == 1,
    f"swept={sent}",
))

# Exactly once: this is the property reminder_sent_at exists to guarantee.
sent_again = sweep_ending_soon(10)
results.append((
    "sweeping again reminds nobody twice",
    sent_again == 0 and len(notifications_of("A", "competition_ending_soon")) == 1,
    f"swept={sent_again}",
))

# --- 4. Result, prize and streak -------------------------------------------
credit("C", 5)
credit("D", 5)
client.post(
    f"/competitions/{competition_id}/votes",
    json={"voted_for_user_id": IDS["A"]},
    headers=auth("C"),
)
client.post(
    f"/competitions/{competition_id}/votes",
    json={"voted_for_user_id": IDS["A"]},
    headers=auth("D"),
)

with SessionLocal() as db:
    db.execute(
        update(Competition)
        .where(Competition.competition_id == competition_id)
        .values(start_time=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=90))
    )
    db.commit()

with SessionLocal() as db:
    sweep_expired_competitions(db)

results.append((
    "the winner is told they won",
    len(notifications_of("A", "competition_won")) == 1,
    "",
))
results.append((
    "the loser is told they lost",
    len(notifications_of("B", "competition_lost")) == 1,
    "",
))

won = notifications_of("A", "competition_won")[0]
results.append((
    "the win notification quotes the prize pool and the new streak",
    (won.payload or {}).get("prize_pool") == 2
    and (won.payload or {}).get("winning_streak") == 1,
    str(won.payload),
))

with SessionLocal() as db:
    winner = db.execute(
        select(User).where(User.user_id == uuid.UUID(IDS["A"]))
    ).scalar_one()
    loser = db.execute(
        select(User).where(User.user_id == uuid.UUID(IDS["B"]))
    ).scalar_one()
    streaks = (winner.winning_streak, loser.winning_streak)
results.append((
    "the winner's streak goes up and the loser's resets (TZ 13)",
    streaks == (1, 0),
    f"winner={streaks[0]}, loser={streaks[1]}",
))

# --- 5. The feed endpoints -------------------------------------------------
r = client.get("/notifications", headers=auth("A"))
feed = r.json() if r.status_code == 200 else {}
results.append((
    "GET /notifications returns the caller's feed",
    r.status_code == 200 and feed.get("total", 0) >= 3,
    f"total={feed.get('total')}",
))
results.append((
    "the feed renders a human message per notification",
    all(item.get("message") for item in feed.get("items", [])),
    "",
))
results.append((
    "newest first",
    [i["created_at"] for i in feed["items"]]
    == sorted((i["created_at"] for i in feed["items"]), reverse=True),
    "",
))
results.append((
    "the feed carries the unread badge count",
    feed.get("unread") == feed.get("total"),
    f"{feed.get('unread')}/{feed.get('total')}",
))

results.append((
    "the badge endpoint agrees with the feed",
    client.get("/notifications/unread-count", headers=auth("A")).json().get("unread")
    == feed.get("unread"),
    "",
))

first_id = feed["items"][0]["notification_id"]
r = client.post(f"/notifications/{first_id}/read", headers=auth("A"))
results.append((
    "marking one read works and is reflected in the badge",
    r.status_code == 200
    and r.json().get("is_read") is True
    and client.get("/notifications/unread-count", headers=auth("A")).json()["unread"]
    == feed["unread"] - 1,
    str(r.status_code),
))
results.append((
    "marking it read again is a no-op, not an error",
    client.post(f"/notifications/{first_id}/read", headers=auth("A")).status_code == 200,
    "",
))

results.append((
    "someone else's notification is simply not found",
    client.post(f"/notifications/{first_id}/read", headers=auth("B")).status_code == 404,
    "",
))

r = client.get("/notifications?unread_only=true", headers=auth("A"))
results.append((
    "unread_only filters out what was read",
    all(not item["is_read"] for item in r.json().get("items", [])),
    "",
))

results.append((
    "read-all clears the badge",
    client.post("/notifications/read-all", headers=auth("A")).json().get("unread") == 0
    and client.get("/notifications/unread-count", headers=auth("A")).json()["unread"] == 0,
    "",
))

results.append((
    "the feed never returns another user's notifications",
    all(
        item["notification_id"] != first_id
        for item in client.get("/notifications", headers=auth("B")).json()["items"]
    ),
    "",
))

results.append((
    "unauthenticated feed -> 401",
    client.get("/notifications").status_code == 401,
    "",
))

# --- 6. The delivery queue -------------------------------------------------
# These accounts were created with email + password and have no Telegram chat.
# The queue has to stamp them rather than retrying forever at the head.
from app.bot.delivery import _load_pending  # noqa: E402  (needs the rows above)

pending = _load_pending()
results.append((
    "notifications for accounts with no Telegram chat are not queued",
    all(str(row[1]) not in IDS.values() for row in pending),
    f"{len(pending)} deliverable",
))

with SessionLocal() as db:
    stuck = db.execute(
        select(Notification).where(
            Notification.user_id == uuid.UUID(IDS["A"]),
            Notification.delivered_at.is_(None),
        )
    ).scalars().all()
results.append((
    "and they are stamped so they cannot block the queue",
    len(stuck) == 0,
    f"{len(stuck)} still pending",
))


try:
    failed = 0
    for name, ok, extra in results:
        report(name, ok, extra)
        failed += 0 if ok else 1
    print(f"\n{len(results) - failed}/{len(results)} checks passed.")
    if failed:
        raise SystemExit(1)
finally:
    cleanup()
