"""
Analytics API Routes
====================

REST API endpoints for accessing Langfuse analytics data.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from .models import (
    TraceResponse,
    TraceListResponse,
    TraceDetailResponse,
    GenerationResponse,
    ScoreResponse,
    SessionListResponse,
    SessionSummary,
    ROIResponse,
    ROIMetrics,
    ROISummaryResponse,
    CostSummaryResponse,
    AgentCost,
    UsageSummaryResponse,
    CostOverTimePoint,
    TokensBySpec,
    ModelUsage,
    PhaseDuration,
    FeatureUsage,
    DailyMetricResponse,
    DailyMetricsListResponse,
    BillingExportResponse,
)
from .langfuse_client import TraceFilter

logger = logging.getLogger(__name__)
router = APIRouter()

# Token estimation constants
# Based on typical Claude conversation patterns where prompts tend to be
# longer than responses due to system prompts, context, and instructions.
# These ratios are estimates used when exact input/output counts aren't available.
DEFAULT_INPUT_TOKEN_RATIO = 0.7
DEFAULT_OUTPUT_TOKEN_RATIO = 0.3


def get_spec_id_from_trace(trace) -> str:
    """
    Extract spec_id from trace with intelligent fallback chain.

    Priority:
    1. metadata.spec_id (if present)
    2. session_id (if present)
    3. First part of trace name (before first '-')
    4. 'trace-' + first 8 chars of trace.id
    """
    # Try metadata first
    spec_id = trace.metadata.get("spec_id") if trace.metadata else None
    if spec_id:
        return spec_id

    # Fallback to session_id
    if trace.session_id:
        return trace.session_id

    # Fallback to name prefix
    if trace.name and "-" in trace.name:
        return trace.name.split("-")[0]

    # Last resort: trace ID prefix
    return f"trace-{trace.id[:8]}"


def get_agent_type_from_trace(trace) -> str:
    """
    Extract agent_type from trace with intelligent fallback.

    Priority:
    1. metadata.agent_type (if present)
    2. Infer from trace name (planner, coder, qa_reviewer, qa_fixer)
    3. 'other'
    """
    # Try metadata first
    agent_type = trace.metadata.get("agent_type") if trace.metadata else None
    if agent_type:
        return agent_type

    # Infer from name
    name_lower = (trace.name or "").lower()
    for known_type in ["planner", "coder", "qa_reviewer", "qa_fixer", "gatherer", "researcher", "writer"]:
        if known_type in name_lower:
            return known_type

    return "other"


def get_client():
    """Get the Langfuse client from the app context."""
    from .app import get_langfuse_client
    client = get_langfuse_client()
    if not client or not client.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Langfuse client not configured. Check API keys."
        )
    return client


# =============================================================================
# Trace Endpoints
# =============================================================================

@router.get("/traces", response_model=TraceListResponse)
async def list_traces(
    spec_id: Optional[str] = Query(None, description="Filter by spec ID"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List traces with optional filtering.

    Supports filtering by spec_id, agent_type, tags, and date range.
    """
    client = get_client()

    # Parse tags
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]

    filter = TraceFilter(
        spec_id=spec_id,
        agent_type=agent_type,
        tags=tag_list,
        from_timestamp=from_date,
        to_timestamp=to_date,
        limit=limit,
        offset=offset,
    )

    traces = await client.get_traces(filter)

    # Convert to response models
    trace_responses = []
    for t in traces:
        trace_responses.append(TraceResponse(
            id=t.id,
            name=t.name,
            timestamp=t.timestamp,
            metadata=t.metadata,
            tags=t.tags,
            session_id=t.session_id,
            user_id=t.user_id,
            total_tokens=t.total_tokens,
            total_cost=t.total_cost,
            latency_ms=t.latency_ms,
            generation_count=t.generation_count,
            spec_id=get_spec_id_from_trace(t),
            agent_type=get_agent_type_from_trace(t),
        ))

    return TraceListResponse(
        traces=trace_responses,
        total=len(trace_responses),  # TODO: Get actual total from Langfuse
        limit=limit,
        offset=offset,
    )


