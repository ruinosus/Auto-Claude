"""
Pydantic Models for Analytics API
==================================

Request and response models for the analytics API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# Health Status Models
# =============================================================================

class ServiceHealth(BaseModel):
    """Health status for a single service."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class HealthStatusResponse(BaseModel):
    """Response model for health status."""
    overall_status: str  # "healthy", "degraded", "unhealthy"
    services: List[ServiceHealth] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Trace Models
# =============================================================================

class TraceResponse(BaseModel):
    """Response model for a single trace."""
    id: str
    name: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    total_tokens: int = 0
    total_cost: float = 0.0
    latency_ms: float = 0.0
    generation_count: int = 0
    # Computed fields
    spec_id: Optional[str] = None
    agent_type: Optional[str] = None

    class Config:
        from_attributes = True


class TraceListResponse(BaseModel):
    """Response model for list of traces."""
    traces: List[TraceResponse]
    total: int
    limit: int
    offset: int


class TraceDetailResponse(TraceResponse):
    """Detailed trace response with input/output."""
    input: Optional[Any] = None
    output: Optional[Any] = None
    generations: List["GenerationResponse"] = Field(default_factory=list)
    scores: List["ScoreResponse"] = Field(default_factory=list)


# =============================================================================
# Generation Models
# =============================================================================

class GenerationResponse(BaseModel):
    """Response model for a generation (LLM call)."""
    id: str
    name: str
    model: str
    timestamp: datetime
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


# =============================================================================
# Score Models
# =============================================================================

class ScoreResponse(BaseModel):
    """Response model for a score."""
    id: str
    name: str
    value: float
    trace_id: str
    comment: Optional[str] = None
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# Session Models
# =============================================================================

class SessionSummary(BaseModel):
    """Summary of a spec's sessions."""
    spec_id: str
    session_count: int
    total_tokens: int
    total_cost: float
    agent_breakdown: Dict[str, int] = Field(default_factory=dict)
    latest_session: Optional[datetime] = None
    status: str = "unknown"  # planning, coding, qa_review, complete


class SessionListResponse(BaseModel):
    """Response model for sessions list."""
    spec_id: str
    sessions: List[TraceResponse]
    summary: SessionSummary


# =============================================================================
# ROI Models (Legacy - for backward compatibility)
# =============================================================================

class ROIMetrics(BaseModel):
    """ROI metrics for a spec or project."""
    roi_percentage: float = 0.0
    business_value_usd: float = 0.0
    actual_cost_usd: float = 0.0
    dev_hours_saved: float = 0.0
    lines_added: int = 0
    lines_removed: int = 0
    files_changed: int = 0
    qa_attempts: int = 0
    qa_passed: bool = False
    confidence_score: float = 0.0
    quality_multiplier: float = 1.0
    estimation_method: str = "hybrid"


class ROIResponse(BaseModel):
    """Response model for ROI data."""
    spec_id: str
    metrics: ROIMetrics
    trace_id: Optional[str] = None
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class ROISummaryResponse(BaseModel):
    """Aggregated ROI summary across specs."""
    total_roi_percentage: float = 0.0
    total_business_value_usd: float = 0.0
    total_actual_cost_usd: float = 0.0
    total_dev_hours_saved: float = 0.0
    spec_count: int = 0
    specs_with_positive_roi: int = 0
    average_confidence: float = 0.0
    by_spec: List[ROIResponse] = Field(default_factory=list)
    period: Optional[Dict[str, Optional[str]]] = None


# =============================================================================
# Unified ROI Models (New - supports all feature types)
# =============================================================================

class ValueBreakdown(BaseModel):
    """Breakdown of ROI value by type."""
    execution_value: float = 0.0  # Direct code work value
    decision_value: float = 0.0   # Strategic decisions, prioritization
    prevention_value: float = 0.0  # Bugs prevented, issues avoided
    knowledge_value: float = 0.0   # Documentation, insights gained


class FeatureROIMetrics(BaseModel):
    """ROI metrics for a specific feature type."""
    feature_type: str  # ideation_security, roadmap_features, etc.
    roi_percentage: float = 0.0
    total_value_usd: float = 0.0
    total_cost_usd: float = 0.0
    net_value_usd: float = 0.0
    confidence_score: float = 0.0
    value_breakdown: ValueBreakdown = Field(default_factory=ValueBreakdown)
    # Feature-specific metrics (varies by type)
    feature_metrics: Dict[str, Any] = Field(default_factory=dict)


