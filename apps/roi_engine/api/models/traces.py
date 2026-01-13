"""
Trace & Session Pydantic models for the ROI Engine API.

Contains models for trace and session management.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════════
# Trace Models
# ═══════════════════════════════════════════════════════════════


class TraceResponse(BaseModel):
    """Response for a single trace."""

    id: str
    name: str
    timestamp: datetime
    session_id: str | None = None
    total_tokens: int = 0
    total_cost: float = 0.0
    latency_ms: float = 0.0
    tags: list[str] = []
    metadata: dict[str, Any] = {}


class TraceListResponse(BaseModel):
    """Response for trace listing."""

    traces: list[TraceResponse]
    total_count: int
    offset: int = 0
    limit: int = 50


class TraceDetailResponse(BaseModel):
    """Detailed trace response with generations."""

    id: str
    name: str
    timestamp: datetime
    session_id: str | None = None
    total_tokens: int = 0
    total_cost: float = 0.0
    latency_ms: float = 0.0
    tags: list[str] = []
    metadata: dict[str, Any] = {}
    input: Any = None
    output: Any = None
    generations: list[dict[str, Any]] = []


# ═══════════════════════════════════════════════════════════════
# Session Models
# ═══════════════════════════════════════════════════════════════


class SessionResponse(BaseModel):
    """Response for a single session."""

    id: str
    name: str
    created_at: datetime
    trace_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0


class SessionListResponse(BaseModel):
    """Response for session listing."""

    sessions: list[SessionResponse]
    total_count: int


# ═══════════════════════════════════════════════════════════════
# Activity Models
# ═══════════════════════════════════════════════════════════════


class ActivityEvent(BaseModel):
    """Single activity event."""

    event_type: str
    timestamp: datetime
    description: str
    spec_id: str | None = None
    trace_id: str | None = None
    value: float | None = None
    metadata: dict[str, Any] = {}


class RecentActivityResponse(BaseModel):
    """Response for recent activity."""

    events: list[ActivityEvent]
    total_count: int
