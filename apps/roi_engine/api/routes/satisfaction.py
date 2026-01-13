"""
Satisfaction Survey Routes.

Endpoints for collecting and analyzing user satisfaction data:
- POST /satisfaction/survey - Submit a satisfaction survey after spec completion
- GET /satisfaction/metrics - Get aggregated satisfaction metrics (NPS, averages)
- GET /satisfaction/nps - Get Net Promoter Score breakdown
- GET /satisfaction/feedback - Get list of feedback entries
- GET /satisfaction/surveys - List all satisfaction surveys
- DELETE /satisfaction/survey/{survey_id} - Delete a satisfaction survey
"""

import json
from collections import Counter
from datetime import datetime as dt, timedelta
from pathlib import Path

from fastapi import APIRouter, Query

from api.models import (
    FeedbackEntry,
    FeedbackListResponse,
    NPSResponse,
    SatisfactionMetrics,
    SatisfactionSurveyRequest,
    SatisfactionSurveyResponse,
    SurveyDeleteResponse,
    SurveyListResponse,
)


# In-memory storage for surveys (in production, use database)
_satisfaction_surveys: list[dict] = []


def _load_surveys(project_path: Path) -> list[dict]:
    """Load surveys from local storage and memory."""
    surveys = list(_satisfaction_surveys)

    surveys_dir = project_path / ".auto-claude" / "satisfaction"
    if surveys_dir.exists():
        for survey_file in surveys_dir.glob("survey_*.json"):
            try:
                data = json.loads(survey_file.read_text())
                # Avoid duplicates
                if not any(s.get("id") == data.get("id") for s in surveys):
                    surveys.append(data)
            except Exception:
                pass

    return surveys


def _extract_feedback_themes(surveys: list[dict]) -> list[str]:
    """Extract common themes from feedback text."""
    words = []
    stop_words = {"the", "a", "an", "is", "it", "to", "and", "of", "for", "in", "on", "with", "this", "that", "was", "be"}

    for survey in surveys:
        feedback = survey.get("feedback", "") or ""
        suggestions = survey.get("improvement_suggestions", "") or ""
        text = f"{feedback} {suggestions}".lower()

        for word in text.split():
            word = word.strip(".,!?()[]{}\"'")
            if len(word) > 3 and word not in stop_words:
                words.append(word)

    # Get most common
    counter = Counter(words)
    return [word for word, _ in counter.most_common(10)]


# Satisfaction router with /satisfaction prefix
router = APIRouter(prefix="/satisfaction", tags=["Satisfaction"])


@router.post(
    "/survey",
    response_model=SatisfactionSurveyResponse,
    summary="Submit satisfaction survey",
    description="Submit a satisfaction survey after spec completion.",
)
async def submit_satisfaction_survey(
    project_dir: str = Query(..., description="Project directory path"),
    survey: SatisfactionSurveyRequest = ...,
):
    """Submit a satisfaction survey."""
    import uuid

    survey_id = f"survey_{uuid.uuid4().hex[:12]}"
    timestamp = dt.now().isoformat()

    survey_data = {
        "id": survey_id,
        "spec_id": survey.spec_id,
        "user_id": survey.user_id,
        "timestamp": timestamp,
        "overall_satisfaction": survey.overall_satisfaction,
        "output_quality": survey.output_quality,
        "time_saved_perception": survey.time_saved_perception,
        "would_recommend": survey.would_recommend,
        "feedback": survey.feedback,
        "improvement_suggestions": survey.improvement_suggestions,
        "project_id": Path(project_dir).name,
    }

    _satisfaction_surveys.append(survey_data)

    # Also save to local storage
    project_path = Path(project_dir)
    surveys_dir = project_path / ".auto-claude" / "satisfaction"
    surveys_dir.mkdir(parents=True, exist_ok=True)

    survey_file = surveys_dir / f"{survey_id}.json"
    survey_file.write_text(json.dumps(survey_data, indent=2))

    return SatisfactionSurveyResponse(**survey_data)


@router.get(
    "/metrics",
    response_model=SatisfactionMetrics,
    summary="Get satisfaction metrics",
    description="Get aggregated satisfaction metrics.",
)
async def get_satisfaction_metrics(
    project_dir: str = Query(..., description="Project directory path"),
    days: int = Query(30, description="Number of days to include"),
):
    """Get aggregated satisfaction metrics."""
    project_path = Path(project_dir)
    surveys = _load_surveys(project_path)

    # Filter by date
    cutoff = (dt.now() - timedelta(days=days)).isoformat()
    filtered = [s for s in surveys if s.get("timestamp", "") >= cutoff]

    if not filtered:
        return SatisfactionMetrics(
            nps_score=0,
            avg_satisfaction=0,
            avg_output_quality=0,
            avg_time_saved=0,
            satisfaction_trend=0,
            response_count=0,
            promoters_count=0,
            passives_count=0,
            detractors_count=0,
            top_feedback_themes=[],
            period_days=days,
        )

    # Calculate metrics
    total_satisfaction = sum(s.get("overall_satisfaction", 0) for s in filtered)
    total_quality = sum(s.get("output_quality", 0) for s in filtered)
    total_time_saved = sum(s.get("time_saved_perception", 0) for s in filtered)

    # NPS calculation
    promoters = sum(1 for s in filtered if s.get("would_recommend", 0) >= 4)
    passives = sum(1 for s in filtered if s.get("would_recommend", 0) == 3)
    detractors = sum(1 for s in filtered if s.get("would_recommend", 0) <= 2)

    total = len(filtered)
    nps = ((promoters - detractors) / total * 100) if total > 0 else 0

    # Extract feedback themes (simple word frequency)
    themes = _extract_feedback_themes(filtered)

    return SatisfactionMetrics(
        nps_score=nps,
        avg_satisfaction=total_satisfaction / total if total > 0 else 0,
        avg_output_quality=total_quality / total if total > 0 else 0,
        avg_time_saved=total_time_saved / total if total > 0 else 0,
        satisfaction_trend=0,  # Would need historical data
        response_count=total,
        promoters_count=promoters,
        passives_count=passives,
        detractors_count=detractors,
        top_feedback_themes=themes[:5],
        period_days=days,
    )


