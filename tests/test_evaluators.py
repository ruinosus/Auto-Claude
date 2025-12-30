# tests/test_evaluators.py
import pytest
from unittest.mock import MagicMock, patch


def test_evaluator_config_creation():
    """Test creating an evaluator configuration."""
    from analytics.evaluators import EvaluatorConfig, create_evaluator_config

    config = create_evaluator_config(
        name="code_quality_judge",
        model="claude-haiku-4-5",
        criteria=[
            "Does the code follow project conventions?",
            "Are there adequate tests?",
            "Is the implementation secure?",
        ],
        output_type="numeric",
        scale_min=1,
        scale_max=10,
    )

    assert config.name == "code_quality_judge"
    assert config.model == "claude-haiku-4-5"
    assert len(config.criteria) == 3
    assert config.output_type == "numeric"


def test_evaluator_registry():
    """Test registering and retrieving evaluators."""
    from analytics.evaluators import register_evaluator, get_evaluator, clear_evaluators

    clear_evaluators()

    config = {
        "name": "test_evaluator",
        "model": "claude-haiku-4-5",
        "criteria": ["Is this good?"],
    }

    register_evaluator("test_evaluator", config)
    retrieved = get_evaluator("test_evaluator")

    assert retrieved is not None
    assert retrieved["name"] == "test_evaluator"


def test_default_evaluators():
    """Test that default evaluators are defined."""
    from analytics.evaluators import DEFAULT_EVALUATORS

    assert "code_quality" in DEFAULT_EVALUATORS
    assert "spec_completeness" in DEFAULT_EVALUATORS
    assert "security_review" in DEFAULT_EVALUATORS


def test_run_evaluation_stub():
    """Test that run_evaluation returns placeholder when not connected."""
    from analytics.evaluators import run_evaluation

    result = run_evaluation(
        evaluator_name="code_quality",
        trace_id="test-trace-123",
        content="def hello(): pass",
    )

    # Should return a placeholder result since Langfuse is not connected
    assert "score" in result or "error" in result
