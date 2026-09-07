"""
End-to-end check of the "looking at other people" endpoints —
GET /users/{id}, /users/{id}/followers, /users/{id}/following,
/users/{id}/avatar, /users/{id}/wardrobe, and GET /leaderboard.

Run from the project root:
    .venv/Scripts/python -m tests.test_public_profile

Covers: profile contents and follow state, self-view, deactivated and
unknown users reported alike, follower/following lists with their
follow-back flags and paging, another user's outfit being public while
their wardrobe honours users.wardrobe_public, leaderboard ordering under
both metrics with the caller's own row always present, and that none of it
leaks account fields. Test users are deleted afterwards.
"""
import time
import uuid
import warnings

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import User

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

client = TestClient(app)

RUN_ID = f"{int(time.time())}{uuid.uuid4().hex[:6]}"
PASSWORD = "SuperSecret123!"

# A: the caller. B: the person being looked at. C: a third party who follows
# B, so B's follower list has someone in it that A does not follow.
# D: deactivated.
NAMES = ["A", "B", "C", "D"]
USERS = {n: f"pub_{n.lower()}_{RUN_ID}" for n in NAMES}
TOKENS: dict[str, str] = {}
IDS: dict[str, str] = {}

NONEXISTENT_ID = str(uuid.uuid4())

ACCOUNT_FIELDS = ("password_hash", "email", "coin_balance", "is_admin", "telegram_id")


