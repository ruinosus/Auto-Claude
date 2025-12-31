"""
Unified ROI Publisher
======================

Publishes ROI scores to Langfuse for any Auto-Claude feature.
This module provides a simple API for all runners to publish their ROI.

Usage:
    from analytics.roi_publisher import publish_feature_roi, FeatureROIData

    # After ideation completes:
    await publish_feature_roi(
        feature_type="ideation_security",
        project_id="my-project",
        cost_usd=0.05,
        tokens=1000,
        metrics={
            "ideas_generated": 5,
            "high_impact_ideas": 2,
        },
        trace_id=langfuse_trace_id,  # Optional
    )
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)

# Import Langfuse integration
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        is_langfuse_ready,
        get_langfuse_client,
        flush_langfuse,
        trace_context,
    )
    LANGFUSE_AVAILABLE = True
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    _langfuse_init_result = False

# Import ROI calculator
from .unified_roi_calculator import UnifiedROICalculator
from .roi_model import FeatureType, ValueType, UnifiedROI


@dataclass
class FeatureROIData:
    """Data structure for publishing ROI."""
    feature_type: str
    project_id: str
    cost_usd: float
    tokens: int
    duration_seconds: float = 0.0
    model: str = ""
    spec_id: Optional[str] = None
    trace_id: Optional[str] = None

    # Feature-specific metrics (varies by feature type)
    metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}


def _get_feature_type(feature_type_str: str) -> FeatureType:
    """Convert string to FeatureType enum."""
    # Try exact match first
    for ft in FeatureType:
        if ft.value == feature_type_str:
            return ft

    # Try partial match
    lower = feature_type_str.lower()
    if "ideation" in lower:
        if "security" in lower:
            return FeatureType.IDEATION_SECURITY
        elif "performance" in lower:
            return FeatureType.IDEATION_PERFORMANCE
        elif "code" in lower and "quality" in lower:
            return FeatureType.IDEATION_QUALITY
        elif "code" in lower:
            return FeatureType.IDEATION_CODE
        elif "doc" in lower:
            return FeatureType.IDEATION_DOCUMENTATION
        elif "ui" in lower or "ux" in lower:
            return FeatureType.IDEATION_UI_UX
    elif "roadmap" in lower:
        if "competitor" in lower:
            return FeatureType.ROADMAP_COMPETITOR
        elif "discovery" in lower:
            return FeatureType.ROADMAP_DISCOVERY
        else:
            return FeatureType.ROADMAP_FEATURES
    elif "spec" in lower:
        if "gatherer" in lower:
            return FeatureType.SPEC_GATHERER
        elif "researcher" in lower:
            return FeatureType.SPEC_RESEARCHER
        elif "writer" in lower:
            return FeatureType.SPEC_WRITER
        elif "critic" in lower:
            return FeatureType.SPEC_CRITIC
    elif "github" in lower or "pr" in lower or "issue" in lower:
        if "pr" in lower or "review" in lower:
            return FeatureType.GITHUB_PR_REVIEW
        elif "batch" in lower:
            return FeatureType.GITHUB_BATCH_ISSUES
        else:
            return FeatureType.GITHUB_ISSUE_TRIAGE
    elif "insight" in lower or "chat" in lower:
        return FeatureType.INSIGHTS_CHAT
    elif "planner" in lower:
        return FeatureType.BUILD_PLANNER
    elif "coder" in lower:
        return FeatureType.BUILD_CODER
    elif "qa" in lower:
        if "fixer" in lower:
            return FeatureType.BUILD_QA_FIXER
        else:
            return FeatureType.BUILD_QA_REVIEWER

    return FeatureType.OTHER


async def publish_feature_roi(
    feature_type: str,
    project_id: str,
    cost_usd: float,
    tokens: int,
    metrics: Dict[str, Any],
    duration_seconds: float = 0.0,
    model: str = "",
    spec_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    hourly_rate: float = 150.0,
) -> Dict[str, Any]:
    """
    Calculate and publish ROI for any feature type.

    Args:
        feature_type: Type of feature (e.g., "ideation_security", "roadmap_features")
        project_id: Project identifier
        cost_usd: Cost of the feature execution
        tokens: Tokens used
        metrics: Feature-specific metrics dict
        duration_seconds: Execution duration
        model: Model used
        spec_id: Optional spec ID
        trace_id: Optional Langfuse trace ID
        hourly_rate: Developer hourly rate for calculations

    Returns:
        Dict with ROI calculation results
    """
    logger.info(f"Publishing ROI for {feature_type} in project {project_id}")

    # Convert feature type
    ft = _get_feature_type(feature_type)
    calculator = UnifiedROICalculator(hourly_rate=hourly_rate)

    # Calculate ROI based on feature type
    roi: Optional[UnifiedROI] = None

    if ft.value.startswith("ideation"):
        roi = calculator.calculate_ideation_roi(
            feature_type=ft,
            ideas_generated=metrics.get("ideas_generated", 0),
            high_impact_ideas=metrics.get("high_impact_ideas", 0),
            ideas_implemented=metrics.get("ideas_implemented", 0),
            cost_usd=cost_usd,
            tokens=tokens,
            duration_seconds=duration_seconds,
            model=model,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
            categories=metrics.get("categories", []),
        )

    elif ft.value.startswith("roadmap"):
        roi = calculator.calculate_roadmap_roi(
            features_identified=metrics.get("features_identified", 0),
            features_prioritized=metrics.get("features_prioritized", 0),
            features_rejected=metrics.get("features_rejected", 0),
            competitor_insights=metrics.get("competitor_insights", 0),
            cost_usd=cost_usd,
            tokens=tokens,
            duration_seconds=duration_seconds,
            model=model,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
        )

    elif ft.value.startswith("spec"):
        roi = calculator.calculate_spec_roi(
            phases_completed=metrics.get("phases_completed", 0),
            requirements_gathered=metrics.get("requirements_gathered", 0),
            complexity_level=metrics.get("complexity_level", "standard"),
            refinement_iterations=metrics.get("refinement_iterations", 0),
            cost_usd=cost_usd,
            tokens=tokens,
            duration_seconds=duration_seconds,
            model=model,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
        )

    elif ft.value.startswith("build"):
        roi = calculator.calculate_build_roi(
            lines_added=metrics.get("lines_added", 0),
            lines_removed=metrics.get("lines_removed", 0),
            files_changed=metrics.get("files_changed", 0),
            qa_attempts=metrics.get("qa_attempts", 0),
            qa_passed=metrics.get("qa_passed", False),
            subtasks_completed=metrics.get("subtasks_completed", 0),
            subtasks_total=metrics.get("subtasks_total", 0),
            cost_usd=cost_usd,
            tokens=tokens,
            duration_seconds=duration_seconds,
            model=model,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
        )

    elif ft.value.startswith("github"):
        roi = calculator.calculate_github_roi(
            prs_reviewed=metrics.get("prs_reviewed", 0),
            issues_triaged=metrics.get("issues_triaged", 0),
            issues_auto_fixed=metrics.get("issues_auto_fixed", 0),
            duplicates_detected=metrics.get("duplicates_detected", 0),
            spam_detected=metrics.get("spam_detected", 0),
            cost_usd=cost_usd,
            tokens=tokens,
            duration_seconds=duration_seconds,
            model=model,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
        )

    elif ft.value.startswith("insight"):
        roi = calculator.calculate_insights_roi(
            messages_exchanged=metrics.get("messages_exchanged", 0),
            tasks_suggested=metrics.get("tasks_suggested", 0),
            tasks_accepted=metrics.get("tasks_accepted", 0),
            files_explored=metrics.get("files_explored", 0),
            cost_usd=cost_usd,
            tokens=tokens,
            duration_seconds=duration_seconds,
            model=model,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
        )

    if roi is None:
        logger.warning(f"No ROI calculator for feature type: {feature_type}")
        return {
            "success": False,
            "error": f"Unknown feature type: {feature_type}",
        }

    # Publish to Langfuse if available
    success = await _publish_to_langfuse(roi, trace_id)

    # Return result
    return {
        "success": success,
        "trace_id": trace_id,
        "feature_type": ft.value,
        "roi_percentage": roi.roi_percentage,
        "total_value_usd": roi.total_value_usd,
        "total_cost_usd": roi.cost.total_cost_usd,
        "net_value_usd": roi.total_value_usd - roi.cost.total_cost_usd,
        "confidence_score": roi.confidence_score,
        "value_breakdown": {vt.value: v for vt, v in roi.value_breakdown.items()},
    }


async def _publish_to_langfuse(roi: UnifiedROI, trace_id: Optional[str] = None) -> bool:
    """Publish ROI scores to Langfuse.

    If no trace_id is provided, creates a dedicated ROI trace using trace_context.
    """
    if not LANGFUSE_AVAILABLE or not is_langfuse_ready():
        logger.warning("Langfuse not available, skipping ROI publish")
        return False

    try:
        client = get_langfuse_client()
        if not client:
            logger.warning("No Langfuse client available")
            return False

        ctx = None
        ctx_obj = None
        created_trace = False

        # If no trace_id provided, create a dedicated ROI trace using trace_context
        if not trace_id:
            trace_name = f"roi-{roi.feature_type.value}-{roi.project_id or 'unknown'}"
            # Use trace_context which uses Langfuse SDK v3 API correctly
            ctx = trace_context(
                name=trace_name,
                spec_id=roi.spec_id,
                project_id=roi.project_id,
                agent_type=f"roi_{roi.feature_type.value}",
                metadata={
                    "feature_type": roi.feature_type.value,
                    "roi_calculation": True,
                },
                tags=[
                    f"feature:{roi.feature_type.value}",
                    "roi",
                ],
                input_data={
                    "feature_type": roi.feature_type.value,
                    "cost_usd": roi.cost.total_cost_usd,
                    "total_tokens": roi.cost.total_tokens,
                },
            )
            ctx_obj = ctx.__enter__()
            if ctx_obj:
                trace_id = ctx_obj.trace_id
                created_trace = True
                logger.info(f"Created ROI trace via trace_context: {trace_id}")
            else:
                logger.warning("Failed to create ROI trace - trace_context returned None")
                ctx.__exit__(None, None, None)
                return False

        # Get scores to publish
        scores = roi.to_langfuse_scores()

        # Publish each score using create_score (Langfuse SDK v3 API)
        for name, value in scores.items():
            try:
                client.create_score(
                    trace_id=trace_id,
                    name=name,
                    value=value,
                    comment=f"Auto-calculated by unified ROI system for {roi.feature_type.value}",
                )
            except Exception as e:
                logger.error(f"Failed to publish score {name}: {e}")

        # Close trace context if we created one
        if created_trace and ctx_obj and ctx:
            ctx_obj.set_output({
                "roi_percentage": roi.roi_percentage,
                "total_value_usd": roi.total_value_usd,
                "net_value_usd": roi.total_value_usd - roi.cost.total_cost_usd,
                "scores_published": len(scores),
            })
            ctx.__exit__(None, None, None)

        # Flush to ensure scores are sent
        flush_langfuse()
        logger.info(f"Published {len(scores)} ROI scores to trace {trace_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to publish ROI to Langfuse: {e}")
        return False


async def publish_ideation_roi(
    project_id: str,
    ideation_type: str,
    ideas_generated: int,
    high_impact_ideas: int,
    cost_usd: float,
    tokens: int,
    trace_id: Optional[str] = None,
    duration_seconds: float = 0.0,
    model: str = "",
) -> Dict[str, Any]:
    """Convenience function for ideation ROI."""
    return await publish_feature_roi(
        feature_type=f"ideation_{ideation_type}",
        project_id=project_id,
        cost_usd=cost_usd,
        tokens=tokens,
        metrics={
            "ideas_generated": ideas_generated,
            "high_impact_ideas": high_impact_ideas,
        },
        duration_seconds=duration_seconds,
        model=model,
        trace_id=trace_id,
    )


async def publish_roadmap_roi(
    project_id: str,
    features_identified: int,
    features_rejected: int = 0,
    cost_usd: float = 0.0,
    tokens: int = 0,
    trace_id: Optional[str] = None,
    duration_seconds: float = 0.0,
    model: str = "",
) -> Dict[str, Any]:
    """Convenience function for roadmap ROI."""
    return await publish_feature_roi(
        feature_type="roadmap_features",
        project_id=project_id,
        cost_usd=cost_usd,
        tokens=tokens,
        metrics={
            "features_identified": features_identified,
            "features_rejected": features_rejected,
        },
        duration_seconds=duration_seconds,
        model=model,
        trace_id=trace_id,
    )


async def publish_github_roi(
    project_id: str,
    prs_reviewed: int = 0,
    issues_triaged: int = 0,
    issues_auto_fixed: int = 0,
    cost_usd: float = 0.0,
    tokens: int = 0,
    trace_id: Optional[str] = None,
    duration_seconds: float = 0.0,
    model: str = "",
) -> Dict[str, Any]:
    """Convenience function for GitHub automation ROI."""
    return await publish_feature_roi(
        feature_type="github_pr_review" if prs_reviewed > 0 else "github_issue_triage",
        project_id=project_id,
        cost_usd=cost_usd,
        tokens=tokens,
        metrics={
            "prs_reviewed": prs_reviewed,
            "issues_triaged": issues_triaged,
            "issues_auto_fixed": issues_auto_fixed,
        },
        duration_seconds=duration_seconds,
        model=model,
        trace_id=trace_id,
    )


async def publish_insights_roi(
    project_id: str,
    messages_exchanged: int,
    tasks_suggested: int = 0,
    tasks_accepted: int = 0,
    files_explored: int = 0,
    cost_usd: float = 0.0,
    tokens: int = 0,
    trace_id: Optional[str] = None,
    duration_seconds: float = 0.0,
    model: str = "",
) -> Dict[str, Any]:
    """Convenience function for insights chat ROI."""
    return await publish_feature_roi(
        feature_type="insights_chat",
        project_id=project_id,
        cost_usd=cost_usd,
        tokens=tokens,
        metrics={
            "messages_exchanged": messages_exchanged,
            "tasks_suggested": tasks_suggested,
            "tasks_accepted": tasks_accepted,
            "files_explored": files_explored,
        },
        duration_seconds=duration_seconds,
        model=model,
        trace_id=trace_id,
    )
