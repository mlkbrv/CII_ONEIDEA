import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.routers import (
    admin_router,
    auth_router,
    avatar_router,
    clothing_router,
    competition_requests_router,
    competitions_router,
    leaderboard_router,
    notifications_router,
    qr_router,
    users_router,
    votes_router,
    wardrobe_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Optionally owns the competition-expiration sweeper.

    The sweeper, the reminder sweep and the Telegram bot normally live in the
    worker process (`python -m app.worker`), because each must run exactly
    once and the API may run several uvicorn workers. RUN_SWEEPER=true brings
    it back in-process for a single-process development run where starting a
    second container is not worth it.
    """
    if not settings.run_sweeper:
        yield
        return

    from app.services.competition_expiration import run_expiration_sweeper

    stop_event = threading.Event()
    thread = threading.Thread(
        target=run_expiration_sweeper,
        args=(stop_event, settings.auto_complete_interval_seconds),
        name="competition-expiration",
        daemon=True,
    )
    thread.start()
    try:
        yield
    finally:
        stop_event.set()
        thread.join(timeout=settings.auto_complete_interval_seconds + 5)


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(qr_router)
app.include_router(clothing_router)
app.include_router(wardrobe_router)
app.include_router(avatar_router)
app.include_router(competition_requests_router)
app.include_router(competitions_router)
app.include_router(votes_router)
app.include_router(leaderboard_router)
app.include_router(notifications_router)
app.include_router(admin_router)


@app.get("/health/db")
def db_health(db: Session = Depends(get_db)) -> dict:
    result = db.execute(text("SELECT 1")).scalar()
    return {"database": "ok", "result": result}