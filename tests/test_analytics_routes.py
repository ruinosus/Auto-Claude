"""
Tests for Analytics API Routes helper functions.

Tests the intelligent fallback logic for extracting spec_id and agent_type
from traces when metadata is missing or incomplete.
"""

import pytest
from unittest.mock import MagicMock


class TestGetSpecIdFromTrace:
    """Tests for get_spec_id_from_trace helper function."""

    def test_spec_id_from_metadata(self):
        """Test that spec_id is extracted from metadata when present."""
        from analytics.api.routes import get_spec_id_from_trace

        trace = MagicMock()
        trace.metadata = {"spec_id": "spec-123"}
        trace.session_id = "session-456"
        trace.name = "coder-spec-045"
        trace.id = "abc12345-xyz"

        result = get_spec_id_from_trace(trace)
        assert result == "spec-123"

    def test_spec_id_fallback_to_session_id(self):
        """Test that spec_id uses session_id when metadata is empty."""
        from analytics.api.routes import get_spec_id_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.session_id = "session-123"
        trace.name = "coder-spec-045"
        trace.id = "abc12345-xyz"

        result = get_spec_id_from_trace(trace)
        assert result != "unknown"
        assert result == "session-123"

    def test_spec_id_uses_name_prefix_when_no_session(self):
        """Test spec_id falls back to name prefix when no session_id."""
        from analytics.api.routes import get_spec_id_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.session_id = None
        trace.name = "coder-spec-045-implementation"
        trace.id = "abc12345-xyz"

        result = get_spec_id_from_trace(trace)
        assert result == "coder"

    def test_spec_id_uses_trace_id_as_last_resort(self):
        """Test spec_id falls back to trace_id[:8] when nothing else available."""
        from analytics.api.routes import get_spec_id_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.session_id = None
        trace.name = ""
        trace.id = "abc12345-xyz"

        result = get_spec_id_from_trace(trace)
        assert result == "trace-abc12345"

    def test_spec_id_with_none_metadata(self):
        """Test spec_id handles None metadata gracefully."""
        from analytics.api.routes import get_spec_id_from_trace

        trace = MagicMock()
        trace.metadata = None
        trace.session_id = "session-999"
        trace.name = "test-trace"
        trace.id = "xyz12345"

        result = get_spec_id_from_trace(trace)
        assert result == "session-999"

    def test_spec_id_with_name_without_hyphen(self):
        """Test spec_id uses trace ID when name has no hyphen."""
        from analytics.api.routes import get_spec_id_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.session_id = None
        trace.name = "simple_name"
        trace.id = "qwerty12345"

        result = get_spec_id_from_trace(trace)
        assert result == "trace-qwerty12"


class TestGetAgentTypeFromTrace:
    """Tests for get_agent_type_from_trace helper function."""

    def test_agent_type_from_metadata(self):
        """Test agent_type extraction from metadata."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = {"agent_type": "coder"}
        trace.name = "some-trace"

        result = get_agent_type_from_trace(trace)
        assert result == "coder"

    def test_agent_type_inferred_from_name_planner(self):
        """Test agent_type inferred from trace name containing 'planner'."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.name = "planner-session-123"

        result = get_agent_type_from_trace(trace)
        assert result == "planner"

    def test_agent_type_inferred_from_name_coder(self):
        """Test agent_type inferred from trace name containing 'coder'."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.name = "coder-spec-045"

        result = get_agent_type_from_trace(trace)
        assert result == "coder"

    def test_agent_type_inferred_from_name_qa_reviewer(self):
        """Test agent_type inferred from trace name containing 'qa_reviewer'."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.name = "qa_reviewer-session-123"

        result = get_agent_type_from_trace(trace)
        assert result == "qa_reviewer"

    def test_agent_type_inferred_from_name_qa_fixer(self):
        """Test agent_type inferred from trace name containing 'qa_fixer'."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.name = "qa_fixer-attempt-2"

        result = get_agent_type_from_trace(trace)
        assert result == "qa_fixer"

    def test_agent_type_inferred_from_name_gatherer(self):
        """Test agent_type inferred from trace name containing 'gatherer'."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.name = "spec-gatherer-session"

        result = get_agent_type_from_trace(trace)
        assert result == "gatherer"

    def test_agent_type_inferred_from_name_researcher(self):
        """Test agent_type inferred from trace name containing 'researcher'."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.name = "researcher-deep-analysis"

        result = get_agent_type_from_trace(trace)
        assert result == "researcher"

    def test_agent_type_inferred_from_name_writer(self):
        """Test agent_type inferred from trace name containing 'writer'."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.name = "spec-writer-final"

        result = get_agent_type_from_trace(trace)
        assert result == "writer"

    def test_agent_type_fallback_to_other(self):
        """Test agent_type falls back to 'other' when no match."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.name = "random-trace-name"

        result = get_agent_type_from_trace(trace)
        assert result == "other"

    def test_agent_type_with_none_metadata(self):
        """Test agent_type handles None metadata gracefully."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = None
        trace.name = "coder-session"

        result = get_agent_type_from_trace(trace)
        assert result == "coder"

    def test_agent_type_with_none_name(self):
        """Test agent_type handles None name gracefully."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.name = None

        result = get_agent_type_from_trace(trace)
        assert result == "other"

    def test_agent_type_case_insensitive(self):
        """Test agent_type matching is case insensitive."""
        from analytics.api.routes import get_agent_type_from_trace

        trace = MagicMock()
        trace.metadata = {}
        trace.name = "PLANNER-Session-123"

        result = get_agent_type_from_trace(trace)
        assert result == "planner"


class TestNoUnknownFallback:
    """Tests to ensure 'unknown' is never returned."""

    def test_spec_id_never_returns_unknown(self):
        """Verify spec_id never returns 'unknown' regardless of input."""
        from analytics.api.routes import get_spec_id_from_trace

        # Worst case scenario - everything is empty/None
        trace = MagicMock()
        trace.metadata = None
        trace.session_id = None
        trace.name = None
        trace.id = "abc12345"

        result = get_spec_id_from_trace(trace)
        assert result != "unknown"
        assert "trace-" in result

    def test_agent_type_never_returns_unknown(self):
        """Verify agent_type never returns 'unknown' regardless of input."""
        from analytics.api.routes import get_agent_type_from_trace

        # Worst case scenario - everything is empty/None
        trace = MagicMock()
        trace.metadata = None
        trace.name = None

        result = get_agent_type_from_trace(trace)
        assert result != "unknown"
        assert result == "other"
