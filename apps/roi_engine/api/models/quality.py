"""
Quality Pydantic models for the ROI Engine API.

Contains models for quality scores and value breakdown.
"""

from pydantic import BaseModel


class QualityScorePoint(BaseModel):
    """Single point in quality score timeline."""

    date: str
    avg_quality_score: float = 0.0
    artifact_count: int = 0
    high_quality_count: int = 0  # score >= 0.8
    low_quality_count: int = 0   # score < 0.5


class QualityScoresResponse(BaseModel):
    """Quality scores over time."""

    scores: list[QualityScorePoint]
    period_start: str
    period_end: str
    overall_avg_quality: float = 0.0
    quality_trend: str = "stable"  # "improving", "declining", "stable"


class QualityByAgentResponse(BaseModel):
    """Quality breakdown by agent type."""

    agent_type: str
    avg_quality_score: float = 0.0
    artifact_count: int = 0
    high_quality_percentage: float = 0.0


class QualityByAgentListResponse(BaseModel):
    """List of quality scores by agent."""

    agents: list[QualityByAgentResponse]
    overall_avg_quality: float = 0.0
