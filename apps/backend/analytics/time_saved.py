"""
Developer Time Saved Calculator
================================

Calculates developer time saved using industry benchmarks.
Compares actual AI-assisted duration against estimated human developer time.
"""

from dataclasses import dataclass, field
from datetime import timedelta, datetime
from typing import Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Complexity(Enum):
    """Task complexity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class TaskBenchmark:
    """Benchmark data for a completed task."""
    task_type: str
    avg_time_without_ai: timedelta
    actual_time_with_ai: timedelta
    time_saved: timedelta
    percentage_saved: float
    complexity: Complexity = Complexity.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)


# Industry benchmarks for developer tasks (without AI assistance)
# These represent typical time a mid-level developer would spend
TASK_BENCHMARKS: Dict[str, timedelta] = {
    # Spec/Planning Phase
    "spec_writing": timedelta(hours=8),
    "requirements_gathering": timedelta(hours=4),
    "complexity_assessment": timedelta(hours=1),
    "context_discovery": timedelta(hours=2),

    # Implementation Phase
    "feature_implementation_simple": timedelta(hours=16),
    "feature_implementation_standard": timedelta(hours=32),
    "feature_implementation_complex": timedelta(hours=40),
    "subtask_implementation": timedelta(hours=4),

    # Code Review & QA
    "code_review": timedelta(minutes=45),
    "qa_review": timedelta(hours=2),
    "qa_fix": timedelta(hours=1),

    # Bug Fixes
    "bug_fix_simple": timedelta(hours=2),
    "bug_fix_medium": timedelta(hours=4),
    "bug_fix_complex": timedelta(hours=8),

    # Documentation
    "documentation": timedelta(hours=4),
    "api_documentation": timedelta(hours=2),
    "readme_update": timedelta(hours=1),

    # Diagrams & Visuals
    "diagram_creation": timedelta(hours=2),
    "architecture_diagram": timedelta(hours=3),
    "sequence_diagram": timedelta(hours=1, minutes=30),

    # Planning & Strategy
    "roadmap_planning": timedelta(hours=16),
    "sprint_planning": timedelta(hours=4),
    "feature_ideation": timedelta(hours=4),

    # Security & Auditing
    "security_audit": timedelta(hours=24),
    "dependency_review": timedelta(hours=2),
    "vulnerability_assessment": timedelta(hours=8),

    # GitHub/PR Tasks
    "pr_review": timedelta(hours=1),
    "issue_triage": timedelta(minutes=15),
    "merge_conflict_resolution": timedelta(minutes=30),

    # Research & Analysis
    "technology_research": timedelta(hours=4),
    "codebase_analysis": timedelta(hours=6),
    "performance_analysis": timedelta(hours=4),
}

# Complexity multipliers
COMPLEXITY_MULTIPLIERS: Dict[Complexity, float] = {
    Complexity.LOW: 0.7,
    Complexity.MEDIUM: 1.0,
    Complexity.HIGH: 1.5,
}


class TimeSavedCalculator:
    """
    Calculates developer time saved by comparing AI-assisted task duration
    against industry benchmarks for human developers.
    """

    def __init__(self, custom_benchmarks: Optional[Dict[str, timedelta]] = None):
        """
        Initialize calculator with optional custom benchmarks.

        Args:
            custom_benchmarks: Override default benchmarks with custom values
        """
        self.benchmarks = {**TASK_BENCHMARKS}
        if custom_benchmarks:
            self.benchmarks.update(custom_benchmarks)

    def calculate_time_saved(
        self,
        task_type: str,
        actual_duration: timedelta,
        complexity: str = "medium"
    ) -> TaskBenchmark:
        """
        Calculate time saved for a specific task.

        Args:
            task_type: Type of task (must match a benchmark key)
            actual_duration: Actual time spent with AI assistance
            complexity: Task complexity (low, medium, high)

        Returns:
            TaskBenchmark with calculated savings

        Raises:
            ValueError: If task_type is not in benchmarks
        """
        if task_type not in self.benchmarks:
            # Try to find a close match or use a default
            task_type = self._find_closest_task_type(task_type)

        # Parse complexity
        try:
            complexity_enum = Complexity(complexity.lower())
        except ValueError:
            complexity_enum = Complexity.MEDIUM

        # Get base benchmark and apply complexity multiplier
        base_benchmark = self.benchmarks[task_type]
        multiplier = COMPLEXITY_MULTIPLIERS[complexity_enum]
        adjusted_benchmark = timedelta(seconds=base_benchmark.total_seconds() * multiplier)

        # Calculate time saved
        time_saved = adjusted_benchmark - actual_duration

        # Calculate percentage saved (avoid division by zero)
        if adjusted_benchmark.total_seconds() > 0:
            percentage_saved = (time_saved.total_seconds() / adjusted_benchmark.total_seconds()) * 100
        else:
            percentage_saved = 0.0

        return TaskBenchmark(
            task_type=task_type,
            avg_time_without_ai=adjusted_benchmark,
            actual_time_with_ai=actual_duration,
            time_saved=time_saved,
            percentage_saved=percentage_saved,
            complexity=complexity_enum,
        )

    def _find_closest_task_type(self, task_type: str) -> str:
        """Find the closest matching task type or return a default."""
        task_lower = task_type.lower()

        # Direct mapping for common variations
        mappings = {
            "spec": "spec_writing",
            "feature": "feature_implementation_standard",
            "feature_simple": "feature_implementation_simple",
            "feature_complex": "feature_implementation_complex",
            "bug": "bug_fix_medium",
            "bug_simple": "bug_fix_simple",
            "bug_complex": "bug_fix_complex",
            "review": "code_review",
            "docs": "documentation",
            "diagram": "diagram_creation",
            "roadmap": "roadmap_planning",
            "security": "security_audit",
            "pr": "pr_review",
            "issue": "issue_triage",
        }

        if task_lower in mappings:
            return mappings[task_lower]

        # Fuzzy match
        for key in self.benchmarks:
            if task_lower in key or key in task_lower:
                return key

        # Default to standard feature implementation
        logger.warning(f"Unknown task type '{task_type}', defaulting to 'subtask_implementation'")
        return "subtask_implementation"

    def calculate_batch_time_saved(
        self,
        tasks: List[Dict[str, any]]
    ) -> List[TaskBenchmark]:
        """
        Calculate time saved for multiple tasks.

        Args:
            tasks: List of dicts with 'task_type', 'actual_duration_seconds',
                   and optional 'complexity'

        Returns:
            List of TaskBenchmark results
        """
        results = []
        for task in tasks:
            actual_duration = timedelta(seconds=task.get("actual_duration_seconds", 0))
            result = self.calculate_time_saved(
                task_type=task.get("task_type", "subtask_implementation"),
                actual_duration=actual_duration,
                complexity=task.get("complexity", "medium"),
            )
            results.append(result)
        return results

    def get_summary(self, benchmarks: List[TaskBenchmark]) -> Dict[str, any]:
        """
        Get aggregate summary of time saved across multiple tasks.

        Args:
            benchmarks: List of TaskBenchmark results

        Returns:
            Summary dict with totals and averages
        """
        if not benchmarks:
            return {
                "total_time_saved_seconds": 0,
                "total_time_saved_hours": 0.0,
                "total_benchmark_seconds": 0,
                "total_benchmark_hours": 0.0,
                "total_actual_seconds": 0,
                "total_actual_hours": 0.0,
                "average_percentage_saved": 0.0,
                "task_count": 0,
                "by_task_type": {},
            }

        total_saved_seconds = sum(b.time_saved.total_seconds() for b in benchmarks)
        total_benchmark_seconds = sum(b.avg_time_without_ai.total_seconds() for b in benchmarks)
        total_actual_seconds = sum(b.actual_time_with_ai.total_seconds() for b in benchmarks)

        # Calculate percentage saved from totals (more accurate than average of percentages)
        overall_percentage = 0.0
        if total_benchmark_seconds > 0:
            overall_percentage = (total_saved_seconds / total_benchmark_seconds) * 100

        # Group by task type
        by_task_type: Dict[str, Dict] = {}
        for b in benchmarks:
            if b.task_type not in by_task_type:
                by_task_type[b.task_type] = {
                    "count": 0,
                    "total_saved_seconds": 0,
                    "total_benchmark_seconds": 0,
                    "total_actual_seconds": 0,
                }
            by_task_type[b.task_type]["count"] += 1
            by_task_type[b.task_type]["total_saved_seconds"] += b.time_saved.total_seconds()
            by_task_type[b.task_type]["total_benchmark_seconds"] += b.avg_time_without_ai.total_seconds()
            by_task_type[b.task_type]["total_actual_seconds"] += b.actual_time_with_ai.total_seconds()

        # Calculate percentage for each task type
        for task_type, data in by_task_type.items():
            if data["total_benchmark_seconds"] > 0:
                data["percentage_saved"] = (
                    data["total_saved_seconds"] / data["total_benchmark_seconds"]
                ) * 100
            else:
                data["percentage_saved"] = 0.0
            # Convert to hours for convenience
            data["total_saved_hours"] = data["total_saved_seconds"] / 3600
            data["total_benchmark_hours"] = data["total_benchmark_seconds"] / 3600
            data["total_actual_hours"] = data["total_actual_seconds"] / 3600

        return {
            "total_time_saved_seconds": total_saved_seconds,
            "total_time_saved_hours": total_saved_seconds / 3600,
            "total_benchmark_seconds": total_benchmark_seconds,
            "total_benchmark_hours": total_benchmark_seconds / 3600,
            "total_actual_seconds": total_actual_seconds,
            "total_actual_hours": total_actual_seconds / 3600,
            "average_percentage_saved": overall_percentage,
            "task_count": len(benchmarks),
            "by_task_type": by_task_type,
        }

    def get_trend_data(
        self,
        benchmarks: List[TaskBenchmark],
        group_by: str = "day"
    ) -> List[Dict[str, any]]:
        """
        Get time saved trend data grouped by time period.

        Args:
            benchmarks: List of TaskBenchmark results
            group_by: Grouping period ('hour', 'day', 'week')

        Returns:
            List of data points for charting
        """
        from collections import defaultdict

        if not benchmarks:
            return []

        # Group benchmarks by period
        grouped: Dict[str, List[TaskBenchmark]] = defaultdict(list)

        for b in benchmarks:
            if group_by == "hour":
                key = b.created_at.strftime("%Y-%m-%d %H:00")
            elif group_by == "week":
                # Get start of week (Monday)
                start_of_week = b.created_at - timedelta(days=b.created_at.weekday())
                key = start_of_week.strftime("%Y-%m-%d")
            else:  # day (default)
                key = b.created_at.strftime("%Y-%m-%d")
            grouped[key].append(b)

        # Calculate totals for each period
        trend_data = []
        for period, period_benchmarks in sorted(grouped.items()):
            saved_seconds = sum(b.time_saved.total_seconds() for b in period_benchmarks)
            benchmark_seconds = sum(b.avg_time_without_ai.total_seconds() for b in period_benchmarks)
            actual_seconds = sum(b.actual_time_with_ai.total_seconds() for b in period_benchmarks)

            percentage = 0.0
            if benchmark_seconds > 0:
                percentage = (saved_seconds / benchmark_seconds) * 100

            trend_data.append({
                "date": period,
                "time_saved_hours": saved_seconds / 3600,
                "benchmark_hours": benchmark_seconds / 3600,
                "actual_hours": actual_seconds / 3600,
                "percentage_saved": percentage,
                "task_count": len(period_benchmarks),
            })

        return trend_data

    def estimate_from_spec_complexity(
        self,
        complexity: str,
        phases_completed: List[str]
    ) -> TaskBenchmark:
        """
        Estimate time saved based on spec complexity and phases completed.

        This is useful for estimating value when exact durations aren't tracked.

        Args:
            complexity: Spec complexity ('simple', 'standard', 'complex')
            phases_completed: List of completed phases

        Returns:
            Estimated TaskBenchmark
        """
        # Map spec complexity to task types
        complexity_mapping = {
            "simple": "feature_implementation_simple",
            "standard": "feature_implementation_standard",
            "complex": "feature_implementation_complex",
        }

        task_type = complexity_mapping.get(complexity.lower(), "feature_implementation_standard")

        # Estimate actual duration based on typical AI performance
        # AI typically completes tasks in 10-30% of human time
        base_benchmark = self.benchmarks.get(task_type, timedelta(hours=32))

        # Adjust based on phases - more phases = more comprehensive work
        phase_count = len(phases_completed)
        if phase_count >= 8:
            ai_efficiency = 0.15  # 85% savings for full complex pipeline
        elif phase_count >= 6:
            ai_efficiency = 0.20  # 80% savings for standard pipeline
        else:
            ai_efficiency = 0.25  # 75% savings for simple pipeline

        estimated_actual = timedelta(seconds=base_benchmark.total_seconds() * ai_efficiency)

        return self.calculate_time_saved(
            task_type=task_type,
            actual_duration=estimated_actual,
            complexity="medium" if complexity == "standard" else complexity.lower(),
        )


# Global instance for convenience
_default_calculator: Optional[TimeSavedCalculator] = None


def get_calculator() -> TimeSavedCalculator:
    """Get the global TimeSavedCalculator instance."""
    global _default_calculator
    if _default_calculator is None:
        _default_calculator = TimeSavedCalculator()
    return _default_calculator


def calculate_time_saved(
    task_type: str,
    actual_duration: timedelta,
    complexity: str = "medium"
) -> TaskBenchmark:
    """
    Convenience function to calculate time saved using the global calculator.

    Args:
        task_type: Type of task (must match a benchmark key)
        actual_duration: Actual time spent with AI assistance
        complexity: Task complexity (low, medium, high)

    Returns:
        TaskBenchmark with calculated savings
    """
    return get_calculator().calculate_time_saved(task_type, actual_duration, complexity)
