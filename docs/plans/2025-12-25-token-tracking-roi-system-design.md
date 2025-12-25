# Token Tracking & ROI System - Design Document

**Date:** 2025-12-25
**Status:** Design Phase
**Owner:** Auto-Claude Team

---

## Executive Summary

This document describes the design of a comprehensive token tracking and ROI measurement system for Auto-Claude. The system provides multi-level usage analytics (billing, optimization, analytics/reporting) with professional-grade observability through OpenTelemetry integration and an integrated Electron UI dashboard.

**Key Features:**
- ✅ Multi-level granularity: Session → Subtask → Individual prompts
- ✅ Dual storage: SQLite for queries + JSON for backup/portability
- ✅ OpenTelemetry integration with flexible backend support (Langfuse, SigNoz, Grafana, etc.)
- ✅ Integrated Electron UI dashboard with real-time metrics
- ✅ Opt-out by default (professional behavior)
- ✅ Zero breaking changes to existing functionality

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Data Collection Layer](#data-collection-layer)
3. [Storage Layer](#storage-layer)
4. [OpenTelemetry Integration](#opentelemetry-integration)
5. [Electron UI Dashboard](#electron-ui-dashboard)
6. [Configuration & API](#configuration--api)
7. [Implementation Plan](#implementation-plan)
8. [Testing Strategy](#testing-strategy)
9. [Rollout Plan](#rollout-plan)

---

## Architecture Overview

### High-Level Design

The system consists of **three primary layers** working together:

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Electron UI  │  │ CLI Commands │  │ Python API   │     │
│  │  Dashboard   │  │  (run.py)    │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              VISUALIZATION & EXPORT LAYER                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Recharts   │  │     OTLP     │  │  CSV/JSON    │     │
│  │   Graphs     │  │   Exporter   │  │   Export     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   STORAGE LAYER                             │
│  ┌──────────────────────────┐  ┌──────────────────────┐    │
│  │   SQLite Database        │  │   JSON Files         │    │
│  │   analytics.db           │  │   usage.json         │    │
│  │   (queries, aggregation) │  │   (backup, portable) │    │
│  └──────────────────────────┘  └──────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │
┌─────────────────────────────────────────────────────────────┐
│              DATA COLLECTION LAYER                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  UsageTracker (session.py integration)               │  │
│  │  - Intercepts AssistantMessage.usage                 │  │
│  │  - Tracks ResultMessage.total_cost_usd               │  │
│  │  - Enriches with context (spec, session, subtask)    │  │
│  │  - Deduplicates messages with same ID               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │
                   Claude Agent SDK
```

### Core Components

#### 1. Data Collection Layer
- **Location:** `auto-claude/analytics/usage_tracker.py`
- **Purpose:** Intercept and capture token usage from Claude Agent SDK
- **Integration Point:** `auto-claude/agents/session.py` (message receive loop)
- **Performance:** <0.1ms overhead per message

#### 2. Storage Layer
- **Primary:** SQLite database (`.auto-claude/analytics.db`)
- **Secondary:** JSON files (`.auto-claude/specs/{id}/memory/usage.json`)
- **Sync Strategy:** Bidirectional (JSON → SQLite on startup, SQLite → JSON on session end)
- **Graceful Degradation:** Falls back to JSON-only if SQLite unavailable

#### 3. Visualization & Export Layer
- **Electron UI:** Integrated dashboard with charts and tables
- **OpenTelemetry:** OTLP exporter for external platforms
- **CLI/API:** Programmatic access to analytics data

### Design Principles

1. **Opt-out by default** - Tracking enabled unless `DISABLE_TOKEN_TRACKING=true`
2. **Zero breaking changes** - Existing functionality unaffected
3. **Minimal performance overhead** - Async writes, batched operations
4. **Multi-level granularity** - Track at session, subtask, and message levels
5. **Flexible backends** - Support multiple observability platforms
6. **Human-readable backups** - JSON files for portability and debugging

---

## Data Collection Layer

### Implementation Location

**Primary Module:** `auto-claude/analytics/usage_tracker.py`

**Integration Point:** `auto-claude/agents/session.py` (lines 354-515)

### UsageTracker Class

```python
from typing import Optional
from datetime import datetime
from claude_agent_sdk import AssistantMessage, ResultMessage

class UsageTracker:
    """
    Tracks token usage and costs during Claude Agent SDK sessions.

    Features:
    - Deduplicates messages with same ID
    - Enriches data with context (spec, session, subtask, phase)
    - Calculates costs based on pricing models
    - Async writes to minimize performance impact
    """

    def __init__(
        self,
        spec_id: str,
        session_num: int,
        phase: str,
        storage: 'AnalyticsStorage'
    ):
        self.spec_id = spec_id
        self.session_num = session_num
        self.phase = phase  # planning, coding, validation
        self.storage = storage

        # Deduplication
        self.message_ids_seen: set[str] = set()

        # Context
        self.current_subtask_id: Optional[str] = None
        self.conversation_id: Optional[int] = None

        # Session totals
        self.session_start = datetime.utcnow()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0

    async def track_message(self, message: AssistantMessage | ResultMessage):
        """Track token usage from Claude Agent SDK message."""

        # AssistantMessage: individual message-level tracking
        if isinstance(message, AssistantMessage) and message.usage:
            # Skip duplicates (same message ID reported multiple times)
            if message.id in self.message_ids_seen:
                return
            self.message_ids_seen.add(message.id)

            # Extract usage data
            usage = message.usage
            input_tokens = usage.get('input_tokens', 0) or 0
            output_tokens = usage.get('output_tokens', 0) or 0
            cache_read = usage.get('cache_read_input_tokens', 0) or 0
            cache_creation = usage.get('cache_creation_input_tokens', 0) or 0

            # Calculate cost
            cost_usd = self._calculate_cost(
                model=message.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read,
                cache_creation_tokens=cache_creation
            )

            # Record message-level data
            await self.storage.record_message(
                conversation_id=self.conversation_id,
                message_id=message.id,
                subtask_id=self.current_subtask_id,
                timestamp=datetime.utcnow(),
                model=message.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read,
                cache_creation_tokens=cache_creation,
                cost_usd=cost_usd
            )

            # Update session totals
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.total_cost_usd += cost_usd

        # ResultMessage: conversation-level totals
        elif isinstance(message, ResultMessage):
            # Record final conversation totals
            await self.storage.update_conversation_totals(
                conversation_id=self.conversation_id,
                ended_at=datetime.utcnow(),
                total_cost_usd=message.total_cost_usd or self.total_cost_usd,
                total_input_tokens=self.total_input_tokens,
                total_output_tokens=self.total_output_tokens
            )

    async def start_conversation(self) -> int:
        """Initialize conversation tracking. Returns conversation_id."""
        self.conversation_id = await self.storage.create_conversation(
            spec_id=self.spec_id,
            session_number=self.session_num,
            phase=self.phase,
            started_at=self.session_start
        )
        return self.conversation_id

    def set_subtask(self, subtask_id: str):
        """Update current subtask context."""
        self.current_subtask_id = subtask_id

    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int,
        cache_creation_tokens: int
    ) -> float:
        """Calculate cost in USD based on model pricing."""
        from auto_claude.analytics.pricing import get_model_pricing

        pricing = get_model_pricing(model)

        # Base costs (per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing.input_price
        output_cost = (output_tokens / 1_000_000) * pricing.output_price

        # Cache costs (with discount)
        cache_read_cost = (cache_read_tokens / 1_000_000) * pricing.input_price * pricing.cache_read_discount
        cache_creation_cost = (cache_creation_tokens / 1_000_000) * pricing.cache_creation_price

        return input_cost + output_cost + cache_read_cost + cache_creation_cost
```

### Integration with session.py

**Modified code in `auto-claude/agents/session.py`:**

```python
# Line ~340: Initialize tracker before session loop
from auto_claude.analytics import UsageTracker, get_analytics_storage, is_tracking_enabled

async def run_agent_session(...):
    # ... existing code ...

    # Initialize usage tracking (if enabled)
    tracker = None
    if is_tracking_enabled():
        storage = get_analytics_storage()
        tracker = UsageTracker(
            spec_id=spec_id,
            session_num=session_number,
            phase=phase,  # planning, coding, or validation
            storage=storage
        )
        await tracker.start_conversation()

    # Line ~350: Message receive loop
    message_count = 0
    tool_count = 0
    response_text = ""

    async for msg in client.receive_response():
        message_count += 1

        # Track token usage (async, non-blocking)
        if tracker:
            asyncio.create_task(tracker.track_message(msg))

        # ... existing message handling code ...

        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    response_text += block.text
                # ... existing tool handling ...

    # Line ~525: Session end - flush tracker
    if tracker:
        await tracker.storage.flush()

    # ... existing return statement ...
```

### Subtask Context Updates

**In `auto-claude/agents/coder.py`:**

```python
# Line ~300: Before processing each subtask
if tracker:
    tracker.set_subtask(current_subtask.id)
```

### Data Captured Per Message

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `message_id` | String | Claude message UUID | `AssistantMessage.id` |
| `timestamp` | Datetime | When message received | `datetime.utcnow()` |
| `spec_id` | String | Current spec identifier | Session context |
| `session_number` | Integer | Session number within spec | Session context |
| `phase` | String | planning/coding/validation | Session context |
| `subtask_id` | String | Current subtask ID (nullable) | Coder agent context |
| `model` | String | Claude model name | `AssistantMessage.model` |
| `input_tokens` | Integer | Input tokens consumed | `message.usage.input_tokens` |
| `output_tokens` | Integer | Output tokens generated | `message.usage.output_tokens` |
| `cache_read_tokens` | Integer | Cache read tokens | `message.usage.cache_read_input_tokens` |
| `cache_creation_tokens` | Integer | Cache creation tokens | `message.usage.cache_creation_input_tokens` |
| `cost_usd` | Float | Calculated cost in USD | Computed from pricing model |

---

## Storage Layer

### Dual Persistence Architecture

**Philosophy:**
- **SQLite = Performance** (fast queries, aggregations, dashboard)
- **JSON = Portability** (backup, human-readable, cross-platform)

### SQLite Schema

**Location:** `.auto-claude/analytics.db`

**Module:** `auto-claude/analytics/storage.py`

#### Table: `conversations`

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id TEXT NOT NULL,
    session_number INTEGER NOT NULL,
    phase TEXT NOT NULL CHECK(phase IN ('planning', 'coding', 'validation')),
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    total_cost_usd REAL DEFAULT 0.0,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(spec_id, session_number)
);

CREATE INDEX idx_conversations_spec ON conversations(spec_id);
CREATE INDEX idx_conversations_phase ON conversations(phase);
CREATE INDEX idx_conversations_started ON conversations(started_at);
```

#### Table: `messages`

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    message_id TEXT UNIQUE NOT NULL,
    subtask_id TEXT,
    timestamp TIMESTAMP NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_creation_tokens INTEGER DEFAULT 0,
    cost_usd REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
CREATE INDEX idx_messages_subtask ON messages(subtask_id);
CREATE INDEX idx_messages_model ON messages(model);
```

#### Table: `spec_totals` (Materialized View)

```sql
CREATE TABLE spec_totals (
    spec_id TEXT PRIMARY KEY,
    total_conversations INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to update spec_totals when conversations change
CREATE TRIGGER update_spec_totals_after_conversation
AFTER UPDATE ON conversations
FOR EACH ROW
BEGIN
    INSERT INTO spec_totals (spec_id, total_conversations, total_cost_usd, total_input_tokens, total_output_tokens, last_updated)
    VALUES (
        NEW.spec_id,
        1,
        NEW.total_cost_usd,
        NEW.total_input_tokens,
        NEW.total_output_tokens,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT(spec_id) DO UPDATE SET
        total_conversations = total_conversations + 1,
        total_cost_usd = total_cost_usd + NEW.total_cost_usd,
        total_input_tokens = total_input_tokens + NEW.total_input_tokens,
        total_output_tokens = total_output_tokens + NEW.total_output_tokens,
        last_updated = CURRENT_TIMESTAMP;
END;
```

#### Table: `daily_aggregates` (Pre-computed Analytics)

```sql
CREATE TABLE daily_aggregates (
    date DATE NOT NULL,
    spec_id TEXT,
    phase TEXT,
    model TEXT,
    total_cost_usd REAL DEFAULT 0.0,
    total_tokens INTEGER DEFAULT 0,
    conversation_count INTEGER DEFAULT 0,
    PRIMARY KEY (date, spec_id, phase, model)
);

CREATE INDEX idx_daily_date ON daily_aggregates(date);
```

### JSON Backup Format

**Location:** `.auto-claude/specs/{spec-id}/memory/usage.json`

```json
{
  "spec_id": "001-azure-foundry-integration",
  "total_cost_usd": 1.2345,
  "total_sessions": 15,
  "created_at": "2025-12-20T10:00:00Z",
  "updated_at": "2025-12-25T15:30:00Z",
  "sessions": [
    {
      "session_number": 1,
      "phase": "planning",
      "started_at": "2025-12-20T10:00:00Z",
      "ended_at": "2025-12-20T10:15:00Z",
      "total_cost_usd": 0.0245,
      "total_input_tokens": 1500,
      "total_output_tokens": 800,
      "model": "claude-sonnet-4-5",
      "messages": [
        {
          "message_id": "msg_abc123xyz",
          "timestamp": "2025-12-20T10:00:15Z",
          "subtask_id": null,
          "model": "claude-sonnet-4-5",
          "input_tokens": 500,
          "output_tokens": 200,
          "cache_read_tokens": 0,
          "cache_creation_tokens": 100,
          "cost_usd": 0.0085
        },
        {
          "message_id": "msg_def456uvw",
          "timestamp": "2025-12-20T10:05:30Z",
          "subtask_id": "subtask-001",
          "model": "claude-sonnet-4-5",
          "input_tokens": 1000,
          "output_tokens": 600,
          "cache_read_tokens": 500,
          "cache_creation_tokens": 0,
          "cost_usd": 0.0160
        }
      ]
    }
  ]
}
```

### AnalyticsStorage Class

```python
import sqlite3
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

class AnalyticsStorage:
    """
    Handles dual persistence: SQLite + JSON backup.

    Guarantees:
    - Atomic writes
    - Bidirectional sync
    - Graceful degradation (SQLite failure → JSON-only mode)
    """

    def __init__(self, db_path: str = ".auto-claude/analytics.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables (schema defined above)
        cursor.executescript(SCHEMA_SQL)

        conn.commit()
        conn.close()

    async def create_conversation(
        self,
        spec_id: str,
        session_number: int,
        phase: str,
        started_at: datetime
    ) -> int:
        """Create new conversation record. Returns conversation_id."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO conversations (spec_id, session_number, phase, started_at)
            VALUES (?, ?, ?, ?)
        """, (spec_id, session_number, phase, started_at.isoformat()))

        conversation_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return conversation_id

    async def record_message(
        self,
        conversation_id: int,
        message_id: str,
        subtask_id: Optional[str],
        timestamp: datetime,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int,
        cache_creation_tokens: int,
        cost_usd: float
    ):
        """Record individual message usage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO messages (
                    conversation_id, message_id, subtask_id, timestamp,
                    model, input_tokens, output_tokens,
                    cache_read_tokens, cache_creation_tokens, cost_usd
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id, message_id, subtask_id, timestamp.isoformat(),
                model, input_tokens, output_tokens,
                cache_read_tokens, cache_creation_tokens, cost_usd
            ))

            conn.commit()
        except sqlite3.IntegrityError:
            # Duplicate message_id (already tracked)
            pass
        finally:
            conn.close()

    async def update_conversation_totals(
        self,
        conversation_id: int,
        ended_at: datetime,
        total_cost_usd: float,
        total_input_tokens: int,
        total_output_tokens: int
    ):
        """Update conversation with final totals."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE conversations
            SET
                ended_at = ?,
                total_cost_usd = ?,
                total_input_tokens = ?,
                total_output_tokens = ?
            WHERE id = ?
        """, (ended_at.isoformat(), total_cost_usd, total_input_tokens, total_output_tokens, conversation_id))

        conn.commit()
        conn.close()

    async def export_to_json(self, spec_id: str, output_path: Path):
        """Export spec data to JSON file."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all conversations for this spec
        cursor.execute("""
            SELECT * FROM conversations
            WHERE spec_id = ?
            ORDER BY session_number
        """, (spec_id,))

        conversations = cursor.fetchall()

        sessions = []
        total_cost = 0.0

        for conv in conversations:
            # Get messages for this conversation
            cursor.execute("""
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp
            """, (conv['id'],))

            messages = [dict(msg) for msg in cursor.fetchall()]

            session_data = dict(conv)
            session_data['messages'] = messages
            sessions.append(session_data)
            total_cost += conv['total_cost_usd'] or 0.0

        # Write JSON
        json_data = {
            "spec_id": spec_id,
            "total_cost_usd": total_cost,
            "total_sessions": len(sessions),
            "created_at": datetime.utcnow().isoformat(),
            "sessions": sessions
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(json_data, f, indent=2)

        conn.close()

    async def import_from_json(self, json_path: Path):
        """Import JSON data into SQLite (for migration/recovery)."""
        with open(json_path) as f:
            data = json.load(f)

        for session in data.get('sessions', []):
            conversation_id = await self.create_conversation(
                spec_id=data['spec_id'],
                session_number=session['session_number'],
                phase=session['phase'],
                started_at=datetime.fromisoformat(session['started_at'])
            )

            for msg in session.get('messages', []):
                await self.record_message(
                    conversation_id=conversation_id,
                    message_id=msg['message_id'],
                    subtask_id=msg.get('subtask_id'),
                    timestamp=datetime.fromisoformat(msg['timestamp']),
                    model=msg['model'],
                    input_tokens=msg['input_tokens'],
                    output_tokens=msg['output_tokens'],
                    cache_read_tokens=msg.get('cache_read_tokens', 0),
                    cache_creation_tokens=msg.get('cache_creation_tokens', 0),
                    cost_usd=msg['cost_usd']
                )

            await self.update_conversation_totals(
                conversation_id=conversation_id,
                ended_at=datetime.fromisoformat(session['ended_at']),
                total_cost_usd=session['total_cost_usd'],
                total_input_tokens=session['total_input_tokens'],
                total_output_tokens=session['total_output_tokens']
            )

    async def flush(self):
        """Flush any pending writes (currently no-op, writes are immediate)."""
        pass
```

### Sync Strategy

**On Session Start:**
1. Check if SQLite DB exists
2. If not, scan for JSON files in specs and import them
3. Use SQLite as primary during session

**During Session:**
1. All writes go to SQLite (fast, transactional)
2. No JSON writes (avoid I/O overhead)

**On Session End:**
1. Export conversation data from SQLite → JSON
2. Write to `.auto-claude/specs/{spec-id}/memory/usage.json`
3. Atomic write using temp file

**Graceful Degradation:**
```python
try:
    storage = AnalyticsStorage()
except Exception as e:
    logger.warning(f"SQLite unavailable, using JSON-only mode: {e}")
    storage = JSONOnlyStorage()  # Fallback implementation
```

---

## OpenTelemetry Integration

### OTLP Exporter Module

**Location:** `auto-claude/analytics/otel_exporter.py`

```python
import os
from typing import Optional
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

class OTelExporter:
    """
    OpenTelemetry exporter for Auto-Claude analytics.

    Exports:
    - Metrics: Token counts, costs, session durations
    - Traces: Conversation flows, tool usage
    - Logs: Events, errors, budget alerts
    """

    def __init__(self):
        self.enabled = os.getenv('OTEL_ENABLED', 'true').lower() == 'true'

        if not self.enabled:
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

        metric_reader = PeriodicExportingMetricReader(
            exporter=metric_exporter,
            export_interval_millis=int(os.getenv('OTEL_EXPORT_INTERVAL_SECONDS', '60')) * 1000
        )

        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )

        metrics.set_meter_provider(meter_provider)
        self.meter = metrics.get_meter("auto-claude")

        # Create instruments
        self._create_instruments()

        # Traces setup (optional)
        if os.getenv('OTEL_TRACES_ENABLED', 'false').lower() == 'true':
            trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            tracer_provider = TracerProvider(resource=resource)
            tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
            trace.set_tracer_provider(tracer_provider)
            self.tracer = trace.get_tracer("auto-claude")

    def _create_instruments(self):
        """Create OpenTelemetry metric instruments."""

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

        # Gauges (current values)
        self.active_sessions = self.meter.create_up_down_counter(
            name="auto_claude.sessions.active",
            description="Number of active sessions",
            unit="sessions"
        )

    def record_message(
        self,
        spec_id: str,
        session_num: int,
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
            "session_number": str(session_num),
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
        session_num: int,
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
```

### Configuration

**Environment Variables (`.env`):**

```bash
# OpenTelemetry Core
OTEL_ENABLED=true
OTEL_SERVICE_NAME=auto-claude
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc  # or http/protobuf
OTEL_EXPORT_INTERVAL_SECONDS=60
OTEL_TRACES_ENABLED=false  # Optional tracing

# Multi-backend support
LANGFUSE_ENABLED=false
LANGFUSE_PUBLIC_KEY=pk_...
LANGFUSE_SECRET_KEY=sk_...
LANGFUSE_HOST=https://cloud.langfuse.com

SIGNOZ_ENABLED=false
SIGNOZ_ENDPOINT=http://localhost:4317

GRAFANA_ENABLED=false
GRAFANA_CLOUD_API_KEY=...
GRAFANA_CLOUD_ENDPOINT=...
```

### Metrics Exported

| Metric Name | Type | Unit | Description | Attributes |
|-------------|------|------|-------------|------------|
| `auto_claude.tokens.total` | Counter | tokens | Cumulative tokens consumed | spec_id, phase, model |
| `auto_claude.cost.total_usd` | Counter | USD | Cumulative cost | spec_id, phase, model |
| `auto_claude.sessions.total` | Counter | sessions | Total sessions run | spec_id, phase |
| `auto_claude.tokens.per_message` | Histogram | tokens | Token distribution per message | spec_id, phase, model |
| `auto_claude.cost.per_session_usd` | Histogram | USD | Cost distribution per session | spec_id, phase |
| `auto_claude.session.duration_seconds` | Histogram | seconds | Session duration | spec_id, phase |
| `auto_claude.sessions.active` | UpDownCounter | sessions | Currently active sessions | - |

### Events/Logs Exported

```json
{
  "timestamp": "2025-12-25T15:30:00Z",
  "severity": "INFO",
  "body": "Agent session completed",
  "attributes": {
    "event.name": "session.completed",
    "spec_id": "001-feature",
    "session_number": 1,
    "phase": "coding",
    "total_cost_usd": 0.245,
    "total_tokens": 15000,
    "duration_seconds": 120.5,
    "model": "claude-sonnet-4-5"
  }
}
```

### Integration with Multi-Backend Platforms

**Langfuse Integration:**

```python
from langfuse import Langfuse

class LangfuseExporter:
    def __init__(self):
        self.client = Langfuse(
            public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
            secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
            host=os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
        )

    def record_session(self, spec_id, session_num, messages, total_cost):
        trace = self.client.trace(
            name=f"auto-claude-session-{session_num}",
            metadata={"spec_id": spec_id}
        )

        for msg in messages:
            trace.generation(
                name="claude-message",
                model=msg['model'],
                input={"tokens": msg['input_tokens']},
                output={"tokens": msg['output_tokens']},
                usage={
                    "input": msg['input_tokens'],
                    "output": msg['output_tokens'],
                    "total": msg['input_tokens'] + msg['output_tokens']
                },
                calculated_costs=[{
                    "amount": msg['cost_usd'],
                    "unit": "USD"
                }]
            )
```

---

## Electron UI Dashboard

### New Analytics View

**Sidebar Addition:**

```tsx
// apps/frontend/src/renderer/components/Sidebar.tsx

const projectNavItems: NavItem[] = [
  { id: 'kanban', labelKey: 'navigation:items.kanban', icon: LayoutGrid, shortcut: 'K' },
  { id: 'terminals', labelKey: 'navigation:items.terminals', icon: Terminal, shortcut: 'A' },
  { id: 'analytics', labelKey: 'navigation:items.analytics', icon: DollarSign, shortcut: '$' }, // NEW
  { id: 'insights', labelKey: 'navigation:items.insights', icon: Sparkles, shortcut: 'N' },
  // ... rest
];
```

### Component Structure

**Directory:** `apps/frontend/src/renderer/components/Analytics/`

```
Analytics/
├── AnalyticsDashboard.tsx         # Main container
├── AnalyticsHeader.tsx            # Time range selector, export buttons
├── CostCard.tsx                   # Total cost summary card
├── TokenCard.tsx                  # Total tokens summary card
├── SessionCard.tsx                # Session count and avg cost card
├── EfficiencyCard.tsx             # Tokens/$, cost efficiency metrics
├── CostTrendChart.tsx             # Line chart: cost over time
├── TokenDistributionChart.tsx     # Pie chart: tokens by phase
├── SpecCostTable.tsx              # Table: specs sorted by cost
├── ModelComparisonChart.tsx       # Bar chart: cost by model
└── BudgetAlert.tsx                # Budget threshold warning
```

### Main Dashboard Component

```tsx
// AnalyticsDashboard.tsx

import { useState } from 'react';
import { useProjectStore } from '../stores/project-store';
import { useAnalyticsStore } from '../stores/analytics-store';
import { Button } from './ui/button';
import { Select } from './ui/select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './ui/tabs';
import {
  CostCard,
  TokenCard,
  SessionCard,
  EfficiencyCard
} from './Analytics';
import {
  CostTrendChart,
  TokenDistributionChart,
  SpecCostTable,
  ModelComparisonChart
} from './Analytics';

type TimeRange = '24h' | '7d' | '30d' | 'all';

export function AnalyticsDashboard() {
  const selectedProjectId = useProjectStore(s => s.selectedProjectId);
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');
  const [viewMode, setViewMode] = useState<'overview' | 'detailed'>('overview');

  const analytics = useAnalyticsStore(s =>
    s.getProjectAnalytics(selectedProjectId, timeRange)
  );

  const handleExport = async (format: 'csv' | 'json') => {
    await window.electronAPI.exportAnalytics(selectedProjectId, format);
  };

  if (!selectedProjectId) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Select a project to view analytics</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analytics & ROI</h1>
          <p className="text-sm text-muted-foreground">
            Token usage and cost tracking for {selectedProjectId}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Select
            value={timeRange}
            onChange={setTimeRange}
            options={[
              { value: '24h', label: 'Last 24 Hours' },
              { value: '7d', label: 'Last 7 Days' },
              { value: '30d', label: 'Last 30 Days' },
              { value: 'all', label: 'All Time' }
            ]}
          />

          <Button variant="outline" onClick={() => handleExport('csv')}>
            Export CSV
          </Button>

          <Button variant="outline" onClick={() => handleExport('json')}>
            Export JSON
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <CostCard
          totalCost={analytics.totalCost}
          trend={analytics.costTrend}
          budget={analytics.budget}
        />

        <TokenCard
          totalTokens={analytics.totalTokens}
          inputTokens={analytics.totalInputTokens}
          outputTokens={analytics.totalOutputTokens}
          trend={analytics.tokenTrend}
        />

        <SessionCard
          totalSessions={analytics.totalSessions}
          avgCostPerSession={analytics.avgCostPerSession}
        />

        <EfficiencyCard
          tokensPerDollar={analytics.tokensPerDollar}
          avgCostPerSubtask={analytics.avgCostPerSubtask}
        />
      </div>

      {/* Tabs */}
      <Tabs value={viewMode} onValueChange={setViewMode}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="detailed">Detailed</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-2 gap-4 mt-4">
            <CostTrendChart data={analytics.costOverTime} />
            <TokenDistributionChart data={analytics.tokensByPhase} />
          </div>

          <div className="mt-4">
            <SpecCostTable specs={analytics.specBreakdown} />
          </div>
        </TabsContent>

        <TabsContent value="detailed">
          <div className="grid grid-cols-2 gap-4 mt-4">
            <ModelComparisonChart data={analytics.costByModel} />
            <TokenDistributionChart data={analytics.tokensBySubtask} />
          </div>

          <div className="mt-4">
            {/* Detailed message-level table */}
            <MessageLevelTable messages={analytics.detailedMessages} />
          </div>
        </TabsContent>
      </Tabs>

      {/* Budget Alert */}
      {analytics.budgetExceeded && (
        <BudgetAlert
          current={analytics.totalCost}
          budget={analytics.budget}
          threshold={analytics.budgetThreshold}
        />
      )}
    </div>
  );
}
```

### Zustand Store

```typescript
// apps/frontend/src/renderer/stores/analytics-store.ts

import { create } from 'zustand';

interface ProjectAnalytics {
  totalCost: number;
  totalTokens: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalSessions: number;
  avgCostPerSession: number;
  tokensPerDollar: number;
  costTrend: number; // % change
  tokenTrend: number; // % change
  costOverTime: Array<{ date: string; cost: number }>;
  tokensByPhase: Array<{ phase: string; tokens: number }>;
  specBreakdown: Array<{
    specId: string;
    cost: number;
    sessions: number;
    tokens: number;
  }>;
  costByModel: Array<{ model: string; cost: number }>;
  budget: number;
  budgetExceeded: boolean;
  budgetThreshold: number;
}

interface AnalyticsState {
  projectAnalytics: Map<string, ProjectAnalytics>;
  isLoading: boolean;
  error: string | null;

  // Actions
  loadAnalytics: (projectId: string, timeRange: string) => Promise<void>;
  getProjectAnalytics: (projectId: string, timeRange: string) => ProjectAnalytics;
  refreshAnalytics: (projectId: string) => Promise<void>;
  clearAnalytics: () => void;
}

export const useAnalyticsStore = create<AnalyticsState>((set, get) => ({
  projectAnalytics: new Map(),
  isLoading: false,
  error: null,

  loadAnalytics: async (projectId, timeRange) => {
    set({ isLoading: true, error: null });

    try {
      const result = await window.electronAPI.getAnalytics(projectId, timeRange);

      if (result.success) {
        set(state => ({
          projectAnalytics: state.projectAnalytics.set(
            `${projectId}-${timeRange}`,
            result.data
          ),
          isLoading: false
        }));
      } else {
        set({ error: result.error, isLoading: false });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Unknown error',
        isLoading: false
      });
    }
  },

  getProjectAnalytics: (projectId, timeRange) => {
    const key = `${projectId}-${timeRange}`;
    const analytics = get().projectAnalytics.get(key);

    if (!analytics) {
      // Trigger load if not cached
      get().loadAnalytics(projectId, timeRange);

      // Return empty default
      return {
        totalCost: 0,
        totalTokens: 0,
        totalInputTokens: 0,
        totalOutputTokens: 0,
        totalSessions: 0,
        avgCostPerSession: 0,
        tokensPerDollar: 0,
        costTrend: 0,
        tokenTrend: 0,
        costOverTime: [],
        tokensByPhase: [],
        specBreakdown: [],
        costByModel: [],
        budget: 0,
        budgetExceeded: false,
        budgetThreshold: 0
      };
    }

    return analytics;
  },

  refreshAnalytics: async (projectId) => {
    // Force reload from backend
    const timeRange = '7d'; // default
    await get().loadAnalytics(projectId, timeRange);
  },

  clearAnalytics: () => {
    set({ projectAnalytics: new Map(), error: null });
  }
}));
```

### IPC Handlers

```typescript
// apps/frontend/src/main/ipc-handlers/analytics-handlers.ts

import { ipcMain } from 'electron';
import path from 'path';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

ipcMain.handle('get-analytics', async (_, projectId: string, timeRange: string) => {
  try {
    const dbPath = path.join(projectId, '.auto-claude', 'analytics.db');

    const db = await open({
      filename: dbPath,
      driver: sqlite3.Database
    });

    // Calculate time range filter
    const timeFilter = getTimeFilter(timeRange);

    // Total cost
    const totalCostResult = await db.get(`
      SELECT SUM(total_cost_usd) as total_cost
      FROM conversations
      WHERE started_at > datetime('now', '${timeFilter}')
    `);

    // Total tokens
    const totalTokensResult = await db.get(`
      SELECT
        SUM(total_input_tokens) as total_input,
        SUM(total_output_tokens) as total_output
      FROM conversations
      WHERE started_at > datetime('now', '${timeFilter}')
    `);

    // Session count
    const sessionCountResult = await db.get(`
      SELECT COUNT(*) as count
      FROM conversations
      WHERE started_at > datetime('now', '${timeFilter}')
    `);

    // Cost over time (daily)
    const costOverTime = await db.all(`
      SELECT
        DATE(started_at) as date,
        SUM(total_cost_usd) as cost
      FROM conversations
      WHERE started_at > datetime('now', '${timeFilter}')
      GROUP BY DATE(started_at)
      ORDER BY date
    `);

    // Tokens by phase
    const tokensByPhase = await db.all(`
      SELECT
        phase,
        SUM(total_input_tokens + total_output_tokens) as tokens
      FROM conversations
      WHERE started_at > datetime('now', '${timeFilter}')
      GROUP BY phase
    `);

    // Spec breakdown
    const specBreakdown = await db.all(`
      SELECT
        spec_id,
        SUM(total_cost_usd) as cost,
        COUNT(*) as sessions,
        SUM(total_input_tokens + total_output_tokens) as tokens
      FROM conversations
      WHERE started_at > datetime('now', '${timeFilter}')
      GROUP BY spec_id
      ORDER BY cost DESC
      LIMIT 10
    `);

    // Cost by model
    const costByModel = await db.all(`
      SELECT
        model,
        SUM(total_cost_usd) as cost
      FROM conversations
      WHERE started_at > datetime('now', '${timeFilter}')
        AND model IS NOT NULL
      GROUP BY model
    `);

    await db.close();

    const totalCost = totalCostResult?.total_cost || 0;
    const totalInputTokens = totalTokensResult?.total_input || 0;
    const totalOutputTokens = totalTokensResult?.total_output || 0;
    const totalSessions = sessionCountResult?.count || 0;

    return {
      success: true,
      data: {
        totalCost,
        totalTokens: totalInputTokens + totalOutputTokens,
        totalInputTokens,
        totalOutputTokens,
        totalSessions,
        avgCostPerSession: totalSessions > 0 ? totalCost / totalSessions : 0,
        tokensPerDollar: totalCost > 0 ? (totalInputTokens + totalOutputTokens) / totalCost : 0,
        costTrend: 0, // TODO: Calculate trend
        tokenTrend: 0, // TODO: Calculate trend
        costOverTime: costOverTime.map(row => ({
          date: row.date,
          cost: row.cost
        })),
        tokensByPhase: tokensByPhase.map(row => ({
          phase: row.phase,
          tokens: row.tokens
        })),
        specBreakdown: specBreakdown.map(row => ({
          specId: row.spec_id,
          cost: row.cost,
          sessions: row.sessions,
          tokens: row.tokens
        })),
        costByModel: costByModel.map(row => ({
          model: row.model,
          cost: row.cost
        })),
        budget: 100.0, // TODO: Load from settings
        budgetExceeded: totalCost > 100.0, // TODO: Check against actual budget
        budgetThreshold: 0.8
      }
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
});

ipcMain.handle('export-analytics', async (_, projectId: string, format: 'csv' | 'json') => {
  try {
    const dbPath = path.join(projectId, '.auto-claude', 'analytics.db');
    const db = await open({
      filename: dbPath,
      driver: sqlite3.Database
    });

    // Get all conversations with messages
    const conversations = await db.all(`
      SELECT c.*, m.*
      FROM conversations c
      LEFT JOIN messages m ON c.id = m.conversation_id
      ORDER BY c.started_at, m.timestamp
    `);

    await db.close();

    if (format === 'json') {
      // Export as JSON
      const outputPath = path.join(projectId, 'analytics-export.json');
      await fs.promises.writeFile(
        outputPath,
        JSON.stringify(conversations, null, 2)
      );
      return { success: true, path: outputPath };
    } else {
      // Export as CSV
      const outputPath = path.join(projectId, 'analytics-export.csv');
      const csv = convertToCSV(conversations);
      await fs.promises.writeFile(outputPath, csv);
      return { success: true, path: outputPath };
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
});

function getTimeFilter(timeRange: string): string {
  switch (timeRange) {
    case '24h': return '-1 day';
    case '7d': return '-7 days';
    case '30d': return '-30 days';
    case 'all': return '-100 years'; // Effectively all time
    default: return '-7 days';
  }
}

function convertToCSV(data: any[]): string {
  // TODO: Implement CSV conversion
  return '';
}
```

### Charts

**Using Recharts library:**

```tsx
// CostTrendChart.tsx

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
  data: Array<{ date: string; cost: number }>;
}

export function CostTrendChart({ data }: Props) {
  return (
    <div className="bg-card rounded-lg border p-4">
      <h3 className="text-lg font-semibold mb-4">Cost Trend</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip formatter={(value) => `$${value.toFixed(4)}`} />
          <Line
            type="monotone"
            dataKey="cost"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

## Configuration & API

### Backend Configuration

**File:** `auto-claude/.env`

```bash
# ===== TOKEN TRACKING & ANALYTICS =====

# Enable/Disable (opt-out - enabled by default)
DISABLE_TOKEN_TRACKING=false

# Storage paths
ANALYTICS_DB_PATH=.auto-claude/analytics.db
ANALYTICS_EXPORT_JSON=true  # Backup to JSON files

# Pricing (per 1M tokens in USD)
CLAUDE_SONNET_4_5_INPUT_PRICE=3.00
CLAUDE_SONNET_4_5_OUTPUT_PRICE=15.00
CLAUDE_HAIKU_4_5_INPUT_PRICE=0.80
CLAUDE_HAIKU_4_5_OUTPUT_PRICE=4.00
CLAUDE_OPUS_4_5_INPUT_PRICE=15.00
CLAUDE_OPUS_4_5_OUTPUT_PRICE=75.00

# Cache pricing
CACHE_READ_DISCOUNT=0.9  # 90% discount
CACHE_CREATION_MULTIPLIER=1.25  # 25% premium

# Budget limits (optional)
MONTHLY_BUDGET_USD=100.00
DAILY_BUDGET_USD=10.00
SESSION_BUDGET_USD=5.00
BUDGET_ALERT_THRESHOLD=0.8  # Alert at 80%
BUDGET_HARD_STOP=false  # Stop execution when budget exceeded

# OpenTelemetry
OTEL_ENABLED=true
OTEL_SERVICE_NAME=auto-claude
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_EXPORT_INTERVAL_SECONDS=60
OTEL_TRACES_ENABLED=false

# Langfuse
LANGFUSE_ENABLED=false
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com

# SigNoz
SIGNOZ_ENABLED=false
SIGNOZ_ENDPOINT=http://localhost:4317

# Grafana Cloud
GRAFANA_ENABLED=false
GRAFANA_CLOUD_API_KEY=
GRAFANA_CLOUD_ENDPOINT=
```

### CLI API

**New commands in `auto-claude/run.py`:**

```bash
# View analytics for a spec
python auto-claude/run.py --spec 001 --analytics

# Generate cost report
python auto-claude/run.py --report costs --format csv --output costs.csv
python auto-claude/run.py --report costs --format json --output costs.json

# View aggregated costs by project
python auto-claude/run.py --costs --project /path/to/project

# Top N most expensive specs
python auto-claude/run.py --top-specs 10

# Budget status check
python auto-claude/run.py --budget-status

# Export all analytics data
python auto-claude/run.py --export-analytics --format json --output analytics.json

# Clear analytics data (with confirmation)
python auto-claude/run.py --clear-analytics --confirm
```

### Python API

**Module:** `auto-claude/analytics/api.py`

```python
from auto_claude.analytics import AnalyticsClient

# Initialize client
analytics = AnalyticsClient(db_path='.auto-claude/analytics.db')

# Query total costs
total_cost = analytics.get_total_cost(spec_id='001-feature')
total_cost_all = analytics.get_total_cost()  # All specs

# Get spec breakdown
specs = analytics.get_spec_breakdown(
    project_id='my-project',
    time_range='30d',
    order_by='cost',
    limit=10
)

for spec in specs:
    print(f"{spec.spec_id}: ${spec.total_cost_usd:.4f} ({spec.total_sessions} sessions)")

# Get cost by model
model_costs = analytics.get_cost_by_model(time_range='7d')

# Get cost over time
daily_costs = analytics.get_cost_over_time(
    time_range='30d',
    granularity='day'  # day, week, month
)

# Real-time session tracking (context manager)
with analytics.track_session(
    spec_id='001',
    session_num=1,
    phase='coding'
) as tracker:
    # Session automatically tracked
    result = await run_autonomous_agent(...)
    # Usage data automatically recorded

# Budget checks
if analytics.is_budget_exceeded(budget_usd=100.0, time_range='month'):
    print("Monthly budget exceeded!")

budget_status = analytics.get_budget_status(
    budget_usd=100.0,
    time_range='month'
)
print(f"Used: ${budget_status.used:.2f} / ${budget_status.total:.2f} ({budget_status.percentage:.1f}%)")

# Export reports
analytics.export_csv('costs.csv', time_range='30d')
analytics.export_json('analytics.json', include_messages=True)

# Cleanup old data
analytics.delete_data_before(date='2025-01-01')
```

### Electron Settings UI

**Component:** `apps/frontend/src/renderer/components/Settings/AnalyticsSettings.tsx`

```tsx
export function AnalyticsSettings() {
  const settings = useSettingsStore(s => s.settings);
  const updateSetting = useSettingsStore(s => s.updateSetting);

  return (
    <SettingsSection title="Analytics & Token Tracking">
      <div className="space-y-4">
        <Toggle
          label="Enable Token Tracking"
          description="Track token usage and costs for all sessions (opt-out)"
          checked={!settings.disableTokenTracking}
          onChange={(enabled) => updateSetting('disableTokenTracking', !enabled)}
        />

        <Separator />

        <h4 className="font-semibold">Budget Limits</h4>

        <NumberInput
          label="Monthly Budget (USD)"
          description="Alert when monthly costs exceed this amount"
          value={settings.monthlyBudgetUSD}
          onChange={(val) => updateSetting('monthlyBudgetUSD', val)}
          min={0}
          step={10}
        />

        <NumberInput
          label="Daily Budget (USD)"
          description="Alert when daily costs exceed this amount"
          value={settings.dailyBudgetUSD}
          onChange={(val) => updateSetting('dailyBudgetUSD', val)}
          min={0}
          step={1}
        />

        <NumberInput
          label="Session Budget (USD)"
          description="Alert when a single session exceeds this amount"
          value={settings.sessionBudgetUSD}
          onChange={(val) => updateSetting('sessionBudgetUSD', val)}
          min={0}
          step={0.5}
        />

        <Slider
          label="Budget Alert Threshold"
          description="Alert when reaching this percentage of budget"
          value={settings.budgetAlertThreshold}
          onChange={(val) => updateSetting('budgetAlertThreshold', val)}
          min={0}
          max={1}
          step={0.1}
          format={(val) => `${(val * 100).toFixed(0)}%`}
        />

        <Toggle
          label="Hard Stop on Budget Exceeded"
          description="Stop agent execution when budget is exceeded"
          checked={settings.budgetHardStop}
          onChange={(enabled) => updateSetting('budgetHardStop', enabled)}
        />

        <Separator />

        <h4 className="font-semibold">OpenTelemetry Export</h4>

        <Toggle
          label="Export to OpenTelemetry"
          description="Send metrics to external observability platforms"
          checked={settings.otelEnabled}
          onChange={(enabled) => updateSetting('otelEnabled', enabled)}
        />

        <Input
          label="OTLP Endpoint"
          description="OpenTelemetry collector endpoint"
          value={settings.otelEndpoint}
          onChange={(val) => updateSetting('otelEndpoint', val)}
          placeholder="http://localhost:4317"
          disabled={!settings.otelEnabled}
        />

        <Select
          label="Default Time Range"
          description="Default time range for analytics dashboard"
          options={[
            { value: '24h', label: 'Last 24 Hours' },
            { value: '7d', label: 'Last 7 Days' },
            { value: '30d', label: 'Last 30 Days' },
            { value: 'all', label: 'All Time' }
          ]}
          value={settings.analyticsTimeRange}
          onChange={(val) => updateSetting('analyticsTimeRange', val)}
        />

        <Separator />

        <div className="flex items-center gap-3">
          <Button onClick={() => handleExportAnalytics()}>
            Export Analytics Data
          </Button>

          <Button variant="destructive" onClick={() => handleClearAnalytics()}>
            Clear Analytics Data
          </Button>
        </div>
      </div>
    </SettingsSection>
  );
}
```

---

## Implementation Plan

### Phase 1: Core Data Collection (Week 1)

**Tasks:**
1. Create `auto-claude/analytics/` module structure
2. Implement `UsageTracker` class
3. Implement `AnalyticsStorage` class (SQLite + JSON)
4. Implement pricing calculator
5. Integrate `UsageTracker` into `session.py`
6. Write unit tests for tracking and storage

**Deliverables:**
- Token tracking working in backend
- Data persisted to SQLite and JSON
- Tests passing

### Phase 2: OpenTelemetry Integration (Week 2)

**Tasks:**
1. Implement `OTelExporter` class
2. Add OTLP metrics export
3. Configure multi-backend support (Langfuse, SigNoz)
4. Add budget checking logic
5. Write integration tests

**Deliverables:**
- Metrics flowing to external platforms
- Budget alerts working
- Tests passing

### Phase 3: Electron UI Dashboard (Week 3-4)

**Tasks:**
1. Create Analytics component structure
2. Implement Zustand analytics store
3. Implement IPC handlers for analytics queries
4. Build summary cards (Cost, Tokens, Sessions, Efficiency)
5. Build charts (Cost Trend, Token Distribution, Model Comparison)
6. Build Spec Cost Table
7. Integrate into Sidebar
8. Add Settings panel for analytics config

**Deliverables:**
- Analytics dashboard accessible in UI
- Real-time data updates
- Export functionality working

### Phase 4: CLI & API (Week 5)

**Tasks:**
1. Add CLI commands to `run.py`
2. Implement `AnalyticsClient` Python API
3. Add export commands (CSV, JSON)
4. Add budget status command
5. Write API documentation
6. Write CLI documentation

**Deliverables:**
- Full CLI API for analytics
- Python API for programmatic access
- Documentation complete

### Phase 5: Testing & Refinement (Week 6)

**Tasks:**
1. End-to-end testing
2. Performance testing (overhead measurement)
3. Load testing (1000+ sessions)
4. UI/UX refinement
5. Bug fixes
6. Documentation updates

**Deliverables:**
- System fully tested
- Performance validated (<0.1ms overhead)
- Documentation complete
- Ready for beta release

---

## Testing Strategy

### Unit Tests

**Module:** `tests/analytics/`

```python
# test_usage_tracker.py
def test_tracker_deduplicates_messages():
    """Ensure messages with same ID are only counted once."""
    tracker = UsageTracker(spec_id='test', session_num=1, phase='planning', storage=mock_storage)

    msg = AssistantMessage(id='msg_123', usage={'input_tokens': 100, 'output_tokens': 50})

    await tracker.track_message(msg)
    await tracker.track_message(msg)  # Duplicate

    assert len(tracker.message_ids_seen) == 1
    assert tracker.total_input_tokens == 100  # Not doubled

# test_storage.py
def test_sqlite_json_sync():
    """Ensure SQLite and JSON stay in sync."""
    storage = AnalyticsStorage(db_path=':memory:')

    conversation_id = await storage.create_conversation(...)
    await storage.record_message(conversation_id, ...)

    # Export to JSON
    json_path = Path('/tmp/test_usage.json')
    await storage.export_to_json('test-spec', json_path)

    # Verify JSON content
    with open(json_path) as f:
        data = json.load(f)

    assert data['spec_id'] == 'test-spec'
    assert len(data['sessions']) == 1

# test_pricing.py
def test_cost_calculation():
    """Verify cost calculations are accurate."""
    tracker = UsageTracker(...)

    cost = tracker._calculate_cost(
        model='claude-sonnet-4-5',
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=0,
        cache_creation_tokens=0
    )

    # $3/1M input + $15/1M output
    expected = (1000/1_000_000 * 3.0) + (500/1_000_000 * 15.0)
    assert abs(cost - expected) < 0.0001
```

### Integration Tests

```python
# test_session_integration.py
async def test_session_tracking_end_to_end():
    """Test full session tracking flow."""
    from auto_claude.agents.session import run_agent_session
    from auto_claude.analytics import get_analytics_storage

    # Run a test session
    result = await run_agent_session(
        spec_id='test-001',
        session_number=1,
        phase='planning',
        prompt='Create a simple function'
    )

    # Verify data was recorded
    storage = get_analytics_storage()
    conn = sqlite3.connect(storage.db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM conversations WHERE spec_id = 'test-001'")
    conversation = cursor.fetchone()

    assert conversation is not None
    assert conversation['total_cost_usd'] > 0
    assert conversation['total_input_tokens'] > 0

    conn.close()
```

### Performance Tests

```python
# test_performance.py
def test_tracking_overhead():
    """Ensure tracking adds <0.1ms overhead per message."""
    import time

    tracker = UsageTracker(...)

    # Measure baseline
    start = time.perf_counter()
    for _ in range(1000):
        pass
    baseline = time.perf_counter() - start

    # Measure with tracking
    start = time.perf_counter()
    for i in range(1000):
        msg = AssistantMessage(id=f'msg_{i}', usage={'input_tokens': 100, 'output_tokens': 50})
        await tracker.track_message(msg)
    tracked = time.perf_counter() - start

    overhead_per_msg = (tracked - baseline) / 1000
    assert overhead_per_msg < 0.0001  # <0.1ms
```

### UI Tests

```typescript
// analytics-dashboard.test.tsx
describe('AnalyticsDashboard', () => {
  it('displays cost summary correctly', async () => {
    const { getByText } = render(<AnalyticsDashboard />);

    await waitFor(() => {
      expect(getByText(/Total Cost/i)).toBeInTheDocument();
      expect(getByText(/\$0\.24/)).toBeInTheDocument();
    });
  });

  it('exports CSV correctly', async () => {
    const { getByRole } = render(<AnalyticsDashboard />);

    const exportButton = getByRole('button', { name: /Export CSV/i });
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(window.electronAPI.exportAnalytics).toHaveBeenCalledWith(
        expect.any(String),
        'csv'
      );
    });
  });
});
```

---

## Rollout Plan

### Beta Release (Week 7)

**Target Audience:** Internal team + 10 beta testers

**Activities:**
1. Deploy to beta environment
2. Enable tracking by default (opt-out via .env)
3. Monitor for issues
4. Collect feedback
5. Fix critical bugs

**Success Criteria:**
- <0.1ms tracking overhead
- 99.9% data accuracy
- Zero crashes
- Positive feedback from beta testers

### Production Release (Week 8)

**Target Audience:** All users

**Activities:**
1. Merge to main branch
2. Update documentation
3. Create migration guide for existing users
4. Announce new feature
5. Monitor adoption

**Success Criteria:**
- 80%+ adoption rate
- <5 bug reports per 1000 users
- Positive user feedback

### Post-Release Support

**Monitoring:**
- Track adoption metrics
- Monitor error rates
- Collect user feedback
- Iterate on UI/UX

**Roadmap:**
- Month 2: Add predictive cost forecasting
- Month 3: Add cost optimization recommendations
- Month 4: Add team/multi-user analytics
- Month 5: Add integration with billing systems

---

## Appendix

### Pricing Models

**As of January 2025:**

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Cache Read Discount | Cache Creation Multiplier |
|-------|----------------------|------------------------|---------------------|--------------------------|
| Claude Sonnet 4.5 | $3.00 | $15.00 | 90% | 1.25x |
| Claude Haiku 4.5 | $0.80 | $4.00 | 90% | 1.25x |
| Claude Opus 4.5 | $15.00 | $75.00 | 90% | 1.25x |

**Source:** https://www.anthropic.com/pricing

### Database Indices

```sql
-- Optimize common queries
CREATE INDEX idx_conversations_spec_started ON conversations(spec_id, started_at);
CREATE INDEX idx_messages_conversation_timestamp ON messages(conversation_id, timestamp);
CREATE INDEX idx_messages_model_timestamp ON messages(model, timestamp);
CREATE INDEX idx_spec_totals_cost ON spec_totals(total_cost_usd DESC);
```

### Sample Queries

**Get top 10 most expensive specs:**
```sql
SELECT spec_id, total_cost_usd, total_conversations
FROM spec_totals
ORDER BY total_cost_usd DESC
LIMIT 10;
```

**Get daily cost breakdown:**
```sql
SELECT
  DATE(started_at) as date,
  SUM(total_cost_usd) as daily_cost,
  COUNT(*) as sessions
FROM conversations
WHERE started_at > datetime('now', '-30 days')
GROUP BY DATE(started_at)
ORDER BY date;
```

**Get cost by phase:**
```sql
SELECT
  phase,
  SUM(total_cost_usd) as cost,
  AVG(total_cost_usd) as avg_cost,
  COUNT(*) as sessions
FROM conversations
GROUP BY phase;
```

---

## References

1. [Claude Agent SDK - Cost Tracking](https://platform.claude.com/docs/en/agent-sdk/cost-tracking)
2. [OpenTelemetry for Claude Code - SigNoz](https://signoz.io/blog/claude-code-monitoring-with-opentelemetry/)
3. [Langfuse Claude Integration](https://langfuse.com/integrations/frameworks/claude-agent-sdk)
4. [LLM Logging with SQLite](https://llm.datasette.io/en/stable/logging.html)
5. [OpenLLMetry Framework](https://github.com/traceloop/openllmetry)
6. [Grafana Anthropic Integration](https://grafana.com/blog/how-to-monitor-claude-usage-and-costs-introducing-the-anthropic-integration-for-grafana-cloud/)

---

**End of Design Document**
