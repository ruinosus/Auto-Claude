"""
Satisfaction Survey API Routes
==============================

API endpoints for developer satisfaction surveys and NPS tracking.
"""

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from .models import (
    SatisfactionSurveyRequest,
    SatisfactionSurveyResponse,
    SatisfactionMetricsResponse,
    NPSResponse,
    FeedbackEntryResponse,
    FeedbackListResponse,
    SurveySubmitResponse,
)

logger = logging.getLogger(__name__)

# Create router for satisfaction endpoints
satisfaction_router = APIRouter(prefix="/satisfaction", tags=["satisfaction"])

# Import satisfaction service
try:
    from analytics.satisfaction import (
        SatisfactionService,
        SatisfactionSurvey,
        get_satisfaction_service,
    )
    SATISFACTION_AVAILABLE = True
except ImportError:
    SATISFACTION_AVAILABLE = False
    logger.warning("Satisfaction service not available")


def _get_satisfaction_service(project_path: str) -> SatisfactionService:
    """Get the satisfaction service for a project."""
    if not SATISFACTION_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Satisfaction service not available"
        )
    return get_satisfaction_service(Path(project_path))


@satisfaction_router.post("/survey", response_model=SurveySubmitResponse)
async def submit_satisfaction_survey(
    survey: SatisfactionSurveyRequest,
    project_path: str = Query(..., description="Project path for storage"),
):
    """
    Submit a satisfaction survey.

    Accepts a survey response with ratings (1-5) for:
    - overall_satisfaction: Overall experience rating
    - output_quality: Quality of AI-generated output
    - time_saved_perception: Perception of time saved
    - would_recommend: Would recommend to others (used for NPS)

    Optional fields:
    - feedback: Free-text feedback
    - improvement_suggestions: Suggestions for improvement
    """
    try:
        service = _get_satisfaction_service(project_path)

        satisfaction_survey = SatisfactionSurvey(
            spec_id=survey.spec_id,
            user_id=survey.user_id,
            overall_satisfaction=survey.overall_satisfaction,
            output_quality=survey.output_quality,
            time_saved_perception=survey.time_saved_perception,
            would_recommend=survey.would_recommend,
            feedback=survey.feedback,
            improvement_suggestions=survey.improvement_suggestions,
        )

        survey_id = service.submit_survey(satisfaction_survey)

        return SurveySubmitResponse(
            success=True,
            survey_id=survey_id,
            message="Survey submitted successfully",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit satisfaction survey: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit survey: {e}")


@satisfaction_router.get("/metrics", response_model=SatisfactionMetricsResponse)
async def get_satisfaction_metrics(
    project_path: str = Query(..., description="Project path"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    spec_id: Optional[str] = Query(None, description="Filter by spec ID"),
    days: int = Query(30, ge=1, le=365, description="Period in days"),
):
    """
    Get aggregated satisfaction metrics.

    Returns:
    - NPS score (-100 to 100)
    - Average satisfaction ratings
    - Satisfaction trend vs previous period
    - Response breakdown (promoters, passives, detractors)
    - Top feedback themes
    """
    try:
        service = _get_satisfaction_service(project_path)
        metrics = service.get_metrics(
            project_id=project_id,
            spec_id=spec_id,
            days=days,
        )

        return SatisfactionMetricsResponse(
            nps_score=metrics.nps_score,
            avg_satisfaction=metrics.avg_satisfaction,
            avg_output_quality=metrics.avg_output_quality,
            avg_time_saved=metrics.avg_time_saved,
            satisfaction_trend=metrics.satisfaction_trend,
            response_count=metrics.response_count,
            promoters_count=metrics.promoters_count,
            passives_count=metrics.passives_count,
            detractors_count=metrics.detractors_count,
            top_feedback_themes=metrics.top_feedback_themes,
            period_days=metrics.period_days,
            period_start=metrics.period_start,
            period_end=metrics.period_end,
        )

    except Exception as e:
        logger.error(f"Failed to get satisfaction metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {e}")


@satisfaction_router.get("/nps", response_model=NPSResponse)
async def get_nps_score(
    project_path: str = Query(..., description="Project path"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    spec_id: Optional[str] = Query(None, description="Filter by spec ID"),
    days: int = Query(30, ge=1, le=365, description="Period in days"),
):
    """
    Get Net Promoter Score (NPS).

    NPS = ((promoters - detractors) / total) * 100
    - Promoters: would_recommend >= 4 (scores 4-5)
    - Passives: would_recommend == 3
    - Detractors: would_recommend <= 2 (scores 1-2)

    Returns a score from -100 (all detractors) to +100 (all promoters).
    """
    try:
        service = _get_satisfaction_service(project_path)
        metrics = service.get_metrics(
            project_id=project_id,
            spec_id=spec_id,
            days=days,
        )

        return NPSResponse(
            nps_score=metrics.nps_score,
            response_count=metrics.response_count,
            promoters_count=metrics.promoters_count,
            passives_count=metrics.passives_count,
            detractors_count=metrics.detractors_count,
            period_days=days,
        )

    except Exception as e:
        logger.error(f"Failed to get NPS score: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get NPS: {e}")


@satisfaction_router.get("/feedback", response_model=FeedbackListResponse)
async def get_categorized_feedback(
    project_path: str = Query(..., description="Project path"),
    days: int = Query(30, ge=1, le=365, description="Period in days"),
    include_empty: bool = Query(False, description="Include surveys without feedback text"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of entries"),
):
    """
    Get categorized feedback entries.

    Returns a list of feedback entries with their associated ratings
    and timestamps, useful for displaying in a feedback review panel.
    """
    try:
        service = _get_satisfaction_service(project_path)
        feedback_list = service.get_feedback_list(
            days=days,
            include_empty=include_empty,
            limit=limit,
        )

        entries = [
            FeedbackEntryResponse(
                id=entry["id"],
                spec_id=entry["spec_id"],
                timestamp=entry.get("timestamp"),
                overall_satisfaction=entry["overall_satisfaction"],
                would_recommend=entry["would_recommend"],
                feedback=entry.get("feedback"),
                improvement_suggestions=entry.get("improvement_suggestions"),
            )
            for entry in feedback_list
        ]

        return FeedbackListResponse(
            feedback=entries,
            total=len(entries),
            period_days=days,
        )

    except Exception as e:
        logger.error(f"Failed to get feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get feedback: {e}")


@satisfaction_router.get("/surveys", response_model=List[SatisfactionSurveyResponse])
async def list_satisfaction_surveys(
    project_path: str = Query(..., description="Project path"),
    spec_id: Optional[str] = Query(None, description="Filter by spec ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    days: int = Query(30, ge=1, le=365, description="Period in days"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of surveys"),
):
    """
    List satisfaction surveys with optional filtering.

    Returns detailed survey data for analysis or export.
    """
    try:
        service = _get_satisfaction_service(project_path)
        surveys = service.get_surveys(
            spec_id=spec_id,
            user_id=user_id,
            days=days,
            limit=limit,
        )

        return [
            SatisfactionSurveyResponse(
                id=s.id,
                spec_id=s.spec_id,
                user_id=s.user_id,
                timestamp=s.timestamp,
                overall_satisfaction=s.overall_satisfaction,
                output_quality=s.output_quality,
                time_saved_perception=s.time_saved_perception,
                would_recommend=s.would_recommend,
                feedback=s.feedback,
                improvement_suggestions=s.improvement_suggestions,
                project_id=s.project_id,
            )
            for s in surveys
        ]

    except Exception as e:
        logger.error(f"Failed to list surveys: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list surveys: {e}")


@satisfaction_router.delete("/survey/{survey_id}")
async def delete_satisfaction_survey(
    survey_id: str,
    project_path: str = Query(..., description="Project path"),
):
    """
    Delete a satisfaction survey.

    Returns success status.
    """
    try:
        service = _get_satisfaction_service(project_path)
        deleted = service.delete_survey(survey_id)

        if not deleted:
            raise HTTPException(status_code=404, detail=f"Survey {survey_id} not found")

        return {"success": True, "message": f"Survey {survey_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete survey: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete survey: {e}")
