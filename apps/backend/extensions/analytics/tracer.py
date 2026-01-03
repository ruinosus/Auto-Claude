"""
Langfuse Tracer
===============

Manages Langfuse traces for the extension layer.

Features:
    - Automatic trace creation per agent session
    - Trace ID propagation to subprocesses
    - Tool usage and artifact tracking
    - Session metrics collection
"""

import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TraceData:
    """Data associated with a trace."""
    trace_id: str
    agent_type: str
    started_at: datetime
    context: Any = None  # Langfuse context manager
    tool_uses: List[Dict[str, Any]] = field(default_factory=list)
    artifacts_created: List[str] = field(default_factory=list)
    session_metrics: Dict[str, Any] = field(default_factory=dict)
    ended: bool = False


# Active traces by trace_id
_active_traces: Dict[str, TraceData] = {}

# Current trace ID (thread-local would be better for multi-threaded)
_current_trace_id: Optional[str] = None


def is_tracing_enabled() -> bool:
    """Check if tracing is enabled."""
    try:
        from analytics.langfuse_integration import is_langfuse_ready
        return is_langfuse_ready()
    except ImportError:
        return False


def start_trace(agent_type: str) -> Optional[str]:
    """
    Start a new Langfuse trace.

    If a trace ID is already in the environment (from parent process),
    it will be reused instead of creating a new one.

    Args:
        agent_type: Type of agent (coder, planner, qa_reviewer, etc.)

    Returns:
        Trace ID or None if tracing is disabled
    """
    global _current_trace_id

    if not is_tracing_enabled():
        return None

    # Check for existing trace from parent process
    env_trace_id = os.environ.get("LANGFUSE_TRACE_ID")
    if env_trace_id and env_trace_id in _active_traces:
        _current_trace_id = env_trace_id
        logger.debug(f"Reusing existing trace: {env_trace_id}")
        return env_trace_id

    # Create new trace
    try:
        from analytics.langfuse_integration import trace_context

        # Determine project ID from environment or cwd
        project_id = os.environ.get("PROJECT_ID", os.path.basename(os.getcwd()))

        ctx = trace_context(
            name=f"{agent_type}-session",
            agent_type=agent_type,
            project_id=project_id,
            tags=[agent_type, "extensions"],
            metadata={
                "instrumented": True,
                "extensions_version": "1.0.0",
            },
        )

        # Enter context
        trace_obj = ctx.__enter__()
        trace_id = trace_obj.trace_id

        # Store trace data
        _active_traces[trace_id] = TraceData(
            trace_id=trace_id,
            agent_type=agent_type,
            started_at=datetime.now(),
            context=ctx,
        )

        _current_trace_id = trace_id
        logger.info(f"Started trace: {trace_id} for {agent_type}")

        return trace_id

    except Exception as e:
        logger.error(f"Failed to start trace: {e}")
        return None


def end_trace(trace_id: str, success: bool = True):
    """
    End a trace and set its output.

    Args:
        trace_id: ID of the trace to end
        success: Whether the session was successful
    """
    if trace_id not in _active_traces:
        logger.warning(f"Trace not found: {trace_id}")
        return

    trace_data = _active_traces[trace_id]

    if trace_data.ended:
        logger.debug(f"Trace already ended: {trace_id}")
        return

    try:
        ctx = trace_data.context

        if ctx:
            # Set output with collected data
            output = {
                "success": success,
                "agent_type": trace_data.agent_type,
                "duration_seconds": (datetime.now() - trace_data.started_at).total_seconds(),
                "tool_uses_count": len(trace_data.tool_uses),
                "artifacts_count": len(trace_data.artifacts_created),
                "session_metrics": trace_data.session_metrics,
            }

            # Get trace object and set output
            if hasattr(ctx, '__enter__'):
                # Context manager style
                trace_obj = ctx.__enter__()
                if hasattr(trace_obj, 'set_output'):
                    trace_obj.set_output(output)
                ctx.__exit__(None, None, None)
            elif hasattr(ctx, 'set_output'):
                ctx.set_output(output)

        trace_data.ended = True
        logger.info(f"Ended trace: {trace_id}, success={success}")

    except Exception as e:
        logger.error(f"Failed to end trace {trace_id}: {e}")

    finally:
        # Flush Langfuse
        try:
            from analytics.langfuse_integration import flush_langfuse
            flush_langfuse()
        except Exception:
            pass


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID."""
    global _current_trace_id

    # First check if we have a local trace
    if _current_trace_id:
        return _current_trace_id

    # Then check environment (from parent process)
    return os.environ.get("LANGFUSE_TRACE_ID")


async def record_tool_use(
    tool_name: str,
    tool_use_id: str,
    success: bool,
):
    """
    Record a tool use for the current trace.

    Args:
        tool_name: Name of the tool
        tool_use_id: Unique ID for this tool use
        success: Whether the tool succeeded
    """
    trace_id = get_current_trace_id()
    if not trace_id or trace_id not in _active_traces:
        return

    _active_traces[trace_id].tool_uses.append({
        "tool_name": tool_name,
        "tool_use_id": tool_use_id,
        "success": success,
        "timestamp": datetime.now().isoformat(),
    })


async def record_artifact_created(
    artifact_id: str,
    artifact_type: str = "unknown",
):
    """
    Record an artifact creation for the current trace.

    Args:
        artifact_id: ID of the created artifact
        artifact_type: Type of artifact
    """
    trace_id = get_current_trace_id()
    if not trace_id or trace_id not in _active_traces:
        return

    _active_traces[trace_id].artifacts_created.append(artifact_id)
    logger.debug(f"Recorded artifact: {artifact_id} ({artifact_type})")


async def record_session_metrics(
    trace_id: Optional[str],
    agent_type: str,
    status: str,
    response_length: int,
    success: bool,
    error: Optional[str] = None,
):
    """
    Record session-level metrics.

    Args:
        trace_id: Trace ID
        agent_type: Type of agent
        status: Session status (completed, error, etc.)
        response_length: Length of response text
        success: Whether session was successful
        error: Error message if failed
    """
    tid = trace_id or get_current_trace_id()
    if not tid or tid not in _active_traces:
        return

    _active_traces[tid].session_metrics = {
        "agent_type": agent_type,
        "status": status,
        "response_length": response_length,
        "success": success,
        "error": error,
    }


def get_trace_data(trace_id: str) -> Optional[TraceData]:
    """Get data for a specific trace."""
    return _active_traces.get(trace_id)


def finalize_all_traces():
    """Finalize all active traces (cleanup)."""
    for trace_id, trace_data in list(_active_traces.items()):
        if not trace_data.ended:
            end_trace(trace_id, success=True)

    _active_traces.clear()