@router.get(
    "/nps",
    response_model=NPSResponse,
    summary="Get NPS score",
    description="Get Net Promoter Score.",
)
async def get_nps_score(
    project_dir: str = Query(..., description="Project directory path"),
    days: int = Query(30, description="Number of days to include"),
):
    """Get Net Promoter Score."""
    project_path = Path(project_dir)
    surveys = _load_surveys(project_path)

    cutoff = (dt.now() - timedelta(days=days)).isoformat()
    filtered = [s for s in surveys if s.get("timestamp", "") >= cutoff]

    promoters = sum(1 for s in filtered if s.get("would_recommend", 0) >= 4)
    passives = sum(1 for s in filtered if s.get("would_recommend", 0) == 3)
    detractors = sum(1 for s in filtered if s.get("would_recommend", 0) <= 2)

    total = len(filtered)
    nps = ((promoters - detractors) / total * 100) if total > 0 else 0

    return NPSResponse(
        nps_score=nps,
        response_count=total,
        promoters_count=promoters,
        passives_count=passives,
        detractors_count=detractors,
        period_days=days,
    )


@router.get(
    "/feedback",
    response_model=FeedbackListResponse,
    summary="Get feedback list",
    description="Get list of feedback entries.",
)
async def get_satisfaction_feedback(
    project_dir: str = Query(..., description="Project directory path"),
    days: int = Query(30, description="Number of days to include"),
    limit: int = Query(50, description="Maximum entries to return"),
):
    """Get list of feedback entries."""
    project_path = Path(project_dir)
    surveys = _load_surveys(project_path)

    cutoff = (dt.now() - timedelta(days=days)).isoformat()
    filtered = [s for s in surveys if s.get("timestamp", "") >= cutoff]

    # Sort by timestamp descending
    filtered.sort(key=lambda s: s.get("timestamp", ""), reverse=True)

    feedback = []
    for s in filtered[:limit]:
        feedback.append(FeedbackEntry(
            id=s.get("id", ""),
            spec_id=s.get("spec_id", ""),
            timestamp=s.get("timestamp"),
            overall_satisfaction=s.get("overall_satisfaction", 0),
            would_recommend=s.get("would_recommend", 0),
            feedback=s.get("feedback"),
            improvement_suggestions=s.get("improvement_suggestions"),
        ))

    return FeedbackListResponse(
        feedback=feedback,
        total=len(filtered),
        period_days=days,
    )


@router.get(
    "/surveys",
    response_model=SurveyListResponse,
    summary="List surveys",
    description="List all satisfaction surveys.",
)
async def list_satisfaction_surveys(
    project_dir: str = Query(..., description="Project directory path"),
    spec_id: str | None = Query(None, description="Filter by spec ID"),
    limit: int = Query(100, description="Maximum entries to return"),
):
    """List all satisfaction surveys."""
    project_path = Path(project_dir)
    surveys = _load_surveys(project_path)

    if spec_id:
        surveys = [s for s in surveys if s.get("spec_id") == spec_id]

    # Sort by timestamp descending
    surveys.sort(key=lambda s: s.get("timestamp", ""), reverse=True)

    result = []
    for s in surveys[:limit]:
        result.append(SatisfactionSurveyResponse(
            id=s.get("id", ""),
            spec_id=s.get("spec_id", ""),
            user_id=s.get("user_id", ""),
            timestamp=s.get("timestamp", ""),
            overall_satisfaction=s.get("overall_satisfaction", 0),
            output_quality=s.get("output_quality", 0),
            time_saved_perception=s.get("time_saved_perception", 0),
            would_recommend=s.get("would_recommend", 0),
            feedback=s.get("feedback"),
            improvement_suggestions=s.get("improvement_suggestions"),
            project_id=s.get("project_id"),
        ))

    return SurveyListResponse(surveys=result, total=len(surveys))


@router.delete(
    "/survey/{survey_id}",
    response_model=SurveyDeleteResponse,
    summary="Delete survey",
    description="Delete a satisfaction survey.",
)
async def delete_satisfaction_survey(
    survey_id: str,
    project_dir: str = Query(..., description="Project directory path"),
):
    """Delete a satisfaction survey."""
    global _satisfaction_surveys

    project_path = Path(project_dir)
    surveys_dir = project_path / ".auto-claude" / "satisfaction"

    survey_file = surveys_dir / f"{survey_id}.json"
    if survey_file.exists():
        survey_file.unlink()
        return SurveyDeleteResponse(
            success=True,
            survey_id=survey_id,
            message=f"Survey {survey_id} deleted",
        )

    # Check in-memory
    original_len = len(_satisfaction_surveys)
    _satisfaction_surveys = [s for s in _satisfaction_surveys if s.get("id") != survey_id]

    if len(_satisfaction_surveys) < original_len:
        return SurveyDeleteResponse(
            success=True,
            survey_id=survey_id,
            message=f"Survey {survey_id} deleted from memory",
        )

    return SurveyDeleteResponse(
        success=False,
        survey_id=survey_id,
        message=f"Survey {survey_id} not found",
    )
