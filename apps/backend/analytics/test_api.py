"""Tests for Analytics API using TDD approach."""
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database with sample analytics data."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create conversations table
    cursor.execute("""
        CREATE TABLE conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spec_id TEXT NOT NULL,
            session_number INTEGER,
            phase TEXT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            total_cost_usd REAL DEFAULT 0.0,
            total_input_tokens INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            model TEXT
        )
    """)

    # Create messages table (for completeness)
    cursor.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT,
            content TEXT,
            tokens INTEGER,
            cost_usd REAL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)

    # Create spec_totals table
    cursor.execute("""
        CREATE TABLE spec_totals (
            spec_id TEXT PRIMARY KEY,
            total_cost_usd REAL DEFAULT 0.0,
            total_input_tokens INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            conversation_count INTEGER DEFAULT 0
        )
    """)

    # Insert sample data
    base_time = datetime.now() - timedelta(days=7)

    # Active session (no ended_at)
    cursor.execute("""
        INSERT INTO conversations
        (spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("001-feature-a", 1, "planner", base_time.isoformat(), None, 0.25, 1000, 500, "claude-opus-4-5"))

    # Completed sessions for spec 001-feature-a
    for day in range(1, 6):
        dt = base_time + timedelta(days=day)
        cursor.execute("""
            INSERT INTO conversations
            (spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("001-feature-a", day + 1, "coder", dt.isoformat(), (dt + timedelta(hours=1)).isoformat(),
              0.50 + (day * 0.1), 2000 + (day * 100), 1000 + (day * 50), "claude-opus-4-5"))

    # Completed sessions for spec 002-feature-b
    for day in range(2, 5):
        dt = base_time + timedelta(days=day)
        cursor.execute("""
            INSERT INTO conversations
            (spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("002-feature-b", day - 1, "qa_reviewer", dt.isoformat(), (dt + timedelta(hours=2)).isoformat(),
              0.30 + (day * 0.05), 1500 + (day * 80), 800 + (day * 40), "claude-sonnet-4-5"))

    # Update spec_totals
    cursor.execute("""
        INSERT INTO spec_totals (spec_id, total_cost_usd, total_input_tokens, total_output_tokens, conversation_count)
        VALUES ('001-feature-a', 3.25, 12500, 6250, 6)
    """)

    cursor.execute("""
        INSERT INTO spec_totals (spec_id, total_cost_usd, total_input_tokens, total_output_tokens, conversation_count)
        VALUES ('002-feature-b', 1.05, 4740, 2520, 3)
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def client(temp_db):
    """Create FastAPI test client with temporary database."""
    os.environ["ANALYTICS_DB_PATH"] = temp_db

    # Import after setting env var to ensure it's picked up
    from analytics.api import app

    with TestClient(app) as client:
        yield client

    # Cleanup
    if "ANALYTICS_DB_PATH" in os.environ:
        del os.environ["ANALYTICS_DB_PATH"]


def test_health_endpoint(client):
    """Test GET /health returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data


def test_health_endpoint_missing_db():
    """Test GET /health returns 503 when database is not configured."""
    # Ensure env var is not set
    if "ANALYTICS_DB_PATH" in os.environ:
        del os.environ["ANALYTICS_DB_PATH"]

    from analytics.api import app

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert "not configured" in data["detail"].lower()


def test_totals_endpoint(client):
    """Test GET /analytics/totals returns global analytics."""
    response = client.get("/analytics/totals")
    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "total_cost_usd" in data
    assert "total_tokens" in data
    assert "active_sessions" in data

    # Verify token structure
    assert "input" in data["total_tokens"]
    assert "output" in data["total_tokens"]

    # Verify values (from our sample data)
    assert data["total_cost_usd"] > 0
    assert data["total_tokens"]["input"] > 0
    assert data["total_tokens"]["output"] > 0
    assert data["active_sessions"] == 1  # One session without ended_at


def test_spec_endpoint_existing_spec(client):
    """Test GET /analytics/spec/{spec_id} returns spec-specific analytics."""
    response = client.get("/analytics/spec/001-feature-a")
    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert data["spec_id"] == "001-feature-a"
    assert "total_cost_usd" in data
    assert "total_tokens" in data
    assert "conversation_count" in data

    # Verify token structure
    assert "input" in data["total_tokens"]
    assert "output" in data["total_tokens"]

    # Verify values
    assert data["total_cost_usd"] == 3.25
    assert data["total_tokens"]["input"] == 12500
    assert data["total_tokens"]["output"] == 6250
    assert data["conversation_count"] == 6


def test_spec_endpoint_nonexistent_spec(client):
    """Test GET /analytics/spec/{spec_id} returns 404 for unknown spec."""
    response = client.get("/analytics/spec/999-nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_conversations_endpoint(client):
    """Test GET /analytics/conversations returns recent conversations."""
    response = client.get("/analytics/conversations")
    assert response.status_code == 200
    data = response.json()

    # Verify it's a list
    assert isinstance(data, list)
    assert len(data) > 0

    # Verify first conversation structure
    conv = data[0]
    assert "id" in conv
    assert "spec_id" in conv
    assert "phase" in conv
    assert "cost" in conv
    assert "tokens" in conv
    assert "started_at" in conv
    assert "ended_at" in conv

    # Verify token structure
    assert "input" in conv["tokens"]
    assert "output" in conv["tokens"]

    # Verify nullable ended_at
    active_convs = [c for c in data if c["ended_at"] is None]
    assert len(active_convs) == 1  # We have one active session


def test_conversations_endpoint_with_limit(client):
    """Test GET /analytics/conversations?limit=3 respects limit parameter."""
    response = client.get("/analytics/conversations?limit=3")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) <= 3


def test_cost_trend_endpoint(client):
    """Test GET /analytics/cost-trend returns daily cost aggregates."""
    response = client.get("/analytics/cost-trend")
    assert response.status_code == 200
    data = response.json()

    # Verify it's a list
    assert isinstance(data, list)
    assert len(data) > 0

    # Verify first entry structure
    entry = data[0]
    assert "date" in entry
    assert "cost" in entry

    # Verify date format (YYYY-MM-DD)
    assert len(entry["date"]) == 10
    assert entry["date"][4] == "-"
    assert entry["date"][7] == "-"

    # Verify cost is a float
    assert isinstance(entry["cost"], float)
    assert entry["cost"] >= 0


def test_cost_trend_endpoint_with_days(client):
    """Test GET /analytics/cost-trend?days=3 respects days parameter."""
    response = client.get("/analytics/cost-trend?days=3")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    # Should have at most 3 days of data
    assert len(data) <= 3
