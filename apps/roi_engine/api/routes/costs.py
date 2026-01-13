"""
Costs Routes - Cost tracking and billing endpoints.

Cost & Billing Endpoints (Phase 5A):
- GET /costs/daily - Get daily cost breakdown for a period
- GET /costs/billing - Get billing summary with breakdowns by model/agent/date

Cost Analysis Endpoints (Phase 5E):
- GET /costs/hourly - Get hourly cost breakdown
- GET /costs/by-model - Get costs grouped by model used
- GET /costs/by-agent - Get costs grouped by agent type
- GET /costs/errors - Get error rate and associated costs
- GET /costs/forecast - Get cost forecast based on historical data

Cost Avoidance Endpoints (Phase 5E):
- GET /costs/avoidance/summary - Get total cost avoided by using AI vs humans
- GET /costs/avoidance/by-role - Get cost avoidance breakdown by squad role
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

from core import (
    ArtifactConsumer,
    get_langfuse_client,
    load_squad_config,
    ROLE_DESCRIPTIONS,
    TraceFilter,
    valuate_artifacts,
)
from api.models import (
    # Phase 5A models
    BillingResponse,
    DailyCostListResponse,
    DailyCostResponse,
    # Phase 5E models
    CostByAgentListResponse,
    CostByAgentResponse,
    CostByModelListResponse,
    CostByModelResponse,
    CostForecastPoint,
    CostForecastResponse,
    ErrorCostResponse,
    HourlyCostListResponse,
    HourlyCostResponse,
    # Cost Avoidance models
    CostAvoidanceByRoleItem,
    CostAvoidanceByRoleResponse,
    CostAvoidanceSummaryResponse,
)


router = APIRouter(prefix="/costs", tags=["Costs"])


# =======================================================================
# Phase 5A: Costs & Billing
# =======================================================================


@router.get(
    "/daily",
    response_model=DailyCostListResponse,
    summary="Get daily costs",
    description="Get daily cost breakdown for a period",
)
async def get_daily_costs(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> DailyCostListResponse:
    """Get daily cost breakdown."""
    client = get_langfuse_client()
    project_id = Path(project_dir).name

    from_date = from_date or (datetime.now() - timedelta(days=30))
    to_date = to_date or datetime.now()

    daily_metrics = await client.get_daily_metrics(from_date, to_date, project_id=project_id)

    return DailyCostListResponse(
        daily_costs=[
            DailyCostResponse(
                date=m.date,
                trace_count=m.trace_count,
                total_tokens=m.total_tokens,
                input_tokens=m.input_tokens,
                output_tokens=m.output_tokens,
                total_cost=m.total_cost,
                avg_latency_ms=m.avg_latency_ms,
            )
            for m in daily_metrics
        ],
        total_cost=sum(m.total_cost for m in daily_metrics),
        period_start=from_date.strftime("%Y-%m-%d"),
        period_end=to_date.strftime("%Y-%m-%d"),
    )


@router.get(
    "/billing",
    response_model=BillingResponse,
    summary="Get billing summary",
    description="Get billing summary for a period",
)
async def get_billing_summary(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> BillingResponse:
    """Get billing summary."""
    client = get_langfuse_client()
    project_id = Path(project_dir).name

    from_date = from_date or (datetime.now() - timedelta(days=30))
    to_date = to_date or datetime.now()

    breakdown = await client.get_cost_breakdown(from_date, to_date, project_id=project_id)
    daily_metrics = await client.get_daily_metrics(from_date, to_date, project_id=project_id)

    total_tokens = sum(m.total_tokens for m in daily_metrics)
    trace_count = sum(m.trace_count for m in daily_metrics)

    return BillingResponse(
        period_start=from_date.strftime("%Y-%m-%d"),
        period_end=to_date.strftime("%Y-%m-%d"),
        total_cost=breakdown.total,
        total_tokens=total_tokens,
        trace_count=trace_count,
        by_model=breakdown.by_model,
        by_agent=breakdown.by_agent,
        by_date=breakdown.by_date,
    )


# =======================================================================
# Phase 5E: Cost Endpoints (hourly, by-model, by-agent, errors, forecast)
# =======================================================================


@router.get(
    "/hourly",
    response_model=HourlyCostListResponse,
    summary="Get hourly costs",
    description="Get hourly cost breakdown for a period",
)
async def get_hourly_costs(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> HourlyCostListResponse:
    """Get hourly cost breakdown."""
    client = get_langfuse_client()
    project_id = Path(project_dir).name

    from_date = from_date or (datetime.now() - timedelta(days=7))
    to_date = to_date or datetime.now()

    # Get traces for the period (filtered by project)
    filter = TraceFilter(
        from_timestamp=from_date,
        to_timestamp=to_date,
        user_id=project_id,
        limit=10000,
    )
    traces = await client.get_traces(filter)

    # Group by hour
    hourly_data: dict[str, dict] = {}
    for trace in traces:
        hour_key = trace.timestamp.strftime("%Y-%m-%dT%H")
        if hour_key not in hourly_data:
            hourly_data[hour_key] = {
                "trace_count": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
            }
        hourly_data[hour_key]["trace_count"] += 1
        hourly_data[hour_key]["total_tokens"] += trace.total_tokens
        hourly_data[hour_key]["total_cost"] += trace.total_cost

    hourly_costs = [
        HourlyCostResponse(
            hour=hour,
            trace_count=data["trace_count"],
            total_tokens=data["total_tokens"],
            total_cost=data["total_cost"],
        )
        for hour, data in sorted(hourly_data.items())
    ]

    return HourlyCostListResponse(
        hourly_costs=hourly_costs,
        total_cost=sum(h.total_cost for h in hourly_costs),
        period_start=from_date.strftime("%Y-%m-%dT%H:%M"),
        period_end=to_date.strftime("%Y-%m-%dT%H:%M"),
    )


@router.get(
    "/by-model",
    response_model=CostByModelListResponse,
    summary="Get costs by model",
    description="Get cost breakdown by model used",
)
async def get_costs_by_model(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> CostByModelListResponse:
    """Get costs grouped by model."""
    client = get_langfuse_client()
    project_id = Path(project_dir).name

    from_date = from_date or (datetime.now() - timedelta(days=30))
    to_date = to_date or datetime.now()

    breakdown = await client.get_cost_breakdown(from_date, to_date, project_id=project_id)

    # Get detailed breakdown per model from traces (filtered by project)
    filter = TraceFilter(
        from_timestamp=from_date,
        to_timestamp=to_date,
        user_id=project_id,
        limit=10000,
    )
    traces = await client.get_traces(filter)

    # Get generations for model info
    model_data: dict[str, dict] = {}
    for trace in traces:
        generations = await client.get_generations(trace.id)
        for gen in generations:
            model = gen.model or "unknown"
            if model not in model_data:
                model_data[model] = {
                    "trace_count": 0,
                    "total_tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_cost": 0.0,
                }
            model_data[model]["trace_count"] += 1
            model_data[model]["total_tokens"] += gen.total_tokens
            model_data[model]["input_tokens"] += gen.input_tokens
            model_data[model]["output_tokens"] += gen.output_tokens
            model_data[model]["total_cost"] += gen.cost

    total_cost = sum(d["total_cost"] for d in model_data.values())

    models = [
        CostByModelResponse(
            model=model,
            trace_count=data["trace_count"],
            total_tokens=data["total_tokens"],
            input_tokens=data["input_tokens"],
            output_tokens=data["output_tokens"],
            total_cost=data["total_cost"],
            percentage=(data["total_cost"] / total_cost * 100) if total_cost > 0 else 0,
        )
        for model, data in sorted(model_data.items(), key=lambda x: x[1]["total_cost"], reverse=True)
    ]

    return CostByModelListResponse(
        models=models,
        total_cost=total_cost,
        period_start=from_date.strftime("%Y-%m-%d"),
        period_end=to_date.strftime("%Y-%m-%d"),
    )


@router.get(
    "/by-agent",
    response_model=CostByAgentListResponse,
    summary="Get costs by agent",
    description="Get cost breakdown by agent type",
)
async def get_costs_by_agent(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> CostByAgentListResponse:
    """Get costs grouped by agent type."""
    client = get_langfuse_client()
    project_id = Path(project_dir).name

    from_date = from_date or (datetime.now() - timedelta(days=30))
    to_date = to_date or datetime.now()

    breakdown = await client.get_cost_breakdown(from_date, to_date, project_id=project_id)

    total_cost = breakdown.total
    agents = [
        CostByAgentResponse(
            agent_type=agent,
            trace_count=0,  # Would need trace-level data
            total_tokens=0,
            total_cost=cost,
            avg_cost_per_trace=0.0,
            percentage=(cost / total_cost * 100) if total_cost > 0 else 0,
        )
        for agent, cost in sorted(breakdown.by_agent.items(), key=lambda x: x[1], reverse=True)
    ]

    return CostByAgentListResponse(
        agents=agents,
        total_cost=total_cost,
        period_start=from_date.strftime("%Y-%m-%d"),
        period_end=to_date.strftime("%Y-%m-%d"),
    )


@router.get(
    "/errors",
    response_model=ErrorCostResponse,
    summary="Get error costs",
    description="Get error rate and associated costs",
)
async def get_error_costs(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> ErrorCostResponse:
    """Get error costs summary."""
    client = get_langfuse_client()
    project_id = Path(project_dir).name

    from_date = from_date or (datetime.now() - timedelta(days=30))
    to_date = to_date or datetime.now()

    # Get traces for the period (filtered by project)
    filter = TraceFilter(
        from_timestamp=from_date,
        to_timestamp=to_date,
        user_id=project_id,
        limit=10000,
    )
    traces = await client.get_traces(filter)

    total_traces = len(traces)
    error_count = 0
    error_cost = 0.0
    by_error_type: dict[str, int] = {}
    by_error_cost: dict[str, float] = {}

    for trace in traces:
        # Check for errors in trace metadata or tags
        has_error = False
        error_type = "unknown"

        if "error" in trace.tags or "failed" in trace.tags:
            has_error = True
            error_type = "trace_error"
        elif trace.metadata and trace.metadata.get("error"):
            has_error = True
            error_type = str(trace.metadata.get("error_type", "api_error"))

        if has_error:
            error_count += 1
            error_cost += trace.total_cost
            by_error_type[error_type] = by_error_type.get(error_type, 0) + 1
            by_error_cost[error_type] = by_error_cost.get(error_type, 0.0) + trace.total_cost

    error_rate = (error_count / total_traces * 100) if total_traces > 0 else 0

    return ErrorCostResponse(
        total_errors=error_count,
        total_error_cost=error_cost,
        error_rate=error_rate,
        by_error_type=by_error_type,
        by_error_cost=by_error_cost,
        period_start=from_date.strftime("%Y-%m-%d"),
        period_end=to_date.strftime("%Y-%m-%d"),
    )


@router.get(
    "/forecast",
    response_model=CostForecastResponse,
    summary="Get cost forecast",
    description="Get cost forecast based on historical data",
)
async def get_cost_forecast(
    project_dir: str = Query(..., description="Project directory path"),
    forecast_days: int = Query(14, ge=1, le=90, description="Days to forecast"),
    from_date: Optional[datetime] = Query(None, description="Historical data from date"),
    to_date: Optional[datetime] = Query(None, description="Historical data to date"),
) -> CostForecastResponse:
    """Get cost forecast."""
    client = get_langfuse_client()
    project_id = Path(project_dir).name

    # Use historical data from the past
    to_date = to_date or datetime.now()
    from_date = from_date or (to_date - timedelta(days=30))

    # Get historical daily costs (filtered by project)
    daily_metrics = await client.get_daily_metrics(from_date, to_date, project_id=project_id)

    # Calculate average daily cost
    costs = [m.total_cost for m in daily_metrics if m.total_cost > 0]
    if not costs:
        avg_daily_cost = 0.0
        std_dev = 0.0
    else:
        avg_daily_cost = sum(costs) / len(costs)
        variance = sum((c - avg_daily_cost) ** 2 for c in costs) / len(costs)
        std_dev = variance ** 0.5

    # Build forecast
    forecast = []

    # Include actuals first
    for m in daily_metrics:
        forecast.append(CostForecastPoint(
            date=m.date,
            forecasted_cost=m.total_cost,
            lower_bound=m.total_cost,
            upper_bound=m.total_cost,
            is_actual=True,
        ))

    # Add forecasted days
    forecast_start = to_date + timedelta(days=1)
    for i in range(forecast_days):
        forecast_date = forecast_start + timedelta(days=i)
        # Simple linear forecast with confidence interval
        uncertainty_factor = 1 + (i * 0.02)  # Increases uncertainty over time
        lower = max(0, avg_daily_cost - std_dev * uncertainty_factor)
        upper = avg_daily_cost + std_dev * uncertainty_factor

        forecast.append(CostForecastPoint(
            date=forecast_date.strftime("%Y-%m-%d"),
            forecasted_cost=avg_daily_cost,
            lower_bound=lower,
            upper_bound=upper,
            is_actual=False,
        ))

    total_forecasted = avg_daily_cost * forecast_days

    return CostForecastResponse(
        forecast=forecast,
        forecast_period_days=forecast_days,
        avg_daily_cost=avg_daily_cost,
        total_forecasted_cost=total_forecasted,
        confidence_level=0.8,
    )


# =======================================================================
# Phase 5E: Cost Avoidance Endpoints (summary, by-role)
# =======================================================================


@router.get(
    "/avoidance/summary",
    response_model=CostAvoidanceSummaryResponse,
    summary="Get cost avoidance summary",
    description="Get total cost avoided by using AI vs humans",
)
async def get_cost_avoidance_summary(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> CostAvoidanceSummaryResponse:
    """Get cost avoidance summary."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)
    client = get_langfuse_client()

    from_date = from_date or (datetime.now() - timedelta(days=30))
    to_date = to_date or datetime.now()

    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)

    # Calculate totals
    total_value = sum(a.calculated_value for a in valued_artifacts)
    total_hours = sum(a.estimated_hours for a in valued_artifacts)

    # Get token cost
    breakdown = await client.get_cost_breakdown(from_date, to_date)
    total_cost = breakdown.total

    cost_avoided = total_value - total_cost
    efficiency_ratio = total_value / total_cost if total_cost > 0 else 0

    # Calculate equivalent salary cost (assuming 40hr week, 52 weeks, with 30% overhead)
    equivalent_salary = total_hours * 125 * 1.3  # Senior rate with overhead

    return CostAvoidanceSummaryResponse(
        total_artifact_value=total_value,
        total_token_cost=total_cost,
        cost_avoided=cost_avoided,
        efficiency_ratio=efficiency_ratio,
        hours_saved=total_hours,
        equivalent_salary_cost=equivalent_salary,
        period_start=from_date.strftime("%Y-%m-%d"),
        period_end=to_date.strftime("%Y-%m-%d"),
    )


