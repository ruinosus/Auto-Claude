# Langfuse Full Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement all 12 underutilized Langfuse features to achieve 100% platform utilization.

**Architecture:** Six parallel workstreams organized by dependency. Backend workstreams (A, B, C, E, F) can run concurrently. Frontend workstream (D) has no backend dependencies. Each workstream produces isolated, testable modules.

**Tech Stack:** Python 3.12+, langfuse>=3.0.0, TypeScript/React, Electron

**Parallelism Strategy:**
```
Workstream A ─────────────────────────────────────► (Scores + Metadata + Sampling)
Workstream B ─────────────────────────────────────► (Prompt Management)
Workstream C ─────────────────────────────────────► (Metrics + Observations API)
Workstream D ─────────────────────────────────────► (Frontend User Feedback)
Workstream E ──────────► depends on A completion ─► (LLM-as-a-Judge)
Workstream F ──────────► depends on B completion ─► (Datasets & Experiments)
```

---

## Workstream A: Categorical/Boolean Scores + Metadata Propagation + Trace Sampling

**Can run in parallel with:** B, C, D

---

### Task A1: Add Categorical and Boolean Score Support

**Files:**
- Modify: `apps/backend/analytics/langfuse_integration.py`
- Create: `tests/test_langfuse_scores.py`

**Step 1: Write the failing test**

```python
# tests/test_langfuse_scores.py
import pytest
from unittest.mock import MagicMock, patch

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
        mock_client.score.assert_called_once_with(
            trace_id="trace-123",
            name="build_status",
            value="success",
            data_type="CATEGORICAL",
            comment="Build completed successfully"
        )


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
        mock_client.score.assert_called_once_with(
            trace_id="trace-123",
            name="qa_first_attempt_pass",
            value=True,
            data_type="BOOLEAN",
            comment="QA passed on first attempt"
        )


def test_save_build_result_score():
    """Test saving build result as categorical score."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        mock_client.score = MagicMock()

        from analytics.langfuse_integration import save_build_result

        # Test success
        save_build_result("trace-123", "success")

        # Test partial
        save_build_result("trace-456", "partial")

        # Test failure
        save_build_result("trace-789", "failure")

        assert mock_client.score.call_count == 3
```

**Step 2: Run test to verify it fails**

Run: `apps/backend/.venv/bin/pytest tests/test_langfuse_scores.py -v`
Expected: FAIL with "ImportError: cannot import name 'save_categorical_score'"

**Step 3: Implement categorical and boolean score functions**

Add to `apps/backend/analytics/langfuse_integration.py`:

```python
# =============================================================================
# Categorical and Boolean Scores
# =============================================================================

def save_categorical_score(
    trace_id: str,
    name: str,
    value: str,
    comment: Optional[str] = None
) -> bool:
    """
    Save a categorical score to a Langfuse trace.

    Args:
        trace_id: The Langfuse trace ID
        name: Score name (e.g., "build_status", "qa_verdict")
        value: Categorical value (e.g., "success", "partial", "failure")
        comment: Optional comment

    Returns:
        True if score was saved successfully
    """
    if not _langfuse_client:
        return False

    try:
        _langfuse_client.score(
            trace_id=trace_id,
            name=name,
            value=value,
            data_type="CATEGORICAL",
            comment=comment
        )
        logger.debug(f"Saved categorical score {name}={value} to trace {trace_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to save categorical score {name}: {e}")
        return False


def save_boolean_score(
    trace_id: str,
    name: str,
    value: bool,
    comment: Optional[str] = None
) -> bool:
    """
    Save a boolean score to a Langfuse trace.

    Args:
        trace_id: The Langfuse trace ID
        name: Score name (e.g., "qa_first_attempt_pass")
        value: Boolean value (True/False)
        comment: Optional comment

    Returns:
        True if score was saved successfully
    """
    if not _langfuse_client:
        return False

    try:
        _langfuse_client.score(
            trace_id=trace_id,
            name=name,
            value=value,
            data_type="BOOLEAN",
            comment=comment
        )
        logger.debug(f"Saved boolean score {name}={value} to trace {trace_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to save boolean score {name}: {e}")
        return False


# Convenience functions for common scores
def save_build_result(trace_id: str, result: str, comment: Optional[str] = None) -> bool:
    """Save build result as categorical score. Values: success, partial, failure"""
    valid_values = ["success", "partial", "failure"]
    if result not in valid_values:
        logger.warning(f"Invalid build result: {result}. Must be one of {valid_values}")
        return False
    return save_categorical_score(trace_id, "build_result", result, comment)


def save_qa_verdict(trace_id: str, verdict: str, comment: Optional[str] = None) -> bool:
    """Save QA verdict as categorical score. Values: approved, rejected, error"""
    valid_values = ["approved", "rejected", "error"]
    if verdict not in valid_values:
        logger.warning(f"Invalid QA verdict: {verdict}. Must be one of {valid_values}")
        return False
    return save_categorical_score(trace_id, "qa_verdict", verdict, comment)


def save_qa_first_attempt(trace_id: str, passed: bool) -> bool:
    """Save whether QA passed on first attempt as boolean score."""
    return save_boolean_score(
        trace_id,
        "qa_first_attempt_pass",
        passed,
        "QA passed on first attempt" if passed else "QA required multiple attempts"
    )
```

**Step 4: Run test to verify it passes**

Run: `apps/backend/.venv/bin/pytest tests/test_langfuse_scores.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/backend/analytics/langfuse_integration.py tests/test_langfuse_scores.py
git commit -m "feat(langfuse): add categorical and boolean score support"
```

---

### Task A2: Implement Metadata Propagation

**Files:**
- Modify: `apps/backend/analytics/langfuse_integration.py`
- Add to: `tests/test_langfuse_scores.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_langfuse_scores.py

def test_propagate_attributes_context():
    """Test metadata propagation context manager."""
    with patch('analytics.langfuse_integration._langfuse_client') as mock_client:
        from analytics.langfuse_integration import propagate_attributes, trace_context

        with propagate_attributes(
            metadata={"spec_id": "001", "project": "test-project"},
            tags=["kanban", "production"]
        ):
            # Create a trace inside - should inherit attributes
            with trace_context(name="test-trace") as ctx:
                assert ctx is not None
                # Metadata should be propagated
```

**Step 2: Run test to verify it fails**

Run: `apps/backend/.venv/bin/pytest tests/test_langfuse_scores.py::test_propagate_attributes_context -v`
Expected: FAIL with "ImportError: cannot import name 'propagate_attributes'"

**Step 3: Implement propagate_attributes**

Add to `apps/backend/analytics/langfuse_integration.py`:

```python
# =============================================================================
# Metadata Propagation
# =============================================================================

# Thread-local storage for propagated attributes
import threading
_propagated_context = threading.local()


def _get_propagated_metadata() -> Dict:
    """Get currently propagated metadata."""
    return getattr(_propagated_context, 'metadata', {})


def _get_propagated_tags() -> List[str]:
    """Get currently propagated tags."""
    return getattr(_propagated_context, 'tags', [])


@contextmanager
def propagate_attributes(
    metadata: Optional[Dict] = None,
    tags: Optional[List[str]] = None,
):
    """
    Context manager for propagating metadata and tags to all nested traces.

    Usage:
        with propagate_attributes(
            metadata={"spec_id": "001", "project": "my-project"},
            tags=["kanban", "production"],
        ):
            # All traces created here inherit these attributes
            await run_coder_session()
            await run_qa_session()

    Args:
        metadata: Metadata dict to propagate
        tags: Tags list to propagate
    """
    # Save previous context
    prev_metadata = getattr(_propagated_context, 'metadata', {})
    prev_tags = getattr(_propagated_context, 'tags', [])

    try:
        # Merge with new context
        _propagated_context.metadata = {**prev_metadata, **(metadata or {})}
        _propagated_context.tags = list(set(prev_tags + (tags or [])))

        yield

    finally:
        # Restore previous context
        _propagated_context.metadata = prev_metadata
        _propagated_context.tags = prev_tags
```

