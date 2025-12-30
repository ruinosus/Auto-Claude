# apps/backend/analytics/prompt_registry.py
"""
Prompt Registry for Langfuse Integration
=========================================

Provides centralized prompt management with Langfuse, with fallback to local files.

Features:
- Fetch versioned prompts from Langfuse
- Fallback to local prompts/*.md files
- Template compilation with variables
- Caching for performance

Usage:
------
    from analytics.prompt_registry import get_prompt_text, get_agent_prompt

    # Get prompt with automatic fallback
    prompt = get_prompt_text("coder", variables={"project": "my-app"})

    # Get prompt for specific agent type
    prompt = get_agent_prompt("coder", project="my-app")

    # Use cached prompts for performance
    from analytics.prompt_registry import get_cached_prompt
    prompt = get_cached_prompt("coder")

Langfuse Setup:
---------------
1. Create prompts in Langfuse UI with names like "coder-agent", "planner-agent"
2. Use labels: "production", "staging", "development"
3. Prompts support Mustache-style variables: {{variable_name}}

Fallback:
---------
When Langfuse is unavailable, prompts are loaded from:
    apps/backend/prompts/{name}.md
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# Prompt file base path
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _get_client():
    """Get Langfuse client lazily."""
    try:
        from analytics.langfuse_integration import get_langfuse_client
        return get_langfuse_client()
    except ImportError:
        return None


def get_prompt(
    name: str,
    label: str = "production",
    version: Optional[int] = None,
) -> Optional[Any]:
    """
    Get a prompt from Langfuse by name.

    Args:
        name: Prompt name in Langfuse (e.g., "coder-agent")
        label: Label to fetch (e.g., "production", "staging", "development")
        version: Optional specific version number

    Returns:
        Langfuse Prompt object, or None if not found
    """
    client = _get_client()
    if not client:
        logger.debug(f"Langfuse not available, cannot fetch prompt: {name}")
        return None

    try:
        if version:
            prompt = client.get_prompt(name, version=version)
        else:
            prompt = client.get_prompt(name, label=label)

        logger.debug(f"Fetched prompt '{name}' (label={label}) from Langfuse")
        return prompt
    except Exception as e:
        logger.warning(f"Failed to fetch prompt '{name}' from Langfuse: {e}")
        return None


def get_prompt_text(
    name: str,
    label: str = "production",
    fallback_path: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Get prompt text with fallback to local file.

    Args:
        name: Prompt name (e.g., "coder" maps to "coder.md")
        label: Langfuse label
        fallback_path: Path to fallback file (relative to prompts/)
        variables: Variables to compile into the prompt

    Returns:
        Compiled prompt text

    Raises:
        FileNotFoundError: If prompt not found in Langfuse or local files
    """
    # Try Langfuse first
    langfuse_prompt = get_prompt(f"{name}-agent", label=label)

    if langfuse_prompt:
        try:
            if variables:
                return langfuse_prompt.compile(**variables)
            return langfuse_prompt.compile()
        except Exception as e:
            logger.warning(f"Failed to compile Langfuse prompt: {e}")

    # Fallback to local file
    if fallback_path:
        file_path = PROMPTS_DIR / fallback_path
    else:
        file_path = PROMPTS_DIR / f"{name}.md"

    if file_path.exists():
        text = file_path.read_text(encoding="utf-8")
        if variables:
            return compile_prompt_template(text, **variables)
        return text

    raise FileNotFoundError(f"Prompt not found: {name} (tried Langfuse and {file_path})")


def compile_prompt_template(template: str, **variables) -> str:
    """
    Compile a prompt template with Mustache-style variables.

    Supports {{variable_name}} syntax with optional whitespace.

    Args:
        template: Template string
        **variables: Variable values

    Returns:
        Compiled string with variables substituted

    Examples:
        >>> compile_prompt_template("Hello {{name}}!", name="World")
        'Hello World!'

        >>> compile_prompt_template("Hello {{ name }}!", name="World")
        'Hello World!'
    """
    result = template
    for key, value in variables.items():
        # Match {{key}} with optional whitespace: {{ key }}, {{key}}, {{  key  }}
        pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
        result = re.sub(pattern, str(value), result)
    return result


@lru_cache(maxsize=32)
def get_cached_prompt(name: str, label: str = "production") -> Optional[str]:
    """
    Get prompt text with caching.

    Cache invalidates when:
    - Application restarts
    - LRU eviction (32 prompts max)

    For production, prompts are fetched once and cached.

    Args:
        name: Prompt name
        label: Langfuse label

    Returns:
        Prompt text, or None if not found
    """
    try:
        return get_prompt_text(name, label=label)
    except FileNotFoundError:
        return None


def clear_prompt_cache():
    """Clear the prompt cache."""
    get_cached_prompt.cache_clear()
    logger.info("Prompt cache cleared")


# Mapping of agent types to prompt names
AGENT_PROMPT_MAPPING = {
    "planner": "planner",
    "coder": "coder",
    "qa_reviewer": "qa_reviewer",
    "qa_fixer": "qa_fixer",
    "spec_gatherer": "spec_gatherer",
    "spec_writer": "spec_writer",
    "spec_critic": "spec_critic",
    "spec_researcher": "spec_researcher",
    "insight_extractor": "insight_extractor",
    "coder_recovery": "coder_recovery",
    "complexity_assessor": "complexity_assessor",
    "validation_fixer": "validation_fixer",
}


def get_agent_prompt(
    agent_type: str,
    label: str = "production",
    **variables,
) -> str:
    """
    Get prompt for a specific agent type.

    Args:
        agent_type: Agent type (e.g., "coder", "planner")
        label: Langfuse label
        **variables: Template variables

    Returns:
        Compiled prompt text

    Raises:
        FileNotFoundError: If prompt not found
    """
    prompt_name = AGENT_PROMPT_MAPPING.get(agent_type, agent_type)
    return get_prompt_text(prompt_name, label=label, variables=variables if variables else None)


def list_available_prompts() -> Dict[str, bool]:
    """
    List all available prompts and their availability status.

    Returns:
        Dict mapping prompt names to availability (True if file exists)
    """
    available = {}
    for agent_type, prompt_name in AGENT_PROMPT_MAPPING.items():
        file_path = PROMPTS_DIR / f"{prompt_name}.md"
        available[agent_type] = file_path.exists()
    return available


def get_prompt_version_info(name: str, label: str = "production") -> Optional[Dict[str, Any]]:
    """
    Get version information for a Langfuse prompt.

    Args:
        name: Prompt name
        label: Langfuse label

    Returns:
        Dict with version info, or None if not available
    """
    prompt = get_prompt(f"{name}-agent", label=label)
    if prompt:
        try:
            return {
                "name": name,
                "version": getattr(prompt, "version", None),
                "label": label,
                "source": "langfuse",
            }
        except Exception:
            pass

    # Check local file
    file_path = PROMPTS_DIR / f"{name}.md"
    if file_path.exists():
        return {
            "name": name,
            "version": None,
            "label": None,
            "source": "local",
            "path": str(file_path),
        }

    return None
