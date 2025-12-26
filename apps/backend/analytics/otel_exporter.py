"""
OpenTelemetry Exporter for Auto-Claude Analytics
================================================

Exports analytics data as OpenTelemetry metrics to OTLP backends.
"""

import os
from typing import Optional

# OpenTelemetry imports are optional - graceful degradation if not installed
try:
    from opentelemetry import metrics
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class OTelExporter:
    """
    OpenTelemetry exporter for Auto-Claude analytics.

    Exports:
    - Metrics: Token counts, costs, session durations
    - Attributes: spec_id, phase, model
    """

    def __init__(self):
        self.enabled = (
            OTEL_AVAILABLE and
            os.getenv('OTEL_ENABLED', 'false').lower() == 'true'
        )

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

    def record_message(
        self,
        spec_id: str,
        phase: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float
    ):
        """Record message-level metrics."""
        if not self.enabled:
            return

        attributes = {
            "spec_id": spec_id,
            "phase": phase,
            "model": model
        }

        total_tokens = input_tokens + output_tokens

        # Update counters
        self.token_counter.add(total_tokens, attributes)
        self.cost_counter.add(cost_usd, attributes)

        # Update histograms
        self.tokens_per_message.record(total_tokens, attributes)

    def record_session(
        self,
        spec_id: str,
        phase: str,
        total_cost_usd: float,
        duration_seconds: float
    ):
        """Record session-level metrics."""
        if not self.enabled:
            return

        attributes = {
            "spec_id": spec_id,
            "phase": phase
        }

        self.session_counter.add(1, attributes)
        self.cost_per_session.record(total_cost_usd, attributes)
        self.session_duration.record(duration_seconds, attributes)

    def start_session(self):
        """Increment active session counter."""
        if not self.enabled:
            return
        self.active_sessions.add(1)

    def end_session(self):
        """Decrement active session counter."""
        if not self.enabled:
            return
        self.active_sessions.add(-1)


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
    return (
        OTEL_AVAILABLE and
        os.getenv('OTEL_ENABLED', 'false').lower() == 'true'
    )
