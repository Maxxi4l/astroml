"""HTTP auth and rate-limit middleware (issue #240, #331)."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from api.auth.config import is_auth_enabled, PUBLIC_PATHS
from api.auth.dependencies import authenticate_token
from api.auth.rate_limit import rate_limiter
from api.database import _sync_session_factory


class AuthMiddleware(BaseHTTPMiddleware):
    """Require JWT/API-key auth on protected routes and enforce rate limits."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if not is_auth_enabled() or path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        token = auth_header[7:]
        session = _sync_session_factory()()
        try:
            auth = authenticate_token(token, session)
        except Exception:  # noqa: BLE001
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
        finally:
            session.close()

        rate_key = f"{auth.auth_type}:{auth.subject}"
        allowed, retry_after = rate_limiter.is_allowed(rate_key, path, auth.auth_type)
        
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "retry_after": retry_after}
            )
            if retry_after is not None:
                response.headers["Retry-After"] = str(retry_after)
            return response

        request.state.auth = auth
        return await call_next(request)
