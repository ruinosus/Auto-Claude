"""
Tests for Quality Multipliers Module
====================================

Tests the QualityMultiplierCalculator and helper functions.
"""

import pytest
import sys
from pathlib import Path

# Add apps/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analytics.quality_multipliers import (
    QualityMultiplier,
    QualityMultiplierCalculator,
    get_quality_tier,
    get_quality_color,
)


class TestQualityMultiplierCalculator:
    """Tests for QualityMultiplierCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create a calculator instance."""
        return QualityMultiplierCalculator()

    def test_first_pass_qa_success_bonus(self, calculator):
        """First-pass QA success should give +30% bonus."""
        result = calculator.calculate(qa_passed=True, qa_attempts=1)
        assert result.final_multiplier == 1.3
        assert len(result.adjustments) == 1
        assert result.adjustments[0][0] == "First-pass QA success"
        assert result.adjustments[0][1] == 0.30

    def test_second_pass_qa_success_bonus(self, calculator):
        """Second-pass QA success should give +15% bonus."""
        result = calculator.calculate(qa_passed=True, qa_attempts=2)
        assert result.final_multiplier == 1.15
        assert len(result.adjustments) == 1
        assert result.adjustments[0][0] == "Second-pass QA success"
        assert result.adjustments[0][1] == 0.15

    def test_qa_failed_penalty(self, calculator):
        """QA failure should give -30% penalty."""
        result = calculator.calculate(qa_passed=False, qa_attempts=1)
        assert result.final_multiplier == 0.7
        assert len(result.adjustments) == 1
        assert result.adjustments[0][0] == "QA failed"
        assert result.adjustments[0][1] == -0.30

    def test_has_tests_bonus(self, calculator):
        """Having tests should give +20% bonus."""
        result = calculator.calculate(qa_passed=True, qa_attempts=1, has_tests=True)
        assert result.final_multiplier == 1.5
        assert any(adj[0] == "Includes tests" for adj in result.adjustments)

    def test_has_docs_bonus(self, calculator):
        """Having docs should give +10% bonus."""
        result = calculator.calculate(qa_passed=True, qa_attempts=1, has_docs=True)
        assert abs(result.final_multiplier - 1.4) < 0.001
        assert any(adj[0] == "Includes documentation" for adj in result.adjustments)

    def test_has_types_bonus(self, calculator):
        """Having types should give +10% bonus."""
        result = calculator.calculate(qa_passed=True, qa_attempts=1, has_types=True)
        assert abs(result.final_multiplier - 1.4) < 0.001
        assert any(adj[0] == "Includes type annotations" for adj in result.adjustments)

    def test_high_code_coverage_bonus(self, calculator):
        """High code coverage (>=80%) should give +15% bonus."""
        result = calculator.calculate(qa_passed=True, qa_attempts=1, code_coverage=85.0)
        assert result.final_multiplier == 1.45
        assert any(adj[0] == "High code coverage (>=80%)" for adj in result.adjustments)

    def test_medium_code_coverage_bonus(self, calculator):
        """Medium code coverage (>=60%) should give +5% bonus."""
        result = calculator.calculate(qa_passed=True, qa_attempts=1, code_coverage=65.0)
        assert result.final_multiplier == 1.35
        assert any(adj[0] == "Medium code coverage (>=60%)" for adj in result.adjustments)

    def test_many_lint_errors_penalty(self, calculator):
        """Many lint errors (>10) should give -10% penalty."""
        result = calculator.calculate(qa_passed=True, qa_attempts=1, lint_errors=15)
        assert result.final_multiplier == 1.2
        assert any(adj[0] == "Many lint errors (>10)" for adj in result.adjustments)

    def test_rework_needed_penalty(self, calculator):
        """Rework needed should give -20% penalty."""
        result = calculator.calculate(qa_passed=True, qa_attempts=1, rework_needed=True)
        assert result.final_multiplier == 1.1
        assert any(adj[0] == "Rework needed" for adj in result.adjustments)

    def test_multiplier_clamp_max(self, calculator):
        """Multiplier should be clamped to max 2.0."""
        # All bonuses: 1 + 0.30 + 0.20 + 0.10 + 0.10 + 0.15 = 1.85, under 2.0
        result = calculator.calculate(
            qa_passed=True,
            qa_attempts=1,
            has_tests=True,
            has_docs=True,
            has_types=True,
            code_coverage=90.0,
        )
        assert result.final_multiplier <= 2.0

    def test_multiplier_clamp_min(self, calculator):
        """Multiplier should be clamped to min 0.5."""
        # All penalties: 1 - 0.30 - 0.10 - 0.20 = 0.4, should clamp to 0.5
        result = calculator.calculate(
            qa_passed=False,
            qa_attempts=5,
            lint_errors=20,
            rework_needed=True,
        )
        assert result.final_multiplier == 0.5

    def test_combined_adjustments(self, calculator):
        """Multiple adjustments should combine correctly."""
        result = calculator.calculate(
            qa_passed=True,
            qa_attempts=1,  # +0.30
            has_tests=True,  # +0.20
            has_docs=True,  # +0.10
        )
        # 1.0 + 0.30 + 0.20 + 0.10 = 1.60
        assert result.final_multiplier == 1.6
        assert len(result.adjustments) == 3

    def test_no_adjustments(self, calculator):
        """Third+ pass QA success with no other factors."""
        result = calculator.calculate(qa_passed=True, qa_attempts=3)
        # No bonus for 3+ attempts, no other factors
        assert result.final_multiplier == 1.0
        assert len(result.adjustments) == 0

    def test_to_dict(self, calculator):
        """Test QualityMultiplier.to_dict() method."""
        result = calculator.calculate(qa_passed=True, qa_attempts=1)
        d = result.to_dict()
        assert d["base_value"] == 1.0
        assert d["final_multiplier"] == 1.3
        assert len(d["adjustments"]) == 1
        assert d["adjustments"][0]["reason"] == "First-pass QA success"
        assert d["adjustments"][0]["delta"] == 0.30

    def test_calculate_from_build_metrics(self, calculator):
        """Test the build metrics convenience method."""
        result = calculator.calculate_from_build_metrics(
            qa_passed=True,
            qa_attempts=1,
            files_changed=10,
            subtasks_completed=10,
            subtasks_total=10,
        )
        # High completion rate with many files = has_tests inferred
        assert result.final_multiplier >= 1.3


