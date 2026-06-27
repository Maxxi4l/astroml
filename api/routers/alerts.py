"""Alerts API router (issue XXX)."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_sync_db
from api.models.orm import FraudAlert
from api.schemas import (
    PrioritizedAlertsResponse,
    PrioritizedAlertOut,
    TransactionSummaryOut,
)
from api.services.alert_prioritization import alert_prioritizer

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("/prioritized", response_model=PrioritizedAlertsResponse)
def get_prioritized_alerts(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_sync_db),
):
    """Get prioritized, deduplicated fraud alerts."""
    # Fetch recent alerts
    alerts = db.scalars(
        select(FraudAlert)
        .order_by(FraudAlert.detected_at.desc())
        .limit(limit * 2)  # Fetch extra to account for deduplication
    ).all()

    total_processed = len(alerts)

    # Process alerts
    processed, reduction_pct = alert_prioritizer.process_alerts(db, alerts)

    # Convert to output model
    data = []
    for enriched in processed:
        data.append(
            PrioritizedAlertOut(
                id=enriched.alert.id,
                account_id=enriched.alert.account_id,
                pattern=enriched.alert.pattern,
                risk_score=enriched.alert.risk_score,
                risk_level=enriched.alert.risk_level,
                priority_score=enriched.priority_score,
                priority_level=enriched.priority_level,
                explanation=enriched.explanation,
                detected_at=enriched.alert.detected_at,
                recent_transactions=[
                    TransactionSummaryOut(
                        hash=tx["hash"],
                        amount=tx["amount"],
                        asset_code=tx["asset_code"],
                        destination_account=tx["destination_account"],
                        created_at=tx["created_at"],
                    ) for tx in enriched.recent_transactions
                ],
                account_activity_score=enriched.account_activity_score,
                is_duplicate=enriched.is_duplicate,
                duplicate_of=enriched.duplicate_of,
            )
        )

    return PrioritizedAlertsResponse(
        data=data[:limit],
        deduplication_reduction_pct=reduction_pct,
        total_processed=total_processed,
        total_remaining=len(data),
    )
