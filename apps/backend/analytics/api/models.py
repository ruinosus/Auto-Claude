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
# ROI Models
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


# Update forward references
TraceDetailResponse.model_rebuild()
