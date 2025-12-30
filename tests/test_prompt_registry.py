# tests/test_prompt_registry.py
"""
Tests for the Langfuse Prompt Registry module.

Tests prompt management with Langfuse integration and fallback to local files.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


def test_compile_prompt_template():
    """Test compiling prompt with Mustache-style variables."""
    from analytics.prompt_registry import compile_prompt_template

    template = "Build feature {{feature_name}} in {{project}}"
    result = compile_prompt_template(
        template,
        feature_name="dark mode",
        project="auto-claude"
    )

    assert result == "Build feature dark mode in auto-claude"


def test_compile_prompt_template_multiple_same_var():
    """Test template with same variable used multiple times."""
    from analytics.prompt_registry import compile_prompt_template

    template = "Hello {{name}}, welcome {{name}}!"
    result = compile_prompt_template(template, name="Alice")

    assert result == "Hello Alice, welcome Alice!"


def test_compile_prompt_template_with_whitespace():
    """Test template with whitespace inside variable braces."""
    from analytics.prompt_registry import compile_prompt_template

    template = "Hello {{ name }}, welcome {{  project  }}!"
    result = compile_prompt_template(template, name="Bob", project="TestProject")

    assert result == "Hello Bob, welcome TestProject!"


def test_compile_prompt_template_no_variables():
    """Test template with no variables returns unchanged."""
    from analytics.prompt_registry import compile_prompt_template

    template = "This is a plain template with no variables."
    result = compile_prompt_template(template)

    assert result == template


def test_compile_prompt_template_unused_variables():
    """Test that unused variables are ignored."""
    from analytics.prompt_registry import compile_prompt_template

    template = "Hello {{name}}!"
    result = compile_prompt_template(template, name="Alice", unused="ignored")

    assert result == "Hello Alice!"


def test_get_prompt_from_langfuse():
    """Test fetching prompt from Langfuse."""
    mock_prompt = MagicMock()
    mock_prompt.compile.return_value = "Compiled prompt content"

    with patch('analytics.prompt_registry._get_client') as mock_get_client:
        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt
        mock_get_client.return_value = mock_client

        from analytics.prompt_registry import get_prompt

        result = get_prompt("coder-agent", label="production")

        mock_client.get_prompt.assert_called_once()
        assert result == mock_prompt


def test_get_prompt_with_version():
    """Test fetching prompt with specific version."""
    mock_prompt = MagicMock()

    with patch('analytics.prompt_registry._get_client') as mock_get_client:
        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt
        mock_get_client.return_value = mock_client

        from analytics.prompt_registry import get_prompt

        result = get_prompt("coder-agent", version=5)

        mock_client.get_prompt.assert_called_once_with("coder-agent", version=5)
        assert result == mock_prompt


def test_get_prompt_returns_none_when_no_client():
    """Test that get_prompt returns None when Langfuse client unavailable."""
    with patch('analytics.prompt_registry._get_client', return_value=None):
        from analytics.prompt_registry import get_prompt

        result = get_prompt("coder-agent")

        assert result is None


def test_get_prompt_text_fallback_to_file(tmp_path):
    """Test fallback to local file when Langfuse unavailable."""
    # Create a temp prompts directory with a test prompt
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "test.md").write_text("This is a test prompt")

    with patch('analytics.prompt_registry._get_client', return_value=None):
        with patch('analytics.prompt_registry.PROMPTS_DIR', prompts_dir):
            from analytics.prompt_registry import get_prompt_text

            result = get_prompt_text("test")

            assert result == "This is a test prompt"


def test_get_prompt_text_with_variables(tmp_path):
    """Test fallback to local file with variable compilation."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "test.md").write_text("Hello {{name}}, working on {{project}}!")

    with patch('analytics.prompt_registry._get_client', return_value=None):
        with patch('analytics.prompt_registry.PROMPTS_DIR', prompts_dir):
            from analytics.prompt_registry import get_prompt_text

            result = get_prompt_text("test", variables={"name": "Alice", "project": "Demo"})

            assert result == "Hello Alice, working on Demo!"


