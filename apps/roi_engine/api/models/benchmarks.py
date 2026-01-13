"""
Benchmark Pydantic models for the ROI Engine API.

Contains models for benchmarking and comparison metrics.
"""

from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════════
# Efficiency Benchmark Models
# ═══════════════════════════════════════════════════════════════


class BenchmarkEfficiencyResponse(BaseModel):
    """Benchmark efficiency metrics."""

    # Core efficiency metrics
    tokens_per_artifact: float = 0.0
    cost_per_artifact: float = 0.0
    cost_per_value_dollar: float = 0.0
    value_per_token: float = 0.0

    # Time-based efficiency
    artifacts_per_day: float = 0.0
    value_per_day: float = 0.0

    # Comparative metrics
    vs_industry_avg: dict[str, float] = {}  # percentage vs industry
    efficiency_rank: str = "unknown"  # "excellent", "good", "average", "below_average"

    # Period
    period_start: str
    period_end: str
    sample_size: int = 0


# ═══════════════════════════════════════════════════════════════
# Squad Benchmark Models
# ═══════════════════════════════════════════════════════════════


class SquadMemberConfig(BaseModel):
    """Configuration for a squad member."""

    role: str
    seniority: str
    hourly_rate: float = 0.0
    artifact_types: list[str] = []


class SquadBenchmarkResult(BaseModel):
    """Benchmark result for a squad configuration."""

    config_name: str
    total_hourly_cost: float = 0.0
    estimated_daily_value: float = 0.0
    estimated_roi: float = 0.0
    member_count: int = 0
    members: list[SquadMemberConfig] = []
    strengths: list[str] = []
    weaknesses: list[str] = []


class SquadBenchmarkResponse(BaseModel):
    """Compare squad configurations response."""

    current_squad: SquadBenchmarkResult
    alternative_squads: list[SquadBenchmarkResult]
    recommended_squad: str | None = None
    potential_roi_improvement: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Project Benchmark Models
# ═══════════════════════════════════════════════════════════════


class ProjectMetrics(BaseModel):
    """Metrics for a project."""

    project_id: str
    project_name: str
    total_artifacts: int = 0
    total_value: float = 0.0
    total_cost: float = 0.0
    roi_percentage: float = 0.0
    avg_artifact_value: float = 0.0
    artifacts_per_day: float = 0.0
    top_artifact_types: list[str] = []
    period_days: int = 0


class ProjectBenchmarkResponse(BaseModel):
    """Compare projects response."""

    projects: list[ProjectMetrics]
    best_roi_project: str | None = None
    best_value_project: str | None = None
    most_productive_project: str | None = None
    overall_avg_roi: float = 0.0
    overall_avg_artifact_value: float = 0.0