@router.get("/traces/{trace_id}", response_model=TraceDetailResponse)
async def get_trace(trace_id: str):
    """
    Get detailed trace information including generations and scores.
    """
    client = get_client()

    trace = await client.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

    # Get generations for this trace
    generations = await client.get_generations(trace_id=trace_id)
    gen_responses = [
        GenerationResponse(
            id=g.id,
            name=g.name,
            model=g.model,
            timestamp=g.timestamp,
            input_tokens=g.input_tokens,
            output_tokens=g.output_tokens,
            total_tokens=g.total_tokens,
            cost=g.cost,
            latency_ms=g.latency_ms,
            metadata=g.metadata,
        )
        for g in generations
    ]

    # Get scores for this trace
    scores = await client.get_scores(trace_id=trace_id)
    score_responses = [
        ScoreResponse(
            id=s.id,
            name=s.name,
            value=s.value,
            trace_id=s.trace_id,
            comment=s.comment,
            timestamp=s.timestamp,
        )
        for s in scores
    ]

    return TraceDetailResponse(
        id=trace.id,
        name=trace.name,
        timestamp=trace.timestamp,
        metadata=trace.metadata,
        tags=trace.tags,
        session_id=trace.session_id,
        user_id=trace.user_id,
        total_tokens=trace.total_tokens,
        total_cost=trace.total_cost,
        latency_ms=trace.latency_ms,
        generation_count=trace.generation_count,
        spec_id=get_spec_id_from_trace(trace),
        agent_type=get_agent_type_from_trace(trace),
        input=trace.input,
        output=trace.output,
        generations=gen_responses,
        scores=score_responses,
    )


# =============================================================================
# Session Endpoints
# =============================================================================

@router.get("/sessions/{spec_id}", response_model=SessionListResponse)
async def get_sessions_for_spec(spec_id: str):
    """
    Get all sessions (traces) for a specific spec.

    Includes a summary with total tokens, cost, and agent breakdown.
    """
    client = get_client()

    traces = await client.get_sessions_for_spec(spec_id)

    # Build session responses
    session_responses = [
        TraceResponse(
            id=t.id,
            name=t.name,
            timestamp=t.timestamp,
            metadata=t.metadata,
            tags=t.tags,
            session_id=t.session_id,
            user_id=t.user_id,
            total_tokens=t.total_tokens,
            total_cost=t.total_cost,
            latency_ms=t.latency_ms,
            generation_count=t.generation_count,
            spec_id=get_spec_id_from_trace(t),
            agent_type=get_agent_type_from_trace(t),
        )
        for t in traces
    ]

    # Calculate summary
    total_tokens = sum(t.total_tokens for t in traces)
    total_cost = sum(t.total_cost for t in traces)

    # Agent breakdown
    agent_breakdown = {}
    for t in traces:
        agent_type = get_agent_type_from_trace(t)
        agent_breakdown[agent_type] = agent_breakdown.get(agent_type, 0) + 1

    # Determine status based on latest agent type
    status = "unknown"
    if traces:
        latest_trace = max(traces, key=lambda t: t.timestamp)
        latest_agent = get_agent_type_from_trace(latest_trace)
        if "qa" in latest_agent.lower():
            status = "qa_review"
        elif latest_agent == "planner":
            status = "planning"
        elif latest_agent == "coder":
            status = "coding"

    summary = SessionSummary(
        spec_id=spec_id,
        session_count=len(traces),
        total_tokens=total_tokens,
        total_cost=total_cost,
        agent_breakdown=agent_breakdown,
        latest_session=max(t.timestamp for t in traces) if traces else None,
        status=status,
    )

    return SessionListResponse(
        spec_id=spec_id,
        sessions=session_responses,
        summary=summary,
    )


# =============================================================================
# ROI Endpoints
# =============================================================================

