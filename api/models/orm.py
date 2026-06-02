"""SQLAlchemy ORM models for the API backend (issue #251).

Extends the existing ``astroml.db.schema.Base`` so all tables are created
by a single ``alembic upgrade head``.

Models
------
Account         — Stellar account info (public_key, first_seen, last_active, balance)
Transaction     — Blockchain transactions (hash, ledger, source, dest, amount, asset, fee)
FraudAlert      — Anomaly detection results (account_id, pattern, risk_score, detected_at)
LoyaltyPoints   — Points balance per account (account_id, balance, tier, multiplier)
PointsTransaction — Earn/redeem/adjust records
ModelRegistry   — Registered model versions (name, version, path, metrics)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

# Reuse the project-wide declarative base so all tables live in one metadata.
from astroml.db.schema import Base

_ID = BigInteger().with_variant(Integer(), "sqlite")


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

class ApiAccount(Base):
    """Stellar account info for the API layer.

    Separate from the ingestion-layer ``accounts`` table so the API can
    store richer profile data without polluting the raw schema.
    """

    __tablename__ = "api_accounts"

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    public_key: Mapped[str] = mapped_column(String(56), nullable=False, unique=True)
    first_seen: Mapped[Optional[datetime]] = mapped_column()
    last_active: Mapped[Optional[datetime]] = mapped_column()
    balance: Mapped[Optional[float]] = mapped_column(Numeric)
    home_domain: Mapped[Optional[str]] = mapped_column(String(253))
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_api_accounts_public_key", "public_key"),
        Index("ix_api_accounts_last_active", "last_active"),
    )


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class ApiTransaction(Base):
    """Blockchain transaction record for the API layer."""

    __tablename__ = "api_transactions"

    hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    ledger_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    source_account: Mapped[str] = mapped_column(String(56), nullable=False)
    destination_account: Mapped[Optional[str]] = mapped_column(String(56))
    amount: Mapped[Optional[float]] = mapped_column(Numeric)
    asset_code: Mapped[Optional[str]] = mapped_column(String(12))
    asset_issuer: Mapped[Optional[str]] = mapped_column(String(56))
    fee: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    operation_type: Mapped[Optional[str]] = mapped_column(String(32))
    successful: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    memo_type: Mapped[Optional[str]] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_api_transactions_source_created_at", "source_account", "created_at"),
        Index("ix_api_transactions_dest_created_at", "destination_account", "created_at"),
        Index("ix_api_transactions_ledger", "ledger_sequence"),
    )


# ---------------------------------------------------------------------------
# FraudAlert
# ---------------------------------------------------------------------------

class FraudAlert(Base):
    """Anomaly detection result produced by the fraud scoring pipeline."""

    __tablename__ = "api_fraud_alerts"

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(String(56), nullable=False)
    pattern: Mapped[Optional[str]] = mapped_column(String(64))   # e.g. sybil_cluster
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)  # low/medium/high
    description: Mapped[Optional[str]] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_api_fraud_alerts_account_id", "account_id"),
        Index("ix_api_fraud_alerts_detected_at", "detected_at"),
        Index("ix_api_fraud_alerts_risk_level", "risk_level"),
    )

    @staticmethod
    def risk_level_for_score(score: float) -> str:
        if score >= 0.8:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"


# ---------------------------------------------------------------------------
# LoyaltyPoints
# ---------------------------------------------------------------------------

class LoyaltyPoints(Base):
    """Points balance per account."""

    __tablename__ = "loyalty_points"

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(String(56), nullable=False, unique=True)
    balance: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    tier: Mapped[str] = mapped_column(String(32), nullable=False, server_default="bronze")
    multiplier: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_loyalty_points_account_id", "account_id"),
    )


# ---------------------------------------------------------------------------
# PointsTransaction
# ---------------------------------------------------------------------------

class PointsTransaction(Base):
    """Earn / redeem / adjust record for loyalty points."""

    __tablename__ = "points_transactions"

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(String(56), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)   # earn|redeem|adjust
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(128))
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_points_transactions_account_id", "account_id"),
        Index("ix_points_transactions_created_at", "created_at"),
    )


# ---------------------------------------------------------------------------
# ModelRegistry
# ---------------------------------------------------------------------------

class ModelRegistry(Base):
    """Registered model version for the model registry (issue #257)."""

    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    metrics: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql")
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="inactive"
    )  # inactive | active | deprecated
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_model_registry_name_version", "name", "version", unique=True),
        Index("ix_model_registry_status", "status"),
    )


# ---------------------------------------------------------------------------
# Auth (issue #240)
# ---------------------------------------------------------------------------

class User(Base):
    """Dashboard/API user for JWT authentication."""

    __tablename__ = "api_users"

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    scopes: Mapped[Optional[list]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, server_default="[]"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())


class ApiKey(Base):
    """Machine-to-machine API key."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(_ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(_ID, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[Optional[list]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, server_default="[]"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_key_hash", "key_hash"),
    )


# Backward-compatible aliases removed — use ApiAccount / ApiTransaction to avoid
# SQLAlchemy mapper name collisions with astroml.db.schema.
