"""
Satisfaction Survey Pydantic models for the ROI Engine API.

Contains models for satisfaction surveys and NPS metrics.
"""

from pydantic import BaseModel, Field


class SatisfactionSurveyRequest(BaseModel):
    """Request to submit a satisfaction survey."""

    spec_id: str
    user_id: str
    overall_satisfaction: int = Field(..., ge=1, le=5, description="Overall satisfaction (1-5)")
    output_quality: int = Field(..., ge=1, le=5, description="Output quality (1-5)")
    time_saved_perception: int = Field(..., ge=1, le=5, description="Time saved perception (1-5)")
    would_recommend: int = Field(..., ge=1, le=5, description="Would recommend (1-5, NPS)")
    feedback: str | None = None
    improvement_suggestions: str | None = None


class SatisfactionSurveyResponse(BaseModel):
    """Response after submitting a survey."""

    id: str
    spec_id: str
    user_id: str
    timestamp: str
    overall_satisfaction: int
    output_quality: int
    time_saved_perception: int
    would_recommend: int
    feedback: str | None = None
    improvement_suggestions: str | None = None
    project_id: str | None = None


class SatisfactionMetrics(BaseModel):
    """Aggregated satisfaction metrics."""

    nps_score: float = Field(0.0, description="Net Promoter Score (-100 to 100)")
    avg_satisfaction: float = Field(0.0, ge=1, le=5, description="Average satisfaction (1-5)")
    avg_output_quality: float = Field(0.0, ge=1, le=5, description="Average output quality (1-5)")
    avg_time_saved: float = Field(0.0, ge=1, le=5, description="Average time saved perception (1-5)")
    satisfaction_trend: float = Field(0.0, description="Percentage change in satisfaction")
    response_count: int = 0
    promoters_count: int = 0
    passives_count: int = 0
    detractors_count: int = 0
    top_feedback_themes: list[str] = []
    period_days: int = 30
    period_start: str | None = None
    period_end: str | None = None


class NPSResponse(BaseModel):
    """Net Promoter Score response."""

    nps_score: float = 0.0
    response_count: int = 0
    promoters_count: int = 0
    passives_count: int = 0
    detractors_count: int = 0
    period_days: int = 30


class FeedbackEntry(BaseModel):
    """Single feedback entry."""

    id: str
    spec_id: str
    timestamp: str | None = None
    overall_satisfaction: int
    would_recommend: int
    feedback: str | None = None
    improvement_suggestions: str | None = None


class FeedbackListResponse(BaseModel):
    """List of feedback entries."""

    feedback: list[FeedbackEntry] = []
    total: int = 0
    period_days: int = 30


class SurveyListResponse(BaseModel):
    """List of satisfaction surveys."""

    surveys: list[SatisfactionSurveyResponse] = []
    total: int = 0


class SurveyDeleteResponse(BaseModel):
    """Response after deleting a survey."""

    success: bool
    survey_id: str
    message: str = ""
