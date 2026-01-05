"""
Developer Satisfaction Service
==============================

Measures developer satisfaction through NPS (Net Promoter Score) surveys.
Stores survey responses and provides aggregate metrics for tracking satisfaction
over time.

Usage:
    from analytics.satisfaction import SatisfactionService, SatisfactionSurvey

    service = SatisfactionService(project_dir)

    # Submit a survey
    survey = SatisfactionSurvey(
        spec_id="001-add-auth",
        user_id="user123",
        overall_satisfaction=4,
        output_quality=5,
        time_saved_perception=4,
        would_recommend=5,
        feedback="Great experience!",
    )
    service.submit_survey(survey)

    # Get NPS score
    nps = service.calculate_nps(days=30)  # -100 to 100

    # Get full metrics
    metrics = service.get_metrics(days=30)
"""

import json
import logging
import threading
import uuid
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Thread lock for file operations
_STORAGE_LOCK = threading.Lock()

# Storage constants
SATISFACTION_DIR = "satisfaction"
SURVEYS_FILE = "surveys.json"
INDEX_FILE = "index.json"


@dataclass
class SatisfactionSurvey:
    """A single satisfaction survey response."""
    spec_id: str
    user_id: str

    # Scale 1-5
    overall_satisfaction: int
    output_quality: int
    time_saved_perception: int
    would_recommend: int  # Used for NPS calculation

    # Optional free text
    feedback: Optional[str] = None
    improvement_suggestions: Optional[str] = None

    # Auto-generated fields
    id: str = field(default_factory=lambda: f"survey_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    project_id: Optional[str] = None

    def validate(self) -> list[str]:
        """Validate survey fields. Returns list of error messages."""
        errors = []

        # Validate scale fields (1-5)
        scale_fields = [
            ("overall_satisfaction", self.overall_satisfaction),
            ("output_quality", self.output_quality),
            ("time_saved_perception", self.time_saved_perception),
            ("would_recommend", self.would_recommend),
        ]

        for field_name, value in scale_fields:
            if not isinstance(value, int) or value < 1 or value > 5:
                errors.append(f"{field_name} must be an integer between 1 and 5")

        # Validate required fields
        if not self.spec_id:
            errors.append("spec_id is required")
        if not self.user_id:
            errors.append("user_id is required")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert datetime to ISO string
        if isinstance(data["timestamp"], datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SatisfactionSurvey":
        """Create from dictionary (loaded from storage)."""
        # Convert ISO string back to datetime
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class SatisfactionMetrics:
    """Aggregated satisfaction metrics."""
    nps_score: float  # Net Promoter Score (-100 to 100)
    avg_satisfaction: float  # Average overall satisfaction (1-5)
    avg_output_quality: float  # Average output quality (1-5)
    avg_time_saved: float  # Average time saved perception (1-5)
    satisfaction_trend: float  # Change vs previous period (percentage points)
    response_count: int
    promoters_count: int  # would_recommend >= 4
    passives_count: int  # would_recommend == 3
    detractors_count: int  # would_recommend <= 2
    top_feedback_themes: list[str] = field(default_factory=list)

    # Period info
    period_days: int = 30
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class SatisfactionService:
    """Service for managing developer satisfaction surveys and metrics."""

    def __init__(self, project_dir: Path):
        """
        Initialize the satisfaction service.

        Args:
            project_dir: Project root directory
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self._storage_dir = self.project_dir / ".auto-claude" / SATISFACTION_DIR
        self._surveys_path = self._storage_dir / SURVEYS_FILE
        self._index_path = self._storage_dir / INDEX_FILE

    def _ensure_storage(self) -> None:
        """Ensure storage directory exists."""
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _load_surveys(self) -> list[dict]:
        """Load all surveys from storage."""
        if not self._surveys_path.exists():
            return []

        try:
            with open(self._surveys_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load surveys: {e}")
            return []

    def _save_surveys(self, surveys: list[dict]) -> None:
        """Save surveys to storage atomically."""
        self._ensure_storage()

        # Write to temp file first
        temp_path = self._surveys_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(surveys, f, indent=2, ensure_ascii=False, default=str)
            temp_path.replace(self._surveys_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _load_index(self) -> dict:
        """Load the survey index."""
        if not self._index_path.exists():
            return {
                "total_surveys": 0,
                "by_spec": {},
                "by_user": {},
                "last_updated": None,
            }

        try:
            with open(self._index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load index: {e}")
            return {
                "total_surveys": 0,
                "by_spec": {},
                "by_user": {},
                "last_updated": None,
            }

    def _save_index(self, index: dict) -> None:
        """Save the index atomically."""
        self._ensure_storage()
        index["last_updated"] = datetime.now(timezone.utc).isoformat()

        temp_path = self._index_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
            temp_path.replace(self._index_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def submit_survey(self, survey: SatisfactionSurvey) -> str:
        """
        Submit a satisfaction survey.

        Args:
            survey: The survey to submit

        Returns:
            The survey ID

        Raises:
            ValueError: If survey validation fails
        """
        # Validate survey
        errors = survey.validate()
        if errors:
            raise ValueError(f"Survey validation failed: {', '.join(errors)}")

        # Set project_id if not set
        if not survey.project_id:
            survey.project_id = self.project_dir.name

        with _STORAGE_LOCK:
            # Load existing surveys
            surveys = self._load_surveys()

            # Add new survey
            survey_dict = survey.to_dict()
            surveys.append(survey_dict)

            # Save surveys
            self._save_surveys(surveys)

            # Update index
            index = self._load_index()
            index["total_surveys"] = len(surveys)

            # Update by_spec index
            if survey.spec_id not in index["by_spec"]:
                index["by_spec"][survey.spec_id] = []
            index["by_spec"][survey.spec_id].append(survey.id)

            # Update by_user index
            if survey.user_id not in index["by_user"]:
                index["by_user"][survey.user_id] = []
            index["by_user"][survey.user_id].append(survey.id)

            self._save_index(index)

        logger.info(f"Submitted satisfaction survey {survey.id} for spec {survey.spec_id}")
        return survey.id

    def get_surveys(
        self,
        spec_id: Optional[str] = None,
        user_id: Optional[str] = None,
        days: int = 30,
        limit: int = 100,
    ) -> list[SatisfactionSurvey]:
        """
        Get surveys with optional filtering.

        Args:
            spec_id: Filter by spec ID
            user_id: Filter by user ID
            days: Only include surveys from the last N days
            limit: Maximum number of surveys to return

        Returns:
            List of SatisfactionSurvey objects
        """
        surveys_data = self._load_surveys()

        # Calculate cutoff date
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Filter surveys
        filtered = []
        for data in surveys_data:
            # Parse timestamp
            timestamp_str = data.get("timestamp", "")
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except (ValueError, TypeError):
                continue

            # Apply date filter
            if timestamp < cutoff:
                continue

            # Apply spec_id filter
            if spec_id and data.get("spec_id") != spec_id:
                continue

            # Apply user_id filter
            if user_id and data.get("user_id") != user_id:
                continue

            filtered.append(data)

        # Sort by timestamp descending
        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Apply limit
        filtered = filtered[:limit]

        # Convert to SatisfactionSurvey objects
        return [SatisfactionSurvey.from_dict(data) for data in filtered]

    def calculate_nps(
        self,
        project_id: Optional[str] = None,
        spec_id: Optional[str] = None,
        days: int = 30,
    ) -> float:
        """
        Calculate Net Promoter Score.

        NPS = ((promoters - detractors) / total) * 100
        - Promoters: would_recommend >= 4 (scores 4-5)
        - Passives: would_recommend == 3
        - Detractors: would_recommend <= 2 (scores 1-2)

        Args:
            project_id: Filter by project ID (unused currently, for future multi-project)
            spec_id: Filter by spec ID
            days: Only include surveys from the last N days

        Returns:
            NPS score (-100 to 100)
        """
        surveys = self.get_surveys(spec_id=spec_id, days=days, limit=10000)

        if not surveys:
            return 0.0

        promoters = sum(1 for s in surveys if s.would_recommend >= 4)
        detractors = sum(1 for s in surveys if s.would_recommend <= 2)
        total = len(surveys)

        nps = ((promoters - detractors) / total) * 100
        return round(nps, 1)

    def _extract_feedback_themes(self, surveys: list[SatisfactionSurvey]) -> list[str]:
        """
        Extract common themes from feedback text.

        This is a simple keyword-based approach. For production,
        consider using NLP/LLM-based theme extraction.
        """
        # Common theme keywords
        theme_keywords = {
            "speed": ["fast", "quick", "slow", "speed", "time"],
            "quality": ["quality", "accurate", "correct", "wrong", "error", "bug"],
            "documentation": ["doc", "documentation", "readme", "comment"],
            "ui": ["ui", "interface", "button", "screen", "display"],
            "reliability": ["reliable", "crash", "fail", "stable", "unstable"],
            "ease_of_use": ["easy", "simple", "complex", "confusing", "intuitive"],
        }

        theme_counts: Counter[str] = Counter()

        for survey in surveys:
            text = f"{survey.feedback or ''} {survey.improvement_suggestions or ''}".lower()

            for theme, keywords in theme_keywords.items():
                if any(kw in text for kw in keywords):
                    theme_counts[theme] += 1

        # Return top 5 themes
        return [theme for theme, _ in theme_counts.most_common(5)]

    def get_metrics(
        self,
        project_id: Optional[str] = None,
        spec_id: Optional[str] = None,
        days: int = 30,
    ) -> SatisfactionMetrics:
        """
        Get aggregated satisfaction metrics.

        Args:
            project_id: Filter by project ID (unused currently)
            spec_id: Filter by spec ID
            days: Period in days

        Returns:
            SatisfactionMetrics with all aggregated data
        """
        surveys = self.get_surveys(spec_id=spec_id, days=days, limit=10000)

        if not surveys:
            return SatisfactionMetrics(
                nps_score=0.0,
                avg_satisfaction=0.0,
                avg_output_quality=0.0,
                avg_time_saved=0.0,
                satisfaction_trend=0.0,
                response_count=0,
                promoters_count=0,
                passives_count=0,
                detractors_count=0,
                top_feedback_themes=[],
                period_days=days,
            )

        # Calculate averages
        total = len(surveys)
        avg_satisfaction = sum(s.overall_satisfaction for s in surveys) / total
        avg_output_quality = sum(s.output_quality for s in surveys) / total
        avg_time_saved = sum(s.time_saved_perception for s in surveys) / total

        # Calculate NPS components
        promoters = sum(1 for s in surveys if s.would_recommend >= 4)
        passives = sum(1 for s in surveys if s.would_recommend == 3)
        detractors = sum(1 for s in surveys if s.would_recommend <= 2)
        nps = ((promoters - detractors) / total) * 100

        # Calculate trend (compare to previous period)
        prev_surveys = self.get_surveys(spec_id=spec_id, days=days * 2, limit=10000)
        # Filter to only previous period
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        prev_period = [s for s in prev_surveys if s.timestamp < cutoff]

        if prev_period:
            prev_avg = sum(s.overall_satisfaction for s in prev_period) / len(prev_period)
            satisfaction_trend = ((avg_satisfaction - prev_avg) / prev_avg) * 100 if prev_avg > 0 else 0
        else:
            satisfaction_trend = 0.0

        # Extract feedback themes
        top_themes = self._extract_feedback_themes(surveys)

        # Calculate period dates
        now = datetime.now(timezone.utc)
        period_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        period_end = now.strftime("%Y-%m-%d")

        return SatisfactionMetrics(
            nps_score=round(nps, 1),
            avg_satisfaction=round(avg_satisfaction, 2),
            avg_output_quality=round(avg_output_quality, 2),
            avg_time_saved=round(avg_time_saved, 2),
            satisfaction_trend=round(satisfaction_trend, 1),
            response_count=total,
            promoters_count=promoters,
            passives_count=passives,
            detractors_count=detractors,
            top_feedback_themes=top_themes,
            period_days=days,
            period_start=period_start,
            period_end=period_end,
        )

    def get_feedback_list(
        self,
        days: int = 30,
        include_empty: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get a list of feedback entries for display.

        Args:
            days: Period in days
            include_empty: Include surveys without feedback text
            limit: Maximum number of entries

        Returns:
            List of feedback entries with survey metadata
        """
        surveys = self.get_surveys(days=days, limit=limit * 2)  # Get more to filter

        feedback_list = []
        for survey in surveys:
            has_feedback = bool(survey.feedback or survey.improvement_suggestions)

            if not include_empty and not has_feedback:
                continue

            feedback_list.append({
                "id": survey.id,
                "spec_id": survey.spec_id,
                "timestamp": survey.timestamp.isoformat() if survey.timestamp else None,
                "overall_satisfaction": survey.overall_satisfaction,
                "would_recommend": survey.would_recommend,
                "feedback": survey.feedback,
                "improvement_suggestions": survey.improvement_suggestions,
            })

            if len(feedback_list) >= limit:
                break

        return feedback_list

    def delete_survey(self, survey_id: str) -> bool:
        """
        Delete a survey by ID.

        Args:
            survey_id: The survey ID to delete

        Returns:
            True if deleted, False if not found
        """
        with _STORAGE_LOCK:
            surveys = self._load_surveys()

            # Find and remove the survey
            original_len = len(surveys)
            surveys = [s for s in surveys if s.get("id") != survey_id]

            if len(surveys) == original_len:
                return False  # Not found

            # Save updated surveys
            self._save_surveys(surveys)

            # Update index (rebuild for simplicity)
            index = self._load_index()
            index["total_surveys"] = len(surveys)

            # Remove from by_spec
            for spec_id in list(index["by_spec"].keys()):
                if survey_id in index["by_spec"][spec_id]:
                    index["by_spec"][spec_id].remove(survey_id)
                if not index["by_spec"][spec_id]:
                    del index["by_spec"][spec_id]

            # Remove from by_user
            for user_id in list(index["by_user"].keys()):
                if survey_id in index["by_user"][user_id]:
                    index["by_user"][user_id].remove(survey_id)
                if not index["by_user"][user_id]:
                    del index["by_user"][user_id]

            self._save_index(index)

        logger.info(f"Deleted satisfaction survey {survey_id}")
        return True


# =============================================================================
# Module-level convenience functions
# =============================================================================

_default_service: Optional[SatisfactionService] = None


def get_satisfaction_service(project_dir: Optional[Path] = None) -> SatisfactionService:
    """
    Get or create the default satisfaction service.

    Args:
        project_dir: Project directory (uses current dir if not provided)

    Returns:
        SatisfactionService instance
    """
    global _default_service

    if _default_service is None or (project_dir and _default_service.project_dir != project_dir):
        _default_service = SatisfactionService(project_dir or Path.cwd())

    return _default_service


def submit_satisfaction_survey(
    spec_id: str,
    user_id: str,
    overall_satisfaction: int,
    output_quality: int,
    time_saved_perception: int,
    would_recommend: int,
    feedback: Optional[str] = None,
    improvement_suggestions: Optional[str] = None,
    project_dir: Optional[Path] = None,
) -> str:
    """
    Convenience function to submit a satisfaction survey.

    Args:
        spec_id: The spec ID this survey is for
        user_id: The user submitting the survey
        overall_satisfaction: Overall satisfaction (1-5)
        output_quality: Output quality rating (1-5)
        time_saved_perception: Time saved perception (1-5)
        would_recommend: Would recommend score (1-5, used for NPS)
        feedback: Optional free-text feedback
        improvement_suggestions: Optional improvement suggestions
        project_dir: Project directory

    Returns:
        The survey ID
    """
    service = get_satisfaction_service(project_dir)
    survey = SatisfactionSurvey(
        spec_id=spec_id,
        user_id=user_id,
        overall_satisfaction=overall_satisfaction,
        output_quality=output_quality,
        time_saved_perception=time_saved_perception,
        would_recommend=would_recommend,
        feedback=feedback,
        improvement_suggestions=improvement_suggestions,
    )
    return service.submit_survey(survey)
