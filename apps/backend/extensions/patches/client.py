"""
Client Patch
============

Patches core.client.create_client to add:
    - Automatic Langfuse trace creation
    - PostToolUse hooks for tracking
    - Trace ID propagation to subprocesses

Uses wrapt for safe monkey patching.
"""

import logging
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)

_client_patched = False


def patch_create_client() -> bool:
    """
    Apply patch to core.client.create_client.

    Returns:
        True if patch was applied, False otherwise.
    """
    global _client_patched

    if _client_patched:
        logger.debug("create_client already patched")
        return True

    try:
        import wrapt
    except ImportError:
        logger.error("wrapt not installed. Run: pip install wrapt")
        return False

    @wrapt.patch_function_wrapper('core.client', 'create_client')
    def create_client_wrapper(wrapped, instance, args, kwargs):
        """
        Wrapper for create_client that adds instrumentation.

        Args:
            wrapped: Original create_client function
            instance: None (module-level function)
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Instrumented ClaudeSDKClient
        """
        return _instrumented_create_client(wrapped, args, kwargs)

    _client_patched = True
    logger.info("Patch applied: core.client.create_client")
    return True


def _instrumented_create_client(wrapped: Callable, args: tuple, kwargs: dict) -> Any:
    """
    Instrumented version of create_client.

    Adds:
        1. Langfuse trace (if not already in context)
        2. Trace ID in env for subprocess propagation
        3. PostToolUse hooks for tracking
    """
    from extensions.analytics.tracer import (
        start_trace,
        get_current_trace_id,
        is_tracing_enabled,
    )

    # Extract agent_type for trace naming
    agent_type = kwargs.get('agent_type', 'unknown')

    # 1. Start trace if tracing is enabled
    trace_id = None
    if is_tracing_enabled():
        trace_id = start_trace(agent_type)
        logger.debug(f"Started trace for {agent_type}: {trace_id}")

    # 2. Inject trace_id into environment for subprocesses
    # Note: We set os.environ directly since create_client doesn't accept 'env' parameter
    if trace_id:
        os.environ['LANGFUSE_TRACE_ID'] = trace_id
        os.environ['AUTO_CLAUDE_INSTRUMENTED'] = '1'

    # 3. Note: Hooks are configured internally in create_client, not via kwargs
    # The create_client function doesn't accept a 'hooks' parameter
    # If tracking hooks are needed, they should be added to the client after creation

    # 4. Call original create_client
    client = wrapped(*args, **kwargs)

    # 5. Wrap client for lifecycle tracking
    if trace_id:
        client = _wrap_client_lifecycle(client, trace_id, agent_type)

    return client


def _merge_hooks(existing: dict, new: dict) -> dict:
    """
    Merge hook configurations.

    Args:
        existing: Existing hooks dict
        new: New hooks to add

    Returns:
        Merged hooks dict
    """
    merged = dict(existing)

    for event, matchers in new.items():
        if event in merged:
            # Append to existing matchers
            if isinstance(merged[event], list):
                merged[event] = merged[event] + matchers
            else:
                merged[event] = [merged[event]] + matchers
        else:
            merged[event] = matchers

    return merged


def _wrap_client_lifecycle(client: Any, trace_id: str, agent_type: str) -> Any:
    """
    Wrap client to track lifecycle events.

    Captures:
        - Session start
        - Session end
        - Artifacts created
        - Errors
    """
    from extensions.analytics.tracer import end_trace
    from extensions.analytics.collector import collect_session_artifacts

    # Store original methods
    original_aenter = client.__class__.__aenter__
    original_aexit = client.__class__.__aexit__

    async def wrapped_aenter(self):
        """Track session start."""
        logger.debug(f"Session starting: {agent_type}")
        return await original_aenter(self)

    async def wrapped_aexit(self, exc_type, exc_val, exc_tb):
        """Track session end and collect artifacts."""
        try:
            # Collect artifacts before closing
            await collect_session_artifacts(trace_id)
            logger.debug(f"Session artifacts collected for trace: {trace_id}")
        except Exception as e:
            logger.warning(f"Failed to collect artifacts: {e}")

        try:
            # End trace
            success = exc_type is None
            end_trace(trace_id, success=success)
            logger.debug(f"Trace ended: {trace_id}, success={success}")
        except Exception as e:
            logger.warning(f"Failed to end trace: {e}")

        # Call original
        return await original_aexit(self, exc_type, exc_val, exc_tb)

    # Apply wrappers (create new class to avoid affecting other instances)
    class InstrumentedClient(client.__class__):
        __aenter__ = wrapped_aenter
        __aexit__ = wrapped_aexit

    # Change instance's class
    client.__class__ = InstrumentedClient

    return client