class FeatureROIResponse(BaseModel):
    """Response model for a single feature ROI."""
    feature_type: str
    project_id: str
    metrics: FeatureROIMetrics
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UnifiedROISummary(BaseModel):
    """Aggregated unified ROI across all feature types."""
    # Overall metrics
    total_roi_percentage: float = 0.0
    total_value_usd: float = 0.0
    total_cost_usd: float = 0.0
    net_value_usd: float = 0.0

    # Value breakdown totals
    total_execution_value: float = 0.0
    total_decision_value: float = 0.0
    total_prevention_value: float = 0.0
    total_knowledge_value: float = 0.0

    # Counts
    total_traces: int = 0
    positive_roi_count: int = 0
    average_confidence: float = 0.0

    # Breakdown by feature type
    by_feature_type: Dict[str, FeatureROIMetrics] = Field(default_factory=dict)

    # Breakdown by value type (for pie chart)
    value_distribution: ValueBreakdown = Field(default_factory=ValueBreakdown)

    # Period info
    period: Optional[Dict[str, Optional[str]]] = None


class UnifiedROIResponse(BaseModel):
    """Complete unified ROI response."""
    summary: UnifiedROISummary
    features: List[FeatureROIResponse] = Field(default_factory=list)
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Cost Models
# =============================================================================

class AgentCost(BaseModel):
    """Cost breakdown for an agent type."""
    agent_type: str
    cost: float
    tokens: int
    trace_count: int


class CostSummaryResponse(BaseModel):
    """Cost summary response."""
    total_cost: float
    total_tokens: int
    generation_count: int
    trace_count: int
    by_agent_type: List[AgentCost] = Field(default_factory=list)
    period: Dict[str, str]


# =============================================================================
# Usage Summary Models (for charts)
# =============================================================================

class CostOverTimePoint(BaseModel):
    """Single point for cost over time chart."""
    date: str  # ISO date string (YYYY-MM-DD)
    cost: float
    tokens: int
    trace_count: int


class TokensBySpec(BaseModel):
    """Token breakdown by spec."""
    spec_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float


class ModelUsage(BaseModel):
    """Model usage statistics."""
    model: str
    tokens: int
    cost: float
    generation_count: int
    percentage: float = 0.0


class PhaseDuration(BaseModel):
    """Duration by phase."""
    phase: str
    avg_duration_ms: float
    total_duration_ms: float
    trace_count: int


class FeatureUsage(BaseModel):
    """Feature usage statistics."""
    feature: str  # agent_type or feature name
    tokens: int
    cost: float
    trace_count: int
    percentage: float = 0.0


class UsageSummaryResponse(BaseModel):
    """
    Comprehensive usage analytics for dashboard charts.

    Provides pre-aggregated data for:
    - Cost Over Time chart
    - Tokens By Spec chart
    - Model Distribution chart
    - Session Duration by Phase chart
    - Feature Usage breakdown
    """
    # Overview metrics
    total_cost: float = 0.0
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_traces: int = 0
    active_specs: int = 0

    # Chart data
    cost_over_time: List[CostOverTimePoint] = Field(default_factory=list)
    tokens_by_spec: List[TokensBySpec] = Field(default_factory=list)
    model_distribution: List[ModelUsage] = Field(default_factory=list)
    duration_by_phase: List[PhaseDuration] = Field(default_factory=list)
    feature_usage: List[FeatureUsage] = Field(default_factory=list)

    # Period info
    period: Optional[Dict[str, Optional[str]]] = None


# =============================================================================
# Daily Metrics Models
# =============================================================================

class DailyMetricResponse(BaseModel):
    """Daily metric data point."""
    date: str  # ISO date (YYYY-MM-DD)
    cost_usd: float
    traces: int
    input_tokens: int = 0
    output_tokens: int = 0
    observations: int = 0


class DailyMetricsListResponse(BaseModel):
    """Response for list of daily metrics."""
    metrics: List[DailyMetricResponse]
    total_cost: float
    total_traces: int
    total_tokens: int
    period: Dict[str, Optional[str]]


class BillingExportResponse(BaseModel):
    """Billing export data."""
    data: List[DailyMetricResponse]
    summary: Dict[str, Any]
    period: Dict[str, Optional[str]]
    export_format: str = "json"


# =============================================================================
# Hourly Metrics Models
# =============================================================================

class HourlyMetric(BaseModel):
    """Metrics for a single hour."""
    hour: str  # ISO format "2024-01-15T14:00:00"
    requests: int = 0
    tokens: int = 0
    cost: float = 0.0
    errors: int = 0


