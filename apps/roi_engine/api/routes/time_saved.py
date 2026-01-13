"""
Time Saved Routes - Time savings calculation and benchmarking endpoints.

This module provides REST endpoints for calculating and analyzing time saved
by using AI assistance compared to manual human work. It maps artifacts to
task types and applies industry benchmarks to estimate time savings.

Endpoints:

Time Saved Analysis (Phase 5L):
- GET /time-saved/summary    - Get total time saved summary across all tasks
- GET /time-saved/by-task    - Get breakdown of time saved by task type
- GET /time-saved/trend      - Get time saved trend over time
- GET /time-saved/dashboard  - Get complete time saved dashboard data
- GET /time-saved/benchmarks - Get available task type benchmarks
"""

from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Query

from core import (
    ArtifactConsumer,
    create_consumer,
)
from api.models import (
    TimeSavedBenchmark,
    TimeSavedBenchmarksResponse,
    TimeSavedByTaskListResponse,
    TimeSavedByTaskType,
    TimeSavedComparisonResponse,
    TimeSavedDashboardResponse,
    TimeSavedSummaryResponse,
    TimeSavedTrendPoint,
    TimeSavedTrendResponse,
)


# Industry benchmarks for task types (in hours)
TASK_TIME_BENCHMARKS = {
    "spec_creation": {"hours": 4.0, "minutes": 0, "seconds": 0},
    "implementation": {"hours": 8.0, "minutes": 0, "seconds": 0},
    "code_review": {"hours": 1.0, "minutes": 0, "seconds": 0},
    "qa_testing": {"hours": 2.0, "minutes": 0, "seconds": 0},
    "bug_fix": {"hours": 2.0, "minutes": 0, "seconds": 0},
    "refactoring": {"hours": 3.0, "minutes": 0, "seconds": 0},
    "documentation": {"hours": 1.5, "minutes": 0, "seconds": 0},
    "architecture_design": {"hours": 6.0, "minutes": 0, "seconds": 0},
    "api_design": {"hours": 3.0, "minutes": 0, "seconds": 0},
    "security_review": {"hours": 2.0, "minutes": 0, "seconds": 0},
    "performance_optimization": {"hours": 4.0, "minutes": 0, "seconds": 0},
    "deployment": {"hours": 1.0, "minutes": 0, "seconds": 0},
    "ideation": {"hours": 2.0, "minutes": 0, "seconds": 0},
    "pr_review": {"hours": 0.5, "minutes": 0, "seconds": 0},
    "issue_triage": {"hours": 0.25, "minutes": 0, "seconds": 0},
}


