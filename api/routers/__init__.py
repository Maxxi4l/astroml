"""API routers package."""
from api.routers.fraud import router as fraud_router
from api.routers.accounts import router as accounts_router
from api.routers.monitoring import router as monitoring_router
from api.routers.loyalty import router as loyalty_router

__all__ = ["fraud_router", "accounts_router", "monitoring_router", "loyalty_router"]
from api.routers.transactions import router as transactions_router
from api.routers.fraud import router as fraud_router
from api.routers.models import router as models_router

__all__ = ["transactions_router", "fraud_router", "models_router"]
