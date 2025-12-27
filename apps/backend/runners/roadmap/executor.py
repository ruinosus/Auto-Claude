"""
Execution layer for agents and scripts in the roadmap generation process.
"""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Optional

from debug import debug, debug_detailed, debug_error, debug_success

# Import feature tracker for token tracking
try:
    from analytics import (
        create_feature_tracker,
        FEATURE_ROADMAP,
        is_tracking_enabled,
    )
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False


class ScriptExecutor:
    """Executes Python scripts with proper error handling and output capture."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        # Go up from roadmap/ -> runners/ -> auto-claude/
        self.scripts_base_dir = Path(__file__).parent.parent.parent

    def run_script(self, script: str, args: list[str]) -> tuple[bool, str]:
        """Run a Python script and return (success, output)."""
        script_path = self.scripts_base_dir / script

        debug_detailed(
            "roadmap_executor",
            f"Running script: {script}",
            script_path=str(script_path),
            args=args,
        )

        if not script_path.exists():
            debug_error("roadmap_executor", f"Script not found: {script_path}")
            return False, f"Script not found: {script_path}"

        cmd = [sys.executable, str(script_path)] + args

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                debug_success("roadmap_executor", f"Script completed: {script}")
                return True, result.stdout
            else:
                debug_error(
                    "roadmap_executor",
                    f"Script failed: {script}",
                    returncode=result.returncode,
                    stderr=result.stderr[:500] if result.stderr else None,
                )
                return False, result.stderr or result.stdout

        except subprocess.TimeoutExpired:
            debug_error("roadmap_executor", f"Script timed out: {script}")
            return False, "Script timed out"
        except Exception as e:
            debug_error("roadmap_executor", f"Script exception: {script}", error=str(e))
            return False, str(e)


class AgentExecutor:
    """Executes Claude AI agents with specific prompts."""

    def __init__(
        self,
        project_dir: Path,
        output_dir: Path,
        model: str,
        create_client_func,
        thinking_budget: int | None = None,
        feature_type: str = FEATURE_ROADMAP if TRACKING_AVAILABLE else "roadmap",
    ):
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.model = model
        self.create_client = create_client_func
        self.thinking_budget = thinking_budget
        self.feature_type = feature_type
        # Go up from roadmap/ -> runners/ -> auto-claude/prompts/
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"

        # Generate a project ID from the project directory
        self.project_id = self._generate_project_id()

        # Feature tracker for token usage
        self.tracker = None
        if TRACKING_AVAILABLE and is_tracking_enabled():
            db_path = str(self.project_dir / ".auto-claude" / "analytics.db")
            self.tracker = create_feature_tracker(
                project_id=self.project_id,
                feature_type=self.feature_type,
                db_path=db_path,
                metadata={"model": self.model, "thinking_budget": self.thinking_budget}
            )
            debug("roadmap_executor", "Feature tracker initialized", project_id=self.project_id)

    def _generate_project_id(self) -> str:
        """Generate a unique project ID from the project directory."""
        # Use project directory name as a simple ID
        # Could be enhanced to use git remote or other identifiers
        return self.project_dir.name

    async def run_agent(
        self,
        prompt_file: str,
        additional_context: str = "",
    ) -> tuple[bool, str]:
        """Run an agent with the given prompt."""
        prompt_path = self.prompts_dir / prompt_file

        debug_detailed(
            "roadmap_executor",
            f"Running agent with prompt: {prompt_file}",
            prompt_path=str(prompt_path),
            model=self.model,
        )

        if not prompt_path.exists():
            debug_error("roadmap_executor", f"Prompt file not found: {prompt_path}")
            return False, f"Prompt not found: {prompt_path}"

        # Load prompt
        prompt = prompt_path.read_text()
        debug_detailed(
            "roadmap_executor", "Loaded prompt file", prompt_length=len(prompt)
        )

        # Add context
        prompt += f"\n\n---\n\n**Output Directory**: {self.output_dir}\n"
        prompt += f"**Project Directory**: {self.project_dir}\n"

        if additional_context:
            prompt += f"\n{additional_context}\n"
            debug_detailed(
                "roadmap_executor",
                "Added additional context",
                context_length=len(additional_context),
            )

        # Create client with thinking budget
        debug(
            "roadmap_executor",
            "Creating Claude client",
            project_dir=str(self.project_dir),
            model=self.model,
            thinking_budget=self.thinking_budget,
        )
        client = self.create_client(
            self.project_dir,
            self.output_dir,
            self.model,
            max_thinking_tokens=self.thinking_budget,
        )

        # Start tracking session if tracker is available
        if self.tracker:
            try:
                self.tracker.update_metadata("prompt_file", prompt_file)
                await self.tracker.start_session()
                debug("roadmap_executor", "Feature tracking session started")
            except Exception as e:
                debug_error("roadmap_executor", f"Failed to start tracking session: {e}")

        try:
            async with client:
                debug("roadmap_executor", "Sending query to agent")
                await client.query(prompt)

                response_text = ""
                async for msg in client.receive_response():
                    msg_type = type(msg).__name__

                    # Track message usage if tracker is available
                    if self.tracker and msg_type == "AssistantMessage":
                        try:
                            await self.tracker.track_message(msg)
                        except Exception as e:
                            debug_error("roadmap_executor", f"Failed to track message: {e}")

                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            block_type = type(block).__name__
                            if block_type == "TextBlock" and hasattr(block, "text"):
                                response_text += block.text
                                print(block.text, end="", flush=True)
                            elif block_type == "ToolUseBlock" and hasattr(
                                block, "name"
                            ):
                                debug_detailed(
                                    "roadmap_executor", f"Tool called: {block.name}"
                                )
                                print(f"\n[Tool: {block.name}]", flush=True)

                    # Track result message for final totals
                    if self.tracker and msg_type == "ResultMessage":
                        try:
                            await self.tracker.track_message(msg)
                        except Exception as e:
                            debug_error("roadmap_executor", f"Failed to track result: {e}")

                print()
                debug_success(
                    "roadmap_executor",
                    f"Agent completed: {prompt_file}",
                    response_length=len(response_text),
                )

                # Finalize tracking
                if self.tracker:
                    try:
                        await self.tracker.finalize()
                        totals = self.tracker.get_totals()
                        debug(
                            "roadmap_executor",
                            "Feature tracking finalized",
                            total_cost_usd=totals.get("total_cost_usd", 0),
                            total_input_tokens=totals.get("total_input_tokens", 0),
                            total_output_tokens=totals.get("total_output_tokens", 0),
                        )
                    except Exception as e:
                        debug_error("roadmap_executor", f"Failed to finalize tracking: {e}")

                return True, response_text

        except Exception as e:
            debug_error(
                "roadmap_executor", f"Agent failed: {prompt_file}", error=str(e)
            )
            # Still try to finalize tracking on error
            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass
            return False, str(e)
