"""
ROI Calculator
==============

Calculates Return on Investment for agent sessions.
Based on the unified_roi_calculator pattern from the main analytics module.

ROI Formula:
    ROI = (Total Value Generated - Total Cost) / Total Cost * 100

Value Sources:
    - Artifacts created (from value_engine)
    - Time saved (estimated from task complexity)
    - Errors prevented (from gotchas, security findings)

Cost Sources:
    - Token usage (from Langfuse or SDK)
    - API costs (calculated from token counts)

Output:
    - ROI percentage
    - Value breakdown by dimension
    - Cost breakdown by model
    - Confidence score
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .value_engine import ValueAttribution, get_artifact_value
from .storage import list_artifacts

logger = logging.getLogger(__name__)


# =============================================================================
# Cost Configuration
# =============================================================================

# Token costs per model (USD per 1M tokens) - as of 2024
MODEL_COSTS = {
    # Claude models
    "claude-opus-4-5-20251101": {"input": 15.0, "output": 75.0},
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    # Legacy models
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku-20241022": {"input": 1.0, "output": 5.0},
    # Default fallback
    "default": {"input": 3.0, "output": 15.0},
}


def get_token_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for token usage."""
    costs = MODEL_COSTS.get(model, MODEL_COSTS["default"])
    input_cost = (input_tokens / 1_000_000) * costs["input"]
    output_cost = (output_tokens / 1_000_000) * costs["output"]
    return input_cost + output_cost


# =============================================================================
# Time Value Configuration
# =============================================================================

# Hourly rate for developer time (USD)
DEVELOPER_HOURLY_RATE = float(os.environ.get("DEVELOPER_HOURLY_RATE", "150"))

# Time saved estimates by artifact type (minutes)
TIME_SAVED_ESTIMATES = {
    "diagram": 60,              # 1 hour to create a good diagram
    "mermaid_diagram": 45,
    "ascii_diagram": 30,
    "pattern_discovered": 120,  # 2 hours of research
    "gotcha_identified": 90,    # 1.5 hours of debugging
    "security_finding": 180,    # 3 hours of security audit
    "recommendation": 30,
    "code_snippet": 20,
    "code_explanation": 15,
    "file_insight": 10,
    "lesson_learned": 45,
    "best_practice": 30,
    "generic": 15,
    "unknown": 10,
}


def estimate_time_saved(artifact_type: str) -> float:
    """Estimate time saved in minutes for an artifact type."""
    return TIME_SAVED_ESTIMATES.get(artifact_type, 10)


def time_to_usd(minutes: float) -> float:
    """Convert time saved to USD value."""
    hours = minutes / 60
    return hours * DEVELOPER_HOURLY_RATE


# =============================================================================
# ROI Data Structures
# =============================================================================

@dataclass
class CostBreakdown:
    """Breakdown of costs by model and type."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_usage(self, model: str, input_tokens: int, output_tokens: int):
        """Add token usage for a model."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens += input_tokens + output_tokens

        cost = get_token_cost(model, input_tokens, output_tokens)
        costs = MODEL_COSTS.get(model, MODEL_COSTS["default"])
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]

        self.input_cost_usd += input_cost
        self.output_cost_usd += output_cost
        self.total_cost_usd += cost

        if model not in self.by_model:
            self.by_model[model] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            }
        self.by_model[model]["input_tokens"] += input_tokens
        self.by_model[model]["output_tokens"] += output_tokens
        self.by_model[model]["cost_usd"] += cost

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "input_cost_usd": round(self.input_cost_usd, 4),
            "output_cost_usd": round(self.output_cost_usd, 4),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "by_model": self.by_model,
        }


@dataclass
class ROIResult:
    """Complete ROI calculation result."""
    # Value metrics
    artifact_value_usd: float = 0.0
    time_saved_value_usd: float = 0.0
    total_value_usd: float = 0.0

    # Cost metrics
    total_cost_usd: float = 0.0

    # ROI calculation
    net_value_usd: float = 0.0
    roi_percentage: float = 0.0

    # Attribution breakdown
    value_attribution: Optional[ValueAttribution] = None
    cost_breakdown: Optional[CostBreakdown] = None

    # Metadata
    confidence_score: float = 0.7
    artifact_count: int = 0
    time_saved_minutes: float = 0.0
    calculated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": {
                "artifact_value_usd": round(self.artifact_value_usd, 2),
                "time_saved_value_usd": round(self.time_saved_value_usd, 2),
                "total_value_usd": round(self.total_value_usd, 2),
            },
            "cost": {
                "total_cost_usd": round(self.total_cost_usd, 4),
                "breakdown": self.cost_breakdown.to_dict() if self.cost_breakdown else {},
            },
            "roi": {
                "net_value_usd": round(self.net_value_usd, 2),
                "roi_percentage": round(self.roi_percentage, 1),
            },
            "attribution": self.value_attribution.to_dict() if self.value_attribution else {},
            "metadata": {
                "confidence_score": round(self.confidence_score, 3),
                "artifact_count": self.artifact_count,
                "time_saved_minutes": round(self.time_saved_minutes, 1),
                "calculated_at": self.calculated_at,
            },
        }


# =============================================================================
# ROI Calculation Functions
# =============================================================================

