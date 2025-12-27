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

# Import feature tracker for token tracking
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
        self.tracker = None

        # Initialize feature tracker for token usage
        if TRACKING_AVAILABLE and is_tracking_enabled():
            project_id = self.project_dir.name
            db_path = str(self.project_dir / ".auto-claude" / "analytics.db")
            self.tracker = create_feature_tracker(
                project_id=project_id,
                feature_type=FEATURE_AI_ANALYZER,
                db_path=db_path,
                metadata={"model": self.DEFAULT_MODEL}
            )
            logger.info(f"[AI_ANALYZER] Feature tracker initialized for project: {project_id}")

        self._validate_oauth_token()

    def _validate_oauth_token(self) -> None:
        """Validate that an authentication token is available."""
        from core.auth import require_auth_token

        require_auth_token()  # Raises ValueError if no token found

    def _get_sdk_env(self) -> dict:
        """Get SDK environment variables for Azure Foundry support."""
        from core.auth import get_sdk_env_vars

        return get_sdk_env_vars()

    async def run_analysis_query(self, prompt: str) -> str:
        """
        Run a Claude query for analysis.

        Args:
            prompt: The analysis prompt

        Returns:
            Claude's response text
        """
        settings_file = self._create_settings_file()

        # Start tracking session if tracker is available
        if self.tracker:
            try:
                await self.tracker.start_session()
                logger.info("[AI_ANALYZER] Feature tracking session started")
            except Exception as e:
                logger.error(f"[AI_ANALYZER] Failed to start tracking session: {e}")

        try:
            client = self._create_client(settings_file)

            async with client:
                await client.query(prompt)
                result = await self._collect_response(client)

            # Finalize tracking
            if self.tracker:
                try:
                    await self.tracker.finalize()
                    logger.info("[AI_ANALYZER] Feature tracking session finalized")
                except Exception as e:
                    logger.error(f"[AI_ANALYZER] Failed to finalize tracking: {e}")

            return result

        except Exception as e:
            # Finalize tracking even on error
            if self.tracker:
                try:
                    await self.tracker.finalize()
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

    async def _collect_response(self, client: Any) -> str:
        """
        Collect text response from Claude client.

        Args:
            client: ClaudeSDKClient instance

        Returns:
            Collected response text
        """
        response_text = ""

        async for msg in client.receive_response():
            msg_type = type(msg).__name__

            # Track message for token usage
            if self.tracker:
                try:
                    await self.tracker.track_message(msg)
                except Exception as e:
                    logger.error(f"[AI_ANALYZER] Failed to track message: {e}")

            if msg_type == "AssistantMessage":
                for content in msg.content:
                    if hasattr(content, "text"):
                        response_text += content.text

        return response_text
