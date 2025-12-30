"""
Execution layer for agents and scripts in the roadmap generation process.
"""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Optional

from debug import debug, debug_detailed, debug_error, debug_success

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
    # Initialize Langfuse early (idempotent - safe to call multiple times)
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    trace_context = None
    _langfuse_init_result = False

# Import legacy feature tracker for backwards compatibility
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

        # Check Langfuse availability
        self.langfuse_enabled = LANGFUSE_AVAILABLE and is_langfuse_ready()
        debug(
            "roadmap_executor",
            "Langfuse integration status",
            langfuse_available=LANGFUSE_AVAILABLE,
            langfuse_ready=self.langfuse_enabled,
        )

        # Feature tracker for token usage (legacy - kept for backwards compatibility)
        self.tracker = None
        if TRACKING_AVAILABLE and is_tracking_enabled():
            db_path = str(self.project_dir / ".auto-claude" / "analytics.db")
            debug(
                "roadmap_executor",
                "Initializing legacy feature tracker",
                project_dir=str(self.project_dir),
                db_path=db_path,
                project_id=self.project_id,
                feature_type=self.feature_type,
            )
            try:
                self.tracker = create_feature_tracker(
                    project_id=self.project_id,
                    feature_type=self.feature_type,
                    db_path=db_path,
                    metadata={"model": self.model, "thinking_budget": self.thinking_budget}
                )
                debug("roadmap_executor", "Legacy feature tracker initialized", project_id=self.project_id)
            except Exception as e:
                debug_error("roadmap_executor", f"Failed to create legacy feature tracker: {e}")
                self.tracker = None
        else:
            debug(
                "roadmap_executor",
                "Legacy feature tracking disabled",
                tracking_available=TRACKING_AVAILABLE,
                tracking_enabled=is_tracking_enabled() if TRACKING_AVAILABLE else False,
            )

    def _generate_project_id(self) -> str:
        """Generate a unique project ID from the project directory."""
        # Use project directory name as a simple ID
        # Could be enhanced to use git remote or other identifiers
        return self.project_dir.name

    async def run_agent(
        self,
        prompt_file: str,
        additional_context: str = "",
    ) -> tuple[bool, str, str | None]:
        """Run an agent with the given prompt.

        Returns:
            Tuple of (success, response_text, langfuse_trace_id)
        """
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

        # Start legacy tracking session if tracker is available
        if self.tracker:
            try:
                self.tracker.update_metadata("prompt_file", prompt_file)
                await self.tracker.start_session()
                debug("roadmap_executor", "Legacy feature tracking session started")
            except Exception as e:
                debug_error("roadmap_executor", f"Failed to start legacy tracking session: {e}")

        # Derive agent type from prompt file name
        agent_type = prompt_file.replace(".md", "").replace("roadmap_", "")

        # Create Langfuse trace context wrapper
        async def _execute_agent() -> tuple[bool, str]:
            """Execute the agent (wrapped by trace_context if available)."""
            try:
                async with client:
                    debug("roadmap_executor", "Sending query to agent")
                    await client.query(prompt)

                    response_text = ""
                    total_input_tokens = 0
                    total_output_tokens = 0

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

                        # Extract usage for Langfuse logging
                        if msg_type == "ResultMessage" and hasattr(msg, "usage"):
                            usage = msg.usage
                            if hasattr(usage, "input_tokens"):
                                total_input_tokens = usage.input_tokens
                            if hasattr(usage, "output_tokens"):
                                total_output_tokens = usage.output_tokens

                    print()

                    # Log generation to Langfuse if enabled
                    if self.langfuse_enabled and LANGFUSE_AVAILABLE:
                        try:
                            log_generation_in_current_trace(
                                name=f"roadmap-{agent_type}",
                                model=self.model,
                                input_data=prompt[:500] + "..." if len(prompt) > 500 else prompt,
                                output_data=response_text[:1000] + "..." if len(response_text) > 1000 else response_text,
                                usage={
                                    "input": total_input_tokens,
                                    "output": total_output_tokens,
                                    "total": total_input_tokens + total_output_tokens,
                                },
                                metadata={
                                    "prompt_file": prompt_file,
                                    "thinking_budget": self.thinking_budget,
                                },
                            )
                            debug("roadmap_executor", "Logged generation to Langfuse")
                        except Exception as e:
                            debug_error("roadmap_executor", f"Failed to log to Langfuse: {e}")

                    debug_success(
                        "roadmap_executor",
                        f"Agent completed: {prompt_file}",
                        response_length=len(response_text),
                    )

                    # Finalize legacy tracking
                    if self.tracker:
                        try:
                            await self.tracker.finalize()
                            totals = self.tracker.get_totals()
                            debug(
                                "roadmap_executor",
                                "Legacy feature tracking finalized",
                                total_cost_usd=totals.get("total_cost_usd", 0),
                                total_input_tokens=totals.get("total_input_tokens", 0),
                                total_output_tokens=totals.get("total_output_tokens", 0),
                            )
                        except Exception as e:
                            debug_error("roadmap_executor", f"Failed to finalize legacy tracking: {e}")

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

        # Execute with Langfuse trace context if available
        if self.langfuse_enabled and trace_context:
            trace_name = f"roadmap-{self.project_id}-{agent_type}"
            # Truncate prompt for trace input
            trace_input = prompt[:2000] + "..." if len(prompt) > 2000 else prompt
            with trace_context(
                name=trace_name,
                project_id=self.project_id,  # Required for data isolation filtering
                agent_type=f"roadmap_{agent_type}",
                metadata={
                    "prompt_file": prompt_file,
                    "model": self.model,
                    "thinking_budget": self.thinking_budget,
                    "feature_type": self.feature_type,
                },
                tags=["roadmap", f"agent:{agent_type}"],
                input_data={"prompt": trace_input, "agent_type": agent_type},
            ) as ctx:
                langfuse_trace_id = ctx.trace_id if ctx else None
                if ctx:
                    debug("roadmap_executor", f"Created Langfuse trace: {langfuse_trace_id}")
                result = await _execute_agent()
                # Set trace output before exiting context
                if ctx and result:
                    success, response_text = result
                    trace_output = response_text[:3000] + "..." if len(response_text) > 3000 else response_text
                    ctx.set_output({"success": success, "response": trace_output})
                # Flush to ensure trace is sent
                if LANGFUSE_AVAILABLE:
                    flush_langfuse()
                # Unpack result and add trace_id
                if result:
                    return result[0], result[1], langfuse_trace_id
                return False, "", langfuse_trace_id
        else:
            # Run without Langfuse tracing
            result = await _execute_agent()
            if result:
                return result[0], result[1], None
            return False, "", None
