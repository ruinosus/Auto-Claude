"""
Time Saved Pydantic models for the ROI Engine API.

Contains models for time saved metrics and dashboard.
"""

from pydantic import BaseModel


class TimeSavedByTaskType(BaseModel):
    """Time saved breakdown for a specific task type."""

    task_type: str
    count: int = 0
    total_saved_hours: float = 0.0
    total_benchmark_hours: float = 0.0
    total_actual_hours: float = 0.0
    percentage_saved: float = 0.0


class TimeSavedSummaryResponse(BaseModel):
    """Summary of time saved across all tasks."""

    total_time_saved_seconds: float = 0.0
    total_time_saved_hours: float = 0.0
    total_benchmark_seconds: float = 0.0
    total_benchmark_hours: float = 0.0
    total_actual_seconds: float = 0.0
    total_actual_hours: float = 0.0
    average_percentage_saved: float = 0.0
    task_count: int = 0
    by_task_type: dict[str, TimeSavedByTaskType] = {}
    period_start: str | None = None
    period_end: str | None = None


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

    trend: list[TimeSavedTrendPoint] = []
    granularity: str = "day"
    total_time_saved_hours: float = 0.0
    period_start: str | None = None
    period_end: str | None = None


class TimeSavedComparisonResponse(BaseModel):
    """Comparison of time with/without AI for a task type."""

    task_type: str
    with_ai_hours: float = 0.0
    without_ai_hours: float = 0.0
    time_saved_hours: float = 0.0
    percentage_saved: float = 0.0
    complexity: str | None = None


class TimeSavedDashboardResponse(BaseModel):
    """Complete time saved dashboard data."""

    summary: TimeSavedSummaryResponse
    by_task_type: list[TimeSavedByTaskType] = []
    trend: list[TimeSavedTrendPoint] = []
    comparisons: list[TimeSavedComparisonResponse] = []
    total_hours_saved: float = 0.0
    equivalent_work_days: float = 0.0
    equivalent_work_weeks: float = 0.0
    period_start: str | None = None
    period_end: str | None = None


class TimeSavedBenchmark(BaseModel):
    """Benchmark time for a task type."""

    hours: float = 0.0
    minutes: float = 0.0
    seconds: float = 0.0


class TimeSavedBenchmarksResponse(BaseModel):
    """Available task type benchmarks."""

    benchmarks: dict[str, TimeSavedBenchmark] = {}


class TimeSavedByTaskListResponse(BaseModel):
    """Breakdown of time saved by task type."""

    breakdown: list[TimeSavedByTaskType] = []
    total_time_saved_hours: float = 0.0
    total_benchmark_hours: float = 0.0
    period_start: str | None = None
    period_end: str | None = None
