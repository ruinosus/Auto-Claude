"""
Langfuse Metrics Client
=======================

Provides access to Langfuse's Daily Metrics API and Observations API
for analytics, billing, and rate-limiting.
"""

import os
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _get_langfuse_api():
    """Get Langfuse API client."""
    try:
        from langfuse import Langfuse
        return Langfuse()
    except Exception as e:
        logger.error(f"Failed to get Langfuse API: {e}")
        return None


@dataclass
class DailyMetric:
    """Daily metric data point."""
    date: str
    cost_total: float
    count_traces: int
    count_observations: int = 0
    usage_input_tokens: int = 0
    usage_output_tokens: int = 0


def get_daily_metrics(
    from_date: date,
    to_date: date,
    user_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> List[DailyMetric]:
    """
    Get daily aggregated metrics from Langfuse.

    Args:
        from_date: Start date
        to_date: End date
        user_id: Filter by user/project ID
        tags: Filter by tags

    Returns:
        List of daily metrics
    """
    api = _get_langfuse_api()
    if not api:
        return []

    try:
        params = {
            "from_timestamp": datetime.combine(from_date, datetime.min.time()).isoformat(),
            "to_timestamp": datetime.combine(to_date, datetime.max.time()).isoformat(),
        }

        if user_id:
            params["user_id"] = user_id
        if tags:
            params["tags"] = tags

        response = api.api.daily_metrics.list(**params)

        return [
            DailyMetric(
                date=m.date,
                cost_total=m.cost_total or 0.0,
                count_traces=m.count_traces or 0,
                count_observations=getattr(m, 'count_observations', 0),
                usage_input_tokens=getattr(m, 'usage_input_tokens', 0),
                usage_output_tokens=getattr(m, 'usage_output_tokens', 0),
            )
            for m in response.data
        ]
    except Exception as e:
        logger.error(f"Failed to get daily metrics: {e}")
        return []


def get_project_cost(
    project_id: str,
    from_date: date,
    to_date: date,
) -> float:
    """
    Get total cost for a project in a date range.

    Args:
        project_id: Project identifier (user_id in Langfuse)
        from_date: Start date
        to_date: End date

    Returns:
        Total cost in USD
    """
    metrics = get_daily_metrics(from_date, to_date, user_id=project_id)
    return sum(m.cost_total for m in metrics)


def get_trace_count(
    project_id: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> int:
    """Get total trace count."""
    if not from_date:
        from_date = date.today()
    if not to_date:
        to_date = date.today()

    metrics = get_daily_metrics(from_date, to_date, user_id=project_id)
    return sum(m.count_traces for m in metrics)


# =============================================================================
# Observations API
# =============================================================================

def get_traces(
    limit: int = 100,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    from_timestamp: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Get traces from Langfuse.

    Args:
        limit: Maximum number of traces to return
        user_id: Filter by user/project ID
        session_id: Filter by session ID
        tags: Filter by tags
        from_timestamp: Only return traces after this time

    Returns:
        List of trace dictionaries
    """
    api = _get_langfuse_api()
    if not api:
        return []

    try:
        params = {"limit": limit}
        if user_id:
            params["user_id"] = user_id
        if session_id:
            params["session_id"] = session_id
        if tags:
            params["tags"] = tags
        if from_timestamp:
            params["from_timestamp"] = from_timestamp.isoformat()

        response = api.api.trace.list(**params)

        return [
            {
                "id": t.id,
                "name": t.name,
                "user_id": t.user_id,
                "session_id": t.session_id,
                "tags": t.tags,
                "metadata": t.metadata,
                "input": t.input,
                "output": t.output,
                "timestamp": t.timestamp,
            }
            for t in response.data
        ]
    except Exception as e:
        logger.error(f"Failed to get traces: {e}")
        return []


def get_observations(
    trace_id: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get observations (spans, generations) for a trace.

    Args:
        trace_id: Trace ID
        limit: Maximum observations to return

    Returns:
        List of observation dictionaries
    """
    api = _get_langfuse_api()
    if not api:
        return []

    try:
        response = api.api.observations.list(trace_id=trace_id, limit=limit)

        return [
            {
                "id": o.id,
                "name": o.name,
                "type": o.type,
                "model": getattr(o, 'model', None),
                "input": o.input,
                "output": o.output,
                "usage": getattr(o, 'usage', None),
                "start_time": o.start_time,
                "end_time": o.end_time,
            }
            for o in response.data
        ]
    except Exception as e:
        logger.error(f"Failed to get observations: {e}")
        return []


def export_traces_for_billing(
    from_date: date,
    to_date: date,
    output_format: str = "dict",
) -> List[Dict[str, Any]]:
    """
    Export traces with cost data for billing.

    Args:
        from_date: Start date
        to_date: End date
        output_format: "dict" or "csv"

    Returns:
        List of trace summaries with costs
    """
    metrics = get_daily_metrics(from_date, to_date)

    summary = []
    for m in metrics:
        summary.append({
            "date": m.date,
            "traces": m.count_traces,
            "input_tokens": m.usage_input_tokens,
            "output_tokens": m.usage_output_tokens,
            "cost_usd": m.cost_total,
        })

    return summary
