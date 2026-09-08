import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

import logging
import pathlib

from app.core.config import settings
from app.core.database import get_db
from app.routers import (
    admin_router,
    auth_router,
    avatar_router,
    catalog_router,
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


# Cache-Control for everything we serve as a file.
#
# Without these the responses carry no caching headers at all, and Cloudflare
# applies its own default TTL by file extension. That is fine for the hashed
# bundles and actively wrong for index.html and sw.js: both keep their names
# across deploys, so a cached copy at the edge pins every visitor to an old
# build. It is how a shipped feature can be invisible in production while the
# container serves the new file correctly.
IMMUTABLE_PREFIXES = ("/app/assets/", "/admin-ui/assets/")
REVALIDATE_EXACT = ("/app/sw.js", "/app/index.html", "/admin-ui/index.html")


@app.middleware("http")
async def cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path

    if path.startswith(IMMUTABLE_PREFIXES):
        # Vite puts a content hash in the filename, so a given URL's bytes can
        # never change. Cache it for a year and never revalidate.
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path in REVALIDATE_EXACT or path in ("/app/", "/admin-ui/"):
        # Stable names, changing content: must be checked on every load.
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    elif path.startswith("/media/"):
        # Artwork changes only when a designer replaces a file, and a short
        # window of staleness there costs nothing.
        response.headers["Cache-Control"] = "public, max-age=3600"

    return response
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
app.include_router(catalog_router)
app.include_router(admin_router)


# Avatar and clothing art. Served by the API rather than a CDN because the
# whole set is a few hundred KB of SVG and one origin means one thing to
# deploy — and Telegram Mini Apps are strict about mixed content.
ROOT = pathlib.Path(__file__).resolve().parent.parent

MEDIA_DIR = ROOT / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


def _mount_spa(mount_path: str, dist: pathlib.Path, name: str) -> None:
    """Serve a built frontend, if it has been built.

    Mounted only when the directory exists so that running the API from a
    source checkout — for tests, or against `npm run dev` — does not fail at
    import time over a missing dist/. In the Docker image both are always
    present, because the build stage produces them.

    html=True makes the mount serve index.html at the mount root. The apps use
    hash routing, so every route lives in that one document and no server-side
    rewrite rule is needed for a deep link to survive a refresh.
    """
    if dist.is_dir():
        app.mount(mount_path, StaticFiles(directory=dist, html=True), name=name)
    else:
        logging.getLogger("cci").warning(
            "%s is not built (%s missing) — %s will 404", name, dist, mount_path
        )


# The Telegram Mini App / PWA, and the operators' admin panel.
_mount_spa("/app", ROOT / "miniapp" / "dist", "miniapp")
_mount_spa("/admin-ui", ROOT / "admin" / "dist", "admin")


@app.get("/oneidea/{_path:path}", include_in_schema=False)
@app.get("/oneidea", include_in_schema=False)
def legacy_miniapp_redirect(_path: str = "") -> RedirectResponse:
    """The Mini App used to live at /oneidea/.

    Whatever URL is configured in BotFather is what Telegram opens, and an
    operator updating it is a manual step that can be forgotten or done late.
    A redirect costs nothing and means the old link never turns into a blank
    screen for a player mid-fest.
    """
    return RedirectResponse(url="/app/", status_code=308)


@app.get("/config")
def public_config() -> dict:
    """The handful of settings the frontend cannot know on its own.

    Public by design and deliberately tiny: a bot's @handle is visible to
    anyone who can message it, and the Mini App URL is in BotFather. Nothing
    secret is reachable from here — the bot TOKEN never leaves the server.

    It exists so the browser/PWA sign-in can render the Telegram Login Widget,
    which needs the bot's handle, without the handle being baked into the
    JavaScript bundle at build time and going stale when the bot changes.
    """
    return {
        "bot_username": settings.telegram_bot_username.strip().lstrip("@"),
        "webapp_url": settings.telegram_webapp_url.strip(),
    }


@app.get("/health")
def health() -> dict:
    """Liveness. Deliberately does NOT touch the database — a health check
    that fails when Postgres blips takes the app out of rotation for a
    problem restarting the app cannot fix. /health/db is the one that
    reports the database."""
    return {"status": "ok"}


@app.get("/health/db")
def db_health(db: Session = Depends(get_db)) -> dict:
    result = db.execute(text("SELECT 1")).scalar()
    return {"database": "ok", "result": result}