@router.get("/roi/summary", response_model=ROISummaryResponse)
async def get_roi_summary(
    project_id: Optional[str] = Query(None, description="Filter by project ID (REQUIRED for accurate data)"),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
):
    """
    Get aggregated ROI summary across specs for a specific project.

    Calculates total business value, costs, and hours saved.

    IMPORTANT: Pass project_id to get accurate data for your project only.
    Without project_id, data from ALL projects will be aggregated (legacy behavior).
    """
    client = get_client()

    # Get ROI scores filtered by project_id
    roi_scores = await client.get_scores(name="roi_percentage", project_id=project_id)

    # Group scores by trace_id to get unique specs
    trace_ids = set(s.trace_id for s in roi_scores)

    by_spec = []
    total_business_value = 0.0
    total_cost = 0.0
    total_hours_saved = 0.0
    specs_with_positive_roi = 0
    confidence_sum = 0.0

    for trace_id in trace_ids:
        # Get all scores for this trace
        trace_scores = await client.get_scores(trace_id=trace_id)
        score_dict = {s.name: s.value for s in trace_scores}

        # Get trace to find spec_id
        trace = await client.get_trace(trace_id)
        spec_id = get_spec_id_from_trace(trace) if trace else f"trace-{trace_id[:8]}"

        metrics = ROIMetrics(
            roi_percentage=score_dict.get("roi_percentage", 0),
            business_value_usd=score_dict.get("business_value_usd", 0),
            actual_cost_usd=score_dict.get("actual_cost_usd", 0),
            dev_hours_saved=score_dict.get("dev_hours_saved", 0),
            lines_added=int(score_dict.get("lines_added", 0)),
            lines_removed=int(score_dict.get("lines_removed", 0)),
            files_changed=int(score_dict.get("files_changed", 0)),
            qa_attempts=int(score_dict.get("qa_attempts", 0)),
            qa_passed=score_dict.get("qa_passed", 0) > 0.5,
            confidence_score=score_dict.get("confidence_score", 0),
            quality_multiplier=score_dict.get("quality_multiplier", 1),
        )

        by_spec.append(ROIResponse(
            spec_id=spec_id,
            metrics=metrics,
            trace_id=trace_id,
        ))

        total_business_value += metrics.business_value_usd
        total_cost += metrics.actual_cost_usd
        total_hours_saved += metrics.dev_hours_saved
        confidence_sum += metrics.confidence_score

        if metrics.roi_percentage > 0:
            specs_with_positive_roi += 1

    # Calculate total ROI
    total_roi = ((total_business_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
    avg_confidence = confidence_sum / len(by_spec) if by_spec else 0

    return ROISummaryResponse(
        total_roi_percentage=total_roi,
        total_business_value_usd=total_business_value,
        total_actual_cost_usd=total_cost,
        total_dev_hours_saved=total_hours_saved,
        spec_count=len(by_spec),
        specs_with_positive_roi=specs_with_positive_roi,
        average_confidence=avg_confidence,
        by_spec=by_spec,
        period={
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None,
        },
    )


@router.get("/roi/{spec_id}", response_model=ROIResponse)
async def get_roi_for_spec(spec_id: str):
    """
    Get ROI metrics for a specific spec.

    Fetches the ROI scores from the most recent trace for this spec.
    """
    client = get_client()

    # Get sessions for this spec
    traces = await client.get_sessions_for_spec(spec_id)
    if not traces:
        raise HTTPException(status_code=404, detail=f"No traces found for spec {spec_id}")

    # Find the trace with ROI scores (usually the latest coder or qa session)
    for trace in sorted(traces, key=lambda t: t.timestamp, reverse=True):
        scores = await client.get_scores(trace_id=trace.id)
        score_dict = {s.name: s.value for s in scores}

        if "roi_percentage" in score_dict:
            metrics = ROIMetrics(
                roi_percentage=score_dict.get("roi_percentage", 0),
                business_value_usd=score_dict.get("business_value_usd", 0),
                actual_cost_usd=score_dict.get("actual_cost_usd", 0),
                dev_hours_saved=score_dict.get("dev_hours_saved", 0),
                lines_added=int(score_dict.get("lines_added", 0)),
                lines_removed=int(score_dict.get("lines_removed", 0)),
                files_changed=int(score_dict.get("files_changed", 0)),
                qa_attempts=int(score_dict.get("qa_attempts", 0)),
                qa_passed=score_dict.get("qa_passed", 0) > 0.5,
                confidence_score=score_dict.get("confidence_score", 0),
                quality_multiplier=score_dict.get("quality_multiplier", 1),
            )

            return ROIResponse(
                spec_id=spec_id,
                metrics=metrics,
                trace_id=trace.id,
            )

    # No ROI scores found - return empty metrics
    return ROIResponse(
        spec_id=spec_id,
        metrics=ROIMetrics(),
        trace_id=None,
    )


# =============================================================================
# Cost Endpoints
# =============================================================================

@router.get("/costs", response_model=CostSummaryResponse)
async def get_cost_summary(
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
):
    """
    Get cost summary for a time period.

    Includes breakdown by agent type.
    """
    client = get_client()

    summary = await client.get_cost_summary(
        from_timestamp=from_date,
        to_timestamp=to_date,
    )

    # Convert agent breakdown to list
    agent_costs = [
        AgentCost(
            agent_type=agent_type,
            cost=data["cost"],
            tokens=data["tokens"],
            trace_count=data["count"],
        )
        for agent_type, data in summary.get("by_agent_type", {}).items()
    ]

    return CostSummaryResponse(
        total_cost=summary["total_cost"],
        total_tokens=summary["total_tokens"],
        generation_count=summary["generation_count"],
        trace_count=summary["trace_count"],
        by_agent_type=agent_costs,
        period=summary["period"],
    )


# =============================================================================
# Usage Summary Endpoint (for dashboard charts)
# =============================================================================

@router.get("/usage/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
):
    """
    Get comprehensive usage analytics for dashboard charts.

    Returns pre-aggregated data for:
    - Cost Over Time (daily breakdown)
    - Tokens By Spec
    - Model Distribution
    - Duration by Phase
    - Feature Usage (by agent type)

    IMPORTANT: Pass project_id to get accurate data for your project only.
    """
    from collections import defaultdict

    client = get_client()

    # Build filter with project_id
    # Note: Langfuse API max limit is 100
    filter = TraceFilter(
        project_id=project_id,
        from_timestamp=from_date,
        to_timestamp=to_date,
        limit=100,  # Langfuse API max limit is 100
    )

    traces = await client.get_traces(filter)

    if not traces:
        return UsageSummaryResponse(
            period={
                "from": from_date.isoformat() if from_date else None,
                "to": to_date.isoformat() if to_date else None,
            }
        )

    # Aggregate data
    total_cost = 0.0
    total_tokens = 0
    total_input_tokens = 0
    total_output_tokens = 0
    specs = set()

    # Daily aggregation for cost over time
    daily_data = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "count": 0})

    # Spec aggregation
    spec_data = defaultdict(lambda: {"input": 0, "output": 0, "total": 0, "cost": 0.0})

    # Phase aggregation
    phase_data = defaultdict(lambda: {"total_ms": 0.0, "count": 0})

    # Feature/agent aggregation
    feature_data = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "count": 0})

    # Model aggregation (from generations)
    model_data = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "count": 0})

    for trace in traces:
        total_cost += trace.total_cost
        total_tokens += trace.total_tokens

        # Estimate input/output token split when exact values aren't available
        trace_input_tokens = int(trace.total_tokens * DEFAULT_INPUT_TOKEN_RATIO)
        trace_output_tokens = trace.total_tokens - trace_input_tokens  # Ensures sum matches total
        total_input_tokens += trace_input_tokens
        total_output_tokens += trace_output_tokens

        spec_id = get_spec_id_from_trace(trace)
        specs.add(spec_id)

        # Daily aggregation
        date_key = trace.timestamp.strftime("%Y-%m-%d")
        daily_data[date_key]["cost"] += trace.total_cost
        daily_data[date_key]["tokens"] += trace.total_tokens
        daily_data[date_key]["count"] += 1

        # Spec aggregation (estimate input/output split)
        spec_data[spec_id]["total"] += trace.total_tokens
        spec_data[spec_id]["input"] += trace_input_tokens
        spec_data[spec_id]["output"] += trace_output_tokens
        spec_data[spec_id]["cost"] += trace.total_cost

        # Phase aggregation
        phase = trace.metadata.get("phase", "coding")
        phase_data[phase]["total_ms"] += trace.latency_ms
        phase_data[phase]["count"] += 1

        # Feature/agent aggregation
        agent_type = get_agent_type_from_trace(trace)
        feature_data[agent_type]["tokens"] += trace.total_tokens
        feature_data[agent_type]["cost"] += trace.total_cost
        feature_data[agent_type]["count"] += 1

    # Get model distribution from generations (sample first 10 traces)
    for trace in traces[:10]:
        generations = await client.get_generations(trace_id=trace.id)
        for gen in generations:
            model_data[gen.model]["tokens"] += gen.total_tokens
            model_data[gen.model]["cost"] += gen.cost
            model_data[gen.model]["count"] += 1

    # Build response
    cost_over_time = sorted([
        CostOverTimePoint(
            date=date,
            cost=round(data["cost"], 4),
            tokens=data["tokens"],
            trace_count=data["count"]
        )
        for date, data in daily_data.items()
    ], key=lambda x: x.date)

    tokens_by_spec = [
        TokensBySpec(
            spec_id=spec_id,
            input_tokens=data["input"],
            output_tokens=data["output"],
            total_tokens=data["total"],
            cost=round(data["cost"], 4)
        )
        for spec_id, data in spec_data.items()
    ]

    # Calculate percentages for model distribution
    total_model_tokens = sum(d["tokens"] for d in model_data.values())
    model_distribution = [
        ModelUsage(
            model=model,
            tokens=data["tokens"],
            cost=round(data["cost"], 4),
            generation_count=data["count"],
            percentage=round((data["tokens"] / total_model_tokens * 100) if total_model_tokens > 0 else 0, 1)
        )
        for model, data in model_data.items()
    ]

    duration_by_phase = [
        PhaseDuration(
            phase=phase,
            avg_duration_ms=round(data["total_ms"] / data["count"], 2) if data["count"] > 0 else 0,
            total_duration_ms=round(data["total_ms"], 2),
            trace_count=data["count"]
        )
        for phase, data in phase_data.items()
    ]

    # Calculate percentages for feature usage
    total_feature_tokens = sum(d["tokens"] for d in feature_data.values())
    feature_usage = [
        FeatureUsage(
            feature=feature,
            tokens=data["tokens"],
            cost=round(data["cost"], 4),
            trace_count=data["count"],
            percentage=round((data["tokens"] / total_feature_tokens * 100) if total_feature_tokens > 0 else 0, 1)
        )
        for feature, data in feature_data.items()
    ]

    return UsageSummaryResponse(
        total_cost=round(total_cost, 4),
        total_tokens=total_tokens,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_traces=len(traces),
        active_specs=len(specs),
        cost_over_time=cost_over_time,
        tokens_by_spec=tokens_by_spec,
        model_distribution=model_distribution,
        duration_by_phase=duration_by_phase,
        feature_usage=feature_usage,
        period={
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None,
        }
    )


