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
import random
from typing import Optional, Any, Dict, List
from dataclasses import dataclass
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Track initialization state
_langfuse_initialized = False
_langfuse_client = None

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


# =============================================================================
# Thread-Safe Trace ID Propagation (for MCP tools)
# =============================================================================

def set_current_trace_id(trace_id: str) -> None:
    """
    Set the current trace_id in thread-local storage.

    This is used to pass the trace_id to MCP tools that run in the same
    thread/process as the caller. Thread-safe for concurrent execution.

    Args:
        trace_id: Langfuse trace ID to set
    """
    _propagated_context.trace_id = trace_id


def get_current_trace_id() -> Optional[str]:
    """
    Get the current trace_id from thread-local storage.

    Returns:
        Current trace_id or None if not set
    """
    return getattr(_propagated_context, 'trace_id', None)


def clear_current_trace_id() -> None:
    """Clear the current trace_id from thread-local storage."""
    if hasattr(_propagated_context, 'trace_id'):
        delattr(_propagated_context, 'trace_id')


@contextmanager
def scoped_trace_id(trace_id: str):
    """
    Context manager for scoped trace_id setting.

    Automatically clears the trace_id when the context exits.
    Thread-safe for concurrent execution.

    Usage:
        with scoped_trace_id(my_trace_id):
            # MCP tools called here will get this trace_id
            await run_mcp_tools()

    Args:
        trace_id: Langfuse trace ID to set for this scope
    """
    previous_trace_id = get_current_trace_id()
    try:
        set_current_trace_id(trace_id)
        yield trace_id
    finally:
        if previous_trace_id:
            set_current_trace_id(previous_trace_id)
        else:
            clear_current_trace_id()


# =============================================================================
# Trace Sampling
# =============================================================================

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

        # Apply sampling rate from environment
        env_rate = get_sampling_from_env()
        if env_rate < 1.0:
            configure_sampling(env_rate)

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
    all Claude Agent SDK calls. The integration is optional - if it
    fails, manual tracing via trace_context() is used instead.

    Note: LangSmith warnings about "Run compression" and "Invalid type dict"
    are suppressed as they don't affect Langfuse integration.
    """
    # Check if instrumentation is explicitly disabled
    if os.environ.get("LANGFUSE_DISABLE_SDK_INSTRUMENTATION", "").lower() == "true":
        logger.debug("Claude SDK instrumentation disabled via LANGFUSE_DISABLE_SDK_INSTRUMENTATION")
        return

    try:
        # Suppress LangSmith warnings that don't affect Langfuse
        os.environ.setdefault("LANGSMITH_SILENCE_WARNINGS", "true")

        # Set required environment variables for OTEL instrumentation
        os.environ.setdefault("LANGSMITH_OTEL_ENABLED", "true")
        os.environ.setdefault("LANGSMITH_OTEL_ONLY", "true")
        os.environ.setdefault("LANGSMITH_TRACING", "true")

        # Suppress insights/compression warnings
        import warnings
        warnings.filterwarnings("ignore", message=".*Run compression.*")
        warnings.filterwarnings("ignore", message=".*Invalid type dict.*")

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
    # Check sampling
    if not should_sample_trace():
        logger.debug(f"Trace '{name}' skipped due to sampling (rate: {_sample_rate})")
        yield None
        return

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

            # Merge with propagated context
            propagated_meta = _get_propagated_metadata()
            trace_metadata = {**propagated_meta, **trace_metadata}

            propagated_tags = _get_propagated_tags()
            if tags:
                all_tags = list(set(propagated_tags + list(tags)))
            else:
                all_tags = propagated_tags if propagated_tags else None

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
                logger.debug(f"trace_context: Got trace_id={trace_id} for '{name}'")
            except Exception as e:
                trace_id = None
                logger.warning(f"trace_context: Failed to get trace_id for '{name}': {e}")

            if trace_id:
                _current_trace_id = trace_id
                _trace_context_stack.append(span)
                # CRITICAL: Set trace_id in thread-local storage for MCP tools
                # This ensures artifacts created via MCP tools are linked to this trace
                set_current_trace_id(trace_id)
                logger.info(f"trace_context: Created Langfuse trace: {trace_id} ({name})")
            else:
                logger.warning(f"trace_context: No trace_id obtained for '{name}', observations may not be tracked")

            # Set trace-level attributes using update_current_trace
            try:
                # Build tags (start from merged all_tags)
                trace_tags = list(all_tags) if all_tags else []
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

        # Restore previous trace_id in thread-local storage or clear if none
        # This maintains proper nesting for nested traces
        if previous_trace_id:
            set_current_trace_id(previous_trace_id)
        else:
            clear_current_trace_id()

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
        logger.warning(f"log_generation_in_current_trace: No Langfuse client available for '{name}'")
        return None

    try:
        # Log for debugging
        logger.debug(f"log_generation_in_current_trace: Creating generation '{name}' with model={model}")

        # Use start_as_current_generation for LLM calls
        gen_cm = _langfuse_client.start_as_current_generation(
            name=name,
            model=model,
            input=input_data,
            metadata=metadata or {},
        )
        gen = gen_cm.__enter__()
        logger.debug(f"log_generation_in_current_trace: Generation context entered, gen={gen}")

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

        # Flush to ensure the generation is sent
        try:
            _langfuse_client.flush()
        except Exception as flush_err:
            logger.debug(f"Failed to flush after generation: {flush_err}")

        return gen
    except Exception as e:
        logger.warning(f"Failed to log generation {name}: {e}", exc_info=True)
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
        _langfuse_client.create_score(
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
        _langfuse_client.create_score(
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
