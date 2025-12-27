#!/usr/bin/env python3
"""
Start the OTEL Collector for Claude Code telemetry.

This script starts the OTLP/HTTP receiver that accepts telemetry from Claude Code
and writes it to analytics.db.

Usage:
    python start_otel_collector.py [--port 4318] [--db /path/to/analytics.db]

Environment Variables (set these for Claude Code):
    CLAUDE_CODE_ENABLE_TELEMETRY=1
    OTEL_METRICS_EXPORTER=otlp
    OTEL_LOGS_EXPORTER=otlp
    OTEL_EXPORTER_OTLP_PROTOCOL=http/json
    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
"""

import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.otel_collector import start_collector, stop_collector


async def main(host: str, port: int, db_path: str):
    """Main entry point for the OTEL collector."""
    print("=" * 60)
    print("Claude Code OTEL Collector")
    print("=" * 60)
    print()
    print("Configuration:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Database: {db_path}")
    print()
    print("To enable telemetry in Claude Code, add to your shell:")
    print()
    print("  export CLAUDE_CODE_ENABLE_TELEMETRY=1")
    print("  export OTEL_METRICS_EXPORTER=otlp")
    print("  export OTEL_LOGS_EXPORTER=otlp")
    print("  export OTEL_EXPORTER_OTLP_PROTOCOL=http/json")
    print(f"  export OTEL_EXPORTER_OTLP_ENDPOINT=http://{host}:{port}")
    print()
    print("=" * 60)
    print()

    # Start the collector
    collector = await start_collector(
        db_path=db_path,
        host=host,
        port=port
    )

    if not collector:
        print("[ERROR] Failed to start collector")
        return

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        print("\n[OTEL_COLLECTOR] Received shutdown signal...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Wait for shutdown signal
    await stop_event.wait()

    # Cleanup
    await stop_collector()
    print("[OTEL_COLLECTOR] Shutdown complete")


def run():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Claude Code OTEL Collector - Receives telemetry and writes to analytics.db"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("OTEL_COLLECTOR_HOST", "127.0.0.1"),
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("OTEL_COLLECTOR_PORT", "4318")),
        help="Port to listen on (default: 4318)"
    )
    parser.add_argument(
        "--db",
        default=os.getenv("ANALYTICS_DB_PATH", ".auto-claude/analytics.db"),
        help="Path to analytics.db (default: .auto-claude/analytics.db)"
    )

    args = parser.parse_args()

    try:
        asyncio.run(main(args.host, args.port, args.db))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
