"""
Forecast Pydantic models for the ROI Engine API.

Contains models for forecasting ROI, costs, value, and scenarios.
"""

from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════════
# Cost Forecast Models
# ═══════════════════════════════════════════════════════════════


class CostForecastPoint(BaseModel):
    """Single point in cost forecast."""

    date: str
    forecasted_cost: float = 0.0
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    is_actual: bool = False


class CostForecastResponse(BaseModel):
    """Cost forecast response."""

    forecast: list[CostForecastPoint]
    forecast_period_days: int
    avg_daily_cost: float = 0.0
    total_forecasted_cost: float = 0.0
    confidence_level: float = 0.8


# ═══════════════════════════════════════════════════════════════
# ROI Forecast Models
# ═══════════════════════════════════════════════════════════════


class ROIForecastPoint(BaseModel):
    """Single point in ROI forecast."""

    date: str
    forecasted_roi: float = 0.0
    forecasted_value: float = 0.0
    forecasted_cost: float = 0.0
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    is_actual: bool = False


class ROIForecastResponse(BaseModel):
    """ROI forecast response."""

    forecast: list[ROIForecastPoint]
    forecast_period_days: int
    avg_daily_roi: float = 0.0
    projected_total_roi: float = 0.0
    confidence_level: float = 0.8
    trend: str = "stable"  # "up", "down", "stable"


# ═══════════════════════════════════════════════════════════════
# Value Forecast Models
# ═══════════════════════════════════════════════════════════════


class ValueForecastPoint(BaseModel):
    """Single point in value forecast."""

    date: str
    forecasted_value: float = 0.0
    forecasted_artifacts: int = 0
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    is_actual: bool = False


class ValueForecastResponse(BaseModel):
    """Value forecast response."""

    forecast: list[ValueForecastPoint]
    forecast_period_days: int
    avg_daily_value: float = 0.0
    projected_total_value: float = 0.0
    confidence_level: float = 0.8


# ═══════════════════════════════════════════════════════════════
# Artifact Forecast Models
# ═══════════════════════════════════════════════════════════════


class ArtifactForecastPoint(BaseModel):
    """Single point in artifact production forecast."""

    date: str
    forecasted_count: int = 0
    by_type: dict[str, int] = {}
    lower_bound: int = 0
    upper_bound: int = 0
    is_actual: bool = False


class ArtifactForecastResponse(BaseModel):
    """Artifact production forecast response."""

    forecast: list[ArtifactForecastPoint]
    forecast_period_days: int
    avg_daily_artifacts: float = 0.0
    projected_total_artifacts: int = 0
    top_projected_types: list[str] = []
    confidence_level: float = 0.8


# ═══════════════════════════════════════════════════════════════
# Forecast Comparison Models
# ═══════════════════════════════════════════════════════════════


class ForecastComparisonPoint(BaseModel):
    """Single point comparing forecast vs actual."""

    date: str
    forecasted: float = 0.0
    actual: float = 0.0
    variance: float = 0.0  # actual - forecasted
    variance_pct: float = 0.0  # (actual - forecasted) / forecasted * 100


class ForecastComparisonResponse(BaseModel):
    """Compare forecast vs actual response."""

    metric: str  # "roi", "cost", "value", "artifacts"
    comparisons: list[ForecastComparisonPoint]
    total_forecasted: float = 0.0
    total_actual: float = 0.0
    mean_absolute_error: float = 0.0
    mean_percentage_error: float = 0.0
    forecast_accuracy: float = 0.0  # 100 - mean_percentage_error
    period_start: str
    period_end: str


# ═══════════════════════════════════════════════════════════════
# Scenario Models
# ═══════════════════════════════════════════════════════════════


class ScenarioInput(BaseModel):
    """Input parameters for a scenario."""

    name: str
    token_cost_multiplier: float = 1.0  # e.g., 1.5 = 50% more expensive
    artifact_rate_multiplier: float = 1.0  # e.g., 0.8 = 20% fewer artifacts
    quality_multiplier: float = 1.0  # e.g., 1.2 = 20% better quality
    days_to_project: int = 30


class ScenarioResult(BaseModel):
    """Result for a single scenario."""

    name: str
    projected_roi: float = 0.0
    projected_value: float = 0.0
    projected_cost: float = 0.0
    projected_artifacts: int = 0
    vs_baseline_roi: float = 0.0  # percentage difference from baseline
    vs_baseline_value: float = 0.0
    vs_baseline_cost: float = 0.0


class ScenariosResponse(BaseModel):
    """What-if scenarios response."""

    baseline: ScenarioResult
    scenarios: list[ScenarioResult]
    best_scenario: str | None = None
    worst_scenario: str | None = None
    recommendation: str | None = None
