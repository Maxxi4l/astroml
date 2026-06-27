"""Token bucket rate limiting with per-endpoint configuration (issue #331)."""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

from api.auth.config import API_KEY_RATE_LIMIT_PER_MINUTE, JWT_RATE_LIMIT_PER_MINUTE


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    tokens: float
    last_refill: float
    capacity: float
    refill_rate: float  # tokens per second


@dataclass
class RateLimitConfig:
    """Per-endpoint rate limit configuration."""

    requests_per_minute: int = 60
    burst_size: int = 10


class RateLimiter:
    """Token bucket rate limiter with per-endpoint configuration and metrics."""

    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = Lock()
        self._metrics: dict[str, int] = defaultdict(int)
        self._endpoint_configs: dict[str, RateLimitConfig] = {
            "/api/v1/auth/login": RateLimitConfig(requests_per_minute=5, burst_size=2),
            "/api/v1/transactions": RateLimitConfig(requests_per_minute=100, burst_size=20),
            "/api/v1/fraud": RateLimitConfig(requests_per_minute=50, burst_size=10),
            "/api/v1/accounts": RateLimitConfig(requests_per_minute=30, burst_size=5),
            "/api/v1/monitoring": RateLimitConfig(requests_per_minute=60, burst_size=10),
        }

    def _get_endpoint_config(self, path: str) -> RateLimitConfig:
        """Get rate limit config for an endpoint."""
        # Check for exact match first
        if path in self._endpoint_configs:
            return self._endpoint_configs[path]
        
        # Check for prefix match
        for endpoint_path, config in self._endpoint_configs.items():
            if path.startswith(endpoint_path):
                return config
        
        # Default config
        return RateLimitConfig(requests_per_minute=60, burst_size=10)

    def is_allowed(
        self,
        key: str,
        path: str,
        auth_type: str = "jwt",
    ) -> tuple[bool, Optional[int]]:
        """Check if request is allowed using token bucket algorithm.
        
        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        config = self._get_endpoint_config(path)
        
        # Adjust limits based on auth type
        if auth_type == "api_key":
            requests_per_minute = API_KEY_RATE_LIMIT_PER_MINUTE
        else:
            requests_per_minute = JWT_RATE_LIMIT_PER_MINUTE
        
        # Use endpoint-specific limit if it's more restrictive
        requests_per_minute = min(requests_per_minute, config.requests_per_minute)
        
        capacity = config.burst_size
        refill_rate = requests_per_minute / 60.0  # tokens per second
        
        now = time.monotonic()
        
        with self._lock:
            bucket = self._buckets.get(key)
            
            if bucket is None:
                bucket = TokenBucket(
                    tokens=capacity,
                    last_refill=now,
                    capacity=capacity,
                    refill_rate=refill_rate,
                )
                self._buckets[key] = bucket
            
            # Refill tokens
            time_passed = now - bucket.last_refill
            bucket.tokens = min(
                bucket.capacity,
                bucket.tokens + time_passed * refill_rate,
            )
            bucket.last_refill = now
            
            # Check if request is allowed
            if bucket.tokens >= 1:
                bucket.tokens -= 1
                self._metrics[f"rate_limit_allowed:{path}"] += 1
                return True, None
            else:
                self._metrics[f"rate_limit_denied:{path}"] += 1
                # Calculate retry-after
                retry_after = int((1 - bucket.tokens) / refill_rate)
                return False, retry_after

    def get_metrics(self) -> dict[str, int]:
        """Get rate limiting metrics."""
        with self._lock:
            return dict(self._metrics)

    def reset_metrics(self) -> None:
        """Reset rate limiting metrics."""
        with self._lock:
            self._metrics.clear()

    def set_endpoint_config(self, path: str, config: RateLimitConfig) -> None:
        """Set rate limit config for a specific endpoint."""
        with self._lock:
            self._endpoint_configs[path] = config


rate_limiter = RateLimiter()
