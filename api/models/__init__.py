"""API-layer ORM models (issue #251).

All models use the shared ``Base`` from ``astroml.db.schema`` so that
``alembic upgrade head`` creates every table in one pass.
"""
from api.models.orm import (
    Account,
    Transaction,
    FraudAlert,
    LoyaltyPoints,
    PointsTransaction,
    ModelRegistry,
)

__all__ = [
    "Account",
    "Transaction",
    "FraudAlert",
    "LoyaltyPoints",
    "PointsTransaction",
    "ModelRegistry",
]
