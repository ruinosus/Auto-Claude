"""
Claude Client
=============

Claude integration for AI-based conflict resolution.

This module provides the factory function for creating an AIResolver
configured to use Claude via the Agent SDK.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Langfuse integration for tracing
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        trace_context,
        log_generation_in_current_trace,
        is_langfuse_ready,
        flush_langfuse,
    )
    LANGFUSE_AVAILABLE = True
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    trace_context = None
    _langfuse_init_result = False

# Legacy analytics tracking (backwards compatibility)
try:
    from analytics import (
        create_feature_tracker,
        FEATURE_INSIGHTS,  # Use INSIGHTS for merge resolution
        is_tracking_enabled,
    )
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False

if TYPE_CHECKING:
    from .resolver import AIResolver

logger = logging.getLogger(__name__)


def create_claude_resolver(project_dir: Path | None = None) -> AIResolver:
    """
    Create an AIResolver configured to use Claude via the Agent SDK.

    Uses the same OAuth token pattern as the rest of the auto-claude framework.

    Args:
        project_dir: Project directory for analytics tracking. If not provided,
                    falls back to current working directory.

    Returns:
        Configured AIResolver instance
    """
    # Import here to avoid circular dependency
    from core.auth import ensure_claude_code_oauth_token, get_auth_token, get_sdk_env_vars

    from .resolver import AIResolver

    if not get_auth_token():
        logger.warning("No authentication token found, AI resolution unavailable")
        return AIResolver()

    # Ensure SDK can find the token
    ensure_claude_code_oauth_token()

    try:
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
    except ImportError:
        logger.warning("claude_agent_sdk not installed, AI resolution unavailable")
        return AIResolver()

    def call_claude(system: str, user: str) -> str:
        """Call Claude using the Agent SDK for merge resolution."""
        sdk_env = get_sdk_env_vars()  # Capture env vars in closure

        async def _run_merge() -> str:
            # Create a minimal client for merge resolution
            client = ClaudeSDKClient(
                options=ClaudeAgentOptions(
                    model="sonnet",
                    system_prompt=system,
                    allowed_tools=[],  # No tools needed for merge
                    max_turns=1,
                    env=sdk_env,  # Pass Azure Foundry env vars
                )
            )

            # Use project_dir if provided, otherwise fall back to cwd
            effective_project_dir = project_dir or Path.cwd()
            project_id = effective_project_dir.name

            # Initialize legacy tracker for this merge resolution
            tracker = None
            if TRACKING_AVAILABLE and is_tracking_enabled():
                try:
                    db_path = str(effective_project_dir / ".auto-claude" / "analytics.db")
                    tracker = create_feature_tracker(
                        project_id=project_id,
                        feature_type=FEATURE_INSIGHTS,
                        db_path=db_path,
                        metadata={"model": "sonnet", "operation": "merge_resolution"}
                    )
                except Exception:
                    tracker = None

            # Check Langfuse availability
            use_langfuse = LANGFUSE_AVAILABLE and is_langfuse_ready()
            trace_ctx = None
            langfuse_ctx_obj = None
            if use_langfuse and trace_context:
                # Truncate user prompt for trace input
                trace_input = user[:2000] + "..." if len(user) > 2000 else user
                trace_ctx = trace_context(
                    name=f"merge-resolver-{project_id}",
                    project_id=project_id,  # Required for data isolation filtering
                    agent_type="merge_resolver",
                    metadata={
                        "model": "sonnet",
                        "operation": "merge_resolution",
                    },
                    tags=["merge", "conflict_resolution"],
                    input_data={"prompt": trace_input, "operation": "merge_resolution"},
                )
                langfuse_ctx_obj = trace_ctx.__enter__()
                logger.info(f"Langfuse trace created for merge resolution")

            try:
                # Start legacy tracking session
                if tracker:
                    try:
                        await tracker.start_session()
                    except Exception:
                        pass

                # Use async context manager to handle connect/disconnect
                # This is the standard pattern used throughout the codebase
                async with client:
                    await client.query(user)

                    response_text = ""
                    total_input_tokens = 0
                    total_output_tokens = 0

                    async for msg in client.receive_response():
                        msg_type = type(msg).__name__

                        # Track message for legacy analytics
                        if tracker and msg_type in ("AssistantMessage", "ResultMessage"):
                            try:
                                await tracker.track_message(msg)
                            except Exception:
                                pass

                        if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                            for block in msg.content:
                                if hasattr(block, "text"):
                                    response_text += block.text

                        # Extract usage for Langfuse
                        if msg_type == "ResultMessage" and hasattr(msg, "usage") and msg.usage:
                            usage = msg.usage
                            if hasattr(usage, "input_tokens"):
                                total_input_tokens = usage.input_tokens
                            if hasattr(usage, "output_tokens"):
                                total_output_tokens = usage.output_tokens

                    # Log to Langfuse if enabled
                    if use_langfuse and LANGFUSE_AVAILABLE:
                        try:
                            log_generation_in_current_trace(
                                name="merge-resolution",
                                model="sonnet",
                                input_data=user[:500] + "..." if len(user) > 500 else user,
                                output_data=response_text[:1000] + "..." if len(response_text) > 1000 else response_text,
                                usage={
                                    "input": total_input_tokens,
                                    "output": total_output_tokens,
                                    "total": total_input_tokens + total_output_tokens,
                                },
                                metadata={"operation": "merge_resolution"},
                            )
                        except Exception:
                            pass

                    # Finalize legacy tracking
                    if tracker:
                        try:
                            await tracker.finalize()
                        except Exception:
                            pass

                    # Finalize Langfuse trace
                    if trace_ctx:
                        try:
                            # Set trace output before exiting
                            if langfuse_ctx_obj:
                                trace_output = response_text[:3000] + "..." if len(response_text) > 3000 else response_text
                                langfuse_ctx_obj.set_output({"response": trace_output})
                            trace_ctx.__exit__(None, None, None)
                            flush_langfuse()
                        except Exception:
                            pass

                    logger.info(f"AI merge response: {len(response_text)} chars")
                    return response_text

            except Exception as e:
                # Finalize tracking on error
                if tracker:
                    try:
                        await tracker.finalize()
                    except Exception:
                        pass
                # Finalize Langfuse on error
                if trace_ctx:
                    try:
                        trace_ctx.__exit__(None, None, None)
                        flush_langfuse()
                    except Exception:
                        pass
                logger.error(f"Claude SDK call failed: {e}")
                print(f"    [ERROR] Claude SDK error: {e}", file=sys.stderr)
                return ""

        try:
            return asyncio.run(_run_merge())
        except Exception as e:
            logger.error(f"asyncio.run failed: {e}")
            print(f"    [ERROR] asyncio error: {e}", file=sys.stderr)
            return ""

    logger.info("Using Claude Agent SDK for merge resolution")
    return AIResolver(ai_call_fn=call_claude)
