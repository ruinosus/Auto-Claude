#!/usr/bin/env python3
"""
Analytics Module Tests
======================

Tests for token tracking, pricing, and storage components.
"""

import asyncio
import json
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Add auto-claude to path if needed
import sys
if str(Path(__file__).parent.parent / "auto-claude") not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent / "auto-claude"))

from analytics import (
    ModelPricing,
    ModelsPricingProvider,
    AnalyticsStorage,
    UsageTracker,
    get_analytics_storage,
    is_tracking_enabled,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_analytics.db"
        yield db_path


@pytest.fixture
def storage(temp_db):
    """Create AnalyticsStorage instance for testing."""
    return AnalyticsStorage(str(temp_db))


@pytest.fixture
def pricing_provider(temp_db):
    """Create ModelsPricingProvider with temp cache."""
    provider = ModelsPricingProvider()
    # Override cache path to use temp directory
    provider.cache_path = temp_db.parent / "models_dev_cache.json"
    provider._cache = None
    return provider


# =============================================================================
# ModelPricing Tests
# =============================================================================

def test_model_pricing_dataclass():
    """Test ModelPricing dataclass creation and properties."""
    pricing = ModelPricing(
        model_id="claude-sonnet-4-5",
        provider="anthropic",
        input_price=3.0,
        output_price=15.0,
        cache_read_price=0.3,
        cache_write_price=3.75,
        context_limit=200000,
        output_limit=64000,
        last_updated=datetime.utcnow()
    )

    assert pricing.model_id == "claude-sonnet-4-5"
    assert pricing.input_price == 3.0
    assert pricing.cache_read_discount == 0.9  # 1.0 - (0.3 / 3.0)
    assert pricing.cache_write_multiplier == 1.25  # 3.75 / 3.0


def test_model_pricing_zero_division():
    """Test ModelPricing handles zero prices gracefully."""
    pricing = ModelPricing(
        model_id="test-model",
        provider="test",
        input_price=0.0,
        output_price=0.0,
        cache_read_price=0.0,
        cache_write_price=0.0,
        context_limit=1000,
        output_limit=1000,
        last_updated=datetime.utcnow()
    )

    assert pricing.cache_read_discount == 0.0
    assert pricing.cache_write_multiplier == 1.0


# =============================================================================
# ModelsPricingProvider Tests
# =============================================================================

@pytest.mark.asyncio
async def test_pricing_provider_normalize_model_id(pricing_provider):
    """Test model ID normalization removes date stamps."""
    assert pricing_provider._normalize_model_id("claude-sonnet-4-5-20250929") == "claude-sonnet-4-5"
    assert pricing_provider._normalize_model_id("claude-3-5-sonnet-20241022") == "claude-3-5-sonnet"
    assert pricing_provider._normalize_model_id("claude-sonnet-4-5") == "claude-sonnet-4-5"


@pytest.mark.asyncio
async def test_pricing_provider_cache_save_load(pricing_provider):
    """Test pricing cache save and load."""
    test_data = {
        "anthropic": {
            "models": {
                "claude-sonnet-4-5": {
                    "cost": {
                        "input": 3.0,
                        "output": 15.0,
                        "cache_read": 0.3,
                        "cache_write": 3.75
                    },
                    "limit": {
                        "context": 200000,
                        "output": 64000
                    }
                }
            }
        }
    }

    pricing_provider._save_cache(test_data)
    assert pricing_provider._cache is not None

    # Reload provider
    new_provider = ModelsPricingProvider()
    new_provider.cache_path = pricing_provider.cache_path
    new_provider._load_cache()
    assert new_provider._cache is not None


@pytest.mark.asyncio
async def test_pricing_provider_extract_pricing(pricing_provider):
    """Test extracting pricing from models.dev data."""
    data = {
        "anthropic": {
            "models": {
                "claude-sonnet-4-5": {
                    "cost": {
                        "input": 3.0,
                        "output": 15.0,
                        "cache_read": 0.3,
                        "cache_write": 3.75
                    },
                    "limit": {
                        "context": 200000,
                        "output": 64000
                    }
                }
            }
        }
    }

    pricing = pricing_provider._extract_pricing_from_data(data, "claude-sonnet-4-5")
    assert pricing is not None
    assert pricing.model_id == "claude-sonnet-4-5"
    assert pricing.provider == "anthropic"
    assert pricing.input_price == 3.0
    assert pricing.output_price == 15.0


@pytest.mark.asyncio
async def test_pricing_provider_fallback_to_default(pricing_provider):
    """Test fallback to default pricing when no data available."""
    # Clear cache
    pricing_provider._cache = None

    # Mock API failure
    with patch.object(pricing_provider, '_fetch_from_api', return_value=None):
        with patch.dict('os.environ', {}, clear=True):  # Clear env vars
            pricing = await pricing_provider.get_pricing("unknown-model")

            # Should fallback to default Sonnet pricing
            assert pricing.model_id == "unknown-model"
            assert pricing.input_price == 3.0
            assert pricing.output_price == 15.0


@pytest.mark.asyncio
async def test_pricing_provider_env_fallback(pricing_provider):
    """Test fallback to environment variables."""
    pricing_provider._cache = None

    with patch.object(pricing_provider, '_fetch_from_api', return_value=None):
        with patch.dict('os.environ', {
            'CLAUDE_SONNET_4_5_INPUT_PRICE': '3.5',
            'CLAUDE_SONNET_4_5_OUTPUT_PRICE': '16.0',
            'CACHE_READ_DISCOUNT': '0.85',
            'CACHE_CREATION_MULTIPLIER': '1.3'
        }):
            pricing = await pricing_provider.get_pricing("claude-sonnet-4-5")

            assert pricing.input_price == 3.5
            assert pricing.output_price == 16.0
            assert pricing.cache_read_price == 3.5 * 0.85
            assert pricing.cache_write_price == 3.5 * 1.3


# =============================================================================
# AnalyticsStorage Tests
# =============================================================================

@pytest.mark.asyncio
async def test_storage_initialization(storage, temp_db):
    """Test storage initializes database with correct schema."""
    assert temp_db.exists()

    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    assert 'conversations' in tables
    assert 'messages' in tables
    assert 'spec_totals' in tables

    conn.close()


@pytest.mark.asyncio
async def test_storage_create_conversation(storage):
    """Test creating conversation record."""
    conversation_id = await storage.create_conversation(
        spec_id="001-test",
        session_number=1,
        phase="coding",
        started_at=datetime.utcnow()
    )

    assert conversation_id > 0

    # Verify in database
    conn = storage._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row['spec_id'] == "001-test"
    assert row['session_number'] == 1
    assert row['phase'] == "coding"


@pytest.mark.asyncio
async def test_storage_record_message(storage):
    """Test recording message usage."""
    # Create conversation first
    conversation_id = await storage.create_conversation(
        spec_id="001-test",
        session_number=1,
        phase="coding",
        started_at=datetime.utcnow()
    )

    # Record message
    await storage.record_message(
        conversation_id=conversation_id,
        message_id="msg_001",
        subtask_id="subtask_1",
        timestamp=datetime.utcnow(),
        model="claude-sonnet-4-5",
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=200,
        cache_creation_tokens=100,
        cost_usd=0.025
    )

    # Verify in database
    conn = storage._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE conversation_id = ?", (conversation_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row['message_id'] == "msg_001"
    assert row['input_tokens'] == 1000
    assert row['output_tokens'] == 500
    assert row['cost_usd'] == 0.025


@pytest.mark.asyncio
async def test_storage_message_deduplication(storage):
    """Test duplicate messages are ignored."""
    conversation_id = await storage.create_conversation(
        spec_id="001-test",
        session_number=1,
        phase="coding",
        started_at=datetime.utcnow()
    )

    # Record same message twice
    for _ in range(2):
        await storage.record_message(
            conversation_id=conversation_id,
            message_id="msg_001",
            subtask_id="subtask_1",
            timestamp=datetime.utcnow(),
            model="claude-sonnet-4-5",
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_usd=0.025
        )

    # Should only have one message
    conn = storage._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation_id,))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1