class HourlyMetricsResponse(BaseModel):
    """Response for hourly metrics."""
    metrics: List[HourlyMetric] = Field(default_factory=list)
    period_hours: int = 24


# =============================================================================
# Error Metrics Models
# =============================================================================

class ErrorBreakdown(BaseModel):
    """Breakdown of errors by type."""
    error_type: str
    count: int = 0
    percentage: float = 0.0
    last_occurrence: Optional[datetime] = None


class ErrorMetricsResponse(BaseModel):
    """Response for error metrics."""
    total_errors: int = 0
    error_rate: float = 0.0  # percentage of traces with errors
    breakdown: List[ErrorBreakdown] = Field(default_factory=list)
    recent_errors: List[Dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# Activity Models
# =============================================================================

class ActivityEvent(BaseModel):
    """Single activity event."""
    spec_id: str
    event_type: str  # "completed", "started", "qa_passed", "qa_failed"
    timestamp: datetime
    agent_type: Optional[str] = None
    details: Optional[str] = None


class RecentActivityResponse(BaseModel):
    """Response for recent activity."""
    events: List[ActivityEvent] = Field(default_factory=list)
    total: int = 0


# =============================================================================
# Query Parameters
# =============================================================================

class TraceQueryParams(BaseModel):
    """Query parameters for trace listing."""
    spec_id: Optional[str] = None
    agent_type: Optional[str] = None
    tags: Optional[List[str]] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class DateRangeParams(BaseModel):
    """Date range query parameters."""
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


# =============================================================================
# Rich Artifact Models
# =============================================================================


class ArtifactMetadataModel(BaseModel):
    """Rich metadata for artifacts."""
    title: Optional[str] = None
    priority: Optional[str] = None  # must, should, could, wont
    complexity: Optional[str] = None  # low, medium, high, very_high
    impact: Optional[str] = None  # low, medium, high
    status: Optional[str] = None
    phase: Optional[str] = None
    phase_id: Optional[str] = None
    feature_id: Optional[str] = None
    feature_name: Optional[str] = None
    feature_index: Optional[int] = None
    has_acceptance_criteria: bool = False
    has_user_stories: bool = False
    has_rationale: bool = False
    dependency_count: int = 0
    ideation_type: Optional[str] = None
    # Allow extra fields
    extra: Dict[str, Any] = Field(default_factory=dict)


class RichArtifactResponse(BaseModel):
    """Enhanced artifact with all rich fields."""
    id: str
    type: str
    format: str
    content: str
    value_usd: float = 0.0
    description: Optional[str] = None
    tab: Optional[str] = None
    created_at: str
    trace_id: Optional[str] = None
    spec_id: Optional[str] = None
    project_id: Optional[str] = None
    agent_type: Optional[str] = None
    session_num: Optional[int] = None
    metadata: ArtifactMetadataModel = Field(default_factory=ArtifactMetadataModel)
    # Extracted rich content (parsed from markdown content)
    rationale: Optional[str] = None
    acceptance_criteria: List[str] = Field(default_factory=list)
    user_stories: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)


class ArtifactQualityMetrics(BaseModel):
    """Quality metrics for artifacts."""
    with_rationale: int = 0
    with_acceptance_criteria: int = 0
    with_user_stories: int = 0
    with_dependencies: int = 0
    total_with_quality: int = 0  # artifacts with at least one quality field
    quality_percentage: float = 0.0  # percentage with at least one quality field


class ArtifactStatistics(BaseModel):
    """Aggregate statistics for artifacts."""
    total_count: int = 0
    total_value_usd: float = 0.0
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_agent: Dict[str, int] = Field(default_factory=dict)
    by_priority: Dict[str, int] = Field(default_factory=dict)
    by_tab: Dict[str, int] = Field(default_factory=dict)
    quality_metrics: ArtifactQualityMetrics = Field(default_factory=ArtifactQualityMetrics)
    avg_value_per_artifact: float = 0.0
    # Value distribution
    value_by_type: Dict[str, float] = Field(default_factory=dict)
    value_by_priority: Dict[str, float] = Field(default_factory=dict)


class ArtifactTimelineEntry(BaseModel):
    """Single entry for artifact timeline."""
    date: str  # ISO date string (YYYY-MM-DD or YYYY-MM-DD HH:00)
    count: int = 0
    value_usd: float = 0.0
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_agent: Dict[str, int] = Field(default_factory=dict)


