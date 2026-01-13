"""
Metrics Pydantic models for the ROI Engine API.

Contains models for:
- HourlyMetric, HourlyMetricsResponse
- ErrorBreakdown, RecentError, ErrorMetricsResponse
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# =============================================================================
# Hourly Metrics Models
# =============================================================================


class HourlyMetric(BaseModel):
    """Metrics for a single hour."""

    hour: str  # ISO timestamp for the hour
    requests: int  # Number of traces/requests
    tokens: int  # Total tokens used
    cost: float  # Total cost in USD
    errors: int  # Number of errors


class HourlyMetricsResponse(BaseModel):
    """Response for hourly metrics endpoint."""

    metrics: list[HourlyMetric]
    period_hours: int
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_errors: int = 0


# =============================================================================
# Error Metrics Models
# =============================================================================


class ErrorBreakdown(BaseModel):
    """Breakdown of errors by type."""

    error_type: str
    count: int
    percentage: float
    last_occurrence: Optional[str] = None


class RecentError(BaseModel):
    """A recent error event."""

    spec_id: str
    error: str
    timestamp: str
    agent_type: str


class ErrorMetricsResponse(BaseModel):
    """Response for error metrics endpoint."""

    total_errors: int
    error_rate: float  # Percentage (0-100)
    breakdown: list[ErrorBreakdown]
    recent_errors: list[RecentError]
    period_hours: int = 24
