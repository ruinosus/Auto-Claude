"""
ROI Routes - ROI calculation endpoints.

Endpoints:
- POST /roi/spec - Calculate ROI for a spec
- POST /roi/trace - Calculate ROI for a trace
- GET /roi/spec/{spec_id} - Get ROI for a spec
- GET /roi/summary/{spec_id} - Get ROI summary
- GET /roi/unified - Get unified ROI
- GET /roi/trends - Get ROI trends
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from core import (
    ArtifactConsumer,
    calculate_roi_for_spec,
    calculate_roi_for_trace,
    get_langfuse_client,
    load_squad_config,
    TraceFilter,
    valuate_artifacts,
)
from api.models import (
    ErrorResponse,
    ROIResponse,
    ROISummaryResponse,
    ROITrendPoint,
    ROITrendsResponse,
    SpecROIRequest,
    TraceROIRequest,
    UnifiedROIResponse,
)


router = APIRouter(prefix="/roi", tags=["ROI"])


@router.post(
    "/spec",
    response_model=ROIResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Calculate ROI for a spec",
    description="Calculate ROI for all artifacts in a spec",
)
async def calculate_spec_roi(request: SpecROIRequest) -> ROIResponse:
    """Calculate ROI for a spec."""
    try:
        project_dir = Path(request.project_dir)
        if not project_dir.exists():
            raise HTTPException(status_code=400, detail=f"Project directory not found: {request.project_dir}")

        squad_config = load_squad_config(project_dir=project_dir)
        result = calculate_roi_for_spec(
            spec_id=request.spec_id,
            project_dir=project_dir,
            token_cost=request.token_cost,
            squad_config=squad_config,
        )

        return ROIResponse(
            scope=result.scope,
            scope_id=result.scope_id,
            total_artifact_value=result.total_artifact_value,
            artifact_count=result.artifact_count,
            by_role=result.by_role,
            by_type=result.by_type,
            token_cost=result.token_cost,
            net_value=result.net_value,
            roi_percentage=result.roi_percentage,
            calculated_at=result.calculated_at,
            squad_config_id=result.squad_config_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/trace",
    response_model=ROIResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Calculate ROI for a trace",
    description="Calculate ROI for all artifacts in a Langfuse trace",
)
async def calculate_trace_roi(request: TraceROIRequest) -> ROIResponse:
    """Calculate ROI for a trace."""
    try:
        project_dir = Path(request.project_dir)
        if not project_dir.exists():
            raise HTTPException(status_code=400, detail=f"Project directory not found: {request.project_dir}")

        squad_config = load_squad_config(project_dir=project_dir)
        result = calculate_roi_for_trace(
            trace_id=request.trace_id,
            project_dir=project_dir,
            token_cost=request.token_cost,
            squad_config=squad_config,
        )

        return ROIResponse(
            scope=result.scope,
            scope_id=result.scope_id,
            total_artifact_value=result.total_artifact_value,
            artifact_count=result.artifact_count,
            by_role=result.by_role,
            by_type=result.by_type,
            token_cost=result.token_cost,
            net_value=result.net_value,
            roi_percentage=result.roi_percentage,
            calculated_at=result.calculated_at,
            squad_config_id=result.squad_config_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/spec/{spec_id}",
    response_model=ROIResponse,
    summary="Get ROI for a spec",
    description="Get cached or calculate ROI for a spec",
)
async def get_spec_roi(
    spec_id: str,
    project_dir: str = Query(..., description="Project directory path"),
    token_cost: float = Query(0.0, description="Token cost in USD"),
) -> ROIResponse:
    """Get ROI for a spec (convenience GET endpoint)."""
    request = SpecROIRequest(
        spec_id=spec_id,
        project_dir=project_dir,
        token_cost=token_cost,
    )
    return await calculate_spec_roi(request)


@router.get(
    "/summary/{spec_id}",
    response_model=ROISummaryResponse,
    summary="Get ROI summary for a spec",
    description="Get a simplified ROI summary for dashboard display",
)
async def get_spec_roi_summary(
    spec_id: str,
    project_dir: str = Query(..., description="Project directory path"),
    token_cost: float = Query(0.0, description="Token cost in USD"),
) -> ROISummaryResponse:
    """Get simplified ROI summary."""
    project_path = Path(project_dir)
    squad_config = load_squad_config(project_dir=project_path)
    result = calculate_roi_for_spec(
        spec_id=spec_id,
        project_dir=project_path,
        token_cost=token_cost,
        squad_config=squad_config,
    )

    # Find top contributors
    top_role = None
    top_role_value = 0.0
    for role, value in result.by_role.items():
        if value > top_role_value:
            top_role = role
            top_role_value = value

    top_type = None
    top_type_value = 0.0
    for artifact_type, value in result.by_type.items():
        if value > top_type_value:
            top_type = artifact_type
            top_type_value = value

    return ROISummaryResponse(
        total_value=result.total_artifact_value,
        total_cost=result.token_cost,
        net_value=result.net_value,
        roi_percentage=result.roi_percentage,
        artifact_count=result.artifact_count,
        top_role=top_role,
        top_role_value=top_role_value,
        top_artifact_type=top_type,
        top_artifact_type_value=top_type_value,
    )


@router.get(
    "/unified",
    response_model=UnifiedROIResponse,
    summary="Get unified ROI",
    description="Get unified ROI combining all specs and artifacts",
)
async def get_unified_roi(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> UnifiedROIResponse:
    """Get unified ROI across all specs."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)
    client = get_langfuse_client()

    # Extract project_id from project directory name for Langfuse filtering
    project_id = project_path.name

    # Get all artifacts
    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)

    # Get cost from Langfuse (filtered by project tag)
    from_dt = from_date or (datetime.now() - timedelta(days=30))
    to_dt = to_date or datetime.now()

    breakdown = await client.get_cost_breakdown(from_dt, to_dt, project_id=project_id)
    total_cost = breakdown.total

    # Fallback: if Langfuse has no cost data, sum from local ROI files
    if total_cost == 0:
        from core.publisher import list_local_roi_results
        local_roi_results = list_local_roi_results(project_path)
        total_cost = sum(r.get("token_cost", 0) for r in local_roi_results)

    # Calculate totals
    total_value = sum(a.calculated_value for a in valued_artifacts)
    net_value = total_value - total_cost
    roi_percentage = (net_value / total_cost * 100) if total_cost > 0 else 0

    # Group by role
    by_role: dict[str, float] = {}
    for a in valued_artifacts:
        role_key = a.role.value
        by_role[role_key] = by_role.get(role_key, 0.0) + a.calculated_value

    # Group by type
    by_type: dict[str, float] = {}
    for a in valued_artifacts:
        by_type[a.artifact_type] = by_type.get(a.artifact_type, 0.0) + a.calculated_value

    # Group by spec
    by_spec: dict[str, float] = {}
    for a in valued_artifacts:
        spec_id = a.spec_id or "unknown"
        by_spec[spec_id] = by_spec.get(spec_id, 0.0) + a.calculated_value

    # Get traces (filtered by user_id which is the project_id in Langfuse)
    trace_filter = TraceFilter(
        from_timestamp=from_dt,
        to_timestamp=to_dt,
        user_id=project_id,
        limit=1000,
    )
    traces = await client.get_traces(trace_filter)

    # Calculate total tokens from traces
    total_tokens = sum(t.total_tokens for t in traces)

    # Get input/output token breakdown from generations (sample first 100 traces)
    input_tokens = 0
    output_tokens = 0
    for trace in traces[:100]:
        generations = await client.get_generations(trace.id)
        for gen in generations:
            input_tokens += gen.input_tokens
            output_tokens += gen.output_tokens

    return UnifiedROIResponse(
        total_artifact_value=total_value,
        total_token_cost=total_cost,
        net_value=net_value,
        roi_percentage=roi_percentage,
        total_tokens=total_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        by_role=by_role,
        by_type=by_type,
        by_spec=by_spec,
        artifact_count=len(valued_artifacts),
        trace_count=len(traces),
        period_start=from_dt.strftime("%Y-%m-%d"),
        period_end=to_dt.strftime("%Y-%m-%d"),
        calculated_at=datetime.now(),
    )