# =============================================================================
# Daily Metrics Endpoints
# =============================================================================

@router.get("/metrics/daily", response_model=DailyMetricsListResponse)
async def get_daily_metrics(
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    """
    Get daily aggregated metrics from Langfuse.

    Useful for billing dashboards and cost tracking.
    """
    from datetime import date as date_type, timedelta

    try:
        from analytics.metrics_client import get_daily_metrics as fetch_metrics, DailyMetric
    except ImportError:
        raise HTTPException(status_code=501, detail="Metrics client not available")

    # Default to last 30 days
    end_date = to_date.date() if to_date else date_type.today()
    start_date = from_date.date() if from_date else end_date - timedelta(days=30)

    metrics = fetch_metrics(
        from_date=start_date,
        to_date=end_date,
        user_id=project_id,
    )

    # Convert to response format
    from .models import DailyMetricResponse, DailyMetricsListResponse

    metric_responses = [
        DailyMetricResponse(
            date=m.date,
            cost_usd=m.cost_total,
            traces=m.count_traces,
            input_tokens=m.usage_input_tokens,
            output_tokens=m.usage_output_tokens,
            observations=m.count_observations,
        )
        for m in metrics
    ]

    total_cost = sum(m.cost_total for m in metrics)
    total_traces = sum(m.count_traces for m in metrics)
    total_tokens = sum(m.usage_input_tokens + m.usage_output_tokens for m in metrics)

    return DailyMetricsListResponse(
        metrics=metric_responses,
        total_cost=round(total_cost, 4),
        total_traces=total_traces,
        total_tokens=total_tokens,
        period={
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
        },
    )


@router.get("/metrics/billing", response_model=BillingExportResponse)
async def export_billing_data(
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    """
    Export billing data for invoicing.

    Returns cost breakdown for the specified period.
    """
    from datetime import date as date_type, timedelta

    try:
        from analytics.metrics_client import export_traces_for_billing
    except ImportError:
        raise HTTPException(status_code=501, detail="Metrics client not available")

    # Default to current month
    end_date = to_date.date() if to_date else date_type.today()
    start_date = from_date.date() if from_date else end_date.replace(day=1)

    billing_data = export_traces_for_billing(
        from_date=start_date,
        to_date=end_date,
    )

    from .models import DailyMetricResponse, BillingExportResponse

    metric_responses = [
        DailyMetricResponse(
            date=d["date"],
            cost_usd=d["cost_usd"],
            traces=d["traces"],
            input_tokens=d.get("input_tokens", 0),
            output_tokens=d.get("output_tokens", 0),
        )
        for d in billing_data
    ]

    total_cost = sum(d["cost_usd"] for d in billing_data)
    total_traces = sum(d["traces"] for d in billing_data)
    total_tokens = sum(d.get("input_tokens", 0) + d.get("output_tokens", 0) for d in billing_data)

    return BillingExportResponse(
        data=metric_responses,
        summary={
            "total_cost_usd": round(total_cost, 4),
            "total_traces": total_traces,
            "total_tokens": total_tokens,
            "days": len(billing_data),
        },
        period={
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
        },
        export_format="json",
    )


@router.get("/metrics/project/{project_id}/cost")
async def get_project_cost(
    project_id: str,
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
):
    """
    Get total cost for a specific project.

    Useful for rate limiting or billing by project.
    """
    from datetime import date as date_type, timedelta

    try:
        from analytics.metrics_client import get_project_cost as fetch_cost
    except ImportError:
        raise HTTPException(status_code=501, detail="Metrics client not available")

    end_date = to_date.date() if to_date else date_type.today()
    start_date = from_date.date() if from_date else end_date.replace(day=1)

    total_cost = fetch_cost(
        project_id=project_id,
        from_date=start_date,
        to_date=end_date,
    )

    return {
        "project_id": project_id,
        "total_cost_usd": round(total_cost, 4),
        "period": {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
        },
    }


# =============================================================================
# Score Endpoints
# =============================================================================

@router.get("/scores", response_model=List[ScoreResponse])
async def list_scores(
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    name: Optional[str] = Query(None, description="Filter by score name"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
):
    """
    List scores with optional filtering.
    """
    client = get_client()

    scores = await client.get_scores(
        trace_id=trace_id,
        name=name,
        limit=limit,
    )

    return [
        ScoreResponse(
            id=s.id,
            name=s.name,
            value=s.value,
            trace_id=s.trace_id,
            comment=s.comment,
            timestamp=s.timestamp,
        )
        for s in scores
    ]