**Step 4: Update trace_context to use propagated attributes**

Modify the `trace_context` function to merge propagated attributes:

```python
# In trace_context(), after building trace_metadata, add:
            # Merge with propagated context
            propagated_meta = _get_propagated_metadata()
            trace_metadata = {**propagated_meta, **trace_metadata}

            propagated_tags = _get_propagated_tags()
            if tags:
                all_tags = list(set(propagated_tags + list(tags)))
            else:
                all_tags = propagated_tags
```

**Step 5: Run test to verify it passes**

Run: `apps/backend/.venv/bin/pytest tests/test_langfuse_scores.py::test_propagate_attributes_context -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/backend/analytics/langfuse_integration.py tests/test_langfuse_scores.py
git commit -m "feat(langfuse): add metadata propagation context manager"
```

---

### Task A3: Implement Trace Sampling

**Files:**
- Modify: `apps/backend/analytics/langfuse_integration.py`
- Add to: `tests/test_langfuse_scores.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_langfuse_scores.py

def test_trace_sampling_rate():
    """Test trace sampling configuration."""
    from analytics.langfuse_integration import configure_sampling, get_sample_rate

    # Default should be 1.0 (100%)
    assert get_sample_rate() == 1.0

    # Configure to 10%
    configure_sampling(0.1)
    assert get_sample_rate() == 0.1

    # Reset to 100%
    configure_sampling(1.0)
    assert get_sample_rate() == 1.0


def test_trace_sampling_skips_traces():
    """Test that sampling actually skips traces."""
    from analytics.langfuse_integration import configure_sampling, should_sample_trace

    # At 0% sampling, all traces should be skipped
    configure_sampling(0.0)

    results = [should_sample_trace() for _ in range(100)]
    assert all(r is False for r in results)

    # At 100% sampling, all traces should be included
    configure_sampling(1.0)

    results = [should_sample_trace() for _ in range(100)]
    assert all(r is True for r in results)
```

**Step 2: Run test to verify it fails**

Run: `apps/backend/.venv/bin/pytest tests/test_langfuse_scores.py::test_trace_sampling_rate -v`
Expected: FAIL with "ImportError: cannot import name 'configure_sampling'"

**Step 3: Implement trace sampling**

Add to `apps/backend/analytics/langfuse_integration.py`:

```python
# =============================================================================
# Trace Sampling
# =============================================================================

import random

_sample_rate: float = 1.0  # Default: sample 100%


def configure_sampling(rate: float) -> None:
    """
    Configure the trace sampling rate.

    Args:
        rate: Float between 0.0 (sample 0%) and 1.0 (sample 100%)
    """
    global _sample_rate
    if not 0.0 <= rate <= 1.0:
        raise ValueError(f"Sample rate must be between 0.0 and 1.0, got {rate}")
    _sample_rate = rate
    logger.info(f"Trace sampling rate configured to {rate * 100:.0f}%")


def get_sample_rate() -> float:
    """Get the current trace sampling rate."""
    return _sample_rate


def should_sample_trace() -> bool:
    """
    Determine if the current trace should be sampled.

    Returns:
        True if trace should be recorded, False if it should be skipped
    """
    if _sample_rate >= 1.0:
        return True
    if _sample_rate <= 0.0:
        return False
    return random.random() < _sample_rate


def get_sampling_from_env() -> float:
    """
    Get sampling rate from environment variable.

    Environment variable: LANGFUSE_SAMPLE_RATE (default: 1.0)
    """
    rate_str = os.environ.get("LANGFUSE_SAMPLE_RATE", "1.0")
    try:
        rate = float(rate_str)
        return max(0.0, min(1.0, rate))
    except ValueError:
        logger.warning(f"Invalid LANGFUSE_SAMPLE_RATE: {rate_str}, using 1.0")
        return 1.0
```

**Step 4: Update init_langfuse to apply sampling from env**

```python
# In init_langfuse(), after successful initialization:
        # Apply sampling rate from environment
        env_rate = get_sampling_from_env()
        if env_rate < 1.0:
            configure_sampling(env_rate)
```

**Step 5: Update trace_context to check sampling**

```python
# At the start of trace_context():
    # Check sampling
    if not should_sample_trace():
        logger.debug(f"Trace '{name}' skipped due to sampling (rate: {_sample_rate})")
        yield None
        return
```

**Step 6: Run tests to verify they pass**

Run: `apps/backend/.venv/bin/pytest tests/test_langfuse_scores.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add apps/backend/analytics/langfuse_integration.py tests/test_langfuse_scores.py
git commit -m "feat(langfuse): add trace sampling support with env configuration"
```

---

### Task A4: Integrate New Scores into QA Flow

**Files:**
- Modify: `apps/backend/qa/loop.py`

**Step 1: Read current implementation**

Read `apps/backend/qa/loop.py` to understand current QA flow.

**Step 2: Add categorical scores at QA completion**

At the end of the QA loop when status is determined:

```python
# Import at top
from analytics.langfuse_integration import (
    save_build_result,
    save_qa_verdict,
    save_qa_first_attempt,
    is_langfuse_ready,
)

# After QA loop completes:
if is_langfuse_ready() and final_trace_id:
    # Save build result
    if qa_passed:
        save_build_result(final_trace_id, "success")
    elif qa_iterations > 0:
        save_build_result(final_trace_id, "partial")
    else:
        save_build_result(final_trace_id, "failure")

    # Save QA verdict
    if qa_status == "approved":
        save_qa_verdict(final_trace_id, "approved")
    elif qa_status == "rejected":
        save_qa_verdict(final_trace_id, "rejected")
    else:
        save_qa_verdict(final_trace_id, "error")

    # Save first attempt pass
    save_qa_first_attempt(final_trace_id, qa_iterations == 1 and qa_passed)
```

**Step 3: Run existing tests**

Run: `apps/backend/.venv/bin/pytest tests/ -k qa -v`
Expected: PASS

**Step 4: Commit**

```bash
git add apps/backend/qa/loop.py
git commit -m "feat(langfuse): add categorical/boolean scores to QA flow"
```

---

## Workstream B: Prompt Management Migration

**Can run in parallel with:** A, C, D

---

### Task B1: Create Prompt Registry Module

**Files:**
- Create: `apps/backend/analytics/prompt_registry.py`
- Create: `tests/test_prompt_registry.py`

**Step 1: Write the failing test**

