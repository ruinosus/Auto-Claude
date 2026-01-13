"""
ROI Pydantic models for the ROI Engine API.

Contains models for ROI calculation requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# Request Models
# ═══════════════════════════════════════════════════════════════


class ROIRequest(BaseModel):
    """Request to calculate ROI."""

    project_dir: str = Field(..., description="Path to project directory")
    token_cost: float = Field(0.0, description="Token cost in USD")
    squad_config_id: str | None = Field(None, description="Squad config ID to use")


class SpecROIRequest(ROIRequest):
    """Request to calculate ROI for a spec."""

    spec_id: str = Field(..., description="Spec identifier")


class TraceROIRequest(ROIRequest):
    """Request to calculate ROI for a trace."""

    trace_id: str = Field(..., description="Langfuse trace ID")


# ═══════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════


class ROIResponse(BaseModel):
    """Response for ROI calculation."""

    scope: str
    scope_id: str
    total_artifact_value: float
    artifact_count: int
    by_role: dict[str, float]
    by_type: dict[str, float]
    token_cost: float
    net_value: float
    roi_percentage: float
    calculated_at: datetime
    squad_config_id: str | None = None


class ROISummaryResponse(BaseModel):
    """Summary response for quick display."""

    total_value: float
    total_cost: float
    net_value: float
    roi_percentage: float
    artifact_count: int
    top_role: str | None = None
    top_role_value: float = 0.0
    top_artifact_type: str | None = None
    top_artifact_type_value: float = 0.0


class UnifiedROIResponse(BaseModel):
    """Unified ROI response combining multiple sources."""

    # Core ROI metrics
    total_artifact_value: float = 0.0
    total_token_cost: float = 0.0
    net_value: float = 0.0
    roi_percentage: float = 0.0

    # Token metrics
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    # Breakdown
    by_role: dict[str, float] = {}
    by_type: dict[str, float] = {}
    by_spec: dict[str, float] = {}

    # Metadata
    artifact_count: int = 0
    trace_count: int = 0
    period_start: str | None = None
    period_end: str | None = None
    calculated_at: datetime = None


class ROITrendPoint(BaseModel):
    """Single point in ROI trend."""

    date: str
    roi_percentage: float = 0.0
    artifact_value: float = 0.0
    token_cost: float = 0.0
    artifact_count: int = 0


class ROITrendsResponse(BaseModel):
    """Response for ROI trends over time."""

    trends: list[ROITrendPoint]
    period_start: str
    period_end: str
    avg_roi: float = 0.0
    trend_direction: str = "stable"  # "up", "down", "stable"


class ValueBreakdownItem(BaseModel):
    """Single item in value breakdown."""

    category: str
    subcategory: str | None = None
    value: float = 0.0
    percentage: float = 0.0
    count: int = 0


class ValueBreakdownResponse(BaseModel):
    """Detailed value breakdown response."""

    total_value: float = 0.0
    by_role: list[ValueBreakdownItem] = []
    by_type: list[ValueBreakdownItem] = []
    by_seniority: list[ValueBreakdownItem] = []
    by_spec: list[ValueBreakdownItem] = []
