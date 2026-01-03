"""
Extensions Analytics
====================

Provides analytics integration for the extension layer:
    - Langfuse tracing (tracer.py)
    - Artifact capture with full content (artifact_capture.py)
    - Value attribution engine (value_engine.py)
    - Atomic artifact storage (storage.py)
    - ROI calculation (roi_calculator.py)
    - Session metrics tracking (session_tracker.py)

This module wraps the existing analytics/ module from the fork,
providing a clean interface for the extension layer.

Key Features:
    - EXPLICIT MODE: Artifacts captured from MCP tool calls
    - EXTRACTION MODE: Optional regex fallback (ARTIFACT_EXTRACTION_ENABLED=true)
    - Full content storage: No truncation of artifacts
    - ROI calculation: Value vs cost with confidence scoring
"""

import logging
import os

logger = logging.getLogger(__name__)

_analytics_initialized = False
_langfuse_available = False


def init_analytics() -> bool:
    """
    Initialize analytics subsystem.

    Returns:
        True if Langfuse is available and configured, False otherwise.
    """
    global _analytics_initialized, _langfuse_available

    if _analytics_initialized:
        return _langfuse_available

    # Check if Langfuse is enabled via env
    langfuse_enabled = os.environ.get("LANGFUSE_ENABLED", "").lower() in ("true", "1", "yes")

    if not langfuse_enabled:
        logger.info("Langfuse disabled (LANGFUSE_ENABLED not set)")
        _analytics_initialized = True
        _langfuse_available = False
        return False

    # Try to initialize Langfuse
    try:
        from analytics.langfuse_integration import init_langfuse, is_langfuse_ready

        init_result = init_langfuse()
        _langfuse_available = is_langfuse_ready()

        if _langfuse_available:
            logger.info("Langfuse initialized successfully")
        else:
            logger.warning("Langfuse init returned but not ready")

    except ImportError as e:
        logger.warning(f"Could not import Langfuse integration: {e}")
        _langfuse_available = False
    except Exception as e:
        logger.error(f"Langfuse initialization failed: {e}")
        _langfuse_available = False

    _analytics_initialized = True
    return _langfuse_available


def finalize_analytics():
    """
    Finalize analytics - flush pending data.
    """
    if not _langfuse_available:
        return

    try:
        from analytics.langfuse_integration import flush_langfuse
        flush_langfuse()
        logger.debug("Langfuse flushed")
    except Exception as e:
        logger.warning(f"Failed to flush Langfuse: {e}")

    try:
        from extensions.analytics.tracer import finalize_all_traces
        finalize_all_traces()
    except Exception as e:
        logger.warning(f"Failed to finalize traces: {e}")


def is_analytics_enabled() -> bool:
    """Check if analytics is available."""
    return _langfuse_available


# Convenience imports - Tracer
from .tracer import (
    start_trace,
    end_trace,
    get_current_trace_id,
    is_tracing_enabled,
    record_tool_use,
    record_artifact_created,
    record_session_metrics,
)

# Convenience imports - Collector (legacy)
from .collector import (
    collect_session_artifacts,
    get_collected_artifacts,
)

# New modules - Value Engine
from .value_engine import (
    get_artifact_value,
    ValueAttribution,
    ValueDimension,
    ARTIFACT_VALUES,
    AGENT_CONFIDENCE,
)

# New modules - Storage
from .storage import (
    save_artifact,
    load_artifact,
    list_artifacts,
    get_artifacts_summary,
)

# New modules - Artifact Capture
from .artifact_capture import (
    capture_from_tool_result,
    capture_from_mcp_tool_result,
    capture_from_agent_output,
    get_session_artifacts_summary,
    ARTIFACT_TOOLS,
)

# New modules - ROI Calculator
from .roi_calculator import (
    calculate_session_roi,
    calculate_artifact_roi,
    get_roi_summary,
    get_token_cost,
    ROIResult,
    CostBreakdown,
)

# New modules - Session Tracker
from .session_tracker import (
    start_session,
    end_session,
    get_current_session,
    track_token_usage,
    track_tool_start,
    track_tool_end,
    track_artifact,
    SessionMetrics,
)

__all__ = [
    # Core
    "init_analytics",
    "finalize_analytics",
    "is_analytics_enabled",
    # Tracer
    "start_trace",
    "end_trace",
    "get_current_trace_id",
    "is_tracing_enabled",
    "record_tool_use",
    "record_artifact_created",
    "record_session_metrics",
    # Collector (legacy)
    "collect_session_artifacts",
    "get_collected_artifacts",
    # Value Engine
    "get_artifact_value",
    "ValueAttribution",
    "ValueDimension",
    "ARTIFACT_VALUES",
    "AGENT_CONFIDENCE",
    # Storage
    "save_artifact",
    "load_artifact",
    "list_artifacts",
    "get_artifacts_summary",
    # Artifact Capture
    "capture_from_tool_result",
    "capture_from_mcp_tool_result",
    "capture_from_agent_output",
    "get_session_artifacts_summary",
    "ARTIFACT_TOOLS",
    # ROI Calculator
    "calculate_session_roi",
    "calculate_artifact_roi",
    "get_roi_summary",
    "get_token_cost",
    "ROIResult",
    "CostBreakdown",
    # Session Tracker
    "start_session",
    "end_session",
    "get_current_session",
    "track_token_usage",
    "track_tool_start",
    "track_tool_end",
    "track_artifact",
    "SessionMetrics",
]
