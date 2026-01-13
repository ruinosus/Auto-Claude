"""
Forecasting Endpoints for ROI Engine.

Provides REST endpoints for forecasting future metrics based on historical data:
- /forecast/roi - Project future ROI based on historical trends
- /forecast/value - Project future artifact value production
- /forecast/artifacts - Project future artifact counts by type
- /forecast/compare - Compare previously forecasted values against actual results
- /forecast/scenarios - Run what-if scenarios to compare different conditions
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

from core import (
    ArtifactConsumer,
    get_langfuse_client,
    load_squad_config,
    valuate_artifacts,
)
from api.models import (
    ROIForecastPoint,
    ROIForecastResponse,
    ValueForecastPoint,
    ValueForecastResponse,
    ArtifactForecastPoint,
    ArtifactForecastResponse,
    ForecastComparisonPoint,
    ForecastComparisonResponse,
    ScenarioInput,
    ScenarioResult,
    ScenariosResponse,
)


router = APIRouter(prefix="/forecast", tags=["Forecasts"])


@router.get(
    "/roi",
    response_model=ROIForecastResponse,
    summary="Forecast ROI",
    description="Project future ROI based on historical data",
)
async def forecast_roi(
    project_dir: str = Query(..., description="Project directory path"),
    forecast_days: int = Query(14, ge=1, le=90, description="Days to forecast"),
    from_date: Optional[datetime] = Query(None, description="Historical data from date"),
    to_date: Optional[datetime] = Query(None, description="Historical data to date"),
) -> ROIForecastResponse:
    """Forecast ROI based on historical trends."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)
    client = get_langfuse_client()

    to_date = to_date or datetime.now()
    from_date = from_date or (to_date - timedelta(days=30))

    # Get historical data
    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)
    daily_metrics = await client.get_daily_metrics(from_date, to_date)

    # Group artifacts by date
    artifacts_by_date: dict[str, list] = {}
    for a in valued_artifacts:
        if a.created_at:
            date_key = a.created_at.strftime("%Y-%m-%d")
            if date_key not in artifacts_by_date:
                artifacts_by_date[date_key] = []
            artifacts_by_date[date_key].append(a)

    cost_by_date = {m.date: m.total_cost for m in daily_metrics}

    # Calculate historical daily ROI
    daily_roi_values = []
    forecast = []

    current_date = from_date
    while current_date <= to_date:
        date_key = current_date.strftime("%Y-%m-%d")
        artifacts_today = artifacts_by_date.get(date_key, [])
        value_today = sum(a.calculated_value for a in artifacts_today)
        cost_today = cost_by_date.get(date_key, 0.0)

        if cost_today > 0:
            roi_today = ((value_today - cost_today) / cost_today) * 100
        else:
            roi_today = 0 if value_today == 0 else 100

        daily_roi_values.append(roi_today)

        forecast.append(ROIForecastPoint(
            date=date_key,
            forecasted_roi=roi_today,
            forecasted_value=value_today,
            forecasted_cost=cost_today,
            lower_bound=roi_today,
            upper_bound=roi_today,
            is_actual=True,
        ))

        current_date += timedelta(days=1)

    # Calculate forecast parameters
    if daily_roi_values:
        avg_roi = sum(daily_roi_values) / len(daily_roi_values)
        variance = sum((r - avg_roi) ** 2 for r in daily_roi_values) / len(daily_roi_values)
        std_dev = variance ** 0.5
    else:
        avg_roi = 0.0
        std_dev = 0.0

    # Determine trend
    trend = "stable"
    if len(daily_roi_values) >= 7:
        first_half = daily_roi_values[:len(daily_roi_values)//2]
        second_half = daily_roi_values[len(daily_roi_values)//2:]
        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0
        if second_avg > first_avg * 1.1:
            trend = "up"
        elif second_avg < first_avg * 0.9:
            trend = "down"

    # Add forecasted days
    forecast_start = to_date + timedelta(days=1)
    for i in range(forecast_days):
        forecast_date = forecast_start + timedelta(days=i)
        uncertainty = 1 + (i * 0.03)  # Increases uncertainty
        lower = avg_roi - std_dev * uncertainty
        upper = avg_roi + std_dev * uncertainty

        forecast.append(ROIForecastPoint(
            date=forecast_date.strftime("%Y-%m-%d"),
            forecasted_roi=avg_roi,
            forecasted_value=0.0,
            forecasted_cost=0.0,
            lower_bound=lower,
            upper_bound=upper,
            is_actual=False,
        ))

    return ROIForecastResponse(
        forecast=forecast,
        forecast_period_days=forecast_days,
        avg_daily_roi=avg_roi,
        projected_total_roi=avg_roi,  # Average maintained
        confidence_level=0.8,
        trend=trend,
    )


@router.get(
    "/value",
    response_model=ValueForecastResponse,
    summary="Forecast value",
    description="Project future artifact value based on historical data",
)
async def forecast_value(
    project_dir: str = Query(..., description="Project directory path"),
    forecast_days: int = Query(14, ge=1, le=90, description="Days to forecast"),
    from_date: Optional[datetime] = Query(None, description="Historical data from date"),
    to_date: Optional[datetime] = Query(None, description="Historical data to date"),
) -> ValueForecastResponse:
    """Forecast artifact value production."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)

    to_date = to_date or datetime.now()
    from_date = from_date or (to_date - timedelta(days=30))

    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)

    # Group by date
    by_date: dict[str, dict] = {}
    for a in valued_artifacts:
        if a.created_at:
            date_key = a.created_at.strftime("%Y-%m-%d")
            if date_key not in by_date:
                by_date[date_key] = {"value": 0.0, "count": 0}
            by_date[date_key]["value"] += a.calculated_value
            by_date[date_key]["count"] += 1

    # Build historical forecast
    daily_values = []
    forecast = []

    current_date = from_date
    while current_date <= to_date:
        date_key = current_date.strftime("%Y-%m-%d")
        data = by_date.get(date_key, {"value": 0.0, "count": 0})

        daily_values.append(data["value"])

        forecast.append(ValueForecastPoint(
            date=date_key,
            forecasted_value=data["value"],
            forecasted_artifacts=data["count"],
            lower_bound=data["value"],
            upper_bound=data["value"],
            is_actual=True,
        ))

        current_date += timedelta(days=1)

    # Calculate forecast parameters
    if daily_values:
        avg_value = sum(daily_values) / len(daily_values)
        variance = sum((v - avg_value) ** 2 for v in daily_values) / len(daily_values)
        std_dev = variance ** 0.5
    else:
        avg_value = 0.0
        std_dev = 0.0

    # Add forecasted days
    forecast_start = to_date + timedelta(days=1)
    for i in range(forecast_days):
        forecast_date = forecast_start + timedelta(days=i)
        uncertainty = 1 + (i * 0.02)
        lower = max(0, avg_value - std_dev * uncertainty)
        upper = avg_value + std_dev * uncertainty

        forecast.append(ValueForecastPoint(
            date=forecast_date.strftime("%Y-%m-%d"),
            forecasted_value=avg_value,
            forecasted_artifacts=0,
            lower_bound=lower,
            upper_bound=upper,
            is_actual=False,
        ))

    total_forecasted = avg_value * forecast_days

    return ValueForecastResponse(
        forecast=forecast,
        forecast_period_days=forecast_days,
        avg_daily_value=avg_value,
        projected_total_value=total_forecasted,
        confidence_level=0.8,
    )


@router.get(
    "/artifacts",
    response_model=ArtifactForecastResponse,
    summary="Forecast artifacts",
    description="Project future artifact production based on historical data",
)
async def forecast_artifacts(
    project_dir: str = Query(..., description="Project directory path"),
    forecast_days: int = Query(14, ge=1, le=90, description="Days to forecast"),
    from_date: Optional[datetime] = Query(None, description="Historical data from date"),
    to_date: Optional[datetime] = Query(None, description="Historical data to date"),
) -> ArtifactForecastResponse:
    """Forecast artifact production."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)

    to_date = to_date or datetime.now()
    from_date = from_date or (to_date - timedelta(days=30))

    all_artifacts = consumer.get_all_artifacts(limit=10000)

    # Group by date
    by_date: dict[str, dict] = {}
    type_counts: dict[str, int] = {}

    for artifact in all_artifacts:
        created_at = artifact.get("created_at")
        if created_at:
            date_key = datetime.fromisoformat(created_at).strftime("%Y-%m-%d")
            artifact_type = artifact.get("type", "unknown")

            if date_key not in by_date:
                by_date[date_key] = {"count": 0, "by_type": {}}
            by_date[date_key]["count"] += 1
            by_date[date_key]["by_type"][artifact_type] = by_date[date_key]["by_type"].get(artifact_type, 0) + 1

            type_counts[artifact_type] = type_counts.get(artifact_type, 0) + 1

    # Build historical forecast
    daily_counts = []
    forecast = []

    current_date = from_date
    while current_date <= to_date:
        date_key = current_date.strftime("%Y-%m-%d")
        data = by_date.get(date_key, {"count": 0, "by_type": {}})

        daily_counts.append(data["count"])

        forecast.append(ArtifactForecastPoint(
            date=date_key,
            forecasted_count=data["count"],
            by_type=data["by_type"],
            lower_bound=data["count"],
            upper_bound=data["count"],
            is_actual=True,
        ))

        current_date += timedelta(days=1)

    # Calculate forecast parameters
    if daily_counts:
        avg_count = sum(daily_counts) / len(daily_counts)
        variance = sum((c - avg_count) ** 2 for c in daily_counts) / len(daily_counts)
        std_dev = variance ** 0.5
    else:
        avg_count = 0.0
        std_dev = 0.0

    # Top types
    top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_type_names = [t[0] for t in top_types]

    # Add forecasted days
    forecast_start = to_date + timedelta(days=1)
    for i in range(forecast_days):
        forecast_date = forecast_start + timedelta(days=i)
        uncertainty = 1 + (i * 0.02)
        lower = max(0, int(avg_count - std_dev * uncertainty))
        upper = int(avg_count + std_dev * uncertainty)

        forecast.append(ArtifactForecastPoint(
            date=forecast_date.strftime("%Y-%m-%d"),
            forecasted_count=int(avg_count),
            by_type={},
            lower_bound=lower,
            upper_bound=upper,
            is_actual=False,
        ))

    total_forecasted = int(avg_count * forecast_days)

    return ArtifactForecastResponse(
        forecast=forecast,
        forecast_period_days=forecast_days,
        avg_daily_artifacts=avg_count,
        projected_total_artifacts=total_forecasted,
        top_projected_types=top_type_names,
        confidence_level=0.8,
    )


@router.get(
    "/compare",
    response_model=ForecastComparisonResponse,
    summary="Compare forecast vs actual",
    description="Compare previously forecasted values against actual results",
)
async def compare_forecast(
    project_dir: str = Query(..., description="Project directory path"),
    metric: str = Query("value", description="Metric to compare: roi, cost, value, artifacts"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> ForecastComparisonResponse:
    """Compare forecast vs actual for a metric."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)
    client = get_langfuse_client()

    to_date = to_date or datetime.now()
    from_date = from_date or (to_date - timedelta(days=14))

    # Get historical data for the first half (to simulate forecast)
    mid_date = from_date + (to_date - from_date) / 2
    forecast_period = to_date - mid_date

    # Get actual data
    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)
    daily_metrics = await client.get_daily_metrics(from_date, to_date)

    # Group by date
    artifacts_by_date: dict[str, dict] = {}
    for a in valued_artifacts:
        if a.created_at:
            date_key = a.created_at.strftime("%Y-%m-%d")
            if date_key not in artifacts_by_date:
                artifacts_by_date[date_key] = {"value": 0.0, "count": 0}
            artifacts_by_date[date_key]["value"] += a.calculated_value
            artifacts_by_date[date_key]["count"] += 1

    cost_by_date = {m.date: m.total_cost for m in daily_metrics}

    # Calculate averages from first half (simulated forecast basis)
    first_half_values = []
    current_date = from_date
    while current_date < mid_date:
        date_key = current_date.strftime("%Y-%m-%d")
        data = artifacts_by_date.get(date_key, {"value": 0.0, "count": 0})
        cost = cost_by_date.get(date_key, 0.0)

        if metric == "value":
            first_half_values.append(data["value"])
        elif metric == "cost":
            first_half_values.append(cost)
        elif metric == "artifacts":
            first_half_values.append(data["count"])
        elif metric == "roi":
            roi = ((data["value"] - cost) / cost * 100) if cost > 0 else 0
            first_half_values.append(roi)

        current_date += timedelta(days=1)

    # Forecasted value (average of first half)
    forecasted_daily = sum(first_half_values) / len(first_half_values) if first_half_values else 0

    # Compare with second half (actual)
    comparisons = []
    total_forecasted = 0.0
    total_actual = 0.0
    errors = []

    current_date = mid_date
    while current_date <= to_date:
        date_key = current_date.strftime("%Y-%m-%d")
        data = artifacts_by_date.get(date_key, {"value": 0.0, "count": 0})
        cost = cost_by_date.get(date_key, 0.0)

        if metric == "value":
            actual = data["value"]
        elif metric == "cost":
            actual = cost
        elif metric == "artifacts":
            actual = data["count"]
        elif metric == "roi":
            actual = ((data["value"] - cost) / cost * 100) if cost > 0 else 0
        else:
            actual = 0

        variance = actual - forecasted_daily
        variance_pct = (variance / forecasted_daily * 100) if forecasted_daily != 0 else 0

        comparisons.append(ForecastComparisonPoint(
            date=date_key,
            forecasted=forecasted_daily,
            actual=actual,
            variance=variance,
            variance_pct=variance_pct,
        ))

        total_forecasted += forecasted_daily
        total_actual += actual
        errors.append(abs(variance_pct))

        current_date += timedelta(days=1)

    mean_abs_error = sum(abs(c.variance) for c in comparisons) / len(comparisons) if comparisons else 0
    mean_pct_error = sum(errors) / len(errors) if errors else 0
    accuracy = max(0, 100 - mean_pct_error)

    return ForecastComparisonResponse(
        metric=metric,
        comparisons=comparisons,
        total_forecasted=total_forecasted,
        total_actual=total_actual,
        mean_absolute_error=mean_abs_error,
        mean_percentage_error=mean_pct_error,
        forecast_accuracy=accuracy,
        period_start=from_date.strftime("%Y-%m-%d"),
        period_end=to_date.strftime("%Y-%m-%d"),
    )


@router.post(
    "/scenarios",
    response_model=ScenariosResponse,
    summary="Run what-if scenarios",
    description="Run what-if scenarios to compare different conditions",
)
async def run_scenarios(
    project_dir: str = Query(..., description="Project directory path"),
    scenarios: list[ScenarioInput] = [],
) -> ScenariosResponse:
    """Run what-if scenarios."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)
    client = get_langfuse_client()

    # Get current baseline data (last 30 days)
    to_date = datetime.now()
    from_date = to_date - timedelta(days=30)

    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)
    breakdown = await client.get_cost_breakdown(from_date, to_date)

    # Calculate baseline daily metrics
    total_value = sum(a.calculated_value for a in valued_artifacts)
    total_cost = breakdown.total
    artifact_count = len(valued_artifacts)
    days = 30

    daily_value = total_value / days if days > 0 else 0
    daily_cost = total_cost / days if days > 0 else 0
    daily_artifacts = artifact_count / days if days > 0 else 0

    # Create baseline result
    baseline_roi = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
    baseline = ScenarioResult(
        name="baseline",
        projected_roi=baseline_roi,
        projected_value=total_value,
        projected_cost=total_cost,
        projected_artifacts=artifact_count,
        vs_baseline_roi=0.0,
        vs_baseline_value=0.0,
        vs_baseline_cost=0.0,
    )

    # Run scenarios
    scenario_results = []
    best_roi = baseline_roi
    worst_roi = baseline_roi
    best_scenario = None
    worst_scenario = None

    # Default scenarios if none provided
    if not scenarios:
        scenarios = [
            ScenarioInput(name="cost_increase_20pct", token_cost_multiplier=1.2, days_to_project=30),
            ScenarioInput(name="cost_decrease_20pct", token_cost_multiplier=0.8, days_to_project=30),
            ScenarioInput(name="productivity_increase_30pct", artifact_rate_multiplier=1.3, days_to_project=30),
            ScenarioInput(name="quality_focus", quality_multiplier=1.2, artifact_rate_multiplier=0.9, days_to_project=30),
        ]

    for scenario in scenarios:
        projected_days = scenario.days_to_project

        # Apply multipliers
        projected_cost = daily_cost * scenario.token_cost_multiplier * projected_days
        projected_artifacts = int(daily_artifacts * scenario.artifact_rate_multiplier * projected_days)
        projected_value = daily_value * scenario.artifact_rate_multiplier * scenario.quality_multiplier * projected_days

        # Calculate ROI
        if projected_cost > 0:
            projected_roi = ((projected_value - projected_cost) / projected_cost) * 100
        else:
            projected_roi = 0 if projected_value == 0 else 100

        # Calculate vs baseline
        vs_roi = projected_roi - baseline_roi
        vs_value = ((projected_value - total_value) / total_value * 100) if total_value > 0 else 0
        vs_cost = ((projected_cost - total_cost) / total_cost * 100) if total_cost > 0 else 0

        result = ScenarioResult(
            name=scenario.name,
            projected_roi=projected_roi,
            projected_value=projected_value,
            projected_cost=projected_cost,
            projected_artifacts=projected_artifacts,
            vs_baseline_roi=vs_roi,
            vs_baseline_value=vs_value,
            vs_baseline_cost=vs_cost,
        )
        scenario_results.append(result)

        if projected_roi > best_roi:
            best_roi = projected_roi
            best_scenario = scenario.name
        if projected_roi < worst_roi:
            worst_roi = projected_roi
            worst_scenario = scenario.name

    # Generate recommendation
    recommendation = None
    if best_scenario and best_roi > baseline_roi * 1.1:
        recommendation = f"Consider '{best_scenario}' scenario for {((best_roi - baseline_roi) / baseline_roi * 100):.1f}% ROI improvement"

    return ScenariosResponse(
        baseline=baseline,
        scenarios=scenario_results,
        best_scenario=best_scenario,
        worst_scenario=worst_scenario,
        recommendation=recommendation,
    )
