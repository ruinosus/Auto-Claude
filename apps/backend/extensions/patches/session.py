"""
Session Patch
=============

Patches agents.session.run_agent_session to add:
    - Session-level tracking
    - Response collection for ROI calculation
    - Error handling with trace context

Uses wrapt for safe monkey patching.
"""

import logging
from typing import Any, Callable, Tuple

logger = logging.getLogger(__name__)

_session_patched = False


def patch_run_agent_session() -> bool:
    """
    Apply patch to agents.session.run_agent_session.

    Returns:
        True if patch was applied, False otherwise.
    """
    global _session_patched

    if _session_patched:
        logger.debug("run_agent_session already patched")
        return True

    try:
        import wrapt
    except ImportError:
        logger.error("wrapt not installed. Run: pip install wrapt")
        return False

    @wrapt.patch_function_wrapper('agents.session', 'run_agent_session')
    def run_agent_session_wrapper(wrapped, instance, args, kwargs):
        """
        Wrapper for run_agent_session that adds instrumentation.
        """
        return _instrumented_run_agent_session(wrapped, args, kwargs)

    _session_patched = True
    logger.info("Patch applied: agents.session.run_agent_session")
    return True


async def _instrumented_run_agent_session(
    wrapped: Callable,
    args: tuple,
    kwargs: dict
) -> Tuple[str, str, str]:
    """
    Instrumented version of run_agent_session.

    Adds:
        1. Session start/end tracking
        2. Response metrics collection
        3. Error context
    """
    from extensions.analytics.tracer import (
        get_current_trace_id,
        record_session_metrics,
    )

    trace_id = get_current_trace_id()
    agent_type = kwargs.get('agent_type', 'unknown')

    logger.debug(f"Session starting: {agent_type}, trace: {trace_id}")

    try:
        # Call original
        result = await wrapped(*args, **kwargs)

        # Unpack result: (status, response_text, trace_id)
        if isinstance(result, tuple) and len(result) >= 2:
            status, response_text = result[0], result[1]
            returned_trace_id = result[2] if len(result) > 2 else None

            # Record metrics
            await record_session_metrics(
                trace_id=trace_id or returned_trace_id,
                agent_type=agent_type,
                status=status,
                response_length=len(response_text) if response_text else 0,
                success=status == "completed",
            )

        return result

    except Exception as e:
        # Record error
        await record_session_metrics(
            trace_id=trace_id,
            agent_type=agent_type,
            status="error",
            response_length=0,
            success=False,
            error=str(e),
        )
        raise
