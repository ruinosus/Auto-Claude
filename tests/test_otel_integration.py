#!/usr/bin/env python3
"""
OpenTelemetry Integration Test
================================

End-to-end test for OpenTelemetry integration with token tracking pipeline.

Tests the complete flow:
1. UsageTracker initialization
2. Session lifecycle (start/end)
3. Message tracking and OTel export
4. Data persistence to SQLite
5. Graceful degradation on OTel failures
"""

import asyncio
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Add auto-claude to path if needed
import sys
if str(Path(__file__).parent.parent / "auto-claude") not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent / "auto-claude"))

from analytics import (
    AnalyticsStorage,
    UsageTracker,
    ModelPricing,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_otel_integration.db"
        yield db_path


@pytest.fixture
def storage(temp_db):
    """Create AnalyticsStorage instance for testing."""
    return AnalyticsStorage(str(temp_db))


@pytest.fixture
def mock_pricing():
    """Mock get_model_pricing function."""
    async def _get_pricing(model_id):
        return ModelPricing(
            model_id=model_id,
            provider="anthropic",
            input_price=3.0,
            output_price=15.0,
            cache_read_price=0.3,
            cache_write_price=3.75,
            context_limit=200000,
            output_limit=64000,
            last_updated=datetime.utcnow()
        )
    return _get_pricing


@pytest.fixture
def mock_otel_exporter():
    """Create mock OTel exporter."""
    exporter = MagicMock()
    exporter.start_session = MagicMock()
    exporter.record_message = MagicMock()
    exporter.record_session = MagicMock()
    exporter.end_session = MagicMock()
    return exporter


# =============================================================================
# End-to-End Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_complete_pipeline_with_otel(storage, temp_db, mock_pricing, mock_otel_exporter):
    """
    End-to-end test of complete pipeline: tracking → storage → OTel.

    Tests:
    - Session lifecycle (start_session, end_session)
    - Message tracking and OTel export (3 messages)
    - Data persistence to SQLite
    - Session metrics calculation
    """
    with patch('analytics.usage_tracker.get_model_pricing', mock_pricing):
        with patch('analytics.usage_tracker.get_otel_exporter', return_value=mock_otel_exporter):
            with patch('analytics.usage_tracker.is_otel_enabled', return_value=True):
                # Step 1: Create UsageTracker
                tracker = UsageTracker(
                    spec_id="001-otel-test",
                    session_num=1,
                    phase="coding",
                    storage=storage
                )

                assert tracker.spec_id == "001-otel-test"
                assert tracker.session_num == 1
                assert tracker.phase == "coding"
                assert tracker.conversation_id is None

                # Step 2: Start session and verify start_session() called
                conversation_id = await tracker.start_conversation()

                assert conversation_id > 0
                assert tracker.conversation_id == conversation_id
                mock_otel_exporter.start_session.assert_called_once()

                # Step 3: Track 3 messages and verify record_message() called 3 times
                for i in range(3):
                    message = MagicMock()
                    message.id = f"msg_{i+1:03d}"
                    message.model = "claude-sonnet-4-5"
                    message.usage = {
                        'input_tokens': 1000 + (i * 100),
                        'output_tokens': 500 + (i * 50),
                        'cache_read_input_tokens': 100 + (i * 10),
                        'cache_creation_input_tokens': 50 + (i * 5)
                    }

                    await tracker._track_assistant_message(message)

                # Verify record_message called 3 times
                assert mock_otel_exporter.record_message.call_count == 3

                # Verify call arguments for messages
                for i, call in enumerate(mock_otel_exporter.record_message.call_args_list):
                    kwargs = call[1]
                    assert kwargs['spec_id'] == "001-otel-test"
                    assert kwargs['phase'] == "coding"
                    assert kwargs['model'] == "claude-sonnet-4-5"
                    assert kwargs['input_tokens'] == 1000 + (i * 100)
                    assert kwargs['output_tokens'] == 500 + (i * 50)
                    assert kwargs['cost_usd'] > 0

                # Verify tracker accumulated totals
                expected_input_tokens = sum(1000 + (i * 100) for i in range(3))
                expected_output_tokens = sum(500 + (i * 50) for i in range(3))

                assert tracker.total_input_tokens == expected_input_tokens  # 3300
                assert tracker.total_output_tokens == expected_output_tokens  # 1650
                assert tracker.total_cost_usd > 0

                # Step 4: Update conversation totals (simulate ResultMessage)
                result_message = MagicMock()
                result_message.total_cost_usd = tracker.total_cost_usd
                await tracker._track_result_message(result_message)

                # Step 5: Finalize and verify record_session() and end_session() called
                await tracker.finalize()

                mock_otel_exporter.record_session.assert_called_once()
                mock_otel_exporter.end_session.assert_called_once()

                # Verify record_session arguments
                session_call = mock_otel_exporter.record_session.call_args[1]
                assert session_call['spec_id'] == "001-otel-test"
                assert session_call['phase'] == "coding"
                assert session_call['total_cost_usd'] > 0
                assert session_call['duration_seconds'] >= 0

                # Step 6: Verify data persisted to SQLite database
                conn = sqlite3.connect(str(temp_db))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Verify conversation record
                cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
                conv_row = cursor.fetchone()

                assert conv_row is not None
                assert conv_row['spec_id'] == "001-otel-test"
                assert conv_row['session_number'] == 1
                assert conv_row['phase'] == "coding"
                assert conv_row['total_input_tokens'] == expected_input_tokens
                assert conv_row['total_output_tokens'] == expected_output_tokens
                assert conv_row['total_cost_usd'] > 0
                assert conv_row['model'] == "claude-sonnet-4-5"
                assert conv_row['ended_at'] is not None

                # Verify 3 messages in database
                cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp", (conversation_id,))
                message_rows = cursor.fetchall()

                assert len(message_rows) == 3

                for i, msg_row in enumerate(message_rows):
                    assert msg_row['message_id'] == f"msg_{i+1:03d}"
                    assert msg_row['model'] == "claude-sonnet-4-5"
                    assert msg_row['input_tokens'] == 1000 + (i * 100)
                    assert msg_row['output_tokens'] == 500 + (i * 50)
                    assert msg_row['cache_read_tokens'] == 100 + (i * 10)
                    assert msg_row['cache_creation_tokens'] == 50 + (i * 5)
                    assert msg_row['cost_usd'] > 0

                conn.close()


@pytest.mark.asyncio
async def test_pipeline_without_otel(storage, temp_db, mock_pricing):
    """
    Test pipeline works correctly when OTel is disabled.

    Ensures tracking continues normally even when OTEL_ENABLED=false.
    """
    with patch('analytics.usage_tracker.get_model_pricing', mock_pricing):
        with patch('analytics.usage_tracker.is_otel_enabled', return_value=False):
            tracker = UsageTracker(
                spec_id="002-no-otel",
                session_num=1,
                phase="planning",
                storage=storage
            )

            # Start session (should not call OTel)
            conversation_id = await tracker.start_conversation()
            assert conversation_id > 0

            # Track messages
            message = MagicMock()
            message.id = "msg_no_otel"
            message.model = "claude-sonnet-4-5"
            message.usage = {
                'input_tokens': 2000,
                'output_tokens': 1000,
                'cache_read_input_tokens': 0,
                'cache_creation_input_tokens': 0
            }

            await tracker._track_assistant_message(message)

            # Verify tracking still works
            assert tracker.total_input_tokens == 2000
            assert tracker.total_output_tokens == 1000
            assert tracker.total_cost_usd > 0

            # Finalize
            await tracker.finalize()

            # Verify data persisted
            conn = sqlite3.connect(str(temp_db))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?", (conversation_id,))
            count = cursor.fetchone()['count']
            assert count == 1

            conn.close()


@pytest.mark.asyncio
async def test_otel_failure_graceful_degradation(storage, mock_pricing):
    """
    Test graceful degradation when OTel export fails.

    Ensures tracking continues even when OTel exporter throws exceptions.
    Note: When record_session() fails in finalize(), end_session() is not called
    because the exception is caught and suppressed by the try/except block.
    """
    # Create failing OTel exporter
    failing_exporter = MagicMock()
    failing_exporter.start_session.side_effect = Exception("OTel service unavailable")
    failing_exporter.record_message.side_effect = Exception("OTel service unavailable")
    failing_exporter.record_session.side_effect = Exception("OTel service unavailable")
    failing_exporter.end_session.side_effect = Exception("OTel service unavailable")

    with patch('analytics.usage_tracker.get_model_pricing', mock_pricing):
        with patch('analytics.usage_tracker.get_otel_exporter', return_value=failing_exporter):
            with patch('analytics.usage_tracker.is_otel_enabled', return_value=True):
                tracker = UsageTracker(
                    spec_id="003-otel-fail",
                    session_num=1,
                    phase="validation",
                    storage=storage
                )

                # Start session (OTel fails but tracking continues)
                conversation_id = await tracker.start_conversation()
                assert conversation_id > 0

                # Track message (OTel fails but tracking continues)
                message = MagicMock()
                message.id = "msg_resilient"
                message.model = "claude-sonnet-4-5"
                message.usage = {
                    'input_tokens': 1500,
                    'output_tokens': 750,
                    'cache_read_input_tokens': 0,
                    'cache_creation_input_tokens': 0
                }

                # Should not raise exception
                await tracker._track_assistant_message(message)

                # Verify tracking still worked
                assert tracker.total_input_tokens == 1500
                assert tracker.total_output_tokens == 750
                assert tracker.total_cost_usd > 0

                # Finalize (OTel fails but tracking completes)
                await tracker.finalize()

                # Verify OTel exporter was called (attempts were made)
                # Note: start_session, record_message, and record_session are called
                # end_session is NOT called when record_session fails
                # because the exception is caught before end_session is reached
                failing_exporter.start_session.assert_called_once()
                failing_exporter.record_message.assert_called_once()
                failing_exporter.record_session.assert_called_once()
                # end_session not called due to exception handling in finalize()


@pytest.mark.asyncio
async def test_multiple_sessions_same_spec(storage, temp_db, mock_pricing, mock_otel_exporter):
    """
    Test tracking multiple sessions for the same spec.

    Verifies:
    - Multiple conversations can be created for same spec
    - Each session is tracked independently
    - Spec totals are aggregated correctly
    """
    with patch('analytics.usage_tracker.get_model_pricing', mock_pricing):
        with patch('analytics.usage_tracker.get_otel_exporter', return_value=mock_otel_exporter):
            with patch('analytics.usage_tracker.is_otel_enabled', return_value=True):
                # Session 1
                tracker1 = UsageTracker(
                    spec_id="004-multi-session",
                    session_num=1,
                    phase="planning",
                    storage=storage
                )
                conv_id_1 = await tracker1.start_conversation()

                message1 = MagicMock()
                message1.id = "msg_session_1"
                message1.model = "claude-sonnet-4-5"
                message1.usage = {
                    'input_tokens': 1000,
                    'output_tokens': 500,
                    'cache_read_input_tokens': 0,
                    'cache_creation_input_tokens': 0
                }
                await tracker1._track_assistant_message(message1)
                await tracker1._track_result_message(MagicMock(total_cost_usd=tracker1.total_cost_usd))
                await tracker1.finalize()

                # Session 2
                tracker2 = UsageTracker(
                    spec_id="004-multi-session",
                    session_num=2,
                    phase="coding",
                    storage=storage
                )
                conv_id_2 = await tracker2.start_conversation()

                message2 = MagicMock()
                message2.id = "msg_session_2"
                message2.model = "claude-sonnet-4-5"
                message2.usage = {
                    'input_tokens': 2000,
                    'output_tokens': 1000,
                    'cache_read_input_tokens': 0,
                    'cache_creation_input_tokens': 0
                }
                await tracker2._track_assistant_message(message2)
                await tracker2._track_result_message(MagicMock(total_cost_usd=tracker2.total_cost_usd))
                await tracker2.finalize()

                # Verify both sessions in database
                conn = sqlite3.connect(str(temp_db))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT COUNT(*) as count FROM conversations WHERE spec_id = ?",
                    ("004-multi-session",)
                )
                count = cursor.fetchone()['count']
                assert count == 2

                # Verify spec totals aggregated
                cursor.execute(
                    "SELECT * FROM spec_totals WHERE spec_id = ?",
                    ("004-multi-session",)
                )
                totals = cursor.fetchone()

                assert totals is not None
                assert totals['total_conversations'] == 2
                assert totals['total_input_tokens'] == 3000  # 1000 + 2000
                assert totals['total_output_tokens'] == 1500  # 500 + 1000

                conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