@router.get(
    "/trends",
    response_model=ROITrendsResponse,
    summary="Get ROI trends",
    description="Get ROI trends over time",
)
async def get_roi_trends(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> ROITrendsResponse:
    """Get ROI trends over time."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)
    client = get_langfuse_client()

    # Extract project_id from project directory name for Langfuse filtering
    project_id = project_path.name

    from_dt = from_date or (datetime.now() - timedelta(days=30))
    to_dt = to_date or datetime.now()

    # Get daily cost metrics (filtered by project tag)
    daily_metrics = await client.get_daily_metrics(from_dt, to_dt, project_id=project_id)

    # Get all artifacts and group by date
    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)

    # Group artifacts by date
    artifacts_by_date: dict[str, list] = {}
    for a in valued_artifacts:
        if a.created_at:
            date_key = a.created_at.strftime("%Y-%m-%d")
            if date_key not in artifacts_by_date:
                artifacts_by_date[date_key] = []
            artifacts_by_date[date_key].append(a)

    # Build trends
    trends = []
    cost_by_date = {m.date: m.total_cost for m in daily_metrics}

    # Get all dates in range
    current_date = from_dt
    while current_date <= to_dt:
        date_key = current_date.strftime("%Y-%m-%d")

        artifacts_today = artifacts_by_date.get(date_key, [])
        value_today = sum(a.calculated_value for a in artifacts_today)
        cost_today = cost_by_date.get(date_key, 0.0)

        roi = ((value_today - cost_today) / cost_today * 100) if cost_today > 0 else 0

        trends.append(ROITrendPoint(
            date=date_key,
            roi_percentage=roi,
            artifact_value=value_today,
            token_cost=cost_today,
            artifact_count=len(artifacts_today),
        ))

        current_date += timedelta(days=1)

    # Calculate average ROI and trend direction
    roi_values = [t.roi_percentage for t in trends if t.roi_percentage != 0]
    avg_roi = sum(roi_values) / len(roi_values) if roi_values else 0

    # Determine trend direction
    trend_direction = "stable"
    if len(roi_values) >= 7:
        first_half = sum(roi_values[:len(roi_values)//2]) / (len(roi_values)//2)
        second_half = sum(roi_values[len(roi_values)//2:]) / (len(roi_values) - len(roi_values)//2)
        if second_half > first_half * 1.1:
            trend_direction = "up"
        elif second_half < first_half * 0.9:
            trend_direction = "down"

    return ROITrendsResponse(
        trends=trends,
        period_start=from_dt.strftime("%Y-%m-%d"),
        period_end=to_dt.strftime("%Y-%m-%d"),
        avg_roi=avg_roi,
        trend_direction=trend_direction,
    )
