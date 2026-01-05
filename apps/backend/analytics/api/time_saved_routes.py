"""
Time Saved API Routes
=====================

REST API endpoints for calculating and displaying developer time saved.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Query

from .models import (
    TimeSavedSummaryResponse,
    TimeSavedByTaskResponse,
    TimeSavedByTaskListResponse,
    TimeSavedTrendPoint,
    TimeSavedTrendResponse,
    TimeSavedComparisonResponse,
    TimeSavedDashboardResponse,
)
from .langfuse_client import TraceFilter

logger = logging.getLogger(__name__)
router = APIRouter()

# Import time saved calculator
try:
    from analytics.time_saved import (
        TimeSavedCalculator,
        TaskBenchmark,
        TASK_BENCHMARKS,
        get_calculator,
    )
    TIME_SAVED_AVAILABLE = True
except ImportError:
    TIME_SAVED_AVAILABLE = False
    TaskBenchmark = None
    TASK_BENCHMARKS = {}

    def get_calculator():
        return None


def get_client():
    """Get the Langfuse client from the app context."""
    from .app import get_langfuse_client
    from fastapi import HTTPException
    client = get_langfuse_client()
    if not client or not client.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Langfuse client not configured. Check API keys."
        )
    return client


def _estimate_task_type_from_trace(trace) -> str:
    """Estimate task type from trace metadata and name."""
    if trace.metadata:
        # Check for explicit task_type
        if "task_type" in trace.metadata:
            return trace.metadata["task_type"]

        # Check for phase
        phase = trace.metadata.get("phase", "")
        if phase:
            phase_mappings = {
                "discovery": "context_discovery",
                "requirements": "requirements_gathering",
                "research": "technology_research",
                "context": "context_discovery",
                "spec": "spec_writing",
                "plan": "feature_implementation_standard",
                "validate": "qa_review",
            }
            if phase in phase_mappings:
                return phase_mappings[phase]

        # Check for complexity
        complexity = trace.metadata.get("complexity", "")
        if complexity == "simple":
            return "feature_implementation_simple"
        elif complexity == "complex":
            return "feature_implementation_complex"

    # Infer from trace name
    name_lower = (trace.name or "").lower()

    if "planner" in name_lower:
        return "feature_implementation_standard"
    elif "coder" in name_lower:
        return "subtask_implementation"
    elif "qa_reviewer" in name_lower:
        return "qa_review"
    elif "qa_fixer" in name_lower:
        return "qa_fix"
    elif "gatherer" in name_lower:
        return "requirements_gathering"
    elif "researcher" in name_lower:
        return "technology_research"
    elif "writer" in name_lower or "spec" in name_lower:
        return "spec_writing"
    elif "roadmap" in name_lower:
        return "roadmap_planning"
    elif "ideation" in name_lower:
        return "feature_ideation"
    elif "pr" in name_lower or "review" in name_lower:
        return "pr_review"
    elif "issue" in name_lower or "triage" in name_lower:
        return "issue_triage"
    elif "diagram" in name_lower:
        return "diagram_creation"
    elif "security" in name_lower:
        return "security_audit"
    elif "doc" in name_lower:
        return "documentation"

    return "subtask_implementation"


def _estimate_complexity_from_trace(trace) -> str:
    """Estimate complexity from trace metadata."""
    if trace.metadata:
        complexity = trace.metadata.get("complexity", "")
        if complexity in ["simple", "low"]:
            return "low"
        elif complexity in ["complex", "high"]:
            return "high"
    return "medium"


@router.get("/time-saved/summary", response_model=TimeSavedSummaryResponse)
async def get_time_saved_summary(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
):
    """
    Get total time saved summary.

    Calculates developer time saved by comparing AI-assisted task duration
    against industry benchmarks for human developers.
    """
    period = {
        "from": from_date.isoformat() if from_date else None,
        "to": to_date.isoformat() if to_date else None,
    }

    if not TIME_SAVED_AVAILABLE:
        return TimeSavedSummaryResponse(period=period)

    client = get_client()
    calculator = get_calculator()

    try:
        # Get traces for the period
        filter = TraceFilter(
            project_id=project_id,
            from_timestamp=from_date,
            to_timestamp=to_date,
            limit=100,
        )
        traces = await client.get_traces(filter)

        if not traces:
            return TimeSavedSummaryResponse(period=period)

        # Calculate time saved for each trace
        benchmarks: List[TaskBenchmark] = []
        for trace in traces:
            task_type = _estimate_task_type_from_trace(trace)
            complexity = _estimate_complexity_from_trace(trace)

            # Use trace latency as actual duration
            actual_duration_seconds = trace.latency_ms / 1000 if trace.latency_ms else 0

            # Skip traces with no meaningful duration
            if actual_duration_seconds < 1:
                continue

            benchmark = calculator.calculate_time_saved(
                task_type=task_type,
                actual_duration=timedelta(seconds=actual_duration_seconds),
                complexity=complexity,
            )
            benchmark.created_at = trace.timestamp
            benchmarks.append(benchmark)

        # Get summary
        summary = calculator.get_summary(benchmarks)

        return TimeSavedSummaryResponse(
            total_time_saved_seconds=summary["total_time_saved_seconds"],
            total_time_saved_hours=summary["total_time_saved_hours"],
            total_benchmark_seconds=summary["total_benchmark_seconds"],
            total_benchmark_hours=summary["total_benchmark_hours"],
            total_actual_seconds=summary["total_actual_seconds"],
            total_actual_hours=summary["total_actual_hours"],
            average_percentage_saved=summary["average_percentage_saved"],
            task_count=summary["task_count"],
            by_task_type=summary["by_task_type"],
            period=period,
        )

    except Exception as e:
        logger.error(f"Failed to get time saved summary: {e}")
        return TimeSavedSummaryResponse(period=period)


@router.get("/time-saved/by-task", response_model=TimeSavedByTaskListResponse)
async def get_time_saved_by_task(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
):
    """
    Get time saved breakdown by task type.

    Shows how much time was saved for each type of task (spec writing,
    implementation, code review, etc.).
    """
    period = {
        "from": from_date.isoformat() if from_date else None,
        "to": to_date.isoformat() if to_date else None,
    }

    if not TIME_SAVED_AVAILABLE:
        return TimeSavedByTaskListResponse(period=period)

    client = get_client()
    calculator = get_calculator()

    try:
        filter = TraceFilter(
            project_id=project_id,
            from_timestamp=from_date,
            to_timestamp=to_date,
            limit=100,
        )
        traces = await client.get_traces(filter)

        if not traces:
            return TimeSavedByTaskListResponse(period=period)

        benchmarks: List[TaskBenchmark] = []
        for trace in traces:
            task_type = _estimate_task_type_from_trace(trace)
            complexity = _estimate_complexity_from_trace(trace)
            actual_duration_seconds = trace.latency_ms / 1000 if trace.latency_ms else 0

            if actual_duration_seconds < 1:
                continue

            benchmark = calculator.calculate_time_saved(
                task_type=task_type,
                actual_duration=timedelta(seconds=actual_duration_seconds),
                complexity=complexity,
            )
            benchmarks.append(benchmark)

        summary = calculator.get_summary(benchmarks)

        # Convert by_task_type to list response
        breakdown = [
            TimeSavedByTaskResponse(
                task_type=task_type,
                count=data["count"],
                total_saved_hours=data["total_saved_hours"],
                total_benchmark_hours=data["total_benchmark_hours"],
                total_actual_hours=data["total_actual_hours"],
                percentage_saved=data["percentage_saved"],
            )
            for task_type, data in summary["by_task_type"].items()
        ]

        # Sort by total saved hours descending
        breakdown.sort(key=lambda x: x.total_saved_hours, reverse=True)

        return TimeSavedByTaskListResponse(
            breakdown=breakdown,
            total_time_saved_hours=summary["total_time_saved_hours"],
            total_benchmark_hours=summary["total_benchmark_hours"],
            period=period,
        )

    except Exception as e:
        logger.error(f"Failed to get time saved by task: {e}")
        return TimeSavedByTaskListResponse(period=period)


@router.get("/time-saved/trend", response_model=TimeSavedTrendResponse)
async def get_time_saved_trend(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    granularity: str = Query("day", description="Grouping period: hour, day, week"),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
):
    """
    Get time saved trend over time.

    Returns time-series data showing time saved grouped by the specified
    granularity (hour, day, or week).
    """
    period = {
        "from": from_date.isoformat() if from_date else None,
        "to": to_date.isoformat() if to_date else None,
    }

    if not TIME_SAVED_AVAILABLE:
        return TimeSavedTrendResponse(granularity=granularity, period=period)

    client = get_client()
    calculator = get_calculator()

    try:
        filter = TraceFilter(
            project_id=project_id,
            from_timestamp=from_date,
            to_timestamp=to_date,
            limit=100,
        )
        traces = await client.get_traces(filter)

        if not traces:
            return TimeSavedTrendResponse(granularity=granularity, period=period)

        benchmarks: List[TaskBenchmark] = []
        for trace in traces:
            task_type = _estimate_task_type_from_trace(trace)
            complexity = _estimate_complexity_from_trace(trace)
            actual_duration_seconds = trace.latency_ms / 1000 if trace.latency_ms else 0

            if actual_duration_seconds < 1:
                continue

            benchmark = calculator.calculate_time_saved(
                task_type=task_type,
                actual_duration=timedelta(seconds=actual_duration_seconds),
                complexity=complexity,
            )
            benchmark.created_at = trace.timestamp
            benchmarks.append(benchmark)

        # Get trend data
        trend_data = calculator.get_trend_data(benchmarks, group_by=granularity)

        total_saved = sum(p["time_saved_hours"] for p in trend_data)

        trend = [
            TimeSavedTrendPoint(
                date=p["date"],
                time_saved_hours=p["time_saved_hours"],
                benchmark_hours=p["benchmark_hours"],
                actual_hours=p["actual_hours"],
                percentage_saved=p["percentage_saved"],
                task_count=p["task_count"],
            )
            for p in trend_data
        ]

        return TimeSavedTrendResponse(
            trend=trend,
            granularity=granularity,
            total_time_saved_hours=total_saved,
            period=period,
        )

    except Exception as e:
        logger.error(f"Failed to get time saved trend: {e}")
        return TimeSavedTrendResponse(granularity=granularity, period=period)


@router.get("/time-saved/dashboard", response_model=TimeSavedDashboardResponse)
async def get_time_saved_dashboard(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
):
    """
    Get complete time saved dashboard data.

    Returns all data needed for the time saved visualization:
    - Summary statistics
    - Breakdown by task type
    - Trend over time
    - AI vs human comparison data
    """
    period = {
        "from": from_date.isoformat() if from_date else None,
        "to": to_date.isoformat() if to_date else None,
    }

    if not TIME_SAVED_AVAILABLE:
        return TimeSavedDashboardResponse(
            summary=TimeSavedSummaryResponse(),
            period=period,
        )

    client = get_client()
    calculator = get_calculator()

    try:
        filter = TraceFilter(
            project_id=project_id,
            from_timestamp=from_date,
            to_timestamp=to_date,
            limit=100,
        )
        traces = await client.get_traces(filter)

        if not traces:
            return TimeSavedDashboardResponse(
                summary=TimeSavedSummaryResponse(),
                period=period,
            )

        benchmarks: List[TaskBenchmark] = []
        for trace in traces:
            task_type = _estimate_task_type_from_trace(trace)
            complexity = _estimate_complexity_from_trace(trace)
            actual_duration_seconds = trace.latency_ms / 1000 if trace.latency_ms else 0

            if actual_duration_seconds < 1:
                continue

            benchmark = calculator.calculate_time_saved(
                task_type=task_type,
                actual_duration=timedelta(seconds=actual_duration_seconds),
                complexity=complexity,
            )
            benchmark.created_at = trace.timestamp
            benchmarks.append(benchmark)

        # Get all data
        summary_data = calculator.get_summary(benchmarks)
        trend_data = calculator.get_trend_data(benchmarks, group_by="day")

        # Build summary response
        summary = TimeSavedSummaryResponse(
            total_time_saved_seconds=summary_data["total_time_saved_seconds"],
            total_time_saved_hours=summary_data["total_time_saved_hours"],
            total_benchmark_seconds=summary_data["total_benchmark_seconds"],
            total_benchmark_hours=summary_data["total_benchmark_hours"],
            total_actual_seconds=summary_data["total_actual_seconds"],
            total_actual_hours=summary_data["total_actual_hours"],
            average_percentage_saved=summary_data["average_percentage_saved"],
            task_count=summary_data["task_count"],
            by_task_type=summary_data["by_task_type"],
        )

        # Build by task type breakdown
        by_task_type = [
            TimeSavedByTaskResponse(
                task_type=task_type,
                count=data["count"],
                total_saved_hours=data["total_saved_hours"],
                total_benchmark_hours=data["total_benchmark_hours"],
                total_actual_hours=data["total_actual_hours"],
                percentage_saved=data["percentage_saved"],
            )
            for task_type, data in summary_data["by_task_type"].items()
        ]
        by_task_type.sort(key=lambda x: x.total_saved_hours, reverse=True)

        # Build trend
        trend = [
            TimeSavedTrendPoint(
                date=p["date"],
                time_saved_hours=p["time_saved_hours"],
                benchmark_hours=p["benchmark_hours"],
                actual_hours=p["actual_hours"],
                percentage_saved=p["percentage_saved"],
                task_count=p["task_count"],
            )
            for p in trend_data
        ]

        # Build comparisons (for side-by-side visualization)
        comparisons = [
            TimeSavedComparisonResponse(
                task_type=task_type,
                with_ai_hours=data["total_actual_hours"],
                without_ai_hours=data["total_benchmark_hours"],
                time_saved_hours=data["total_saved_hours"],
                percentage_saved=data["percentage_saved"],
            )
            for task_type, data in summary_data["by_task_type"].items()
        ]
        comparisons.sort(key=lambda x: x.time_saved_hours, reverse=True)

        # Calculate work day/week equivalents (8 hours/day, 40 hours/week)
        total_hours = summary_data["total_time_saved_hours"]
        work_days = total_hours / 8
        work_weeks = total_hours / 40

        return TimeSavedDashboardResponse(
            summary=summary,
            by_task_type=by_task_type,
            trend=trend,
            comparisons=comparisons,
            total_hours_saved=total_hours,
            equivalent_work_days=round(work_days, 1),
            equivalent_work_weeks=round(work_weeks, 2),
            period=period,
        )

    except Exception as e:
        logger.error(f"Failed to get time saved dashboard: {e}")
        return TimeSavedDashboardResponse(
            summary=TimeSavedSummaryResponse(),
            period=period,
        )


@router.get("/time-saved/benchmarks")
async def get_time_saved_benchmarks():
    """
    Get available task type benchmarks.

    Returns the industry standard benchmarks used for calculating time saved.
    """
    if not TIME_SAVED_AVAILABLE:
        return {"benchmarks": {}, "error": "Time saved calculator not available"}

    return {
        "benchmarks": {
            task_type: {
                "hours": duration.total_seconds() / 3600,
                "minutes": duration.total_seconds() / 60,
                "seconds": duration.total_seconds(),
            }
            for task_type, duration in TASK_BENCHMARKS.items()
        }
    }
