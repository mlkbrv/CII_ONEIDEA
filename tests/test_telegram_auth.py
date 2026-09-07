"""
End-to-end check of Telegram sign-in — POST /auth/telegram,
POST /auth/telegram-login, and the `Authorization: tma <initData>` scheme.

Run from the project root:
    .venv/Scripts/python -m tests.test_telegram_auth

Covers: a valid Mini App sign-in creating exactly one user + avatar +
auth_providers row, the second sign-in reusing that account, profile fields
refreshing while our username is left alone, username collisions and
non-Latin names, every forgery and staleness rejection (tampered payload,
wrong bot token, no hash, no user, expired auth_date, future auth_date),
deactivated accounts, the tma header on a protected endpoint, and Login
Widget sign-in. Test users are deleted afterwards so the development DB is
left clean.
"""
import hashlib
import hmac
import json
import time
import urllib.parse
import uuid
import warnings

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.main import app
from app.models import AuthProvider, AuthProviderType, Avatar, User

# Starlette emits this when a TestClient is constructed, not when it is
# imported, so the filter is installed here rather than above the imports.
warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

client = TestClient(app)

RUN_ID = f"{int(time.time())}{uuid.uuid4().hex[:6]}"

# Telegram ids are just big integers; these sit far outside any real range so
# a collision with a genuine account is impossible.
TG_MAIN = 900_000_000_000 + int(uuid.uuid4().hex[:6], 16)
TG_SECOND = TG_MAIN + 1
TG_CYRILLIC = TG_MAIN + 2
TG_INACTIVE = TG_MAIN + 3
TG_WIDGET = TG_MAIN + 4
TG_NEVER = TG_MAIN + 5

SUFFIX = uuid.uuid4().hex[:6]
HANDLE_MAIN = f"tg_main_{SUFFIX}"
HANDLE_TAKEN = f"tg_taken_{SUFFIX}"
PASSWORD = "SuperSecret123!"

ALL_TELEGRAM_IDS = [TG_MAIN, TG_SECOND, TG_CYRILLIC, TG_INACTIVE, TG_WIDGET, TG_NEVER]

cleaned = 0


