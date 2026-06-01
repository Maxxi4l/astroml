"""Fraud Detection API (issue #249).

Endpoints
---------
POST /api/v1/fraud/score   — Score one or more accounts
GET  /api/v1/fraud/alerts  — Recent fraud alerts (paginated, filterable)
GET  /api/v1/fraud/stats   — Aggregated fraud statistics

Model loading
-------------
Models are loaded lazily on first request and cached in module-level state.
If checkpoints are absent the /score endpoint returns 503 with a clear message
rather than crashing the server.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import torch
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.orm import FraudAlert, ModelRegistry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/fraud", tags=["fraud"])

MODEL_STORE_PATH = Path(os.environ.get("MODEL_STORE_PATH", "model_store"))

# ─── Model cache ─────────────────────────────────────────────────────────────

_scorer: Any = None          # InductiveAnomalyScorer once loaded
_scorer_loaded: bool = False  # True even if loading failed (avoids retry spam)


def _try_load_scorer() -> bool:
    """Attempt to load the active model checkpoint. Returns True on success."""
    global _scorer, _scorer_loaded
    if _scorer_loaded:
        return _scorer is not None

    _scorer_loaded = True
    try:
        from astroml.pipeline.scoring import InductiveAnomalyScorer  # noqa: F401
        from astroml.pipeline.inductive import InductiveGraphSAGE
        from astroml.models.deep_svdd import DeepSVDD
        from astroml.models.sage_encoder import InductiveSAGEEncoder

        # Look for the most recently modified .pth file under MODEL_STORE_PATH
        checkpoints = sorted(MODEL_STORE_PATH.rglob("*.pth"), key=lambda p: p.stat().st_mtime)
        if not checkpoints:
            logger.warning("No model checkpoints found in %s", MODEL_STORE_PATH)
            return False

        ckpt_path = checkpoints[-1]
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)

        input_dim = ckpt.get("input_dim", 8)
        hidden_dims = ckpt.get("hidden_dims", [64, 32])
        sage_hidden = ckpt.get("sage_hidden", 32)

        encoder = InductiveSAGEEncoder(input_dim=input_dim, hidden_dim=sage_hidden)
        if "sage_state" in ckpt:
            encoder.load_state_dict(ckpt["sage_state"])

        svdd = DeepSVDD(input_dim=sage_hidden, hidden_dims=hidden_dims)
        if "svdd_state" in ckpt:
            svdd.load_state_dict(ckpt["svdd_state"])
        if "center" in ckpt:
            svdd.center = ckpt["center"]

        pipeline = InductiveGraphSAGE(encoder=encoder, fanout=[10, 5])
        _scorer = InductiveAnomalyScorer(pipeline=pipeline, svdd=svdd)
        logger.info("Loaded fraud scorer from %s", ckpt_path)
        return True

    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load fraud scorer: %s", exc)
        _scorer = None
        return False


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ScoreRequest(BaseModel):
    accounts: list[str]
    edges: list[dict[str, Any]] = []


class ScoreResponse(BaseModel):
    scores: dict[str, float]


class AlertOut(BaseModel):
    id: int
    account_id: str
    pattern: Optional[str]
    risk_score: float
    risk_level: str
    description: Optional[str]
    detected_at: datetime

    model_config = {"from_attributes": True}


class AlertsResponse(BaseModel):
    data: list[AlertOut]
    page: int
    page_size: int
    total: int


class FraudStatsOut(BaseModel):
    total_alerts: int
    high_risk: int
    medium_risk: int
    low_risk: int
    recent_alerts: list[AlertOut]
    risk_over_time: list[dict[str, Any]]


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/score", response_model=ScoreResponse)
async def score_accounts(body: ScoreRequest):
    """Score one or more accounts for fraud.

    Returns anomaly scores in [0, ∞) — higher means more suspicious.
    Returns 503 if no trained model is available.
    """
    if not _try_load_scorer():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fraud scoring model is not available. Train and register a model first.",
        )

    import time
    ref_time = time.time()
    scores = _scorer.score_new_accounts(
        edges=body.edges,
        account_ids=body.accounts,
        ref_time=ref_time,
    )
    return ScoreResponse(scores=scores)


@router.get("/alerts", response_model=AlertsResponse)
async def list_alerts(
    risk_level: Optional[str] = Query(None, description="Filter by risk level: low|medium|high"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Return recent fraud alerts, optionally filtered by risk level."""
    q = select(FraudAlert)
    if risk_level:
        q = q.where(FraudAlert.risk_level == risk_level)

    total = (await db.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar_one()

    q = q.order_by(FraudAlert.detected_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return AlertsResponse(data=rows, page=page, page_size=page_size, total=total)


@router.get("/stats", response_model=FraudStatsOut)
async def fraud_stats(db: AsyncSession = Depends(get_db)):
    """Aggregated fraud statistics matching the FraudStats frontend type."""
    total = (await db.execute(
        select(func.count()).select_from(FraudAlert)
    )).scalar_one()

    high = (await db.execute(
        select(func.count()).where(FraudAlert.risk_level == "high")
    )).scalar_one()
    medium = (await db.execute(
        select(func.count()).where(FraudAlert.risk_level == "medium")
    )).scalar_one()
    low = (await db.execute(
        select(func.count()).where(FraudAlert.risk_level == "low")
    )).scalar_one()

    recent_rows = (await db.execute(
        select(FraudAlert).order_by(FraudAlert.detected_at.desc()).limit(10)
    )).scalars().all()

    # Daily risk score averages over the last 30 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    daily_rows = (await db.execute(
        select(
            func.date_trunc("day", FraudAlert.detected_at).label("day"),
            func.avg(FraudAlert.risk_score).label("avg_score"),
        )
        .where(FraudAlert.detected_at >= cutoff)
        .group_by(func.date_trunc("day", FraudAlert.detected_at))
        .order_by(func.date_trunc("day", FraudAlert.detected_at))
    )).all()

    risk_over_time = [
        {"date": str(r.day)[:10], "score": round(float(r.avg_score), 4)}
        for r in daily_rows
    ]

    return FraudStatsOut(
        total_alerts=total,
        high_risk=high,
        medium_risk=medium,
        low_risk=low,
        recent_alerts=recent_rows,
        risk_over_time=risk_over_time,
    )
