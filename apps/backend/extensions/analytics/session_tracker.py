"""
Session Tracker
===============

Tracks metrics for agent sessions including:
- Token usage per model
- Tool call counts and timing
- Session duration
- Agent type and status

This data is used for:
- ROI calculation (cost side)
- Langfuse trace enrichment
- Analytics dashboards

Thread-safe for concurrent tool calls within a session.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Thread-local storage for session context
_session_context = threading.local()


@dataclass
class ToolCall:
    """Record of a single tool call."""
    tool_name: str
    started_at: float
    ended_at: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None

    def complete(self, success: bool = True, error: Optional[str] = None):
        """Mark the tool call as complete."""
        self.ended_at = time.time()
        self.duration_ms = (self.ended_at - self.started_at) * 1000
        self.success = success
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "duration_ms": round(self.duration_ms, 2) if self.duration_ms else None,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class SessionMetrics:
    """Metrics collected during an agent session."""
    # Identity
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    spec_id: Optional[str] = None
    agent_type: str = "unknown"
    project_dir: Optional[str] = None

    # Timing
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ended_at: Optional[str] = None
    duration_seconds: Optional[float] = None

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    by_model: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # Tool calls
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_call_count: int = 0
    tool_success_count: int = 0
    tool_error_count: int = 0
    tool_calls_by_name: Dict[str, int] = field(default_factory=dict)

    # Artifacts (populated at end of session)
    artifact_count: int = 0
    artifact_value_usd: float = 0.0

    # Status
    status: str = "running"  # running, completed, failed

    # Thread safety
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add_token_usage(self, model: str, input_tokens: int, output_tokens: int):
        """Add token usage for a model."""
        with self._lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.total_tokens += input_tokens + output_tokens

            if model not in self.by_model:
                self.by_model[model] = {"input_tokens": 0, "output_tokens": 0}
            self.by_model[model]["input_tokens"] += input_tokens
            self.by_model[model]["output_tokens"] += output_tokens

    def start_tool_call(self, tool_name: str) -> ToolCall:
        """Record the start of a tool call."""
        tool_call = ToolCall(tool_name=tool_name, started_at=time.time())
        with self._lock:
            self.tool_calls.append(tool_call)
            self.tool_call_count += 1
            if tool_name not in self.tool_calls_by_name:
                self.tool_calls_by_name[tool_name] = 0
            self.tool_calls_by_name[tool_name] += 1
        return tool_call

    def end_tool_call(self, tool_call: ToolCall, success: bool = True, error: Optional[str] = None):
        """Record the end of a tool call."""
        tool_call.complete(success=success, error=error)
        with self._lock:
            if success:
                self.tool_success_count += 1
            else:
                self.tool_error_count += 1

    def complete(self, status: str = "completed"):
        """Mark the session as complete."""
        self.ended_at = datetime.now(timezone.utc).isoformat()
        self.status = status

        # Calculate duration
        started = datetime.fromisoformat(self.started_at.replace('Z', '+00:00'))
        ended = datetime.fromisoformat(self.ended_at.replace('Z', '+00:00'))
        self.duration_seconds = (ended - started).total_seconds()

    def get_token_usage_for_roi(self) -> List[Dict[str, Any]]:
        """Get token usage in format expected by ROI calculator."""
        return [
            {
                "model": model,
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
            }
            for model, usage in self.by_model.items()
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": {
                "session_id": self.session_id,
                "trace_id": self.trace_id,
                "spec_id": self.spec_id,
                "agent_type": self.agent_type,
            },
            "timing": {
                "started_at": self.started_at,
                "ended_at": self.ended_at,
                "duration_seconds": round(self.duration_seconds, 2) if self.duration_seconds else None,
            },
            "tokens": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens,
                "by_model": self.by_model,
            },
            "tools": {
                "call_count": self.tool_call_count,
                "success_count": self.tool_success_count,
                "error_count": self.tool_error_count,
                "by_name": self.tool_calls_by_name,
            },
            "artifacts": {
                "count": self.artifact_count,
                "value_usd": round(self.artifact_value_usd, 2),
            },
            "status": self.status,
        }


# =============================================================================
# Session Context Management
# =============================================================================

def start_session(
    agent_type: str,
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    project_dir: Optional[str] = None,
    session_id: Optional[str] = None,
) -> SessionMetrics:
    """
    Start tracking a new agent session.

    Call this at the beginning of an agent run.
    """
    metrics = SessionMetrics(
        session_id=session_id,
        trace_id=trace_id,
        spec_id=spec_id,
        agent_type=agent_type,
        project_dir=project_dir,
    )

    # Store in thread-local
    _session_context.metrics = metrics

    logger.info(f"Started session tracking for {agent_type}")
    return metrics


def get_current_session() -> Optional[SessionMetrics]:
    """Get the current session metrics."""
    return getattr(_session_context, 'metrics', None)


def end_session(status: str = "completed") -> Optional[SessionMetrics]:
    """
    End the current session and return final metrics.

    Call this at the end of an agent run.
    """
    metrics = get_current_session()
    if metrics:
        metrics.complete(status=status)
        logger.info(
            f"Ended session: {metrics.agent_type} "
            f"({metrics.tool_call_count} tools, {metrics.total_tokens} tokens)"
        )

        # Clear thread-local
        _session_context.metrics = None

    return metrics


# =============================================================================
# Tracking Functions (called from hooks)
# =============================================================================

def track_token_usage(model: str, input_tokens: int, output_tokens: int):
    """Track token usage for the current session."""
    metrics = get_current_session()
    if metrics:
        metrics.add_token_usage(model, input_tokens, output_tokens)
        logger.debug(f"Tracked tokens: {model} +{input_tokens}in +{output_tokens}out")


def track_tool_start(tool_name: str) -> Optional[ToolCall]:
    """Track the start of a tool call."""
    metrics = get_current_session()
    if metrics:
        tool_call = metrics.start_tool_call(tool_name)
        logger.debug(f"Tool started: {tool_name}")
        return tool_call
    return None


def track_tool_end(tool_call: Optional[ToolCall], success: bool = True, error: Optional[str] = None):
    """Track the end of a tool call."""
    if tool_call is None:
        return

    metrics = get_current_session()
    if metrics:
        metrics.end_tool_call(tool_call, success=success, error=error)
        logger.debug(
            f"Tool ended: {tool_call.tool_name} "
            f"({tool_call.duration_ms:.1f}ms, {'success' if success else 'error'})"
        )


def track_artifact(artifact_type: str, value_usd: float):
    """Track an artifact creation in the current session."""
    metrics = get_current_session()
    if metrics:
        with metrics._lock:
            metrics.artifact_count += 1
            metrics.artifact_value_usd += value_usd
        logger.debug(f"Tracked artifact: {artifact_type} (${value_usd:.2f})")


# =============================================================================
# Session Registry (for multi-session tracking)
# =============================================================================

_session_registry: Dict[str, SessionMetrics] = {}
_registry_lock = threading.Lock()


def register_session(session_id: str, metrics: SessionMetrics):
    """Register a session in the global registry."""
    with _registry_lock:
        _session_registry[session_id] = metrics


def get_session(session_id: str) -> Optional[SessionMetrics]:
    """Get a session from the registry."""
    return _session_registry.get(session_id)


def get_all_sessions() -> Dict[str, SessionMetrics]:
    """Get all registered sessions."""
    return dict(_session_registry)


def cleanup_completed_sessions(max_age_seconds: int = 3600):
    """Remove completed sessions older than max_age_seconds."""
    now = datetime.now(timezone.utc)
    to_remove = []

    with _registry_lock:
        for session_id, metrics in _session_registry.items():
            if metrics.status != "running" and metrics.ended_at:
                ended = datetime.fromisoformat(metrics.ended_at.replace('Z', '+00:00'))
                age = (now - ended).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(session_id)

        for session_id in to_remove:
            del _session_registry[session_id]

    if to_remove:
        logger.info(f"Cleaned up {len(to_remove)} old sessions")