class ArtifactTimelineResponse(BaseModel):
    """Response for artifact timeline."""
    timeline: List[ArtifactTimelineEntry] = Field(default_factory=list)
    granularity: str = "day"  # hour, day, week
    total_count: int = 0
    total_value: float = 0.0


class LocalArtifactsResponse(BaseModel):
    """Response for local artifacts listing."""
    artifacts: List[RichArtifactResponse] = Field(default_factory=list)
    total: int = 0
    limit: int = 100
    offset: int = 0
    # Statistics for the filtered results
    stats: Optional[ArtifactStatistics] = None


# =============================================================================
# Satisfaction Survey Models
# =============================================================================


class SatisfactionSurveyRequest(BaseModel):
    """Request model for submitting a satisfaction survey."""
    spec_id: str = Field(..., description="The spec ID this survey is for")
    user_id: str = Field(..., description="The user submitting the survey")

    # Scale 1-5
    overall_satisfaction: int = Field(..., ge=1, le=5, description="Overall satisfaction (1-5)")
    output_quality: int = Field(..., ge=1, le=5, description="Output quality rating (1-5)")
    time_saved_perception: int = Field(..., ge=1, le=5, description="Time saved perception (1-5)")
    would_recommend: int = Field(..., ge=1, le=5, description="Would recommend score (1-5, used for NPS)")

    # Optional free text
    feedback: Optional[str] = Field(None, max_length=2000, description="Optional feedback text")
    improvement_suggestions: Optional[str] = Field(None, max_length=2000, description="Optional improvement suggestions")


class SatisfactionSurveyResponse(BaseModel):
    """Response model for a satisfaction survey."""
    id: str
    spec_id: str
    user_id: str
    timestamp: datetime
    overall_satisfaction: int
    output_quality: int
    time_saved_perception: int
    would_recommend: int
    feedback: Optional[str] = None
    improvement_suggestions: Optional[str] = None
    project_id: Optional[str] = None


class SatisfactionMetricsResponse(BaseModel):
    """Response model for aggregated satisfaction metrics."""
    nps_score: float = Field(..., description="Net Promoter Score (-100 to 100)")
    avg_satisfaction: float = Field(..., description="Average overall satisfaction (1-5)")
    avg_output_quality: float = Field(..., description="Average output quality (1-5)")
    avg_time_saved: float = Field(..., description="Average time saved perception (1-5)")
    satisfaction_trend: float = Field(..., description="Change vs previous period (percentage points)")
    response_count: int = Field(..., description="Total number of responses")
    promoters_count: int = Field(..., description="Number of promoters (would_recommend >= 4)")
    passives_count: int = Field(..., description="Number of passives (would_recommend == 3)")
    detractors_count: int = Field(..., description="Number of detractors (would_recommend <= 2)")
    top_feedback_themes: List[str] = Field(default_factory=list, description="Top feedback themes")
    period_days: int = Field(default=30, description="Period in days")
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class NPSResponse(BaseModel):
    """Response model for NPS score."""
    nps_score: float = Field(..., description="Net Promoter Score (-100 to 100)")
    response_count: int = Field(..., description="Number of responses used in calculation")
    promoters_count: int = Field(..., description="Number of promoters")
    passives_count: int = Field(..., description="Number of passives")
    detractors_count: int = Field(..., description="Number of detractors")
    period_days: int = Field(default=30)


class FeedbackEntryResponse(BaseModel):
    """Response model for a single feedback entry."""
    id: str
    spec_id: str
    timestamp: Optional[str] = None
    overall_satisfaction: int
    would_recommend: int
    feedback: Optional[str] = None
    improvement_suggestions: Optional[str] = None


class FeedbackListResponse(BaseModel):
    """Response model for a list of feedback entries."""
    feedback: List[FeedbackEntryResponse] = Field(default_factory=list)
    total: int = 0
    period_days: int = 30


class SurveySubmitResponse(BaseModel):
    """Response model for survey submission."""
    success: bool
    survey_id: str
    message: str = "Survey submitted successfully"


# =============================================================================
# Time Saved Models
# =============================================================================


class TaskBenchmarkResponse(BaseModel):
    """Response model for a single task benchmark."""
    task_type: str
    avg_time_without_ai_seconds: float
    actual_time_with_ai_seconds: float
    time_saved_seconds: float
    percentage_saved: float
    complexity: str = "medium"
    created_at: Optional[datetime] = None


