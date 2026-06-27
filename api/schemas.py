"""Pydantic schemas shared across all API routers."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


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
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    f1_score: Optional[float] = None   # alias populated from f1 for compatibility
    auc: Optional[float] = None
    auc_roc: Optional[float] = None    # alias populated from auc for compatibility
    drift_score: Optional[float] = None
    recorded_at: Optional[datetime] = None


class PerformancePoint(BaseModel):
    date: str
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
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


# ─── Mentorship ────────────────────────────────────────────────────────────

class MentorProfileIn(BaseModel):
    bio: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    years_experience: int = Field(ge=0)
    preferred_session_day: Optional[str] = None
    max_mentees: int = Field(default=3, ge=1, le=10)


class MentorProfileOut(BaseModel):
    id: int
    github_username: str
    bio: Optional[str] = None
    skills: List[str]
    years_experience: int
    preferred_session_day: Optional[str] = None
    max_mentees: int
    is_available: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MenteeProfileIn(BaseModel):
    bio: Optional[str] = None
    learning_interests: List[str] = Field(default_factory=list)
    years_experience: int = Field(ge=0)
    preferred_session_day: Optional[str] = None
    goals: Optional[str] = None


class MenteeProfileOut(BaseModel):
    id: int
    github_username: str
    bio: Optional[str] = None
    learning_interests: List[str]
    years_experience: int
    preferred_session_day: Optional[str] = None
    goals: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MentorMatchOut(BaseModel):
    mentor_id: int
    mentor_username: str
    skill_overlap: float
    experience_gap: float
    availability_match: float
    total_score: float


class MentorshipOut(BaseModel):
    id: int
    mentor_id: int
    mentor_username: str
    mentee_id: int
    mentee_username: str
    status: str
    match_score: float
    started_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MentorshipSessionIn(BaseModel):
    duration_minutes: int = Field(gt=0, le=480)  # max 8 hours
    topic: str = Field(min_length=3, max_length=256)
    notes: Optional[str] = None


class MentorshipSessionOut(BaseModel):
    id: int
    mentorship_id: int
    session_date: datetime
    duration_minutes: int
    topic: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class MentorshipFeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    feedback_text: Optional[str] = None


class MentorshipFeedbackOut(BaseModel):
    id: int
    session_id: int
    rating: int
    feedback_text: Optional[str] = None
    is_mentor_feedback: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MentorshipMetrics(BaseModel):
    total_sessions: int
    total_hours: float
    avg_rating: float
    topics_covered: List[str]
    last_session_date: Optional[datetime] = None


class MentorMetrics(BaseModel):
    total_mentees: int
    total_sessions: int
    total_hours: float
    avg_rating: float


class MentorshipListResponse(BaseModel):
    data: List[MentorshipOut]
    page: int
    page_size: int
    total: int


class MentorListResponse(BaseModel):
    data: List[MentorProfileOut]
    page: int
    page_size: int
    total: int


class MenteeListResponse(BaseModel):
    data: List[MenteeProfileOut]
    page: int
    page_size: int
    total: int


# ─── Notifications ─────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: int
    event_type: str
    title: str
    content: Optional[str] = None
    link: Optional[str] = None
    actor: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    data: List[NotificationOut]
    unread_count: int


class NotificationPreferenceIn(BaseModel):
    email_enabled: bool = True
    slack_enabled: bool = False
    discord_enabled: bool = False
    pr_comments: bool = True
    pr_mentions: bool = True
    issue_comments: bool = True
    issue_mentions: bool = True
    review_requests: bool = True
    digest_frequency: str = "weekly"  # daily|weekly|never
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None


class NotificationPreferenceOut(BaseModel):
    id: int
    user_id: int
    email_enabled: bool
    slack_enabled: bool
    discord_enabled: bool
    pr_comments: bool
    pr_mentions: bool
    issue_comments: bool
    issue_mentions: bool
    review_requests: bool
    digest_frequency: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookEventIn(BaseModel):
    event_type: str  # pr_comment|issue_comment|review_request|pr_merged
    pr_number: Optional[int] = None
    issue_number: Optional[int] = None
    commenter: Optional[str] = None
    content: Optional[str] = None
    reviewer_id: Optional[int] = None
    author_id: Optional[int] = None
    repo: str
    link: str


class DigestEmailOut(BaseModel):
    user_id: int
    period: str
    notifications_count: int
    generated_at: datetime


# ─── Onboarding ────────────────────────────────────────────────────────────

class OnboardingStepIn(BaseModel):
    step: str


class OnboardingChecklistItem(BaseModel):
    step: str
    label: str
    completed: bool


class OnboardingProgressOut(BaseModel):
    github_username: str
    checklist: List[OnboardingChecklistItem]
    completed_count: int
    total_steps: int
    progress_pct: int
    is_complete: bool
    started_at: str
    last_updated: str


# ─── FAQ (issue #307) ───────────────────────────────────────────────────────────

class FAQOut(BaseModel):
    id: int
    category: str
    question: str
    answer: str
    order: int
    is_published: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FAQIn(BaseModel):
    category: str = Field(..., min_length=1, max_length=64)
    question: str = Field(..., min_length=1, max_length=512)
    answer: str = Field(..., min_length=1)
    order: int = Field(default=0, ge=0)
    is_published: bool = True


class FAQUpdateIn(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=64)
    question: Optional[str] = Field(None, min_length=1, max_length=512)
    answer: Optional[str] = Field(None, min_length=1)
    order: Optional[int] = Field(None, ge=0)
    is_published: Optional[bool] = None


class FAQListResponse(BaseModel):
    data: List[FAQOut]
    categories: List[str]
    total: int


class FAQFeedbackIn(BaseModel):
    is_helpful: bool
    user_comment: Optional[str] = None


class FAQFeedbackOut(BaseModel):
    id: int
    faq_id: int
    is_helpful: bool
    user_comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FAQSuggestionIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=512)
    suggested_answer: Optional[str] = None
    category: Optional[str] = Field(None, max_length=64)


class FAQSuggestionOut(BaseModel):
    id: int
    question: str
    suggested_answer: Optional[str] = None
    category: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FAQSuggestionListResponse(BaseModel):
    data: List[FAQSuggestionOut]
    page: int
    page_size: int
    total: int


# ─── Contact / Support tickets (issue #305) ─────────────────────────────────

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ContactFormIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)
    # reCAPTCHA token from the frontend widget; optional when verification is off.
    recaptcha_token: Optional[str] = None

    @field_validator("name", "subject", "message")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v.strip()

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip()
        if not _EMAIL_RE.match(v):
            raise ValueError("invalid email address")
        return v


class SupportTicketOut(BaseModel):
    reference: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContactSubmitResponse(BaseModel):
    message: str
    ticket: SupportTicketOut
