"""API routers package."""
from api.routers.accounts import router as accounts_router
from api.routers.audit import router as audit_router
from api.routers.auth import router as auth_router
from api.routers.backup import router as backup_router
from api.routers.chat import router as chat_router
from api.routers.contact import router as contact_router
from api.routers.errors import router as errors_router
from api.routers.faq import router as faq_router
from api.routers.feedback import router as feedback_router
from api.routers.fraud import router as fraud_router
from api.routers.loyalty import router as loyalty_router
from api.routers.mentorship import router as mentorship_router
from api.routers.models import router as models_router
from api.routers.monitoring import router as monitoring_router
from api.routers.notifications import router as notifications_router
from api.routers.contributors import router as contributors_router
from api.routers.rate_limit import router as rate_limit_router
from api.routers.transactions import router as transactions_router
from api.routers.onboarding import router as onboarding_router
from api.routers.validation import router as validation_router
from api.routers.ws import router as ws_router
from api.routers.streaming import router as streaming_router
from api.routers.llm import router as llm_router
from api.routers.reports import router as reports_router
from api.routers.alerts import router as alerts_router

__all__ = [
    "accounts_router",
    "audit_router",
    "backup_router",
    "chat_router",
    "contact_router",
    "contributors_router",
    "auth_router",
    "errors_router",
    "faq_router",
    "feedback_router",
    "fraud_router",
    "loyalty_router",
    "mentorship_router",
    "models_router",
    "monitoring_router",
    "notifications_router",
    "onboarding_router",
    "rate_limit_router",
    "transactions_router",
    "validation_router",
    "ws_router",
    "streaming_router",
    "llm_router",
    "reports_router",
    "alerts_router",
]