def _calculate_time_saved_from_artifacts(
    artifacts: list[dict],
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    """Calculate time saved based on artifacts produced."""
    by_task_type: dict[str, dict] = {}
    total_benchmark = 0.0
    total_actual = 0.0

    for artifact in artifacts:
        created_at = artifact.get("created_at", "")
        if from_date and created_at < from_date:
            continue
        if to_date and created_at > to_date:
            continue

        # Map artifact type to task type
        artifact_type = artifact.get("type", "unknown").lower()
        task_type = _map_artifact_to_task_type(artifact_type)

        if task_type not in by_task_type:
            by_task_type[task_type] = {
                "count": 0,
                "total_benchmark_hours": 0.0,
                "total_actual_hours": 0.0,
            }

        # Get benchmark time for this task type
        benchmark = TASK_TIME_BENCHMARKS.get(task_type, {"hours": 1.0})
        benchmark_hours = benchmark["hours"]

        # Estimate actual time (AI takes ~10-30% of human time based on role)
        estimated_hours = artifact.get("estimated_hours", 1.0)
        actual_hours = estimated_hours * 0.2  # AI takes ~20% of benchmark time

        by_task_type[task_type]["count"] += 1
        by_task_type[task_type]["total_benchmark_hours"] += benchmark_hours
        by_task_type[task_type]["total_actual_hours"] += actual_hours

        total_benchmark += benchmark_hours
        total_actual += actual_hours

    return {
        "by_task_type": by_task_type,
        "total_benchmark": total_benchmark,
        "total_actual": total_actual,
        "total_saved": total_benchmark - total_actual,
    }


def _map_artifact_to_task_type(artifact_type: str) -> str:
    """Map artifact type to task type for time saved calculation."""
    mapping = {
        # Spec creation
        "spec_document": "spec_creation",
        "requirements": "spec_creation",
        "context_discovery": "spec_creation",
        # Implementation
        "code_example": "implementation",
        "refactoring": "refactoring",
        "bug_fix": "bug_fix",
        "commit": "implementation",
        # Architecture
        "diagram": "architecture_design",
        "architecture_insight": "architecture_design",
        "system_design": "architecture_design",
        "adr": "architecture_design",
        "api_design": "api_design",
        # QA
        "test_case": "qa_testing",
        "qa_report": "qa_testing",
        "qa_verdict": "qa_testing",
        "qa_finding": "qa_testing",
        # Review
        "pr_verdict": "pr_review",
        "code_review": "code_review",
        # Security
        "security_finding": "security_review",
        # Other
        "implementation_plan": "spec_creation",
        "complexity_assessment": "spec_creation",
        "performance_insight": "performance_optimization",
        "deployment_plan": "deployment",
        "recommendation": "ideation",
    }
    return mapping.get(artifact_type, "implementation")


router = APIRouter(prefix="/time-saved", tags=["Time Saved"])


@router.get(
    "/summary",
    response_model=TimeSavedSummaryResponse,
    summary="Get time saved summary",
    description="Get total time saved across all tasks.",
)
async def get_time_saved_summary(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get summary of time saved."""
    project_path = Path(project_dir)
    consumer = create_consumer(project_path)
    artifacts = consumer.get_all_artifacts()

    data = _calculate_time_saved_from_artifacts(artifacts, from_date, to_date)

    total_saved_hours = data["total_saved"]
    total_benchmark_hours = data["total_benchmark"]
    total_actual_hours = data["total_actual"]
    avg_percentage = (
        (total_saved_hours / total_benchmark_hours * 100)
        if total_benchmark_hours > 0 else 0
    )

    by_task_type_response = {}
    for task_type, info in data["by_task_type"].items():
        saved = info["total_benchmark_hours"] - info["total_actual_hours"]
        pct = (saved / info["total_benchmark_hours"] * 100) if info["total_benchmark_hours"] > 0 else 0
        by_task_type_response[task_type] = TimeSavedByTaskType(
            task_type=task_type,
            count=info["count"],
            total_saved_hours=saved,
            total_benchmark_hours=info["total_benchmark_hours"],
            total_actual_hours=info["total_actual_hours"],
            percentage_saved=pct,
        )

    return TimeSavedSummaryResponse(
        total_time_saved_seconds=total_saved_hours * 3600,
        total_time_saved_hours=total_saved_hours,
        total_benchmark_seconds=total_benchmark_hours * 3600,
        total_benchmark_hours=total_benchmark_hours,
        total_actual_seconds=total_actual_hours * 3600,
        total_actual_hours=total_actual_hours,
        average_percentage_saved=avg_percentage,
        task_count=sum(info["count"] for info in data["by_task_type"].values()),
        by_task_type=by_task_type_response,
        period_start=from_date,
        period_end=to_date,
    )


@router.get(
    "/by-task",
    response_model=TimeSavedByTaskListResponse,
    summary="Get time saved by task type",
    description="Get breakdown of time saved by task type.",
)
async def get_time_saved_by_task(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get time saved breakdown by task type."""
    project_path = Path(project_dir)
    consumer = create_consumer(project_path)
    artifacts = consumer.get_all_artifacts()

    data = _calculate_time_saved_from_artifacts(artifacts, from_date, to_date)

    breakdown = []
    for task_type, info in data["by_task_type"].items():
        saved = info["total_benchmark_hours"] - info["total_actual_hours"]
        pct = (saved / info["total_benchmark_hours"] * 100) if info["total_benchmark_hours"] > 0 else 0
        breakdown.append(TimeSavedByTaskType(
            task_type=task_type,
            count=info["count"],
            total_saved_hours=saved,
            total_benchmark_hours=info["total_benchmark_hours"],
            total_actual_hours=info["total_actual_hours"],
            percentage_saved=pct,
        ))

    return TimeSavedByTaskListResponse(
        breakdown=breakdown,
        total_time_saved_hours=data["total_saved"],
        total_benchmark_hours=data["total_benchmark"],
        period_start=from_date,
        period_end=to_date,
    )


@router.get(
    "/trend",
    response_model=TimeSavedTrendResponse,
    summary="Get time saved trend",
    description="Get time saved trend over time.",
)
async def get_time_saved_trend(
    project_dir: str = Query(..., description="Project directory path"),
    granularity: str = Query("day", description="Granularity (hour, day, week)"),
    from_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get time saved trend over time."""
    project_path = Path(project_dir)
    consumer = create_consumer(project_path)
    artifacts = consumer.get_all_artifacts()

    # Group artifacts by date
    by_date: dict[str, list] = defaultdict(list)

    for artifact in artifacts:
        created_at = artifact.get("created_at", "")
        if not created_at:
            continue
        if from_date and created_at < from_date:
            continue
        if to_date and created_at > to_date:
            continue

        # Extract date based on granularity
        if granularity == "hour":
            date_key = created_at[:13]  # YYYY-MM-DDTHH
        elif granularity == "week":
            # Get week start
            try:
                parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                week_start = parsed - timedelta(days=parsed.weekday())
                date_key = week_start.strftime("%Y-%m-%d")
            except Exception:
                date_key = created_at[:10]
        else:
            date_key = created_at[:10]  # YYYY-MM-DD

        by_date[date_key].append(artifact)

    # Calculate trend points
    trend = []
    total_saved = 0.0

    for date_key in sorted(by_date.keys()):
        artifacts_in_period = by_date[date_key]
        data = _calculate_time_saved_from_artifacts(artifacts_in_period)

        saved = data["total_saved"]
        benchmark = data["total_benchmark"]
        actual = data["total_actual"]
        pct = (saved / benchmark * 100) if benchmark > 0 else 0

        trend.append(TimeSavedTrendPoint(
            date=date_key,
            time_saved_hours=saved,
            benchmark_hours=benchmark,
            actual_hours=actual,
            percentage_saved=pct,
            task_count=sum(info["count"] for info in data["by_task_type"].values()),
        ))
        total_saved += saved

    return TimeSavedTrendResponse(
        trend=trend,
        granularity=granularity,
        total_time_saved_hours=total_saved,
        period_start=from_date,
        period_end=to_date,
    )


@router.get(
    "/dashboard",
    response_model=TimeSavedDashboardResponse,
    summary="Get time saved dashboard",
    description="Get complete time saved dashboard data.",
)
async def get_time_saved_dashboard(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get complete time saved dashboard data."""
    # Get summary
    summary = await get_time_saved_summary(project_dir, from_date, to_date)

    # Get by task type
    by_task_response = await get_time_saved_by_task(project_dir, from_date, to_date)

    # Get trend
    trend_response = await get_time_saved_trend(project_dir, "day", from_date, to_date)

    # Calculate comparisons
    comparisons = []
    for task_info in by_task_response.breakdown:
        comparisons.append(TimeSavedComparisonResponse(
            task_type=task_info.task_type,
            with_ai_hours=task_info.total_actual_hours,
            without_ai_hours=task_info.total_benchmark_hours,
            time_saved_hours=task_info.total_saved_hours,
            percentage_saved=task_info.percentage_saved,
        ))

    # Calculate equivalents (8 hours/day, 40 hours/week)
    total_saved = summary.total_time_saved_hours
    work_days = total_saved / 8.0
    work_weeks = total_saved / 40.0

    return TimeSavedDashboardResponse(
        summary=summary,
        by_task_type=by_task_response.breakdown,
        trend=trend_response.trend,
        comparisons=comparisons,
        total_hours_saved=total_saved,
        equivalent_work_days=work_days,
        equivalent_work_weeks=work_weeks,
        period_start=from_date,
        period_end=to_date,
    )


@router.get(
    "/benchmarks",
    response_model=TimeSavedBenchmarksResponse,
    summary="Get time saved benchmarks",
    description="Get available task type benchmarks.",
)
async def get_time_saved_benchmarks():
    """Get available task type benchmarks."""
    benchmarks = {}
    for task_type, info in TASK_TIME_BENCHMARKS.items():
        benchmarks[task_type] = TimeSavedBenchmark(
            hours=info["hours"],
            minutes=info.get("minutes", 0),
            seconds=info.get("seconds", 0),
        )

    return TimeSavedBenchmarksResponse(benchmarks=benchmarks)
