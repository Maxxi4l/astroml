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

from fastapi import FastAPI

from api.routers.transactions import router as transactions_router
from api.routers.fraud import router as fraud_router
from api.routers.models import router as models_router

app = FastAPI(
    title="AstroML API",
    version="1.0.0",
    description="Fraud detection, transaction history, and model registry for AstroML.",
)

app.include_router(transactions_router)
app.include_router(fraud_router)
app.include_router(models_router)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"status": "ok"}
