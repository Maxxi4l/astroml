"""Authentication configuration (issue #240)."""
from __future__ import annotations

import os

SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or os.environ.get(
    "SECRET_KEY", "change-me-in-production"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get("ACCESS_TOKEN_EXPIRE_HOURS", "24"))
API_KEY_EXPIRE_DAYS = int(os.environ.get("API_KEY_EXPIRE_DAYS", "365"))

AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "true").lower() in ("1", "true", "yes")


def is_auth_enabled() -> bool:
    """Read AUTH_ENABLED at call time (supports test monkeypatching)."""
    return os.environ.get("AUTH_ENABLED", "true").lower() in ("1", "true", "yes")

DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

JWT_RATE_LIMIT_PER_MINUTE = int(os.environ.get("JWT_RATE_LIMIT_PER_MINUTE", "100"))
API_KEY_RATE_LIMIT_PER_MINUTE = int(os.environ.get("API_KEY_RATE_LIMIT_PER_MINUTE", "1000"))

PUBLIC_PATHS = frozenset({
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/auth/login",
})
