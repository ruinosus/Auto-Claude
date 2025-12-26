"""FastAPI Analytics API for Auto-Claude usage metrics.

Run with: ANALYTICS_DB_PATH=/path/to/analytics.db python -m analytics.api
"""
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


# Create FastAPI app
app = FastAPI(
    title="Auto-Claude Analytics API",
    description="Analytics API for querying Auto-Claude usage metrics",
    version="1.0.0",
)

# Enable CORS for localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:*",
        "http://127.0.0.1:*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection():
    """Get database connection or raise 503 if not configured/accessible."""
    # Get database path from environment (dynamically to support testing)
    db_path = os.getenv("ANALYTICS_DB_PATH")

    if not db_path:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Set ANALYTICS_DB_PATH environment variable.",
        )

    if not Path(db_path).exists():
        raise HTTPException(
            status_code=503,
            detail=f"Database not found at {db_path}",
        )

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection error: {str(e)}",
        )


@app.get("/health")
def health_check():
    """Health check endpoint.

    Returns:
        dict: Health status and database connectivity
    """
    # Get database path from environment (dynamically to support testing)
    db_path = os.getenv("ANALYTICS_DB_PATH")

    if not db_path:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Set ANALYTICS_DB_PATH environment variable.",
        )

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()

        return {
            "status": "healthy",
            "database": "connected",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database health check failed: {str(e)}",
        )


@app.get("/analytics/totals")
def get_totals():
    """Get global analytics totals.

    Returns:
        dict: Total cost, tokens, and active sessions
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get total cost and tokens from all conversations
        cursor.execute("""
            SELECT
                COALESCE(SUM(total_cost_usd), 0.0) as total_cost,
                COALESCE(SUM(total_input_tokens), 0) as total_input,
                COALESCE(SUM(total_output_tokens), 0) as total_output
            FROM conversations
        """)
        row = cursor.fetchone()

        # Get active sessions count (ended_at IS NULL)
        cursor.execute("""
            SELECT COUNT(*) as active_count
            FROM conversations
            WHERE ended_at IS NULL
        """)
        active_row = cursor.fetchone()

        return {
            "total_cost_usd": float(row["total_cost"]),
            "total_tokens": {
                "input": int(row["total_input"]),
                "output": int(row["total_output"]),
            },
            "active_sessions": int(active_row["active_count"]),
        }
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query error: {str(e)}",
        )
    finally:
        conn.close()


@app.get("/analytics/spec/{spec_id}")
def get_spec_analytics(spec_id: str):
    """Get analytics for a specific spec.

    Args:
        spec_id: Spec identifier

    Returns:
        dict: Spec-specific analytics

    Raises:
        HTTPException: 404 if spec not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if spec exists in spec_totals
        cursor.execute("""
            SELECT
                spec_id,
                total_cost_usd,
                total_input_tokens,
                total_output_tokens,
                conversation_count
            FROM spec_totals
            WHERE spec_id = ?
        """, (spec_id,))

        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Spec '{spec_id}' not found",
            )

        return {
            "spec_id": row["spec_id"],
            "total_cost_usd": float(row["total_cost_usd"]),
            "total_tokens": {
                "input": int(row["total_input_tokens"]),
                "output": int(row["total_output_tokens"]),
            },
            "conversation_count": int(row["conversation_count"]),
        }
    except HTTPException:
        raise
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query error: {str(e)}",
        )
    finally:
        conn.close()


@app.get("/analytics/conversations")
def get_conversations(limit: int = Query(default=100, ge=1, le=1000)):
    """Get recent conversations.

    Args:
        limit: Maximum number of conversations to return (1-1000)

    Returns:
        list: List of conversation records
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                spec_id,
                phase,
                total_cost_usd as cost,
                total_input_tokens,
                total_output_tokens,
                started_at,
                ended_at
            FROM conversations
            ORDER BY started_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "spec_id": row["spec_id"],
                "phase": row["phase"],
                "cost": float(row["cost"]) if row["cost"] else 0.0,
                "tokens": {
                    "input": int(row["total_input_tokens"]) if row["total_input_tokens"] else 0,
                    "output": int(row["total_output_tokens"]) if row["total_output_tokens"] else 0,
                },
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],  # None if still active
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query error: {str(e)}",
        )
    finally:
        conn.close()


@app.get("/analytics/cost-trend")
def get_cost_trend(days: int = Query(default=7, ge=1, le=90)):
    """Get daily cost trend.

    Args:
        days: Number of days to include (1-90)

    Returns:
        list: Daily cost aggregates
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Calculate date threshold
        threshold = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                DATE(started_at) as date,
                SUM(total_cost_usd) as daily_cost
            FROM conversations
            WHERE started_at >= ?
            GROUP BY DATE(started_at)
            ORDER BY date ASC
        """, (threshold,))

        rows = cursor.fetchall()

        return [
            {
                "date": row["date"],
                "cost": float(row["daily_cost"]) if row["daily_cost"] else 0.0,
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query error: {str(e)}",
        )
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8765"))
    uvicorn.run(
        "analytics.api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
