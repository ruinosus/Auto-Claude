"""
Langfuse Integration for Auto-Claude
=====================================

Provides LLM observability, cost tracking, and analytics via Langfuse.
Uses Langfuse's native Python SDK for tracing Claude Agent SDK calls.

This is the PRIMARY observability system for Auto-Claude. All traces,
generations, and ROI scores are stored in Langfuse.

Integration approach:
- For Claude Agent SDK: Uses LangSmith OTEL instrumentation (automatic)
- For manual tracing: Uses start_as_current_span + update_current_trace

Setup:
------
1. Start Langfuse local: ./infra/langfuse/setup.sh start
2. Create account at http://localhost:3001
3. Create project and get API keys
4. Set in .env:
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=http://localhost:3001
   LANGFUSE_ENABLED=true

References:
- https://langfuse.com/integrations/frameworks/claude-agent-sdk
- https://langfuse.com/integrations/model-providers/anthropic
- https://langfuse.com/docs/sdk/python/decorators
"""

import os
import logging
from typing import Optional, Any, Dict, List
from dataclasses import dataclass
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Track initialization state
_langfuse_initialized = False
_langfuse_client = None


def is_langfuse_enabled() -> bool:
    """Check if Langfuse integration is enabled via environment variable."""
    return os.environ.get("LANGFUSE_ENABLED", "").lower() == "true"


def get_langfuse_host() -> str:
    """Get the Langfuse host URL (default: local Docker instance)."""
    return os.environ.get("LANGFUSE_HOST", os.environ.get("LANGFUSE_BASE_URL", "http://localhost:3001"))


def _check_langfuse_config() -> bool:
    """
    Check if Langfuse is properly configured.

    Returns:
        True if all required environment variables are set
    """
    required_vars = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
    missing = [var for var in required_vars if not os.environ.get(var)]

    if missing:
        logger.warning(
            f"Langfuse enabled but missing environment variables: {', '.join(missing)}. "
            f"See docs/ANALYTICS_ROI_GUIDE.md for setup instructions."
        )
        return False

    return True


