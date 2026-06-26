"""Streaming Service Health API.

Endpoints:
  GET /api/v1/streaming/health — overall streaming health
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/streaming", tags=["streaming"])


# In-memory storage for streaming state (will be updated by streaming service)
class StreamState:
    def __init__(self):
        self.streams: Dict[str, Dict[str, Any]] = {}
        self.last_updated: Optional[float] = None


_stream_state = StreamState()


def update_stream_state(stream_id: str, state: Dict[str, Any]) -> None:
    """Update the state for a specific stream. Called by streaming service."""
    _stream_state.streams[stream_id] = state
    _stream_state.last_updated = time.time()


class StreamHealth(BaseModel):
    stream_id: str
    stream_type: str
    horizon_url: str
    is_healthy: bool
    status: str  # "active", "inactive", "error"
    cursor: Optional[str] = None
    processed_count: int = 0
    consecutive_failures: int = 0
    current_backoff_seconds: float = 0.0
    lag_seconds: Optional[float] = None


class StreamingHealthOut(BaseModel):
    overall_status: str  # "healthy", "degraded", "unhealthy"
    last_updated: Optional[float]
    streams: List[StreamHealth]


@router.get("/health", response_model=StreamingHealthOut)
def get_streaming_health():
    """Return overall health of all streaming services."""
    streams = []
    healthy_count = 0
    total_count = len(_stream_state.streams)
    
    for stream_id, state in _stream_state.streams.items():
        is_healthy = state.get("is_healthy", False)
        if is_healthy:
            healthy_count += 1
        
        streams.append(StreamHealth(
            stream_id=stream_id,
            stream_type=state.get("stream_type", "unknown"),
            horizon_url=state.get("horizon_url", "unknown"),
            is_healthy=is_healthy,
            status=state.get("status", "inactive"),
            cursor=state.get("cursor"),
            processed_count=state.get("processed_count", 0),
            consecutive_failures=state.get("consecutive_failures", 0),
            current_backoff_seconds=state.get("current_backoff", 0.0),
            lag_seconds=state.get("lag_seconds")
        ))
    
    # Determine overall status
    if total_count == 0:
        overall_status = "degraded"
    elif healthy_count == total_count:
        overall_status = "healthy"
    elif healthy_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return StreamingHealthOut(
        overall_status=overall_status,
        last_updated=_stream_state.last_updated,
        streams=streams
    )
