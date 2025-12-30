"""
ROI Score Publisher
====================

Publishes ROI scores to Langfuse after spec completion.
Combines git diff stats with Langfuse trace costs to calculate and store ROI metrics.

This module is the bridge between:
- ROITracker: Captures git diff stats and QA results
- ROICalculator: Calculates ROI using hybrid methodology
- Langfuse: Stores ROI scores for frontend consumption

Usage:
    from analytics.roi_score_publisher import publish_roi_scores

    # After QA passes or spec completes:
    result = await publish_roi_scores(
        spec_id="001-feature",
        project_dir=Path("/path/to/project"),
        qa_attempts=2,
        qa_passed=True,
    )
"""

import os
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any, List, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


def get_git_diff_stats(project_dir: Path, initial_commit: Optional[str] = None) -> Dict[str, int]:
    """
    Get git diff statistics for a project.

    Args:
        project_dir: Path to the project directory
        initial_commit: Optional initial commit to diff from (defaults to HEAD~1)

    Returns:
        Dict with lines_added, lines_removed, files_changed
    """
    try:
        # If no initial commit, try to get the parent of HEAD
        if not initial_commit:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD~1'],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                initial_commit = result.stdout.strip()
            else:
                # Fallback: compare with empty tree for first commit
                initial_commit = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # Empty tree SHA

        # Get diff stats
        result = subprocess.run(
            ['git', 'diff', '--numstat', initial_commit, 'HEAD'],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.warning(f"git diff failed: {result.stderr}")
            return {'lines_added': 0, 'lines_removed': 0, 'files_changed': 0}

        lines_added = 0
        lines_removed = 0
        files_changed = 0

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                try:
                    added = int(parts[0]) if parts[0] != '-' else 0
                    removed = int(parts[1]) if parts[1] != '-' else 0
                    lines_added += added
                    lines_removed += removed
                    files_changed += 1
                except ValueError:
                    continue

        return {
            'lines_added': lines_added,
            'lines_removed': lines_removed,
            'files_changed': files_changed,
        }

    except Exception as e:
        logger.error(f"Failed to get git diff stats: {e}")
        return {'lines_added': 0, 'lines_removed': 0, 'files_changed': 0}


def get_spec_trace_costs(spec_id: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get total costs from Langfuse traces for a spec.

    Uses session_id to group traces by spec.

    Args:
        spec_id: The spec identifier (used as session_id in Langfuse)
        project_id: Optional project ID for filtering

    Returns:
        Dict with total_cost, total_tokens, total_duration_seconds, trace_count
    """
    try:
        # Get Langfuse client
        from analytics.langfuse_integration import get_langfuse_client, is_langfuse_ready

        if not is_langfuse_ready():
            logger.warning("Langfuse not ready, returning zero costs")
            return {
                'total_cost': 0.0,
                'total_tokens': 0,
                'total_duration_seconds': 0.0,
                'trace_count': 0,
                'planning_duration': 0.0,
                'coding_duration': 0.0,
                'qa_duration': 0.0,
            }

        client = get_langfuse_client()
        if not client:
            return {
                'total_cost': 0.0,
                'total_tokens': 0,
                'total_duration_seconds': 0.0,
                'trace_count': 0,
            }

        # Fetch traces for this spec
        # Note: We use session_id = spec_id in trace_context()
        response = client.api.trace.list(limit=100)

        total_cost = 0.0
        total_tokens = 0
        total_duration_ms = 0.0
        trace_count = 0
        planning_duration = 0.0
        coding_duration = 0.0
        qa_duration = 0.0

        for trace in response.data:
            # Check if this trace belongs to the spec
            session_id = getattr(trace, 'session_id', None)
            metadata = getattr(trace, 'metadata', {}) or {}

            # Filter by session_id (spec_id) or metadata.spec_id
            if session_id != spec_id and metadata.get('spec_id') != spec_id:
                continue

            # Filter by project_id if specified
            if project_id:
                user_id = getattr(trace, 'user_id', None)
                if user_id != project_id and metadata.get('project_id') != project_id:
                    continue

            # Accumulate costs
            cost = getattr(trace, 'total_cost', 0) or 0
            latency = getattr(trace, 'latency', 0) or 0  # in ms

            total_cost += cost
            total_duration_ms += latency
            trace_count += 1

            # Count tokens from observations
            observations = getattr(trace, 'observations', []) or []
            for obs in observations:
                usage = getattr(obs, 'usage', None)
                if usage:
                    total_tokens += getattr(usage, 'total', 0) or 0

            # Track duration by agent type
            agent_type = metadata.get('agent_type', '')
            if 'planner' in agent_type.lower():
                planning_duration += latency / 1000  # Convert to seconds
            elif 'coder' in agent_type.lower():
                coding_duration += latency / 1000
            elif 'qa' in agent_type.lower():
                qa_duration += latency / 1000

        return {
            'total_cost': total_cost,
            'total_tokens': total_tokens,
            'total_duration_seconds': total_duration_ms / 1000,
            'trace_count': trace_count,
            'planning_duration': planning_duration,
            'coding_duration': coding_duration,
            'qa_duration': qa_duration,
        }

    except Exception as e:
        logger.error(f"Failed to get spec trace costs: {e}")
        return {
            'total_cost': 0.0,
            'total_tokens': 0,
            'total_duration_seconds': 0.0,
            'trace_count': 0,
        }


def get_last_trace_id_for_spec(spec_id: str, project_id: Optional[str] = None) -> Optional[str]:
    """
    Get the most recent trace ID for a spec.

    ROI scores will be attached to this trace.

    Args:
        spec_id: The spec identifier
        project_id: Optional project ID for filtering

    Returns:
        Trace ID or None
    """
    import time

    try:
        from analytics.langfuse_integration import get_langfuse_client, is_langfuse_ready, flush_langfuse

        if not is_langfuse_ready():
            return None

        client = get_langfuse_client()
        if not client:
            return None

        # Flush to ensure recent traces are available
        flush_langfuse()

        # Small delay to allow trace to be indexed
        time.sleep(0.5)

        response = client.api.trace.list(limit=100)

        latest_trace = None
        latest_time = None

        logger.debug(f"Searching for traces with spec_id={spec_id}, project_id={project_id}")
        logger.debug(f"Found {len(response.data)} traces total")

        for trace in response.data:
            session_id = getattr(trace, 'session_id', None)
            metadata = getattr(trace, 'metadata', {}) or {}
            trace_name = getattr(trace, 'name', '')

            # Filter by spec_id - check multiple locations
            spec_match = (
                session_id == spec_id or
                metadata.get('spec_id') == spec_id or
                f"spec-{spec_id}" in (trace_name or '')
            )

            if not spec_match:
                continue

            # Filter by project_id if specified
            if project_id:
                user_id = getattr(trace, 'user_id', None)
                project_match = (
                    user_id == project_id or
                    metadata.get('project_id') == project_id
                )
                if not project_match:
                    continue

            trace_time = getattr(trace, 'timestamp', None)
            if trace_time:
                if latest_time is None or trace_time > latest_time:
                    latest_time = trace_time
                    latest_trace = trace.id

        if latest_trace:
            logger.info(f"Found trace {latest_trace} for spec {spec_id}")
        else:
            logger.warning(f"No trace found for spec {spec_id}")

        return latest_trace

    except Exception as e:
        logger.error(f"Failed to get last trace ID: {e}")
        return None


# =============================================================================
# Main Publisher Function
# =============================================================================


async def publish_roi_scores(
    spec_id: str,
    project_dir: Path,
    qa_attempts: int = 0,
    qa_passed: bool = False,
    initial_commit: Optional[str] = None,
    hourly_rate: float = 150.0,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate and publish ROI scores to Langfuse.

    This function:
    1. Gets git diff stats (lines added/removed, files changed)
    2. Gets trace costs from Langfuse for the spec
    3. Calculates ROI using the hybrid methodology
    4. Saves ROI scores to the most recent trace (or specified trace)

    Args:
        spec_id: The spec identifier
        project_dir: Path to the project directory
        qa_attempts: Number of QA attempts
        qa_passed: Whether QA passed
        initial_commit: Optional initial commit for git diff
        hourly_rate: Developer hourly rate for ROI calculation
        trace_id: Optional trace ID to attach scores to (if known)

    Returns:
        Dict with calculation results and status
    """
    logger.info(f"Publishing ROI scores for spec {spec_id}")

    # Get project_id from project directory name
    project_id = project_dir.name if project_dir else None

    # 1. Get git diff stats
    diff_stats = get_git_diff_stats(project_dir, initial_commit)
    logger.info(f"Git diff stats: +{diff_stats['lines_added']} -{diff_stats['lines_removed']} files={diff_stats['files_changed']}")

    # 2. Get trace costs from Langfuse
    cost_data = get_spec_trace_costs(spec_id, project_id)
    logger.info(f"Trace costs: ${cost_data['total_cost']:.4f}, {cost_data['total_tokens']} tokens")

    # 3. Calculate ROI using ROICalculator
    from analytics.api.roi_calculator import (
        ROICalculator,
        CodeMetrics,
        QAMetrics,
        TimeMetrics,
        CostMetrics,
    )

    code_metrics = CodeMetrics(
        lines_added=diff_stats['lines_added'],
        lines_removed=diff_stats['lines_removed'],
        files_changed=diff_stats['files_changed'],
        complexity="moderate",  # Could be detected from project analysis
    )

    qa_metrics = QAMetrics(
        attempts=qa_attempts,
        passed=qa_passed,
    )

    time_metrics = TimeMetrics(
        total_duration_seconds=cost_data.get('total_duration_seconds', 0),
        planning_duration_seconds=cost_data.get('planning_duration', 0),
        coding_duration_seconds=cost_data.get('coding_duration', 0),
        qa_duration_seconds=cost_data.get('qa_duration', 0),
    )

    cost_metrics = CostMetrics(
        total_tokens=cost_data['total_tokens'],
        total_cost_usd=cost_data['total_cost'],
    )

    calculator = ROICalculator(hourly_rate=hourly_rate)
    roi_result = calculator.calculate(
        code_metrics=code_metrics,
        qa_metrics=qa_metrics,
        time_metrics=time_metrics,
        cost_metrics=cost_metrics,
    )

    logger.info(f"ROI calculated: {roi_result.roi_percentage:.1f}%, Business Value: ${roi_result.business_value_usd:.2f}")

    # 4. Get trace ID - use provided trace_id or search for it
    if not trace_id:
        trace_id = get_last_trace_id_for_spec(spec_id, project_id)

    if not trace_id:
        logger.warning(f"No trace found for spec {spec_id}, creating standalone scores")
        # We'll still return the calculated values
        return {
            'success': False,
            'error': 'No trace found for spec',
            'roi_percentage': roi_result.roi_percentage,
            'business_value_usd': roi_result.business_value_usd,
            'actual_cost_usd': roi_result.actual_cost_usd,
            'dev_hours_saved': roi_result.dev_hours_saved,
            'lines_added': diff_stats['lines_added'],
            'lines_removed': diff_stats['lines_removed'],
            'files_changed': diff_stats['files_changed'],
            'qa_attempts': qa_attempts,
            'qa_passed': qa_passed,
            'confidence_score': roi_result.confidence_score,
        }

    # 5. Save ROI scores to Langfuse
    from analytics.langfuse_integration import save_roi_scores, ROIScores, flush_langfuse

    roi_scores = ROIScores(
        roi_percentage=roi_result.roi_percentage,
        business_value_usd=roi_result.business_value_usd,
        actual_cost_usd=roi_result.actual_cost_usd,
        dev_hours_saved=roi_result.dev_hours_saved,
        lines_added=diff_stats['lines_added'],
        lines_removed=diff_stats['lines_removed'],
        files_changed=diff_stats['files_changed'],
        qa_attempts=qa_attempts,
        qa_passed=qa_passed,
        confidence_score=roi_result.confidence_score,
        quality_multiplier=roi_result.quality_multiplier,
        estimation_method=roi_result.estimation_method,
    )

    success = save_roi_scores(trace_id, roi_scores)
    flush_langfuse()

    if success:
        logger.info(f"ROI scores saved to trace {trace_id}")
    else:
        logger.error(f"Failed to save ROI scores to trace {trace_id}")

    return {
        'success': success,
        'trace_id': trace_id,
        'roi_percentage': roi_result.roi_percentage,
        'business_value_usd': roi_result.business_value_usd,
        'actual_cost_usd': roi_result.actual_cost_usd,
        'dev_hours_saved': roi_result.dev_hours_saved,
        'lines_added': diff_stats['lines_added'],
        'lines_removed': diff_stats['lines_removed'],
        'files_changed': diff_stats['files_changed'],
        'qa_attempts': qa_attempts,
        'qa_passed': qa_passed,
        'confidence_score': roi_result.confidence_score,
        'quality_multiplier': roi_result.quality_multiplier,
    }


# =============================================================================
# Convenience Functions
# =============================================================================


async def publish_roi_on_qa_completion(
    spec_id: str,
    spec_dir: Path,
    project_dir: Path,
    qa_attempts: int,
    qa_passed: bool,
    initial_commit: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to publish ROI after QA completes.

    This is the main entry point for integration with qa/loop.py.

    Args:
        spec_id: The spec identifier
        spec_dir: Path to the spec directory
        project_dir: Path to the project directory
        qa_attempts: Number of QA attempts
        qa_passed: Whether QA passed
        initial_commit: Optional initial commit for git diff

    Returns:
        Dict with calculation results
    """
    return await publish_roi_scores(
        spec_id=spec_id,
        project_dir=project_dir,
        qa_attempts=qa_attempts,
        qa_passed=qa_passed,
        initial_commit=initial_commit,
    )


def create_roi_summary_trace(
    project_id: str,
    spec_ids: List[str],
    total_roi: float,
    total_business_value: float,
    total_cost: float,
) -> Optional[str]:
    """
    Create a summary trace with aggregated ROI for multiple specs.

    Useful for project-level ROI reporting.

    Args:
        project_id: Project identifier
        spec_ids: List of spec IDs included
        total_roi: Total ROI percentage
        total_business_value: Total business value
        total_cost: Total actual cost

    Returns:
        Trace ID if successful
    """
    try:
        from analytics.langfuse_integration import (
            get_langfuse_client,
            is_langfuse_ready,
            flush_langfuse,
        )

        if not is_langfuse_ready():
            return None

        client = get_langfuse_client()
        if not client:
            return None

        # Create a summary span
        span_cm = client.start_as_current_span(
            name=f"roi-summary-{project_id}",
            metadata={
                "project_id": project_id,
                "spec_ids": spec_ids,
                "type": "roi_summary",
            },
            input={"spec_count": len(spec_ids)},
        )
        span = span_cm.__enter__()

        # Get trace ID
        trace_id = client.get_current_trace_id()

        # Update trace with summary data
        client.update_current_trace(
            name=f"ROI Summary: {project_id}",
            user_id=project_id,
            tags=["roi", "summary", f"project:{project_id}"],
            output={
                "total_roi_percentage": total_roi,
                "total_business_value_usd": total_business_value,
                "total_actual_cost_usd": total_cost,
                "spec_count": len(spec_ids),
            },
        )

        # Save aggregate scores
        if trace_id:
            client.create_score(trace_id=trace_id, name="total_roi_percentage", value=total_roi)
            client.create_score(trace_id=trace_id, name="total_business_value_usd", value=total_business_value)
            client.create_score(trace_id=trace_id, name="total_actual_cost_usd", value=total_cost)
            client.create_score(trace_id=trace_id, name="spec_count", value=float(len(spec_ids)))

        span_cm.__exit__(None, None, None)
        flush_langfuse()

        return trace_id

    except Exception as e:
        logger.error(f"Failed to create ROI summary trace: {e}")
        return None
