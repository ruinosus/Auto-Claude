"""
Metrics Routes - Hourly and error metrics endpoints.

Endpoints:
- GET /metrics/hourly - Get hourly metrics (requests, tokens, cost, errors)
- GET /metrics/errors - Get error metrics and breakdown
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from core import get_langfuse_client, TraceFilter
from api.models import (
    ErrorBreakdown,
    ErrorMetricsResponse,
    HourlyMetric,
    HourlyMetricsResponse,
    RecentError,
)


router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get(
    "/hourly",
    response_model=HourlyMetricsResponse,
    summary="Get hourly metrics",
    description="Get metrics aggregated by hour including requests, tokens, cost, and errors",
)
async def get_hourly_metrics(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to fetch"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
) -> HourlyMetricsResponse:
    """Get metrics aggregated by hour."""
    client = get_langfuse_client()

    # Calculate time range
    to_dt = datetime.now()
    from_dt = to_dt - timedelta(hours=hours)

    # Fetch traces from Langfuse
    trace_filter = TraceFilter(
        from_timestamp=from_dt,
        to_timestamp=to_dt,
        limit=10000,  # Get all traces in the period
    )

    traces = await client.get_traces(trace_filter)

    # Filter by project_id if provided (check metadata or tags)
    if project_id:
        traces = [
            t for t in traces
            if t.metadata.get("project_id") == project_id
            or project_id in (t.tags or [])
        ]

    # Group traces by hour
    hourly_data: dict[str, dict] = defaultdict(
        lambda: {"requests": 0, "tokens": 0, "cost": 0.0, "errors": 0}
    )

    for trace in traces:
        # Truncate timestamp to hour
        hour_key = trace.timestamp.strftime("%Y-%m-%dT%H:00:00")

        hourly_data[hour_key]["requests"] += 1
        hourly_data[hour_key]["tokens"] += trace.total_tokens or 0
        hourly_data[hour_key]["cost"] += trace.total_cost or 0.0

        # Check for errors in trace metadata or status
        if trace.metadata.get("error") or trace.metadata.get("status") == "error":
            hourly_data[hour_key]["errors"] += 1

    # Build response with all hours in the range (fill gaps with zeros)
    metrics = []
    current_hour = from_dt.replace(minute=0, second=0, microsecond=0)

    while current_hour <= to_dt:
        hour_key = current_hour.strftime("%Y-%m-%dT%H:00:00")
        data = hourly_data.get(hour_key, {"requests": 0, "tokens": 0, "cost": 0.0, "errors": 0})

        metrics.append(HourlyMetric(
            hour=hour_key,
            requests=data["requests"],
            tokens=data["tokens"],
            cost=round(data["cost"], 4),
            errors=data["errors"],
        ))

        current_hour += timedelta(hours=1)

    # Calculate totals
    total_requests = sum(m.requests for m in metrics)
    total_tokens = sum(m.tokens for m in metrics)
    total_cost = sum(m.cost for m in metrics)
    total_errors = sum(m.errors for m in metrics)

    return HourlyMetricsResponse(
        metrics=metrics,
        period_hours=hours,
        total_requests=total_requests,
        total_tokens=total_tokens,
        total_cost=round(total_cost, 4),
        total_errors=total_errors,
    )


@router.get(
    "/errors",
    response_model=ErrorMetricsResponse,
    summary="Get error metrics",
    description="Get error metrics including total errors, error rate, breakdown by type, and recent errors",
)
async def get_error_metrics(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to fetch"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
) -> ErrorMetricsResponse:
    """Get error metrics and breakdown."""
    client = get_langfuse_client()

    # Calculate time range
    to_dt = datetime.now()
    from_dt = to_dt - timedelta(hours=hours)

    # Fetch traces from Langfuse
    trace_filter = TraceFilter(
        from_timestamp=from_dt,
        to_timestamp=to_dt,
        limit=10000,
    )

    traces = await client.get_traces(trace_filter)

    # Filter by project_id if provided
    if project_id:
        traces = [
            t for t in traces
            if t.metadata.get("project_id") == project_id
            or project_id in (t.tags or [])
        ]

    total_traces = len(traces)

    # Find traces with errors
    error_traces = []
    for trace in traces:
        error_info = None

        # Check various error indicators
        if trace.metadata.get("error"):
            error_info = {
                "type": trace.metadata.get("error_type", "unknown"),
                "message": str(trace.metadata.get("error")),
                "trace": trace,
            }
        elif trace.metadata.get("status") == "error":
            error_info = {
                "type": trace.metadata.get("error_type", "execution_error"),
                "message": trace.metadata.get("error_message", "Unknown error"),
                "trace": trace,
            }
        elif trace.metadata.get("qa_status") == "rejected":
            error_info = {
                "type": "qa_rejection",
                "message": trace.metadata.get("qa_reason", "QA rejected"),
                "trace": trace,
            }

        if error_info:
            error_traces.append(error_info)

    total_errors = len(error_traces)
    error_rate = (total_errors / total_traces * 100) if total_traces > 0 else 0.0

    # Build error breakdown by type
    error_counts: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "last_occurrence": None}
    )

    for error in error_traces:
        error_type = error["type"]
        error_counts[error_type]["count"] += 1
        timestamp = error["trace"].timestamp.isoformat()
        if (
            error_counts[error_type]["last_occurrence"] is None
            or timestamp > error_counts[error_type]["last_occurrence"]
        ):
            error_counts[error_type]["last_occurrence"] = timestamp

    breakdown = []
    for error_type, data in sorted(error_counts.items(), key=lambda x: -x[1]["count"]):
        breakdown.append(ErrorBreakdown(
            error_type=error_type,
            count=data["count"],
            percentage=round(data["count"] / total_errors * 100, 1) if total_errors > 0 else 0.0,
            last_occurrence=data["last_occurrence"],
        ))

    # Get recent errors (last 10)
    recent_errors = []
    sorted_errors = sorted(
        error_traces,
        key=lambda x: x["trace"].timestamp,
        reverse=True
    )[:10]

    for error in sorted_errors:
        trace = error["trace"]
        recent_errors.append(RecentError(
            spec_id=trace.metadata.get("spec_id", "unknown"),
            error=error["message"][:200],  # Truncate long messages
            timestamp=trace.timestamp.isoformat(),
            agent_type=trace.metadata.get("agent_type", "unknown"),
        ))

    return ErrorMetricsResponse(
        total_errors=total_errors,
        error_rate=round(error_rate, 2),
        breakdown=breakdown,
        recent_errors=recent_errors,
        period_hours=hours,
    )
