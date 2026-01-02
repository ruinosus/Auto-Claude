"""
Agent Runner
============

Handles the execution of AI agents for the spec creation pipeline.
"""

from pathlib import Path

# Configure safe encoding before any output (fixes Windows encoding errors)
from ui.capabilities import configure_safe_encoding

configure_safe_encoding()

from core.client import create_client
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from security.tool_input_validator import get_safe_tool_input
from task_logger import (
    LogEntryType,
    LogPhase,
    TaskLogger,
)

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


class AgentRunner:
    """Manages agent execution with logging and error handling."""

    def __init__(
        self,
        project_dir: Path,
        spec_dir: Path,
        model: str,
        task_logger: TaskLogger | None = None,
    ):
        """Initialize the agent runner.

        Args:
            project_dir: The project root directory
            spec_dir: The spec directory
            model: The model to use for agent execution
            task_logger: Optional task logger for tracking progress
        """
        self.project_dir = project_dir
        self.spec_dir = spec_dir
        self.model = model
        self.task_logger = task_logger

        # Check Langfuse availability
        self.langfuse_enabled = LANGFUSE_AVAILABLE and is_langfuse_ready()
        debug(
            "agent_runner",
            "Langfuse integration status",
            langfuse_available=LANGFUSE_AVAILABLE,
            langfuse_ready=self.langfuse_enabled,
        )

    async def run_agent(
        self,
        prompt_file: str,
        additional_context: str = "",
        interactive: bool = False,
        thinking_budget: int | None = None,
        prior_phase_summaries: str | None = None,
    ) -> tuple[bool, str, str | None]:
        """Run an agent with the given prompt.

        Args:
            prompt_file: The prompt file to use (relative to prompts directory)
            additional_context: Additional context to add to the prompt
            interactive: Whether to run in interactive mode
            thinking_budget: Token budget for extended thinking (None = disabled)
            prior_phase_summaries: Summaries from previous phases for context

        Returns:
            Tuple of (success, response_text, langfuse_trace_id)
        """
        debug_section("agent_runner", f"Spec Agent - {prompt_file}")
        debug(
            "agent_runner",
            "Running spec creation agent",
            prompt_file=prompt_file,
            spec_dir=str(self.spec_dir),
            model=self.model,
            interactive=interactive,
        )

        prompt_path = Path(__file__).parent.parent.parent / "prompts" / prompt_file

        if not prompt_path.exists():
            debug_error("agent_runner", f"Prompt file not found: {prompt_path}")
            return False, f"Prompt not found: {prompt_path}", None

        # Load prompt
        prompt = prompt_path.read_text()
        debug_detailed(
            "agent_runner",
            "Loaded prompt file",
            prompt_length=len(prompt),
        )

        # Add context
        prompt += f"\n\n---\n\n**Spec Directory**: {self.spec_dir}\n"
        prompt += f"**Project Directory**: {self.project_dir}\n"

        # Add summaries from previous phases (compaction)
        if prior_phase_summaries:
            prompt += f"\n{prior_phase_summaries}\n"
            debug_detailed(
                "agent_runner",
                "Added prior phase summaries",
                summaries_length=len(prior_phase_summaries),
            )

        if additional_context:
            prompt += f"\n{additional_context}\n"
            debug_detailed(
                "agent_runner",
                "Added additional context",
                context_length=len(additional_context),
            )

        # Create client with thinking budget
        debug(
            "agent_runner",
            "Creating Claude SDK client...",
            thinking_budget=thinking_budget,
        )
        client = create_client(
            self.project_dir,
            self.spec_dir,
            self.model,
            max_thinking_tokens=thinking_budget,
        )

        current_tool = None
        message_count = 0
        tool_count = 0

        # Derive phase name from prompt file
        phase_name = prompt_file.replace(".md", "").replace("spec_", "")
        spec_id = self.spec_dir.name
        trace_name = f"spec-{spec_id}-{phase_name}"

        # Create Langfuse trace context if available
        trace_ctx = None
        langfuse_ctx_obj = None
        langfuse_trace_id = None
        if self.langfuse_enabled and trace_context:
            # Derive project_id from project_dir
            project_id = self.project_dir.name if self.project_dir else None
            # Truncate prompt for trace input
            trace_input = prompt[:2000] + "..." if len(prompt) > 2000 else prompt
            trace_ctx = trace_context(
                name=trace_name,
                spec_id=spec_id,  # Required for spec-level filtering
                project_id=project_id,  # Required for data isolation filtering
                agent_type=f"spec_{phase_name}",
                metadata={
                    "prompt_file": prompt_file,
                    "model": self.model,
                    "thinking_budget": thinking_budget,
                    "interactive": interactive,
                },
                tags=["spec", f"phase:{phase_name}"],
                input_data={"prompt": trace_input, "phase": phase_name},
            )
            langfuse_ctx_obj = trace_ctx.__enter__()
            if langfuse_ctx_obj:
                langfuse_trace_id = langfuse_ctx_obj.trace_id
            debug("agent_runner", f"Langfuse trace created: {trace_name}", trace_id=langfuse_trace_id)

        try:
            async with client:
                debug("agent_runner", "Sending query to Claude SDK...")
                await client.query(prompt)
                debug_success("agent_runner", "Query sent successfully")

                response_text = ""
                total_input_tokens = 0
                total_output_tokens = 0

                debug("agent_runner", "Starting to receive response stream...")
                async for msg in client.receive_response():
                    msg_type = type(msg).__name__
                    message_count += 1
                    debug_detailed(
                        "agent_runner",
                        f"Received message #{message_count}",
                        msg_type=msg_type,
                    )

                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            block_type = type(block).__name__
                            if block_type == "TextBlock" and hasattr(block, "text"):
                                response_text += block.text
                                print(block.text, end="", flush=True)
                                if self.task_logger and block.text.strip():
                                    self.task_logger.log(
                                        block.text,
                                        LogEntryType.TEXT,
                                        LogPhase.PLANNING,
                                        print_to_console=False,
                                    )
                            elif block_type == "ToolUseBlock" and hasattr(
                                block, "name"
                            ):
                                tool_name = block.name
                                tool_count += 1

                                # Safely extract tool input (handles None, non-dict, etc.)
                                inp = get_safe_tool_input(block)
                                tool_input_display = self._extract_tool_input_display(
                                    inp
                                )

                                debug(
                                    "agent_runner",
                                    f"Tool call #{tool_count}: {tool_name}",
                                    tool_input=tool_input_display,
                                )

                                if self.task_logger:
                                    self.task_logger.tool_start(
                                        tool_name,
                                        tool_input_display,
                                        LogPhase.PLANNING,
                                        print_to_console=True,
                                    )
                                else:
                                    print(f"\n[Tool: {tool_name}]", flush=True)
                                current_tool = tool_name

                    elif msg_type == "UserMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            block_type = type(block).__name__
                            if block_type == "ToolResultBlock":
                                is_error = getattr(block, "is_error", False)
                                result_content = getattr(block, "content", "")
                                if is_error:
                                    debug_error(
                                        "agent_runner",
                                        f"Tool error: {current_tool}",
                                        error=str(result_content)[:200],
                                    )
                                else:
                                    debug_detailed(
                                        "agent_runner",
                                        f"Tool success: {current_tool}",
                                        result_length=len(str(result_content)),
                                    )
                                if self.task_logger and current_tool:
                                    detail_content = self._get_tool_detail_content(
                                        current_tool, result_content
                                    )
                                    self.task_logger.tool_end(
                                        current_tool,
                                        success=not is_error,
                                        detail=detail_content,
                                        phase=LogPhase.PLANNING,
                                    )
                                current_tool = None

                    # Extract usage for Langfuse
                    if msg_type == "ResultMessage" and hasattr(msg, "usage") and msg.usage:
                        usage = msg.usage
                        if hasattr(usage, "input_tokens"):
                            total_input_tokens = usage.input_tokens
                        if hasattr(usage, "output_tokens"):
                            total_output_tokens = usage.output_tokens

                print()

                # Log to Langfuse if enabled
                if self.langfuse_enabled and LANGFUSE_AVAILABLE:
                    try:
                        log_generation_in_current_trace(
                            name=f"spec-{phase_name}",
                            model=self.model,
                            input_data=prompt[:500] + "..." if len(prompt) > 500 else prompt,
                            output_data=response_text[:1000] + "..." if len(response_text) > 1000 else response_text,
                            usage={
                                "input": total_input_tokens,
                                "output": total_output_tokens,
                                "total": total_input_tokens + total_output_tokens,
                            },
                            metadata={"prompt_file": prompt_file, "tool_count": tool_count},
                        )
                        debug("agent_runner", "Logged generation to Langfuse")
                    except Exception as e:
                        debug_error("agent_runner", f"Failed to log to Langfuse: {e}")

                debug_success(
                    "agent_runner",
                    "Agent session completed successfully",
                    message_count=message_count,
                    tool_count=tool_count,
                    response_length=len(response_text),
                )

                # Finalize Langfuse trace
                if trace_ctx:
                    try:
                        # Set trace output before closing
                        if langfuse_ctx_obj:
                            # FULL content - NO truncation (Zero Truncation Policy)
                            langfuse_ctx_obj.set_output({
                                "response": response_text,
                                "message_count": message_count,
                                "tool_count": tool_count,
                            })
                        trace_ctx.__exit__(None, None, None)
                        flush_langfuse()
                        debug("agent_runner", "Langfuse trace finalized")
                    except Exception as e:
                        debug_error("agent_runner", f"Failed to finalize Langfuse: {e}")

                return True, response_text, langfuse_trace_id

        except Exception as e:
            debug_error(
                "agent_runner",
                f"Agent session error: {e}",
                exception_type=type(e).__name__,
            )
            if self.task_logger:
                self.task_logger.log_error(f"Agent error: {e}", LogPhase.PLANNING)
            # Still try to finalize Langfuse trace on error
            if trace_ctx:
                try:
                    if langfuse_ctx_obj:
                        langfuse_ctx_obj.set_output({"error": str(e)})
                    trace_ctx.__exit__(None, None, None)
                    flush_langfuse()
                except Exception:
                    pass
            return False, str(e), langfuse_trace_id

    @staticmethod
    def _extract_tool_input_display(inp: dict) -> str | None:
        """Extract meaningful tool input for display.

        Args:
            inp: The tool input dictionary

        Returns:
            A formatted string for display, or None
        """
        if not isinstance(inp, dict):
            return None

        if "pattern" in inp:
            return f"pattern: {inp['pattern']}"
        elif "file_path" in inp:
            fp = inp["file_path"]
            if len(fp) > 50:
                fp = "..." + fp[-47:]
            return fp
        elif "command" in inp:
            cmd = inp["command"]
            if len(cmd) > 50:
                cmd = cmd[:47] + "..."
            return cmd
        elif "path" in inp:
            return inp["path"]

        return None

    @staticmethod
    def _get_tool_detail_content(tool_name: str, result_content: str) -> str | None:
        """Get detail content for specific tools.

        Args:
            tool_name: The name of the tool
            result_content: The result content from the tool

        Returns:
            Detail content if relevant, otherwise None
        """
        if tool_name not in ("Read", "Grep", "Bash", "Edit", "Write"):
            return None

        result_str = str(result_content)
        if len(result_str) < 50000:
            return result_str

        return None
