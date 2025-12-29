#!/usr/bin/env python3
"""
Tests for Analytics Evolution Features
======================================

Tests the new ROI analytics evolution modules:
- BenchmarkService (G15): Market benchmark comparisons
- BudgetEnforcer (G04): Budget enforcement and controls
- AnomalyDetector (G05): Cost and usage anomaly detection
- QualityTracker (G13): Code quality metrics tracking
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add apps/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analytics.benchmarks import (
    BenchmarkService,
    Benchmark,
    HOURLY_RATES,
    MINUTES_PER_LINE
)
from analytics.budget_enforcer import (
    BudgetEnforcer,
    BudgetSettings,
    BudgetCheckResult
)
from analytics.anomaly_detector import (
    AnomalyDetector,
    Anomaly
)
from analytics.quality_tracker import (
    QualityTracker,
    QualityMetrics,
    LintResult,
    TypeCheckResult,
    LINTER_CONFIG_FILES,
    TYPE_CHECKER_CONFIG_FILES
)
from analytics.storage import AnalyticsStorage


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_analytics.db"
        yield str(db_path)


@pytest.fixture
def analytics_storage(temp_db_path):
    """Create AnalyticsStorage instance with temp database."""
    return AnalyticsStorage(temp_db_path)


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for QualityTracker tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ==============================================================================
# BenchmarkService Tests
# ==============================================================================

class TestBenchmarkService:
    """Tests for BenchmarkService market benchmarks."""

    def test_get_benchmark_us_senior(self):
        """Test getting benchmark for US senior developer."""
        service = BenchmarkService()
        benchmark = service.get_benchmark('us', 'senior')

        assert benchmark.region == 'us'
        assert benchmark.seniority == 'senior'
        assert benchmark.hourly_rate == 130
        assert benchmark.minutes_per_line == 1.5

    def test_get_benchmark_latam_junior(self):
        """Test getting benchmark for LATAM junior developer."""
        service = BenchmarkService()
        benchmark = service.get_benchmark('latam', 'junior')

        assert benchmark.region == 'latam'
        assert benchmark.seniority == 'junior'
        assert benchmark.hourly_rate == 25
        assert benchmark.minutes_per_line == 4.0

    def test_get_benchmark_eu_mid(self):
        """Test getting benchmark for EU mid-level developer."""
        service = BenchmarkService()
        benchmark = service.get_benchmark('eu', 'mid')

        assert benchmark.region == 'eu'
        assert benchmark.seniority == 'mid'
        assert benchmark.hourly_rate == 70
        assert benchmark.minutes_per_line == 2.5

    def test_get_all_benchmarks(self):
        """Test retrieving all benchmarks."""
        service = BenchmarkService()
        benchmarks = service.get_all_benchmarks()

        # Should have 9 combinations (3 regions x 3 seniorities)
        assert len(benchmarks) == 9

        # Verify all regions present
        regions = {b.region for b in benchmarks}
        assert regions == {'us', 'latam', 'eu'}

        # Verify all seniorities present
        seniorities = {b.seniority for b in benchmarks}
        assert seniorities == {'junior', 'mid', 'senior'}

    def test_calculate_savings_vs_benchmark_positive_savings(self):
        """Test savings calculation with positive savings (AI cheaper)."""
        service = BenchmarkService()

        result = service.calculate_savings_vs_benchmark(
            actual_cost=5.00,
            lines_changed=100,
            region='us',
            seniority='senior'
        )

        # Benchmark: 100 lines * 1.5 min/line = 150 min = 2.5 hours
        # Benchmark cost: 2.5 * $130 = $325
        expected_benchmark_cost = (100 * 1.5 / 60) * 130  # 325.0
        expected_savings = expected_benchmark_cost - 5.00

        assert result['actual_cost'] == 5.00
        assert result['benchmark_cost'] == pytest.approx(expected_benchmark_cost, rel=0.01)
        assert result['savings'] == pytest.approx(expected_savings, rel=0.01)
        assert result['savings_percent'] > 0
        assert result['hours_equivalent'] == pytest.approx(2.5, rel=0.01)

    def test_calculate_savings_vs_benchmark_negative_savings(self):
        """Test savings calculation with negative savings (AI more expensive)."""
        service = BenchmarkService()

        result = service.calculate_savings_vs_benchmark(
            actual_cost=500.00,
            lines_changed=10,  # Very few lines for the cost
            region='latam',
            seniority='junior'
        )

        # Benchmark: 10 lines * 4 min/line = 40 min = 0.67 hours
        # Benchmark cost: 0.67 * $25 = ~$16.67
        expected_benchmark_cost = (10 * 4.0 / 60) * 25

        assert result['savings'] < 0  # Negative savings
        assert result['savings_percent'] < 0

    def test_calculate_savings_zero_lines(self):
        """Test savings calculation with zero lines changed."""
        service = BenchmarkService()

        result = service.calculate_savings_vs_benchmark(
            actual_cost=1.00,
            lines_changed=0,
            region='us',
            seniority='mid'
        )

        # With zero lines, benchmark cost is 0, savings_percent should be 0
        assert result['benchmark_cost'] == 0
        assert result['savings'] == -1.00
        assert result['savings_percent'] == 0

    def test_get_percentile_ranking_empty_list(self):
        """Test percentile ranking with empty comparison list."""
        service = BenchmarkService()
        percentile = service.get_percentile_ranking(50.0, [])

        # Default to 50th percentile when no data
        assert percentile == 50

    def test_get_percentile_ranking_lowest(self):
        """Test percentile ranking when value is lowest."""
        service = BenchmarkService()
        percentile = service.get_percentile_ranking(10.0, [20.0, 30.0, 40.0, 50.0])

        # 0 values below, so 0th percentile
        assert percentile == 0

    def test_get_percentile_ranking_highest(self):
        """Test percentile ranking when value is highest."""
        service = BenchmarkService()
        percentile = service.get_percentile_ranking(100.0, [20.0, 30.0, 40.0, 50.0])

        # All values below, so 100th percentile
        assert percentile == 100

    def test_get_percentile_ranking_middle(self):
        """Test percentile ranking in the middle."""
        service = BenchmarkService()
        percentile = service.get_percentile_ranking(35.0, [10.0, 20.0, 30.0, 40.0, 50.0])

        # 3 values below (10, 20, 30), so 60th percentile
        assert percentile == 60


# ==============================================================================
# BudgetEnforcer Tests
# ==============================================================================

class TestBudgetEnforcer:
    """Tests for BudgetEnforcer budget controls."""

    def test_default_settings(self, analytics_storage):
        """Test that default settings are returned when none exist."""
        enforcer = BudgetEnforcer(analytics_storage)
        settings = enforcer.get_settings()

        assert isinstance(settings, BudgetSettings)
        assert settings.enforce_blocking == False
        assert settings.warn_threshold_percent == 80.0
        assert settings.block_threshold_percent == 100.0
        assert settings.notification_enabled == True
        assert settings.override_allowed == True

    def test_save_and_retrieve_settings(self, analytics_storage):
        """Test saving and retrieving budget settings."""
        enforcer = BudgetEnforcer(analytics_storage)

        custom_settings = BudgetSettings(
            enforce_blocking=True,
            warn_threshold_percent=70.0,
            block_threshold_percent=90.0,
            notification_enabled=False,
            override_allowed=False
        )
        enforcer.save_settings(custom_settings)

        retrieved = enforcer.get_settings()
        assert retrieved.enforce_blocking == True
        assert retrieved.warn_threshold_percent == 70.0
        assert retrieved.block_threshold_percent == 90.0
        assert retrieved.notification_enabled == False
        assert retrieved.override_allowed == False

    def test_save_settings_invalid_threshold(self, analytics_storage):
        """Test that invalid threshold percentages raise ValueError."""
        enforcer = BudgetEnforcer(analytics_storage)

        with pytest.raises(ValueError, match="warn_threshold_percent"):
            enforcer.save_settings(BudgetSettings(warn_threshold_percent=-10))

        with pytest.raises(ValueError, match="block_threshold_percent"):
            enforcer.save_settings(BudgetSettings(block_threshold_percent=150))

    def test_set_and_get_spec_budget(self, analytics_storage):
        """Test setting and getting spec budget."""
        enforcer = BudgetEnforcer(analytics_storage)

        enforcer.set_spec_budget("001-feature", 100.0)
        budget = enforcer.get_budget("001-feature")

        assert budget == 100.0

    def test_set_negative_budget_raises_error(self, analytics_storage):
        """Test that negative budget raises ValueError."""
        enforcer = BudgetEnforcer(analytics_storage)

        with pytest.raises(ValueError, match="non-negative"):
            enforcer.set_spec_budget("001-feature", -50.0)

    def test_get_budget_nonexistent_spec(self, analytics_storage):
        """Test getting budget for non-existent spec returns None."""
        enforcer = BudgetEnforcer(analytics_storage)
        budget = enforcer.get_budget("nonexistent-spec")

        assert budget is None

    def test_check_budget_no_budget_set(self, analytics_storage):
        """Test budget check when no budget is set."""
        enforcer = BudgetEnforcer(analytics_storage)

        result = enforcer.check_budget("001-feature")

        assert result.allowed == True
        assert result.remaining == float('inf')
        assert result.percentage_used == 0.0
        assert result.reason is None

    def test_check_budget_under_budget(self, analytics_storage):
        """Test budget check when under budget."""
        enforcer = BudgetEnforcer(analytics_storage)
        enforcer.set_spec_budget("001-feature", 100.0)

        result = enforcer.check_budget("001-feature", estimated_additional_cost=10.0)

        assert result.allowed == True
        assert result.remaining == 90.0
        assert result.percentage_used == 10.0
        assert result.reason is None

    def test_check_budget_at_warn_threshold(self, analytics_storage):
        """Test budget check at warning threshold."""
        enforcer = BudgetEnforcer(analytics_storage)
        enforcer.set_spec_budget("001-feature", 100.0)

        # Add cost to reach warning threshold (80%)
        # We need to add conversations to simulate existing cost
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (spec_id, session_number, phase, started_at, total_cost_usd)
            VALUES (?, 1, 'coding', ?, ?)
        """, ("001-feature", datetime.now().isoformat(), 80.0))
        conn.commit()
        conn.close()

        result = enforcer.check_budget("001-feature")

        assert result.allowed == True
        assert result.percentage_used >= 80.0
        assert result.reason is not None
        assert "Warning" in result.reason

    def test_check_budget_over_block_threshold_with_blocking(self, analytics_storage):
        """Test budget check when over block threshold with blocking enabled."""
        enforcer = BudgetEnforcer(analytics_storage)

        # Enable blocking
        enforcer.save_settings(BudgetSettings(enforce_blocking=True))
        enforcer.set_spec_budget("001-feature", 100.0)

        # Add cost over 100%
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (spec_id, session_number, phase, started_at, total_cost_usd)
            VALUES (?, 1, 'coding', ?, ?)
        """, ("001-feature", datetime.now().isoformat(), 110.0))
        conn.commit()
        conn.close()

        result = enforcer.check_budget("001-feature")

        assert result.allowed == False
        assert result.percentage_used >= 100.0
        assert result.reason is not None
        assert "exceeded" in result.reason.lower()

    def test_check_budget_over_block_threshold_without_blocking(self, analytics_storage):
        """Test budget check when over threshold but blocking disabled."""
        enforcer = BudgetEnforcer(analytics_storage)

        # Blocking disabled by default
        enforcer.set_spec_budget("001-feature", 100.0)

        # Add cost over 100%
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (spec_id, session_number, phase, started_at, total_cost_usd)
            VALUES (?, 1, 'coding', ?, ?)
        """, ("001-feature", datetime.now().isoformat(), 110.0))
        conn.commit()
        conn.close()

        result = enforcer.check_budget("001-feature")

        # Should be allowed since blocking is disabled
        assert result.allowed == True
        # But should have a warning
        assert result.reason is not None

    def test_can_proceed_returns_boolean(self, analytics_storage):
        """Test can_proceed returns correct boolean."""
        enforcer = BudgetEnforcer(analytics_storage)

        # No budget set - should proceed
        assert enforcer.can_proceed("001-feature") == True

        # With blocking and over budget
        enforcer.save_settings(BudgetSettings(enforce_blocking=True))
        enforcer.set_spec_budget("002-feature", 10.0)

        # Add cost over budget
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (spec_id, session_number, phase, started_at, total_cost_usd)
            VALUES (?, 1, 'coding', ?, ?)
        """, ("002-feature", datetime.now().isoformat(), 20.0))
        conn.commit()
        conn.close()

        assert enforcer.can_proceed("002-feature") == False

    def test_record_override(self, analytics_storage):
        """Test recording budget override."""
        enforcer = BudgetEnforcer(analytics_storage)

        enforcer.record_override(
            spec_id="001-feature",
            reason="Emergency deployment required",
            user="admin"
        )

        # Verify override was recorded in anomalies table
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM anomalies WHERE anomaly_type = 'budget_override' AND spec_id = ?
        """, ("001-feature",))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert "admin" in row['dismissed_by']
        assert "Emergency" in row['dismissed_by']

    def test_get_budget_status(self, analytics_storage):
        """Test getting comprehensive budget status."""
        enforcer = BudgetEnforcer(analytics_storage)
        enforcer.set_spec_budget("001-feature", 100.0)

        # Add some cost
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (spec_id, session_number, phase, started_at, total_cost_usd)
            VALUES (?, 1, 'coding', ?, ?)
        """, ("001-feature", datetime.now().isoformat(), 50.0))
        conn.commit()
        conn.close()

        status = enforcer.get_budget_status("001-feature")

        assert status['spec_id'] == "001-feature"
        assert status['budget'] == 100.0
        assert status['current_cost'] == 50.0
        assert status['remaining'] == 50.0
        assert status['percentage_used'] == 50.0
        assert status['is_warning'] == False
        assert status['is_blocked'] == False

    def test_get_budget_status_no_budget(self, analytics_storage):
        """Test budget status when no budget is set."""
        enforcer = BudgetEnforcer(analytics_storage)

        status = enforcer.get_budget_status("nonexistent-spec")

        assert status['budget'] is None
        assert status['remaining'] is None
        assert status['percentage_used'] == 0.0
        assert status['is_warning'] == False
        assert status['is_blocked'] == False


# ==============================================================================
# AnomalyDetector Tests
# ==============================================================================

class TestAnomalyDetector:
    """Tests for AnomalyDetector anomaly detection."""

    def _add_conversations_with_costs(self, storage, costs: list, base_date: datetime = None):
        """Helper to add conversations with specific costs."""
        if base_date is None:
            base_date = datetime.now()

        conn = storage._get_connection()
        cursor = conn.cursor()

        for i, cost in enumerate(costs):
            date = base_date - timedelta(days=len(costs) - i - 1)
            cursor.execute("""
                INSERT INTO conversations (spec_id, session_number, phase, started_at, total_cost_usd, total_input_tokens, total_output_tokens)
                VALUES (?, ?, 'coding', ?, ?, ?, ?)
            """, (f"spec-{i}", i + 1, date.isoformat(), cost, cost * 1000, cost * 500))

        conn.commit()
        conn.close()

    def test_detect_cost_anomalies_insufficient_data(self, analytics_storage):
        """Test that anomaly detection requires minimum data points."""
        detector = AnomalyDetector(analytics_storage, sensitivity=2.0)

        # Add only 2 data points (need at least 3)
        self._add_conversations_with_costs(analytics_storage, [1.0, 2.0])

        anomalies = detector.detect_cost_anomalies()
        assert len(anomalies) == 0

    def test_detect_cost_anomalies_normal_data(self, analytics_storage):
        """Test no anomalies detected in normal data."""
        detector = AnomalyDetector(analytics_storage, sensitivity=2.0)

        # Add consistent costs
        self._add_conversations_with_costs(analytics_storage, [5.0, 5.1, 4.9, 5.2, 4.8])

        anomalies = detector.detect_cost_anomalies()
        assert len(anomalies) == 0

    def test_detect_cost_anomalies_with_spike(self, analytics_storage):
        """Test anomaly detected with cost spike."""
        detector = AnomalyDetector(analytics_storage, sensitivity=2.0)

        # Add costs with one significant spike
        # Need enough baseline data points so the outlier doesn't inflate stdev too much
        # With 10 normal values and 1 spike, z-score calculation is more reliable
        costs = [5.0, 5.1, 4.9, 5.0, 5.2, 4.8, 5.0, 5.1, 4.9, 5.0, 100.0]
        self._add_conversations_with_costs(analytics_storage, costs)

        anomalies = detector.detect_cost_anomalies()

        assert len(anomalies) >= 1
        # The spike should be detected
        spike_anomaly = next((a for a in anomalies if a.actual_value == 100.0), None)
        assert spike_anomaly is not None
        assert spike_anomaly.anomaly_type == 'cost_spike'
        assert spike_anomaly.z_score > 2.0

    def test_detect_token_anomalies(self, analytics_storage):
        """Test token anomaly detection."""
        detector = AnomalyDetector(analytics_storage, sensitivity=2.0)

        # Add conversations with varying token usage
        # Need enough baseline data points so outlier doesn't inflate stdev
        base_date = datetime.now()
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()

        # 10 normal values plus 1 spike
        token_usage = [1000, 1100, 900, 1000, 1050, 950, 1000, 1100, 900, 1000, 20000]
        for i, tokens in enumerate(token_usage):
            date = base_date - timedelta(days=len(token_usage) - i - 1)
            cursor.execute("""
                INSERT INTO conversations (spec_id, session_number, phase, started_at, total_cost_usd, total_input_tokens, total_output_tokens)
                VALUES (?, ?, 'coding', ?, ?, ?, ?)
            """, (f"spec-{i}", i + 1, date.isoformat(), 1.0, tokens // 2, tokens // 2))

        conn.commit()
        conn.close()

        anomalies = detector.detect_token_anomalies()

        assert len(anomalies) >= 1
        spike_anomaly = anomalies[0]
        assert spike_anomaly.anomaly_type == 'token_spike'

    def test_severity_calculation_info(self, analytics_storage):
        """Test severity is 'info' for z-score between 2 and 3."""
        detector = AnomalyDetector(analytics_storage, sensitivity=2.0)

        # Z-score of 2.5 should be 'info'
        severity = detector._get_severity(2.5)
        assert severity == 'info'

    def test_severity_calculation_warning(self, analytics_storage):
        """Test severity is 'warning' for z-score between 3 and 4."""
        detector = AnomalyDetector(analytics_storage, sensitivity=2.0)

        # Z-score of 3.5 should be 'warning'
        severity = detector._get_severity(3.5)
        assert severity == 'warning'

    def test_severity_calculation_critical(self, analytics_storage):
        """Test severity is 'critical' for z-score >= 4."""
        detector = AnomalyDetector(analytics_storage, sensitivity=2.0)

        # Z-score of 4.5 should be 'critical'
        severity = detector._get_severity(4.5)
        assert severity == 'critical'

    def test_severity_negative_zscore(self, analytics_storage):
        """Test severity calculation with negative z-score."""
        detector = AnomalyDetector(analytics_storage, sensitivity=2.0)

        # Negative z-score should use absolute value
        assert detector._get_severity(-2.5) == 'info'
        assert detector._get_severity(-3.5) == 'warning'
        assert detector._get_severity(-4.5) == 'critical'

    def test_run_detection_saves_anomalies(self, analytics_storage):
        """Test that run_detection saves anomalies to database."""
        detector = AnomalyDetector(analytics_storage, sensitivity=2.0)

        # Add costs with spike
        costs = [5.0, 5.0, 5.0, 5.0, 100.0]
        self._add_conversations_with_costs(analytics_storage, costs)

        anomalies = detector.run_detection()

        # Verify anomalies are saved
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM anomalies WHERE anomaly_type != 'budget_override'")
        row = cursor.fetchone()
        conn.close()

        assert row['count'] >= len(anomalies)

    def test_get_active_anomalies(self, analytics_storage):
        """Test retrieving non-dismissed anomalies."""
        detector = AnomalyDetector(analytics_storage, sensitivity=2.0)

        # Manually insert some anomalies
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO anomalies (detected_at, anomaly_type, severity, metric_name, expected_value, actual_value, z_score, dismissed)
            VALUES (?, 'cost_spike', 'warning', 'daily_cost', 5.0, 50.0, 3.5, 0)
        """, (datetime.now().isoformat(),))
        cursor.execute("""
            INSERT INTO anomalies (detected_at, anomaly_type, severity, metric_name, expected_value, actual_value, z_score, dismissed)
            VALUES (?, 'token_spike', 'info', 'daily_tokens', 1000, 5000, 2.5, 1)
        """, (datetime.now().isoformat(),))
        conn.commit()
        conn.close()

        active = detector.get_active_anomalies()

        # Only non-dismissed anomaly should be returned
        assert len(active) == 1
        assert active[0].anomaly_type == 'cost_spike'
        assert active[0].dismissed == False

    def test_dismiss_anomaly(self, analytics_storage):
        """Test dismissing an anomaly."""
        detector = AnomalyDetector(analytics_storage, sensitivity=2.0)

        # Add an anomaly
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO anomalies (detected_at, anomaly_type, severity, metric_name, expected_value, actual_value, z_score, dismissed)
            VALUES (?, 'cost_spike', 'warning', 'daily_cost', 5.0, 50.0, 3.5, 0)
        """, (datetime.now().isoformat(),))
        anomaly_id = cursor.lastrowid
        conn.commit()
        conn.close()

        detector.dismiss_anomaly(anomaly_id, dismissed_by="test_user")

        # Verify dismissed
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT dismissed, dismissed_by FROM anomalies WHERE id = ?", (anomaly_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['dismissed'] == 1
        assert row['dismissed_by'] == "test_user"

    def test_custom_sensitivity(self, analytics_storage):
        """Test anomaly detection with custom sensitivity."""
        # Higher sensitivity = fewer anomalies detected
        detector_strict = AnomalyDetector(analytics_storage, sensitivity=4.0)
        detector_loose = AnomalyDetector(analytics_storage, sensitivity=1.5)

        # Add costs with moderate spike
        costs = [5.0, 5.0, 5.0, 5.0, 15.0]  # 3x normal
        self._add_conversations_with_costs(analytics_storage, costs)

        strict_anomalies = detector_strict.detect_cost_anomalies()
        loose_anomalies = detector_loose.detect_cost_anomalies()

        # Looser sensitivity should detect more anomalies
        assert len(loose_anomalies) >= len(strict_anomalies)


# ==============================================================================
# QualityTracker Tests
# ==============================================================================

class TestQualityTracker:
    """Tests for QualityTracker code quality metrics."""

    def test_linter_detection_eslint_config(self, temp_project_dir, analytics_storage):
        """Test ESLint detection from config file."""
        # Create eslint config
        (temp_project_dir / ".eslintrc.json").write_text("{}")

        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)
        linter = tracker._detect_linter()

        assert linter == "eslint"

    def test_linter_detection_ruff_config(self, temp_project_dir, analytics_storage):
        """Test Ruff detection from config file."""
        (temp_project_dir / "ruff.toml").write_text("")

        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)
        linter = tracker._detect_linter()

        assert linter == "ruff"

    def test_linter_detection_pylint_config(self, temp_project_dir, analytics_storage):
        """Test Pylint detection from config file."""
        (temp_project_dir / ".pylintrc").write_text("")

        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)
        linter = tracker._detect_linter()

        assert linter == "pylint"

    def test_linter_detection_from_package_json(self, temp_project_dir, analytics_storage):
        """Test linter detection from package.json."""
        package_json = {
            "name": "test-project",
            "devDependencies": {"eslint": "^8.0.0"}
        }
        (temp_project_dir / "package.json").write_text(json.dumps(package_json))

        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)
        linter = tracker._detect_linter()

        assert linter == "eslint"

    def test_linter_detection_biome(self, temp_project_dir, analytics_storage):
        """Test Biome detection from config file."""
        (temp_project_dir / "biome.json").write_text("{}")

        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)
        linter = tracker._detect_linter()

        assert linter == "biome"

    def test_type_checker_detection_tsconfig(self, temp_project_dir, analytics_storage):
        """Test TypeScript checker detection from tsconfig.json."""
        (temp_project_dir / "tsconfig.json").write_text("{}")

        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)
        checker = tracker._detect_type_checker()

        assert checker == "tsc"

    def test_type_checker_detection_mypy(self, temp_project_dir, analytics_storage):
        """Test mypy detection from config file."""
        (temp_project_dir / "mypy.ini").write_text("")

        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)
        checker = tracker._detect_type_checker()

        assert checker == "mypy"

    def test_type_checker_detection_cargo(self, temp_project_dir, analytics_storage):
        """Test Rust type checker detection from Cargo.toml."""
        (temp_project_dir / "Cargo.toml").write_text("[package]\nname = 'test'")

        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)
        checker = tracker._detect_type_checker()

        assert checker == "cargo_check"

    def test_no_linter_detected(self, temp_project_dir, analytics_storage):
        """Test no linter detection when no config exists."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)
        linter = tracker._detect_linter()

        assert linter is None

    def test_grade_calculation_grade_a(self, temp_project_dir, analytics_storage):
        """Test grade A calculation (0 errors, < 5 warnings)."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        lint_result = LintResult(linter="eslint", errors=0, warnings=3, success=True)
        type_result = TypeCheckResult(checker="tsc", errors=0, success=True)

        grade = tracker._calculate_grade(lint_result, type_result)
        assert grade == "A"

    def test_grade_calculation_grade_b(self, temp_project_dir, analytics_storage):
        """Test grade B calculation (0 errors, 5-9 warnings)."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        lint_result = LintResult(linter="eslint", errors=0, warnings=7, success=True)
        type_result = TypeCheckResult(checker="tsc", errors=0, success=True)

        grade = tracker._calculate_grade(lint_result, type_result)
        assert grade == "B"

    def test_grade_calculation_grade_c(self, temp_project_dir, analytics_storage):
        """Test grade C calculation (1-5 errors)."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        lint_result = LintResult(linter="eslint", errors=3, warnings=0, success=True)
        type_result = TypeCheckResult(checker="tsc", errors=0, success=True)

        grade = tracker._calculate_grade(lint_result, type_result)
        assert grade == "C"

    def test_grade_calculation_grade_d(self, temp_project_dir, analytics_storage):
        """Test grade D calculation (6-10 errors)."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        lint_result = LintResult(linter="eslint", errors=8, warnings=0, success=True)
        type_result = TypeCheckResult(checker="tsc", errors=0, success=True)

        grade = tracker._calculate_grade(lint_result, type_result)
        assert grade == "D"

    def test_grade_calculation_grade_f(self, temp_project_dir, analytics_storage):
        """Test grade F calculation (> 10 errors)."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        lint_result = LintResult(linter="eslint", errors=15, warnings=0, success=True)
        type_result = TypeCheckResult(checker="tsc", errors=0, success=True)

        grade = tracker._calculate_grade(lint_result, type_result)
        assert grade == "F"

    def test_grade_calculation_combines_lint_and_type_errors(self, temp_project_dir, analytics_storage):
        """Test that grade calculation combines lint and type errors."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        lint_result = LintResult(linter="eslint", errors=3, warnings=0, success=True)
        type_result = TypeCheckResult(checker="tsc", errors=3, success=True)

        # Total 6 errors = grade D
        grade = tracker._calculate_grade(lint_result, type_result)
        assert grade == "D"

    def test_grade_calculation_with_none_results(self, temp_project_dir, analytics_storage):
        """Test grade calculation when no linter/type checker results."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        grade = tracker._calculate_grade(None, None)
        # 0 errors, 0 warnings = A
        assert grade == "A"

    def test_grade_calculation_with_failed_lint(self, temp_project_dir, analytics_storage):
        """Test grade calculation ignores failed lint results."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        lint_result = LintResult(linter="eslint", errors=100, warnings=100, success=False)
        type_result = TypeCheckResult(checker="tsc", errors=0, success=True)

        # Failed lint should be ignored
        grade = tracker._calculate_grade(lint_result, type_result)
        assert grade == "A"

    @pytest.mark.asyncio
    async def test_store_metrics(self, temp_project_dir, analytics_storage):
        """Test storing quality metrics in database."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        metrics = QualityMetrics(
            spec_id="001-feature",
            lint_errors=5,
            lint_warnings=10,
            type_errors=2,
            quality_grade="C",
            linter_used="eslint",
            type_checker_used="tsc",
            analyzed_at=datetime.utcnow()
        )

        await tracker._store_metrics(metrics)

        # Verify stored
        conn = analytics_storage._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM spec_quality_metrics WHERE spec_id = ?", ("001-feature",))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row['lint_errors'] == 5
        assert row['lint_warnings'] == 10
        assert row['type_errors'] == 2
        assert row['quality_grade'] == "C"

    @pytest.mark.asyncio
    async def test_get_quality_metrics(self, temp_project_dir, analytics_storage):
        """Test retrieving stored quality metrics."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        # Store metrics
        metrics = QualityMetrics(
            spec_id="001-feature",
            lint_errors=5,
            lint_warnings=10,
            type_errors=2,
            quality_grade="C",
            analyzed_at=datetime.utcnow()
        )
        await tracker._store_metrics(metrics)

        # Retrieve
        retrieved = await tracker.get_quality_metrics()

        assert retrieved is not None
        assert retrieved.spec_id == "001-feature"
        assert retrieved.lint_errors == 5
        assert retrieved.quality_grade == "C"

    @pytest.mark.asyncio
    async def test_get_quality_metrics_nonexistent(self, temp_project_dir, analytics_storage):
        """Test retrieving metrics for non-existent spec."""
        tracker = QualityTracker(temp_project_dir, "nonexistent-spec", analytics_storage)

        result = await tracker.get_quality_metrics()
        assert result is None

    def test_is_command_available(self, temp_project_dir, analytics_storage):
        """Test command availability check."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        # ls should be available on all unix systems
        assert tracker._is_command_available("ls") == True

        # Random nonexistent command should not be available
        assert tracker._is_command_available("nonexistent_command_xyz123") == False

    def test_file_exists_with_glob(self, temp_project_dir, analytics_storage):
        """Test file existence check with glob pattern."""
        # Create some Python files
        (temp_project_dir / "test.py").write_text("# test")
        (temp_project_dir / "subdir").mkdir()
        (temp_project_dir / "subdir" / "other.py").write_text("# other")

        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        assert tracker._file_exists("*.py") == True
        assert tracker._file_exists("**/*.py") == True
        assert tracker._file_exists("*.rs") == False

    @patch('subprocess.run')
    def test_run_eslint_parses_json_output(self, mock_run, temp_project_dir, analytics_storage):
        """Test ESLint runner parses JSON output correctly."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        # Mock ESLint JSON output
        eslint_output = json.dumps([
            {
                "filePath": "/path/to/file.ts",
                "messages": [
                    {"severity": 2, "message": "Error 1"},
                    {"severity": 1, "message": "Warning 1"},
                    {"severity": 2, "message": "Error 2"}
                ]
            }
        ])

        mock_run.return_value = Mock(stdout=eslint_output, stderr="", returncode=0)

        result = tracker._run_eslint()

        assert result.linter == "eslint"
        assert result.errors == 2
        assert result.warnings == 1

    @patch('subprocess.run')
    def test_run_ruff_parses_json_output(self, mock_run, temp_project_dir, analytics_storage):
        """Test Ruff runner parses JSON output correctly."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        # Mock Ruff JSON output
        ruff_output = json.dumps([
            {"code": "E501", "message": "Line too long"},
            {"code": "W001", "message": "Warning"},
            {"code": "F401", "message": "Unused import"}
        ])

        mock_run.return_value = Mock(stdout=ruff_output, stderr="", returncode=0)

        result = tracker._run_ruff()

        assert result.linter == "ruff"
        assert result.errors == 2  # E501 and F401
        assert result.warnings == 1  # W001

    @patch('subprocess.run')
    def test_run_tsc_parses_output(self, mock_run, temp_project_dir, analytics_storage):
        """Test TypeScript compiler runner parses output correctly."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        # Mock tsc output
        tsc_output = """
        src/file1.ts(10,5): error TS2304: Cannot find name 'foo'.
        src/file2.ts(20,10): error TS2339: Property 'bar' does not exist.
        """

        mock_run.return_value = Mock(stdout=tsc_output, stderr="", returncode=1)

        result = tracker._run_tsc()

        assert result.checker == "tsc"
        assert result.errors == 2

    @patch('subprocess.run')
    def test_run_mypy_parses_output(self, mock_run, temp_project_dir, analytics_storage):
        """Test mypy runner parses output correctly."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        # Mock mypy output
        mypy_output = """
        file1.py:10: error: Argument 1 to "func" has incompatible type
        file2.py:20: error: Incompatible return value type
        file3.py:30: note: Some note
        """

        mock_run.return_value = Mock(stdout=mypy_output, stderr="", returncode=1)

        result = tracker._run_mypy()

        assert result.checker == "mypy"
        assert result.errors == 2  # Only error lines, not notes

    @patch('subprocess.run')
    def test_linter_timeout_handling(self, mock_run, temp_project_dir, analytics_storage):
        """Test linter handles timeout gracefully."""
        tracker = QualityTracker(temp_project_dir, "001-feature", analytics_storage)

        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="eslint", timeout=120)

        result = tracker._run_eslint()

        assert result.success == False


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestIntegration:
    """Integration tests combining multiple modules."""

    @pytest.mark.asyncio
    async def test_budget_with_anomaly_detection(self, temp_db_path):
        """Test budget enforcement with anomaly detection."""
        storage = AnalyticsStorage(temp_db_path)
        enforcer = BudgetEnforcer(storage)
        detector = AnomalyDetector(storage, sensitivity=2.0)

        # Set up budget
        enforcer.set_spec_budget("001-feature", 50.0)

        # Add conversations with normal costs
        conn = storage._get_connection()
        cursor = conn.cursor()
        base_date = datetime.now()

        for i in range(5):
            date = base_date - timedelta(days=5 - i)
            cursor.execute("""
                INSERT INTO conversations (spec_id, session_number, phase, started_at, total_cost_usd, total_input_tokens, total_output_tokens)
                VALUES (?, ?, 'coding', ?, ?, ?, ?)
            """, ("001-feature", i + 1, date.isoformat(), 5.0, 5000, 2500))

        conn.commit()
        conn.close()

        # Check budget status
        status = enforcer.get_budget_status("001-feature")
        assert status['current_cost'] == 25.0  # 5 * 5.0
        assert status['remaining'] == 25.0

        # Run anomaly detection
        anomalies = detector.run_detection()
        # No anomalies expected with consistent costs
        cost_anomalies = [a for a in anomalies if a.anomaly_type == 'cost_spike']
        assert len(cost_anomalies) == 0

    def test_benchmark_with_savings_calculation(self):
        """Test full savings calculation workflow."""
        service = BenchmarkService()

        # Simulate AI completing task
        actual_cost = 2.50
        lines_changed = 200

        # Calculate savings against different benchmarks
        us_senior = service.calculate_savings_vs_benchmark(
            actual_cost, lines_changed, 'us', 'senior'
        )
        latam_junior = service.calculate_savings_vs_benchmark(
            actual_cost, lines_changed, 'latam', 'junior'
        )

        # US senior should show higher savings
        assert us_senior['savings'] > latam_junior['savings']
        assert us_senior['savings_percent'] > 0
        assert latam_junior['savings_percent'] > 0

    @pytest.mark.asyncio
    async def test_quality_metrics_persistence_cycle(self, temp_project_dir, temp_db_path):
        """Test full quality metrics persistence cycle."""
        storage = AnalyticsStorage(temp_db_path)
        tracker = QualityTracker(temp_project_dir, "001-feature", storage)

        # Store initial metrics
        metrics1 = QualityMetrics(
            spec_id="001-feature",
            lint_errors=10,
            lint_warnings=5,
            type_errors=3,
            quality_grade="D",
            analyzed_at=datetime.utcnow()
        )
        await tracker._store_metrics(metrics1)

        # Update with better metrics (simulating fixes)
        metrics2 = QualityMetrics(
            spec_id="001-feature",
            lint_errors=0,
            lint_warnings=2,
            type_errors=0,
            quality_grade="A",
            analyzed_at=datetime.utcnow()
        )
        await tracker._store_metrics(metrics2)

        # Retrieve should show latest
        retrieved = await tracker.get_quality_metrics()
        assert retrieved.quality_grade == "A"
        assert retrieved.lint_errors == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
