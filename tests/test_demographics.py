"""
Checks of the optional gender/age form (no database needed: the session is a
small fake, so this verifies the logic and the HTTP contract, not the SQL).

Run from the project root:
    python -m tests.test_demographics

Covers: the bonus is paid once and recorded in the ledger, skipping never pays
and never overwrites an answer, bad years and empty bodies are rejected, the
age groups line up, and the dashboard statistics add up.
"""
import os
import sys
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace as NS

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5/x")
os.environ.setdefault("SECRET_KEY", "k")

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.services import demographics


class Result:
    def __init__(self, rows=None, scalar=None):
        self.rows = rows or []
        self.scalar = scalar

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.scalar


class FakeDB:
    def __init__(self, user, stats_rows=None, average=None):
        self.user = user
        self.added = []
        self.commits = 0
        self.stats_rows = list(stats_rows or [])
        self.average = average

    def get(self, model, key, **kwargs):
        return self.user

    def execute(self, query):
        if self.stats_rows:
            return Result(rows=self.stats_rows.pop(0))
        return Result(scalar=7)

    def scalar(self, query):
        return self.average

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        pass


def make_user(**overrides):
    values = dict(
        user_id=uuid.uuid4(), username="tester", email=None, biography=None,
        profile_picture_url=None, is_active=True, language="ru", gender=None,
        birth_year=None, demographics_status=None, coin_balance=1000,
        created_at=datetime.now(timezone.utc),
    )
    values.update(overrides)
    return NS(**values)


def client_for(db, user):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def run() -> list[tuple[str, bool]]:
    results = []
    year = demographics.current_year()

    user = make_user()
    db = FakeDB(user)
    client = client_for(db, user)
    response = client.post("/users/me/demographics", json={"gender": "female", "birth_year": year - 25})
    body = response.json()
    results.append(("first answer pays the bonus", response.status_code == 200
                    and body["bonus_coins"] == settings.demographics_bonus_coins
                    and body["balance"] == 1000 + settings.demographics_bonus_coins))
    results.append(("bonus is written to the ledger", len(db.added) == 1
                    and db.added[0].amount == settings.demographics_bonus_coins
                    and db.added[0].balance_after == user.coin_balance))
    results.append(("answers are stored", user.gender == "female" and user.birth_year == year - 25
                    and user.demographics_status == "answered"))

    again = client.post("/users/me/demographics", json={"gender": "male"})
    results.append(("second answer pays nothing", again.json()["bonus_coins"] == 0 and len(db.added) == 1))

    skipped = make_user()
    client = client_for(FakeDB(skipped), skipped)
    r = client.post("/users/me/demographics/skip")
    results.append(("skip marks the user as asked", r.status_code == 200 and skipped.demographics_status == "skipped"))
    paid = FakeDB(skipped)
    client = client_for(paid, skipped)
    r = client.post("/users/me/demographics", json={"birth_year": year - 30})
    results.append(("answering after a skip still pays once", r.json()["bonus_coins"] == settings.demographics_bonus_coins))

    answered = make_user(demographics_status="answered", gender="male")
    client = client_for(FakeDB(answered), answered)
    client.post("/users/me/demographics/skip")
    results.append(("skip never overwrites an answer", answered.demographics_status == "answered"))

    client = client_for(FakeDB(make_user()), make_user())
    results.append(("empty body is rejected", client.post("/users/me/demographics", json={}).status_code == 422))
    results.append(("year in the future is rejected",
                    client.post("/users/me/demographics", json={"birth_year": year + 1}).status_code == 422))
    results.append(("year 1900 is rejected",
                    client.post("/users/me/demographics", json={"birth_year": 1900}).status_code == 422))
    results.append(("unknown gender is rejected",
                    client.post("/users/me/demographics", json={"gender": "x"}).status_code == 422))

    groups = [demographics.age_group(year - age) for age in (10, 17, 18, 24, 25, 34, 35, 44, 45, 80)]
    results.append(("age groups", groups == ["under_18", "under_18", "18_24", "18_24", "25_34", "25_34",
                                              "35_44", "35_44", "45_plus", "45_plus"]))

    fake = FakeDB(None, stats_rows=[
        [("answered", 3), ("skipped", 2), (None, 5)],
        [("male", 2), ("female", 1), (None, 7)],
        [(year - 20, 2), (year - 40, 1), (None, 7)],
    ], average=year - 30)
    stats = demographics.stats(fake)
    results.append(("stats add up", stats["answered"] + stats["skipped"] + stats["not_asked"] == 10
                    and sum(stats["gender"].values()) == 10 and sum(stats["age_groups"].values()) == 10
                    and stats["age_groups"]["18_24"] == 2 and stats["average_age"] == 30.0))

    app.dependency_overrides.clear()
    return results


def main() -> int:
    results = run()
    for name, ok in results:
        print("PASS" if ok else "FAIL", name)
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    sys.exit(main())
