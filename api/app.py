"""AstroML REST API — main FastAPI application.

Wires together all routers:
  - /api/v1/transactions      (Issue #248)
  - /api/v1/fraud/*           (Issue #254)
  - /api/v1/accounts/*        (Issue #247)
  - /api/v1/monitoring/*      (Issue #256)
  - /api/v1/loyalty/*         (Issue #255)
  - /api/v1/models/*          (Issue #237)
  - /api/v1/auth/*            (Issue #240)
  - /api/v1/ws/*              (Issue #239)
  - /api/v1/mentorship/*      (Contributors)

Usage
-----
    uvicorn api.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.auth.middleware import AuthMiddleware
from api.database import get_async_session_factory
from api.routers import (
    accounts_router,
    auth_router,
    fraud_router,
    loyalty_router,
    mentorship_router,
    models_router,
    monitoring_router,
    notifications_router,
    transactions_router,
    ws_router,
)
from api.routers.monitoring import record_latency
from api.routers.ws import poll_and_broadcast_transactions


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    session_factory = get_async_session_factory()

    try:
        from api.database import _sync_session_factory
        from api.routers.auth import ensure_default_admin

        db = _sync_session_factory()()
        try:
            ensure_default_admin(db)
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        pass

    try:
        from astroml.api.scheduler import build_score_fn, start_scheduler  # noqa: PLC0415

        if os.environ.get("DISABLE_SCHEDULER", "").lower() not in ("1", "true", "yes"):
            start_scheduler(session_factory, score_fn=build_score_fn())
    except Exception:  # noqa: BLE001
        pass

    poll_task = None
    if os.environ.get("DISABLE_WS_POLLER", "").lower() not in ("1", "true", "yes"):
        try:
            poll_task = asyncio.create_task(
                poll_and_broadcast_transactions(),
                name="ws-transaction-poller",
            )
        except Exception:  # noqa: BLE001
            poll_task = None

    yield

    try:
        from astroml.api.scheduler import stop_scheduler  # noqa: PLC0415

        await stop_scheduler()
    except Exception:  # noqa: BLE001
        pass

    if poll_task is not None:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="AstroML API",
    version="1.0.0",
    description="Fraud detection, account management, model monitoring, and loyalty points.",
    lifespan=lifespan,
)

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _latency_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    record_latency((time.perf_counter() - start) * 1000)
    return response


app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(fraud_router)
app.include_router(accounts_router)
app.include_router(monitoring_router)
app.include_router(loyalty_router)
app.include_router(models_router)
app.include_router(mentorship_router)
app.include_router(notifications_router)
app.include_router(ws_router)


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}
