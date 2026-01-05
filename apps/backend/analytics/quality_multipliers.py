"""
Quality Multipliers for ROI Calculation
========================================

This module provides a quality multiplier system that adjusts ROI values
based on QA outcomes and code quality metrics.

Multipliers reward:
- First-pass QA success (high quality code)
- Tests, docs, types (professional practices)
- High code coverage
- Low lint errors

And penalize:
- QA failures
- Multiple QA attempts
- Rework
- High lint error counts

Usage:
    from analytics.quality_multipliers import QualityMultiplierCalculator

    calculator = QualityMultiplierCalculator()
    result = calculator.calculate(
        qa_passed=True,
        qa_attempts=1,
        has_tests=True,
        has_docs=True,
        has_types=True,
        code_coverage=85.0,
        lint_errors=2,
        rework_needed=False,
    )

    # Apply to ROI
    adjusted_value = base_value * result.final_multiplier
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class QualityMultiplier:
    """
    Result of quality multiplier calculation.

    Attributes:
        base_value: Starting multiplier value (always 1.0)
        adjustments: List of (reason, delta) tuples explaining each adjustment
        final_multiplier: The final computed multiplier, clamped to [0.5, 2.0]
    """
    base_value: float = 1.0
    adjustments: List[Tuple[str, float]] = field(default_factory=list)
    final_multiplier: float = 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary for API serialization."""
        return {
            "base_value": self.base_value,
            "adjustments": [
                {"reason": reason, "delta": delta}
                for reason, delta in self.adjustments
            ],
            "final_multiplier": self.final_multiplier,
        }