@pytest.mark.asyncio
async def test_storage_update_conversation_totals(storage):
    """Test updating conversation with final totals."""
    conversation_id = await storage.create_conversation(
        spec_id="001-test",
        session_number=1,
        phase="coding",
        started_at=datetime.utcnow()
    )

    await storage.update_conversation_totals(
        conversation_id=conversation_id,
        ended_at=datetime.utcnow(),
        total_cost_usd=0.5,
        total_input_tokens=10000,
        total_output_tokens=5000,
        model="claude-sonnet-4-5"
    )

    # Verify update
    conn = storage._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    row = cursor.fetchone()
    conn.close()

    assert row['total_cost_usd'] == 0.5
    assert row['total_input_tokens'] == 10000
    assert row['total_output_tokens'] == 5000
    assert row['model'] == "claude-sonnet-4-5"


@pytest.mark.asyncio
async def test_storage_export_to_json(storage, temp_db):
    """Test JSON export functionality."""
    # Create conversation and messages
    conversation_id = await storage.create_conversation(
        spec_id="001-test",
        session_number=1,
        phase="coding",
        started_at=datetime.utcnow()
    )

    await storage.record_message(
        conversation_id=conversation_id,
        message_id="msg_001",
        subtask_id="subtask_1",
        timestamp=datetime.utcnow(),
        model="claude-sonnet-4-5",
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        cost_usd=0.025
    )

    await storage.update_conversation_totals(
        conversation_id=conversation_id,
        ended_at=datetime.utcnow(),
        total_cost_usd=0.025,
        total_input_tokens=1000,
        total_output_tokens=500,
        model="claude-sonnet-4-5"
    )

    # Export to JSON
    json_path = temp_db.parent / "usage.json"
    await storage.export_to_json("001-test", json_path)

    # Verify JSON file
    assert json_path.exists()
    with open(json_path) as f:
        data = json.load(f)

    assert data['spec_id'] == "001-test"
    assert data['total_sessions'] == 1
    assert len(data['sessions']) == 1
    assert len(data['sessions'][0]['messages']) == 1