def test_get_prompt_text_from_langfuse():
    """Test getting prompt text from Langfuse."""
    mock_prompt = MagicMock()
    mock_prompt.compile.return_value = "Langfuse compiled prompt"

    with patch('analytics.prompt_registry._get_client') as mock_get_client:
        mock_client = MagicMock()
        mock_client.get_prompt.return_value = mock_prompt
        mock_get_client.return_value = mock_client

        from analytics.prompt_registry import get_prompt_text

        result = get_prompt_text("test")

        assert result == "Langfuse compiled prompt"


def test_get_prompt_text_file_not_found():
    """Test FileNotFoundError when prompt not found anywhere."""
    with patch('analytics.prompt_registry._get_client', return_value=None):
        with patch('analytics.prompt_registry.PROMPTS_DIR', Path("/nonexistent/path")):
            from analytics.prompt_registry import get_prompt_text

            with pytest.raises(FileNotFoundError):
                get_prompt_text("nonexistent_prompt")


def test_agent_prompt_mapping():
    """Test that agent prompt mapping contains expected agents."""
    from analytics.prompt_registry import AGENT_PROMPT_MAPPING

    expected_agents = ["planner", "coder", "qa_reviewer", "qa_fixer"]
    for agent in expected_agents:
        assert agent in AGENT_PROMPT_MAPPING


def test_agent_prompt_mapping_spec_agents():
    """Test that agent prompt mapping contains spec agents."""
    from analytics.prompt_registry import AGENT_PROMPT_MAPPING

    spec_agents = ["spec_gatherer", "spec_writer", "spec_critic", "spec_researcher"]
    for agent in spec_agents:
        assert agent in AGENT_PROMPT_MAPPING


def test_clear_prompt_cache():
    """Test cache clearing functionality."""
    from analytics.prompt_registry import clear_prompt_cache, get_cached_prompt

    # This should not raise any errors
    clear_prompt_cache()


def test_get_cached_prompt(tmp_path):
    """Test cached prompt retrieval."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "cached.md").write_text("Cached prompt content")

    with patch('analytics.prompt_registry._get_client', return_value=None):
        with patch('analytics.prompt_registry.PROMPTS_DIR', prompts_dir):
            from analytics.prompt_registry import get_cached_prompt, clear_prompt_cache

            # Clear cache first
            clear_prompt_cache()

            result = get_cached_prompt("cached")

            assert result == "Cached prompt content"


def test_get_cached_prompt_returns_none_for_missing():
    """Test cached prompt returns None for missing prompts."""
    with patch('analytics.prompt_registry._get_client', return_value=None):
        with patch('analytics.prompt_registry.PROMPTS_DIR', Path("/nonexistent/path")):
            from analytics.prompt_registry import get_cached_prompt, clear_prompt_cache

            # Clear cache first
            clear_prompt_cache()

            result = get_cached_prompt("nonexistent")

            assert result is None


def test_get_agent_prompt(tmp_path):
    """Test getting prompt for a specific agent type."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "coder.md").write_text("You are a coder agent for {{project}}.")

    with patch('analytics.prompt_registry._get_client', return_value=None):
        with patch('analytics.prompt_registry.PROMPTS_DIR', prompts_dir):
            from analytics.prompt_registry import get_agent_prompt

            result = get_agent_prompt("coder", project="TestProject")

            assert result == "You are a coder agent for TestProject."


def test_get_agent_prompt_unknown_agent(tmp_path):
    """Test getting prompt for unknown agent type falls back to name."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "custom_agent.md").write_text("Custom agent prompt")

    with patch('analytics.prompt_registry._get_client', return_value=None):
        with patch('analytics.prompt_registry.PROMPTS_DIR', prompts_dir):
            from analytics.prompt_registry import get_agent_prompt

            result = get_agent_prompt("custom_agent")

            assert result == "Custom agent prompt"