def report(name: str, ok: bool, extra: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({extra})" if extra else ""))


def cleanup() -> None:
    global cleaned
    with SessionLocal() as db:
        rows = list(
            db.execute(
                select(User).where(User.telegram_id.in_(ALL_TELEGRAM_IDS))
            ).scalars().all()
        )
        rows += list(
            db.execute(select(User).where(User.username == HANDLE_TAKEN)).scalars().all()
        )
        for row in rows:
            db.delete(row)
        db.commit()
        cleaned = len(rows)
    print(f"\nCleaned up {cleaned} test user(s).")


# --- Signing helpers -------------------------------------------------------
# These reproduce, client-side, exactly what Telegram does on its side. If
# app/core/telegram.py ever drifts from the documented scheme these stop
# matching and the tests fail, which is the point of rebuilding them here
# instead of importing the implementation under test.


def _sign(fields: dict, secret: bytes) -> str:
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    return hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()


def sign_init_data(user, auth_date=None, token=None) -> str:
    fields = {
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": f"AAH{uuid.uuid4().hex[:16]}",
    }
    secret = hmac.new(
        b"WebAppData", (token or settings.telegram_bot_token).encode(), hashlib.sha256
    ).digest()
    fields["hash"] = _sign(fields, secret)
    return urllib.parse.urlencode(fields)


def sign_widget(user, auth_date=None, token=None) -> dict:
    fields = {str(k): str(v) for k, v in user.items()}
    fields["auth_date"] = str(auth_date if auth_date is not None else int(time.time()))
    secret = hashlib.sha256((token or settings.telegram_bot_token).encode()).digest()
    fields["hash"] = _sign(fields, secret)
    return fields


def tg_user(telegram_id: int, first_name: str = "Test", **extra) -> dict:
    return {"id": telegram_id, "first_name": first_name, **extra}


def load_user(telegram_id: int):
    with SessionLocal() as db:
        return db.execute(
            select(User).where(User.telegram_id == telegram_id)
        ).scalar_one_or_none()


results = []


# --- 1. Mini App sign-in creates the account -------------------------------
init_data = sign_init_data(
    tg_user(TG_MAIN, first_name="Uzeir", last_name="A", username=HANDLE_MAIN)
)
response = client.post("/auth/telegram", json={"init_data": init_data})
token_main = response.json().get("access_token", "")
results.append(
    (
        "valid initData -> 200 with token",
        response.status_code == 200 and bool(token_main),
        str(response.status_code),
    )
)

user = load_user(TG_MAIN)
results.append(("account created for the Telegram id", user is not None, ""))
# Everything below inspects this row; stop here rather than reporting a
# cascade of confusing failures if sign-in did not create it.
assert user is not None, "sign-in did not create an account"
results.append(
    (
        "username taken from the Telegram @handle",
        user is not None and user.username == HANDLE_MAIN,
        user.username if user else "-",
    )
)
results.append(
    ("Telegram-only account has no email", user is not None and user.email is None, "")
)
results.append(
    (
        "Telegram-only account has no password",
        user is not None and user.password_hash is None,
        "",
    )
)
results.append(
    (
        "first/last name mirrored",
        user is not None and user.first_name == "Uzeir" and user.last_name == "A",
        "",
    )
)

with SessionLocal() as db:
    avatars = db.execute(
        select(Avatar).where(Avatar.user_id == user.user_id)
    ).scalars().all()
    providers = db.execute(
        select(AuthProvider).where(AuthProvider.user_id == user.user_id)
    ).scalars().all()
results.append(
    ("exactly one avatar created with the account", len(avatars) == 1, str(len(avatars)))
)
results.append(
    (
        "auth_providers row records the Telegram link",
        len(providers) == 1
        and providers[0].provider == AuthProviderType.TELEGRAM
        and providers[0].provider_user_id == str(TG_MAIN),
        str(len(providers)),
    )
)

# --- 2. Signing in again reuses the same account ---------------------------
first_user_id = user.user_id
response = client.post(
    "/auth/telegram",
    json={
        "init_data": sign_init_data(
            tg_user(TG_MAIN, first_name="Uzeir", last_name="A", username=HANDLE_MAIN)
        )
    },
)
with SessionLocal() as db:
    same = db.execute(select(User).where(User.telegram_id == TG_MAIN)).scalars().all()
results.append(
    (
        "second sign-in returns the same account, not a duplicate",
        response.status_code == 200
        and len(same) == 1
        and same[0].user_id == first_user_id,
        f"{len(same)} row(s)",
    )
)

# --- 3. Telegram profile changes mirror; our username does not -------------
with SessionLocal() as db:
    row = db.execute(select(User).where(User.telegram_id == TG_MAIN)).scalar_one()
    row.username = f"renamed_{SUFFIX}"
    db.commit()
    chosen_username = row.username

client.post(
    "/auth/telegram",
    json={
        "init_data": sign_init_data(
            tg_user(TG_MAIN, first_name="Uzeyir", username="brand_new_handle")
        )
    },
)
user = load_user(TG_MAIN)
assert user is not None, "the account disappeared between sign-ins"
results.append(
    (
        "changed Telegram first_name is mirrored",
        user.first_name == "Uzeyir",
        user.first_name or "-",
    )
)
results.append(
    (
        "changed Telegram @handle is recorded separately",
        user.telegram_username == "brand_new_handle",
        user.telegram_username or "-",
    )
)
results.append(
    (
        "a username the user chose is NOT overwritten",
        user.username == chosen_username,
        user.username,
    )
)

# --- 4. Username collisions ------------------------------------------------
client.post(
    "/auth/register",
    json={
        "username": HANDLE_TAKEN,
        "email": f"{HANDLE_TAKEN}@example.com",
        "password": PASSWORD,
    },
)
client.post(
    "/auth/telegram",
    json={
        "init_data": sign_init_data(
            tg_user(TG_SECOND, first_name="Clash", username=HANDLE_TAKEN)
        )
    },
)
user = load_user(TG_SECOND)
results.append(
    (
        "colliding @handle gets a numbered suffix",
        user is not None and user.username == f"{HANDLE_TAKEN}_2",
        user.username if user else "-",
    )
)

# --- 5. A name outside our username alphabet -------------------------------
client.post(
    "/auth/telegram",
    json={"init_data": sign_init_data(tg_user(TG_CYRILLIC, first_name="Узеир"))},
)
user = load_user(TG_CYRILLIC)
ok = (
    user is not None
    and user.username.replace("_", "").isalnum()
    and len(user.username) >= 3
)
results.append(
    (
        "Cyrillic name with no @handle still yields a valid username",
        ok,
        user.username if user else "-",
    )
)
results.append(
    (
        "the original name is still kept as first_name",
        user is not None and user.first_name == "Узеир",
        user.first_name if user else "-",
    )
)

# --- 6. Forged and stale payloads are rejected -----------------------------
tampered = sign_init_data(tg_user(TG_NEVER, first_name="Mallory")).replace(
    "Mallory", "Admin1"
)
response = client.post("/auth/telegram", json={"init_data": tampered})
results.append(
    (
        "payload edited after signing -> 401",
        response.status_code == 401,
        str(response.status_code),
    )
)

wrong_token = sign_init_data(tg_user(TG_NEVER), token="999999:SOME_OTHER_BOT_TOKEN")
response = client.post("/auth/telegram", json={"init_data": wrong_token})
results.append(
    (
        "signed by a different bot -> 401",
        response.status_code == 401,
        str(response.status_code),
    )
)

no_hash = urllib.parse.urlencode(
    {"user": json.dumps(tg_user(TG_NEVER)), "auth_date": str(int(time.time()))}
)
response = client.post("/auth/telegram", json={"init_data": no_hash})
results.append(
    (
        "initData with no hash -> 401",
        response.status_code == 401,
        str(response.status_code),
    )
)

stale = sign_init_data(
    tg_user(TG_NEVER),
    auth_date=int(time.time()) - settings.telegram_init_data_max_age_seconds - 60,
)
response = client.post("/auth/telegram", json={"init_data": stale})
results.append(
    (
        "auth_date older than the max age -> 401",
        response.status_code == 401,
        str(response.status_code),
    )
)

future = sign_init_data(tg_user(TG_NEVER), auth_date=int(time.time()) + 3600)
response = client.post("/auth/telegram", json={"init_data": future})
results.append(
    (
        "auth_date in the future -> 401",
        response.status_code == 401,
        str(response.status_code),
    )
)

secret = hmac.new(
    b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256
).digest()
signed_no_user = {"auth_date": str(int(time.time()))}
signed_no_user["hash"] = _sign(signed_no_user, secret)
response = client.post(
    "/auth/telegram", json={"init_data": urllib.parse.urlencode(signed_no_user)}
)
results.append(
    (
        "correctly signed but carrying no user -> 401",
        response.status_code == 401,
        str(response.status_code),
    )
)

response = client.post("/auth/telegram", json={"init_data": "not-even-close"})
results.append(
    ("garbage initData -> 401", response.status_code == 401, str(response.status_code))
)

results.append(
    ("no account was created by any rejected attempt", load_user(TG_NEVER) is None, "")
)

# --- 7. The tma scheme on a protected endpoint -----------------------------
fresh = sign_init_data(
    tg_user(TG_MAIN, first_name="Uzeyir", username="brand_new_handle")
)
response = client.get("/users/me", headers={"Authorization": f"tma {fresh}"})
results.append(
    (
        "tma header authenticates a protected endpoint",
        response.status_code == 200
        and response.json().get("username") == chosen_username,
        str(response.status_code),
    )
)

response = client.get("/users/me", headers={"Authorization": f"tma {tampered}"})
results.append(
    (
        "tma header with a forged payload -> 401",
        response.status_code == 401,
        str(response.status_code),
    )
)

response = client.get("/users/me", headers={"Authorization": "tma "})
results.append(
    (
        "tma header with no payload -> 401",
        response.status_code == 401,
        str(response.status_code),
    )
)

response = client.get("/users/me", headers={"Authorization": f"Bearer {token_main}"})
results.append(
    (
        "a JWT issued by /auth/telegram still works",
        response.status_code == 200,
        str(response.status_code),
    )
)

response = client.get("/users/me", headers={"Authorization": f"Basic {fresh}"})
results.append(
    ("an unknown auth scheme -> 401", response.status_code == 401, str(response.status_code))
)

# --- 8. Deactivated accounts -----------------------------------------------
client.post(
    "/auth/telegram",
    json={"init_data": sign_init_data(tg_user(TG_INACTIVE, first_name="Banned"))},
)
with SessionLocal() as db:
    row = db.execute(select(User).where(User.telegram_id == TG_INACTIVE)).scalar_one()
    row.is_active = False
    db.commit()

banned_data = sign_init_data(tg_user(TG_INACTIVE, first_name="Banned"))
response = client.post("/auth/telegram", json={"init_data": banned_data})
results.append(
    (
        "deactivated account cannot get a token -> 403",
        response.status_code == 403,
        str(response.status_code),
    )
)
response = client.get("/users/me", headers={"Authorization": f"tma {banned_data}"})
results.append(
    (
        "deactivated account rejected on the tma path -> 401",
        response.status_code == 401,
        str(response.status_code),
    )
)

# --- 9. Login Widget (browser / PWA mode) ----------------------------------
widget = sign_widget(
    {"id": TG_WIDGET, "first_name": "Web", "username": f"web_{SUFFIX}"}
)
response = client.post("/auth/telegram-login", json={"data": widget})
results.append(
    (
        "valid Login Widget payload -> 200 with token",
        response.status_code == 200 and bool(response.json().get("access_token")),
        str(response.status_code),
    )
)
results.append(("Login Widget created the account", load_user(TG_WIDGET) is not None, ""))

widget_bad = dict(widget)
widget_bad["first_name"] = "Someone Else"
response = client.post("/auth/telegram-login", json={"data": widget_bad})
results.append(
    (
        "Login Widget payload edited after signing -> 401",
        response.status_code == 401,
        str(response.status_code),
    )
)

# The two schemes derive their secret differently, so a blob signed for one
# must not verify as the other.
response = client.post(
    "/auth/telegram-login", json={"data": dict(urllib.parse.parse_qsl(fresh))}
)
results.append(
    (
        "initData replayed at the Login Widget endpoint -> 401",
        response.status_code == 401,
        str(response.status_code),
    )
)


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