```python
# tests/test_prompt_registry.py
import pytest
from unittest.mock import MagicMock, patch


def test_get_prompt_from_langfuse():
    """Test fetching prompt from Langfuse."""
    mock_prompt = MagicMock()
    mock_prompt.compile.return_value = "Compiled prompt content"

    with patch('analytics.prompt_registry._langfuse_client') as mock_client:
        mock_client.get_prompt.return_value = mock_prompt

        from analytics.prompt_registry import get_prompt

        result = get_prompt("coder-agent", label="production")

        mock_client.get_prompt.assert_called_once_with("coder-agent", label="production")
        assert result == mock_prompt


def test_get_prompt_fallback_to_file():
    """Test fallback to local file when Langfuse unavailable."""
    with patch('analytics.prompt_registry._langfuse_client', None):
        from analytics.prompt_registry import get_prompt_text

        # Should fall back to local file
        result = get_prompt_text("coder", fallback_path="prompts/coder.md")

        assert result is not None
        assert len(result) > 0


def test_compile_prompt_with_variables():
    """Test compiling prompt with template variables."""
    from analytics.prompt_registry import compile_prompt_template

    template = "Build feature {{feature_name}} in {{project}}"
    result = compile_prompt_template(
        template,
        feature_name="dark mode",
        project="auto-claude"
    )

    assert result == "Build feature dark mode in auto-claude"
```

**Step 2: Run test to verify it fails**

Run: `apps/backend/.venv/bin/pytest tests/test_prompt_registry.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'analytics.prompt_registry'"

**Step 3: Implement prompt registry**

```python
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
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# Get Langfuse client
_langfuse_client = None

def _get_client():
    """Get Langfuse client lazily."""
    global _langfuse_client
    if _langfuse_client is None:
        try:
            from analytics.langfuse_integration import get_langfuse_client
            _langfuse_client = get_langfuse_client()
        except ImportError:
            pass
    return _langfuse_client


# Prompt file base path
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


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

    Supports {{variable_name}} syntax.

    Args:
        template: Template string
        **variables: Variable values

    Returns:
        Compiled string
    """
    result = template
    for key, value in variables.items():
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
    """
    return get_prompt_text(name, label=label)


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
    """
    prompt_name = AGENT_PROMPT_MAPPING.get(agent_type, agent_type)
    return get_prompt_text(prompt_name, label=label, variables=variables if variables else None)
```

**Step 4: Run test to verify it passes**

Run: `apps/backend/.venv/bin/pytest tests/test_prompt_registry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/backend/analytics/prompt_registry.py tests/test_prompt_registry.py
git commit -m "feat(langfuse): add prompt registry with Langfuse + fallback support"
```

---

### Task B2: Create Prompt Migration Script

**Files:**
- Create: `apps/backend/scripts/migrate_prompts_to_langfuse.py`

**Step 1: Write migration script**

```python
#!/usr/bin/env python3
"""
Migrate Prompts to Langfuse
===========================

