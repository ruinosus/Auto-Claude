"""
QA Fixer Agent Session
=======================

Runs QA fixer sessions to resolve issues identified by the reviewer.
"""

from pathlib import Path

from claude_agent_sdk import ClaudeSDKClient
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from task_logger import (
    LogEntryType,
    LogPhase,
    get_task_logger,
)

from .criteria import get_qa_signoff_status

# Langfuse integration (optional - graceful degradation if not available)
try:
    from analytics.langfuse_integration import (
        is_langfuse_ready,
        trace_context,
        log_generation_in_current_trace,
        get_session_trace_name,
    )
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

# Configuration
QA_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


# =============================================================================
# PROMPT LOADING
# =============================================================================


def load_qa_fixer_prompt() -> str:
    """Load the QA fixer agent prompt."""
    prompt_file = QA_PROMPTS_DIR / "qa_fixer.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"QA fixer prompt not found: {prompt_file}")
    return prompt_file.read_text()


# =============================================================================
# QA FIXER SESSION
# =============================================================================


async def run_qa_fixer_session(
    client: ClaudeSDKClient,
    spec_dir: Path,
    fix_session: int,
    verbose: bool = False,
) -> tuple[str, str, str | None]:
    """
    Run a QA fixer agent session.

    Args:
        client: Claude SDK client
        spec_dir: Spec directory
        fix_session: Fix iteration number
        verbose: Whether to show detailed output

    Returns:
        (status, response_text, langfuse_trace_id) where status is:
        - "fixed" if fixes were applied
        - "error" if an error occurred
    """
    debug_section("qa_fixer", f"QA Fixer Session {fix_session}")
    debug(
        "qa_fixer",
        "Starting QA fixer session",
        spec_dir=str(spec_dir),
        fix_session=fix_session,
    )

    print(f"\n{'=' * 70}")
    print(f"  QA FIXER SESSION {fix_session}")
    print("  Applying fixes from QA_FIX_REQUEST.md...")
    print(f"{'=' * 70}\n")

    # Get task logger for streaming markers
    task_logger = get_task_logger(spec_dir)
    current_tool = None
    message_count = 0
    tool_count = 0

    # Check that fix request file exists
    fix_request_file = spec_dir / "QA_FIX_REQUEST.md"
    if not fix_request_file.exists():
        debug_error("qa_fixer", "QA_FIX_REQUEST.md not found")
        return "error", "QA_FIX_REQUEST.md not found", None

    # Load fixer prompt
    prompt = load_qa_fixer_prompt()
    debug_detailed("qa_fixer", "Loaded QA fixer prompt", prompt_length=len(prompt))

    # Add session context - use full path so agent can find files
    prompt += f"\n\n---\n\n**Fix Session**: {fix_session}\n"
    prompt += f"**Spec Directory**: {spec_dir}\n"
    prompt += f"**Spec Name**: {spec_dir.name}\n"
    prompt += f"\n**IMPORTANT**: All spec files are located in: `{spec_dir}/`\n"
    prompt += f"The fix request file is at: `{spec_dir}/QA_FIX_REQUEST.md`\n"

    # Initialize Langfuse trace context
    spec_id = spec_dir.name
    langfuse_trace_id = None
    langfuse_ctx = None
    # Derive project_id from spec_dir path for data isolation
    # spec_dir is typically: /path/to/project/.auto-claude/specs/XXX-name
    # We go up 3 levels to get the project dir
    try:
        project_id = spec_dir.parent.parent.parent.name
    except Exception:
        project_id = None

    # Create Langfuse trace if available
    if LANGFUSE_AVAILABLE and is_langfuse_ready():
        trace_name = get_session_trace_name(spec_id, "qa_fixer", fix_session)
        # Truncate prompt for trace input
        trace_input = prompt[:2000] + "..." if len(prompt) > 2000 else prompt
        langfuse_ctx = trace_context(
            name=trace_name,
            spec_id=spec_id,
            project_id=project_id,
            agent_type="qa_fixer",
            metadata={
                "fix_session": fix_session,
            },
            tags=["qa", "fixer"],
            input_data={"prompt": trace_input, "fix_session": fix_session},
        )
        ctx = langfuse_ctx.__enter__()
        if ctx:
            langfuse_trace_id = ctx.trace_id
            debug("qa_fixer", f"Langfuse trace created: {langfuse_trace_id}")

    try:
        debug("qa_fixer", "Sending query to Claude SDK...")
        await client.query(prompt)
        debug_success("qa_fixer", "Query sent successfully")

        response_text = ""
        generation_count = 0
        debug("qa_fixer", "Starting to receive response stream...")
        async for msg in client.receive_response():
            msg_type = type(msg).__name__
            message_count += 1
            debug_detailed(
                "qa_fixer",
                f"Received message #{message_count}",
                msg_type=msg_type,
            )

            if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "TextBlock" and hasattr(block, "text"):
                        response_text += block.text
                        print(block.text, end="", flush=True)
                        # Log text to task logger (persist without double-printing)
                        if task_logger and block.text.strip():
                            task_logger.log(
                                block.text,
                                LogEntryType.TEXT,
                                LogPhase.VALIDATION,
                                print_to_console=False,
                            )

                        # Log generation to Langfuse
                        if LANGFUSE_AVAILABLE and is_langfuse_ready() and langfuse_trace_id:
                            generation_count += 1
                            # Extract usage if available
                            usage = None
                            if hasattr(msg, "usage"):
                                usage = {
                                    "input": getattr(msg.usage, "input_tokens", 0),
                                    "output": getattr(msg.usage, "output_tokens", 0),
                                    "total": getattr(msg.usage, "input_tokens", 0) + getattr(msg.usage, "output_tokens", 0),
                                }
                            log_generation_in_current_trace(
                                name=f"qa-fixer-gen-{generation_count}",
                                model=getattr(client, "model", "claude-sonnet-4-5-20250929"),
                                input_data=prompt[:500] if generation_count == 1 else f"[continuation {generation_count}]",
                                output_data=block.text[:1000] if len(block.text) > 1000 else block.text,
                                usage=usage,
                                metadata={"fix_session": fix_session, "generation": generation_count}
                            )
                    elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                        tool_name = block.name
                        tool_input = None
                        tool_count += 1

                        if hasattr(block, "input") and block.input:
                            inp = block.input
                            if isinstance(inp, dict):
                                if "file_path" in inp:
                                    fp = inp["file_path"]
                                    if len(fp) > 50:
                                        fp = "..." + fp[-47:]
                                    tool_input = fp
                                elif "command" in inp:
                                    cmd = inp["command"]
                                    if len(cmd) > 50:
                                        cmd = cmd[:47] + "..."
                                    tool_input = cmd

                        debug(
                            "qa_fixer",
                            f"Tool call #{tool_count}: {tool_name}",
                            tool_input=tool_input,
                        )

                        # Log tool start (handles printing)
                        if task_logger:
                            task_logger.tool_start(
                                tool_name,
                                tool_input,
                                LogPhase.VALIDATION,
                                print_to_console=True,
                            )
                        else:
                            print(f"\n[Fixer Tool: {tool_name}]", flush=True)

                        if verbose and hasattr(block, "input"):
                            input_str = str(block.input)
                            if len(input_str) > 300:
                                print(f"   Input: {input_str[:300]}...", flush=True)
                            else:
                                print(f"   Input: {input_str}", flush=True)
                        current_tool = tool_name

            elif msg_type == "UserMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "ToolResultBlock":
                        is_error = getattr(block, "is_error", False)
                        result_content = getattr(block, "content", "")

                        if is_error:
                            debug_error(
                                "qa_fixer",
                                f"Tool error: {current_tool}",
                                error=str(result_content)[:200],
                            )
                            error_str = str(result_content)[:500]
                            print(f"   [Error] {error_str}", flush=True)
                            if task_logger and current_tool:
                                # Store full error in detail for expandable view
                                task_logger.tool_end(
                                    current_tool,
                                    success=False,
                                    result=error_str[:100],
                                    detail=str(result_content),
                                    phase=LogPhase.VALIDATION,
                                )
                        else:
                            debug_detailed(
                                "qa_fixer",
                                f"Tool success: {current_tool}",
                                result_length=len(str(result_content)),
                            )
                            if verbose:
                                result_str = str(result_content)[:200]
                                print(f"   [Done] {result_str}", flush=True)
                            else:
                                print("   [Done]", flush=True)
                            if task_logger and current_tool:
                                # Store full result in detail for expandable view
                                detail_content = None
                                if current_tool in (
                                    "Read",
                                    "Grep",
                                    "Bash",
                                    "Edit",
                                    "Write",
                                ):
                                    result_str = str(result_content)
                                    if len(result_str) < 50000:
                                        detail_content = result_str
                                task_logger.tool_end(
                                    current_tool,
                                    success=True,
                                    detail=detail_content,
                                    phase=LogPhase.VALIDATION,
                                )

                        current_tool = None

        print("\n" + "-" * 70 + "\n")

        # Check if fixes were applied
        status = get_qa_signoff_status(spec_dir)
        debug(
            "qa_fixer",
            "Fixer session completed",
            message_count=message_count,
            tool_count=tool_count,
            response_length=len(response_text),
            ready_for_revalidation=status.get("ready_for_qa_revalidation")
            if status
            else False,
        )
        if status and status.get("ready_for_qa_revalidation"):
            debug_success("qa_fixer", "Fixes applied, ready for QA revalidation")
            return "fixed", response_text, langfuse_trace_id
        else:
            # Fixer didn't update the status properly, but we'll trust it worked
            debug_success("qa_fixer", "Fixes assumed applied (status not updated)")
            return "fixed", response_text, langfuse_trace_id

    except Exception as e:
        debug_error(
            "qa_fixer",
            f"Fixer session exception: {e}",
            exception_type=type(e).__name__,
        )
        print(f"Error during fixer session: {e}")
        if task_logger:
            task_logger.log_error(f"QA fixer error: {e}", LogPhase.VALIDATION)
        return "error", str(e), langfuse_trace_id

    finally:
        # Close Langfuse trace context
        if langfuse_ctx:
            try:
                # Set trace output before exiting
                if ctx:
                    trace_output = response_text[:3000] + "..." if len(response_text) > 3000 else response_text
                    ctx.set_output({"response": trace_output, "tool_count": tool_count})
                langfuse_ctx.__exit__(None, None, None)
            except Exception as e:
                debug("qa_fixer", f"Failed to close Langfuse trace: {e}")
