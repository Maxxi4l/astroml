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

from importlib import import_module
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
except Exception:  # noqa: BLE001
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    def generate_latest() -> bytes:
        return b""

from api.auth.middleware import AuthMiddleware
from api.audit_middleware import AuditLoggingMiddleware
from api.config import settings
from api.database import get_async_session_factory
from api.tracing import setup_tracing
from api.validation_middleware import ValidationMiddleware
from api.routers import (
    accounts_router,
    audit_router,
    auth_router,
    backup_router,
    chat_router,
    contact_router,
    contributors_router,
    errors_router,
    faq_router,
    feedback_router,
    fraud_router,
    loyalty_router,
    mentorship_router,
    models_router,
    monitoring_router,
    notifications_router,
    onboarding_router,
    rate_limit_router,
    transactions_router,
    validation_router,
    ws_router,
    streaming_router,
    llm_router,
    reports_router,
    alerts_router,
    sentiment_router,
)
from api.routers.monitoring import record_latency
from api.routers.ws import poll_and_broadcast_transactions


def _optional_router(module_name: str, attr_name: str = "router"):
    try:
        module = import_module(module_name)
    except Exception:  # noqa: BLE001
        return None
    return getattr(module, attr_name, None)


compliance_router = _optional_router("api.routers.compliance")
discussions_router = _optional_router("api.routers.discussions")
llm_health_router = _optional_router("api.routers.llm_health")
voice_router = _optional_router("api.routers.voice")
query_router = _optional_router("api.routers.query")
health_router = _optional_router("api.routers.health")
admin_router = _optional_router("api.routers.admin")

graphql_app = None
try:
    from strawberry.fastapi import GraphQLRouter
    from api.graphql.context import get_graphql_context
    from api.graphql.schema import schema
except Exception:  # noqa: BLE001
    GraphQLRouter = None
    get_graphql_context = None
    schema = None
else:
    if GraphQLRouter is not None and schema is not None:
        graphql_app = GraphQLRouter(schema, context_getter=get_graphql_context)

# Setup distributed tracing (issue #336)
_tracer_provider = setup_tracing()


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
app.add_middleware(ValidationMiddleware)
app.add_middleware(AuditLoggingMiddleware)
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
app.include_router(audit_router)
app.include_router(rate_limit_router)
app.include_router(errors_router)
app.include_router(contact_router)
app.include_router(transactions_router)
app.include_router(fraud_router)
app.include_router(accounts_router)
app.include_router(monitoring_router)
app.include_router(loyalty_router)
app.include_router(models_router)
app.include_router(contributors_router)
app.include_router(mentorship_router)
app.include_router(notifications_router)
app.include_router(onboarding_router)
app.include_router(faq_router)
app.include_router(feedback_router)
app.include_router(validation_router)
app.include_router(backup_router)
app.include_router(chat_router)
app.include_router(ws_router)
app.include_router(streaming_router)
app.include_router(llm_router)
app.include_router(reports_router)
app.include_router(alerts_router)
app.include_router(sentiment_router)

if compliance_router is not None:
    app.include_router(compliance_router)
if discussions_router is not None:
    app.include_router(discussions_router)
if voice_router is not None:
    app.include_router(voice_router)
if llm_health_router is not None:
    app.include_router(llm_health_router)
if health_router is not None:
    app.include_router(health_router)
if admin_router is not None:
    app.include_router(admin_router)
if graphql_app is not None:
    app.include_router(graphql_app, prefix="/graphql")
if query_router is not None:
    app.include_router(query_router)


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}


@app.get("/api/v1", tags=["ops"])
async def api_root():
    return {"version": settings.api_version, "status": "ok"}


@app.get("/metrics", tags=["ops"])
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


if os.environ.get("ENV", "development") == "development" and graphql_app is not None:
    @app.get("/graphql/playground")
    async def graphql_playground():
        from strawberry.fastapi import GraphQLPlayground

        return GraphQLPlayground()