@pytest.mark.asyncio
async def test_storage_spec_totals_trigger(storage):
    """Test spec_totals materialized view is updated via trigger."""
    # Create and complete conversation
    conversation_id = await storage.create_conversation(
        spec_id="001-test",
        session_number=1,
        phase="coding",
        started_at=datetime.utcnow()
    )

    await storage.update_conversation_totals(
        conversation_id=conversation_id,
        ended_at=datetime.utcnow(),
        total_cost_usd=0.5,
        total_input_tokens=10000,
        total_output_tokens=5000,
        model="claude-sonnet-4-5"
    )

    # Check spec_totals was updated
    totals = await storage.get_spec_totals("001-test")
    assert totals is not None
    assert totals['total_conversations'] == 1
    assert totals['total_cost_usd'] == 0.5


# =============================================================================
# UsageTracker Tests
# =============================================================================

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


@pytest.mark.asyncio
async def test_usage_tracker_initialization(storage):
    """Test UsageTracker initialization."""
    tracker = UsageTracker(
        spec_id="001-test",
        session_num=1,
        phase="coding",
        storage=storage
    )

    assert tracker.spec_id == "001-test"
    assert tracker.session_num == 1
    assert tracker.phase == "coding"
    assert tracker.conversation_id is None
    assert tracker.total_input_tokens == 0
    assert tracker.total_output_tokens == 0


@pytest.mark.asyncio
async def test_usage_tracker_start_conversation(storage):
    """Test starting conversation tracking."""
    tracker = UsageTracker(
        spec_id="001-test",
        session_num=1,
        phase="coding",
        storage=storage
    )

    conversation_id = await tracker.start_conversation()
    assert conversation_id > 0
    assert tracker.conversation_id == conversation_id