@router.get(
    "/avoidance/by-role",
    response_model=CostAvoidanceByRoleResponse,
    summary="Get cost avoidance by role",
    description="Get cost avoidance breakdown by squad role",
)
async def get_cost_avoidance_by_role(
    project_dir: str = Query(..., description="Project directory path"),
) -> CostAvoidanceByRoleResponse:
    """Get cost avoidance by role."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)

    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)

    # Group by role
    by_role_data: dict[str, dict] = {}
    for a in valued_artifacts:
        role = a.role.value
        if role not in by_role_data:
            by_role_data[role] = {
                "value": 0.0,
                "hours": 0.0,
                "hourly_rate": a.hourly_rate,
            }
        by_role_data[role]["value"] += a.calculated_value
        by_role_data[role]["hours"] += a.estimated_hours

    # Build response
    by_role = []
    total_human_cost = 0.0
    total_token_cost = 0.0  # Would need per-role token cost allocation

    for role, data in sorted(by_role_data.items(), key=lambda x: x[1]["value"], reverse=True):
        from core.models import Role
        try:
            role_enum = Role(role)
            role_desc = ROLE_DESCRIPTIONS.get(role_enum, "")
        except ValueError:
            role_desc = ""

        human_cost = data["hours"] * data["hourly_rate"]
        total_human_cost += human_cost

        by_role.append(CostAvoidanceByRoleItem(
            role=role,
            role_description=role_desc,
            artifact_value=data["value"],
            estimated_hours=data["hours"],
            hourly_rate=data["hourly_rate"],
            human_cost=human_cost,
            token_cost=0.0,  # Would need allocation
            cost_avoided=human_cost,  # Assuming full cost avoidance
        ))

    return CostAvoidanceByRoleResponse(
        by_role=by_role,
        total_human_cost=total_human_cost,
        total_token_cost=total_token_cost,
        total_cost_avoided=total_human_cost - total_token_cost,
    )