This script uploads all prompts from apps/backend/prompts/*.md to Langfuse
with proper versioning and labels.

Usage:
    python scripts/migrate_prompts_to_langfuse.py [--dry-run] [--label production]
"""

import argparse
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv(backend_path / ".env")


def migrate_prompts(dry_run: bool = False, label: str = "production"):
    """Migrate all prompts to Langfuse."""
    from langfuse import Langfuse

    client = Langfuse()

    if not client.auth_check():
        print("ERROR: Langfuse authentication failed")
        return False

    prompts_dir = backend_path / "prompts"
    migrated = 0
    failed = 0

    for prompt_file in prompts_dir.glob("*.md"):
        prompt_name = f"{prompt_file.stem}-agent"
        content = prompt_file.read_text(encoding="utf-8")

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating: {prompt_file.name} -> {prompt_name}")

        if dry_run:
            print(f"  Content length: {len(content)} chars")
            print(f"  Label: {label}")
            migrated += 1
            continue

        try:
            # Create or update prompt
            client.create_prompt(
                name=prompt_name,
                prompt=content,
                labels=[label],
                type="text",  # or "chat" for chat prompts
            )
            print(f"  SUCCESS: Created/updated {prompt_name}")
            migrated += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migration complete:")
    print(f"  Migrated: {migrated}")
    print(f"  Failed: {failed}")

    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Migrate prompts to Langfuse")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--label", default="production", help="Label for prompts")

    args = parser.parse_args()

    success = migrate_prompts(dry_run=args.dry_run, label=args.label)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

**Step 2: Make executable and test dry-run**

```bash
chmod +x apps/backend/scripts/migrate_prompts_to_langfuse.py
python apps/backend/scripts/migrate_prompts_to_langfuse.py --dry-run
```

**Step 3: Commit**

```bash
git add apps/backend/scripts/migrate_prompts_to_langfuse.py
git commit -m "feat(langfuse): add prompt migration script"
```

---

### Task B3: Update Agents to Use Prompt Registry

**Files:**
- Modify: `apps/backend/agents/coder.py`
- Modify: `apps/backend/agents/planner.py`
- Modify: `apps/backend/qa/reviewer.py`
- Modify: `apps/backend/qa/fixer.py`

**Step 1: Update coder.py**

Replace direct file reading with prompt registry:

```python
# At top of file, add:
from analytics.prompt_registry import get_agent_prompt

# Replace prompt loading:
# OLD: prompt = (PROMPTS_DIR / "coder.md").read_text()
# NEW:
try:
    prompt = get_agent_prompt("coder", label="production", spec_id=spec_id)
except FileNotFoundError:
    # Fallback to direct file read if registry fails
    prompt = (PROMPTS_DIR / "coder.md").read_text()
```

**Step 2: Repeat for planner.py, reviewer.py, fixer.py**

Same pattern for each agent file.

**Step 3: Run tests**

Run: `apps/backend/.venv/bin/pytest tests/ -v`
Expected: PASS

**Step 4: Commit**

```bash
git add apps/backend/agents/*.py apps/backend/qa/*.py
git commit -m "feat(langfuse): update agents to use prompt registry"
```

---

## Workstream C: Daily Metrics API + Observations API

**Can run in parallel with:** A, B, D

---

### Task C1: Create Metrics Client Module

**Files:**
- Create: `apps/backend/analytics/metrics_client.py`
- Create: `tests/test_metrics_client.py`

**Step 1: Write the failing test**

```python
# tests/test_metrics_client.py
import pytest
from datetime import date
from unittest.mock import MagicMock, patch


def test_get_daily_metrics():
    """Test fetching daily metrics from Langfuse."""
    from analytics.metrics_client import get_daily_metrics

    with patch('analytics.metrics_client._get_langfuse_api') as mock_api:
        mock_api.return_value.daily_metrics.list.return_value.data = [
            MagicMock(date="2025-01-01", cost_total=10.5, count_traces=100),
            MagicMock(date="2025-01-02", cost_total=12.3, count_traces=120),
        ]

        result = get_daily_metrics(
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )

        assert len(result) == 2
        assert result[0].cost_total == 10.5


def test_get_project_cost():
    """Test getting total cost for a project."""
    from analytics.metrics_client import get_project_cost

    with patch('analytics.metrics_client.get_daily_metrics') as mock_metrics:
        mock_metrics.return_value = [
            MagicMock(cost_total=10.0),
            MagicMock(cost_total=15.0),
            MagicMock(cost_total=20.0),
        ]

        total = get_project_cost(
            project_id="test-project",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
        )

        assert total == 45.0
```

**Step 2: Run test to verify it fails**

Run: `apps/backend/.venv/bin/pytest tests/test_metrics_client.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement metrics client**

```python
# apps/backend/analytics/metrics_client.py
"""
Langfuse Metrics Client
=======================

Provides access to Langfuse's Daily Metrics API and Observations API
for analytics, billing, and rate-limiting.
"""

import os
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _get_langfuse_api():
    """Get Langfuse API client."""
    try:
        from langfuse import Langfuse
        return Langfuse()
    except Exception as e:
        logger.error(f"Failed to get Langfuse API: {e}")
        return None


@dataclass
class DailyMetric:
    """Daily metric data point."""
    date: str
    cost_total: float
    count_traces: int
    count_observations: int = 0
    usage_input_tokens: int = 0
    usage_output_tokens: int = 0


def get_daily_metrics(
    from_date: date,
    to_date: date,
    user_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> List[DailyMetric]:
    """
    Get daily aggregated metrics from Langfuse.

    Args:
        from_date: Start date
        to_date: End date
        user_id: Filter by user/project ID
        tags: Filter by tags

    Returns:
        List of daily metrics
    """
    api = _get_langfuse_api()
    if not api:
        return []

    try:
        params = {
            "from_timestamp": datetime.combine(from_date, datetime.min.time()).isoformat(),
            "to_timestamp": datetime.combine(to_date, datetime.max.time()).isoformat(),
        }

        if user_id:
            params["user_id"] = user_id
        if tags:
            params["tags"] = tags

        response = api.api.daily_metrics.list(**params)

        return [
            DailyMetric(
                date=m.date,
                cost_total=m.cost_total or 0.0,
                count_traces=m.count_traces or 0,
                count_observations=getattr(m, 'count_observations', 0),
                usage_input_tokens=getattr(m, 'usage_input_tokens', 0),
                usage_output_tokens=getattr(m, 'usage_output_tokens', 0),
            )
            for m in response.data
        ]
    except Exception as e:
        logger.error(f"Failed to get daily metrics: {e}")
        return []


def get_project_cost(
    project_id: str,
    from_date: date,
    to_date: date,
) -> float:
    """
    Get total cost for a project in a date range.

    Args:
        project_id: Project identifier (user_id in Langfuse)
        from_date: Start date
        to_date: End date

    Returns:
        Total cost in USD
    """
    metrics = get_daily_metrics(from_date, to_date, user_id=project_id)
    return sum(m.cost_total for m in metrics)


def get_trace_count(
    project_id: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> int:
    """Get total trace count."""
    if not from_date:
        from_date = date.today()
    if not to_date:
        to_date = date.today()

    metrics = get_daily_metrics(from_date, to_date, user_id=project_id)
    return sum(m.count_traces for m in metrics)


# =============================================================================
# Observations API
# =============================================================================

def get_traces(
    limit: int = 100,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    from_timestamp: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Get traces from Langfuse.

    Args:
        limit: Maximum number of traces to return
        user_id: Filter by user/project ID
        session_id: Filter by session ID
        tags: Filter by tags
        from_timestamp: Only return traces after this time

    Returns:
        List of trace dictionaries
    """
    api = _get_langfuse_api()
    if not api:
        return []

    try:
        params = {"limit": limit}
        if user_id:
            params["user_id"] = user_id
        if session_id:
            params["session_id"] = session_id
        if tags:
            params["tags"] = tags
        if from_timestamp:
            params["from_timestamp"] = from_timestamp.isoformat()

        response = api.api.trace.list(**params)

        return [
            {
                "id": t.id,
                "name": t.name,
                "user_id": t.user_id,
                "session_id": t.session_id,
                "tags": t.tags,
                "metadata": t.metadata,
                "input": t.input,
                "output": t.output,
                "timestamp": t.timestamp,
            }
            for t in response.data
        ]
    except Exception as e:
        logger.error(f"Failed to get traces: {e}")
        return []


def get_observations(
    trace_id: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get observations (spans, generations) for a trace.

    Args:
        trace_id: Trace ID
        limit: Maximum observations to return

    Returns:
        List of observation dictionaries
    """
    api = _get_langfuse_api()
    if not api:
        return []

    try:
        response = api.api.observations.list(trace_id=trace_id, limit=limit)

        return [
            {
                "id": o.id,
                "name": o.name,
                "type": o.type,
                "model": getattr(o, 'model', None),
                "input": o.input,
                "output": o.output,
                "usage": getattr(o, 'usage', None),
                "start_time": o.start_time,
                "end_time": o.end_time,
            }
            for o in response.data
        ]
    except Exception as e:
        logger.error(f"Failed to get observations: {e}")
        return []


def export_traces_for_billing(
    from_date: date,
    to_date: date,
    output_format: str = "dict",
) -> List[Dict[str, Any]]:
    """
    Export traces with cost data for billing.

    Args:
        from_date: Start date
        to_date: End date
        output_format: "dict" or "csv"

    Returns:
        List of trace summaries with costs
    """
    metrics = get_daily_metrics(from_date, to_date)

    summary = []
    for m in metrics:
        summary.append({
            "date": m.date,
            "traces": m.count_traces,
            "input_tokens": m.usage_input_tokens,
            "output_tokens": m.usage_output_tokens,
            "cost_usd": m.cost_total,
        })

    return summary
```

**Step 4: Run test to verify it passes**

Run: `apps/backend/.venv/bin/pytest tests/test_metrics_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/backend/analytics/metrics_client.py tests/test_metrics_client.py
git commit -m "feat(langfuse): add metrics and observations API client"
```

---

### Task C2: Create Cost Dashboard Endpoint

**Files:**
- Modify: `apps/backend/api/analytics_router.py` (create if doesn't exist)

**Step 1: Create analytics router**

```python
# apps/backend/api/analytics_router.py
"""
Analytics API Router
====================

FastAPI router for analytics endpoints.
"""

from datetime import date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Query
from pydantic import BaseModel

from analytics.metrics_client import (
    get_daily_metrics,
    get_project_cost,
    get_trace_count,
    export_traces_for_billing,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


class DailyMetricResponse(BaseModel):
    date: str
    cost_total: float
    count_traces: int
    usage_input_tokens: int
    usage_output_tokens: int


class ProjectCostResponse(BaseModel):
    project_id: str
    from_date: str
    to_date: str
    total_cost_usd: float
    trace_count: int


@router.get("/metrics/daily", response_model=List[DailyMetricResponse])
async def get_daily_metrics_endpoint(
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
):
    """Get daily metrics for the specified date range."""
    if not from_date:
        from_date = date.today() - timedelta(days=30)
    if not to_date:
        to_date = date.today()

    metrics = get_daily_metrics(from_date, to_date, user_id=project_id)

    return [
        DailyMetricResponse(
            date=m.date,
            cost_total=m.cost_total,
            count_traces=m.count_traces,
            usage_input_tokens=m.usage_input_tokens,
            usage_output_tokens=m.usage_output_tokens,
        )
        for m in metrics
    ]


@router.get("/cost/{project_id}", response_model=ProjectCostResponse)
async def get_project_cost_endpoint(
    project_id: str,
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
):
    """Get total cost for a project."""
    if not from_date:
        from_date = date.today() - timedelta(days=30)
    if not to_date:
        to_date = date.today()

    total_cost = get_project_cost(project_id, from_date, to_date)
    trace_count = get_trace_count(project_id, from_date, to_date)

    return ProjectCostResponse(
        project_id=project_id,
        from_date=from_date.isoformat(),
        to_date=to_date.isoformat(),
        total_cost_usd=total_cost,
        trace_count=trace_count,
    )


@router.get("/export/billing")
async def export_billing_data(
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
):
    """Export billing data for the date range."""
    if not from_date:
        from_date = date.today() - timedelta(days=30)
    if not to_date:
        to_date = date.today()

    return export_traces_for_billing(from_date, to_date)
```

**Step 2: Commit**

```bash
git add apps/backend/api/analytics_router.py
git commit -m "feat(langfuse): add analytics API endpoints"
```

---

## Workstream D: Frontend User Feedback (Browser SDK)

**Can run in parallel with:** A, B, C (no backend dependencies)

---

### Task D1: Add Langfuse Package to Frontend

**Files:**
- Modify: `apps/frontend/package.json`

**Step 1: Add langfuse dependency**

```bash
cd apps/frontend
npm install langfuse
```

**Step 2: Commit**

```bash
git add apps/frontend/package.json apps/frontend/package-lock.json
git commit -m "feat(frontend): add langfuse package for user feedback"
```

---

### Task D2: Create Langfuse Web Service

**Files:**
- Create: `apps/frontend/src/renderer/services/langfuse-web.ts`

**Step 1: Create Langfuse web service**

```typescript
// apps/frontend/src/renderer/services/langfuse-web.ts
/**
 * Langfuse Web Service
 *
 * Provides user feedback collection via Langfuse Browser SDK.
 */

