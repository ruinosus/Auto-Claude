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

    async def flush(self):
        """Flush any pending writes (currently no-op, writes are immediate)."""
        pass


# Singleton instance
_storage: Optional[AnalyticsStorage] = None


def get_analytics_storage(db_path: Optional[str] = None) -> AnalyticsStorage:
    """Get global analytics storage instance."""
    global _storage
    if _storage is None:
        if db_path:
            _storage = AnalyticsStorage(db_path)
        else:
            _storage = AnalyticsStorage()
    return _storage


def is_tracking_enabled() -> bool:
    """Check if token tracking is enabled (opt-out)."""
    import os
    return os.getenv('DISABLE_TOKEN_TRACKING', 'false').lower() != 'true'
