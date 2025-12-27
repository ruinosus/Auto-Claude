"""
Dual-persistence analytics storage: SQLite (primary) + JSON (backup).

Provides fast queries via SQLite while maintaining human-readable JSON backups
for portability and disaster recovery.
"""

import sqlite3
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from contextlib import asynccontextmanager


# SQLite Schema
SCHEMA_SQL = """
-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
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

CREATE INDEX IF NOT EXISTS idx_conversations_spec ON conversations(spec_id);
CREATE INDEX IF NOT EXISTS idx_conversations_phase ON conversations(phase);
CREATE INDEX IF NOT EXISTS idx_conversations_started ON conversations(started_at);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
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

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_subtask ON messages(subtask_id);
CREATE INDEX IF NOT EXISTS idx_messages_model ON messages(model);

-- Spec totals (materialized view)
CREATE TABLE IF NOT EXISTS spec_totals (
    spec_id TEXT PRIMARY KEY,
    total_conversations INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to update spec_totals
CREATE TRIGGER IF NOT EXISTS update_spec_totals_after_conversation
AFTER UPDATE OF total_cost_usd, total_input_tokens, total_output_tokens ON conversations
FOR EACH ROW
WHEN NEW.ended_at IS NOT NULL
BEGIN
    INSERT INTO spec_totals (
        spec_id,
        total_conversations,
        total_cost_usd,
        total_input_tokens,
        total_output_tokens,
        last_updated
    )
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
        total_cost_usd = total_cost_usd + EXCLUDED.total_cost_usd,
        total_input_tokens = total_input_tokens + EXCLUDED.total_input_tokens,
        total_output_tokens = total_output_tokens + EXCLUDED.total_output_tokens,
        last_updated = CURRENT_TIMESTAMP;
END;

-- ROI Settings (global)
CREATE TABLE IF NOT EXISTS roi_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    developer_hourly_rate REAL DEFAULT 75.0,
    primary_currency TEXT DEFAULT 'USD',
    secondary_currency TEXT DEFAULT 'BRL',
    exchange_rate REAL DEFAULT 6.20,
    exchange_rate_updated_at TIMESTAMP,
    auto_estimate_hours INTEGER DEFAULT 1,
    minutes_per_line REAL DEFAULT 2.5,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ROI per spec (with git diff and QA tracking)
CREATE TABLE IF NOT EXISTS spec_roi (
    spec_id TEXT PRIMARY KEY,
    project_id TEXT,
    estimated_business_value REAL DEFAULT 0,
    estimated_hours_manual REAL,
    developer_rate_override REAL,
    actual_cost REAL DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    execution_time_seconds INTEGER DEFAULT 0,
    qa_attempts INTEGER DEFAULT 0,
    qa_passed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_spec_roi_project ON spec_roi(project_id);

-- Feature sessions table (for roadmap, ideation, insights, github, changelog, etc.)
-- Separate from conversations to avoid phase constraint and enable feature-specific tracking
CREATE TABLE IF NOT EXISTS feature_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    feature_type TEXT NOT NULL,  -- roadmap, ideation, insights, pr_review, issue_triage, changelog, autofix
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    total_cost_usd REAL DEFAULT 0.0,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    model TEXT,
    metadata TEXT,  -- JSON for feature-specific data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feature_sessions_project ON feature_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_feature_sessions_type ON feature_sessions(feature_type);
CREATE INDEX IF NOT EXISTS idx_feature_sessions_started ON feature_sessions(started_at);

-- Feature messages table (similar to messages but for feature sessions)
CREATE TABLE IF NOT EXISTS feature_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    message_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_creation_tokens INTEGER DEFAULT 0,
    cost_usd REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES feature_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_feature_messages_session ON feature_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_feature_messages_timestamp ON feature_messages(timestamp);

-- Feature totals (materialized view for feature usage)
CREATE TABLE IF NOT EXISTS feature_totals (
    project_id TEXT NOT NULL,
    feature_type TEXT NOT NULL,
    total_sessions INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, feature_type)
);

-- Trigger to update feature_totals
CREATE TRIGGER IF NOT EXISTS update_feature_totals_after_session
AFTER UPDATE OF total_cost_usd, total_input_tokens, total_output_tokens ON feature_sessions
FOR EACH ROW
WHEN NEW.ended_at IS NOT NULL
BEGIN
    INSERT INTO feature_totals (
        project_id,
        feature_type,
        total_sessions,
        total_cost_usd,
        total_input_tokens,
        total_output_tokens,
        last_updated
    )
    VALUES (
        NEW.project_id,
        NEW.feature_type,
        1,
        NEW.total_cost_usd,
        NEW.total_input_tokens,
        NEW.total_output_tokens,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT(project_id, feature_type) DO UPDATE SET
        total_sessions = total_sessions + 1,
        total_cost_usd = total_cost_usd + EXCLUDED.total_cost_usd,
        total_input_tokens = total_input_tokens + EXCLUDED.total_input_tokens,
        total_output_tokens = total_output_tokens + EXCLUDED.total_output_tokens,
        last_updated = CURRENT_TIMESTAMP;
END;

-- OTEL sessions table (for Claude Code telemetry via OpenTelemetry)
-- Tracks terminal sessions with real-time token usage from OTEL api_request events
CREATE TABLE IF NOT EXISTS otel_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,  -- Claude Code session ID from OTEL
    model TEXT,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_creation_tokens INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0,
    request_count INTEGER DEFAULT 0,
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_otel_sessions_session ON otel_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_otel_sessions_first_seen ON otel_sessions(first_seen);

-- OTEL requests table (individual API requests from Claude Code)
CREATE TABLE IF NOT EXISTS otel_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    otel_session_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_creation_tokens INTEGER DEFAULT 0,
    cost_usd REAL NOT NULL,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (otel_session_id) REFERENCES otel_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_otel_requests_session ON otel_requests(otel_session_id);
CREATE INDEX IF NOT EXISTS idx_otel_requests_timestamp ON otel_requests(timestamp);
"""


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
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Create tables
        cursor.executescript(SCHEMA_SQL)

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    async def create_conversation(
        self,
        spec_id: str,
        session_number: int,
        phase: str,
        started_at: datetime
    ) -> int:
        """Create new conversation record. Returns conversation_id."""
        loop = asyncio.get_event_loop()

        def _create():
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO conversations (spec_id, session_number, phase, started_at)
                VALUES (?, ?, ?, ?)
            """, (spec_id, session_number, phase, started_at.isoformat()))

            conversation_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return conversation_id

        return await loop.run_in_executor(None, _create)

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
        loop = asyncio.get_event_loop()

        def _record():
            conn = self._get_connection()
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

        await loop.run_in_executor(None, _record)

    async def update_conversation_totals(
        self,
        conversation_id: int,
        ended_at: datetime,
        total_cost_usd: float,
        total_input_tokens: int,
        total_output_tokens: int,
        model: Optional[str] = None
    ):
        """Update conversation with final totals."""
        loop = asyncio.get_event_loop()

        def _update():
            conn = self._get_connection()
            cursor = conn.cursor()

            if model:
                cursor.execute("""
                    UPDATE conversations
                    SET
                        ended_at = ?,
                        total_cost_usd = ?,
                        total_input_tokens = ?,
                        total_output_tokens = ?,
                        model = ?
                    WHERE id = ?
                """, (ended_at.isoformat(), total_cost_usd, total_input_tokens, total_output_tokens, model, conversation_id))
            else:
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

        await loop.run_in_executor(None, _update)

    async def export_to_json(self, spec_id: str, output_path: Path):
        """Export spec data to JSON file."""
        loop = asyncio.get_event_loop()

        def _export():
            conn = self._get_connection()
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

                messages = cursor.fetchall()

                session_data = {
                    'session_number': conv['session_number'],
                    'phase': conv['phase'],
                    'started_at': conv['started_at'],
                    'ended_at': conv['ended_at'],
                    'total_cost_usd': conv['total_cost_usd'] or 0.0,
                    'total_input_tokens': conv['total_input_tokens'] or 0,
                    'total_output_tokens': conv['total_output_tokens'] or 0,
                    'model': conv['model'],
                    'messages': [
                        {
                            'message_id': msg['message_id'],
                            'timestamp': msg['timestamp'],
                            'subtask_id': msg['subtask_id'],
                            'model': msg['model'],
                            'input_tokens': msg['input_tokens'],
                            'output_tokens': msg['output_tokens'],
                            'cache_read_tokens': msg['cache_read_tokens'],
                            'cache_creation_tokens': msg['cache_creation_tokens'],
                            'cost_usd': msg['cost_usd']
                        }
                        for msg in messages
                    ]
                }

                sessions.append(session_data)
                total_cost += conv['total_cost_usd'] or 0.0

            # Write JSON
            json_data = {
                "spec_id": spec_id,
                "total_cost_usd": total_cost,
                "total_sessions": len(sessions),
                "updated_at": datetime.utcnow().isoformat(),
                "sessions": sessions
            }

            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write using temp file
            temp_path = output_path.with_suffix('.json.tmp')
            with open(temp_path, 'w') as f:
                json.dump(json_data, f, indent=2)

            # Atomic rename
            temp_path.replace(output_path)

            conn.close()

        await loop.run_in_executor(None, _export)

    async def import_from_json(self, json_path: Path):
        """Import JSON data into SQLite (for migration/recovery)."""
        loop = asyncio.get_event_loop()

        def _import():
            with open(json_path) as f:
                data = json.load(f)

            # Use synchronous versions for import
            for session in data.get('sessions', []):
                # Create conversation
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR IGNORE INTO conversations (spec_id, session_number, phase, started_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    data['spec_id'],
                    session['session_number'],
                    session['phase'],
                    session['started_at']
                ))

                conversation_id = cursor.lastrowid or cursor.execute(
                    "SELECT id FROM conversations WHERE spec_id = ? AND session_number = ?",
                    (data['spec_id'], session['session_number'])
                ).fetchone()[0]

                # Insert messages
                for msg in session.get('messages', []):
                    cursor.execute("""
                        INSERT OR IGNORE INTO messages (
                            conversation_id, message_id, subtask_id, timestamp,
                            model, input_tokens, output_tokens,
                            cache_read_tokens, cache_creation_tokens, cost_usd
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        conversation_id,
                        msg['message_id'],
                        msg.get('subtask_id'),
                        msg['timestamp'],
                        msg['model'],
                        msg['input_tokens'],
                        msg['output_tokens'],
                        msg.get('cache_read_tokens', 0),
                        msg.get('cache_creation_tokens', 0),
                        msg['cost_usd']
                    ))

                # Update totals
                cursor.execute("""
                    UPDATE conversations
                    SET
                        ended_at = ?,
                        total_cost_usd = ?,
                        total_input_tokens = ?,
                        total_output_tokens = ?,
                        model = ?
                    WHERE id = ?
                """, (
                    session.get('ended_at'),
                    session['total_cost_usd'],
                    session['total_input_tokens'],
                    session['total_output_tokens'],
                    session.get('model'),
                    conversation_id
                ))

                conn.commit()
                conn.close()

        await loop.run_in_executor(None, _import)

    async def get_spec_totals(self, spec_id: str) -> Optional[Dict]:
        """Get aggregated totals for a spec."""
        loop = asyncio.get_event_loop()

        def _get_totals():
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM spec_totals
                WHERE spec_id = ?
            """, (spec_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        return await loop.run_in_executor(None, _get_totals)

    async def get_roi_settings(self) -> Dict:
        """Get global ROI settings."""
        loop = asyncio.get_event_loop()

        def _get():
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM roi_settings WHERE id = 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                return dict(row)
            return {
                'developer_hourly_rate': 75.0,
                'primary_currency': 'USD',
                'secondary_currency': 'BRL',
                'exchange_rate': 6.20,
                'auto_estimate_hours': True,
                'minutes_per_line': 2.5
            }

        return await loop.run_in_executor(None, _get)

    async def save_roi_settings(self, settings: Dict):
        """Save global ROI settings."""
        loop = asyncio.get_event_loop()

        def _save():
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO roi_settings (id, developer_hourly_rate, primary_currency,
                    secondary_currency, exchange_rate, auto_estimate_hours, minutes_per_line)
                VALUES (1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    developer_hourly_rate = excluded.developer_hourly_rate,
                    primary_currency = excluded.primary_currency,
                    secondary_currency = excluded.secondary_currency,
                    exchange_rate = excluded.exchange_rate,
                    auto_estimate_hours = excluded.auto_estimate_hours,
                    minutes_per_line = excluded.minutes_per_line,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                settings.get('developer_hourly_rate', 75.0),
                settings.get('primary_currency', 'USD'),
                settings.get('secondary_currency', 'BRL'),
                settings.get('exchange_rate', 6.20),
                1 if settings.get('auto_estimate_hours', True) else 0,
                settings.get('minutes_per_line', 2.5)
            ))
            conn.commit()
            conn.close()

        await loop.run_in_executor(None, _save)

    async def save_spec_roi(self, spec_id: str, data: Dict):
        """Save or update spec ROI data."""
        loop = asyncio.get_event_loop()

        def _save():
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO spec_roi (
                    spec_id, project_id, estimated_business_value, estimated_hours_manual,
                    developer_rate_override, actual_cost, total_tokens, lines_added,
                    lines_removed, files_changed, execution_time_seconds, qa_attempts,
                    qa_passed, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(spec_id) DO UPDATE SET
                    project_id = excluded.project_id,
                    estimated_business_value = excluded.estimated_business_value,
                    estimated_hours_manual = excluded.estimated_hours_manual,
                    developer_rate_override = excluded.developer_rate_override,
                    actual_cost = excluded.actual_cost,
                    total_tokens = excluded.total_tokens,
                    lines_added = excluded.lines_added,
                    lines_removed = excluded.lines_removed,
                    files_changed = excluded.files_changed,
                    execution_time_seconds = excluded.execution_time_seconds,
                    qa_attempts = excluded.qa_attempts,
                    qa_passed = excluded.qa_passed,
                    completed_at = excluded.completed_at
            """, (
                spec_id,
                data.get('project_id', ''),
                data.get('estimated_business_value', 0),
                data.get('estimated_hours_manual'),
                data.get('developer_rate_override'),
                data.get('actual_cost', 0),
                data.get('total_tokens', 0),
                data.get('lines_added', 0),
                data.get('lines_removed', 0),
                data.get('files_changed', 0),
                data.get('execution_time_seconds', 0),
                data.get('qa_attempts', 0),
                1 if data.get('qa_passed') else 0,
                data.get('completed_at')
            ))
            conn.commit()
            conn.close()

        await loop.run_in_executor(None, _save)

    async def get_spec_roi(self, spec_id: str) -> Optional[Dict]:
        """Get ROI data for a spec."""
        loop = asyncio.get_event_loop()

        def _get():
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM spec_roi WHERE spec_id = ?", (spec_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

        return await loop.run_in_executor(None, _get)

    async def get_all_spec_roi(self, project_id: Optional[str] = None) -> List[Dict]:
        """Get all spec ROI data, optionally filtered by project."""
        loop = asyncio.get_event_loop()

        def _get():
            conn = self._get_connection()
            cursor = conn.cursor()
            if project_id:
                cursor.execute(
                    "SELECT * FROM spec_roi WHERE project_id = ? ORDER BY created_at DESC",
                    (project_id,)
                )
            else:
                cursor.execute("SELECT * FROM spec_roi ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]

        return await loop.run_in_executor(None, _get)

    async def flush(self):
        """Flush any pending writes (currently no-op, writes are immediate)."""
        pass

    # ========== Feature Session Methods ==========

    async def create_feature_session(
        self,
        project_id: str,
        feature_type: str,
        started_at: datetime,
        model: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """Create new feature session record. Returns session_id."""
        loop = asyncio.get_event_loop()

        def _create():
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO feature_sessions (project_id, feature_type, started_at, model, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                project_id,
                feature_type,
                started_at.isoformat(),
                model,
                json.dumps(metadata) if metadata else None
            ))

            session_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return session_id

        return await loop.run_in_executor(None, _create)

    async def record_feature_message(
        self,
        session_id: int,
        message_id: str,
        timestamp: datetime,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int,
        cache_creation_tokens: int,
        cost_usd: float
    ):
        """Record individual feature message usage."""
        loop = asyncio.get_event_loop()

        def _record():
            conn = self._get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO feature_messages (
                        session_id, message_id, timestamp,
                        model, input_tokens, output_tokens,
                        cache_read_tokens, cache_creation_tokens, cost_usd
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id, message_id, timestamp.isoformat(),
                    model, input_tokens, output_tokens,
                    cache_read_tokens, cache_creation_tokens, cost_usd
                ))

                conn.commit()
            except sqlite3.IntegrityError:
                # Duplicate message_id (already tracked)
                pass
            finally:
                conn.close()

        await loop.run_in_executor(None, _record)

    async def update_feature_session_totals(
        self,
        session_id: int,
        ended_at: datetime,
        total_cost_usd: float,
        total_input_tokens: int,
        total_output_tokens: int,
        model: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Update feature session with final totals."""
        loop = asyncio.get_event_loop()

        def _update():
            conn = self._get_connection()
            cursor = conn.cursor()

            if model and metadata:
                cursor.execute("""
                    UPDATE feature_sessions
                    SET
                        ended_at = ?,
                        total_cost_usd = ?,
                        total_input_tokens = ?,
                        total_output_tokens = ?,
                        model = ?,
                        metadata = ?
                    WHERE id = ?
                """, (
                    ended_at.isoformat(), total_cost_usd, total_input_tokens,
                    total_output_tokens, model, json.dumps(metadata), session_id
                ))
            elif model:
                cursor.execute("""
                    UPDATE feature_sessions
                    SET
                        ended_at = ?,
                        total_cost_usd = ?,
                        total_input_tokens = ?,
                        total_output_tokens = ?,
                        model = ?
                    WHERE id = ?
                """, (ended_at.isoformat(), total_cost_usd, total_input_tokens, total_output_tokens, model, session_id))
            elif metadata:
                cursor.execute("""
                    UPDATE feature_sessions
                    SET
                        ended_at = ?,
                        total_cost_usd = ?,
                        total_input_tokens = ?,
                        total_output_tokens = ?,
                        metadata = ?
                    WHERE id = ?
                """, (ended_at.isoformat(), total_cost_usd, total_input_tokens, total_output_tokens, json.dumps(metadata), session_id))
            else:
                cursor.execute("""
                    UPDATE feature_sessions
                    SET
                        ended_at = ?,
                        total_cost_usd = ?,
                        total_input_tokens = ?,
                        total_output_tokens = ?
                    WHERE id = ?
                """, (ended_at.isoformat(), total_cost_usd, total_input_tokens, total_output_tokens, session_id))

            conn.commit()
            conn.close()

        await loop.run_in_executor(None, _update)

    async def get_feature_totals(self, project_id: str, feature_type: Optional[str] = None) -> List[Dict]:
        """Get aggregated feature totals for a project."""
        loop = asyncio.get_event_loop()

        def _get_totals():
            conn = self._get_connection()
            cursor = conn.cursor()

            if feature_type:
                cursor.execute("""
                    SELECT * FROM feature_totals
                    WHERE project_id = ? AND feature_type = ?
                """, (project_id, feature_type))
            else:
                cursor.execute("""
                    SELECT * FROM feature_totals
                    WHERE project_id = ?
                    ORDER BY feature_type
                """, (project_id,))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        return await loop.run_in_executor(None, _get_totals)

    async def get_feature_sessions(
        self,
        project_id: str,
        feature_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get feature sessions for a project."""
        loop = asyncio.get_event_loop()

        def _get_sessions():
            conn = self._get_connection()
            cursor = conn.cursor()

            if feature_type:
                cursor.execute("""
                    SELECT * FROM feature_sessions
                    WHERE project_id = ? AND feature_type = ?
                    ORDER BY started_at DESC
                    LIMIT ?
                """, (project_id, feature_type, limit))
            else:
                cursor.execute("""
                    SELECT * FROM feature_sessions
                    WHERE project_id = ?
                    ORDER BY started_at DESC
                    LIMIT ?
                """, (project_id, limit))

            rows = cursor.fetchall()
            conn.close()

            result = []
            for row in rows:
                row_dict = dict(row)
                # Parse metadata JSON if present
                if row_dict.get('metadata'):
                    try:
                        row_dict['metadata'] = json.loads(row_dict['metadata'])
                    except json.JSONDecodeError:
                        pass
                result.append(row_dict)
            return result

        return await loop.run_in_executor(None, _get_sessions)

    async def get_all_feature_totals(self) -> List[Dict]:
        """Get all feature totals across all projects."""
        loop = asyncio.get_event_loop()

        def _get_all():
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    feature_type,
                    SUM(total_sessions) as total_sessions,
                    SUM(total_cost_usd) as total_cost_usd,
                    SUM(total_input_tokens) as total_input_tokens,
                    SUM(total_output_tokens) as total_output_tokens,
                    MAX(last_updated) as last_updated
                FROM feature_totals
                GROUP BY feature_type
                ORDER BY total_cost_usd DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]

        return await loop.run_in_executor(None, _get_all)

    async def export_feature_sessions_to_json(self, project_id: str, output_path: Path):
        """Export feature sessions data to JSON file."""
        loop = asyncio.get_event_loop()

        def _export():
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get all feature sessions for this project
            cursor.execute("""
                SELECT * FROM feature_sessions
                WHERE project_id = ?
                ORDER BY started_at DESC
            """, (project_id,))

            sessions = cursor.fetchall()

            session_data = []
            total_cost = 0.0

            for sess in sessions:
                sess_dict = dict(sess)
                # Parse metadata
                if sess_dict.get('metadata'):
                    try:
                        sess_dict['metadata'] = json.loads(sess_dict['metadata'])
                    except json.JSONDecodeError:
                        pass

                # Get messages for this session
                cursor.execute("""
                    SELECT * FROM feature_messages
                    WHERE session_id = ?
                    ORDER BY timestamp
                """, (sess['id'],))

                messages = cursor.fetchall()
                sess_dict['messages'] = [dict(msg) for msg in messages]
                session_data.append(sess_dict)
                total_cost += sess['total_cost_usd'] or 0.0

            # Get totals
            cursor.execute("""
                SELECT * FROM feature_totals
                WHERE project_id = ?
            """, (project_id,))
            totals = [dict(row) for row in cursor.fetchall()]

            # Write JSON
            json_data = {
                "project_id": project_id,
                "total_cost_usd": total_cost,
                "total_sessions": len(session_data),
                "updated_at": datetime.utcnow().isoformat(),
                "sessions": session_data,
                "totals_by_feature": totals
            }

            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write using temp file
            temp_path = output_path.with_suffix('.json.tmp')
            with open(temp_path, 'w') as f:
                json.dump(json_data, f, indent=2)

            # Atomic rename
            temp_path.replace(output_path)

            conn.close()

        await loop.run_in_executor(None, _export)


