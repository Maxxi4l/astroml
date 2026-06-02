"""Pydantic schemas shared across all API routers."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─── Fraud ────────────────────────────────────────────────────────────────────

class EdgeInput(BaseModel):
    src: str
    dst: str
    amount: float = 0.0
    timestamp: float = 0.0
    asset: str = "XLM"


class ScoreRequest(BaseModel):
    accounts: List[str] = Field(..., max_length=50)
    edges: List[EdgeInput] = Field(default_factory=list)


class ScoreResponse(BaseModel):
    scores: Dict[str, float]


class FraudAlertOut(BaseModel):
    id: int
    account_id: str
    pattern: Optional[str] = None
    risk_score: float
    risk_level: str
    description: Optional[str] = None
    detected_at: datetime

    class Config:
        from_attributes = True


class FraudAlertsResponse(BaseModel):
    data: List[FraudAlertOut]
    page: int
    page_size: int
    total: int


class RiskPoint(BaseModel):
    date: str
    score: float


class FraudStatsResponse(BaseModel):
    total_alerts: int
    high_risk: int
    medium_risk: int
    low_risk: int
    recent_alerts: List[FraudAlertOut]
    risk_over_time: List[RiskPoint]


# ─── Accounts ─────────────────────────────────────────────────────────────────

class AccountOut(BaseModel):
    account_id: str
    balance: Optional[float] = None
    sequence: Optional[int] = None
    home_domain: Optional[str] = None
    flags: int = 0
    last_modified_ledger: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AccountsResponse(BaseModel):
    data: List[AccountOut]
    page: int
    page_size: int
    total: int


class TransactionOut(BaseModel):
    hash: str
    ledger_sequence: int
    source_account: str
    created_at: datetime
    fee: int
    operation_count: int
    successful: bool
    memo_type: Optional[str] = None
    memo: Optional[str] = None

    class Config:
        from_attributes = True


class TransactionsResponse(BaseModel):
    data: List[TransactionOut]
    page: int
    page_size: int
    total: int


class FraudSummaryOut(BaseModel):
    account_id: str
    total_alerts: int
    high_risk: int
    medium_risk: int
    low_risk: int
    latest_score: Optional[float] = None


class LoyaltySummaryOut(BaseModel):
    account_id: str
    points_balance: int
    tier_id: str
    tier_name: str


# ─── Monitoring ───────────────────────────────────────────────────────────────

class ModelMetricsOut(BaseModel):
    accuracy: Optional[float] = None
    f1: Optional[float] = None
    auc: Optional[float] = None
    drift_score: Optional[float] = None
    recorded_at: Optional[datetime] = None


class PerformancePoint(BaseModel):
    date: str
    accuracy: Optional[float] = None
    f1: Optional[float] = None
    auc: Optional[float] = None


class DriftReport(BaseModel):
    features: Dict[str, float]
    overall_drift: float
    generated_at: datetime


class PredictionStats(BaseModel):
    total_predictions: int
    anomaly_rate: float
    avg_score: float
    period_days: int


class LatencyStats(BaseModel):
    p50_ms: float
    p95_ms: float
    p99_ms: float


# ─── Loyalty ──────────────────────────────────────────────────────────────────

class LoyaltyTierOut(BaseModel):
    id: str
    name: str
    threshold: int
    multiplier: float
    color: str


class BenefitOut(BaseModel):
    id: str
    title: str
    description: str


class NextTierInfo(BaseModel):
    tier: LoyaltyTierOut
    remaining_to_upgrade: int
    progress_pct: int


class LoyaltySummaryFull(BaseModel):
    current_tier: LoyaltyTierOut
    points_balance: int
    next_tier: Optional[NextTierInfo] = None
    benefits: List[BenefitOut]


class PointsTransactionOut(BaseModel):
    id: str
    date: str
    type: str  # earn | redeem | adjust
    points: int
    source: Optional[str] = None
    note: Optional[str] = None


class PointsHistoryResponse(BaseModel):
    data: List[PointsTransactionOut]
    page: int
    page_size: int
    total: int


class RedeemRequest(BaseModel):
    points: int = Field(..., gt=0)
    reward_id: Optional[str] = None


class RedeemResponse(BaseModel):
    new_balance: int
    transaction: PointsTransactionOut


class ReferralOut(BaseModel):
    url: str
    invited: int
    rewards: int