import { LangfuseWeb } from 'langfuse';

// Singleton instance
let langfuseWeb: LangfuseWeb | null = null;

export function initLangfuseWeb(publicKey: string, host?: string): LangfuseWeb {
  if (!langfuseWeb) {
    langfuseWeb = new LangfuseWeb({
      publicKey,
      baseUrl: host || 'http://localhost:3001',
    });
  }
  return langfuseWeb;
}

export function getLangfuseWeb(): LangfuseWeb | null {
  return langfuseWeb;
}

export interface UserFeedback {
  traceId: string;
  value: number; // 1 for positive, 0 for negative
  comment?: string;
}

export async function submitUserFeedback(feedback: UserFeedback): Promise<boolean> {
  const client = getLangfuseWeb();
  if (!client) {
    console.warn('[Langfuse] Web client not initialized');
    return false;
  }

  try {
    await client.score({
      traceId: feedback.traceId,
      name: 'user_satisfaction',
      value: feedback.value,
      comment: feedback.comment,
    });
    console.log(`[Langfuse] User feedback submitted for trace ${feedback.traceId}`);
    return true;
  } catch (error) {
    console.error('[Langfuse] Failed to submit feedback:', error);
    return false;
  }
}

export async function submitThumbsUp(traceId: string, comment?: string): Promise<boolean> {
  return submitUserFeedback({ traceId, value: 1, comment: comment || 'User approved' });
}

export async function submitThumbsDown(traceId: string, comment?: string): Promise<boolean> {
  return submitUserFeedback({ traceId, value: 0, comment: comment || 'User rejected' });
}

export async function submitRating(
  traceId: string,
  rating: 1 | 2 | 3 | 4 | 5,
  comment?: string
): Promise<boolean> {
  const client = getLangfuseWeb();
  if (!client) {
    return false;
  }

  try {
    await client.score({
      traceId,
      name: 'user_rating',
      value: rating,
      comment,
    });
    return true;
  } catch (error) {
    console.error('[Langfuse] Failed to submit rating:', error);
    return false;
  }
}
```

**Step 2: Commit**

```bash
git add apps/frontend/src/renderer/services/langfuse-web.ts
git commit -m "feat(frontend): add Langfuse web service for user feedback"
```

---

### Task D3: Create UserFeedback Component

**Files:**
- Create: `apps/frontend/src/renderer/components/UserFeedback.tsx`

**Step 1: Create UserFeedback component**

```typescript
// apps/frontend/src/renderer/components/UserFeedback.tsx
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ThumbsUp, ThumbsDown, Star, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from './ui/popover';
import { cn } from '../lib/utils';
import {
  submitThumbsUp,
  submitThumbsDown,
  submitRating,
} from '../services/langfuse-web';

interface UserFeedbackProps {
  traceId: string;
  onFeedbackSubmitted?: (type: 'positive' | 'negative' | 'rating', value?: number) => void;
  variant?: 'thumbs' | 'stars' | 'both';
  className?: string;
}