@pytest.mark.asyncio
async def test_usage_tracker_track_assistant_message(storage, mock_pricing):
    """Test tracking AssistantMessage."""
    tracker = UsageTracker(
        spec_id="001-test",
        session_num=1,
        phase="coding",
        storage=storage
    )
    await tracker.start_conversation()

    # Create mock AssistantMessage
    message = MagicMock()
    message.id = "msg_001"
    message.model = "claude-sonnet-4-5"
    message.usage = {
        'input_tokens': 1000,
        'output_tokens': 500,
        'cache_read_input_tokens': 200,
        'cache_creation_input_tokens': 100
    }

    with patch('analytics.usage_tracker.get_model_pricing', mock_pricing):
        await tracker._track_assistant_message(message)

    # Check totals updated
    assert tracker.total_input_tokens == 1000
    assert tracker.total_output_tokens == 500
    assert tracker.total_cost_usd > 0

    # Check message recorded
    conn = storage._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (tracker.conversation_id,))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1


@pytest.mark.asyncio
async def test_usage_tracker_message_deduplication(storage, mock_pricing):
    """Test UsageTracker deduplicates messages by ID."""
    tracker = UsageTracker(
        spec_id="001-test",
        session_num=1,
        phase="coding",
        storage=storage
    )
    await tracker.start_conversation()

    # Create mock message
    message = MagicMock()
    message.id = "msg_001"
    message.model = "claude-sonnet-4-5"
    message.usage = {
        'input_tokens': 1000,
        'output_tokens': 500,
        'cache_read_input_tokens': 0,
        'cache_creation_input_tokens': 0
    }

    with patch('analytics.usage_tracker.get_model_pricing', mock_pricing):
        # Track same message twice
        await tracker._track_assistant_message(message)
        await tracker._track_assistant_message(message)

    # Totals should only count once
    assert tracker.total_input_tokens == 1000
    assert tracker.total_output_tokens == 500


@pytest.mark.asyncio
async def test_usage_tracker_cost_calculation(storage, mock_pricing):
    """Test cost calculation with cache tokens."""
    tracker = UsageTracker(
        spec_id="001-test",
        session_num=1,
        phase="coding",
        storage=storage
    )

    with patch('analytics.usage_tracker.get_model_pricing', mock_pricing):
        cost = await tracker._calculate_cost(
            model="claude-sonnet-4-5",
            input_tokens=1_000_000,  # 1M tokens
            output_tokens=1_000_000,  # 1M tokens
            cache_read_tokens=1_000_000,  # 1M tokens
            cache_creation_tokens=1_000_000  # 1M tokens
        )

    # Expected: (1M * 3.0) + (1M * 15.0) + (1M * 0.3) + (1M * 3.75)
    expected = 3.0 + 15.0 + 0.3 + 3.75
    assert abs(cost - expected) < 0.01


@pytest.mark.asyncio
async def test_usage_tracker_finalize(storage, temp_db, mock_pricing, monkeypatch):
    """Test tracker finalization and JSON export."""
    # Change to temp directory for finalize
    import os
    original_cwd = os.getcwd()
    temp_dir = temp_db.parent
    monkeypatch.chdir(temp_dir)

    try:
        tracker = UsageTracker(
            spec_id="001-test",
            session_num=1,
            phase="coding",
            storage=storage
        )
        await tracker.start_conversation()

        # Track a message
        message = MagicMock()
        message.id = "msg_001"
        message.model = "claude-sonnet-4-5"
        message.usage = {
            'input_tokens': 1000,
            'output_tokens': 500,
            'cache_read_input_tokens': 0,
            'cache_creation_input_tokens': 0
        }

        with patch('analytics.usage_tracker.get_model_pricing', mock_pricing):
            await tracker._track_assistant_message(message)

        # Update totals
        await tracker._track_result_message(MagicMock(total_cost_usd=0.025))

        # Finalize
        json_path = Path(".auto-claude/specs/001-test/memory/usage.json")
        await tracker.finalize()

        # Verify JSON was exported
        assert json_path.exists()
    finally:
        monkeypatch.chdir(original_cwd)


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_tracking_enabled_default():
    """Test tracking is enabled by default."""
    with patch.dict('os.environ', {}, clear=True):
        assert is_tracking_enabled() is True