class TimeSavedSummaryResponse(BaseModel):
    """Summary of time saved across tasks."""
    total_time_saved_seconds: float = 0.0
    total_time_saved_hours: float = 0.0
    total_benchmark_seconds: float = 0.0
    total_benchmark_hours: float = 0.0
    total_actual_seconds: float = 0.0
    total_actual_hours: float = 0.0
    average_percentage_saved: float = 0.0
    task_count: int = 0
    by_task_type: Dict[str, Any] = Field(default_factory=dict)
    period: Optional[Dict[str, Optional[str]]] = None


class TimeSavedByTaskResponse(BaseModel):
    """Time saved breakdown by task type."""
    task_type: str
    count: int = 0
    total_saved_hours: float = 0.0
    total_benchmark_hours: float = 0.0
    total_actual_hours: float = 0.0
    percentage_saved: float = 0.0


class TimeSavedByTaskListResponse(BaseModel):
    """List of time saved by task type."""
    breakdown: List[TimeSavedByTaskResponse] = Field(default_factory=list)
    total_time_saved_hours: float = 0.0
    total_benchmark_hours: float = 0.0
    period: Optional[Dict[str, Optional[str]]] = None


class TimeSavedTrendPoint(BaseModel):
    """Single point in time saved trend."""
    date: str
    time_saved_hours: float = 0.0
    benchmark_hours: float = 0.0
    actual_hours: float = 0.0
    percentage_saved: float = 0.0
    task_count: int = 0


class TimeSavedTrendResponse(BaseModel):
    """Time saved trend over time."""
    trend: List[TimeSavedTrendPoint] = Field(default_factory=list)
    granularity: str = "day"  # hour, day, week
    total_time_saved_hours: float = 0.0
    period: Optional[Dict[str, Optional[str]]] = None


class TimeSavedComparisonResponse(BaseModel):
    """Comparison of time with AI vs without AI."""
    task_type: str
    with_ai_hours: float
    without_ai_hours: float
    time_saved_hours: float
    percentage_saved: float
    complexity: str = "medium"


class TimeSavedDashboardResponse(BaseModel):
    """Complete dashboard data for time saved visualization."""
    summary: TimeSavedSummaryResponse
    by_task_type: List[TimeSavedByTaskResponse] = Field(default_factory=list)
    trend: List[TimeSavedTrendPoint] = Field(default_factory=list)
    comparisons: List[TimeSavedComparisonResponse] = Field(default_factory=list)
    # Animated clock data
    total_hours_saved: float = 0.0
    equivalent_work_days: float = 0.0
    equivalent_work_weeks: float = 0.0
    period: Optional[Dict[str, Optional[str]]] = None


# =============================================================================
# Impact Forecast Models
# =============================================================================


class ForecastPredictRequest(BaseModel):
    """Request model for predicting spec ROI."""
    spec_id: str = Field(..., description="Unique identifier for the spec")
    spec_complexity: str = Field(
        default="standard",
        description="Complexity level: simple, standard, or complex"
    )
    estimated_lines: int = Field(
        default=200,
        ge=1,
        description="Estimated lines of code to be changed"
    )
    feature_type: str = Field(
        default="feature",
        description="Type: bugfix, feature, refactor, test, documentation, security, performance"
    )
    historical_similar: List[str] = Field(
        default_factory=list,
        description="List of similar spec IDs for adjustment"
    )


class ImpactForecastResponse(BaseModel):
    """Predicted impact metrics for a spec."""
    spec_id: str
    predicted_value_usd: float
    predicted_cost_usd: float
    predicted_roi: float
    confidence_interval: List[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="95% confidence interval [low, high]"
    )
    prediction_factors: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ForecastComparisonResponse(BaseModel):
    """Comparison between predicted and actual ROI."""
    spec_id: str
    predicted_roi: float
    actual_roi: float
    predicted_value_usd: float
    actual_value_usd: float
    predicted_cost_usd: float
    actual_cost_usd: float
    accuracy_percentage: float = Field(
        ...,
        description="How close the prediction was (100 = perfect)"
    )
    prediction_error: float = Field(
        ...,
        description="Signed error (positive = overestimated)"
    )
    within_confidence: bool = Field(
        ...,
        description="Whether actual ROI was within confidence interval"
    )


class ModelAccuracyResponse(BaseModel):
    """Overall model accuracy statistics."""
    total_predictions: int = 0
    mean_accuracy: float = Field(
        default=0.0,
        description="Average accuracy percentage"
    )
    mean_absolute_error: float = Field(
        default=0.0,
        description="Mean absolute ROI error"
    )
    root_mean_square_error: float = Field(
        default=0.0,
        description="RMSE for ROI predictions"
    )
    within_confidence_rate: float = Field(
        default=0.0,
        description="Percentage of predictions within confidence interval"
    )
    bias: float = Field(
        default=0.0,
        description="Average signed error (positive = tends to overestimate)"
    )
    recent_accuracy: float = Field(
        default=0.0,
        description="Accuracy of last 10 predictions"
    )


