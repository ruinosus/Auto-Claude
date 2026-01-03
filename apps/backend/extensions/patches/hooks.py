"""
SDK Hooks for Tracking
======================

Provides PostToolUse hooks for automatic tracking of:
    - Tool usage (which tools, how many times)
    - Artifact capture (EXPLICIT mode via MCP tools)
    - Session metrics (tokens, timing)
    - ROI calculation

Uses Claude SDK's native hook system.

Hook Chain:
    1. track_tool_timing - Records tool start/end for session metrics
    2. capture_artifacts - Captures artifacts from MCP tool results
    3. track_tool_usage - Records to Langfuse tracer
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_hooks_registered = False

# Get current session context (injected by session_tracker)
_current_context: Dict[str, Any] = {}


def set_hook_context(
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    agent_type: str = "unknown",
    project_dir: Optional[str] = None,
):
    """
    Set context for hooks to use.

    Call this when starting an agent session to provide
    context for artifact capture and tracking.
    """
    global _current_context
    _current_context = {
        "trace_id": trace_id,
        "spec_id": spec_id,
        "agent_type": agent_type,
        "project_dir": project_dir,
    }
    logger.debug(f"Hook context set: {agent_type}, trace={trace_id}")


def clear_hook_context():
    """Clear the hook context."""
    global _current_context
    _current_context = {}


def register_hooks() -> bool:
    """
    Register hooks configuration.

    Note: Hooks are not "registered" globally, they're added to each
    client via get_tracking_hooks(). This function just validates
    that the hook system is available.

    Returns:
        True if hooks system is available, False otherwise.
    """
    global _hooks_registered

    if _hooks_registered:
        return True

    try:
        from claude_agent_sdk import HookMatcher
        _hooks_registered = True
        logger.info("SDK hooks system available")
        return True
    except ImportError:
        logger.warning("claude_agent_sdk not available, hooks disabled")
        return False


def get_tracking_hooks() -> Dict[str, List[Any]]:
    """
    Get hook configuration for tracking.

    Returns:
        Dict of event -> HookMatcher list
    """
    if not _hooks_registered:
        return {}

    try:
        from claude_agent_sdk import HookMatcher

        return {
            "PostToolUse": [
                # Track all tool usage timing
                HookMatcher(matcher="*", hooks=[track_tool_timing]),
                # Capture artifacts from MCP tools (EXPLICIT MODE)
                HookMatcher(
                    matcher="mcp__auto-claude__*",
                    hooks=[capture_artifacts]
                ),
                # Track to Langfuse
                HookMatcher(matcher="*", hooks=[track_tool_usage]),
            ],
        }
    except ImportError:
        return {}


# =============================================================================
# Hook: Tool Timing (Session Tracker)
# =============================================================================

async def track_tool_timing(
    input_data: dict,
    tool_use_id: str,
    context: dict
) -> dict:
    """
    PostToolUse hook that tracks tool execution timing.

    Integrates with session_tracker for metrics collection.
    """
    try:
        from extensions.analytics.session_tracker import (
            get_current_session,
            track_tool_end,
        )

        tool_name = input_data.get("tool_name", "unknown")
        tool_result = input_data.get("tool_result", {})

        # Determine success
        is_error = False
        error_msg = None
        if isinstance(tool_result, dict):
            is_error = tool_result.get("is_error", False)
            if is_error:
                error_msg = tool_result.get("error", "Unknown error")

        # Get session and find the tool call by ID
        session = get_current_session()
        if session:
            # Find the tool call that matches this tool_use_id
            for tool_call in reversed(session.tool_calls):
                if tool_call.tool_name == tool_name and tool_call.ended_at is None:
                    track_tool_end(tool_call, success=not is_error, error=error_msg)
                    break

    except ImportError:
        pass  # Session tracker not available
    except Exception as e:
        logger.warning(f"Failed to track tool timing: {e}")

    return {}


# =============================================================================
# Hook: Artifact Capture (EXPLICIT MODE)
# =============================================================================

async def capture_artifacts(
    input_data: dict,
    tool_use_id: str,
    context: dict
) -> dict:
    """
    PostToolUse hook for capturing artifacts from MCP tools.

    This is EXPLICIT MODE - only captures from artifact creation tools
    that return structured artifact data.

    Args:
        input_data: Contains tool_name, tool_input, tool_result
        tool_use_id: Unique ID for this tool use
        context: Additional context

    Returns:
        Empty dict (observes only, doesn't modify)
    """
    try:
        from extensions.analytics.artifact_capture import (
            capture_from_tool_result,
            ARTIFACT_TOOLS,
        )
        from extensions.analytics.session_tracker import track_artifact

        tool_name = input_data.get("tool_name", "")

        # Only process artifact creation tools
        if tool_name not in ARTIFACT_TOOLS:
            return {}

        tool_result = input_data.get("tool_result", {})

        # Get context
        trace_id = _current_context.get("trace_id")
        spec_id = _current_context.get("spec_id")
        agent_type = _current_context.get("agent_type", "unknown")
        project_dir = _current_context.get("project_dir")

        # Capture and save artifact
        saved_artifacts, value_attribution = capture_from_tool_result(
            tool_name=tool_name,
            tool_result=tool_result,
            agent_type=agent_type,
            trace_id=trace_id,
            spec_id=spec_id,
            project_dir=project_dir,
        )

        # Track in session metrics
        for artifact in saved_artifacts:
            artifact_type = artifact.get("type", "unknown")
            value_usd = artifact.get("value_usd", 0)
            track_artifact(artifact_type, value_usd)

        if saved_artifacts:
            logger.info(
                f"[Hook] Captured {len(saved_artifacts)} artifact(s) "
                f"from {tool_name}"
            )

    except ImportError as e:
        logger.debug(f"Artifact capture not available: {e}")
    except Exception as e:
        logger.warning(f"Failed to capture artifacts: {e}")

    return {}


# =============================================================================
# Hook: Tool Usage (Langfuse Tracer)
# =============================================================================

async def track_tool_usage(
    input_data: dict,
    tool_use_id: str,
    context: dict
) -> dict:
    """
    PostToolUse hook that tracks all tool usage to Langfuse.

    This hook is called AFTER every tool execution.

    Args:
        input_data: Contains tool_name, tool_input, tool_result
        tool_use_id: Unique ID for this tool use
        context: Additional context

    Returns:
        Empty dict (observes only, doesn't modify)
    """
    try:
        from extensions.analytics.tracer import record_tool_use

        tool_name = input_data.get("tool_name", "unknown")
        tool_result = input_data.get("tool_result", {})

        # Determine success
        is_error = False
        if isinstance(tool_result, dict):
            is_error = tool_result.get("is_error", False)
        elif hasattr(tool_result, "is_error"):
            is_error = tool_result.is_error

        await record_tool_use(
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            success=not is_error,
        )

        logger.debug(f"Tracked tool use: {tool_name} (success={not is_error})")

    except ImportError:
        pass  # Tracer not available
    except Exception as e:
        # Never fail the tool execution due to tracking errors
        logger.warning(f"Failed to track tool usage: {e}")

    # Return empty dict - we only observe, don't modify
    return {}


# =============================================================================
# Convenience: Start/End Session with Hooks
# =============================================================================

def start_tracked_session(
    agent_type: str,
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    project_dir: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """
    Start a tracked session with all integrations.

    This sets up:
    - Hook context for artifact capture
    - Session tracker for metrics
    - Returns the session metrics object
    """
    from extensions.analytics.session_tracker import start_session

    # Set hook context
    set_hook_context(
        trace_id=trace_id,
        spec_id=spec_id,
        agent_type=agent_type,
        project_dir=project_dir,
    )

    # Start session tracking
    return start_session(
        agent_type=agent_type,
        trace_id=trace_id,
        spec_id=spec_id,
        project_dir=project_dir,
        session_id=session_id,
    )


def end_tracked_session(status: str = "completed") -> Optional[Dict[str, Any]]:
    """
    End a tracked session and get final metrics.

    This:
    - Calculates final ROI
    - Publishes to Langfuse
    - Clears hook context
    - Returns session summary

    Returns:
        Dict with session metrics and ROI, or None if no session
    """
    from extensions.analytics.session_tracker import end_session, get_current_session
    from extensions.analytics.roi_calculator import calculate_session_roi

    session = get_current_session()
    if not session:
        clear_hook_context()
        return None

    # End session tracking
    final_session = end_session(status=status)

    # Calculate ROI
    roi_result = calculate_session_roi(
        trace_id=session.trace_id,
        spec_id=session.spec_id,
        project_dir=session.project_dir,
        token_usage=session.get_token_usage_for_roi(),
    )

    # Clear hook context
    clear_hook_context()

    # Build summary
    summary = {
        "session": final_session.to_dict() if final_session else {},
        "roi": roi_result.to_dict(),
    }

    logger.info(
        f"Session ended: ROI={roi_result.roi_percentage:.1f}% "
        f"(value=${roi_result.total_value_usd:.2f}, cost=${roi_result.total_cost_usd:.4f})"
    )

    return summary
