"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import engine
from app.models import Base
from app.routers import assessment, attempts, auth, events, me, progress, today
from app.worker import start_background_worker

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("pmcoach")

_worker_state: dict = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Convenience for local development. In a deployment, run Alembic migrations
    # instead (see server/README.md).
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)

    if settings.run_inline_worker:
        thread, stop = start_background_worker()
        _worker_state["thread"] = thread
        _worker_state["stop"] = stop
    logger.info(
        "PM Thinking Coach API ready (env=%s, evaluator=%s, inline_worker=%s)",
        settings.environment,
        settings.evaluator_provider,
        settings.run_inline_worker,
    )
    yield
    stop = _worker_state.get("stop")
    if stop is not None:
        stop.set()
    thread = _worker_state.get("thread")
    if thread is not None:
        thread.join(timeout=5)


app = FastAPI(
    title="PM Thinking Coach API",
    version="0.1.0",
    summary="Server-owned scoring, XP, dates and AI evaluation for the iOS MVP.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else [],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    me.router,
    assessment.router,
    today.router,
    attempts.router,
    progress.router,
    events.router,
):
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        "evaluatorProvider": settings.evaluator_provider,
        "devAuthEnabled": settings.allow_dev_auth and not settings.is_production,
    }
