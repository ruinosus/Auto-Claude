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
    # Satisfaction models
    SatisfactionSurveyRequest,
    SatisfactionSurveyResponse,
    SatisfactionMetricsResponse,
    NPSResponse,
    FeedbackEntryResponse,
    FeedbackListResponse,
    SurveySubmitResponse,
    # Time Saved models
    TaskBenchmarkResponse,
    TimeSavedSummaryResponse,
    TimeSavedByTaskResponse,
    TimeSavedByTaskListResponse,
    TimeSavedTrendPoint,
    TimeSavedTrendResponse,
    TimeSavedComparisonResponse,
    TimeSavedDashboardResponse,
    # ROI Comparison models
    ROIComparisonResult,
    MarketBenchmarks,
    PercentileThreshold,
    ROIComparisonResponse,
    MultiProjectComparisonResponse,
    BreakEvenAnalysisResult,
    BreakEvenResponse,
    # Value Attribution Breakdown models
    SubcategoryValueResponse,
    ValueBreakdownByCategory,
    ValueBreakdownExpandedResponse,
    ValueBreakdownResponse,
    # Quality Multiplier models
    QualityAdjustment,
    QualityMultiplierResponse,
    QualityMultiplierRequest,
    SpecQualityResponse,
    QualityLeaderboardEntry,
    QualityLeaderboardResponse,
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


# =============================================================================
# Impact Forecast Endpoints
# =============================================================================

# Import forecast models
from .models import (
    ForecastPredictRequest,
    ImpactForecastResponse,
    ForecastComparisonResponse,
    ModelAccuracyResponse,
    ForecastHistoryEntry,
    ForecastHistoryResponse,
    RecordActualRequest,
)

# Lazy import forecast model to avoid circular imports
_forecast_model = None


def _get_forecast_model():
    """Get the forecast model singleton with lazy initialization."""
    global _forecast_model
    if _forecast_model is None:
        try:
            from analytics.impact_forecast import get_forecast_model
            # Use .auto-claude directory for storage if available
            storage_path = Path(".auto-claude/analytics")
            _forecast_model = get_forecast_model(storage_path)
        except ImportError:
            logger.warning("Impact forecast module not available")
            return None
    return _forecast_model


@router.post("/forecast/predict", response_model=ImpactForecastResponse)
async def predict_roi(request: ForecastPredictRequest):
    """
    Predict ROI before running a spec.

    Uses historical data and spec characteristics to forecast:
    - Predicted value (USD)
    - Predicted cost (USD)
    - Predicted ROI percentage
    - 95% confidence interval

    Call this before executing a spec to set expectations.
    """
    model = _get_forecast_model()
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Forecast model not available"
        )

    try:
        forecast = model.predict(
            spec_id=request.spec_id,
            spec_complexity=request.spec_complexity,
            estimated_lines=request.estimated_lines,
            feature_type=request.feature_type,
            historical_similar=request.historical_similar,
        )

        return ImpactForecastResponse(
            spec_id=forecast.spec_id,
            predicted_value_usd=forecast.predicted_value_usd,
            predicted_cost_usd=forecast.predicted_cost_usd,
            predicted_roi=forecast.predicted_roi,
            confidence_interval=list(forecast.confidence_interval),
            prediction_factors=forecast.prediction_factors,
            created_at=forecast.created_at,
        )
    except Exception as e:
        logger.error(f"Failed to predict ROI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast/{spec_id}", response_model=ImpactForecastResponse)
async def get_forecast(spec_id: str):
    """
    Get existing forecast for a spec.

    Returns the prediction made before execution.
    """
    model = _get_forecast_model()
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Forecast model not available"
        )

    forecast = model.get_forecast(spec_id)
    if not forecast:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast found for spec {spec_id}"
        )

    return ImpactForecastResponse(
        spec_id=forecast.spec_id,
        predicted_value_usd=forecast.predicted_value_usd,
        predicted_cost_usd=forecast.predicted_cost_usd,
        predicted_roi=forecast.predicted_roi,
        confidence_interval=list(forecast.confidence_interval),
        prediction_factors=forecast.prediction_factors,
        created_at=forecast.created_at,
    )


@router.post("/forecast/{spec_id}/record-actual", response_model=ForecastComparisonResponse)
async def record_actual_roi(spec_id: str, request: RecordActualRequest):
    """
    Record actual ROI and compare with prediction.

    Call this after spec execution to:
    - Compare predicted vs actual ROI
    - Track prediction accuracy
    - Improve future predictions
    """
    model = _get_forecast_model()
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Forecast model not available"
        )

    comparison = model.compare_with_actual(
        spec_id=spec_id,
        actual_roi=request.actual_roi,
        actual_value_usd=request.actual_value_usd,
        actual_cost_usd=request.actual_cost_usd,
    )

    if not comparison:
        raise HTTPException(
            status_code=404,
            detail=f"No forecast found for spec {spec_id}"
        )

    return ForecastComparisonResponse(
        spec_id=comparison.spec_id,
        predicted_roi=comparison.predicted_roi,
        actual_roi=comparison.actual_roi,
        predicted_value_usd=comparison.predicted_value_usd,
        actual_value_usd=comparison.actual_value_usd,
        predicted_cost_usd=comparison.predicted_cost_usd,
        actual_cost_usd=comparison.actual_cost_usd,
        accuracy_percentage=comparison.accuracy_percentage,
        prediction_error=comparison.prediction_error,
        within_confidence=comparison.within_confidence,
    )


@router.get("/forecast/{spec_id}/comparison", response_model=ForecastComparisonResponse)
async def get_forecast_comparison(spec_id: str):
    """
    Get prediction vs actual comparison for a spec.

    Returns the comparison if actual ROI has been recorded.
    """
    model = _get_forecast_model()
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Forecast model not available"
        )

    # Search history for this spec
    for forecast, actual_roi in model.history:
        if forecast.spec_id == spec_id:
            # Reconstruct comparison
            error = forecast.predicted_roi - actual_roi
            if forecast.predicted_roi != 0:
                relative_error = abs(error) / abs(forecast.predicted_roi)
            else:
                relative_error = abs(error) / 100 if actual_roi != 0 else 0
            accuracy = max(0, 100 - (relative_error * 100))

            ci_low, ci_high = forecast.confidence_interval
            within_ci = ci_low <= actual_roi <= ci_high

            return ForecastComparisonResponse(
                spec_id=spec_id,
                predicted_roi=forecast.predicted_roi,
                actual_roi=actual_roi,
                predicted_value_usd=forecast.predicted_value_usd,
                actual_value_usd=0.0,  # Not stored in history
                predicted_cost_usd=forecast.predicted_cost_usd,
                actual_cost_usd=0.0,  # Not stored in history
                accuracy_percentage=round(accuracy, 2),
                prediction_error=round(error, 2),
                within_confidence=within_ci,
            )

    raise HTTPException(
        status_code=404,
        detail=f"No comparison data found for spec {spec_id}"
    )


