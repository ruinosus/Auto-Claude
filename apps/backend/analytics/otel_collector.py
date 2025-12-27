"""
OpenTelemetry Collector for Claude Code Telemetry
==================================================

Receives OTLP/HTTP telemetry from Claude Code and stores it in analytics.db.

Claude Code emits:
- Metrics: claude_code.token.usage, claude_code.cost.usage, etc.
- Events: claude_code.api_request with token details

This collector:
1. Listens on port 4318 (OTLP/HTTP)
2. Parses incoming OTLP protobuf/JSON messages
3. Extracts token usage from api_request events
4. Writes to analytics.db feature_sessions table

Configuration:
    OTEL_COLLECTOR_PORT=4318
    OTEL_COLLECTOR_HOST=127.0.0.1
"""

import asyncio
import json
import gzip
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    web = None


@dataclass
class TokenUsageRecord:
    """A single token usage record extracted from OTEL telemetry."""
    timestamp: datetime
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    cost_usd: float
    duration_ms: int = 0
    event_type: str = "api_request"


@dataclass
class CollectorStats:
    """Statistics for the OTEL collector."""
    requests_received: int = 0
    events_processed: int = 0
    records_written: int = 0
    errors: int = 0
    last_event_time: Optional[datetime] = None


class OTELCollector:
    """
    OTLP/HTTP receiver for Claude Code telemetry.

    Receives telemetry on port 4318 (configurable) and writes to analytics.db.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 4318
    ):
        self.host = host
        self.port = port
        self.db_path = db_path
        self.stats = CollectorStats()
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self._storage = None

        # Buffer for batching writes
        self._buffer: List[TokenUsageRecord] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_interval = 5  # seconds
        self._flush_task: Optional[asyncio.Task] = None

    async def _get_storage(self):
        """Lazy-load storage to avoid import issues."""
        if self._storage is None:
            from analytics.storage import get_analytics_storage
            self._storage = get_analytics_storage(self.db_path)
        return self._storage

    async def start(self):
        """Start the OTLP/HTTP collector server."""
        if not AIOHTTP_AVAILABLE:
            print("[OTEL_COLLECTOR] aiohttp not installed, collector disabled")
            return False

        self.app = web.Application()
        self._setup_routes()

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

        # Start periodic flush task
        self._flush_task = asyncio.create_task(self._periodic_flush())

        print(f"[OTEL_COLLECTOR] Started on http://{self.host}:{self.port}")
        print(f"[OTEL_COLLECTOR] OTLP endpoints:")
        print(f"  - POST /v1/logs    (OTLP logs/events)")
        print(f"  - POST /v1/metrics (OTLP metrics)")
        print(f"  - GET  /health     (health check)")
        print(f"  - GET  /stats      (collector stats)")

        return True

    async def stop(self):
        """Stop the collector server."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Flush remaining buffer
        await self._flush_buffer()

        if self.runner:
            await self.runner.cleanup()

        print(f"[OTEL_COLLECTOR] Stopped. Stats: {self.stats}")

    def _setup_routes(self):
        """Setup HTTP routes for OTLP endpoints."""
        self.app.router.add_post('/v1/logs', self._handle_logs)
        self.app.router.add_post('/v1/metrics', self._handle_metrics)
        self.app.router.add_get('/health', self._handle_health)
        self.app.router.add_get('/stats', self._handle_stats)
        # OTLP uses /v1/traces for traces, we don't need it but add for completeness
        self.app.router.add_post('/v1/traces', self._handle_traces)

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "ok", "service": "otel-collector"})

    async def _handle_stats(self, request: web.Request) -> web.Response:
        """Return collector statistics."""
        return web.json_response({
            "requests_received": self.stats.requests_received,
            "events_processed": self.stats.events_processed,
            "records_written": self.stats.records_written,
            "errors": self.stats.errors,
            "buffer_size": len(self._buffer),
            "last_event_time": self.stats.last_event_time.isoformat() if self.stats.last_event_time else None
        })

    async def _handle_traces(self, request: web.Request) -> web.Response:
        """Handle traces (not used by Claude Code, but good to have)."""
        return web.Response(status=200)

    async def _handle_logs(self, request: web.Request) -> web.Response:
        """
        Handle OTLP logs endpoint.

        Claude Code sends events (api_request, tool_result, etc.) as logs.
        """
        self.stats.requests_received += 1

        try:
            body = await self._read_body(request)
            data = self._parse_otlp(body, request.content_type)

            # Extract log records from OTLP format
            records = self._extract_log_records(data)

            for record in records:
                await self._process_log_record(record)
                self.stats.events_processed += 1

            self.stats.last_event_time = datetime.utcnow()
            return web.Response(status=200)

        except Exception as e:
            self.stats.errors += 1
            print(f"[OTEL_COLLECTOR] Error processing logs: {e}")
            return web.Response(status=500, text=str(e))

    async def _handle_metrics(self, request: web.Request) -> web.Response:
        """
        Handle OTLP metrics endpoint.

        Claude Code sends metrics like claude_code.token.usage.
        """
        self.stats.requests_received += 1

        try:
            body = await self._read_body(request)
            data = self._parse_otlp(body, request.content_type)

            # Extract metrics from OTLP format
            metrics = self._extract_metrics(data)

            for metric in metrics:
                await self._process_metric(metric)
                self.stats.events_processed += 1

            self.stats.last_event_time = datetime.utcnow()
            return web.Response(status=200)

        except Exception as e:
            self.stats.errors += 1
            print(f"[OTEL_COLLECTOR] Error processing metrics: {e}")
            return web.Response(status=500, text=str(e))

    async def _read_body(self, request: web.Request) -> bytes:
        """Read and decompress request body if needed."""
        body = await request.read()

        # Handle gzip compression
        if request.headers.get('Content-Encoding') == 'gzip':
            body = gzip.decompress(body)

        return body

    def _parse_otlp(self, body: bytes, content_type: str) -> Dict[str, Any]:
        """Parse OTLP body (JSON or protobuf)."""
        # For simplicity, we'll handle JSON format
        # Claude Code can use http/json protocol
        if 'json' in content_type or 'application/json' in content_type:
            return json.loads(body.decode('utf-8'))

        # For protobuf, we'd need opentelemetry-proto package
        # For now, try JSON parsing as fallback
        try:
            return json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            # If protobuf, we need the proto definitions
            # This is a simplified implementation
            print(f"[OTEL_COLLECTOR] Received protobuf data, JSON fallback failed")
            return {}

    def _extract_log_records(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract log records from OTLP logs format."""
        records = []

        # OTLP logs structure:
        # { "resourceLogs": [{ "scopeLogs": [{ "logRecords": [...] }] }] }
        resource_logs = data.get('resourceLogs', [])

        for resource_log in resource_logs:
            # Extract resource attributes (session_id, etc.)
            resource_attrs = self._extract_attributes(
                resource_log.get('resource', {}).get('attributes', [])
            )

            for scope_log in resource_log.get('scopeLogs', []):
                for log_record in scope_log.get('logRecords', []):
                    # Combine resource and log attributes
                    log_attrs = self._extract_attributes(
                        log_record.get('attributes', [])
                    )

                    records.append({
                        'timestamp': log_record.get('timeUnixNano', 0),
                        'body': log_record.get('body', {}),
                        'attributes': {**resource_attrs, **log_attrs},
                        'severity': log_record.get('severityText', 'INFO')
                    })

        return records

    def _extract_metrics(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract metrics from OTLP metrics format."""
        metrics = []

        # OTLP metrics structure:
        # { "resourceMetrics": [{ "scopeMetrics": [{ "metrics": [...] }] }] }
        resource_metrics = data.get('resourceMetrics', [])

        for resource_metric in resource_metrics:
            resource_attrs = self._extract_attributes(
                resource_metric.get('resource', {}).get('attributes', [])
            )

            for scope_metric in resource_metric.get('scopeMetrics', []):
                for metric in scope_metric.get('metrics', []):
                    metrics.append({
                        'name': metric.get('name', ''),
                        'description': metric.get('description', ''),
                        'unit': metric.get('unit', ''),
                        'data': metric,
                        'resource_attributes': resource_attrs
                    })

        return metrics

    def _extract_attributes(self, attrs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert OTLP attributes array to dict."""
        result = {}
        for attr in attrs:
            key = attr.get('key', '')
            value = attr.get('value', {})

            # OTLP values are typed: stringValue, intValue, doubleValue, etc.
            if 'stringValue' in value:
                result[key] = value['stringValue']
            elif 'intValue' in value:
                result[key] = int(value['intValue'])
            elif 'doubleValue' in value:
                result[key] = float(value['doubleValue'])
            elif 'boolValue' in value:
                result[key] = value['boolValue']
            else:
                result[key] = str(value)

        return result

    async def _process_log_record(self, record: Dict[str, Any]):
        """Process a single log record (event) from Claude Code."""
        attrs = record.get('attributes', {})
        body = record.get('body', {})

        # Get event name from body or attributes
        event_name = None
        if isinstance(body, dict):
            event_name = body.get('stringValue', '')
        elif isinstance(body, str):
            event_name = body

        # Also check attributes for event.name
        if not event_name:
            event_name = attrs.get('event.name', '')

        # Process api_request events - these contain token usage
        if 'api_request' in str(event_name) or attrs.get('event.name') == 'api_request':
            await self._process_api_request_event(attrs, record)

        # Also track other interesting events
        elif 'user_prompt' in str(event_name):
            # Could track prompt counts
            pass
        elif 'tool_result' in str(event_name):
            # Could track tool usage
            pass

    async def _process_api_request_event(self, attrs: Dict[str, Any], record: Dict[str, Any]):
        """
        Process api_request event containing token usage.

        Attributes:
        - model: Model used
        - cost_usd: Estimated cost
        - input_tokens: Number of input tokens
        - output_tokens: Number of output tokens
        - cache_read_tokens: Tokens read from cache
        - cache_creation_tokens: Tokens used for cache creation
        - duration_ms: Request duration
        """
        # Extract token usage
        usage_record = TokenUsageRecord(
            timestamp=datetime.utcnow(),
            session_id=attrs.get('session.id', attrs.get('session_id', 'unknown')),
            model=attrs.get('model', 'claude-sonnet-4-5'),
            input_tokens=int(attrs.get('input_tokens', 0)),
            output_tokens=int(attrs.get('output_tokens', 0)),
            cache_read_tokens=int(attrs.get('cache_read_tokens', 0)),
            cache_creation_tokens=int(attrs.get('cache_creation_tokens', 0)),
            cost_usd=float(attrs.get('cost_usd', 0)),
            duration_ms=int(attrs.get('duration_ms', 0)),
            event_type='api_request'
        )

        # Add to buffer
        async with self._buffer_lock:
            self._buffer.append(usage_record)

        print(f"[OTEL_COLLECTOR] Received: model={usage_record.model}, "
              f"in={usage_record.input_tokens}, out={usage_record.output_tokens}, "
              f"cost=${usage_record.cost_usd:.4f}")

    async def _process_metric(self, metric: Dict[str, Any]):
        """Process a metric from Claude Code."""
        name = metric.get('name', '')

        # Token usage metric
        if name == 'claude_code.token.usage':
            await self._process_token_usage_metric(metric)

        # Cost metric
        elif name == 'claude_code.cost.usage':
            await self._process_cost_metric(metric)

    async def _process_token_usage_metric(self, metric: Dict[str, Any]):
        """Process token usage counter metric."""
        data = metric.get('data', {})
        resource_attrs = metric.get('resource_attributes', {})

        # Sum metric has dataPoints
        sum_data = data.get('sum', {})
        data_points = sum_data.get('dataPoints', [])

        for point in data_points:
            attrs = self._extract_attributes(point.get('attributes', []))
            token_type = attrs.get('type', 'unknown')  # input, output, cacheRead, cacheCreation
            model = attrs.get('model', 'unknown')
            value = int(point.get('asInt', point.get('asDouble', 0)))

            # We'll aggregate these in the buffer
            print(f"[OTEL_COLLECTOR] Token metric: type={token_type}, model={model}, value={value}")

    async def _process_cost_metric(self, metric: Dict[str, Any]):
        """Process cost counter metric."""
        data = metric.get('data', {})

        sum_data = data.get('sum', {})
        data_points = sum_data.get('dataPoints', [])

        for point in data_points:
            attrs = self._extract_attributes(point.get('attributes', []))
            model = attrs.get('model', 'unknown')
            value = float(point.get('asDouble', 0))

            print(f"[OTEL_COLLECTOR] Cost metric: model={model}, value=${value:.4f}")

    async def _periodic_flush(self):
        """Periodically flush buffer to database."""
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush_buffer()

    async def _flush_buffer(self):
        """Flush buffered records to database."""
        async with self._buffer_lock:
            if not self._buffer:
                return

            records = self._buffer.copy()
            self._buffer.clear()

        try:
            storage = await self._get_storage()

            # Aggregate records by session
            session_totals: Dict[str, Dict[str, Any]] = {}

            for record in records:
                key = record.session_id
                if key not in session_totals:
                    session_totals[key] = {
                        'session_id': record.session_id,
                        'model': record.model,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'cache_read_tokens': 0,
                        'cache_creation_tokens': 0,
                        'cost_usd': 0.0,
                        'first_seen': record.timestamp,
                        'last_seen': record.timestamp,
                        'request_count': 0
                    }

                totals = session_totals[key]
                totals['input_tokens'] += record.input_tokens
                totals['output_tokens'] += record.output_tokens
                totals['cache_read_tokens'] += record.cache_read_tokens
                totals['cache_creation_tokens'] += record.cache_creation_tokens
                totals['cost_usd'] += record.cost_usd
                totals['last_seen'] = max(totals['last_seen'], record.timestamp)
                totals['request_count'] += 1

            # Write to database
            for session_id, totals in session_totals.items():
                # Use terminal feature type for Claude Code sessions
                await storage.upsert_terminal_session(
                    session_id=session_id,
                    model=totals['model'],
                    input_tokens=totals['input_tokens'],
                    output_tokens=totals['output_tokens'],
                    cache_read_tokens=totals['cache_read_tokens'],
                    cache_creation_tokens=totals['cache_creation_tokens'],
                    cost_usd=totals['cost_usd'],
                    started_at=totals['first_seen'],
                    ended_at=totals['last_seen'],
                    request_count=totals['request_count']
                )
                self.stats.records_written += 1

            print(f"[OTEL_COLLECTOR] Flushed {len(records)} records for {len(session_totals)} sessions")

        except Exception as e:
            self.stats.errors += 1
            print(f"[OTEL_COLLECTOR] Error flushing buffer: {e}")
            # Put records back in buffer for retry
            async with self._buffer_lock:
                self._buffer.extend(records)


# Global collector instance
_collector: Optional[OTELCollector] = None


async def start_collector(
    db_path: Optional[str] = None,
    host: str = "127.0.0.1",
    port: int = 4318
) -> OTELCollector:
    """Start the OTEL collector."""
    global _collector

    if _collector is not None:
        return _collector

    _collector = OTELCollector(db_path=db_path, host=host, port=port)
    await _collector.start()

    return _collector


async def stop_collector():
    """Stop the OTEL collector."""
    global _collector

    if _collector is not None:
        await _collector.stop()
        _collector = None


def get_collector() -> Optional[OTELCollector]:
    """Get the running collector instance."""
    return _collector


# CLI entry point
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Claude Code OTEL Collector')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=4318, help='Port to listen on')
    parser.add_argument('--db', help='Path to analytics.db')

    args = parser.parse_args()

    async def main():
        collector = await start_collector(
            db_path=args.db,
            host=args.host,
            port=args.port
        )

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await stop_collector()

    asyncio.run(main())
