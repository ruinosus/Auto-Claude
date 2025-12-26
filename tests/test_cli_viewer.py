#!/usr/bin/env python3
"""
CLI Viewer Tests
================

Tests for analytics CLI visualization tool.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
import sys
from datetime import datetime

if str(Path(__file__).parent.parent / "auto-claude") not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent / "auto-claude"))


@pytest.mark.asyncio
async def test_cli_viewer_shows_summary(capsys):
    """Test CLI viewer displays summary."""
    from analytics.cli_viewer import show_summary
    from analytics import AnalyticsStorage

    # Create temp DB with data
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        storage = AnalyticsStorage(str(db_path))

        # Add test data
        conv_id = await storage.create_conversation(
            spec_id="001-test",
            session_number=1,
            phase="coding",
            started_at=datetime.utcnow()
        )

        await storage.update_conversation_totals(
            conversation_id=conv_id,
            ended_at=datetime.utcnow(),
            total_cost_usd=0.5,
            total_input_tokens=10000,
            total_output_tokens=5000,
            model="claude-sonnet-4-5"
        )

        # Show summary
        show_summary(str(db_path))

        # Verify output
        captured = capsys.readouterr()
        assert "001-test" in captured.out
        assert "0.5" in captured.out  # Cost
        assert "10,000" in captured.out  # Input tokens (formatted with comma)


@pytest.mark.asyncio
async def test_cli_viewer_shows_spec_detail(capsys):
    """Test CLI viewer displays spec detail."""
    from analytics.cli_viewer import show_spec
    from analytics import AnalyticsStorage

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        storage = AnalyticsStorage(str(db_path))

        conv_id = await storage.create_conversation(
            spec_id="002-test",
            session_number=1,
            phase="planning",
            started_at=datetime.utcnow()
        )

        await storage.update_conversation_totals(
            conversation_id=conv_id,
            ended_at=datetime.utcnow(),
            total_cost_usd=0.75,
            total_input_tokens=15000,
            total_output_tokens=7500,
            model="claude-sonnet-4-5"
        )

        show_spec("002-test", str(db_path))

        captured = capsys.readouterr()
        assert "002-test" in captured.out
        assert "0.75" in captured.out


def test_cli_viewer_missing_database(capsys):
    """Test CLI viewer handles missing database gracefully."""
    from analytics.cli_viewer import show_summary

    show_summary("/nonexistent/path/db.sqlite")

    captured = capsys.readouterr()
    assert "Analytics database not found" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
