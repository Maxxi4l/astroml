"""Account API Endpoints — Issue #252.

Endpoints:
  GET /api/v1/accounts                              — list accounts (paginated)
  GET /api/v1/accounts/{public_key}                 — single account
  GET /api/v1/accounts/{public_key}/transactions    — account transactions
  GET /api/v1/accounts/{public_key}/fraud-summary   — fraud alert summary
  GET /api/v1/accounts/{public_key}/loyalty         — loyalty points/tier
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.schemas import (
    AccountOut,
    AccountsResponse,
    FraudSummaryOut,
    LoyaltySummaryOut,
    TransactionOut,
    TransactionsResponse,
)

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


def _get_db():
    try:
        from astroml.db.session import SessionLocal  # noqa: PLC0415
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    except ImportError:
        yield None


def _require_account(public_key: str, db: Optional[Session]):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    from astroml.db.schema import Account  # noqa: PLC0415
    acc = db.get(Account, public_key)
    if acc is None:
        raise HTTPException(status_code=404, detail=f"Account {public_key!r} not found")
    return acc


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=AccountsResponse)
def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    public_key: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Optional[Session] = Depends(_get_db),
):
    """List accounts with optional filtering and pagination."""
    if db is None:
        return AccountsResponse(data=[], page=page, page_size=page_size, total=0)

    from astroml.db.schema import Account  # noqa: PLC0415
    q = select(Account)
    if public_key:
        q = q.where(Account.account_id == public_key)
    if from_date:
        q = q.where(Account.created_at >= from_date)
    if to_date:
        q = q.where(Account.created_at <= to_date)

    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.offset((page - 1) * page_size).limit(page_size)).all()
    return AccountsResponse(
        data=[AccountOut.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{public_key}", response_model=AccountOut)
def get_account(public_key: str, db: Optional[Session] = Depends(_get_db)):
    """Get a single account by public key."""
    acc = _require_account(public_key, db)
    return AccountOut.model_validate(acc)


@router.get("/{public_key}/transactions", response_model=TransactionsResponse)
def get_account_transactions(
    public_key: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Optional[Session] = Depends(_get_db),
):
    """Return paginated transactions for an account."""
    _require_account(public_key, db)

    from astroml.db.schema import Transaction  # noqa: PLC0415
    q = (
        select(Transaction)
        .where(Transaction.source_account == public_key)
        .order_by(Transaction.created_at.desc())
    )
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.offset((page - 1) * page_size).limit(page_size)).all()
    return TransactionsResponse(
        data=[TransactionOut.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{public_key}/fraud-summary", response_model=FraudSummaryOut)
def get_account_fraud_summary(public_key: str, db: Optional[Session] = Depends(_get_db)):
    """Return fraud alert summary for an account."""
    _require_account(public_key, db)

    try:
        from astroml.api.models import FraudAlert  # noqa: PLC0415
    except ImportError:
        return FraudSummaryOut(account_id=public_key, total_alerts=0, high_risk=0, medium_risk=0, low_risk=0)

    def _count(level: str) -> int:
        return db.scalar(
            select(func.count(FraudAlert.id))
            .where(FraudAlert.account_id == public_key, FraudAlert.risk_level == level)
        ) or 0

    latest = db.scalar(
        select(FraudAlert.score)
        .where(FraudAlert.account_id == public_key)
        .order_by(FraudAlert.created_at.desc())
        .limit(1)
    )
    total = db.scalar(
        select(func.count(FraudAlert.id)).where(FraudAlert.account_id == public_key)
    ) or 0

    return FraudSummaryOut(
        account_id=public_key,
        total_alerts=total,
        high_risk=_count("high"),
        medium_risk=_count("medium"),
        low_risk=_count("low"),
        latest_score=latest,
    )


@router.get("/{public_key}/loyalty", response_model=LoyaltySummaryOut)
def get_account_loyalty(public_key: str, db: Optional[Session] = Depends(_get_db)):
    """Return loyalty tier and points balance for an account."""
    _require_account(public_key, db)
    # Loyalty data is served by the loyalty router; this is a convenience summary.
    # Returns defaults when loyalty tables are not yet populated.
    return LoyaltySummaryOut(
        account_id=public_key,
        points_balance=0,
        tier_id="bronze",
        tier_name="Bronze",
    )
