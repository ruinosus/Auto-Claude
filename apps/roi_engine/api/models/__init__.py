"""
ROI Engine API Models Package.

This package contains modular model files organized by domain:
- common.py: Health and error responses
- roi.py: ROI calculation models
- artifacts.py: Artifact CRUD and management models
- costs.py: Cost analysis and billing models
- quality.py: Quality scores and value breakdown models
- traces.py: Trace and session models
- benchmarks.py: Benchmarking models
- forecasts.py: Forecasting models
- time_saved.py: Time saved metrics models
- satisfaction.py: Satisfaction survey models
- migration.py: Migration models
- config.py: Configuration models
"""

# Common models
from .common import (
    ErrorResponse,
    HealthCheckResponse,
    HealthResponse,
)

# ROI models
from .roi import (
    ROIRequest,
    ROIResponse,
    ROISummaryResponse,
    ROITrendPoint,
    ROITrendsResponse,
    SpecROIRequest,
    TraceROIRequest,
    UnifiedROIResponse,
    ValueBreakdownItem,
    ValueBreakdownResponse,
)

# Artifact models
from .artifacts import (
    ArtifactListResponse,
    ArtifactSearchResponse,
    ArtifactSearchResult,
    ArtifactsByRoleItem,
    ArtifactsByRoleResponse,
    ArtifactStatisticsResponse,
    ArtifactTimelinePoint,
    ArtifactTimelineResponse,
    ArtifactTypesResponse,
    ArtifactValuePreviewRequest,
    ArtifactValuePreviewResponse,
    ArtifactValueResponse,
    CompleteArtifactResponse,
    ContinueArtifactRequest,
    ContinueArtifactResponse,
    DeleteArtifactResponse,
    DuplicateArtifactPair,
    DuplicatesResponse,
    LocalArtifactResponse,
    LocalArtifactsListResponse,
    MergeArtifactsRequest,
    MergeArtifactsResponse,
    UpdateContentRequest,
    UpdateContentResponse,
    UpdateQualityRequest,
    UpdateQualityResponse,
    UpdateStatusRequest,
    UpdateStatusResponse,
)

# Cost models
from .costs import (
    BillingResponse,
    CostAvoidanceByRoleItem,
    CostAvoidanceByRoleResponse,
    CostAvoidanceSummaryResponse,
    CostByAgentListResponse,
    CostByAgentResponse,
    CostByModelListResponse,
    CostByModelResponse,
    DailyCostListResponse,
    DailyCostResponse,
    ErrorCostResponse,
    HourlyCostListResponse,
    HourlyCostResponse,
)

# Quality models
from .quality import (
    QualityByAgentListResponse,
    QualityByAgentResponse,
    QualityScorePoint,
    QualityScoresResponse,
)

# Trace and session models
from .traces import (
    ActivityEvent,
    RecentActivityResponse,
    SessionListResponse,
    SessionResponse,
    TraceDetailResponse,
    TraceListResponse,
    TraceResponse,
)

# Benchmark models
from .benchmarks import (
    BenchmarkEfficiencyResponse,
    ProjectBenchmarkResponse,
    ProjectMetrics,
    SquadBenchmarkResponse,
    SquadBenchmarkResult,
    SquadMemberConfig,
)

# Forecast models
from .forecasts import (
    ArtifactForecastPoint,
    ArtifactForecastResponse,
    CostForecastPoint,
    CostForecastResponse,
    ForecastComparisonPoint,
    ForecastComparisonResponse,
    ROIForecastPoint,
    ROIForecastResponse,
    ScenarioInput,
    ScenarioResult,
    ScenariosResponse,
    ValueForecastPoint,
    ValueForecastResponse,
)

# Time saved models
from .time_saved import (
    TimeSavedBenchmark,
    TimeSavedBenchmarksResponse,
    TimeSavedByTaskListResponse,
    TimeSavedByTaskType,
    TimeSavedComparisonResponse,
    TimeSavedDashboardResponse,
    TimeSavedSummaryResponse,
    TimeSavedTrendPoint,
    TimeSavedTrendResponse,
)

# Satisfaction models
from .satisfaction import (
    FeedbackEntry,
    FeedbackListResponse,
    NPSResponse,
    SatisfactionMetrics,
    SatisfactionSurveyRequest,
    SatisfactionSurveyResponse,
    SurveyDeleteResponse,
    SurveyListResponse,
)