export function UserFeedback({
  traceId,
  onFeedbackSubmitted,
  variant = 'thumbs',
  className,
}: UserFeedbackProps) {
  const { t } = useTranslation('common');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<'positive' | 'negative' | null>(null);
  const [showCommentPopover, setShowCommentPopover] = useState(false);
  const [pendingFeedback, setPendingFeedback] = useState<'positive' | 'negative' | null>(null);
  const [comment, setComment] = useState('');
  const [rating, setRating] = useState(0);

  const handleThumbsUp = async () => {
    setPendingFeedback('positive');
    setShowCommentPopover(true);
  };

  const handleThumbsDown = async () => {
    setPendingFeedback('negative');
    setShowCommentPopover(true);
  };

  const submitFeedback = async () => {
    if (!pendingFeedback) return;

    setIsSubmitting(true);
    try {
      const success =
        pendingFeedback === 'positive'
          ? await submitThumbsUp(traceId, comment || undefined)
          : await submitThumbsDown(traceId, comment || undefined);

      if (success) {
        setSubmitted(pendingFeedback);
        onFeedbackSubmitted?.(pendingFeedback);
      }
    } finally {
      setIsSubmitting(false);
      setShowCommentPopover(false);
      setComment('');
    }
  };

  const handleStarRating = async (stars: 1 | 2 | 3 | 4 | 5) => {
    setIsSubmitting(true);
    setRating(stars);
    try {
      const success = await submitRating(traceId, stars);
      if (success) {
        onFeedbackSubmitted?.('rating', stars);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className={cn('flex items-center gap-2 text-muted-foreground', className)}>
        {submitted === 'positive' ? (
          <>
            <ThumbsUp className="h-4 w-4 text-green-500" />
            <span className="text-sm">{t('feedback.thankYou')}</span>
          </>
        ) : (
          <>
            <ThumbsDown className="h-4 w-4 text-red-500" />
            <span className="text-sm">{t('feedback.noted')}</span>
          </>
        )}
      </div>
    );
  }

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {(variant === 'thumbs' || variant === 'both') && (
        <Popover open={showCommentPopover} onOpenChange={setShowCommentPopover}>
          <div className="flex items-center gap-1">
            <PopoverTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleThumbsUp}
                disabled={isSubmitting}
                className="h-8 w-8 p-0"
              >
                <ThumbsUp className="h-4 w-4" />
              </Button>
            </PopoverTrigger>
            <PopoverTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleThumbsDown}
                disabled={isSubmitting}
                className="h-8 w-8 p-0"
              >
                <ThumbsDown className="h-4 w-4" />
              </Button>
            </PopoverTrigger>
          </div>
          <PopoverContent className="w-80">
            <div className="space-y-4">
              <h4 className="font-medium">
                {pendingFeedback === 'positive'
                  ? t('feedback.whatWorked')
                  : t('feedback.whatWentWrong')}
              </h4>
              <Textarea
                placeholder={t('feedback.optionalComment')}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={3}
              />
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowCommentPopover(false)}
                >
                  {t('common.cancel')}
                </Button>
                <Button
                  size="sm"
                  onClick={submitFeedback}
                  disabled={isSubmitting}
                >
                  {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {t('feedback.submit')}
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      )}

      {(variant === 'stars' || variant === 'both') && (
        <div className="flex items-center gap-0.5">
          {[1, 2, 3, 4, 5].map((star) => (
            <Button
              key={star}
              variant="ghost"
              size="sm"
              onClick={() => handleStarRating(star as 1 | 2 | 3 | 4 | 5)}
              disabled={isSubmitting}
              className="h-8 w-8 p-0"
            >
              <Star
                className={cn(
                  'h-4 w-4',
                  star <= rating ? 'fill-yellow-400 text-yellow-400' : 'text-muted-foreground'
                )}
              />
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Add translations**

Add to `apps/frontend/src/shared/i18n/locales/en/common.json`:

```json
{
  "feedback": {
    "thankYou": "Thanks for your feedback!",
    "noted": "We'll work on improving this",
    "whatWorked": "What worked well?",
    "whatWentWrong": "What went wrong?",
    "optionalComment": "Add a comment (optional)",
    "submit": "Submit"
  }
}
```

**Step 3: Commit**

```bash
git add apps/frontend/src/renderer/components/UserFeedback.tsx
git add apps/frontend/src/shared/i18n/locales/en/common.json
git add apps/frontend/src/shared/i18n/locales/fr/common.json
git commit -m "feat(frontend): add UserFeedback component with thumbs/stars"
```

---

### Task D4: Integrate UserFeedback into TaskCard

**Files:**
- Modify: `apps/frontend/src/renderer/components/TaskCard.tsx`

**Step 1: Add UserFeedback to completed tasks**

Add import and component:

```typescript
import { UserFeedback } from './UserFeedback';

// In the component, after task completion:
{task.status === 'completed' && task.langfuseTraceId && (
  <UserFeedback
    traceId={task.langfuseTraceId}
    variant="thumbs"
    className="mt-2"
  />
)}
```

**Step 2: Update Task type to include traceId**

Add to `apps/frontend/src/shared/types.ts`:

```typescript
interface Task {
  // ... existing fields
  langfuseTraceId?: string;
}
```

**Step 3: Commit**

```bash
git add apps/frontend/src/renderer/components/TaskCard.tsx
git add apps/frontend/src/shared/types.ts
git commit -m "feat(frontend): integrate UserFeedback into TaskCard"
```

---

## Workstream E: LLM-as-a-Judge Evaluators

**Depends on:** Workstream A completion (scores infrastructure)

---

### Task E1: Create Evaluator Configuration Module

**Files:**
- Create: `apps/backend/analytics/evaluators.py`
- Create: `tests/test_evaluators.py`

**Step 1: Write the failing test**

```python
# tests/test_evaluators.py
import pytest
from unittest.mock import MagicMock, patch


def test_create_evaluator():
    """Test creating an evaluator config."""
    from analytics.evaluators import create_evaluator_config, EvaluatorType

    config = create_evaluator_config(
        name="code_quality",
        evaluator_type=EvaluatorType.LLM_JUDGE,
        model="claude-haiku-4-5",
        criteria=[
            "Does the code follow project conventions?",
            "Are there adequate tests?",
            "Is the implementation secure?",
        ],
        output_type="numeric",
        score_range=(1, 10),
    )

    assert config.name == "code_quality"
    assert config.model == "claude-haiku-4-5"
    assert len(config.criteria) == 3


def test_run_evaluation():
    """Test running an evaluation on a trace."""
    from analytics.evaluators import run_evaluation

    with patch('analytics.evaluators._get_langfuse_client') as mock_client:
        mock_client.return_value.score = MagicMock()

        result = run_evaluation(
            trace_id="trace-123",
            evaluator_name="code_quality",
            trace_output="def hello(): print('world')",
        )

        assert result is not None
        assert 'score' in result
```

**Step 2: Implement evaluators module**

```python
# apps/backend/analytics/evaluators.py
"""
LLM-as-a-Judge Evaluators
=========================

Automated evaluation of LLM outputs using another LLM as a judge.
"""

import os
import json
import logging
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class EvaluatorType(Enum):
    LLM_JUDGE = "llm_judge"
    KEYWORD = "keyword"
    REGEX = "regex"
    CUSTOM = "custom"


class OutputType(Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


@dataclass
class EvaluatorConfig:
    """Configuration for an evaluator."""
    name: str
    evaluator_type: EvaluatorType
    model: str = "claude-haiku-4-5"
    criteria: List[str] = field(default_factory=list)
    output_type: OutputType = OutputType.NUMERIC
    score_range: Tuple[int, int] = (1, 10)
    categories: List[str] = field(default_factory=list)
    prompt_template: Optional[str] = None
    enabled: bool = True


def create_evaluator_config(
    name: str,
    evaluator_type: EvaluatorType,
    model: str = "claude-haiku-4-5",
    criteria: Optional[List[str]] = None,
    output_type: str = "numeric",
    score_range: Tuple[int, int] = (1, 10),
    categories: Optional[List[str]] = None,
    prompt_template: Optional[str] = None,
) -> EvaluatorConfig:
    """Create an evaluator configuration."""
    return EvaluatorConfig(
        name=name,
        evaluator_type=evaluator_type,
        model=model,
        criteria=criteria or [],
        output_type=OutputType(output_type),
        score_range=score_range,
        categories=categories or [],
        prompt_template=prompt_template,
    )


# Pre-defined evaluators
BUILTIN_EVALUATORS = {
    "code_quality": create_evaluator_config(
        name="code_quality",
        evaluator_type=EvaluatorType.LLM_JUDGE,
        model="claude-haiku-4-5",
        criteria=[
            "Code follows project conventions and style",
            "Proper error handling is implemented",
            "Code is well-documented with comments",
            "No obvious security vulnerabilities",
            "Code is maintainable and readable",
        ],
        output_type="numeric",
        score_range=(1, 10),
    ),
    "spec_completeness": create_evaluator_config(
        name="spec_completeness",
        evaluator_type=EvaluatorType.LLM_JUDGE,
        model="claude-haiku-4-5",
        criteria=[
            "All acceptance criteria are clearly defined",
            "Edge cases are considered",
            "Technical approach is specified",
            "Testing strategy is included",
        ],
        output_type="numeric",
        score_range=(1, 10),
    ),
    "qa_accuracy": create_evaluator_config(
        name="qa_accuracy",
        evaluator_type=EvaluatorType.LLM_JUDGE,
        model="claude-haiku-4-5",
        criteria=[
            "QA correctly identified all issues",
            "No false positives in the review",
            "Suggestions are actionable and clear",
        ],
        output_type="categorical",
        categories=["accurate", "partially_accurate", "inaccurate"],
    ),
}


def _get_langfuse_client():
    """Get Langfuse client."""
    try:
        from analytics.langfuse_integration import get_langfuse_client
        return get_langfuse_client()
    except ImportError:
        return None


def _build_judge_prompt(
    config: EvaluatorConfig,
    trace_input: str,
    trace_output: str,
) -> str:
    """Build the prompt for LLM judge."""
    if config.prompt_template:
        return config.prompt_template.format(
            input=trace_input,
            output=trace_output,
            criteria="\n".join(f"- {c}" for c in config.criteria),
        )

    criteria_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(config.criteria))

    if config.output_type == OutputType.NUMERIC:
        score_instruction = f"Score from {config.score_range[0]} to {config.score_range[1]}"
    elif config.output_type == OutputType.CATEGORICAL:
        score_instruction = f"Choose one: {', '.join(config.categories)}"
    else:
        score_instruction = "Answer: true or false"

    return f"""You are an expert evaluator. Evaluate the following output based on these criteria:

{criteria_text}

INPUT:
{trace_input[:2000]}

OUTPUT:
{trace_output[:2000]}

{score_instruction}

Respond with JSON:
{{
    "score": <your score>,
    "reasoning": "<brief explanation>"
}}
"""


async def run_evaluation(
    trace_id: str,
    evaluator_name: str,
    trace_input: str = "",
    trace_output: str = "",
    save_to_langfuse: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Run an evaluation on a trace.

    Args:
        trace_id: Langfuse trace ID
        evaluator_name: Name of the evaluator to use
        trace_input: Input text to evaluate
        trace_output: Output text to evaluate
        save_to_langfuse: Whether to save the score to Langfuse

    Returns:
        Evaluation result dict with score and reasoning
    """
    config = BUILTIN_EVALUATORS.get(evaluator_name)
    if not config:
        logger.error(f"Unknown evaluator: {evaluator_name}")
        return None

    if not config.enabled:
        logger.debug(f"Evaluator {evaluator_name} is disabled")
        return None

    try:
        from anthropic import Anthropic

        client = Anthropic()
        prompt = _build_judge_prompt(config, trace_input, trace_output)

        response = client.messages.create(
            model=config.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        response_text = response.content[0].text

        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"score": 5, "reasoning": response_text}
        except json.JSONDecodeError:
            result = {"score": 5, "reasoning": response_text}

        # Save to Langfuse
        if save_to_langfuse:
            langfuse = _get_langfuse_client()
            if langfuse:
                from analytics.langfuse_integration import save_score
                save_score(
                    trace_id=trace_id,
                    name=f"eval_{evaluator_name}",
                    value=float(result.get("score", 5)),
                    comment=result.get("reasoning", ""),
                )

        return result

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return None


def register_evaluator(config: EvaluatorConfig) -> None:
    """Register a custom evaluator."""
    BUILTIN_EVALUATORS[config.name] = config
    logger.info(f"Registered evaluator: {config.name}")


def list_evaluators() -> List[str]:
    """List all available evaluators."""
    return list(BUILTIN_EVALUATORS.keys())
```

**Step 3: Run tests**

Run: `apps/backend/.venv/bin/pytest tests/test_evaluators.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add apps/backend/analytics/evaluators.py tests/test_evaluators.py
git commit -m "feat(langfuse): add LLM-as-a-Judge evaluators"
```

---

## Workstream F: Datasets & Experiments

**Depends on:** Workstream B completion (prompt registry)

---

### Task F1: Create Dataset Management Module

**Files:**
- Create: `apps/backend/analytics/datasets.py`
- Create: `tests/test_datasets.py`

**Step 1: Write the failing test**

```python
# tests/test_datasets.py
import pytest
from unittest.mock import MagicMock, patch


def test_create_dataset():
    """Test creating a dataset."""
    from analytics.datasets import create_dataset, DatasetItem

    with patch('analytics.datasets._get_langfuse_client') as mock_client:
        mock_client.return_value.create_dataset.return_value = MagicMock(id="ds-123")

        result = create_dataset(
            name="spec-validation-dataset",
            description="Dataset for validating spec generation",
        )

        assert result is not None
        mock_client.return_value.create_dataset.assert_called_once()


def test_add_dataset_item():
    """Test adding item to dataset."""
    from analytics.datasets import add_dataset_item

    with patch('analytics.datasets._get_langfuse_client') as mock_client:
        result = add_dataset_item(
            dataset_name="spec-validation-dataset",
            input_data={"task": "Add login feature"},
            expected_output={"spec": "..."},
        )

        assert result is True


def test_run_experiment():
    """Test running an experiment on a dataset."""
    from analytics.datasets import run_experiment

    with patch('analytics.datasets._get_langfuse_client') as mock_client:
        result = run_experiment(
            dataset_name="spec-validation-dataset",
            experiment_name="sonnet-vs-opus",
            prompt_name="spec-writer-agent",
            prompt_label="production",
        )

        assert result is not None
```

**Step 2: Implement datasets module**

```python
# apps/backend/analytics/datasets.py
"""
Datasets & Experiments
======================

Manage datasets for prompt testing and run experiments.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DatasetItem:
    """A single item in a dataset."""
    id: Optional[str]
    input_data: Dict[str, Any]
    expected_output: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExperimentResult:
    """Result from running an experiment."""
    experiment_id: str
    dataset_name: str
    prompt_name: str
    run_count: int
    scores: Dict[str, float]
    created_at: datetime


def _get_langfuse_client():
    """Get Langfuse client."""
    try:
        from langfuse import Langfuse
        return Langfuse()
    except Exception as e:
        logger.error(f"Failed to get Langfuse client: {e}")
        return None


def create_dataset(
    name: str,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Create a new dataset in Langfuse.

    Args:
        name: Dataset name
        description: Optional description
        metadata: Optional metadata

    Returns:
        Dataset ID or None if failed
    """
    client = _get_langfuse_client()
    if not client:
        return None

    try:
        dataset = client.create_dataset(
            name=name,
            description=description,
            metadata=metadata,
        )
        logger.info(f"Created dataset: {name} (id: {dataset.id})")
        return dataset.id
    except Exception as e:
        logger.error(f"Failed to create dataset: {e}")
        return None


def add_dataset_item(
    dataset_name: str,
    input_data: Dict[str, Any],
    expected_output: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Add an item to a dataset.

    Args:
        dataset_name: Name of the dataset
        input_data: Input for the test case
        expected_output: Expected output (ground truth)
        metadata: Optional metadata

    Returns:
        True if successful
    """
    client = _get_langfuse_client()
    if not client:
        return False

    try:
        client.create_dataset_item(
            dataset_name=dataset_name,
            input=input_data,
            expected_output=expected_output,
            metadata=metadata,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to add dataset item: {e}")
        return False


def get_dataset_items(
    dataset_name: str,
    limit: int = 100,
) -> List[DatasetItem]:
    """Get items from a dataset."""
    client = _get_langfuse_client()
    if not client:
        return []

    try:
        dataset = client.get_dataset(dataset_name)
        items = []

        for item in dataset.items[:limit]:
            items.append(DatasetItem(
                id=item.id,
                input_data=item.input,
                expected_output=item.expected_output,
                metadata=item.metadata,
            ))

        return items
    except Exception as e:
        logger.error(f"Failed to get dataset items: {e}")
        return []


async def run_experiment(
    dataset_name: str,
    experiment_name: str,
    prompt_name: str,
    prompt_label: str = "production",
    evaluators: Optional[List[str]] = None,
    model: str = "claude-sonnet-4-5-20250929",
) -> Optional[ExperimentResult]:
    """
    Run an experiment on a dataset.

    Args:
        dataset_name: Name of the dataset to use
        experiment_name: Name for this experiment run
        prompt_name: Prompt to test (from Langfuse)
        prompt_label: Label of prompt version
        evaluators: List of evaluator names to run
        model: Model to use

    Returns:
        ExperimentResult or None if failed
    """
    client = _get_langfuse_client()
    if not client:
        return None

    try:
        from analytics.prompt_registry import get_prompt
        from analytics.evaluators import run_evaluation

        # Get dataset items
        items = get_dataset_items(dataset_name)
        if not items:
            logger.error(f"No items in dataset: {dataset_name}")
            return None

        # Get prompt
        prompt = get_prompt(prompt_name, label=prompt_label)

        # Run each item
        scores_sum = {}
        for item in items:
            # Create trace for this run
            trace = client.trace(
                name=f"experiment-{experiment_name}",
                metadata={
                    "experiment": experiment_name,
                    "dataset": dataset_name,
                    "prompt": prompt_name,
                },
            )

            # Compile prompt with input
            if prompt:
                compiled = prompt.compile(**item.input_data)
            else:
                compiled = json.dumps(item.input_data)

            # Generate output (simplified - in reality would call the model)
            # For now, just log the structure
            trace.update(input=compiled)

            # Run evaluators
            if evaluators:
                for eval_name in evaluators:
                    result = await run_evaluation(
                        trace_id=trace.id,
                        evaluator_name=eval_name,
                        trace_input=compiled,
                        trace_output="",  # Would be actual output
                    )
                    if result:
                        if eval_name not in scores_sum:
                            scores_sum[eval_name] = []
                        scores_sum[eval_name].append(result.get("score", 0))

        # Calculate average scores
        avg_scores = {
            name: sum(scores) / len(scores)
            for name, scores in scores_sum.items()
            if scores
        }

        return ExperimentResult(
            experiment_id=f"exp-{experiment_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            dataset_name=dataset_name,
            prompt_name=prompt_name,
            run_count=len(items),
            scores=avg_scores,
            created_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        return None


# =============================================================================
# Pre-built Datasets
# =============================================================================

def create_spec_validation_dataset() -> str:
    """Create a dataset for spec validation testing."""
    dataset_id = create_dataset(
        name="spec-validation-golden",
        description="Golden dataset for spec generation validation",
        metadata={"type": "spec_validation", "version": "1.0"},
    )

    # Add sample items
    sample_items = [
        {
            "input": {"task": "Add user authentication with OAuth2"},
            "expected": {"has_acceptance_criteria": True, "has_tech_approach": True},
        },
        {
            "input": {"task": "Fix bug in payment processing"},
            "expected": {"has_reproduction_steps": True, "has_root_cause": True},
        },
        {
            "input": {"task": "Refactor database layer for performance"},
            "expected": {"has_metrics": True, "has_testing_strategy": True},
        },
    ]

    for item in sample_items:
        add_dataset_item(
            dataset_name="spec-validation-golden",
            input_data=item["input"],
            expected_output=item["expected"],
        )

    return dataset_id


def create_qa_accuracy_dataset() -> str:
    """Create a dataset for QA accuracy testing."""
    dataset_id = create_dataset(
        name="qa-accuracy-golden",
        description="Golden dataset for QA reviewer accuracy testing",
        metadata={"type": "qa_accuracy", "version": "1.0"},
    )

    return dataset_id
```

**Step 3: Run tests**

Run: `apps/backend/.venv/bin/pytest tests/test_datasets.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add apps/backend/analytics/datasets.py tests/test_datasets.py
git commit -m "feat(langfuse): add datasets and experiments support"
```

---

## Final Integration Tasks

---

### Task Z1: Update .env.example with All Langfuse Config

**Files:**
- Modify: `apps/backend/.env.example`

**Step 1: Add complete Langfuse configuration section**

```bash
# =============================================================================
# LANGFUSE CONFIGURATION (Full Feature Set)
# =============================================================================
# Enable Langfuse integration
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:3001

# API Keys (get from Langfuse dashboard)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# Trace Sampling (0.0 to 1.0, default: 1.0 = 100%)
# Reduce in high-volume production environments
LANGFUSE_SAMPLE_RATE=1.0

# Prompt Management Labels
LANGFUSE_PROMPT_LABEL=production  # or: staging, development

# Spend Alerts (optional)
LANGFUSE_DAILY_COST_LIMIT=50.0
LANGFUSE_TRACE_COST_ALERT=5.0
```

**Step 2: Commit**

```bash
git add apps/backend/.env.example
git commit -m "docs: add complete Langfuse configuration to .env.example"
```

---

### Task Z2: Final Integration Test

**Files:**
- Create: `tests/test_langfuse_full_integration.py`

**Step 1: Write integration test**

```python
# tests/test_langfuse_full_integration.py
"""
Full Langfuse Integration Test
==============================

Tests all Langfuse features working together.
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock


class TestLangfuseFullIntegration:
    """Test all Langfuse features."""

    def test_categorical_scores_available(self):
        """Verify categorical score functions are available."""
        from analytics.langfuse_integration import (
            save_categorical_score,
            save_boolean_score,
            save_build_result,
            save_qa_verdict,
            save_qa_first_attempt,
        )
        assert callable(save_categorical_score)
        assert callable(save_boolean_score)
        assert callable(save_build_result)
        assert callable(save_qa_verdict)
        assert callable(save_qa_first_attempt)

    def test_metadata_propagation_available(self):
        """Verify metadata propagation is available."""
        from analytics.langfuse_integration import propagate_attributes
        assert callable(propagate_attributes)

    def test_trace_sampling_available(self):
        """Verify trace sampling is available."""
        from analytics.langfuse_integration import (
            configure_sampling,
            get_sample_rate,
            should_sample_trace,
        )
        assert callable(configure_sampling)
        assert callable(get_sample_rate)
        assert callable(should_sample_trace)

    def test_prompt_registry_available(self):
        """Verify prompt registry is available."""
        from analytics.prompt_registry import (
            get_prompt,
            get_prompt_text,
            get_agent_prompt,
            compile_prompt_template,
        )
        assert callable(get_prompt)
        assert callable(get_prompt_text)
        assert callable(get_agent_prompt)
        assert callable(compile_prompt_template)

    def test_metrics_client_available(self):
        """Verify metrics client is available."""
        from analytics.metrics_client import (
            get_daily_metrics,
            get_project_cost,
            get_traces,
            get_observations,
        )
        assert callable(get_daily_metrics)
        assert callable(get_project_cost)
        assert callable(get_traces)
        assert callable(get_observations)

    def test_evaluators_available(self):
        """Verify evaluators are available."""
        from analytics.evaluators import (
            create_evaluator_config,
            run_evaluation,
            list_evaluators,
            BUILTIN_EVALUATORS,
        )
        assert callable(create_evaluator_config)
        assert callable(run_evaluation)
        assert callable(list_evaluators)
        assert "code_quality" in BUILTIN_EVALUATORS

    def test_datasets_available(self):
        """Verify datasets are available."""
        from analytics.datasets import (
            create_dataset,
            add_dataset_item,
            get_dataset_items,
            run_experiment,
        )
        assert callable(create_dataset)
        assert callable(add_dataset_item)
        assert callable(get_dataset_items)
        assert callable(run_experiment)
```

**Step 2: Run full test suite**

Run: `apps/backend/.venv/bin/pytest tests/test_langfuse_full_integration.py -v`
Expected: PASS

**Step 3: Final commit**

```bash
git add tests/test_langfuse_full_integration.py
git commit -m "test: add Langfuse full integration test suite"
```

---

## Summary

This plan implements all 12 Langfuse features through 6 parallel workstreams:

| Workstream | Features | Tasks | Parallel With |
|------------|----------|-------|---------------|
| A | Scores, Metadata, Sampling | A1-A4 | B, C, D |
| B | Prompt Management | B1-B3 | A, C, D |
| C | Metrics API | C1-C2 | A, B, D |
| D | Frontend Feedback | D1-D4 | A, B, C |
| E | LLM-as-a-Judge | E1 | After A |
| F | Datasets/Experiments | F1 | After B |

**Total tasks:** 17 main tasks + 2 integration tasks = 19 tasks

**Estimated parallel execution:**
- Wave 1: A, B, C, D (parallel)
- Wave 2: E, F (parallel, after Wave 1)
- Wave 3: Z1, Z2 (final integration)

---

Plan complete and saved to `apps/backend/plans/2025-12-30-langfuse-full-integration.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**