class QualityMultiplierCalculator:
    """
    Calculator for quality-based ROI multipliers.

    Computes a multiplier that adjusts ROI based on code quality signals.
    The multiplier is clamped to [0.5, 2.0] to prevent extreme values.
    """

    # Multiplier adjustment values
    FIRST_PASS_QA_BONUS = 0.30       # +30% for first-pass QA success
    SECOND_PASS_QA_BONUS = 0.15     # +15% for second-pass QA success
    QA_FAILED_PENALTY = -0.30       # -30% for QA failure

    HAS_TESTS_BONUS = 0.20          # +20% for having tests
    HAS_DOCS_BONUS = 0.10           # +10% for having documentation
    HAS_TYPES_BONUS = 0.10          # +10% for having type annotations

    HIGH_COVERAGE_BONUS = 0.15      # +15% for >= 80% coverage
    MEDIUM_COVERAGE_BONUS = 0.05    # +5% for >= 60% coverage

    MANY_LINT_ERRORS_PENALTY = -0.10  # -10% for > 10 lint errors
    REWORK_PENALTY = -0.20          # -20% for rework needed

    MIN_MULTIPLIER = 0.5
    MAX_MULTIPLIER = 2.0

    def calculate(
        self,
        qa_passed: bool,
        qa_attempts: int = 1,
        has_tests: bool = False,
        has_docs: bool = False,
        has_types: bool = False,
        code_coverage: Optional[float] = None,
        lint_errors: int = 0,
        rework_needed: bool = False,
    ) -> QualityMultiplier:
        """
        Calculate the quality multiplier based on quality signals.

        Args:
            qa_passed: Whether QA passed
            qa_attempts: Number of QA attempts (1 = first-pass)
            has_tests: Whether the code includes tests
            has_docs: Whether the code includes documentation
            has_types: Whether the code includes type annotations
            code_coverage: Code coverage percentage (0-100), None if unknown
            lint_errors: Number of lint errors
            rework_needed: Whether rework was flagged

        Returns:
            QualityMultiplier with adjustments and final value
        """
        result = QualityMultiplier(base_value=1.0, adjustments=[])
        current_value = 1.0

        # QA outcome adjustments
        if qa_passed:
            if qa_attempts <= 1:
                result.adjustments.append(("First-pass QA success", self.FIRST_PASS_QA_BONUS))
                current_value += self.FIRST_PASS_QA_BONUS
            elif qa_attempts == 2:
                result.adjustments.append(("Second-pass QA success", self.SECOND_PASS_QA_BONUS))
                current_value += self.SECOND_PASS_QA_BONUS
            # No bonus for 3+ attempts, but no penalty either if passed
        else:
            result.adjustments.append(("QA failed", self.QA_FAILED_PENALTY))
            current_value += self.QA_FAILED_PENALTY

        # Professional practices bonuses
        if has_tests:
            result.adjustments.append(("Includes tests", self.HAS_TESTS_BONUS))
            current_value += self.HAS_TESTS_BONUS

        if has_docs:
            result.adjustments.append(("Includes documentation", self.HAS_DOCS_BONUS))
            current_value += self.HAS_DOCS_BONUS

        if has_types:
            result.adjustments.append(("Includes type annotations", self.HAS_TYPES_BONUS))
            current_value += self.HAS_TYPES_BONUS

        # Code coverage adjustments
        if code_coverage is not None:
            if code_coverage >= 80.0:
                result.adjustments.append(("High code coverage (>=80%)", self.HIGH_COVERAGE_BONUS))
                current_value += self.HIGH_COVERAGE_BONUS
            elif code_coverage >= 60.0:
                result.adjustments.append(("Medium code coverage (>=60%)", self.MEDIUM_COVERAGE_BONUS))
                current_value += self.MEDIUM_COVERAGE_BONUS

        # Penalties
        if lint_errors > 10:
            result.adjustments.append(("Many lint errors (>10)", self.MANY_LINT_ERRORS_PENALTY))
            current_value += self.MANY_LINT_ERRORS_PENALTY

        if rework_needed:
            result.adjustments.append(("Rework needed", self.REWORK_PENALTY))
            current_value += self.REWORK_PENALTY

        # Clamp to valid range
        result.final_multiplier = max(
            self.MIN_MULTIPLIER,
            min(self.MAX_MULTIPLIER, current_value)
        )

        logger.debug(
            f"Quality multiplier calculated: {result.final_multiplier:.2f} "
            f"(adjustments: {len(result.adjustments)})"
        )

        return result

    def calculate_from_build_metrics(
        self,
        qa_passed: bool,
        qa_attempts: int,
        files_changed: int = 0,
        subtasks_completed: int = 0,
        subtasks_total: int = 0,
    ) -> QualityMultiplier:
        """
        Calculate quality multiplier from build metrics.

        This is a convenience method that extracts quality signals from
        typical build metrics when detailed code analysis isn't available.

        Args:
            qa_passed: Whether QA passed
            qa_attempts: Number of QA attempts
            files_changed: Number of files changed
            subtasks_completed: Number of subtasks completed
            subtasks_total: Total number of subtasks

        Returns:
            QualityMultiplier with adjustments and final value
        """
        # Estimate quality indicators from build metrics
        # If all subtasks completed, likely includes tests/docs
        completion_rate = (
            subtasks_completed / subtasks_total
            if subtasks_total > 0
            else 1.0
        )

        # Heuristic: if completion rate is high, likely includes tests
        has_tests = completion_rate >= 0.9 and files_changed >= 3

        # Rework needed if many QA attempts
        rework_needed = qa_attempts > 3

        return self.calculate(
            qa_passed=qa_passed,
            qa_attempts=qa_attempts,
            has_tests=has_tests,
            has_docs=False,  # Can't infer from metrics
            has_types=False,  # Can't infer from metrics
            code_coverage=None,  # Not available
            lint_errors=0,  # Not available
            rework_needed=rework_needed,
        )


def get_quality_tier(multiplier: float) -> str:
    """
    Get a human-readable quality tier based on the multiplier value.

    Args:
        multiplier: The quality multiplier value

    Returns:
        Quality tier string: "exceptional", "good", "neutral", "low", or "poor"
    """
    if multiplier >= 1.5:
        return "exceptional"
    elif multiplier >= 1.2:
        return "good"
    elif multiplier >= 0.9:
        return "neutral"
    elif multiplier >= 0.7:
        return "low"
    else:
        return "poor"


def get_quality_color(multiplier: float) -> str:
    """
    Get a color indicator based on the multiplier value.

    Args:
        multiplier: The quality multiplier value

    Returns:
        Color string: "green", "blue", "gray", "yellow", or "red"
    """
    if multiplier >= 1.2:
        return "green"
    elif multiplier >= 1.0:
        return "blue"
    elif multiplier >= 0.9:
        return "gray"
    elif multiplier >= 0.7:
        return "yellow"
    else:
        return "red"