# Migration models
from .migration import (
    MigrationResponse,
    MigrationSummary,
    MigrationValueChange,
    MigrationValueSummary,
)

# Config models
from .config import RateTableResponse

# Metrics models
from .metrics import (
    ErrorBreakdown,
    ErrorMetricsResponse,
    HourlyMetric,
    HourlyMetricsResponse,
    RecentError,
)

__all__ = [
    # Common
    "ErrorResponse",
    "HealthCheckResponse",
    "HealthResponse",
    # ROI
    "ROIRequest",
    "ROIResponse",
    "ROISummaryResponse",
    "ROITrendPoint",
    "ROITrendsResponse",
    "SpecROIRequest",
    "TraceROIRequest",
    "UnifiedROIResponse",
    "ValueBreakdownItem",
    "ValueBreakdownResponse",
    # Artifacts
    "ArtifactForecastPoint",
    "ArtifactForecastResponse",
    "ArtifactListResponse",
    "ArtifactSearchResponse",
    "ArtifactSearchResult",
    "ArtifactsByRoleItem",
    "ArtifactsByRoleResponse",
    "ArtifactStatisticsResponse",
    "ArtifactTimelinePoint",
    "ArtifactTimelineResponse",
    "ArtifactTypesResponse",
    "ArtifactValuePreviewRequest",
    "ArtifactValuePreviewResponse",
    "ArtifactValueResponse",
    "CompleteArtifactResponse",
    "ContinueArtifactRequest",
    "ContinueArtifactResponse",
    "DeleteArtifactResponse",
    "DuplicateArtifactPair",
    "DuplicatesResponse",
    "LocalArtifactResponse",
    "LocalArtifactsListResponse",
    "MergeArtifactsRequest",
    "MergeArtifactsResponse",
    "UpdateContentRequest",
    "UpdateContentResponse",
    "UpdateQualityRequest",
    "UpdateQualityResponse",
    "UpdateStatusRequest",
    "UpdateStatusResponse",
    # Costs
    "BillingResponse",
    "CostAvoidanceByRoleItem",
    "CostAvoidanceByRoleResponse",
    "CostAvoidanceSummaryResponse",
    "CostByAgentListResponse",
    "CostByAgentResponse",
    "CostByModelListResponse",
    "CostByModelResponse",
    "DailyCostListResponse",
    "DailyCostResponse",
    "ErrorCostResponse",
    "HourlyCostListResponse",
    "HourlyCostResponse",
    # Quality
    "QualityByAgentListResponse",
    "QualityByAgentResponse",
    "QualityScorePoint",
    "QualityScoresResponse",
    # Traces
    "ActivityEvent",
    "RecentActivityResponse",
    "SessionListResponse",
    "SessionResponse",
    "TraceDetailResponse",
    "TraceListResponse",
    "TraceResponse",
    # Benchmarks
    "BenchmarkEfficiencyResponse",
    "ProjectBenchmarkResponse",
    "ProjectMetrics",
    "SquadBenchmarkResponse",
    "SquadBenchmarkResult",
    "SquadMemberConfig",
    # Forecasts
    "CostForecastPoint",
    "CostForecastResponse",
    "ForecastComparisonPoint",
    "ForecastComparisonResponse",
    "ROIForecastPoint",
    "ROIForecastResponse",
    "ScenarioInput",
    "ScenarioResult",
    "ScenariosResponse",
    "ValueForecastPoint",
    "ValueForecastResponse",
    # Time Saved
    "TimeSavedBenchmark",
    "TimeSavedBenchmarksResponse",
    "TimeSavedByTaskListResponse",
    "TimeSavedByTaskType",
    "TimeSavedComparisonResponse",
    "TimeSavedDashboardResponse",
    "TimeSavedSummaryResponse",
    "TimeSavedTrendPoint",
    "TimeSavedTrendResponse",
    # Satisfaction
    "FeedbackEntry",
    "FeedbackListResponse",
    "NPSResponse",
    "SatisfactionMetrics",
    "SatisfactionSurveyRequest",
    "SatisfactionSurveyResponse",
    "SurveyDeleteResponse",
    "SurveyListResponse",
    # Migration
    "MigrationResponse",
    "MigrationSummary",
    "MigrationValueChange",
    "MigrationValueSummary",
    # Config
    "RateTableResponse",
    # Metrics
    "ErrorBreakdown",
    "ErrorMetricsResponse",
    "HourlyMetric",
    "HourlyMetricsResponse",
    "RecentError",
]
