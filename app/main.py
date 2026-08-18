from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.bot.runner import start_polling_task, stop_polling_task
from app.routers.auth import router as auth_router
from app.routers.promo_code import router as promo_code_router

MINIAPP_DIR = Path(__file__).resolve().parent.parent / "miniapp"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await start_polling_task()
    try:
        yield
    finally:
        with suppress(Exception):
            await stop_polling_task()


app = FastAPI(title="CCI", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(promo_code_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/miniapp", StaticFiles(directory=MINIAPP_DIR, html=True), name="miniapp")
