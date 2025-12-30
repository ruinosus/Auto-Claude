# tests/test_metrics_client.py
import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch


def test_get_daily_metrics():
    """Test fetching daily metrics from Langfuse."""
    with patch('analytics.metrics_client._get_langfuse_api') as mock_api:
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(
                date="2025-01-01",
                cost_total=10.5,
                count_traces=100,
                count_observations=500,
                usage_input_tokens=10000,
                usage_output_tokens=5000,
            ),
            MagicMock(
                date="2025-01-02",
                cost_total=12.3,
                count_traces=120,
                count_observations=600,
                usage_input_tokens=12000,
                usage_output_tokens=6000,
            ),
        ]
        mock_api.return_value.api.daily_metrics.list.return_value = mock_response

        from analytics.metrics_client import get_daily_metrics

        result = get_daily_metrics(
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )

        assert len(result) == 2
        assert result[0].cost_total == 10.5
        assert result[0].count_traces == 100


def test_get_project_cost():
    """Test getting total cost for a project."""
    with patch('analytics.metrics_client.get_daily_metrics') as mock_metrics:
        from analytics.metrics_client import DailyMetric
        mock_metrics.return_value = [
            DailyMetric(date="2025-01-01", cost_total=10.0, count_traces=100),
            DailyMetric(date="2025-01-02", cost_total=15.0, count_traces=150),
            DailyMetric(date="2025-01-03", cost_total=20.0, count_traces=200),
        ]

        from analytics.metrics_client import get_project_cost

        total = get_project_cost(
            project_id="test-project",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )

        assert total == 45.0


def test_get_trace_count():
    """Test getting trace count."""
    with patch('analytics.metrics_client.get_daily_metrics') as mock_metrics:
        from analytics.metrics_client import DailyMetric
        mock_metrics.return_value = [
            DailyMetric(date="2025-01-01", cost_total=10.0, count_traces=100),
            DailyMetric(date="2025-01-02", cost_total=15.0, count_traces=150),
        ]

        from analytics.metrics_client import get_trace_count

        total = get_trace_count(
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )

        assert total == 250


def test_get_traces():
    """Test fetching traces from Langfuse."""
    with patch('analytics.metrics_client._get_langfuse_api') as mock_api:
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(
                id="trace-1",
                name="test-trace",
                user_id="user-1",
                session_id="session-1",
                tags=["tag1"],
                metadata={"key": "value"},
                input={"prompt": "test"},
                output={"response": "result"},
                timestamp=datetime.now(),
            ),
        ]
        mock_api.return_value.api.trace.list.return_value = mock_response

        from analytics.metrics_client import get_traces

        result = get_traces(limit=10)

        assert len(result) == 1
        assert result[0]["id"] == "trace-1"


def test_export_traces_for_billing():
    """Test exporting traces for billing."""
    with patch('analytics.metrics_client.get_daily_metrics') as mock_metrics:
        from analytics.metrics_client import DailyMetric
        mock_metrics.return_value = [
            DailyMetric(
                date="2025-01-01",
                cost_total=10.0,
                count_traces=100,
                usage_input_tokens=10000,
                usage_output_tokens=5000,
            ),
        ]

        from analytics.metrics_client import export_traces_for_billing

        result = export_traces_for_billing(
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )

        assert len(result) == 1
        assert result[0]["cost_usd"] == 10.0
        assert result[0]["traces"] == 100