def init_langfuse() -> bool:
    """
    Initialize Langfuse integration.

    This should be called once at application startup. The function is
    idempotent - calling it multiple times has no effect after the first
    successful initialization.

    Returns:
        True if Langfuse was successfully initialized
    """
    global _langfuse_initialized, _langfuse_client

    # Already initialized
    if _langfuse_initialized:
        return True

    # Check if enabled
    if not is_langfuse_enabled():
        logger.debug("Langfuse integration disabled (LANGFUSE_ENABLED != 'true')")
        return False

    # Check configuration
    if not _check_langfuse_config():
        return False

    try:
        # Ensure LANGFUSE_HOST is also available as LANGFUSE_BASE_URL
        host = get_langfuse_host()
        if not os.environ.get("LANGFUSE_BASE_URL"):
            os.environ["LANGFUSE_BASE_URL"] = host

        # Use get_client() - the correct way per Langfuse docs
        from langfuse import get_client

        _langfuse_client = get_client()

        # Verify authentication
        if not _langfuse_client.auth_check():
            logger.error("Langfuse authentication failed. Check your API keys.")
            return False

        _langfuse_initialized = True
        logger.info(f"Langfuse integration initialized (host: {host})")

        # Try to configure Claude Agent SDK instrumentation (optional)
        _configure_claude_sdk_instrumentation()

        return True

    except ImportError as e:
        logger.warning(
            f"Langfuse package not installed: {e}. "
            f"Run: pip install langfuse"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse: {e}")
        return False


def _configure_claude_sdk_instrumentation():
    """
    Configure automatic instrumentation for Claude Agent SDK.

    This uses LangSmith's OTEL integration to automatically capture
    all Claude Agent SDK calls.
    """
    try:
        # Set required environment variables for OTEL instrumentation
        os.environ.setdefault("LANGSMITH_OTEL_ENABLED", "true")
        os.environ.setdefault("LANGSMITH_OTEL_ONLY", "true")
        os.environ.setdefault("LANGSMITH_TRACING", "true")

        from langsmith.integrations.claude_agent_sdk import configure_claude_agent_sdk
        configure_claude_agent_sdk()
        logger.info("Claude Agent SDK instrumentation configured")
    except ImportError:
        logger.debug("LangSmith Claude SDK instrumentation not available - manual tracing will be used")
    except Exception as e:
        logger.debug(f"Failed to configure Claude SDK instrumentation: {e}")


def get_langfuse_client():
    """
    Get the Langfuse client for custom observations.

    Returns:
        Langfuse client instance, or None if not initialized
    """
    global _langfuse_client

    if not _langfuse_initialized:
        return None

    return _langfuse_client


def flush_langfuse() -> None:
    """Flush any pending Langfuse data."""
    if _langfuse_client:
        try:
            _langfuse_client.flush()
        except Exception as e:
            logger.debug(f"Failed to flush Langfuse: {e}")


def is_langfuse_ready() -> bool:
    """Check if Langfuse is initialized and ready to receive traces."""
    return _langfuse_initialized


# =============================================================================
# Trace Context Management
# =============================================================================

# Global trace context stack (for nested traces)
_trace_context_stack: List[Any] = []
_current_trace_id: Optional[str] = None


def get_current_trace_id() -> Optional[str]:
    """Get the current active trace ID."""
    if _langfuse_client:
        try:
            return _langfuse_client.get_current_trace_id()
        except Exception:
            pass
    return _current_trace_id


def set_current_trace_id(trace_id: Optional[str]):
    """Set the current active trace ID."""
    global _current_trace_id
    _current_trace_id = trace_id


class TraceContext:
    """Context holder for trace info with input/output tracking."""

    def __init__(self, trace_id: Optional[str], span: Any, name: str):
        self.trace_id = trace_id
        self.span = span
        self.name = name
        self._input = None
        self._output = None

    def set_input(self, input_data: Any) -> None:
        """Set the trace input."""
        self._input = input_data
        if _langfuse_client:
            try:
                _langfuse_client.update_current_trace(input=input_data)
            except Exception as e:
                logger.debug(f"Failed to update trace input: {e}")

    def set_output(self, output_data: Any) -> None:
        """Set the trace output."""
        self._output = output_data
        if _langfuse_client:
            try:
                _langfuse_client.update_current_trace(output=output_data)
            except Exception as e:
                logger.debug(f"Failed to update trace output: {e}")

    def update(self, input_data: Optional[Any] = None, output_data: Optional[Any] = None) -> None:
        """Update trace input and/or output."""
        if input_data is not None:
            self.set_input(input_data)
        if output_data is not None:
            self.set_output(output_data)


@contextmanager
def trace_context(
    name: str,
    spec_id: Optional[str] = None,
    project_id: Optional[str] = None,
    agent_type: Optional[str] = None,
    metadata: Optional[Dict] = None,
    tags: Optional[List[str]] = None,
    input_data: Optional[Any] = None,
    output_data: Optional[Any] = None,
):
    """
    Context manager for creating and managing Langfuse traces.

    Uses start_as_current_span() and update_current_trace() per Langfuse docs.

    Usage:
        with trace_context(
            name="spec-001-build",
            spec_id="001",
            project_id="my-project",
            agent_type="coder",
            input_data={"prompt": "Build feature X"},
        ) as ctx:
            # Run agent session
            result = run_agent()
            ctx.set_output({"result": result})

    Args:
        name: Trace name
        spec_id: Optional spec identifier
        project_id: Optional project identifier (for isolating data between projects)
        agent_type: Optional agent type (planner, coder, qa_reviewer, qa_fixer)
        metadata: Additional metadata
        tags: Optional tags
        input_data: Initial input data for the trace
        output_data: Initial output data for the trace (usually set later)

    Yields:
        TraceContext object with trace_id and methods to update input/output
    """
    global _current_trace_id, _trace_context_stack

    span = None
    span_cm = None
    previous_trace_id = _current_trace_id
    trace_id = None
    ctx = None

    try:
        if _langfuse_client:
            # Build metadata
            trace_metadata = metadata.copy() if metadata else {}
            if spec_id:
                trace_metadata["spec_id"] = spec_id
            if project_id:
                trace_metadata["project_id"] = project_id
            if agent_type:
                trace_metadata["agent_type"] = agent_type
            trace_metadata["started_at"] = datetime.utcnow().isoformat()

            # Use start_as_current_span (correct API per Langfuse docs)
            span_cm = _langfuse_client.start_as_current_span(
                name=name,
                metadata=trace_metadata,
                input=input_data,
            )
            span = span_cm.__enter__()

            # Get trace ID
            try:
                trace_id = _langfuse_client.get_current_trace_id()
            except Exception:
                trace_id = None

            if trace_id:
                _current_trace_id = trace_id
                _trace_context_stack.append(span)
                logger.debug(f"Created Langfuse trace: {trace_id} ({name})")

            # Set trace-level attributes using update_current_trace
            try:
                # Build tags
                trace_tags = list(tags) if tags else []
                if project_id:
                    trace_tags.append(f"project:{project_id}")
                if spec_id:
                    trace_tags.append(f"spec:{spec_id}")
                if agent_type:
                    trace_tags.append(f"agent:{agent_type}")

                _langfuse_client.update_current_trace(
                    name=name,
                    input=input_data,
                    user_id=project_id,  # Use project_id as user_id for filtering
                    session_id=spec_id,  # Use spec_id as session_id for grouping
                    tags=trace_tags,
                )
            except Exception as e:
                logger.debug(f"Failed to update trace attributes: {e}")

        ctx = TraceContext(trace_id, span, name) if trace_id else None
        if ctx and input_data:
            ctx._input = input_data

        yield ctx

    except Exception as e:
        logger.debug(f"Error in trace_context: {e}")
        raise

    finally:
        if span_cm:
            try:
                # Update trace with final output if set via context
                if _langfuse_client and ctx:
                    final_output = ctx._output
                    if final_output is not None:
                        _langfuse_client.update_current_trace(output=final_output)

                    # Update span metadata with end time
                    if span:
                        span.update(
                            metadata={
                                **(metadata or {}),
                                "ended_at": datetime.utcnow().isoformat()
                            }
                        )
            except Exception as e:
                logger.debug(f"Failed to update trace on exit: {e}")

            # Exit the span context manager
            try:
                span_cm.__exit__(None, None, None)
            except Exception as e:
                logger.debug(f"Failed to exit span context: {e}")

        # Restore previous context
        if _trace_context_stack:
            _trace_context_stack.pop()
        _current_trace_id = previous_trace_id

        # Flush to ensure data is sent
        flush_langfuse()


# =============================================================================
# Generation Logging (within traces)
# =============================================================================

def log_generation_in_current_trace(
    name: str,
    model: str,
    input_data: Any,
    output_data: Optional[Any] = None,
    usage: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
    update_trace_io: bool = True,
) -> Optional[Any]:
    """
    Log a generation (LLM call) in the current active trace.

    Args:
        name: Generation name
        model: Model name (e.g., "claude-sonnet-4-5")
        input_data: Input to the model (prompt)
        output_data: Output from the model (response)
        usage: Token usage dict with keys: input, output, total
        metadata: Optional additional metadata
        update_trace_io: If True, also updates trace-level input/output

    Returns:
        Generation span object, or None if failed
    """
    if not _langfuse_client:
        return None

    try:
        # Use start_as_current_generation for LLM calls
        gen_cm = _langfuse_client.start_as_current_generation(
            name=name,
            model=model,
            input=input_data,
            metadata=metadata or {},
        )
        gen = gen_cm.__enter__()

        # Update with output and usage
        if gen:
            update_kwargs = {}
            if output_data is not None:
                update_kwargs["output"] = output_data
            if usage:
                update_kwargs["usage"] = {
                    "input": usage.get("input", usage.get("input_tokens", 0)),
                    "output": usage.get("output", usage.get("output_tokens", 0)),
                    "total": usage.get("total", usage.get("total_tokens", 0)),
                }
                if "cache_read" in usage:
                    update_kwargs["usage"]["cache_read_input_tokens"] = usage["cache_read"]
                if "cache_creation" in usage:
                    update_kwargs["usage"]["cache_creation_input_tokens"] = usage["cache_creation"]

            if update_kwargs:
                gen.update(**update_kwargs)

        # Exit generation context
        gen_cm.__exit__(None, None, None)

        logger.debug(f"Logged generation '{name}': model={model}")

        # Update trace-level input/output if requested
        if update_trace_io:
            try:
                update_kwargs = {}
                if input_data is not None:
                    update_kwargs["input"] = input_data
                if output_data is not None:
                    update_kwargs["output"] = output_data
                if update_kwargs:
                    _langfuse_client.update_current_trace(**update_kwargs)
            except Exception as e:
                logger.debug(f"Failed to update trace with generation IO: {e}")

        return gen
    except Exception as e:
        logger.warning(f"Failed to log generation {name}: {e}")
        return None


def create_span_in_current_trace(
    name: str,
    input_data: Optional[Any] = None,
    output_data: Optional[Any] = None,
    metadata: Optional[Dict] = None,
) -> Optional[Any]:
    """
    Create a span in the current active trace.

    Args:
        name: Span name
        input_data: Input data for the span
        output_data: Output data for the span
        metadata: Optional metadata

    Returns:
        Span context manager, or None if failed
    """
    if not _langfuse_client:
        return None

    try:
        return _langfuse_client.start_as_current_span(
            name=name,
            input=input_data,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.debug(f"Failed to create span {name}: {e}")
        return None


# =============================================================================
# ROI Scores Integration
# =============================================================================

@dataclass
class ROIScores:
    """ROI metrics to be saved as Langfuse scores."""
    roi_percentage: float
    business_value_usd: float
    actual_cost_usd: float
    dev_hours_saved: float
    lines_added: int = 0
    lines_removed: int = 0
    files_changed: int = 0
    qa_attempts: int = 0
    qa_passed: bool = False
    confidence_score: float = 0.0
    quality_multiplier: float = 1.0
    estimation_method: str = "hybrid"


def save_roi_scores(trace_id: str, scores: ROIScores) -> bool:
    """
    Save ROI scores to a Langfuse trace.

    Args:
        trace_id: The Langfuse trace ID
        scores: ROIScores dataclass with all metrics

    Returns:
        True if scores were saved successfully
    """
    if not _langfuse_client:
        logger.debug("Langfuse not initialized, skipping ROI scores")
        return False

    try:
        score_data = [
            ("roi_percentage", scores.roi_percentage),
            ("business_value_usd", scores.business_value_usd),
            ("actual_cost_usd", scores.actual_cost_usd),
            ("dev_hours_saved", scores.dev_hours_saved),
            ("confidence_score", scores.confidence_score),
            ("quality_multiplier", scores.quality_multiplier),
            ("lines_added", float(scores.lines_added)),
            ("lines_removed", float(scores.lines_removed)),
            ("files_changed", float(scores.files_changed)),
            ("qa_attempts", float(scores.qa_attempts)),
            ("qa_passed", 1.0 if scores.qa_passed else 0.0),
        ]

        for name, value in score_data:
            _langfuse_client.create_score(
                trace_id=trace_id,
                name=name,
                value=float(value),
                comment=f"Auto-calculated via {scores.estimation_method}"
            )

        logger.info(f"Saved ROI scores to trace {trace_id}: ROI={scores.roi_percentage:.1f}%")
        flush_langfuse()
        return True

    except Exception as e:
        logger.error(f"Failed to save ROI scores: {e}")
        return False


def save_score(trace_id: str, name: str, value: float, comment: Optional[str] = None) -> bool:
    """
    Save a single score to a Langfuse trace.

    Args:
        trace_id: The Langfuse trace ID
        name: Score name
        value: Score value (numeric)
        comment: Optional comment

    Returns:
        True if score was saved successfully
    """
    if not _langfuse_client:
        return False

    try:
        _langfuse_client.create_score(
            trace_id=trace_id,
            name=name,
            value=float(value),
            comment=comment
        )
        return True
    except Exception as e:
        logger.debug(f"Failed to save score {name}: {e}")
        return False


# =============================================================================
# Decorator for automatic tracing
# =============================================================================

def observe(name: Optional[str] = None, capture_input: bool = True, capture_output: bool = True):
    """
    Decorator to trace a function with Langfuse.

    Usage:
        @observe("my-function")
        def my_function(arg1, arg2):
            return result
    """
    def decorator(func):
        if not _langfuse_initialized:
            return func

        try:
            from langfuse.decorators import observe as langfuse_observe
            return langfuse_observe(
                name=name or func.__name__,
                capture_input=capture_input,
                capture_output=capture_output,
            )(func)
        except ImportError:
            return func

    return decorator


# =============================================================================
# Utility functions
# =============================================================================

def get_trace_url(trace_id: str) -> Optional[str]:
    """Get the Langfuse dashboard URL for a trace."""
    if not trace_id:
        return None

    host = get_langfuse_host()
    return f"{host}/trace/{trace_id}"


def fetch_trace_scores(trace_id: str) -> Dict[str, float]:
    """
    Fetch all scores for a trace from Langfuse.

    Returns:
        Dict mapping score names to values
    """
    if not _langfuse_client:
        return {}

    try:
        # Note: This may not be available in all Langfuse versions
        scores = _langfuse_client.fetch_scores(trace_id=trace_id)
        return {s.name: s.value for s in scores.data}
    except Exception as e:
        logger.debug(f"Failed to fetch scores for trace {trace_id}: {e}")
        return {}


def get_session_trace_name(spec_id: str, agent_type: str, session_num: int = 1) -> str:
    """Generate a consistent trace name for agent sessions."""
    return f"spec-{spec_id}-{agent_type}-session-{session_num}"
