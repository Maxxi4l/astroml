"""Fraud Detection API — Issue #254.

Endpoints:
  POST /api/v1/fraud/score   — real-time anomaly scoring
  GET  /api/v1/fraud/alerts  — paginated fraud alerts
  GET  /api/v1/fraud/stats   — aggregated fraud statistics

Model loading
-------------
Models are loaded lazily on first request and cached in module-level state.
The active model version from the registry takes precedence over
``MODEL_CHECKPOINT_PATH`` when set.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import cast, func, select, Date
from sqlalchemy.orm import Session

from api.database import get_sync_db
from api.models.orm import FraudAlert
from api.schemas import (
    FraudAlertOut,
    FraudAlertsResponse,
    FraudStatsResponse,
    RiskPoint,
    ScoreRequest,
    ScoreResponse,
)
from api.services.scorer import invalidate_scorer_cache, load_scorer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/fraud", tags=["fraud"])


def _get_scorer():
    """Load and cache the InductiveAnomalyScorer. Returns None if unavailable."""
    return load_scorer()


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/score", response_model=ScoreResponse)
async def score_accounts(body: ScoreRequest):
    """Score up to 50 accounts for anomaly/fraud risk."""
    scorer = _get_scorer()
    if scorer is None:
        scores = {acc: 0.0 for acc in body.accounts}
        return ScoreResponse(scores=scores)

    ref_time = datetime.now(timezone.utc).timestamp()
    try:
        edges = [e.model_dump() for e in body.edges]
        scores = scorer.score_new_accounts(
            edges=edges,
            account_ids=body.accounts,
            ref_time=ref_time,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Scoring failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Scoring service temporarily unavailable") from exc

    return ScoreResponse(scores=scores)


@router.get("/alerts", response_model=FraudAlertsResponse)
def get_fraud_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_level: Optional[str] = Query(None, pattern="^(low|medium|high)$"),
    db: Session = Depends(get_sync_db),
):
    """Return paginated fraud alerts, optionally filtered by risk level."""
    q = select(FraudAlert)
    if risk_level:
        q = q.where(FraudAlert.risk_level == risk_level)
    q = q.order_by(FraudAlert.detected_at.desc())

    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.offset((page - 1) * page_size).limit(page_size)).all()
    return FraudAlertsResponse(
        data=[FraudAlertOut.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/stats", response_model=FraudStatsResponse)
def get_fraud_stats(db: Session = Depends(get_sync_db)):
    """Return aggregated fraud statistics."""
    def _count(level: str) -> int:
        return db.scalar(
            select(func.count(FraudAlert.id)).where(FraudAlert.risk_level == level)
        ) or 0

    total = db.scalar(select(func.count(FraudAlert.id))) or 0
    recent = db.scalars(
        select(FraudAlert).order_by(FraudAlert.detected_at.desc()).limit(10)
    ).all()

    daily = db.execute(
        select(
            cast(FraudAlert.detected_at, Date).label("day"),
            func.avg(FraudAlert.risk_score).label("avg_score"),
        )
        .group_by("day")
        .order_by("day")
        .limit(14)
    ).all()

    return FraudStatsResponse(
        total_alerts=total,
        high_risk=_count("high"),
        medium_risk=_count("medium"),
        low_risk=_count("low"),
        recent_alerts=[FraudAlertOut.model_validate(r) for r in recent],
        risk_over_time=[
            RiskPoint(date=str(row.day), score=round(float(row.avg_score), 4))
            for row in daily
        ],
    )


# Re-export for model activation hook
__all__ = ["router", "invalidate_scorer_cache"]