class ForecastHistoryEntry(BaseModel):
    """Single entry in forecast history."""
    spec_id: str
    predicted_roi: float
    actual_roi: float
    error: float
    within_ci: bool
    created_at: str


class ForecastHistoryResponse(BaseModel):
    """Response for forecast history listing."""
    history: List[ForecastHistoryEntry] = Field(default_factory=list)
    total: int = 0


class RecordActualRequest(BaseModel):
    """Request to record actual ROI for comparison."""
    spec_id: str
    actual_roi: float
    actual_value_usd: float = 0.0
    actual_cost_usd: float = 0.0


# =============================================================================
# ROI Comparison Models
# =============================================================================


class ROIComparisonResult(BaseModel):
    """ROI comparison result for a project against market benchmarks."""
    project_id: str
    roi_percentage: float = 0.0
    cost_per_dollar_value: float = 0.0  # $1 cost -> $X value
    break_even_days: Optional[int] = None
    vs_market_avg: float = 0.0  # % above/below market average
    percentile: int = 50  # Top X% (1 = top 1%, 100 = bottom)
    market_position: str = "average"  # top_performer, above_average, average, below_average
    total_value_usd: float = 0.0
    total_cost_usd: float = 0.0
    net_value_usd: float = 0.0
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class MarketBenchmarks(BaseModel):
    """Market benchmark reference data."""
    average_roi: float = 370.0  # Forrester study
    top_performers_roi: float = 1030.0  # Top 10% performers
    median_roi: float = 250.0
    low_performers_roi: float = 100.0
    median_time_saved_percent: float = 26.0


class PercentileThreshold(BaseModel):
    """ROI threshold for a percentile bracket."""
    min_roi: float
    label: str


class ROIComparisonResponse(BaseModel):
    """Response for single project ROI comparison."""
    comparison: ROIComparisonResult
    benchmarks: MarketBenchmarks = Field(default_factory=MarketBenchmarks)
    percentile_thresholds: Dict[str, PercentileThreshold] = Field(default_factory=dict)


class MultiProjectComparisonResponse(BaseModel):
    """Response for comparing multiple projects."""
    comparisons: List[ROIComparisonResult] = Field(default_factory=list)
    benchmarks: MarketBenchmarks = Field(default_factory=MarketBenchmarks)
    best_performer: Optional[str] = None  # project_id of best performer
    worst_performer: Optional[str] = None
    average_roi: float = 0.0
    total_projects: int = 0


class BreakEvenAnalysisResult(BaseModel):
    """Break-even analysis result."""
    project_id: str
    break_even_days: Optional[int] = None
    daily_value_rate: float = 0.0
    daily_cost_rate: float = 0.0
    cumulative_value: float = 0.0
    cumulative_cost: float = 0.0
    is_profitable: bool = False
    days_since_start: int = 0
    projected_annual_roi: Optional[float] = None


class BreakEvenResponse(BaseModel):
    """Response for break-even analysis."""
    analysis: BreakEvenAnalysisResult
    recommendation: str = ""  # Human-readable recommendation


# =============================================================================
# Value Attribution Breakdown Models
# =============================================================================


class SubcategoryValueResponse(BaseModel):
    """Value for a specific subcategory with confidence and evidence."""
    subcategory: str = Field(..., description="The subcategory identifier (e.g., 'code_generated')")
    parent_type: str = Field(..., description="Parent type: execution, decision, prevention, knowledge")
    value_usd: float = Field(default=0.0, description="Total value in USD")
    confidence: float = Field(default=0.8, ge=0, le=1, description="Confidence score (0-1)")
    count: int = Field(default=1, description="Number of attributions for this subcategory")
    evidence_count: int = Field(default=0, description="Number of evidence items")


class ValueBreakdownByCategory(BaseModel):
    """Breakdown of values within a parent category (execution, decision, etc.)."""
    category: str = Field(..., description="Parent category: execution, decision, prevention, knowledge")
    total_value: float = Field(default=0.0, description="Total value for this category")
    subcategories: List[SubcategoryValueResponse] = Field(
        default_factory=list,
        description="Subcategory breakdown within this category"
    )