@router.get("/forecast/accuracy", response_model=ModelAccuracyResponse)
async def get_forecast_accuracy():
    """
    Get overall model accuracy metrics.

    Returns statistics on prediction performance:
    - Mean accuracy percentage
    - Mean absolute error
    - RMSE
    - Within confidence rate
    - Bias (over/under estimation tendency)
    """
    model = _get_forecast_model()
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Forecast model not available"
        )

    metrics = model.get_model_accuracy()

    return ModelAccuracyResponse(
        total_predictions=metrics.total_predictions,
        mean_accuracy=metrics.mean_accuracy,
        mean_absolute_error=metrics.mean_absolute_error,
        root_mean_square_error=metrics.root_mean_square_error,
        within_confidence_rate=metrics.within_confidence_rate,
        bias=metrics.bias,
        recent_accuracy=metrics.recent_accuracy,
    )


@router.get("/forecast/history", response_model=ForecastHistoryResponse)
async def get_forecast_history(
    limit: int = Query(default=20, ge=1, le=100, description="Max entries to return")
):
    """
    Get recent forecast history with comparisons.

    Returns list of past predictions and their actual outcomes.
    """
    model = _get_forecast_model()
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Forecast model not available"
        )

    history_data = model.get_history_summary(limit=limit)

    history_entries = [
        ForecastHistoryEntry(
            spec_id=entry["spec_id"],
            predicted_roi=entry["predicted_roi"],
            actual_roi=entry["actual_roi"],
            error=entry["error"],
            within_ci=entry["within_ci"],
            created_at=entry["created_at"],
        )
        for entry in history_data
    ]

    return ForecastHistoryResponse(
        history=history_entries,
        total=len(history_entries),
    )


# =============================================================================
# Cost Avoidance Endpoints
# =============================================================================

# Import cost avoidance models
from .models import (
    CostAvoidanceEventResponse,
    CostAvoidanceSummaryResponse,
    CostAvoidanceEventsListResponse,
    CostAvoidanceTrendPoint,
    CostAvoidanceTrendResponse,
    RecordCostAvoidanceEventRequest,
    RecordCostAvoidanceEventResponse,
)

# Lazy import cost avoidance tracker
_cost_avoidance_tracker_cache = {}


def _get_cost_avoidance_tracker(project_path: str):
    """Get or create a cost avoidance tracker for a project."""
    if project_path not in _cost_avoidance_tracker_cache:
        try:
            from analytics.cost_avoidance import CostAvoidanceTracker
            _cost_avoidance_tracker_cache[project_path] = CostAvoidanceTracker(Path(project_path))
        except ImportError:
            logger.warning("Cost avoidance module not available")
            return None
    return _cost_avoidance_tracker_cache[project_path]


