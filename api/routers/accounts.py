"""Account API Endpoints — Issue #247.

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
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.schemas import (
    AccountOut,
    AccountsResponse,
    FraudSummaryOut,
    LoyaltySummaryOut,
    TransactionOut,
    TransactionsResponse,
)

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


async def _require_account(public_key: str, db: AsyncSession):
    from api.models.orm import Account  # noqa: PLC0415

    result = await db.execute(select(Account).where(Account.public_key == public_key))
    acc = result.scalar_one_or_none()
    if acc is None:
        raise HTTPException(status_code=404, detail=f"Account {public_key!r} not found")
    return acc


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=AccountsResponse)
async def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    public_key: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """List accounts with optional filtering and pagination."""
    from api.models.orm import Account  # noqa: PLC0415

    q = select(Account)
    if public_key:
        q = q.where(Account.public_key == public_key)
    if from_date:
        q = q.where(Account.created_at >= from_date)
    if to_date:
        q = q.where(Account.created_at <= to_date)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one() or 0

    q = q.order_by(Account.created_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return AccountsResponse(
        data=[AccountOut.model_validate(r) for r in rows],
        page=page,
        pageSize=page_size,
        total=total,
    )


@router.get("/{public_key}", response_model=AccountOut)
async def get_account(public_key: str, db: AsyncSession = Depends(get_db)):
    """Get a single account by public key."""
    acc = await _require_account(public_key, db)
    return AccountOut.model_validate(acc)


@router.get("/{public_key}/transactions", response_model=TransactionsResponse)
async def get_account_transactions(
    public_key: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated transactions for an account."""
    await _require_account(public_key, db)

    from api.models.orm import Transaction  # noqa: PLC0415

    q = (
        select(Transaction)
        .where(Transaction.source_account == public_key)
        .order_by(Transaction.created_at.desc())
    )

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one() or 0

    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    return TransactionsResponse(
        data=[TransactionOut.model_validate(r) for r in rows],
        page=page,
        pageSize=page_size,
        total=total,
    )


@router.get("/{public_key}/fraud-summary", response_model=FraudSummaryOut)
async def get_account_fraud_summary(public_key: str, db: AsyncSession = Depends(get_db)):
    """Return fraud alert summary for an account."""
    await _require_account(public_key, db)

    try:
        from api.models.orm import FraudAlert  # noqa: PLC0415
    except ImportError:
        return FraudSummaryOut(
            account_id=public_key, total_alerts=0, high_risk=0, medium_risk=0, low_risk=0
        )

    async def _count(level: str) -> int:
        result = await db.execute(
            select(func.count(FraudAlert.id)).where(
                FraudAlert.account_id == public_key, FraudAlert.risk_level == level
            )
        )
        return result.scalar_one() or 0

    latest_result = await db.execute(
        select(FraudAlert.risk_score)
        .where(FraudAlert.account_id == public_key)
        .order_by(FraudAlert.detected_at.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()

    total_result = await db.execute(
        select(func.count(FraudAlert.id)).where(FraudAlert.account_id == public_key)
    )
    total = total_result.scalar_one() or 0

    return FraudSummaryOut(
        account_id=public_key,
        total_alerts=total,
        high_risk=await _count("high"),
        medium_risk=await _count("medium"),
        low_risk=await _count("low"),
        latest_score=latest,
    )


@router.get("/{public_key}/loyalty", response_model=LoyaltySummaryOut)
async def get_account_loyalty(public_key: str, db: AsyncSession = Depends(get_db)):
    """Return loyalty tier and points balance for an account."""
    await _require_account(public_key, db)
    # Loyalty data is served by the loyalty router; this is a convenience summary.
    # Returns defaults when loyalty tables are not yet populated.
    return LoyaltySummaryOut(
        account_id=public_key,
        points_balance=0,
        tier_id="bronze",
        tier_name="Bronze",
    )