@pytest.mark.asyncio
async def test_tracking_disabled_via_env():
    """Test tracking can be disabled via environment variable."""
    with patch.dict('os.environ', {'DISABLE_TOKEN_TRACKING': 'true'}):
        assert is_tracking_enabled() is False


@pytest.mark.asyncio
async def test_get_analytics_storage_singleton():
    """Test get_analytics_storage returns singleton."""
    storage1 = get_analytics_storage()
    storage2 = get_analytics_storage()
    assert storage1 is storage2


@pytest.mark.asyncio
async def test_usage_tracker_otel_integration(storage, mock_pricing):
    """Test UsageTracker emits OTel metrics."""
    from unittest.mock import MagicMock, patch

    mock_exporter = MagicMock()

    with patch('analytics.usage_tracker.get_model_pricing', mock_pricing):
        with patch('analytics.usage_tracker.get_otel_exporter', return_value=mock_exporter):
            with patch('analytics.usage_tracker.is_otel_enabled', return_value=True):
                tracker = UsageTracker(
                    spec_id="001-test",
                    session_num=1,
                    phase="coding",
                    storage=storage
                )

                await tracker.start_conversation()
                mock_exporter.start_session.assert_called_once()

                message = MagicMock()
                message.id = "msg_otel_test"
                message.model = "claude-sonnet-4-5"
                message.usage = {
                    'input_tokens': 1000,
                    'output_tokens': 500,
                    'cache_read_input_tokens': 0,
                    'cache_creation_input_tokens': 0
                }

                await tracker._track_assistant_message(message)

                assert mock_exporter.record_message.called
                call_kwargs = mock_exporter.record_message.call_args[1]
                assert call_kwargs['spec_id'] == "001-test"
                assert call_kwargs['phase'] == "coding"
                assert call_kwargs['model'] == "claude-sonnet-4-5"
                assert call_kwargs['input_tokens'] == 1000
                assert call_kwargs['output_tokens'] == 500

                await tracker.finalize()
                mock_exporter.record_session.assert_called_once()
                mock_exporter.end_session.assert_called_once()


@pytest.mark.asyncio
async def test_usage_tracker_otel_failure_graceful(storage, mock_pricing):
    """Test UsageTracker continues tracking when OTel export fails."""
    from unittest.mock import MagicMock, patch

    mock_exporter = MagicMock()
    mock_exporter.start_session.side_effect = Exception("OTel unavailable")
    mock_exporter.record_message.side_effect = Exception("OTel unavailable")
    mock_exporter.record_session.side_effect = Exception("OTel unavailable")
    mock_exporter.end_session.side_effect = Exception("OTel unavailable")

    with patch('analytics.usage_tracker.get_model_pricing', mock_pricing):
        with patch('analytics.usage_tracker.get_otel_exporter', return_value=mock_exporter):
            with patch('analytics.usage_tracker.is_otel_enabled', return_value=True):
                tracker = UsageTracker(
                    spec_id="001-test",
                    session_num=1,
                    phase="coding",
                    storage=storage
                )

                await tracker.start_conversation()

                message = MagicMock()
                message.id = "msg_test"
                message.model = "claude-sonnet-4-5"
                message.usage = {
                    'input_tokens': 1000,
                    'output_tokens': 500,
                    'cache_read_input_tokens': 0,
                    'cache_creation_input_tokens': 0
                }

                await tracker._track_assistant_message(message)
                await tracker.finalize()

                assert tracker.total_input_tokens == 1000
                assert tracker.total_output_tokens == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