@router.get("/cost-avoidance/summary", response_model=CostAvoidanceSummaryResponse)
async def get_cost_avoidance_summary(
    project_path: str = Query(..., description="Project path to get cost avoidance data"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days to include"),
    spec_id: Optional[str] = Query(None, description="Filter by spec ID"),
):
    """
    Get aggregated cost avoidance summary.

    Returns totals by type, severity, and detector along with individual events.
    """
    tracker = _get_cost_avoidance_tracker(project_path)
    if not tracker:
        return CostAvoidanceSummaryResponse()

    try:
        summary = tracker.get_summary(days=days, spec_id=spec_id)

        # Convert events to response models
        events = [
            CostAvoidanceEventResponse(
                id=e.id,
                type=e.type.value,
                severity=e.severity.value,
                estimated_cost_avoided=e.estimated_cost_avoided,
                confidence=e.confidence,
                detected_by=e.detected_by,
                trace_id=e.trace_id,
                artifact_id=e.artifact_id,
                spec_id=e.spec_id,
                project_id=e.project_id,
                description=e.description,
                evidence=e.evidence,
                created_at=e.created_at.isoformat(),
            )
            for e in summary.events
        ]

        return CostAvoidanceSummaryResponse(
            total_cost_avoided=round(summary.total_cost_avoided, 2),
            event_count=summary.event_count,
            by_type={k: round(v, 2) for k, v in summary.by_type.items()},
            by_severity={k: round(v, 2) for k, v in summary.by_severity.items()},
            by_detector={k: round(v, 2) for k, v in summary.by_detector.items()},
            avg_confidence=round(summary.avg_confidence, 2),
            period_start=summary.period_start.isoformat() if summary.period_start else None,
            period_end=summary.period_end.isoformat() if summary.period_end else None,
            events=events,
        )

    except Exception as e:
        logger.error(f"Failed to get cost avoidance summary: {e}")
        return CostAvoidanceSummaryResponse()


@router.get("/cost-avoidance/events", response_model=CostAvoidanceEventsListResponse)
async def list_cost_avoidance_events(
    project_path: str = Query(..., description="Project path to get events"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days to include"),
    type: Optional[str] = Query(None, description="Filter by type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    spec_id: Optional[str] = Query(None, description="Filter by spec ID"),
):
    """
    List cost avoidance events with optional filtering.
    """
    tracker = _get_cost_avoidance_tracker(project_path)
    if not tracker:
        return CostAvoidanceEventsListResponse(days=days)

    try:
        from analytics.cost_avoidance import CostAvoidanceType, Severity as AvoidanceSeverity

        # Convert string filters to enums
        type_filter = CostAvoidanceType(type) if type else None
        severity_filter = AvoidanceSeverity(severity.lower()) if severity else None

        events = tracker.get_events(
            days=days,
            avoidance_type=type_filter,
            severity=severity_filter,
            spec_id=spec_id,
        )

        event_responses = [
            CostAvoidanceEventResponse(
                id=e.id,
                type=e.type.value,
                severity=e.severity.value,
                estimated_cost_avoided=e.estimated_cost_avoided,
                confidence=e.confidence,
                detected_by=e.detected_by,
                trace_id=e.trace_id,
                artifact_id=e.artifact_id,
                spec_id=e.spec_id,
                project_id=e.project_id,
                description=e.description,
                evidence=e.evidence,
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ]

        return CostAvoidanceEventsListResponse(
            events=event_responses,
            total=len(event_responses),
            days=days,
        )

    except Exception as e:
        logger.error(f"Failed to list cost avoidance events: {e}")
        return CostAvoidanceEventsListResponse(days=days)


@router.post("/cost-avoidance/event", response_model=RecordCostAvoidanceEventResponse)
async def record_cost_avoidance_event(
    project_path: str = Query(..., description="Project path to record event in"),
    request: RecordCostAvoidanceEventRequest = ...,
):
    """
    Manually record a cost avoidance event.

    Use this to record events detected by external tools or manual review.
    """
    tracker = _get_cost_avoidance_tracker(project_path)
    if not tracker:
        raise HTTPException(
            status_code=503,
            detail="Cost avoidance tracker not available"
        )

    try:
        from analytics.cost_avoidance import (
            CostAvoidanceType,
            Severity as AvoidanceSeverity,
            CostAvoidanceEvent,
            calculate_avoidance_value,
        )

        # Parse type and severity
        avoidance_type = CostAvoidanceType(request.type)
        severity = AvoidanceSeverity(request.severity.lower())

        # Calculate estimated cost avoided
        estimated_cost = calculate_avoidance_value(
            avoidance_type, severity, request.base_cost
        )

        # Create event
        event = CostAvoidanceEvent(
            type=avoidance_type,
            severity=severity,
            estimated_cost_avoided=estimated_cost,
            confidence=request.confidence,
            detected_by=request.detected_by,
            trace_id=request.trace_id,
            artifact_id=request.artifact_id,
            spec_id=request.spec_id,
            project_id=Path(project_path).name,
            description=request.description,
            evidence=request.evidence,
        )

        event_id = tracker.record_event(event)

        return RecordCostAvoidanceEventResponse(
            success=True,
            event_id=event_id,
            estimated_cost_avoided=round(estimated_cost, 2),
            message=f"Cost avoidance event recorded: ${estimated_cost:.2f} saved",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type or severity: {e}"
        )
    except Exception as e:
        logger.error(f"Failed to record cost avoidance event: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record event: {e}"
        )


@router.get("/cost-avoidance/trend", response_model=CostAvoidanceTrendResponse)
async def get_cost_avoidance_trend(
    project_path: str = Query(..., description="Project path to get trend data"),
    days: int = Query(default=90, ge=7, le=365, description="Number of days to include"),
    granularity: str = Query(default="week", description="Aggregation granularity: day, week, month"),
):
    """
    Get cost avoidance trend over time for visualization.

    Returns time-series data showing cost avoided per period.
    """
    from collections import defaultdict

    tracker = _get_cost_avoidance_tracker(project_path)
    if not tracker:
        return CostAvoidanceTrendResponse(granularity=granularity)

    try:
        events = tracker.get_events(days=days)

        if not events:
            return CostAvoidanceTrendResponse(granularity=granularity)

        # Group by period
        trend_data = defaultdict(lambda: {"cost_avoided": 0.0, "event_count": 0, "by_type": defaultdict(float)})

        for event in events:
            dt = event.created_at

            if granularity == "day":
                period_key = dt.strftime("%Y-%m-%d")
            elif granularity == "month":
                period_key = dt.strftime("%Y-%m-01")
            else:  # week
                week_start = dt - timedelta(days=dt.weekday())
                period_key = week_start.strftime("%Y-%m-%d")

            trend_data[period_key]["cost_avoided"] += event.estimated_cost_avoided
            trend_data[period_key]["event_count"] += 1
            trend_data[period_key]["by_type"][event.type.value] += event.estimated_cost_avoided

        # Convert to response
        total_cost = sum(d["cost_avoided"] for d in trend_data.values())

        trend = [
            CostAvoidanceTrendPoint(
                date=date,
                cost_avoided=round(data["cost_avoided"], 2),
                event_count=data["event_count"],
                by_type={k: round(v, 2) for k, v in data["by_type"].items()},
            )
            for date, data in sorted(trend_data.items())
        ]

        return CostAvoidanceTrendResponse(
            trend=trend,
            granularity=granularity,
            total_cost_avoided=round(total_cost, 2),
        )

    except Exception as e:
        logger.error(f"Failed to get cost avoidance trend: {e}")
        return CostAvoidanceTrendResponse(granularity=granularity)


# =============================================================================
# ROI Comparison Endpoints
# =============================================================================


@router.get("/roi/compare", response_model=MultiProjectComparisonResponse)
async def compare_project_roi(
    project_ids: Optional[str] = Query(
        None,
        description="Comma-separated list of project IDs to compare"
    ),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
):
    """
    Compare ROI across multiple projects.

    Returns comparative ROI data including market positioning for each project.
    If no project_ids provided, compares all available projects.
    """
    try:
        from analytics.roi_comparison import ROIComparator, ProjectROIData

        client = get_client()
        comparator = ROIComparator()

        # Parse project IDs
        project_id_list = None
        if project_ids:
            project_id_list = [p.strip() for p in project_ids.split(",")]

        # Get ROI data for each project
        projects_data: List[ProjectROIData] = []

        if project_id_list:
            for project_id in project_id_list:
                roi_scores = await client.get_scores(
                    name="roi_percentage",
                    project_id=project_id
                )
                if roi_scores:
                    # Aggregate project data
                    total_value = 0.0
                    total_cost = 0.0
                    first_date = None
                    latest_date = None

                    for score in roi_scores:
                        trace = await client.get_trace(score.trace_id)
                        if trace:
                            trace_scores = await client.get_scores(trace_id=trace.id)
                            score_dict = {s.name: s.value for s in trace_scores}
                            total_value += score_dict.get(
                                "total_value_usd",
                                score_dict.get("business_value_usd", 0)
                            )
                            total_cost += score_dict.get(
                                "total_cost_usd",
                                score_dict.get("actual_cost_usd", 0)
                            )
                            if first_date is None or trace.timestamp < first_date:
                                first_date = trace.timestamp
                            if latest_date is None or trace.timestamp > latest_date:
                                latest_date = trace.timestamp

                    if total_cost > 0:
                        roi_pct = ((total_value - total_cost) / total_cost) * 100
                    else:
                        roi_pct = 0.0

                    projects_data.append(ProjectROIData(
                        project_id=project_id,
                        total_value_usd=total_value,
                        total_cost_usd=total_cost,
                        roi_percentage=roi_pct,
                        trace_count=len(roi_scores),
                        first_trace_date=first_date,
                        latest_trace_date=latest_date,
                    ))
        else:
            # Get all available projects from traces
            all_scores = await client.get_scores(name="roi_percentage", limit=500)
            project_aggregates: Dict[str, Dict] = {}

            for score in all_scores:
                trace = await client.get_trace(score.trace_id)
                if not trace:
                    continue

                proj_id = trace.metadata.get("project_id", "default") if trace.metadata else "default"
                if proj_id not in project_aggregates:
                    project_aggregates[proj_id] = {
                        "total_value": 0.0,
                        "total_cost": 0.0,
                        "trace_count": 0,
                        "first_date": None,
                        "latest_date": None,
                    }

                trace_scores = await client.get_scores(trace_id=trace.id)
                score_dict = {s.name: s.value for s in trace_scores}

                project_aggregates[proj_id]["total_value"] += score_dict.get(
                    "total_value_usd",
                    score_dict.get("business_value_usd", 0)
                )
                project_aggregates[proj_id]["total_cost"] += score_dict.get(
                    "total_cost_usd",
                    score_dict.get("actual_cost_usd", 0)
                )
                project_aggregates[proj_id]["trace_count"] += 1

                if project_aggregates[proj_id]["first_date"] is None or \
                   trace.timestamp < project_aggregates[proj_id]["first_date"]:
                    project_aggregates[proj_id]["first_date"] = trace.timestamp
                if project_aggregates[proj_id]["latest_date"] is None or \
                   trace.timestamp > project_aggregates[proj_id]["latest_date"]:
                    project_aggregates[proj_id]["latest_date"] = trace.timestamp

            for proj_id, data in project_aggregates.items():
                if data["total_cost"] > 0:
                    roi_pct = ((data["total_value"] - data["total_cost"]) / data["total_cost"]) * 100
                else:
                    roi_pct = 0.0

                projects_data.append(ProjectROIData(
                    project_id=proj_id,
                    total_value_usd=data["total_value"],
                    total_cost_usd=data["total_cost"],
                    roi_percentage=roi_pct,
                    trace_count=data["trace_count"],
                    first_trace_date=data["first_date"],
                    latest_trace_date=data["latest_date"],
                ))

        # Compare projects
        comparisons = comparator.compare_projects(projects_data)

        # Convert to response models
        comparison_results = [
            ROIComparisonResult(
                project_id=c.project_id,
                roi_percentage=c.roi_percentage,
                cost_per_dollar_value=c.cost_per_dollar_value if c.cost_per_dollar_value != float("inf") else 9999.99,
                break_even_days=c.break_even_days,
                vs_market_avg=c.vs_market_avg,
                percentile=c.percentile,
                market_position=c.market_position,
                total_value_usd=c.total_value_usd,
                total_cost_usd=c.total_cost_usd,
                net_value_usd=c.net_value_usd,
                calculated_at=c.calculated_at,
            )
            for c in comparisons
        ]

        # Calculate average ROI
        avg_roi = sum(c.roi_percentage for c in comparisons) / len(comparisons) if comparisons else 0.0

        # Determine best/worst performers
        best_performer = comparisons[0].project_id if comparisons else None
        worst_performer = comparisons[-1].project_id if comparisons else None

        benchmarks = comparator.get_market_benchmarks()

        return MultiProjectComparisonResponse(
            comparisons=comparison_results,
            benchmarks=MarketBenchmarks(
                average_roi=benchmarks["average_roi"],
                top_performers_roi=benchmarks["top_performers_roi"],
                median_roi=benchmarks["median_roi"],
                low_performers_roi=benchmarks["low_performers_roi"],
                median_time_saved_percent=benchmarks["median_time_saved_percent"],
            ),
            best_performer=best_performer,
            worst_performer=worst_performer,
            average_roi=round(avg_roi, 1),
            total_projects=len(comparisons),
        )

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="ROI comparison module not available"
        )
    except Exception as e:
        logger.error(f"Failed to compare project ROI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roi/benchmark", response_model=ROIComparisonResponse)
async def get_roi_benchmark(
    project_id: str = Query(..., description="Project ID to benchmark"),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
):
    """
    Get ROI benchmark position for a single project against market averages.

    Returns detailed market positioning including:
    - Percentile ranking
    - Comparison to market average
    - Break-even analysis (if applicable)
    """
    try:
        from analytics.roi_comparison import ROIComparator

        client = get_client()
        comparator = ROIComparator()

        # Get ROI data for the project
        roi_scores = await client.get_scores(name="roi_percentage", project_id=project_id)

        if not roi_scores:
            raise HTTPException(
                status_code=404,
                detail=f"No ROI data found for project {project_id}"
            )

        # Aggregate project data
        total_value = 0.0
        total_cost = 0.0
        first_date = None
        latest_date = None

        for score in roi_scores:
            trace = await client.get_trace(score.trace_id)
            if trace:
                trace_scores = await client.get_scores(trace_id=trace.id)
                score_dict = {s.name: s.value for s in trace_scores}
                total_value += score_dict.get(
                    "total_value_usd",
                    score_dict.get("business_value_usd", 0)
                )
                total_cost += score_dict.get(
                    "total_cost_usd",
                    score_dict.get("actual_cost_usd", 0)
                )
                if first_date is None or trace.timestamp < first_date:
                    first_date = trace.timestamp
                if latest_date is None or trace.timestamp > latest_date:
                    latest_date = trace.timestamp

        # Calculate ROI
        if total_cost > 0:
            roi_percentage = ((total_value - total_cost) / total_cost) * 100
        else:
            roi_percentage = 0.0

        # Calculate days active
        days_active = None
        if first_date:
            delta = (latest_date or datetime.utcnow()) - first_date
            days_active = max(1, delta.days)

        # Compare to market
        comparison = comparator.compare_to_market(
            project_id=project_id,
            roi_percentage=roi_percentage,
            total_value_usd=total_value,
            total_cost_usd=total_cost,
            days_active=days_active,
        )

        # Get percentile thresholds
        thresholds = comparator.get_percentile_thresholds()
        threshold_models = {
            key: PercentileThreshold(min_roi=data["min_roi"], label=data["label"])
            for key, data in thresholds.items()
        }

        benchmarks = comparator.get_market_benchmarks()

        return ROIComparisonResponse(
            comparison=ROIComparisonResult(
                project_id=comparison.project_id,
                roi_percentage=comparison.roi_percentage,
                cost_per_dollar_value=comparison.cost_per_dollar_value if comparison.cost_per_dollar_value != float("inf") else 9999.99,
                break_even_days=comparison.break_even_days,
                vs_market_avg=comparison.vs_market_avg,
                percentile=comparison.percentile,
                market_position=comparison.market_position,
                total_value_usd=comparison.total_value_usd,
                total_cost_usd=comparison.total_cost_usd,
                net_value_usd=comparison.net_value_usd,
                calculated_at=comparison.calculated_at,
            ),
            benchmarks=MarketBenchmarks(
                average_roi=benchmarks["average_roi"],
                top_performers_roi=benchmarks["top_performers_roi"],
                median_roi=benchmarks["median_roi"],
                low_performers_roi=benchmarks["low_performers_roi"],
                median_time_saved_percent=benchmarks["median_time_saved_percent"],
            ),
            percentile_thresholds=threshold_models,
        )

    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="ROI comparison module not available"
        )
    except Exception as e:
        logger.error(f"Failed to get ROI benchmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roi/break-even/{project_id}", response_model=BreakEvenResponse)
async def get_break_even_analysis(
    project_id: str,
):
    """
    Calculate break-even analysis for a project.

    Returns:
    - Days until break-even (if not yet profitable)
    - Daily value and cost rates
    - Projected annual ROI
    - Human-readable recommendation
    """
    try:
        from analytics.roi_comparison import ROIComparator, ProjectROIData

        client = get_client()
        comparator = ROIComparator()

        # Get ROI data for the project
        roi_scores = await client.get_scores(name="roi_percentage", project_id=project_id)

        if not roi_scores:
            raise HTTPException(
                status_code=404,
                detail=f"No ROI data found for project {project_id}"
            )

        # Aggregate project data
        total_value = 0.0
        total_cost = 0.0
        first_date = None
        latest_date = None

        for score in roi_scores:
            trace = await client.get_trace(score.trace_id)
            if trace:
                trace_scores = await client.get_scores(trace_id=trace.id)
                score_dict = {s.name: s.value for s in trace_scores}
                total_value += score_dict.get(
                    "total_value_usd",
                    score_dict.get("business_value_usd", 0)
                )
                total_cost += score_dict.get(
                    "total_cost_usd",
                    score_dict.get("actual_cost_usd", 0)
                )
                if first_date is None or trace.timestamp < first_date:
                    first_date = trace.timestamp
                if latest_date is None or trace.timestamp > latest_date:
                    latest_date = trace.timestamp

        # Calculate ROI
        if total_cost > 0:
            roi_percentage = ((total_value - total_cost) / total_cost) * 100
        else:
            roi_percentage = 0.0

        project_data = ProjectROIData(
            project_id=project_id,
            total_value_usd=total_value,
            total_cost_usd=total_cost,
            roi_percentage=roi_percentage,
            trace_count=len(roi_scores),
            first_trace_date=first_date,
            latest_trace_date=latest_date,
        )

        # Calculate break-even
        analysis = comparator.calculate_break_even(project_data)

        # Generate recommendation
        if analysis.is_profitable:
            if analysis.projected_annual_roi and analysis.projected_annual_roi > 500:
                recommendation = (
                    f"Excellent! Project is generating ${analysis.daily_value_rate:.2f}/day "
                    f"in value. Projected annual ROI: {analysis.projected_annual_roi:.0f}%."
                )
            else:
                recommendation = (
                    f"Project is profitable with ${analysis.cumulative_value - analysis.cumulative_cost:.2f} "
                    f"net value. Continue current usage patterns."
                )
        elif analysis.break_even_days is not None:
            if analysis.break_even_days <= 30:
                recommendation = (
                    f"Project should break even in approximately {analysis.break_even_days} days. "
                    f"Consider increasing AI usage to accelerate value generation."
                )
            else:
                recommendation = (
                    f"Break-even estimated in {analysis.break_even_days} days. "
                    f"Review usage patterns to optimize value extraction."
                )
        else:
            recommendation = (
                "Insufficient data for break-even analysis. "
                "Continue using AI features to accumulate more data points."
            )

        return BreakEvenResponse(
            analysis=BreakEvenAnalysisResult(
                project_id=analysis.project_id,
                break_even_days=analysis.break_even_days,
                daily_value_rate=analysis.daily_value_rate,
                daily_cost_rate=analysis.daily_cost_rate,
                cumulative_value=analysis.cumulative_value,
                cumulative_cost=analysis.cumulative_cost,
                is_profitable=analysis.is_profitable,
                days_since_start=analysis.days_since_start,
                projected_annual_roi=analysis.projected_annual_roi,
            ),
            recommendation=recommendation,
        )

    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="ROI comparison module not available"
        )
    except Exception as e:
        logger.error(f"Failed to calculate break-even: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Value Attribution Breakdown Endpoints
# =============================================================================

# Lazy import for value attribution service
_value_attribution_service_cache = {}


def _get_value_attribution_service(project_path: str):
    """Get or create ValueAttributionService for a project."""
    if project_path not in _value_attribution_service_cache:
        try:
            from analytics.value_attribution import ValueAttributionService
            _value_attribution_service_cache[project_path] = ValueAttributionService()
        except ImportError:
            return None
    return _value_attribution_service_cache.get(project_path)


@router.get("/value/breakdown", response_model=ValueBreakdownResponse)
async def get_value_breakdown(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    project_path: Optional[str] = Query(None, description="Project path to load artifacts from"),
    from_date: Optional[str] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="To date (YYYY-MM-DD)"),
    feature_type: Optional[str] = Query(None, description="Filter by feature type"),
    min_confidence: Optional[float] = Query(
        None, ge=0, le=1,
        description="Minimum confidence threshold"
    ),
):
    """
    Get value breakdown by category and subcategory.

    Returns hierarchical value data suitable for:
    - Treemap visualization (category -> subcategory)
    - Sunburst chart (multi-level drill-down)
    - Category comparison charts

    Filters:
    - project_id: Filter to specific project
    - from_date/to_date: Date range filter
    - feature_type: Filter by feature type (build, spec, insights, etc.)
    - min_confidence: Only include attributions above this confidence threshold
    """
    from collections import defaultdict

    # Try to get artifacts from local storage if project_path is provided
    if project_path and ARTIFACT_STORAGE_AVAILABLE:
        try:
            artifacts = list_local_artifacts(
                project_dir=Path(project_path),
                date_from=from_date,
                date_to=to_date,
                limit=500,
            )
        except Exception as e:
            logger.error(f"Failed to load local artifacts: {e}")
            artifacts = []
    else:
        # Fall back to getting artifacts from Langfuse
        try:
            client = get_client()

            # Parse date filters
            from_timestamp = None
            to_timestamp = None
            if from_date:
                try:
                    from_timestamp = datetime.fromisoformat(from_date)
                except ValueError:
                    pass
            if to_date:
                try:
                    to_timestamp = datetime.fromisoformat(to_date) + timedelta(days=1)
                except ValueError:
                    pass

            filter_obj = TraceFilter(
                project_id=project_id,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                limit=100,
            )
            traces = await client.get_traces(filter_obj)

            # Extract artifacts from traces
            artifacts = []
            for trace in traces:
                full_trace = await client.get_trace(trace.id)
                if not full_trace or not full_trace.output:
                    continue

                output = full_trace.output if isinstance(full_trace.output, dict) else {}
                value_attr = output.get("value_attribution", {})
                trace_artifacts = value_attr.get("artifacts", [])

                for art in trace_artifacts:
                    art["trace_id"] = trace.id
                    art["project_id"] = project_id
                    artifacts.append(art)

        except Exception as e:
            logger.error(f"Failed to get artifacts from Langfuse: {e}")
            artifacts = []

    # Filter by feature type if specified
    if feature_type:
        artifacts = [a for a in artifacts if a.get("feature_type") == feature_type]

    # Use ValueAttributionService to calculate breakdown
    service = _get_value_attribution_service(project_path or "default")

    # Import value attribution modules
    try:
        from analytics.value_attribution import (
            ValueCategory,
            CATEGORY_PARENT_MAP,
            ARTIFACT_TYPE_MAPPING,
        )
        VALUE_ATTRIBUTION_AVAILABLE = True
    except ImportError:
        VALUE_ATTRIBUTION_AVAILABLE = False
        ARTIFACT_TYPE_MAPPING = {}
        CATEGORY_PARENT_MAP = {}

    # Aggregate by category and subcategory
    subcategory_data = defaultdict(lambda: {
        "value_usd": 0.0,
        "confidence_sum": 0.0,
        "count": 0,
        "evidence_count": 0,
        "parent_type": "other",
    })

    category_totals = defaultdict(float)
    total_confidence_sum = 0.0
    total_count = 0

    for artifact in artifacts:
        artifact_type = artifact.get("type", "unknown")
        content = artifact.get("content", "")

        # Get value attribution
        if service and VALUE_ATTRIBUTION_AVAILABLE:
            attribution = service.attribute_value(
                artifact_type=artifact_type,
                content=content,
                metadata=artifact,
            )

            # Apply confidence filter
            if min_confidence and attribution.confidence < min_confidence:
                continue

            subcategory = attribution.category.value
            parent_type = attribution.parent_type
            value = attribution.value_usd
            confidence = attribution.confidence
        else:
            # Fallback: use artifact's pre-calculated value
            value = artifact.get("value_usd", 0)
            confidence = 0.8

            # Map artifact type to category
            mapped_category = ARTIFACT_TYPE_MAPPING.get(artifact_type) if VALUE_ATTRIBUTION_AVAILABLE else None
            if mapped_category:
                subcategory = mapped_category.value
                parent_type = CATEGORY_PARENT_MAP.get(mapped_category, "other")
            else:
                subcategory = "insight_discovered"
                parent_type = "knowledge"

        # Aggregate
        subcategory_data[subcategory]["value_usd"] += value
        subcategory_data[subcategory]["confidence_sum"] += confidence
        subcategory_data[subcategory]["count"] += 1
        subcategory_data[subcategory]["evidence_count"] += len(artifact.get("evidence", []))
        subcategory_data[subcategory]["parent_type"] = parent_type

        category_totals[parent_type] += value
        total_confidence_sum += confidence
        total_count += 1

    # Build response structures
    # Create flat subcategory map
    by_subcategory = {}
    for subcat, data in subcategory_data.items():
        avg_confidence = data["confidence_sum"] / data["count"] if data["count"] > 0 else 0
        by_subcategory[subcat] = SubcategoryValueResponse(
            subcategory=subcat,
            parent_type=data.get("parent_type", "other"),
            value_usd=round(data["value_usd"], 2),
            confidence=round(avg_confidence, 2),
            count=data["count"],
            evidence_count=data["evidence_count"],
        )

    # Build hierarchical category structure
    by_category = []
    for cat_name in ["execution", "decision", "prevention", "knowledge"]:
        cat_subcats = [
            by_subcategory[k]
            for k, v in subcategory_data.items()
            if v.get("parent_type") == cat_name
        ]
        if cat_subcats or category_totals[cat_name] > 0:
            by_category.append(ValueBreakdownByCategory(
                category=cat_name,
                total_value=round(category_totals[cat_name], 2),
                subcategories=sorted(cat_subcats, key=lambda x: x.value_usd, reverse=True),
            ))

    # Calculate totals
    total_value = sum(category_totals.values())
    avg_confidence = total_confidence_sum / total_count if total_count > 0 else 0

    breakdown = ValueBreakdownExpandedResponse(
        execution_value=round(category_totals.get("execution", 0), 2),
        decision_value=round(category_totals.get("decision", 0), 2),
        prevention_value=round(category_totals.get("prevention", 0), 2),
        knowledge_value=round(category_totals.get("knowledge", 0), 2),
        total_value=round(total_value, 2),
        by_category=sorted(by_category, key=lambda x: x.total_value, reverse=True),
        by_subcategory=by_subcategory,
        attribution_count=total_count,
        average_confidence=round(avg_confidence, 2),
    )

    return ValueBreakdownResponse(
        breakdown=breakdown,
        period={
            "from": from_date,
            "to": to_date,
        },
        filters_applied={
            "project_id": project_id,
            "feature_type": feature_type,
            "min_confidence": min_confidence,
        },
    )


# =============================================================================
# Project Benchmark Endpoints (Module 6)
# =============================================================================

# Import benchmark models
from .models import (
    ProjectBenchmarkResponse,
    BestPracticeResponse,
    ProjectRankingsResponse,
    BestPracticesResponse,
    ImprovementSuggestionsResponse,
    PercentileMetricComparison,
    PercentileComparisonResponse,
)

# Lazy import for benchmark service
_benchmark_service = None


def _get_benchmark_service():
    """Get the benchmark service singleton with lazy initialization."""
    global _benchmark_service
    if _benchmark_service is None:
        try:
            from analytics.benchmarks import BenchmarkService
            # Pass Langfuse client if available
            client = get_client()
            _benchmark_service = BenchmarkService(langfuse_client=client)
        except ImportError:
            logger.warning("Benchmark service module not available")
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize benchmark service: {e}")
            from analytics.benchmarks import BenchmarkService
            _benchmark_service = BenchmarkService()  # Use mock data
    return _benchmark_service


@router.get("/benchmarks/projects", response_model=ProjectRankingsResponse)
async def get_project_rankings(
    metric: str = Query(
        default="roi",
        description="Ranking metric: 'roi', 'value', or 'success_rate'"
    ),
    period: str = Query(
        default="30d",
        description="Time period: '7d', '30d', '90d', or 'all'"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of projects to return"
    ),
):
    """
    Get projects ranked by specified metric.

    Returns a leaderboard of projects with their benchmark data,
    useful for comparing team/project performance.

    Metrics:
    - roi: Total ROI percentage (default)
    - value: Total value generated in USD
    - success_rate: Percentage of specs with positive ROI
    """
    service = _get_benchmark_service()
    if not service:
        return ProjectRankingsResponse(metric=metric, period=period)

    try:
        rankings = await service.get_project_rankings(
            metric=metric,
            period=period,
            limit=limit,
        )

        # Convert to response models
        ranking_responses = [
            ProjectBenchmarkResponse(
                project_id=r.project_id,
                total_roi=round(r.total_roi, 2),
                avg_roi_per_spec=round(r.avg_roi_per_spec, 2),
                total_value_generated=round(r.total_value_generated, 2),
                total_cost=round(r.total_cost, 2),
                specs_count=r.specs_count,
                success_rate=round(r.success_rate, 2),
                best_feature_type=r.best_feature_type,
                worst_feature_type=r.worst_feature_type,
                rank=r.rank,
                avg_qa_attempts=round(r.avg_qa_attempts, 2),
                avg_iterations=round(r.avg_iterations, 2),
                total_hours_saved=round(r.total_hours_saved, 2),
                avg_complexity=r.avg_complexity,
            )
            for r in rankings
        ]

        return ProjectRankingsResponse(
            rankings=ranking_responses,
            total=len(ranking_responses),
            metric=metric,
            period=period,
        )

    except Exception as e:
        logger.error(f"Failed to get project rankings: {e}")
        return ProjectRankingsResponse(metric=metric, period=period)


@router.get("/benchmarks/best-practices", response_model=BestPracticesResponse)
async def get_best_practices(
    top_n: int = Query(
        default=10,
        ge=3,
        le=50,
        description="Number of top projects to analyze for patterns"
    ),
):
    """
    Identify best practices from top performers.

    Analyzes top-performing projects to identify success patterns:
    - Low QA iterations
    - High success rates
    - Feature type diversity
    - Cost efficiency
    - Consistent delivery

    Returns actionable insights with adoption rates and examples.
    """
    service = _get_benchmark_service()
    if not service:
        return BestPracticesResponse()

    try:
        practices = await service.identify_best_practices(top_n=top_n)

        # Convert to response models
        practice_responses = [
            BestPracticeResponse(
                pattern=p.pattern,
                description=p.description,
                impact=p.impact,
                adoption_rate=round(p.adoption_rate, 2),
                examples=p.examples[:5],  # Limit examples
                category=p.category,
            )
            for p in practices
        ]

        return BestPracticesResponse(
            practices=practice_responses,
            analyzed_projects=top_n,
            analysis_period="30d",
        )

    except Exception as e:
        logger.error(f"Failed to identify best practices: {e}")
        return BestPracticesResponse()


@router.get("/benchmarks/{project_id}/suggestions", response_model=ImprovementSuggestionsResponse)
async def get_improvement_suggestions(
    project_id: str,
):
    """
    Get improvement suggestions for a specific project.

    Compares the project against top performers and identifies
    specific areas for improvement with actionable recommendations.
    """
    service = _get_benchmark_service()
    if not service:
        return ImprovementSuggestionsResponse(
            project_id=project_id,
            suggestions=["Benchmark service not available"],
        )

    try:
        suggestions = await service.get_improvement_suggestions(project_id=project_id)

        # Get project rank
        rankings = await service.get_project_rankings(limit=100)
        project = next((r for r in rankings if r.project_id == project_id), None)
        current_rank = project.rank if project else None

        return ImprovementSuggestionsResponse(
            project_id=project_id,
            suggestions=suggestions,
            current_rank=current_rank,
            total_projects=len(rankings),
        )

    except Exception as e:
        logger.error(f"Failed to get improvement suggestions: {e}")
        return ImprovementSuggestionsResponse(
            project_id=project_id,
            suggestions=[f"Error generating suggestions: {str(e)}"],
        )


@router.get("/benchmarks/{project_id}/percentile", response_model=PercentileComparisonResponse)
async def compare_to_percentile(
    project_id: str,
    percentile: int = Query(
        default=50,
        ge=1,
        le=99,
        description="Percentile to compare against (50 = median)"
    ),
):
    """
    Compare a project to a specific percentile.

    Returns detailed metric comparisons showing how the project
    performs relative to the specified percentile of all projects.

    Common percentiles:
    - 50: Median (typical performance)
    - 75: Above average
    - 90: Top performer threshold
    """
    service = _get_benchmark_service()
    if not service:
        return PercentileComparisonResponse(
            project_id=project_id,
            percentile=percentile,
        )

    try:
        comparison = await service.compare_to_percentile(
            project_id=project_id,
            percentile=percentile,
        )

        # Convert metrics to response models
        metrics_response = {}
        for metric_name, metric_data in comparison.metrics.items():
            metrics_response[metric_name] = PercentileMetricComparison(
                project_value=round(metric_data["project_value"], 2),
                percentile_value=round(metric_data["percentile_value"], 2),
                delta=round(metric_data["delta"], 2),
                status=metric_data["status"],
            )

        return PercentileComparisonResponse(
            project_id=project_id,
            percentile=percentile,
            metrics=metrics_response,
        )

    except Exception as e:
        logger.error(f"Failed to compare to percentile: {e}")
        return PercentileComparisonResponse(
            project_id=project_id,
            percentile=percentile,
        )


# =============================================================================
# Quality Multiplier Endpoints
# =============================================================================


def _get_quality_calculator():
    """Get the QualityMultiplierCalculator instance."""
    try:
        from analytics.quality_multipliers import (
            QualityMultiplierCalculator,
            get_quality_tier,
            get_quality_color,
        )
        return QualityMultiplierCalculator(), get_quality_tier, get_quality_color
    except ImportError:
        return None, None, None


@router.get("/quality/{spec_id}", response_model=SpecQualityResponse)
async def get_quality_for_spec(
    spec_id: str,
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    """
    Get quality multiplier for a specific spec.

    Fetches QA metrics from Langfuse and calculates the quality multiplier.
    """
    calculator, get_tier, get_color = _get_quality_calculator()
    if not calculator:
        raise HTTPException(
            status_code=503,
            detail="Quality multiplier module not available"
        )

    client = get_client()

    try:
        # Get sessions for this spec
        traces = await client.get_sessions_for_spec(spec_id)
        if not traces:
            raise HTTPException(
                status_code=404,
                detail=f"No traces found for spec {spec_id}"
            )

        # Find QA metrics from traces
        qa_passed = False
        qa_attempts = 0
        has_tests = False
        has_docs = False
        has_types = False
        code_coverage = None
        lint_errors = 0
        rework_needed = False

        for trace in sorted(traces, key=lambda t: t.timestamp, reverse=True):
            # Get scores for this trace
            scores = await client.get_scores(trace_id=trace.id)
            score_dict = {s.name: s.value for s in scores}

            if "qa_passed" in score_dict:
                qa_passed = score_dict.get("qa_passed", 0) > 0.5
                qa_attempts = int(score_dict.get("qa_attempts", 0))
                break

            # Check metadata for QA info
            if trace.metadata:
                if "qa_passed" in trace.metadata:
                    qa_passed = trace.metadata.get("qa_passed", False)
                if "qa_attempts" in trace.metadata:
                    qa_attempts = trace.metadata.get("qa_attempts", 0)
                if "has_tests" in trace.metadata:
                    has_tests = trace.metadata.get("has_tests", False)
                if "has_docs" in trace.metadata:
                    has_docs = trace.metadata.get("has_docs", False)
                if "has_types" in trace.metadata:
                    has_types = trace.metadata.get("has_types", False)
                if "code_coverage" in trace.metadata:
                    code_coverage = trace.metadata.get("code_coverage")
                if "lint_errors" in trace.metadata:
                    lint_errors = trace.metadata.get("lint_errors", 0)
                if "rework_needed" in trace.metadata:
                    rework_needed = trace.metadata.get("rework_needed", False)

        # Calculate quality multiplier
        result = calculator.calculate(
            qa_passed=qa_passed,
            qa_attempts=qa_attempts,
            has_tests=has_tests,
            has_docs=has_docs,
            has_types=has_types,
            code_coverage=code_coverage,
            lint_errors=lint_errors,
            rework_needed=rework_needed,
        )

        return SpecQualityResponse(
            spec_id=spec_id,
            multiplier=QualityMultiplierResponse(
                base_value=result.base_value,
                adjustments=[
                    QualityAdjustment(reason=r, delta=d)
                    for r, d in result.adjustments
                ],
                final_multiplier=result.final_multiplier,
                tier=get_tier(result.final_multiplier),
                color=get_color(result.final_multiplier),
            ),
            qa_passed=qa_passed,
            qa_attempts=qa_attempts,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quality for spec {spec_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get quality metrics: {e}"
        )


@router.get("/quality/leaderboard", response_model=QualityLeaderboardResponse)
async def get_quality_leaderboard(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
):
    """
    Get specs ordered by quality multiplier (highest first).

    Returns a leaderboard of specs ranked by their quality multipliers,
    with summary statistics.
    """
    calculator, get_tier, get_color = _get_quality_calculator()
    if not calculator:
        raise HTTPException(
            status_code=503,
            detail="Quality multiplier module not available"
        )

    client = get_client()

    try:
        # Get ROI scores to find specs with QA data
        roi_scores = await client.get_scores(name="roi_percentage", project_id=project_id)

        # Deduplicate by spec
        spec_ids = set()
        for score in roi_scores:
            trace = await client.get_trace(score.trace_id)
            if trace:
                spec_id = get_spec_id_from_trace(trace)
                if spec_id and not spec_id.startswith("trace-"):
                    spec_ids.add(spec_id)

        # Calculate quality for each spec
        entries = []
        tier_counts = {"exceptional": 0, "good": 0, "neutral": 0, "low": 0, "poor": 0}
        multiplier_sum = 0.0

        for spec_id in list(spec_ids)[:limit * 2]:  # Get extra in case some fail
            try:
                traces = await client.get_sessions_for_spec(spec_id)
                if not traces:
                    continue

                # Find QA metrics
                qa_passed = False
                qa_attempts = 0

                for trace in sorted(traces, key=lambda t: t.timestamp, reverse=True):
                    scores = await client.get_scores(trace_id=trace.id)
                    score_dict = {s.name: s.value for s in scores}

                    if "qa_passed" in score_dict:
                        qa_passed = score_dict.get("qa_passed", 0) > 0.5
                        qa_attempts = int(score_dict.get("qa_attempts", 0))
                        break

                    if trace.metadata and "qa_passed" in trace.metadata:
                        qa_passed = trace.metadata.get("qa_passed", False)
                        qa_attempts = trace.metadata.get("qa_attempts", 0)
                        break

                # Calculate quality
                result = calculator.calculate(
                    qa_passed=qa_passed,
                    qa_attempts=qa_attempts,
                )

                tier = get_tier(result.final_multiplier)
                color = get_color(result.final_multiplier)

                entries.append(QualityLeaderboardEntry(
                    spec_id=spec_id,
                    final_multiplier=result.final_multiplier,
                    tier=tier,
                    color=color,
                    qa_passed=qa_passed,
                    qa_attempts=qa_attempts,
                    adjustments_count=len(result.adjustments),
                ))

                tier_counts[tier] += 1
                multiplier_sum += result.final_multiplier

            except Exception as e:
                logger.debug(f"Could not get quality for spec {spec_id}: {e}")
                continue

        # Sort by multiplier (highest first)
        entries.sort(key=lambda e: e.final_multiplier, reverse=True)
        entries = entries[:limit]

        avg_multiplier = multiplier_sum / len(entries) if entries else 1.0

        return QualityLeaderboardResponse(
            entries=entries,
            total=len(entries),
            average_multiplier=round(avg_multiplier, 2),
            exceptional_count=tier_counts["exceptional"],
            good_count=tier_counts["good"],
            neutral_count=tier_counts["neutral"],
            low_count=tier_counts["low"],
            poor_count=tier_counts["poor"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quality leaderboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get leaderboard: {e}"
        )


@router.post("/quality/calculate", response_model=QualityMultiplierResponse)
async def calculate_quality_multiplier(
    request: QualityMultiplierRequest,
):
    """
    Calculate quality multiplier from provided metrics.

    This endpoint allows calculating a quality multiplier without
    needing a spec - useful for previewing or manual calculations.
    """
    calculator, get_tier, get_color = _get_quality_calculator()
    if not calculator:
        raise HTTPException(
            status_code=503,
            detail="Quality multiplier module not available"
        )

    try:
        result = calculator.calculate(
            qa_passed=request.qa_passed,
            qa_attempts=request.qa_attempts,
            has_tests=request.has_tests,
            has_docs=request.has_docs,
            has_types=request.has_types,
            code_coverage=request.code_coverage,
            lint_errors=request.lint_errors,
            rework_needed=request.rework_needed,
        )

        return QualityMultiplierResponse(
            base_value=result.base_value,
            adjustments=[
                QualityAdjustment(reason=r, delta=d)
                for r, d in result.adjustments
            ],
            final_multiplier=result.final_multiplier,
            tier=get_tier(result.final_multiplier),
            color=get_color(result.final_multiplier),
        )

    except Exception as e:
        logger.error(f"Failed to calculate quality multiplier: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate: {e}"
        )
