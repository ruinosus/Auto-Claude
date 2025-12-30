# tests/test_langfuse_scores.py
"""Tests for Langfuse categorical and boolean score support."""
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the backend directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))


def test_save_categorical_score():
    """Test saving categorical score to Langfuse."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_categorical_score

        result = save_categorical_score(
            trace_id="trace-123",
            name="build_status",
            value="success",
            comment="Build completed successfully"
        )

        assert result is True


def test_save_categorical_score_no_client():
    """Test saving categorical score when client is None."""
    with patch('analytics.langfuse_integration._langfuse_client', None):
        # Need to reimport to get the function with patched global
        import importlib
        import analytics.langfuse_integration as module
        importlib.reload(module)

        result = module.save_categorical_score(
            trace_id="trace-123",
            name="build_status",
            value="success"
        )

        assert result is False


def test_save_boolean_score():
    """Test saving boolean score to Langfuse."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_boolean_score

        result = save_boolean_score(
            trace_id="trace-123",
            name="qa_first_attempt_pass",
            value=True,
            comment="QA passed on first attempt"
        )

        assert result is True


def test_save_boolean_score_false():
    """Test saving boolean score with False value."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_boolean_score

        result = save_boolean_score(
            trace_id="trace-123",
            name="qa_first_attempt_pass",
            value=False,
            comment="QA required multiple attempts"
        )

        assert result is True


def test_save_boolean_score_no_client():
    """Test saving boolean score when client is None."""
    with patch('analytics.langfuse_integration._langfuse_client', None):
        import importlib
        import analytics.langfuse_integration as module
        importlib.reload(module)

        result = module.save_boolean_score(
            trace_id="trace-123",
            name="qa_first_attempt_pass",
            value=True
        )

        assert result is False


def test_save_build_result_success():
    """Test saving build result as categorical score - success."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_build_result

        result = save_build_result("trace-123", "success")

        assert result is True


def test_save_build_result_partial():
    """Test saving build result as categorical score - partial."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_build_result

        result = save_build_result("trace-456", "partial")

        assert result is True


def test_save_build_result_failure():
    """Test saving build result as categorical score - failure."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_build_result

        result = save_build_result("trace-789", "failure")

        assert result is True


def test_save_build_result_invalid():
    """Test saving build result with invalid value."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_build_result

        result = save_build_result("trace-123", "invalid_status")

        assert result is False


def test_save_qa_verdict_approved():
    """Test saving QA verdict as categorical score - approved."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_qa_verdict

        result = save_qa_verdict("trace-123", "approved")

        assert result is True


def test_save_qa_verdict_rejected():
    """Test saving QA verdict as categorical score - rejected."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_qa_verdict

        result = save_qa_verdict("trace-456", "rejected")

        assert result is True


def test_save_qa_verdict_error():
    """Test saving QA verdict as categorical score - error."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_qa_verdict

        result = save_qa_verdict("trace-789", "error")

        assert result is True


def test_save_qa_verdict_invalid():
    """Test saving QA verdict with invalid value."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_qa_verdict

        result = save_qa_verdict("trace-123", "invalid_verdict")

        assert result is False


def test_save_qa_first_attempt_passed():
    """Test saving QA first attempt status - passed."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_qa_first_attempt

        result = save_qa_first_attempt("trace-123", True)

        assert result is True


def test_save_qa_first_attempt_failed():
    """Test saving QA first attempt status - failed (required multiple attempts)."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_qa_first_attempt

        result = save_qa_first_attempt("trace-456", False)

        assert result is True
