"""API routers package."""
from api.routers.accounts import router as accounts_router
from api.routers.auth import router as auth_router
from api.routers.errors import router as errors_router
from api.routers.fraud import router as fraud_router
from api.routers.loyalty import router as loyalty_router
from api.routers.mentorship import router as mentorship_router
from api.routers.models import router as models_router
from api.routers.monitoring import router as monitoring_router
from api.routers.notifications import router as notifications_router
from api.routers.contributors import router as contributors_router
from api.routers.transactions import router as transactions_router
from api.routers.onboarding import router as onboarding_router
from api.routers.ws import router as ws_router

__all__ = [
    "accounts_router",
    "contributors_router",
    "auth_router",
    "errors_router",
    "fraud_router",
    "loyalty_router",
    "mentorship_router",
    "models_router",
    "monitoring_router",
    "notifications_router",
    "onboarding_router",
    "transactions_router",
    "ws_router",
]
