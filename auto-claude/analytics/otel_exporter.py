"""
OpenTelemetry Exporter for Auto-Claude Analytics
================================================

Exports analytics data as OpenTelemetry metrics to OTLP backends.
"""

import os
from typing import Optional
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource


class OTelExporter:
    """
    OpenTelemetry exporter for Auto-Claude analytics.

    Exports:
    - Metrics: Token counts, costs, session durations
    - Attributes: spec_id, phase, model, session_number
    """

    def __init__(self):
        self.enabled = os.getenv('OTEL_ENABLED', 'true').lower() == 'true'

        if not self.enabled:
            self.meter = None
            return

        # Resource attributes
        resource = Resource.create({
            "service.name": os.getenv('OTEL_SERVICE_NAME', 'auto-claude'),
            "service.version": "1.0.0",
            "deployment.environment": os.getenv('ENVIRONMENT', 'production')
        })

        # Metrics setup
        otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317')
        metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)

        export_interval_seconds = int(os.getenv('OTEL_EXPORT_INTERVAL_SECONDS', '60'))
        metric_reader = PeriodicExportingMetricReader(
            exporter=metric_exporter,
            export_interval_millis=export_interval_seconds * 1000
        )

        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )

        metrics.set_meter_provider(meter_provider)
        self.meter = metrics.get_meter("auto-claude")

        # Create instruments
        self._create_instruments()

    def _create_instruments(self):
        """Create OpenTelemetry metric instruments."""
        if not self.enabled or not self.meter:
            return

        # Counters (cumulative totals)
        self.token_counter = self.meter.create_counter(
            name="auto_claude.tokens.total",
            description="Total tokens consumed",
            unit="tokens"
        )

        self.cost_counter = self.meter.create_counter(
            name="auto_claude.cost.total_usd",
            description="Total cost in USD",
            unit="USD"
        )

        self.session_counter = self.meter.create_counter(
            name="auto_claude.sessions.total",
            description="Total agent sessions",
            unit="sessions"
        )

        # Histograms (distributions)
        self.tokens_per_message = self.meter.create_histogram(
            name="auto_claude.tokens.per_message",
            description="Token distribution per message",
            unit="tokens"
        )

        self.cost_per_session = self.meter.create_histogram(
            name="auto_claude.cost.per_session_usd",
            description="Cost distribution per session",
            unit="USD"
        )

        self.session_duration = self.meter.create_histogram(
            name="auto_claude.session.duration_seconds",
            description="Session duration in seconds",
            unit="seconds"
        )

        # UpDownCounter (current values)
        self.active_sessions = self.meter.create_up_down_counter(
            name="auto_claude.sessions.active",
            description="Number of active sessions",
            unit="sessions"
        )


# Singleton instance
_otel_exporter: Optional[OTelExporter] = None


def get_otel_exporter() -> OTelExporter:
    """Get global OTel exporter instance."""
    global _otel_exporter
    if _otel_exporter is None:
        _otel_exporter = OTelExporter()
    return _otel_exporter


def is_otel_enabled() -> bool:
    """Check if OpenTelemetry export is enabled."""
    return os.getenv('OTEL_ENABLED', 'true').lower() == 'true'
