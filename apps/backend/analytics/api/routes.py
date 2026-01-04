"""
Analytics API Routes
====================

REST API endpoints for accessing Langfuse analytics data.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

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
    ServiceHealth,
    HealthStatusResponse,
    HourlyMetric,
    HourlyMetricsResponse,
    ActivityEvent,
    RecentActivityResponse,
    ErrorBreakdown,
    ErrorMetricsResponse,
    # Unified ROI models
    ValueBreakdown,
    FeatureROIMetrics,
    FeatureROIResponse,
    UnifiedROISummary,
    UnifiedROIResponse,
    # Rich Artifact models
    ArtifactMetadataModel,
    RichArtifactResponse,
    ArtifactQualityMetrics,
    ArtifactStatistics,
    ArtifactTimelineEntry,
    ArtifactTimelineResponse,
    LocalArtifactsResponse,
)
from .langfuse_client import TraceFilter
from pathlib import Path

# Import artifact storage for loading full content
try:
    from analytics.artifact_storage import (
        load_artifact,
        list_artifacts as list_local_artifacts,
    )
    ARTIFACT_STORAGE_AVAILABLE = True
except ImportError:
    ARTIFACT_STORAGE_AVAILABLE = False

    def load_artifact(*args, **kwargs):
        return None

    def list_local_artifacts(*args, **kwargs):
        return []

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
    2. For ROI calculation traces: use feature_type from metadata
    3. session_id (if present)
    4. For spec traces: extract XXX-name from "spec-XXX-name-..."
    5. First meaningful part of trace name (skip generic prefixes)
    6. 'trace-' + first 8 chars of trace.id
    """
    # Try metadata first
    if trace.metadata:
        spec_id = trace.metadata.get("spec_id")
        if spec_id:
            return spec_id

        # For ROI calculation traces, use feature_type as identifier
        if trace.metadata.get("roi_calculation"):
            feature_type = trace.metadata.get("feature_type", "unknown")
            return f"feature:{feature_type}"

    # Fallback to session_id
    if trace.session_id:
        return trace.session_id

    # Try to extract spec ID from trace name
    if trace.name:
        name = trace.name

        # Handle spec traces like "spec-001-bearer-token-authentication-writer"
        if name.startswith("spec-"):
            parts = name.split("-")
            # Find the spec ID pattern (XXX-name-...)
            if len(parts) >= 3:
                # Reconstruct spec ID: parts[1] is the number, subsequent parts are the name
                spec_parts = [parts[1]]
                for i in range(2, len(parts)):
                    # Stop at agent type suffixes
                    if parts[i] in ["writer", "researcher", "gatherer", "coder", "planner",
                                    "complexity_assessor", "qa_reviewer", "qa_fixer"]:
                        break
                    spec_parts.append(parts[i])
                return "-".join(spec_parts)

        # Skip generic prefixes that aren't spec IDs
        if "-" in name:
            prefix = name.split("-")[0]
            # Skip ROI, insight, compaction prefixes - they're not spec IDs
            if prefix in ["roi", "insight"]:
                # Try to get a better ID from later parts
                parts = name.split("-")
                if len(parts) >= 2:
                    return parts[1] if parts[1] not in ["extraction", "calculation"] else f"{prefix}-trace"
            return prefix

    # Last resort: trace ID prefix
    return f"trace-{trace.id[:8]}"