def report(name: str, ok: bool, extra: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({extra})" if extra else ""))


def cleanup() -> None:
    with SessionLocal() as db:
        rows = db.execute(
            select(User).where(User.username.in_(list(USERS.values())))
        ).scalars().all()
        for row in rows:
            db.delete(row)
        db.commit()
    print(f"\nCleaned up {len(USERS)} test user(s).")


def auth(name: str) -> dict:
    return {"Authorization": f"Bearer {TOKENS[name]}"}


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
    # Give B a streak and a bio so the profile has something to show.
    b_row = db.execute(select(User).where(User.username == USERS["B"])).scalar_one()
    b_row.winning_streak = 4
    b_row.biography = "battle-tested"
    d_row = db.execute(select(User).where(User.username == USERS["D"])).scalar_one()
    d_row.is_active = False
    db.commit()

# C follows B; A does not (yet).
client.post(f"/users/{IDS['B']}/follow", headers=auth("C"))

results.append(("setup: all four users registered and logged in", all(TOKENS.values()), ""))

# --- 1. Public profile -----------------------------------------------------
r = client.get(f"/users/{IDS['B']}", headers=auth("A"))
profile = r.json() if r.status_code == 200 else {}
results.append((
    "GET /users/{id} returns the profile",
    r.status_code == 200 and profile.get("username") == USERS["B"],
    str(r.status_code),
))
results.append((
    "profile carries the public game fields",
    profile.get("winning_streak") == 4 and profile.get("biography") == "battle-tested",
    f"streak={profile.get('winning_streak')}",
))
results.append((
    "profile counts followers and following",
    profile.get("followers_count") == 1 and profile.get("following_count") == 0,
    f"{profile.get('followers_count')}/{profile.get('following_count')}",
))
results.append((
    "not following yet -> is_following false",
    profile.get("is_following") is False and profile.get("is_self") is False,
    "",
))
results.append((
    "profile embeds the avatar so the outfit renders in one request",
    isinstance(profile.get("avatar"), dict) and "equipment" in (profile.get("avatar") or {}),
    "",
))
results.append((
    "profile exposes no account fields",
    not any(field in str(profile) for field in ACCOUNT_FIELDS),
    "",
))

client.post(f"/users/{IDS['B']}/follow", headers=auth("A"))
after = client.get(f"/users/{IDS['B']}", headers=auth("A")).json()
results.append((
    "after following -> is_following true and the count grows",
    after.get("is_following") is True and after.get("followers_count") == 2,
    f"{after.get('followers_count')}",
))

own = client.get(f"/users/{IDS['A']}", headers=auth("A")).json()
results.append((
    "own profile reports is_self and never is_following",
    own.get("is_self") is True and own.get("is_following") is False,
    "",
))

r = client.get(f"/users/{NONEXISTENT_ID}", headers=auth("A"))
results.append(("unknown user -> 404", r.status_code == 404, str(r.status_code)))

r = client.get(f"/users/{IDS['D']}", headers=auth("A"))
results.append((
    "deactivated user is reported as missing, not as banned",
    r.status_code == 404,
    str(r.status_code),
))

r = client.get(f"/users/{IDS['B']}")
results.append(("unauthenticated profile -> 401", r.status_code == 401, str(r.status_code)))

# --- 2. Follower / following lists ----------------------------------------
r = client.get(f"/users/{IDS['B']}/followers", headers=auth("A"))
body = r.json() if r.status_code == 200 else {}
usernames = {item["username"] for item in body.get("items", [])}
results.append((
    "followers list contains both followers",
    r.status_code == 200 and usernames == {USERS["A"], USERS["C"]} and body.get("total") == 2,
    f"{sorted(usernames)}",
))

by_name = {item["username"]: item for item in body.get("items", [])}
results.append((
    "each row says whether the caller already follows them",
    by_name.get(USERS["C"], {}).get("is_following") is False,
    str(by_name.get(USERS["C"], {}).get("is_following")),
))

r = client.get(f"/users/{IDS['A']}/following", headers=auth("A"))
body = r.json() if r.status_code == 200 else {}
results.append((
    "following list shows who A follows",
    r.status_code == 200
    and [item["username"] for item in body.get("items", [])] == [USERS["B"]],
    str(r.status_code),
))

r = client.get(f"/users/{IDS['B']}/followers?limit=1", headers=auth("A"))
body = r.json()
results.append((
    "paging returns one row but the full total",
    len(body.get("items", [])) == 1 and body.get("total") == 2,
    f"{len(body.get('items', []))}/{body.get('total')}",
))

r = client.get(f"/users/{NONEXISTENT_ID}/followers", headers=auth("A"))
results.append(("followers of an unknown user -> 404", r.status_code == 404, str(r.status_code)))

# --- 3. Someone else's outfit and wardrobe --------------------------------
r = client.get(f"/users/{IDS['B']}/avatar", headers=auth("A"))
results.append((
    "another user's outfit is public",
    r.status_code == 200 and "equipment" in r.json(),
    str(r.status_code),
))

r = client.get(f"/users/{IDS['B']}/wardrobe", headers=auth("A"))
results.append((
    "wardrobe is readable while wardrobe_public is true",
    r.status_code == 200 and "items" in r.json(),
    str(r.status_code),
))

with SessionLocal() as db:
    row = db.execute(select(User).where(User.username == USERS["B"])).scalar_one()
    row.wardrobe_public = False
    db.commit()

r = client.get(f"/users/{IDS['B']}/wardrobe", headers=auth("A"))
results.append((
    "a private wardrobe -> 403 for everyone else",
    r.status_code == 403,
    str(r.status_code),
))
r = client.get(f"/users/{IDS['B']}/wardrobe", headers=auth("B"))
results.append((
    "the owner still reads their own private wardrobe",
    r.status_code == 200,
    str(r.status_code),
))
results.append((
    "the profile advertises the wardrobe as private so the tab can hide",
    client.get(f"/users/{IDS['B']}", headers=auth("A")).json().get("wardrobe_public") is False,
    "",
))
results.append((
    "a private wardrobe does not hide the outfit",
    client.get(f"/users/{IDS['B']}/avatar", headers=auth("A")).status_code == 200,
    "",
))

# --- 4. Leaderboard --------------------------------------------------------
r = client.get("/leaderboard?limit=100", headers=auth("A"))
board = r.json() if r.status_code == 200 else {}
rows = board.get("items", [])
results.append((
    "GET /leaderboard returns a ranked page",
    r.status_code == 200 and len(rows) > 0,
    str(r.status_code),
))
results.append((
    "ranks are dense and start at 1",
    [row["rank"] for row in rows] == list(range(1, len(rows) + 1)),
    "",
))
results.append((
    "rows are ordered by winning streak, highest first",
    all(
        rows[i]["winning_streak"] >= rows[i + 1]["winning_streak"]
        for i in range(len(rows) - 1)
    ),
    "",
))
b_entry = next((row for row in rows if row["username"] == USERS["B"]), None)
results.append((
    "B's streak of 4 puts them on the board",
    b_entry is not None and b_entry["winning_streak"] == 4,
    str(b_entry["rank"]) if b_entry else "absent",
))
results.append((
    "the caller's own row comes back alongside the page",
    board.get("me") is not None
    and board["me"]["user_id"] == IDS["A"]
    and board["me"]["is_self"] is True,
    "",
))
results.append((
    "the deactivated user is not ranked",
    all(row["username"] != USERS["D"] for row in rows),
    "",
))
results.append((
    "leaderboard exposes no account fields",
    not any(field in str(board) for field in ACCOUNT_FIELDS),
    "",
))

r = client.get("/leaderboard?metric=wins&limit=100", headers=auth("A"))
wins_board = r.json() if r.status_code == 200 else {}
results.append((
    "the wins metric is accepted and ranks by wins",
    r.status_code == 200
    and wins_board.get("metric") == "wins"
    and all(
        wins_board["items"][i]["competitions_won"]
        >= wins_board["items"][i + 1]["competitions_won"]
        for i in range(len(wins_board.get("items", [])) - 1)
    ),
    str(r.status_code),
))

results.append((
    "an unknown metric -> 422",
    client.get("/leaderboard?metric=coins", headers=auth("A")).status_code == 422,
    "",
))

# The caller's rank must be their position among ALL users, not within the
# page they happened to fetch — that is the whole reason `me` is computed
# from the same ranking rather than looked up in `items`.
paged = client.get("/leaderboard?limit=1", headers=auth("A")).json()
full = client.get("/leaderboard?limit=100", headers=auth("A")).json()
my_rank_in_full = next(
    (row["rank"] for row in full["items"] if row["user_id"] == IDS["A"]), None
)
results.append((
    "the caller's rank is global, not relative to the page",
    paged.get("me", {}).get("rank") == my_rank_in_full,
    f"paged={paged.get('me', {}).get('rank')}, full={my_rank_in_full}",
))

results.append((
    "unauthenticated leaderboard -> 401",
    client.get("/leaderboard").status_code == 401,
    "",
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
