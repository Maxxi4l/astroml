"""In-memory rate limiting (issue #240)."""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from api.auth.config import API_KEY_RATE_LIMIT_PER_MINUTE, JWT_RATE_LIMIT_PER_MINUTE


@dataclass
class _Bucket:
    timestamps: list[float] = field(default_factory=list)


class RateLimiter:
    """Sliding-window rate limiter keyed by identity string."""

    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = defaultdict(_Bucket)
        self._lock = Lock()

    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._buckets[key]
            bucket.timestamps = [t for t in bucket.timestamps if t > cutoff]
            if len(bucket.timestamps) >= limit:
                return False
            bucket.timestamps.append(now)
            return True

    def limit_for_auth_type(self, auth_type: str) -> int:
        if auth_type == "api_key":
            return API_KEY_RATE_LIMIT_PER_MINUTE
        return JWT_RATE_LIMIT_PER_MINUTE


rate_limiter = RateLimiter()