def normalize_model_name(model: str) -> str:
    """
    Normalize model names to group similar models together.

    Examples:
    - "claude-sonnet-4-5-20250929" -> "claude-sonnet-4-5"
    - "claude-opus-4-5-20251101" -> "claude-opus-4-5"
    - "claude-3-5-sonnet-20241022" -> "claude-3-5-sonnet"
    """
    if not model:
        return "unknown"

    # Remove date suffixes (format: -YYYYMMDD)
    import re
    normalized = re.sub(r'-\d{8}$', '', model)

    return normalized


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

    # Hourly rate for calculating hours saved from value
    HOURLY_RATE = 150.0

    for trace_id in trace_ids:
        # Get all scores for this trace
        trace_scores = await client.get_scores(trace_id=trace_id)
        score_dict = {s.name: s.value for s in trace_scores}

        # Get trace to find spec_id
        trace = await client.get_trace(trace_id)
        spec_id = get_spec_id_from_trace(trace) if trace else f"trace-{trace_id[:8]}"

        # Use correct score names (total_value_usd, total_cost_usd)
        # Fall back to legacy names for backwards compatibility
        business_value = score_dict.get("total_value_usd", score_dict.get("business_value_usd", 0))
        actual_cost = score_dict.get("total_cost_usd", score_dict.get("actual_cost_usd", 0))

        # Calculate hours saved from value (value / hourly_rate)
        # Use explicit dev_hours_saved if available, otherwise calculate
        hours_saved = score_dict.get("dev_hours_saved", 0)
        if hours_saved == 0 and business_value > 0:
            hours_saved = business_value / HOURLY_RATE

        metrics = ROIMetrics(
            roi_percentage=score_dict.get("roi_percentage", 0),
            business_value_usd=business_value,
            actual_cost_usd=actual_cost,
            dev_hours_saved=hours_saved,
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

    # Calculate total ROI from aggregated values
    # If we have positive value but zero cost, ROI is infinite (use a high number)
    if total_cost > 0:
        total_roi = ((total_business_value - total_cost) / total_cost * 100)
    elif total_business_value > 0:
        total_roi = 10000.0  # 10000% ROI when cost is zero but value exists
    else:
        total_roi = 0.0
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


@router.get("/roi/unified", response_model=UnifiedROIResponse)
async def get_unified_roi(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
):
    """
    Get unified ROI summary across all feature types.

    Returns comprehensive ROI data including:
    - Total ROI across all Auto-Claude features
    - Value breakdown by type (execution, decision, prevention, knowledge)
    - Breakdown by feature type (ideation, roadmap, spec, build, github, insights)

    This endpoint aggregates data from the new unified ROI system which captures
    value from all phases of development, not just code execution.
    """
    client = get_client()

    # Aggregate data by feature type
    feature_data: Dict[str, Dict] = {}
    total_value = 0.0
    total_cost = 0.0
    total_execution = 0.0
    total_decision = 0.0
    total_prevention = 0.0
    total_knowledge = 0.0
    positive_roi_count = 0
    confidence_sum = 0.0
    trace_count = 0

    # Get all traces with ROI scores
    roi_scores = await client.get_scores(name="roi_percentage", project_id=project_id)

    for score in roi_scores:
        trace_id = score.trace_id
        trace = await client.get_trace(trace_id)
        if not trace:
            continue

        # Get all scores for this trace
        trace_scores = await client.get_scores(trace_id=trace_id)
        score_dict = {s.name: s.value for s in trace_scores}

        # Determine feature type from metadata or trace name
        feature_type = "other"
        if trace.metadata:
            feature_type = trace.metadata.get("feature_type", "other")
        if feature_type == "other":
            # Infer from trace name
            name_lower = (trace.name or "").lower()
            if "ideation" in name_lower:
                feature_type = "ideation"
            elif "roadmap" in name_lower:
                feature_type = "roadmap"
            elif "spec" in name_lower:
                feature_type = "spec"
            elif "github" in name_lower or "pr" in name_lower:
                feature_type = "github"
            elif "insight" in name_lower:
                feature_type = "insights"
            elif any(x in name_lower for x in ["planner", "coder", "qa"]):
                feature_type = "build"

        # Initialize feature data if needed
        if feature_type not in feature_data:
            feature_data[feature_type] = {
                "roi_sum": 0.0,
                "value_sum": 0.0,
                "cost_sum": 0.0,
                "execution_sum": 0.0,
                "decision_sum": 0.0,
                "prevention_sum": 0.0,
                "knowledge_sum": 0.0,
                "confidence_sum": 0.0,
                "count": 0,
            }

        # Accumulate values
        roi = score_dict.get("roi_percentage", 0)
        value = score_dict.get("total_value_usd", score_dict.get("business_value_usd", 0))
        cost = score_dict.get("total_cost_usd", score_dict.get("actual_cost_usd", 0))
        execution = score_dict.get("value_execution_usd", 0)
        decision = score_dict.get("value_decision_usd", 0)
        prevention = score_dict.get("value_prevention_usd", 0)
        knowledge = score_dict.get("value_knowledge_usd", 0)
        confidence = score_dict.get("confidence_score", 0)

        feature_data[feature_type]["roi_sum"] += roi
        feature_data[feature_type]["value_sum"] += value
        feature_data[feature_type]["cost_sum"] += cost
        feature_data[feature_type]["execution_sum"] += execution
        feature_data[feature_type]["decision_sum"] += decision
        feature_data[feature_type]["prevention_sum"] += prevention
        feature_data[feature_type]["knowledge_sum"] += knowledge
        feature_data[feature_type]["confidence_sum"] += confidence
        feature_data[feature_type]["count"] += 1

        total_value += value
        total_cost += cost
        total_execution += execution
        total_decision += decision
        total_prevention += prevention
        total_knowledge += knowledge
        confidence_sum += confidence
        trace_count += 1

        if roi > 0:
            positive_roi_count += 1

    # Build response
    by_feature_type = {}
    features_list = []

    for ft, data in feature_data.items():
        count = data["count"]
        avg_roi = data["roi_sum"] / count if count > 0 else 0
        avg_confidence = data["confidence_sum"] / count if count > 0 else 0

        metrics = FeatureROIMetrics(
            feature_type=ft,
            roi_percentage=avg_roi,
            total_value_usd=data["value_sum"],
            total_cost_usd=data["cost_sum"],
            net_value_usd=data["value_sum"] - data["cost_sum"],
            confidence_score=avg_confidence,
            value_breakdown=ValueBreakdown(
                execution_value=data["execution_sum"],
                decision_value=data["decision_sum"],
                prevention_value=data["prevention_sum"],
                knowledge_value=data["knowledge_sum"],
            ),
            feature_metrics={"trace_count": count},
        )

        by_feature_type[ft] = metrics
        features_list.append(FeatureROIResponse(
            feature_type=ft,
            project_id=project_id or "all",
            metrics=metrics,
        ))

    # Calculate totals
    total_roi = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
    avg_confidence = confidence_sum / trace_count if trace_count > 0 else 0

    summary = UnifiedROISummary(
        total_roi_percentage=total_roi,
        total_value_usd=total_value,
        total_cost_usd=total_cost,
        net_value_usd=total_value - total_cost,
        total_execution_value=total_execution,
        total_decision_value=total_decision,
        total_prevention_value=total_prevention,
        total_knowledge_value=total_knowledge,
        total_traces=trace_count,
        positive_roi_count=positive_roi_count,
        average_confidence=avg_confidence,
        by_feature_type=by_feature_type,
        value_distribution=ValueBreakdown(
            execution_value=total_execution,
            decision_value=total_decision,
            prevention_value=total_prevention,
            knowledge_value=total_knowledge,
        ),
        period={
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None,
        },
    )

    return UnifiedROIResponse(
        summary=summary,
        features=features_list,
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

    # Get model distribution from generations (sample up to 100 traces for better accuracy)
    # Normalize model names to group similar models (e.g., "claude-sonnet-4-5-20250929" -> "claude-sonnet-4-5")
    for trace in traces[:100]:
        generations = await client.get_generations(trace_id=trace.id)
        for gen in generations:
            normalized_model = normalize_model_name(gen.model)
            model_data[normalized_model]["tokens"] += gen.total_tokens
            model_data[normalized_model]["cost"] += gen.cost
            model_data[normalized_model]["count"] += 1

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

    # Calculate percentages for feature usage (use cost instead of tokens since tokens may be 0)
    total_feature_cost = sum(d["cost"] for d in feature_data.values())
    feature_usage = sorted([
        FeatureUsage(
            feature=feature,
            tokens=data["tokens"],
            cost=round(data["cost"], 4),
            trace_count=data["count"],
            percentage=round((data["cost"] / total_feature_cost * 100) if total_feature_cost > 0 else 0, 1)
        )
        for feature, data in feature_data.items()
    ], key=lambda x: x.cost, reverse=True)  # Sort by cost descending

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


@router.get("/metrics/hourly", response_model=HourlyMetricsResponse)
async def get_hourly_metrics(
    hours: int = Query(default=24, le=168),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
) -> HourlyMetricsResponse:
    """Get metrics aggregated by hour for the last N hours.

    Pass project_id to filter data for a specific project.
    """
    from .app import get_langfuse_client

    client = get_langfuse_client()
    if not client or not client.is_configured():
        return HourlyMetricsResponse(period_hours=hours)

    try:
        from_date = datetime.utcnow() - timedelta(hours=hours)
        filter = TraceFilter(from_timestamp=from_date, project_id=project_id)
        traces = await client.get_traces(filter)

        # Aggregate by hour
        hourly_data: Dict[str, HourlyMetric] = {}
        for trace in traces:
            hour_key = trace.timestamp.strftime("%Y-%m-%dT%H:00:00")
            if hour_key not in hourly_data:
                hourly_data[hour_key] = HourlyMetric(hour=hour_key)

            metric = hourly_data[hour_key]
            metric.requests += 1
            metric.tokens += trace.total_tokens
            metric.cost += trace.total_cost
            # Check for errors in trace metadata
            if trace.metadata and trace.metadata.get("error"):
                metric.errors += 1

        # Sort by hour
        sorted_metrics = sorted(hourly_data.values(), key=lambda m: m.hour)

        return HourlyMetricsResponse(metrics=sorted_metrics, period_hours=hours)
    except Exception as e:
        logger.error(f"Failed to get hourly metrics: {e}")
        return HourlyMetricsResponse(period_hours=hours)


@router.get("/metrics/errors", response_model=ErrorMetricsResponse)
async def get_error_metrics(
    hours: int = Query(default=24, le=168),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
) -> ErrorMetricsResponse:
    """Get error metrics and breakdown for the last N hours.

    Pass project_id to filter data for a specific project.
    """
    from .app import get_langfuse_client

    client = get_langfuse_client()
    if not client or not client.is_configured():
        return ErrorMetricsResponse()

    try:
        from_date = datetime.utcnow() - timedelta(hours=hours)
        filter = TraceFilter(from_timestamp=from_date, project_id=project_id)
        traces = await client.get_traces(filter)

        total_traces = len(traces)
        error_counts: Dict[str, int] = {}
        recent_errors = []
        last_occurrences: Dict[str, datetime] = {}

        for trace in traces:
            error = trace.metadata.get("error") if trace.metadata else None
            if error:
                error_type = str(type(error).__name__) if not isinstance(error, str) else error[:50]
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

                if error_type not in last_occurrences or trace.timestamp > last_occurrences[error_type]:
                    last_occurrences[error_type] = trace.timestamp

                if len(recent_errors) < 5:
                    recent_errors.append({
                        "spec_id": get_spec_id_from_trace(trace),
                        "error": error[:100] if isinstance(error, str) else str(error)[:100],
                        "timestamp": trace.timestamp.isoformat(),
                        "agent_type": get_agent_type_from_trace(trace)
                    })

        total_errors = sum(error_counts.values())
        error_rate = (total_errors / total_traces * 100) if total_traces > 0 else 0.0

        breakdown = [
            ErrorBreakdown(
                error_type=error_type,
                count=count,
                percentage=(count / total_errors * 100) if total_errors > 0 else 0.0,
                last_occurrence=last_occurrences.get(error_type)
            )
            for error_type, count in sorted(error_counts.items(), key=lambda x: -x[1])
        ]

        return ErrorMetricsResponse(
            total_errors=total_errors,
            error_rate=round(error_rate, 2),
            breakdown=breakdown,
            recent_errors=recent_errors
        )
    except Exception as e:
        logger.error(f"Failed to get error metrics: {e}")
        return ErrorMetricsResponse()


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


# =============================================================================
# Health Status Endpoints
# =============================================================================

@router.get("/health/status", response_model=HealthStatusResponse)
async def get_health_status() -> HealthStatusResponse:
    """
    Get health status of all connected services.

    Checks Langfuse API configuration status.
    Returns overall_status: "healthy", "degraded", or "unhealthy".
    """
    from .app import get_langfuse_client

    services = []
    overall_status = "healthy"

    # Check Langfuse configuration
    try:
        client = get_langfuse_client()
        if client and client.is_configured():
            services.append(ServiceHealth(
                name="langfuse",
                status="healthy",
                message="Configured and ready"
            ))
        else:
            services.append(ServiceHealth(
                name="langfuse",
                status="degraded",
                message="Not configured - analytics features limited"
            ))
            overall_status = "degraded"
    except Exception as e:
        services.append(ServiceHealth(
            name="langfuse",
            status="unhealthy",
            message=str(e)
        ))
        overall_status = "unhealthy"

    return HealthStatusResponse(
        overall_status=overall_status,
        services=services
    )


# =============================================================================
# Recent Activity Endpoints
# =============================================================================

# =============================================================================
# Artifacts Endpoints (Value Attribution Traceability)
# =============================================================================

def _enrich_artifact_with_full_content(artifact: dict, project_path: Optional[str]) -> dict:
    """
    Enrich an artifact with full content from local storage if available.

    If the artifact has an 'id' and local storage is available, load the full content
    from the local file system instead of using the truncated Langfuse preview.
    """
    if not project_path or not ARTIFACT_STORAGE_AVAILABLE:
        return artifact

    artifact_id = artifact.get("id")
    if not artifact_id:
        return artifact

    try:
        full_artifact = load_artifact(artifact_id, Path(project_path))
        if full_artifact:
            # Replace truncated content with full content
            return {
                **artifact,
                "content": full_artifact.get("content", artifact.get("content", "")),
                "full_content_loaded": True,
            }
    except Exception as e:
        logger.debug(f"Failed to load full artifact {artifact_id}: {e}")

    return artifact


@router.get("/artifacts")
async def get_artifacts(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    trace_id: Optional[str] = Query(None, description="Get artifacts for specific trace"),
    project_path: Optional[str] = Query(None, description="Project path to load full artifact content from local storage"),
    from_date: Optional[str] = Query(None, description="Filter from date (ISO format YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter to date (ISO format YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
):
    """
    Get artifacts generated by insights/agents with value attribution.

    Returns artifacts extracted from trace outputs including:
    - Diagrams (mermaid, ascii)
    - Code examples
    - Recommendations
    - Security findings

    Each artifact includes its value contribution to ROI.

    If project_path is provided and local artifact storage is available,
    artifacts will include FULL content instead of truncated previews.
    """
    client = get_client()

    try:
        artifacts_response = []

        if trace_id:
            # Get specific trace
            trace = await client.get_trace(trace_id)
            if trace and trace.output:
                output = trace.output if isinstance(trace.output, dict) else {}
                value_attr = output.get("value_attribution", {})
                artifacts = value_attr.get("artifacts", [])

                # Enrich artifacts with full content from local storage
                enriched_artifacts = [
                    _enrich_artifact_with_full_content(a, project_path)
                    for a in artifacts
                ]

                artifacts_response.append({
                    "trace_id": trace_id,
                    "trace_name": trace.name,
                    "timestamp": trace.timestamp.isoformat() if trace.timestamp else None,
                    "query": trace.input[:200] if isinstance(trace.input, str) else str(trace.input)[:200],
                    "total_value_usd": output.get("total_calculated_value", 0),
                    "value_breakdown": {
                        # Standard categories (from insights value_attribution)
                        "diagrams": value_attr.get("diagrams", {}).get("total_value", 0),
                        "security": value_attr.get("security_insights", {}).get("total_value", 0),
                        "recommendations": value_attr.get("recommendations", {}).get("total_value", 0),
                        "code_explanations": value_attr.get("code_explanations", {}).get("total_value", 0),
                        # Additional categories from artifact_values_by_type (for all MCP-created artifacts)
                        **{
                            art_type: info.get("total_value", 0)
                            for art_type, info in value_attr.get("artifact_values_by_type", {}).items()
                            if info.get("total_value", 0) > 0
                        },
                    },
                    "artifacts": enriched_artifacts,
                    "artifact_count": len(enriched_artifacts),
                })
        else:
            # Parse date filters if provided
            from_timestamp = None
            to_timestamp = None
            if from_date:
                try:
                    from_timestamp = datetime.fromisoformat(from_date)
                except ValueError:
                    logger.warning(f"Invalid from_date format: {from_date}")
            if to_date:
                try:
                    # Add 1 day to include the end date fully
                    to_timestamp = datetime.fromisoformat(to_date) + timedelta(days=1)
                except ValueError:
                    logger.warning(f"Invalid to_date format: {to_date}")

            # Get recent traces with artifacts
            filter = TraceFilter(
                project_id=project_id,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                limit=limit,
            )
            traces = await client.get_traces(filter)

            for trace in traces:
                # Get full trace details to access output
                full_trace = await client.get_trace(trace.id)
                if not full_trace or not full_trace.output:
                    continue

                output = full_trace.output if isinstance(full_trace.output, dict) else {}
                value_attr = output.get("value_attribution", {})
                artifacts = value_attr.get("artifacts", [])

                # Only include traces that have artifacts
                if artifacts or output.get("total_calculated_value", 0) > 0:
                    # Enrich artifacts with full content from local storage
                    enriched_artifacts = [
                        _enrich_artifact_with_full_content(a, project_path)
                        for a in artifacts
                    ]

                    artifacts_response.append({
                        "trace_id": trace.id,
                        "trace_name": trace.name,
                        "timestamp": trace.timestamp.isoformat() if trace.timestamp else None,
                        "query": full_trace.input[:200] if isinstance(full_trace.input, str) else str(full_trace.input)[:200] if full_trace.input else "",
                        "total_value_usd": output.get("total_calculated_value", 0),
                        "value_breakdown": {
                            # Standard categories (from insights value_attribution)
                            "diagrams": value_attr.get("diagrams", {}).get("total_value", 0),
                            "security": value_attr.get("security_insights", {}).get("total_value", 0),
                            "recommendations": value_attr.get("recommendations", {}).get("total_value", 0),
                            "code_explanations": value_attr.get("code_explanations", {}).get("total_value", 0),
                            # Additional categories from artifact_values_by_type (for all MCP-created artifacts)
                            **{
                                art_type: info.get("total_value", 0)
                                for art_type, info in value_attr.get("artifact_values_by_type", {}).items()
                                if info.get("total_value", 0) > 0
                            },
                        },
                        "artifacts": enriched_artifacts,
                        "artifact_count": len(enriched_artifacts),
                    })

        return {
            "artifacts": artifacts_response,
            "total": len(artifacts_response),
        }

    except Exception as e:
        logger.error(f"Failed to get artifacts: {e}")
        return {"artifacts": [], "total": 0, "error": str(e)}


@router.get("/artifacts/local")
async def get_local_artifacts(
    project_path: str = Query(..., description="Project path to load artifacts from"),
    spec_id: Optional[str] = Query(None, description="Filter by spec ID"),
    trace_id: Optional[str] = Query(None, description="Filter by trace ID"),
    artifact_type: Optional[str] = Query(None, description="Filter by artifact type"),
    from_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
):
    """
    Get artifacts directly from local storage with FULL content.

    This endpoint bypasses Langfuse and reads artifacts directly from the
    .auto-claude/artifacts/ directory, returning complete untruncated content.
    """
    if not ARTIFACT_STORAGE_AVAILABLE:
        return {
            "artifacts": [],
            "total": 0,
            "error": "Artifact storage module not available",
        }

    try:
        # list_local_artifacts expects keyword arguments, not a dict
        artifacts = list_local_artifacts(
            project_dir=Path(project_path),
            spec_id=spec_id,
            trace_id=trace_id,
            date_from=from_date,
            date_to=to_date,
            artifact_types=[artifact_type] if artifact_type else None,
            limit=limit,
        )

        return {
            "artifacts": artifacts,
            "total": len(artifacts),
            "source": "local_storage",
            "full_content": True,
        }
    except Exception as e:
        logger.error(f"Failed to get local artifacts: {e}")
        return {"artifacts": [], "total": 0, "error": str(e)}


@router.get("/artifacts/local/{artifact_id}")
async def get_local_artifact(
    artifact_id: str,
    project_path: str = Query(..., description="Project path to load artifact from"),
):
    """
    Get a single artifact by ID with FULL content from local storage.

    This endpoint reads the artifact directly from the .auto-claude/artifacts/
    directory, returning the complete untruncated content.
    """
    if not ARTIFACT_STORAGE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Artifact storage module not available",
        )

    try:
        artifact = load_artifact(artifact_id, Path(project_path))
        if not artifact:
            raise HTTPException(
                status_code=404,
                detail=f"Artifact not found: {artifact_id}",
            )

        return {
            "artifact": artifact,
            "source": "local_storage",
            "full_content": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get local artifact {artifact_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load artifact: {str(e)}",
        )


@router.get("/specs/recent-activity", response_model=RecentActivityResponse)
async def get_recent_activity(limit: int = Query(default=10, le=50)) -> RecentActivityResponse:
    """Get recent spec activity events."""
    from .app import get_langfuse_client

    client = get_langfuse_client()
    if not client or not client.is_configured():
        return RecentActivityResponse()

    try:
        filter = TraceFilter(limit=limit)
        traces = await client.get_traces(filter)
        events = []
        for trace in traces:
            agent_type = get_agent_type_from_trace(trace)
            spec_id = get_spec_id_from_trace(trace)

            # Determine event type from agent
            event_type = "started"
            if "qa" in agent_type:
                event_type = "qa_review"
            elif agent_type == "coder":
                event_type = "coding"
            elif agent_type == "planner":
                event_type = "planning"

            events.append(ActivityEvent(
                spec_id=spec_id,
                event_type=event_type,
                timestamp=trace.timestamp,
                agent_type=agent_type,
                details=trace.name
            ))

        return RecentActivityResponse(events=events, total=len(events))
    except Exception as e:
        logger.error(f"Failed to get recent activity: {e}")
        return RecentActivityResponse()


# =============================================================================
# Rich Artifact Endpoints (Search, Statistics, Timeline)
# =============================================================================


def _parse_artifact_metadata(artifact: dict) -> ArtifactMetadataModel:
    """Parse artifact metadata into the ArtifactMetadataModel."""
    meta = artifact.get("metadata", {})
    return ArtifactMetadataModel(
        title=meta.get("title") or meta.get("feature_name"),
        priority=meta.get("priority"),
        complexity=meta.get("complexity"),
        impact=meta.get("impact"),
        status=meta.get("status"),
        phase=meta.get("phase"),
        phase_id=meta.get("phase_id"),
        feature_id=meta.get("feature_id"),
        feature_name=meta.get("feature_name"),
        feature_index=meta.get("feature_index"),
        has_acceptance_criteria=meta.get("has_acceptance_criteria", False),
        has_user_stories=meta.get("has_user_stories", False),
        has_rationale=meta.get("has_rationale", False),
        dependency_count=meta.get("dependency_count", 0),
        ideation_type=meta.get("ideation_type"),
    )


def _extract_rich_fields_from_content(content: str) -> dict:
    """Extract rationale, acceptance criteria, user stories, and dependencies from content."""
    import re

    result = {
        "rationale": None,
        "acceptance_criteria": [],
        "user_stories": [],
        "dependencies": [],
    }

    if not content:
        return result

    # Extract Strategic Rationale section
    rationale_match = re.search(
        r'##\s*(?:Strategic\s+)?Rationale\s*\n+(.+?)(?=\n##|\Z)',
        content, re.DOTALL | re.IGNORECASE
    )
    if rationale_match:
        result["rationale"] = rationale_match.group(1).strip()

    # Extract Acceptance Criteria section (numbered list)
    ac_match = re.search(
        r'##\s*Acceptance\s+Criteria\s*\n+(.+?)(?=\n##|\Z)',
        content, re.DOTALL | re.IGNORECASE
    )
    if ac_match:
        criteria_text = ac_match.group(1)
        result["acceptance_criteria"] = re.findall(r'^\d+\.\s*(.+)$', criteria_text, re.MULTILINE)

    # Extract User Stories section (bullet list)
    us_match = re.search(
        r'##\s*User\s+Stories\s*\n+(.+?)(?=\n##|\Z)',
        content, re.DOTALL | re.IGNORECASE
    )
    if us_match:
        stories_text = us_match.group(1)
        result["user_stories"] = re.findall(r'^-\s*(.+)$', stories_text, re.MULTILINE)

    # Extract Dependencies section
    deps_match = re.search(
        r'##\s*Dependencies\s*\n+(.+?)(?=\n##|\Z)',
        content, re.DOTALL | re.IGNORECASE
    )
    if deps_match:
        deps_text = deps_match.group(1)
        # Match "Requires: **Feature Name**" pattern
        deps = re.findall(r'Requires:\s*\*\*([^*]+)\*\*', deps_text)
        if not deps:
            # Fallback to bullet list
            deps = re.findall(r'^-\s*(.+)$', deps_text, re.MULTILINE)
        result["dependencies"] = deps

    return result


def _convert_to_rich_artifact(artifact: dict) -> RichArtifactResponse:
    """Convert a raw artifact dict to RichArtifactResponse."""
    metadata = _parse_artifact_metadata(artifact)
    content = artifact.get("content", "")
    rich_fields = _extract_rich_fields_from_content(content)

    return RichArtifactResponse(
        id=artifact.get("id", ""),
        type=artifact.get("type", "unknown"),
        format=artifact.get("format", "markdown"),
        content=content,
        value_usd=artifact.get("value_usd", 0.0),
        description=artifact.get("description"),
        tab=artifact.get("tab"),
        created_at=artifact.get("created_at", ""),
        trace_id=artifact.get("trace_id"),
        spec_id=artifact.get("spec_id"),
        project_id=artifact.get("project_id"),
        agent_type=artifact.get("agent_type"),
        session_num=artifact.get("session_num"),
        metadata=metadata,
        rationale=rich_fields["rationale"],
        acceptance_criteria=rich_fields["acceptance_criteria"],
        user_stories=rich_fields["user_stories"],
        dependencies=rich_fields["dependencies"],
    )


@router.get("/artifacts/search", response_model=LocalArtifactsResponse)
async def search_artifacts(
    project_path: str = Query(..., description="Project path to search artifacts"),
    query: Optional[str] = Query(None, description="Full-text search query"),
    types: Optional[str] = Query(None, description="Comma-separated artifact types"),
    priorities: Optional[str] = Query(None, description="Comma-separated priorities (must,should,could,wont)"),
    has_rationale: Optional[bool] = Query(None, description="Filter by has rationale"),
    has_acceptance_criteria: Optional[bool] = Query(None, description="Filter by has acceptance criteria"),
    has_dependencies: Optional[bool] = Query(None, description="Filter by has dependencies"),
    min_value: Optional[float] = Query(None, description="Minimum value USD"),
    max_value: Optional[float] = Query(None, description="Maximum value USD"),
    agent_types: Optional[str] = Query(None, description="Comma-separated agent types"),
    tabs: Optional[str] = Query(None, description="Comma-separated tabs (dev,techlead,ops,business)"),
    from_date: Optional[str] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="To date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    Search artifacts with rich filtering and full-text search.

    Supports filtering by:
    - Full-text query across content, title, description
    - Artifact type (roadmap_feature, idea, security_finding, etc.)
    - Priority (must, should, could, wont)
    - Quality flags (has_rationale, has_acceptance_criteria, has_dependencies)
    - Value range (min_value, max_value)
    - Agent type (roadmap_generator, ideation, qa_reviewer, etc.)
    - Tab (dev, techlead, ops, business)
    - Date range
    """
    if not ARTIFACT_STORAGE_AVAILABLE:
        return LocalArtifactsResponse(
            artifacts=[],
            total=0,
            error="Artifact storage module not available",
        )

    try:
        # Parse comma-separated filters
        type_list = [t.strip() for t in types.split(",")] if types else None
        priority_list = [p.strip().lower() for p in priorities.split(",")] if priorities else None
        agent_type_list = [a.strip() for a in agent_types.split(",")] if agent_types else None
        tab_list = [t.strip() for t in tabs.split(",")] if tabs else None

        # Get all artifacts with basic filtering
        artifacts = list_local_artifacts(
            project_dir=Path(project_path),
            date_from=from_date,
            date_to=to_date,
            artifact_types=type_list,
            limit=500,  # Get more to filter locally
        )

        # Apply additional filters
        filtered = []
        for art in artifacts:
            # Full-text search
            if query:
                query_lower = query.lower()
                content = (art.get("content", "") or "").lower()
                description = (art.get("description", "") or "").lower()
                title = (art.get("metadata", {}).get("title", "") or "").lower()
                if query_lower not in content and query_lower not in description and query_lower not in title:
                    continue

            # Priority filter
            if priority_list:
                art_priority = (art.get("metadata", {}).get("priority", "") or "").lower()
                if art_priority not in priority_list:
                    continue

            # Quality flags filters
            meta = art.get("metadata", {})
            if has_rationale is not None and meta.get("has_rationale", False) != has_rationale:
                continue
            if has_acceptance_criteria is not None and meta.get("has_acceptance_criteria", False) != has_acceptance_criteria:
                continue
            if has_dependencies is not None and (meta.get("dependency_count", 0) > 0) != has_dependencies:
                continue

            # Value range filter
            value = art.get("value_usd", 0)
            if min_value is not None and value < min_value:
                continue
            if max_value is not None and value > max_value:
                continue

            # Agent type filter
            if agent_type_list:
                art_agent = art.get("agent_type", "")
                if art_agent not in agent_type_list:
                    continue

            # Tab filter
            if tab_list:
                art_tab = art.get("tab", "")
                if art_tab not in tab_list:
                    continue

            filtered.append(art)

        # Apply pagination
        total = len(filtered)
        paginated = filtered[offset:offset + limit]

        # Convert to rich response
        rich_artifacts = [_convert_to_rich_artifact(a) for a in paginated]

        # Calculate stats for filtered results
        stats = _calculate_artifact_statistics(filtered)

        return LocalArtifactsResponse(
            artifacts=rich_artifacts,
            total=total,
            limit=limit,
            offset=offset,
            stats=stats,
        )

    except Exception as e:
        logger.error(f"Failed to search artifacts: {e}")
        return LocalArtifactsResponse(artifacts=[], total=0, error=str(e))


def _calculate_artifact_statistics(artifacts: List[dict]) -> ArtifactStatistics:
    """Calculate statistics from a list of artifacts."""
    from collections import defaultdict

    if not artifacts:
        return ArtifactStatistics()

    by_type = defaultdict(int)
    by_agent = defaultdict(int)
    by_priority = defaultdict(int)
    by_tab = defaultdict(int)
    value_by_type = defaultdict(float)
    value_by_priority = defaultdict(float)

    total_value = 0.0
    with_rationale = 0
    with_acceptance_criteria = 0
    with_user_stories = 0
    with_dependencies = 0
    with_any_quality = 0

    for art in artifacts:
        art_type = art.get("type", "unknown")
        agent = art.get("agent_type", "unknown")
        tab = art.get("tab", "unknown")
        value = art.get("value_usd", 0)
        meta = art.get("metadata", {})
        priority = (meta.get("priority", "") or "unknown").lower()

        by_type[art_type] += 1
        by_agent[agent] += 1
        by_priority[priority] += 1
        by_tab[tab] += 1

        total_value += value
        value_by_type[art_type] += value
        value_by_priority[priority] += value

        # Quality metrics
        has_r = meta.get("has_rationale", False)
        has_ac = meta.get("has_acceptance_criteria", False)
        has_us = meta.get("has_user_stories", False)
        has_deps = meta.get("dependency_count", 0) > 0

        if has_r:
            with_rationale += 1
        if has_ac:
            with_acceptance_criteria += 1
        if has_us:
            with_user_stories += 1
        if has_deps:
            with_dependencies += 1
        if has_r or has_ac or has_us or has_deps:
            with_any_quality += 1

    total_count = len(artifacts)
    quality_pct = (with_any_quality / total_count * 100) if total_count > 0 else 0

    return ArtifactStatistics(
        total_count=total_count,
        total_value_usd=round(total_value, 2),
        by_type=dict(by_type),
        by_agent=dict(by_agent),
        by_priority=dict(by_priority),
        by_tab=dict(by_tab),
        quality_metrics=ArtifactQualityMetrics(
            with_rationale=with_rationale,
            with_acceptance_criteria=with_acceptance_criteria,
            with_user_stories=with_user_stories,
            with_dependencies=with_dependencies,
            total_with_quality=with_any_quality,
            quality_percentage=round(quality_pct, 1),
        ),
        avg_value_per_artifact=round(total_value / total_count, 2) if total_count > 0 else 0,
        value_by_type={k: round(v, 2) for k, v in value_by_type.items()},
        value_by_priority={k: round(v, 2) for k, v in value_by_priority.items()},
    )


@router.get("/artifacts/statistics", response_model=ArtifactStatistics)
async def get_artifact_statistics(
    project_path: str = Query(..., description="Project path to get statistics"),
    from_date: Optional[str] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="To date (YYYY-MM-DD)"),
):
    """
    Get aggregate statistics for artifacts.

    Returns:
    - Total count and value
    - Breakdown by type, agent, priority, tab
    - Quality metrics (rationale, acceptance criteria, user stories, dependencies)
    - Value distribution by type and priority
    """
    if not ARTIFACT_STORAGE_AVAILABLE:
        return ArtifactStatistics()

    try:
        artifacts = list_local_artifacts(
            project_dir=Path(project_path),
            date_from=from_date,
            date_to=to_date,
            limit=1000,  # Get all for statistics
        )

        return _calculate_artifact_statistics(artifacts)

    except Exception as e:
        logger.error(f"Failed to get artifact statistics: {e}")
        return ArtifactStatistics()


@router.get("/artifacts/timeline", response_model=ArtifactTimelineResponse)
async def get_artifact_timeline(
    project_path: str = Query(..., description="Project path to get timeline"),
    granularity: str = Query("day", description="Timeline granularity (hour, day, week)"),
    from_date: Optional[str] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="To date (YYYY-MM-DD)"),
):
    """
    Get artifact creation timeline for visualization.

    Returns time-series data showing artifact creation over time,
    grouped by the specified granularity (hour, day, or week).
    """
    from collections import defaultdict

    if not ARTIFACT_STORAGE_AVAILABLE:
        return ArtifactTimelineResponse(granularity=granularity)

    try:
        artifacts = list_local_artifacts(
            project_dir=Path(project_path),
            date_from=from_date,
            date_to=to_date,
            limit=1000,
        )

        # Group by time period
        timeline_data = defaultdict(lambda: {
            "count": 0,
            "value_usd": 0.0,
            "by_type": defaultdict(int),
            "by_agent": defaultdict(int),
        })

        total_count = 0
        total_value = 0.0

        for art in artifacts:
            created_at = art.get("created_at", "")
            if not created_at:
                continue

            # Parse timestamp and get period key
            try:
                if "T" in created_at:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    dt = datetime.fromisoformat(created_at)

                if granularity == "hour":
                    period_key = dt.strftime("%Y-%m-%d %H:00")
                elif granularity == "week":
                    # Get start of week (Monday)
                    week_start = dt - timedelta(days=dt.weekday())
                    period_key = week_start.strftime("%Y-%m-%d")
                else:  # day
                    period_key = dt.strftime("%Y-%m-%d")

            except (ValueError, TypeError):
                continue

            art_type = art.get("type", "unknown")
            agent = art.get("agent_type", "unknown")
            value = art.get("value_usd", 0)

            timeline_data[period_key]["count"] += 1
            timeline_data[period_key]["value_usd"] += value
            timeline_data[period_key]["by_type"][art_type] += 1
            timeline_data[period_key]["by_agent"][agent] += 1

            total_count += 1
            total_value += value

        # Convert to response
        timeline = [
            ArtifactTimelineEntry(
                date=date,
                count=data["count"],
                value_usd=round(data["value_usd"], 2),
                by_type=dict(data["by_type"]),
                by_agent=dict(data["by_agent"]),
            )
            for date, data in sorted(timeline_data.items())
        ]

        return ArtifactTimelineResponse(
            timeline=timeline,
            granularity=granularity,
            total_count=total_count,
            total_value=round(total_value, 2),
        )

    except Exception as e:
        logger.error(f"Failed to get artifact timeline: {e}")
        return ArtifactTimelineResponse(granularity=granularity)
