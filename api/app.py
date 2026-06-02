"""AstroML REST API — main FastAPI application.

Wires together all routers:
  - /api/v1/fraud/*       (Issue #254)
  - /api/v1/accounts/*    (Issue #252)
  - /api/v1/monitoring/*  (Issue #256)
  - /api/v1/loyalty/*     (Issue #255)

Usage:
"""AstroML REST API application.

Mounts all routers:
  - /api/v1/transactions  (issue #253)
  - /api/v1/fraud         (issue #249)
  - /api/v1/models        (issue #257)

Usage
-----
    uvicorn api.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routers import accounts_router, fraud_router, loyalty_router, monitoring_router
from api.routers.monitoring import record_latency


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    # Ensure loyalty tables exist (non-blocking; skipped if DB unavailable)
    try:
        from api.loyalty_models import LoyaltyBase  # noqa: PLC0415
        from astroml.db.session import engine  # noqa: PLC0415
        async with engine.begin() as conn:
            await conn.run_sync(LoyaltyBase.metadata.create_all)
    except Exception:  # noqa: BLE001
        pass

    # Start the existing batch scoring scheduler
    try:
        from astroml.api.scheduler import start_scheduler, stop_scheduler  # noqa: PLC0415
        from astroml.db.session import async_session_factory  # noqa: PLC0415
        start_scheduler(async_session_factory)
        yield
        await stop_scheduler()
    except Exception:  # noqa: BLE001
        yield


app = FastAPI(
    title="AstroML API",
    version="1.0.0",
    description="Fraud detection, account management, model monitoring, and loyalty points.",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Latency middleware ───────────────────────────────────────────────────────
@app.middleware("http")
async def _latency_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    record_latency((time.perf_counter() - start) * 1000)
    return response


# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(fraud_router)
app.include_router(accounts_router)
app.include_router(monitoring_router)
app.include_router(loyalty_router)


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}
