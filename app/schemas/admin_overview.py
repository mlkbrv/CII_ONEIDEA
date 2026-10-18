"""
Schema for GET /admin/overview — the dashboard's live numbers.

One flat object rather than nested groups: this is read by a dashboard that
renders every field as its own stat tile, so there is nothing to gain from
nesting and it would only cost the frontend an extra level of unwrapping.
"""
from datetime import datetime

from pydantic import BaseModel


class DemographicsStats(BaseModel):
    """Self-reported gender and age, counted over all users.

    `unknown` buckets are the players who skipped or were never asked, so the
    numbers in each group always add up to users_total.
    """

    answered: int
    skipped: int
    not_asked: int
    gender: dict[str, int]
    age_groups: dict[str, int]
    average_age: float | None


class AdminOverview(BaseModel):
    users_total: int
    users_active: int
    users_via_telegram: int
    users_new_24h: int

    coins_in_circulation: int
    coins_issued_total: int
    coins_spent_total: int

    qr_codes_active: int
    qr_codes_redeemed: int
    qr_codes_expired: int

    catalog_items_total: int
    catalog_items_available: int

    competitions_active: int
    competitions_completed: int
    votes_cast_total: int

    notifications_pending: int

    demographics: DemographicsStats

    # When this snapshot was computed — every field above is a live COUNT/SUM
    # at read time, not a cached rollup, so a dashboard polling this endpoint
    # can show "as of just now" rather than implying it is itself stale.
    generated_at: datetime