class ValueBreakdownExpandedResponse(BaseModel):
    """
    Expanded value breakdown with hierarchical category and subcategory details.

    Used for treemap and drill-down visualizations.
    """
    # Parent type totals
    execution_value: float = Field(default=0.0, description="Total execution value (direct work)")
    decision_value: float = Field(default=0.0, description="Total decision value (strategic)")
    prevention_value: float = Field(default=0.0, description="Total prevention value (problems avoided)")
    knowledge_value: float = Field(default=0.0, description="Total knowledge value (learning)")

    # Total across all categories
    total_value: float = Field(default=0.0, description="Sum of all category values")

    # Hierarchical breakdown for treemap
    by_category: List[ValueBreakdownByCategory] = Field(
        default_factory=list,
        description="Breakdown by parent category with subcategories"
    )

    # Flat subcategory breakdown for detailed tables
    by_subcategory: Dict[str, SubcategoryValueResponse] = Field(
        default_factory=dict,
        description="Flat map of subcategory to value details"
    )

    # Attribution metadata
    attribution_count: int = Field(default=0, description="Total number of value attributions")
    average_confidence: float = Field(default=0.0, description="Average confidence across attributions")


class ValueBreakdownParams(BaseModel):
    """Query parameters for value breakdown endpoint."""
    project_id: Optional[str] = Field(None, description="Filter by project ID")
    from_date: Optional[str] = Field(None, description="From date (ISO format)")
    to_date: Optional[str] = Field(None, description="To date (ISO format)")
    feature_type: Optional[str] = Field(None, description="Filter by feature type")
    min_confidence: Optional[float] = Field(
        None, ge=0, le=1,
        description="Minimum confidence threshold for attributions"
    )


class ValueBreakdownResponse(BaseModel):
    """
    Response for GET /analytics/value/breakdown endpoint.

    Provides hierarchical value breakdown suitable for:
    - Treemap visualization (category -> subcategory hierarchy)
    - Sunburst chart (multi-level drill-down)
    - Category comparison charts
    """
    breakdown: ValueBreakdownExpandedResponse = Field(
        default_factory=ValueBreakdownExpandedResponse,
        description="The value breakdown data"
    )
    period: Optional[Dict[str, Optional[str]]] = Field(
        None,
        description="Time period for the breakdown"
    )
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters that were applied to generate this breakdown"
    )


# =============================================================================
# Cost Avoidance Models
# =============================================================================


class CostAvoidanceEventResponse(BaseModel):
    """Response model for a single cost avoidance event."""
    id: str
    type: str  # bug_production, security_breach, rework_avoided, etc.
    severity: str  # critical, high, medium, low
    estimated_cost_avoided: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    detected_by: str  # qa_reviewer, security_scan, ideation, etc.
    trace_id: str
    artifact_id: Optional[str] = None
    spec_id: Optional[str] = None
    project_id: Optional[str] = None
    description: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class CostAvoidanceSummaryResponse(BaseModel):
    """Summary of cost avoidance data."""
    total_cost_avoided: float = 0.0
    event_count: int = 0
    by_type: Dict[str, float] = Field(default_factory=dict)
    by_severity: Dict[str, float] = Field(default_factory=dict)
    by_detector: Dict[str, float] = Field(default_factory=dict)
    avg_confidence: float = 0.0
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    events: List[CostAvoidanceEventResponse] = Field(default_factory=list)


class CostAvoidanceEventsListResponse(BaseModel):
    """Response for listing cost avoidance events."""
    events: List[CostAvoidanceEventResponse] = Field(default_factory=list)
    total: int = 0
    days: int = 30


class CostAvoidanceTrendPoint(BaseModel):
    """Single point in cost avoidance trend."""
    date: str
    cost_avoided: float = 0.0
    event_count: int = 0
    by_type: Dict[str, float] = Field(default_factory=dict)


class CostAvoidanceTrendResponse(BaseModel):
    """Cost avoidance trend over time."""
    trend: List[CostAvoidanceTrendPoint] = Field(default_factory=list)
    granularity: str = "week"  # day, week, month
    total_cost_avoided: float = 0.0


class RecordCostAvoidanceEventRequest(BaseModel):
    """Request to manually record a cost avoidance event."""
    type: str = Field(..., description="Type: bug_production, security_breach, rework_avoided, duplicate_feature, wrong_architecture")
    severity: str = Field(..., description="Severity: critical, high, medium, low")
    detected_by: str = Field(..., description="Detection source: qa_reviewer, security_scan, ideation, spec_creation, manual")
    trace_id: str = Field(..., description="Associated trace ID")
    description: Optional[str] = Field(None, description="Human-readable description")
    artifact_id: Optional[str] = Field(None, description="Associated artifact ID")
    spec_id: Optional[str] = Field(None, description="Associated spec ID")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Additional evidence data")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score")
    base_cost: Optional[float] = Field(None, description="Base cost for percentage-based calculations")