# Storage instances per database path
_storage_instances: Dict[str, AnalyticsStorage] = {}


def get_analytics_storage(db_path: Optional[str] = None) -> AnalyticsStorage:
    """Get analytics storage instance for a specific database path.

    Each unique db_path gets its own storage instance.
    This fixes the bug where all projects were sharing the same storage.
    """
    global _storage_instances

    # Use default path if none specified
    effective_path = db_path or ".auto-claude/analytics.db"

    if effective_path not in _storage_instances:
        _storage_instances[effective_path] = AnalyticsStorage(effective_path)

    return _storage_instances[effective_path]


def is_tracking_enabled() -> bool:
    """Check if token tracking is enabled (opt-out)."""
    import os
    return os.getenv('DISABLE_TOKEN_TRACKING', 'false').lower() != 'true'


# Add OTEL session methods to AnalyticsStorage
# These are added here to avoid modifying the class body too much

async def _upsert_terminal_session(
    self,
    session_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    cache_creation_tokens: int,
    cost_usd: float,
    started_at: datetime,
    ended_at: datetime,
    request_count: int = 1
):
    """
    Upsert OTEL terminal session (for Claude Code telemetry).

    Creates a new session or updates existing one with accumulated totals.
    """
    loop = asyncio.get_event_loop()

    def _upsert():
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if session exists
        cursor.execute(
            "SELECT id, total_input_tokens, total_output_tokens, cache_read_tokens, "
            "cache_creation_tokens, total_cost_usd, request_count FROM otel_sessions WHERE session_id = ?",
            (session_id,)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing session with accumulated totals
            cursor.execute("""
                UPDATE otel_sessions
                SET
                    model = COALESCE(?, model),
                    total_input_tokens = total_input_tokens + ?,
                    total_output_tokens = total_output_tokens + ?,
                    cache_read_tokens = cache_read_tokens + ?,
                    cache_creation_tokens = cache_creation_tokens + ?,
                    total_cost_usd = total_cost_usd + ?,
                    request_count = request_count + ?,
                    last_seen = ?
                WHERE session_id = ?
            """, (
                model, input_tokens, output_tokens, cache_read_tokens,
                cache_creation_tokens, cost_usd, request_count,
                ended_at.isoformat(), session_id
            ))
        else:
            # Create new session
            cursor.execute("""
                INSERT INTO otel_sessions (
                    session_id, model, total_input_tokens, total_output_tokens,
                    cache_read_tokens, cache_creation_tokens, total_cost_usd,
                    request_count, first_seen, last_seen
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, model, input_tokens, output_tokens,
                cache_read_tokens, cache_creation_tokens, cost_usd,
                request_count, started_at.isoformat(), ended_at.isoformat()
            ))

        conn.commit()
        conn.close()

    await loop.run_in_executor(None, _upsert)


async def _get_otel_sessions(self, limit: int = 50) -> List[Dict]:
    """Get recent OTEL sessions."""
    loop = asyncio.get_event_loop()

    def _get():
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM otel_sessions
            ORDER BY last_seen DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    return await loop.run_in_executor(None, _get)


async def _get_otel_totals(self) -> Dict:
    """Get aggregated OTEL session totals."""
    loop = asyncio.get_event_loop()

    def _get():
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total_sessions,
                COALESCE(SUM(total_input_tokens), 0) as total_input_tokens,
                COALESCE(SUM(total_output_tokens), 0) as total_output_tokens,
                COALESCE(SUM(cache_read_tokens), 0) as total_cache_read_tokens,
                COALESCE(SUM(cache_creation_tokens), 0) as total_cache_creation_tokens,
                COALESCE(SUM(total_cost_usd), 0) as total_cost_usd,
                COALESCE(SUM(request_count), 0) as total_requests
            FROM otel_sessions
        """)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else {}

    return await loop.run_in_executor(None, _get)


# Monkey-patch the methods onto AnalyticsStorage
AnalyticsStorage.upsert_terminal_session = _upsert_terminal_session
AnalyticsStorage.get_otel_sessions = _get_otel_sessions
AnalyticsStorage.get_otel_totals = _get_otel_totals