class TestQualityHelpers:
    """Tests for helper functions."""

    def test_get_quality_tier_exceptional(self):
        """Exceptional tier for multiplier >= 1.5."""
        assert get_quality_tier(1.5) == "exceptional"
        assert get_quality_tier(2.0) == "exceptional"

    def test_get_quality_tier_good(self):
        """Good tier for multiplier >= 1.2."""
        assert get_quality_tier(1.2) == "good"
        assert get_quality_tier(1.4) == "good"

    def test_get_quality_tier_neutral(self):
        """Neutral tier for multiplier >= 0.9."""
        assert get_quality_tier(0.9) == "neutral"
        assert get_quality_tier(1.0) == "neutral"
        assert get_quality_tier(1.1) == "neutral"

    def test_get_quality_tier_low(self):
        """Low tier for multiplier >= 0.7."""
        assert get_quality_tier(0.7) == "low"
        assert get_quality_tier(0.8) == "low"

    def test_get_quality_tier_poor(self):
        """Poor tier for multiplier < 0.7."""
        assert get_quality_tier(0.5) == "poor"
        assert get_quality_tier(0.6) == "poor"

    def test_get_quality_color_green(self):
        """Green color for multiplier >= 1.2."""
        assert get_quality_color(1.2) == "green"
        assert get_quality_color(1.5) == "green"

    def test_get_quality_color_blue(self):
        """Blue color for multiplier >= 1.0."""
        assert get_quality_color(1.0) == "blue"
        assert get_quality_color(1.1) == "blue"

    def test_get_quality_color_gray(self):
        """Gray color for multiplier >= 0.9."""
        assert get_quality_color(0.9) == "gray"

    def test_get_quality_color_yellow(self):
        """Yellow color for multiplier >= 0.7."""
        assert get_quality_color(0.7) == "yellow"
        assert get_quality_color(0.8) == "yellow"

    def test_get_quality_color_red(self):
        """Red color for multiplier < 0.7."""
        assert get_quality_color(0.5) == "red"
        assert get_quality_color(0.6) == "red"


class TestQualityMultiplierDataclass:
    """Tests for the QualityMultiplier dataclass."""

    def test_default_values(self):
        """Test default values for QualityMultiplier."""
        m = QualityMultiplier()
        assert m.base_value == 1.0
        assert m.adjustments == []
        assert m.final_multiplier == 1.0

    def test_with_adjustments(self):
        """Test QualityMultiplier with adjustments."""
        m = QualityMultiplier(
            base_value=1.0,
            adjustments=[("Test bonus", 0.10), ("Docs bonus", 0.05)],
            final_multiplier=1.15,
        )
        assert len(m.adjustments) == 2
        assert m.final_multiplier == 1.15