class RecordCostAvoidanceEventResponse(BaseModel):
    """Response for recording a cost avoidance event."""
    success: bool
    event_id: str
    estimated_cost_avoided: float
    message: str = "Event recorded successfully"


# =============================================================================
# Quality Multiplier Models
# =============================================================================


class QualityAdjustment(BaseModel):
    """Single adjustment to quality multiplier."""
    reason: str
    delta: float


class QualityMultiplierResponse(BaseModel):
    """Response model for quality multiplier calculation."""
    base_value: float = 1.0
    adjustments: List[QualityAdjustment] = Field(default_factory=list)
    final_multiplier: float = 1.0
    tier: str = "neutral"  # exceptional, good, neutral, low, poor
    color: str = "gray"    # green, blue, gray, yellow, red


class QualityMultiplierRequest(BaseModel):
    """Request model for quality multiplier calculation."""
    qa_passed: bool
    qa_attempts: int = 1
    has_tests: bool = False
    has_docs: bool = False
    has_types: bool = False
    code_coverage: Optional[float] = None
    lint_errors: int = 0
    rework_needed: bool = False


class SpecQualityResponse(BaseModel):
    """Quality metrics for a specific spec."""
    spec_id: str
    multiplier: QualityMultiplierResponse
    qa_passed: bool
    qa_attempts: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QualityLeaderboardEntry(BaseModel):
    """Single entry in the quality leaderboard."""
    spec_id: str
    final_multiplier: float
    tier: str
    color: str
    qa_passed: bool
    qa_attempts: int
    adjustments_count: int


class QualityLeaderboardResponse(BaseModel):
    """Response model for quality leaderboard."""
    entries: List[QualityLeaderboardEntry] = Field(default_factory=list)
    total: int = 0
    average_multiplier: float = 1.0
    exceptional_count: int = 0
    good_count: int = 0
    neutral_count: int = 0
    low_count: int = 0
    poor_count: int = 0


# =============================================================================
# Project Benchmark Models (Module 6)
# =============================================================================


class ProjectBenchmarkResponse(BaseModel):
    """Benchmark data for a single project."""
    project_id: str
    total_roi: float = 0.0
    avg_roi_per_spec: float = 0.0
    total_value_generated: float = 0.0
    total_cost: float = 0.0
    specs_count: int = 0
    success_rate: float = 0.0  # % specs with positive ROI
    best_feature_type: str = "unknown"
    worst_feature_type: str = "unknown"
    rank: int = 0
    avg_qa_attempts: float = 0.0
    avg_iterations: float = 0.0
    total_hours_saved: float = 0.0
    avg_complexity: str = "medium"


class BestPracticeResponse(BaseModel):
    """A success pattern identified from top performers."""
    pattern: str
    description: str
    impact: str  # high, medium, low
    adoption_rate: float  # % of top performers using this
    examples: List[str] = Field(default_factory=list)  # project_ids demonstrating this
    category: str = "general"  # general, complexity, qa, agent, iteration


class ProjectRankingsResponse(BaseModel):
    """Response for project rankings."""
    rankings: List[ProjectBenchmarkResponse] = Field(default_factory=list)
    total: int = 0
    metric: str = "roi"
    period: str = "30d"


class BestPracticesResponse(BaseModel):
    """Response for best practices identification."""
    practices: List[BestPracticeResponse] = Field(default_factory=list)
    analyzed_projects: int = 0
    analysis_period: str = "30d"


class ImprovementSuggestionsResponse(BaseModel):
    """Response for improvement suggestions."""
    project_id: str
    suggestions: List[str] = Field(default_factory=list)
    current_rank: Optional[int] = None
    total_projects: int = 0


class PercentileMetricComparison(BaseModel):
    """Single metric comparison against percentile."""
    project_value: float
    percentile_value: float
    delta: float
    status: str  # above, below, equal


class PercentileComparisonResponse(BaseModel):
    """Response for percentile comparison."""
    project_id: str
    percentile: int = 50
    metrics: Dict[str, PercentileMetricComparison] = Field(default_factory=dict)


# Update forward references
TraceDetailResponse.model_rebuild()
