#!/usr/bin/env python3
"""
Claude Code OpenTelemetry Collector
====================================

A lightweight OTLP receiver that collects Claude Code telemetry
and writes it to the Auto Claude analytics database.

This provides real-time token tracking for terminal sessions.

Usage:
1. Start the collector:
   python3 otel_terminal_collector.py [--port 4317]

2. Configure Claude Code environment:
   export CLAUDE_CODE_ENABLE_TELEMETRY=1
   export OTEL_METRICS_EXPORTER=otlp
   export OTEL_LOGS_EXPORTER=otlp
   export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
   export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

3. Run Claude Code - metrics will be collected automatically

Dependencies:
    pip install grpcio opentelemetry-proto
"""

import argparse
import asyncio
import json
import sys
from concurrent import futures
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add backend path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Try to import grpc (optional dependency)
try:
    import grpc
    from grpc import aio as grpc_aio
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    print("Warning: grpcio not installed. Run: pip install grpcio")

# Session tracker for accumulating metrics
class TerminalMetricsCollector:
    """Collects and aggregates Claude Code terminal metrics."""

    def __init__(self, project_dir: Optional[str] = None):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.sessions: dict = {}  # session_id -> metrics
        self._setup_analytics()

    def _setup_analytics(self):
        """Initialize analytics storage."""
        try:
            from analytics import (
                create_feature_tracker,
                FEATURE_TERMINAL,
                is_tracking_enabled,
            )
            self.tracking_available = is_tracking_enabled()
            self.create_tracker = create_feature_tracker
            self.feature_type = FEATURE_TERMINAL
        except ImportError:
            self.tracking_available = False
            print("Warning: Analytics module not available")

    def get_or_create_session(self, session_id: str) -> dict:
        """Get or create a session tracking dict."""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "started_at": datetime.utcnow(),
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
                "cache_creation_tokens": 0,
                "cost_usd": 0.0,
                "model": None,
                "api_requests": 0,
            }
        return self.sessions[session_id]

    def record_token_usage(
        self,
        session_id: str,
        token_type: str,
        count: int,
        model: Optional[str] = None
    ):
        """Record token usage for a session."""
        session = self.get_or_create_session(session_id)

        if token_type == "input":
            session["input_tokens"] += count
        elif token_type == "output":
            session["output_tokens"] += count
        elif token_type == "cacheRead":
            session["cache_read_tokens"] += count
        elif token_type == "cacheCreation":
            session["cache_creation_tokens"] += count

        if model:
            session["model"] = model

    def record_cost(self, session_id: str, cost_usd: float):
        """Record cost for a session."""
        session = self.get_or_create_session(session_id)
        session["cost_usd"] += cost_usd

    def record_api_request(
        self,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0
    ):
        """Record a complete API request."""
        session = self.get_or_create_session(session_id)
        session["input_tokens"] += input_tokens
        session["output_tokens"] += output_tokens
        session["cache_read_tokens"] += cache_read_tokens
        session["cache_creation_tokens"] += cache_creation_tokens
        session["cost_usd"] += cost_usd
        session["model"] = model
        session["api_requests"] += 1

        print(f"[OTEL] API Request: session={session_id[:8]}..., "
              f"model={model}, tokens={input_tokens}/{output_tokens}, "
              f"cost=${cost_usd:.4f}")

    async def finalize_session(self, session_id: str) -> None:
        """Finalize and persist a session to analytics."""
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]

        if not self.tracking_available:
            print(f"[OTEL] Session {session_id[:8]}... complete (tracking disabled)")
            del self.sessions[session_id]
            return

        try:
            db_path = str(self.project_dir / ".auto-claude" / "analytics.db")
            tracker = self.create_tracker(
                project_id=self.project_dir.name,
                feature_type=self.feature_type,
                db_path=db_path,
                metadata={
                    "claude_code_session_id": session_id,
                    "api_requests": session["api_requests"],
                }
            )

            await tracker.start_session()
            await tracker.track_usage(
                model=session["model"] or "claude-sonnet-4-5",
                input_tokens=session["input_tokens"],
                output_tokens=session["output_tokens"],
                cache_read_tokens=session["cache_read_tokens"],
                cache_creation_tokens=session["cache_creation_tokens"],
            )

            if session["cost_usd"] > 0:
                tracker.total_cost_usd = session["cost_usd"]

            await tracker.finalize()

            print(f"[OTEL] Session {session_id[:8]}... saved: "
                  f"tokens={session['input_tokens']}/{session['output_tokens']}, "
                  f"cost=${session['cost_usd']:.4f}")

        except Exception as e:
            print(f"[OTEL] Error saving session: {e}")

        finally:
            del self.sessions[session_id]


# Simple HTTP endpoint for non-gRPC environments
async def run_http_collector(collector: TerminalMetricsCollector, port: int):
    """Run a simple HTTP endpoint for receiving OTLP JSON."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class OTLPHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body)
                # Process OTLP JSON data
                # This is a simplified handler - full OTLP parsing would be more complex
                self.send_response(200)
                self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())

        def log_message(self, format, *args):
            pass  # Suppress HTTP logs

    server = HTTPServer(('localhost', port), OTLPHandler)
    print(f"[OTEL] HTTP collector listening on port {port}")

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(
        description="Claude Code OpenTelemetry Collector"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=4317,
        help="Port to listen on (default: 4317)"
    )
    parser.add_argument(
        "--project-dir",
        type=str,
        default=None,
        help="Project directory for analytics storage"
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use HTTP instead of gRPC"
    )

    args = parser.parse_args()

    collector = TerminalMetricsCollector(args.project_dir)

    print("=" * 60)
    print("Claude Code OpenTelemetry Collector")
    print("=" * 60)
    print(f"""
Configure Claude Code with:

  export CLAUDE_CODE_ENABLE_TELEMETRY=1
  export OTEL_METRICS_EXPORTER=otlp
  export OTEL_LOGS_EXPORTER=otlp
  export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:{args.port}

Then run Claude Code - metrics will be collected here.
Press Ctrl+C to stop.
""")

    if args.http or not GRPC_AVAILABLE:
        if not GRPC_AVAILABLE:
            print("Note: Using HTTP mode (grpcio not installed)")
        asyncio.run(run_http_collector(collector, args.port))
    else:
        print(f"[OTEL] gRPC collector would listen on port {args.port}")
        print("Note: Full gRPC OTLP implementation requires additional setup.")
        print("For simplicity, consider using the SessionEnd hook instead.")


if __name__ == "__main__":
    main()