def calculate_session_roi(
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    project_dir: Optional[str] = None,
    token_usage: Optional[Dict[str, Any]] = None,
) -> ROIResult:
    """
    Calculate ROI for a session based on artifacts and token usage.

    Args:
        trace_id: Langfuse trace ID to filter artifacts
        spec_id: Spec ID to filter artifacts
        project_dir: Project directory for artifact lookup
        token_usage: Token usage data from SDK or Langfuse
            Expected format: {"model": str, "input_tokens": int, "output_tokens": int}
            Or list of such dicts for multiple models

    Returns:
        ROIResult with complete breakdown
    """
    result = ROIResult()
    result.value_attribution = ValueAttribution()
    result.cost_breakdown = CostBreakdown()

    # ===========================================
    # 1. Calculate artifact value
    # ===========================================
    artifacts = list_artifacts(
        trace_id=trace_id,
        spec_id=spec_id,
        project_dir=project_dir,
        include_content=False,  # Don't need content for ROI
    )

    result.artifact_count = len(artifacts)

    for artifact in artifacts:
        artifact_type = artifact.get("type", "unknown")
        agent_type = artifact.get("agent_type", "unknown")
        artifact_value = artifact.get("value_usd", 0)

        # Add to value attribution
        value_info = get_artifact_value(artifact_type, agent_type)
        result.value_attribution.add_artifact(value_info)

        # Use stored value or calculated
        result.artifact_value_usd += artifact_value or value_info["adjusted_value_usd"]

        # Calculate time saved
        time_saved = estimate_time_saved(artifact_type)
        result.time_saved_minutes += time_saved

    # Convert time saved to USD
    result.time_saved_value_usd = time_to_usd(result.time_saved_minutes)

    # Total value
    result.total_value_usd = result.artifact_value_usd + result.time_saved_value_usd

    # ===========================================
    # 2. Calculate costs
    # ===========================================
    if token_usage:
        if isinstance(token_usage, list):
            for usage in token_usage:
                result.cost_breakdown.add_usage(
                    model=usage.get("model", "default"),
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                )
        elif isinstance(token_usage, dict):
            result.cost_breakdown.add_usage(
                model=token_usage.get("model", "default"),
                input_tokens=token_usage.get("input_tokens", 0),
                output_tokens=token_usage.get("output_tokens", 0),
            )

    result.total_cost_usd = result.cost_breakdown.total_cost_usd

    # ===========================================
    # 3. Calculate ROI
    # ===========================================
    result.net_value_usd = result.total_value_usd - result.total_cost_usd

    if result.total_cost_usd > 0:
        result.roi_percentage = (result.net_value_usd / result.total_cost_usd) * 100
    else:
        # No cost means infinite ROI (cap at 1000%)
        result.roi_percentage = 1000.0 if result.total_value_usd > 0 else 0.0

    # ===========================================
    # 4. Calculate confidence
    # ===========================================
    # Confidence based on artifact count and value attribution confidence
    if result.artifact_count == 0:
        result.confidence_score = 0.5  # Low confidence with no artifacts
    elif result.value_attribution:
        result.confidence_score = result.value_attribution.confidence_score
    else:
        result.confidence_score = 0.7

    logger.info(
        f"ROI calculated: {result.roi_percentage:.1f}% "
        f"(value=${result.total_value_usd:.2f}, cost=${result.total_cost_usd:.4f})"
    )

    return result


def calculate_artifact_roi(
    artifact: Dict[str, Any],
    token_usage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calculate ROI for a single artifact.

    Useful for understanding the value of individual artifacts.
    """
    artifact_type = artifact.get("type", "unknown")
    agent_type = artifact.get("agent_type", "unknown")
    artifact_value = artifact.get("value_usd", 0)

    # Get value info
    value_info = get_artifact_value(artifact_type, agent_type)
    value = artifact_value or value_info["adjusted_value_usd"]

    # Time saved value
    time_saved = estimate_time_saved(artifact_type)
    time_value = time_to_usd(time_saved)

    total_value = value + time_value

    # Calculate cost if provided
    cost = 0.0
    if token_usage:
        cost = get_token_cost(
            model=token_usage.get("model", "default"),
            input_tokens=token_usage.get("input_tokens", 0),
            output_tokens=token_usage.get("output_tokens", 0),
        )

    net_value = total_value - cost
    roi_percentage = (net_value / cost * 100) if cost > 0 else 1000.0

    return {
        "artifact_id": artifact.get("id"),
        "artifact_type": artifact_type,
        "value_usd": round(value, 2),
        "time_saved_value_usd": round(time_value, 2),
        "total_value_usd": round(total_value, 2),
        "cost_usd": round(cost, 4),
        "net_value_usd": round(net_value, 2),
        "roi_percentage": round(roi_percentage, 1),
        "confidence": value_info["confidence"],
    }


def get_roi_summary(
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    project_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get a summary of ROI for publishing to Langfuse.

    Returns a compact dict suitable for trace output.
    """
    result = calculate_session_roi(
        trace_id=trace_id,
        spec_id=spec_id,
        project_dir=project_dir,
    )

    return {
        "roi_percentage": round(result.roi_percentage, 1),
        "net_value_usd": round(result.net_value_usd, 2),
        "artifact_count": result.artifact_count,
        "confidence": round(result.confidence_score, 3),
        "breakdown": {
            "execution": round(result.value_attribution.execution_value, 2) if result.value_attribution else 0,
            "decision": round(result.value_attribution.decision_value, 2) if result.value_attribution else 0,
            "prevention": round(result.value_attribution.prevention_value, 2) if result.value_attribution else 0,
            "knowledge": round(result.value_attribution.knowledge_value, 2) if result.value_attribution else 0,
        },
    }
