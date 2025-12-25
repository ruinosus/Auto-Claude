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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
