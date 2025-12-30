"""
Claude SDK client wrapper for AI analysis.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

# Add backend path for imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

logger = logging.getLogger(__name__)

# Import Langfuse integration for tracing
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        trace_context,
        log_generation_in_current_trace,
        is_langfuse_ready,
        flush_langfuse,
    )
    LANGFUSE_AVAILABLE = True
    # Initialize Langfuse early (idempotent)
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    trace_context = None
    _langfuse_init_result = False

# Import legacy feature tracker for token tracking (backwards compatibility)
try:
    from analytics import (
        create_feature_tracker,
        FEATURE_AI_ANALYZER,
        is_tracking_enabled,
    )
    TRACKING_AVAILABLE = True
except ImportError as e:
    TRACKING_AVAILABLE = False

try:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False


class ClaudeAnalysisClient:
    """Wrapper for Claude SDK client with analysis-specific configuration."""

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
    ALLOWED_TOOLS = ["Read", "Glob", "Grep", "Skill"]  # Enable Skills for analysis
    MAX_TURNS = 50

    def __init__(self, project_dir: Path):
        """
        Initialize Claude client.

        Args:
            project_dir: Root directory of project being analyzed
        """
        if not CLAUDE_SDK_AVAILABLE:
            raise RuntimeError(
                "claude-agent-sdk not available. Install with: pip install claude-agent-sdk"
            )

        self.project_dir = project_dir
        self.project_id = self.project_dir.name
        self.tracker = None

        # Check Langfuse availability
        self.langfuse_enabled = LANGFUSE_AVAILABLE and is_langfuse_ready()
        logger.info(f"[AI_ANALYZER] Langfuse integration: available={LANGFUSE_AVAILABLE}, ready={self.langfuse_enabled}")

        # Initialize legacy feature tracker for token usage (backwards compatibility)
        if TRACKING_AVAILABLE and is_tracking_enabled():
            db_path = str(self.project_dir / ".auto-claude" / "analytics.db")
            self.tracker = create_feature_tracker(
                project_id=self.project_id,
                feature_type=FEATURE_AI_ANALYZER,
                db_path=db_path,
                metadata={"model": self.DEFAULT_MODEL}
            )
            logger.info(f"[AI_ANALYZER] Legacy feature tracker initialized for project: {self.project_id}")

        self._validate_oauth_token()

    def _validate_oauth_token(self) -> None:
        """Validate that an authentication token is available."""
        from core.auth import require_auth_token

        require_auth_token()  # Raises ValueError if no token found

    def _get_sdk_env(self) -> dict:
        """Get SDK environment variables for Azure Foundry support."""
        from core.auth import get_sdk_env_vars

        return get_sdk_env_vars()

    async def run_analysis_query(self, prompt: str, analyzer_name: str = "analysis") -> tuple[str, str | None]:
        """
        Run a Claude query for analysis.

        Args:
            prompt: The analysis prompt
            analyzer_name: Name of the analyzer for tracing

        Returns:
            Tuple of (response_text, langfuse_trace_id)
        """
        settings_file = self._create_settings_file()
        trace_name = f"ai-analyzer-{self.project_id}-{analyzer_name}"

        # Start legacy tracking session if tracker is available
        if self.tracker:
            try:
                await self.tracker.start_session()
                logger.info("[AI_ANALYZER] Legacy feature tracking session started")
            except Exception as e:
                logger.error(f"[AI_ANALYZER] Failed to start tracking session: {e}")

        # Create Langfuse trace context if available
        trace_ctx = None
        langfuse_ctx_obj = None
        langfuse_trace_id = None
        if self.langfuse_enabled and trace_context:
            # Truncate prompt for trace input
            trace_input = prompt[:2000] + "..." if len(prompt) > 2000 else prompt
            trace_ctx = trace_context(
                name=trace_name,
                project_id=self.project_id,  # Required for data isolation filtering
                agent_type=f"ai_analyzer_{analyzer_name}",
                metadata={
                    "analyzer_name": analyzer_name,
                    "model": self.DEFAULT_MODEL,
                },
                tags=["ai_analyzer", f"analyzer:{analyzer_name}"],
                input_data={"prompt": trace_input, "analyzer_name": analyzer_name},
            )
            langfuse_ctx_obj = trace_ctx.__enter__()
            if langfuse_ctx_obj:
                langfuse_trace_id = langfuse_ctx_obj.trace_id
            logger.info(f"[AI_ANALYZER] Langfuse trace created: {trace_name}, trace_id: {langfuse_trace_id}")

        try:
            client = self._create_client(settings_file)

            async with client:
                await client.query(prompt)
                result, total_input_tokens, total_output_tokens = await self._collect_response_with_usage(client)

            # Log to Langfuse if enabled
            if self.langfuse_enabled and LANGFUSE_AVAILABLE:
                try:
                    log_generation_in_current_trace(
                        name=f"ai-analyzer-{analyzer_name}",
                        model=self.DEFAULT_MODEL,
                        input_data=prompt[:500] + "..." if len(prompt) > 500 else prompt,
                        output_data=result[:1000] + "..." if len(result) > 1000 else result,
                        usage={
                            "input": total_input_tokens,
                            "output": total_output_tokens,
                            "total": total_input_tokens + total_output_tokens,
                        },
                        metadata={"analyzer_name": analyzer_name},
                    )
                    logger.info("[AI_ANALYZER] Logged generation to Langfuse")
                except Exception as e:
                    logger.error(f"[AI_ANALYZER] Failed to log to Langfuse: {e}")

            # Finalize legacy tracking
            if self.tracker:
                try:
                    await self.tracker.finalize()
                    logger.info("[AI_ANALYZER] Legacy feature tracking session finalized")
                except Exception as e:
                    logger.error(f"[AI_ANALYZER] Failed to finalize tracking: {e}")

            # Finalize Langfuse trace
            if trace_ctx:
                try:
                    # Set trace output before exiting
                    if langfuse_ctx_obj:
                        trace_output = result[:3000] + "..." if len(result) > 3000 else result
                        langfuse_ctx_obj.set_output({"response": trace_output})
                    trace_ctx.__exit__(None, None, None)
                    flush_langfuse()
                    logger.info("[AI_ANALYZER] Langfuse trace finalized")
                except Exception as e:
                    logger.error(f"[AI_ANALYZER] Failed to finalize Langfuse: {e}")

            return result, langfuse_trace_id

        except Exception as e:
            # Finalize tracking even on error
            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass
            # Finalize Langfuse trace on error
            if trace_ctx:
                try:
                    trace_ctx.__exit__(None, None, None)
                    flush_langfuse()
                except Exception:
                    pass
            raise

        finally:
            # Cleanup settings file
            if settings_file.exists():
                settings_file.unlink()

    def _create_settings_file(self) -> Path:
        """
        Create temporary security settings file.

        Returns:
            Path to settings file
        """
        settings = {
            "sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True},
            "permissions": {
                "defaultMode": "acceptEdits",
                "allow": [
                    "Read(./**)",
                    "Glob(./**)",
                    "Grep(./**)",
                ],
            },
        }

        settings_file = self.project_dir / ".claude_ai_analyzer_settings.json"
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)

        return settings_file

    def _create_client(self, settings_file: Path) -> Any:
        """
        Create configured Claude SDK client.

        Args:
            settings_file: Path to security settings file

        Returns:
            ClaudeSDKClient instance
        """
        system_prompt = (
            f"You are a senior software architect analyzing this codebase. "
            f"Your working directory is: {self.project_dir.resolve()}\n"
            f"Use Read, Grep, and Glob tools to analyze actual code. "
            f"Output your analysis as valid JSON only."
        )

        return ClaudeSDKClient(
            options=ClaudeAgentOptions(
                model=self.DEFAULT_MODEL,
                system_prompt=system_prompt,
                allowed_tools=self.ALLOWED_TOOLS,
                # Load Skills from user and project directories
                setting_sources=["user", "project"],
                max_turns=self.MAX_TURNS,
                cwd=str(self.project_dir.resolve()),
                settings=str(settings_file.resolve()),
                env=self._get_sdk_env(),  # Pass Azure Foundry env vars
            )
        )

    async def _collect_response_with_usage(self, client: Any) -> tuple[str, int, int]:
        """
        Collect text response and usage data from Claude client.

        Args:
            client: ClaudeSDKClient instance

        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """
        response_text = ""
        total_input_tokens = 0
        total_output_tokens = 0

        async for msg in client.receive_response():
            msg_type = type(msg).__name__

            # Track message for legacy token usage
            if self.tracker:
                try:
                    await self.tracker.track_message(msg)
                except Exception as e:
                    logger.error(f"[AI_ANALYZER] Failed to track message: {e}")

            if msg_type == "AssistantMessage":
                for content in msg.content:
                    if hasattr(content, "text"):
                        response_text += content.text

            # Extract usage for Langfuse
            if msg_type == "ResultMessage" and hasattr(msg, "usage") and msg.usage:
                usage = msg.usage
                if hasattr(usage, "input_tokens"):
                    total_input_tokens = usage.input_tokens
                if hasattr(usage, "output_tokens"):
                    total_output_tokens = usage.output_tokens

        return response_text, total_input_tokens, total_output_tokens
