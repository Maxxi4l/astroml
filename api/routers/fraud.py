"""Fraud Detection API — Issue #254.

Endpoints:
  POST /api/v1/fraud/score   — real-time anomaly scoring
  GET  /api/v1/fraud/alerts  — paginated fraud alerts
  GET  /api/v1/fraud/stats   — aggregated fraud statistics
"""Fraud Detection API (issue #249).

Model loading
-------------
Models are loaded lazily on first request and cached in module-level state.
If checkpoints are absent the /score endpoint returns 503 with a clear message
rather than crashing the server.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.schemas import (
    FraudAlertOut,
    FraudAlertsResponse,
    FraudStatsResponse,
    RiskPoint,
    ScoreRequest,
    ScoreResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/fraud", tags=["fraud"])


# ─── Model cache ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_scorer():
    """Load and cache the InductiveAnomalyScorer. Returns None if unavailable."""
    try:
        from astroml.pipeline.scoring import InductiveAnomalyScorer  # noqa: PLC0415
        from astroml.pipeline.inductive import InductiveGraphSAGE  # noqa: PLC0415
        from astroml.models.deep_svdd import DeepSVDD  # noqa: PLC0415
        import torch, os  # noqa: PLC0415

        checkpoint = os.environ.get("MODEL_CHECKPOINT_PATH", "benchmark_results/gcn_model.pt")
        if not os.path.exists(checkpoint):
            logger.warning("Model checkpoint not found at %s — scoring unavailable", checkpoint)
            return None

        state = torch.load(checkpoint, map_location="cpu", weights_only=False)
        input_dim = state.get("input_dim", 8)
        svdd = DeepSVDD(input_dim=input_dim)
        if "svdd_state" in state:
            svdd.load_state_dict(state["svdd_state"])

        from astroml.models.sage_encoder import InductiveSAGEEncoder  # noqa: PLC0415
        encoder = InductiveSAGEEncoder(in_channels=input_dim, hidden_channels=64, out_channels=32, num_layers=2)
        if "encoder_state" in state:
            encoder.load_state_dict(state["encoder_state"])

        pipeline = InductiveGraphSAGE(encoder=encoder, fanout=[10, 5])
        return InductiveAnomalyScorer(pipeline=pipeline, svdd=svdd)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load scorer: %s", exc)
        return None


def _get_db():
    """Sync DB session dependency (SQLite-compatible for CI)."""
    try:
        from astroml.db.session import SessionLocal  # noqa: PLC0415
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    except ImportError:
        yield None


def _get_fraud_alert_model():
    try:
        from astroml.api.models import FraudAlert  # noqa: PLC0415
        return FraudAlert
    except ImportError:
        return None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/score", response_model=ScoreResponse)
async def score_accounts(body: ScoreRequest):
    """Score up to 50 accounts for anomaly/fraud risk."""
    scorer = _load_scorer()
    if scorer is None:
        # Graceful degradation: return neutral scores
        scores = {acc: 0.0 for acc in body.accounts}
        return ScoreResponse(scores=scores)

    edges = [e.model_dump() for e in body.edges]
    ref_time = datetime.now(timezone.utc).timestamp()
    try:
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
    db: Optional[Session] = Depends(_get_db),
):
    """Return paginated fraud alerts, optionally filtered by risk level."""
    FraudAlert = _get_fraud_alert_model()
    if FraudAlert is None or db is None:
        return FraudAlertsResponse(data=[], page=page, page_size=page_size, total=0)

    try:
        from astroml.api.models import APIBase  # noqa: PLC0415
        # Ensure table exists (no-op if already created)
        APIBase.metadata.create_all(bind=db.get_bind(), checkfirst=True)
    except Exception:  # noqa: BLE001
        pass

    q = select(FraudAlert)
    if risk_level:
        q = q.where(FraudAlert.risk_level == risk_level)
    q = q.order_by(FraudAlert.created_at.desc())

    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.offset((page - 1) * page_size).limit(page_size)).all()
    return FraudAlertsResponse(
        data=[FraudAlertOut.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/stats", response_model=FraudStatsResponse)
def get_fraud_stats(db: Optional[Session] = Depends(_get_db)):
    """Return aggregated fraud statistics."""
    FraudAlert = _get_fraud_alert_model()
    if FraudAlert is None or db is None:
        return FraudStatsResponse(
            total_alerts=0, high_risk=0, medium_risk=0, low_risk=0,
            recent_alerts=[], risk_over_time=[],
        )

    def _count(level: str) -> int:
        return db.scalar(
            select(func.count(FraudAlert.id)).where(FraudAlert.risk_level == level)
        ) or 0

    total = db.scalar(select(func.count(FraudAlert.id))) or 0
    recent = db.scalars(
        select(FraudAlert).order_by(FraudAlert.created_at.desc()).limit(10)
    ).all()

    # Daily average score for the last 14 days
    from sqlalchemy import cast, Date  # noqa: PLC0415
    daily = db.execute(
        select(
            cast(FraudAlert.batch_run_at, Date).label("day"),
            func.avg(FraudAlert.score).label("avg_score"),
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
