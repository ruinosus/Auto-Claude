"""
ROI Calculator
==============

Implements the hybrid ROI calculation methodology.
Combines lines-based and time-based estimation with quality adjustments.

Formula:
  ROI = ((Business Value - Actual Cost) / Actual Cost) × 100

Business Value Calculation (Hybrid Method):
  - 40% weight: Lines-based estimation
  - 60% weight: Time-based estimation (Claude Agent SDK timing)
  - Quality multiplier based on QA results
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Developer hourly rates for ROI calculation
DEFAULT_HOURLY_RATE = 150.0  # USD/hour for senior developer
JUNIOR_HOURLY_RATE = 75.0
SENIOR_HOURLY_RATE = 150.0
STAFF_HOURLY_RATE = 200.0

# Lines of code estimation factors
LINES_PER_HOUR_SIMPLE = 50  # Simple/boilerplate code
LINES_PER_HOUR_MODERATE = 25  # Moderate complexity
LINES_PER_HOUR_COMPLEX = 10  # Complex/algorithmic code

# Hybrid method weights
LINES_WEIGHT = 0.40
TIME_WEIGHT = 0.60

# Quality multipliers
QA_PASS_FIRST_ATTEMPT_MULTIPLIER = 1.2
QA_PASS_SECOND_ATTEMPT_MULTIPLIER = 1.1
QA_PASS_THIRD_PLUS_MULTIPLIER = 1.0
QA_FAIL_MULTIPLIER = 0.8

# Complexity adjustments
COMPLEXITY_SIMPLE = 0.8
COMPLEXITY_MODERATE = 1.0
COMPLEXITY_COMPLEX = 1.3


@dataclass
class CodeMetrics:
    """Metrics about code changes."""
    lines_added: int = 0
    lines_removed: int = 0
    files_changed: int = 0
    complexity: str = "moderate"  # simple, moderate, complex


@dataclass
class QAMetrics:
    """Metrics about QA validation."""
    attempts: int = 0
    passed: bool = False
    issues_found: int = 0
    issues_fixed: int = 0


@dataclass
class TimeMetrics:
    """Timing metrics from Claude Agent SDK."""
    total_duration_seconds: float = 0.0
    planning_duration_seconds: float = 0.0
    coding_duration_seconds: float = 0.0
    qa_duration_seconds: float = 0.0


@dataclass
class CostMetrics:
    """Cost metrics from Langfuse."""
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ROIResult:
    """Complete ROI calculation result."""
    roi_percentage: float
    business_value_usd: float
    actual_cost_usd: float
    dev_hours_saved: float
    confidence_score: float
    quality_multiplier: float
    estimation_method: str
    # Breakdown
    lines_based_value: float
    time_based_value: float
    # Input metrics
    code_metrics: CodeMetrics
    qa_metrics: QAMetrics
    time_metrics: TimeMetrics
    cost_metrics: CostMetrics


class ROICalculator:
    """
    Calculates ROI using hybrid methodology.

    Combines multiple estimation approaches:
    1. Lines-based: Estimates dev time from code changes
    2. Time-based: Uses actual AI execution time as proxy
    3. Quality adjustment: Adjusts based on QA results
    """

    def __init__(
        self,
        hourly_rate: float = DEFAULT_HOURLY_RATE,
        lines_weight: float = LINES_WEIGHT,
        time_weight: float = TIME_WEIGHT,
    ):
        self.hourly_rate = hourly_rate
        self.lines_weight = lines_weight
        self.time_weight = time_weight

    def calculate(
        self,
        code_metrics: CodeMetrics,
        qa_metrics: QAMetrics,
        time_metrics: TimeMetrics,
        cost_metrics: CostMetrics,
    ) -> ROIResult:
        """
        Calculate ROI using hybrid methodology.

        Args:
            code_metrics: Lines of code and file changes
            qa_metrics: QA validation results
            time_metrics: Timing from agent sessions
            cost_metrics: Token costs from Langfuse

        Returns:
            ROIResult with full breakdown
        """
        # 1. Calculate lines-based estimate
        lines_based_hours = self._estimate_hours_from_lines(code_metrics)
        lines_based_value = lines_based_hours * self.hourly_rate

        # 2. Calculate time-based estimate
        time_based_hours = self._estimate_hours_from_time(time_metrics)
        time_based_value = time_based_hours * self.hourly_rate

        # 3. Calculate quality multiplier
        quality_multiplier = self._calculate_quality_multiplier(qa_metrics)

        # 4. Combine estimates with weights
        raw_business_value = (
            self.lines_weight * lines_based_value +
            self.time_weight * time_based_value
        )

        # 5. Apply quality multiplier
        business_value = raw_business_value * quality_multiplier

        # 6. Get actual cost
        actual_cost = cost_metrics.total_cost_usd

        # 7. Calculate ROI
        if actual_cost > 0:
            roi_percentage = ((business_value - actual_cost) / actual_cost) * 100
        else:
            roi_percentage = 0.0 if business_value == 0 else float('inf')

        # 8. Calculate confidence score
        confidence = self._calculate_confidence(
            code_metrics, qa_metrics, time_metrics
        )

        # 9. Calculate dev hours saved
        dev_hours_saved = (
            self.lines_weight * lines_based_hours +
            self.time_weight * time_based_hours
        ) * quality_multiplier

        return ROIResult(
            roi_percentage=roi_percentage,
            business_value_usd=business_value,
            actual_cost_usd=actual_cost,
            dev_hours_saved=dev_hours_saved,
            confidence_score=confidence,
            quality_multiplier=quality_multiplier,
            estimation_method="hybrid",
            lines_based_value=lines_based_value,
            time_based_value=time_based_value,
            code_metrics=code_metrics,
            qa_metrics=qa_metrics,
            time_metrics=time_metrics,
            cost_metrics=cost_metrics,
        )

    def _estimate_hours_from_lines(self, metrics: CodeMetrics) -> float:
        """
        Estimate developer hours from lines of code.

        Uses complexity-adjusted lines per hour rates.
        """
        total_lines = metrics.lines_added + metrics.lines_removed

        # Select lines per hour based on complexity
        if metrics.complexity == "simple":
            lines_per_hour = LINES_PER_HOUR_SIMPLE
            complexity_factor = COMPLEXITY_SIMPLE
        elif metrics.complexity == "complex":
            lines_per_hour = LINES_PER_HOUR_COMPLEX
            complexity_factor = COMPLEXITY_COMPLEX
        else:
            lines_per_hour = LINES_PER_HOUR_MODERATE
            complexity_factor = COMPLEXITY_MODERATE

        # Base hours from lines
        base_hours = total_lines / lines_per_hour

        # Add file change overhead (context switching)
        file_overhead = metrics.files_changed * 0.1  # 6 min per file

        # Apply complexity factor
        total_hours = (base_hours + file_overhead) * complexity_factor

        return max(0.5, total_hours)  # Minimum 30 minutes

    def _estimate_hours_from_time(self, metrics: TimeMetrics) -> float:
        """
        Estimate developer hours from AI execution time.

        Uses a multiplier since AI typically works faster than humans.
        """
        # AI execution time to human time multiplier
        # AI can typically do in 1 hour what takes a dev 4-8 hours
        AI_TO_HUMAN_MULTIPLIER = 6.0

        total_ai_hours = metrics.total_duration_seconds / 3600.0

        # Apply multiplier to get equivalent human hours
        human_hours = total_ai_hours * AI_TO_HUMAN_MULTIPLIER

        # Adjust for different phases
        # Planning is typically faster for humans relative to AI
        # Coding is where AI has biggest advantage
        if metrics.planning_duration_seconds > 0:
            planning_adjustment = (metrics.planning_duration_seconds / 3600.0) * 2.0
        else:
            planning_adjustment = 0

        if metrics.coding_duration_seconds > 0:
            coding_adjustment = (metrics.coding_duration_seconds / 3600.0) * 8.0
        else:
            coding_adjustment = 0

        if metrics.qa_duration_seconds > 0:
            qa_adjustment = (metrics.qa_duration_seconds / 3600.0) * 4.0
        else:
            qa_adjustment = 0

        # Use phase-specific if available, otherwise use total
        if planning_adjustment or coding_adjustment or qa_adjustment:
            human_hours = planning_adjustment + coding_adjustment + qa_adjustment
        else:
            human_hours = total_ai_hours * AI_TO_HUMAN_MULTIPLIER

        return max(0.5, human_hours)  # Minimum 30 minutes

    def _calculate_quality_multiplier(self, metrics: QAMetrics) -> float:
        """
        Calculate quality adjustment multiplier based on QA results.
        """
        if not metrics.passed:
            return QA_FAIL_MULTIPLIER

        if metrics.attempts == 1:
            return QA_PASS_FIRST_ATTEMPT_MULTIPLIER
        elif metrics.attempts == 2:
            return QA_PASS_SECOND_ATTEMPT_MULTIPLIER
        else:
            return QA_PASS_THIRD_PLUS_MULTIPLIER

    def _calculate_confidence(
        self,
        code_metrics: CodeMetrics,
        qa_metrics: QAMetrics,
        time_metrics: TimeMetrics,
    ) -> float:
        """
        Calculate confidence score for the ROI estimate.

        Higher confidence when:
        - More code changes (better signal)
        - QA passed (validated quality)
        - Reasonable timing data available
        """
        confidence = 0.5  # Base confidence

        # More lines = more confidence (up to 500 lines)
        total_lines = code_metrics.lines_added + code_metrics.lines_removed
        if total_lines > 500:
            confidence += 0.2
        elif total_lines > 100:
            confidence += 0.15
        elif total_lines > 20:
            confidence += 0.1

        # QA passed = higher confidence
        if qa_metrics.passed:
            confidence += 0.15

        # Multiple files changed = more realistic estimate
        if code_metrics.files_changed >= 3:
            confidence += 0.1
        elif code_metrics.files_changed >= 1:
            confidence += 0.05

        # Timing data available = higher confidence
        if time_metrics.total_duration_seconds > 0:
            confidence += 0.1

        return min(1.0, confidence)


def calculate_roi_from_trace_data(
    trace_data: Dict[str, Any],
    scores: Dict[str, float],
    generations: list,
) -> ROIResult:
    """
    Calculate ROI from Langfuse trace data.

    Convenience function that extracts metrics from trace data
    and runs the ROI calculation.

    Args:
        trace_data: Trace metadata and details
        scores: Score values keyed by name
        generations: List of generation records

    Returns:
        ROIResult with full calculation
    """
    # Extract code metrics from scores
    code_metrics = CodeMetrics(
        lines_added=int(scores.get("lines_added", 0)),
        lines_removed=int(scores.get("lines_removed", 0)),
        files_changed=int(scores.get("files_changed", 0)),
        complexity=trace_data.get("metadata", {}).get("complexity", "moderate"),
    )

    # Extract QA metrics
    qa_metrics = QAMetrics(
        attempts=int(scores.get("qa_attempts", 0)),
        passed=scores.get("qa_passed", 0) > 0.5,
        issues_found=int(scores.get("issues_found", 0)),
        issues_fixed=int(scores.get("issues_fixed", 0)),
    )

    # Calculate timing from generations
    total_duration = 0.0
    for gen in generations:
        if hasattr(gen, "latency_ms"):
            total_duration += gen.latency_ms / 1000.0
        elif isinstance(gen, dict) and "latency_ms" in gen:
            total_duration += gen["latency_ms"] / 1000.0

    time_metrics = TimeMetrics(
        total_duration_seconds=total_duration,
    )

    # Extract cost metrics
    total_tokens = 0
    total_cost = 0.0
    for gen in generations:
        if hasattr(gen, "total_tokens"):
            total_tokens += gen.total_tokens
        elif isinstance(gen, dict) and "total_tokens" in gen:
            total_tokens += gen["total_tokens"]

        if hasattr(gen, "cost"):
            total_cost += gen.cost
        elif isinstance(gen, dict) and "cost" in gen:
            total_cost += gen["cost"]

    cost_metrics = CostMetrics(
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
    )

    # Run calculation
    calculator = ROICalculator()
    return calculator.calculate(
        code_metrics=code_metrics,
        qa_metrics=qa_metrics,
        time_metrics=time_metrics,
        cost_metrics=cost_metrics,
    )
