#!/usr/bin/env python3
"""
OpenTelemetry Exporter Tests
=============================

Tests for OTLP metrics export functionality.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add auto-claude to path
if str(Path(__file__).parent.parent / "auto-claude") not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent / "auto-claude"))


def test_otel_exporter_initialization_enabled():
    """Test OTelExporter initializes when enabled."""
    with patch.dict('os.environ', {'OTEL_ENABLED': 'true'}):
        with patch('analytics.otel_exporter.OTLPMetricExporter'):
            with patch('analytics.otel_exporter.MeterProvider'):
                from analytics.otel_exporter import OTelExporter

                exporter = OTelExporter()

                assert exporter.enabled is True
                assert hasattr(exporter, 'meter')


def test_otel_exporter_initialization_disabled():
    """Test OTelExporter respects OTEL_ENABLED=false."""
    with patch.dict('os.environ', {'OTEL_ENABLED': 'false'}):
        from analytics.otel_exporter import OTelExporter

        exporter = OTelExporter()

        assert exporter.enabled is False


def test_otel_exporter_creates_instruments():
    """Test OTelExporter creates all required instruments."""
    with patch.dict('os.environ', {'OTEL_ENABLED': 'true'}):
        with patch('analytics.otel_exporter.OTLPMetricExporter'):
            with patch('analytics.otel_exporter.MeterProvider'):
                from analytics.otel_exporter import OTelExporter

                exporter = OTelExporter()

                # Check all instruments exist
                assert hasattr(exporter, 'token_counter')
                assert hasattr(exporter, 'cost_counter')
                assert hasattr(exporter, 'session_counter')
                assert hasattr(exporter, 'tokens_per_message')
                assert hasattr(exporter, 'cost_per_session')
                assert hasattr(exporter, 'session_duration')
                assert hasattr(exporter, 'active_sessions')


def test_otel_exporter_record_message():
    """Test recording message metrics."""
    with patch.dict('os.environ', {'OTEL_ENABLED': 'true'}):
        with patch('analytics.otel_exporter.OTLPMetricExporter'):
            with patch('analytics.otel_exporter.MeterProvider') as mock_provider:
                from analytics.otel_exporter import OTelExporter

                exporter = OTelExporter()

                # Mock instruments
                exporter.token_counter = MagicMock()
                exporter.cost_counter = MagicMock()
                exporter.tokens_per_message = MagicMock()

                # Record message
                exporter.record_message(
                    spec_id="001-test",
                    phase="coding",
                    model="claude-sonnet-4-5",
                    input_tokens=1000,
                    output_tokens=500,
                    cost_usd=0.025
                )

                # Verify metrics were recorded
                assert exporter.token_counter.add.called
                assert exporter.cost_counter.add.called
                assert exporter.tokens_per_message.record.called


def test_otel_exporter_record_session():
    """Test recording session metrics."""
    with patch.dict('os.environ', {'OTEL_ENABLED': 'true'}):
        with patch('analytics.otel_exporter.OTLPMetricExporter'):
            with patch('analytics.otel_exporter.MeterProvider'):
                from analytics.otel_exporter import OTelExporter

                exporter = OTelExporter()

                # Mock instruments
                exporter.session_counter = MagicMock()
                exporter.cost_per_session = MagicMock()
                exporter.session_duration = MagicMock()

                # Record session
                exporter.record_session(
                    spec_id="001-test",
                    phase="coding",
                    total_cost_usd=0.5,
                    duration_seconds=120.5
                )

                # Verify metrics were recorded
                assert exporter.session_counter.add.called
                assert exporter.cost_per_session.record.called
                assert exporter.session_duration.record.called


def test_otel_exporter_session_lifecycle():
    """Test session start/end tracking."""
    with patch.dict('os.environ', {'OTEL_ENABLED': 'true'}):
        with patch('analytics.otel_exporter.OTLPMetricExporter'):
            with patch('analytics.otel_exporter.MeterProvider'):
                from analytics.otel_exporter import OTelExporter

                exporter = OTelExporter()
                exporter.active_sessions = MagicMock()

                # Start session
                exporter.start_session()
                exporter.active_sessions.add.assert_called_with(1)

                # End session
                exporter.end_session()
                exporter.active_sessions.add.assert_called_with(-1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
