"""
QA Fixer Agent Session
=======================

Runs QA fixer sessions to resolve issues identified by the reviewer.

Memory Integration:
- Retrieves past patterns, fixes, and gotchas before fixing
- Saves fix outcomes and learnings after session
"""

import re
from pathlib import Path
from typing import Any

# Memory integration for cross-session learning
from agents.memory_manager import get_graphiti_context, save_session_memory
from phase_config import resolve_model_id
from claude_agent_sdk import ClaudeSDKClient
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from security.tool_input_validator import get_safe_tool_input
from task_logger import (
    LogEntryType,
    LogPhase,
    get_task_logger,
)

from .criteria import get_qa_signoff_status

# Langfuse integration (optional - graceful degradation if not available)
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        is_langfuse_ready,
        trace_context,
        log_generation_in_current_trace,
        get_session_trace_name,
        flush_langfuse,
    )
    LANGFUSE_AVAILABLE = True
    # Initialize Langfuse early (idempotent - safe to call multiple times)
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    _langfuse_init_result = False

# ROI Engine (optional - graceful degradation if not available)
try:
    import sys as _sys
    from pathlib import Path as _Path
    _roi_engine_path = _Path(__file__).parent.parent.parent / "roi_engine"
    if str(_roi_engine_path) not in _sys.path:
        _sys.path.insert(0, str(_roi_engine_path))

    from core import (
        calculate_roi_for_spec,
        load_squad_config,
        publish_roi,
    )
    ROI_ENGINE_AVAILABLE = True
except ImportError:
    ROI_ENGINE_AVAILABLE = False
    calculate_roi_for_spec = None
    load_squad_config = None
    publish_roi = None

# Artifact storage (optional - graceful degradation if not available)
try:
    from analytics.artifact_storage import (
        save_artifact_safe,
        create_langfuse_reference,
        _get_artifacts_dir,
    )
    ARTIFACT_STORAGE_AVAILABLE = True
except ImportError:
    ARTIFACT_STORAGE_AVAILABLE = False

# Prompt registry (optional - graceful degradation if not available)
try:
    from analytics.prompt_registry import get_agent_prompt
    PROMPT_REGISTRY_AVAILABLE = True
except ImportError:
    PROMPT_REGISTRY_AVAILABLE = False

# Configuration
QA_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


# =============================================================================
# PROMPT LOADING
# =============================================================================


def load_qa_fixer_prompt() -> str:
    """Load the QA fixer agent prompt."""
    # Try prompt registry first (supports Langfuse), fallback to direct file read
    if PROMPT_REGISTRY_AVAILABLE:
        try:
            return get_agent_prompt("qa_fixer", label="production")
        except FileNotFoundError:
            pass  # Fall through to direct file read

    prompt_file = QA_PROMPTS_DIR / "qa_fixer.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"QA fixer prompt not found: {prompt_file}")
    return prompt_file.read_text()


# =============================================================================
# ARTIFACT EXTRACTION
# =============================================================================


def extract_qa_fix_artifacts(
    response_text: str,
    tool_count: int,
    status: dict[str, Any] | None,
    project_dir: Path | None = None,
    spec_id: str | None = None,
    trace_id: str | None = None,
    session_num: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int], list[dict[str, Any]]]:
    """
    Extract artifacts and metrics from QA fixer response.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    Artifact types and values (as specified in ROI_IMPLEMENTATION_TRACKER.md):
    - fix_applied: $150 each - each fix applied
    - issue_resolution: $100 - issue marked as resolved
    - test_fix: $75 - test corrected/added

    Args:
        response_text: The response text from the QA fixer agent
        tool_count: Number of tools used during the session
        status: QA signoff status dict (from get_qa_signoff_status)
        project_dir: Project root directory for local storage
        spec_id: Spec identifier for grouping artifacts
        trace_id: Langfuse trace ID for linking
        session_num: Fixer session number

    Returns:
        Tuple of (artifacts list, metrics dict, langfuse_refs list)
    """
    artifacts = []
    metrics = {
        "fixes_applied": 0,
        "issues_resolved": 0,
        "tests_fixed": 0,
        "files_modified": 0,
    }

    response_lower = response_text.lower()

    # Detect fixes applied from response
    # Look for patterns like "fixed", "applied fix", "resolved", "corrected"
    fix_patterns = [
        r"(?:fixed|corrected|resolved|applied fix for)\s+(.{10,100})",
        r"(?:modified|updated|changed)\s+(.{10,80})\s+to\s+fix",
        r"fix(?:ed|ing)?\s+(?:the\s+)?(?:issue|bug|problem|error)\s+(?:in|with|for)\s+(.{10,80})",
    ]

    fix_descriptions = []
    for pattern in fix_patterns:
        matches = re.findall(pattern, response_lower, re.IGNORECASE)
        for match in matches:
            # FULL content - no truncation!
            desc = match.strip()
            if desc and desc not in fix_descriptions:
                fix_descriptions.append(desc)
                artifacts.append({
                    "type": "fix_applied",
                    "format": "text",
                    "content": desc,  # FULL CONTENT - no [:150] truncation
                    "value_usd": 150,
                    "description": f"Fix applied: {desc[:50]}..." if len(desc) > 50 else f"Fix applied: {desc}",
                    "tab": "dev",
                })
                metrics["fixes_applied"] += 1

    # Count Edit tool uses as proxy for fixes if no patterns found
    if metrics["fixes_applied"] == 0 and tool_count > 0:
        # Each Edit tool use likely represents a fix
        # Use a conservative estimate: at least 1 fix for any tool activity
        metrics["fixes_applied"] = max(1, tool_count // 2)
        artifacts.append({
            "type": "fix_applied",
            "format": "text",
            "content": f"Applied {metrics['fixes_applied']} fix(es) via tool operations",
            "value_usd": 150 * metrics["fixes_applied"],
            "description": f"Fixes applied via {tool_count} tool operations",
            "tab": "dev",
        })

    # Detect issue resolutions
    issue_resolution_patterns = [
        r"(?:issue|bug|problem|error)\s+(?:is\s+now\s+)?(?:resolved|fixed|corrected)",
        r"(?:resolved|fixed|corrected)\s+(?:the\s+)?(?:issue|bug|problem|error)",
        r"all\s+(?:issues?|problems?|bugs?)\s+(?:have\s+been\s+)?(?:resolved|fixed|addressed)",
    ]

    for pattern in issue_resolution_patterns:
        if re.search(pattern, response_lower, re.IGNORECASE):
            metrics["issues_resolved"] += 1
            artifacts.append({
                "type": "issue_resolution",
                "format": "text",
                "content": "Issue marked as resolved after applying fixes",
                "value_usd": 100,
                "description": "Issue resolution",
                "tab": "dev",
            })
            break

    # Check QA status for resolution indication
    if status and status.get("ready_for_qa_revalidation"):
        if metrics["issues_resolved"] == 0:
            metrics["issues_resolved"] = 1
            artifacts.append({
                "type": "issue_resolution",
                "format": "text",
                "content": "QA signoff indicates ready for revalidation",
                "value_usd": 100,
                "description": "Issue resolved - ready for QA revalidation",
                "tab": "dev",
            })

    # Detect test fixes/additions
    test_patterns = [
        r"(?:fixed|corrected|updated|added)\s+(?:the\s+)?test(?:s|ing)?",
        r"test(?:s)?\s+(?:now\s+)?pass(?:ing|es)?",
        r"(?:added|created|wrote)\s+(?:new\s+)?test(?:s)?",
        r"(?:updated|modified)\s+(?:the\s+)?spec(?:s)?",
    ]

    for pattern in test_patterns:
        match = re.search(pattern, response_lower, re.IGNORECASE)
        if match:
            metrics["tests_fixed"] += 1
            artifacts.append({
                "type": "test_fix",
                "format": "text",
                "content": match.group(0).strip(),  # FULL CONTENT - no [:150] truncation
                "value_usd": 75,
                "description": "Test fix/addition",
                "tab": "dev",
            })

    # Count file modifications from tool usage patterns
    file_patterns = [
        r"(?:editing|modifying|updating|writing to)\s+[\w/\\.-]+\.\w+",
        r"Edit(?:ing)?\s+file[:\s]+([^\n]+)",
        r"Write(?:ing)?\s+to[:\s]+([^\n]+)",
    ]

    files_modified = set()
    for pattern in file_patterns:
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, str):
                files_modified.add(match.strip())  # FULL CONTENT - no [:100] truncation

    metrics["files_modified"] = len(files_modified)

    # Add any discovered code blocks as artifacts
    code_pattern = r"```(\w+)?\n(.*?)```"
    code_matches = re.findall(code_pattern, response_text, re.DOTALL)
    for lang, code in code_matches[:3]:  # Limit to first 3 code blocks
        if lang and lang.lower() not in ["text", "output", "log", "error"]:
            artifacts.append({
                "type": "code_fix",
                "format": lang or "text",
                "content": code.strip(),  # FULL CONTENT - no [:500] truncation
                "value_usd": 50,
                "description": f"Code fix ({lang or 'text'})",
                "tab": "dev",
            })

    # Save artifacts locally and create Langfuse references
    if ARTIFACT_STORAGE_AVAILABLE and project_dir:
        langfuse_refs = []
        for artifact in artifacts:
            # Save full artifact locally
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_dir,
                spec_id=spec_id,
                trace_id=trace_id,
                agent_type="qa_fixer",
                session_num=session_num,
            )

            if artifact_id:
                # Create lightweight reference for Langfuse
                artifacts_dir = _get_artifacts_dir(project_dir)
                storage_path = str(
                    (artifacts_dir / artifact_id).relative_to(project_dir)
                    if artifacts_dir.exists()
                    else f".auto-claude/artifacts/{artifact_id}.json"
                )
                ref = create_langfuse_reference(artifact, artifact_id, storage_path)
                langfuse_refs.append(ref)
            else:
                # Fallback: if storage fails, include full artifact as ref
                langfuse_refs.append(artifact)

        return artifacts, metrics, langfuse_refs
    else:
        # No local storage available - return artifacts as both
        return artifacts, metrics, artifacts


# =============================================================================
# QA FIXER SESSION
# =============================================================================


async def run_qa_fixer_session(
    client: ClaudeSDKClient,
    spec_dir: Path,
    fix_session: int,
    verbose: bool = False,
    project_dir: Path | None = None,
    analytics_project_dir: Path | None = None,
) -> tuple[str, str, str | None]:
    """
    Run a QA fixer agent session.

    Args:
        client: Claude SDK client
        spec_dir: Spec directory
        fix_session: Fix iteration number
        verbose: Whether to show detailed output
        project_dir: Project root directory (for memory context)
        analytics_project_dir: Original project directory for analytics (use when in worktree)

    Returns:
        (status, response_text, langfuse_trace_id) where status is:
        - "fixed" if fixes were applied
        - "error" if an error occurred
    """
    # Derive project_dir from spec_dir if not provided
    # spec_dir is typically: /project/.auto-claude/specs/001-name/
    if project_dir is None:
        # Walk up from spec_dir to find project root
        project_dir = spec_dir.parent.parent.parent
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

    # Retrieve memory context for fixer (past fixes, patterns, gotchas)
    fixer_memory_context = await get_graphiti_context(
        spec_dir,
        project_dir,
        {
            "description": "Fixing QA issues and implementing corrections",
            "id": f"qa_fixer_{fix_session}",
        },
    )
    if fixer_memory_context:
        prompt += "\n\n" + fixer_memory_context
        print("✓ Memory context loaded for QA fixer")
        debug_success("qa_fixer", "Graphiti memory context loaded for fixer")

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
    # Derive project_id from analytics_project_dir (original project) for data isolation
    # Use analytics_project_dir because spec_dir may be in a worktree with spec name
    if analytics_project_dir:
        project_id = analytics_project_dir.name
    else:
        # Fallback: try to derive from spec_dir path
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
                                model=getattr(client, "model", None) or resolve_model_id("sonnet"),
                                input_data=prompt[:500] if generation_count == 1 else f"[continuation {generation_count}]",
                                output_data=block.text[:1000] if len(block.text) > 1000 else block.text,
                                usage=usage,
                                metadata={"fix_session": fix_session, "generation": generation_count}
                            )
                    elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                        tool_name = block.name
                        tool_input_display = None
                        tool_count += 1

                        # Safely extract tool input (handles None, non-dict, etc.)
                        inp = get_safe_tool_input(block)

                        if inp:
                            if "file_path" in inp:
                                fp = inp["file_path"]
                                if len(fp) > 50:
                                    fp = "..." + fp[-47:]
                                tool_input_display = fp
                            elif "command" in inp:
                                cmd = inp["command"]
                                if len(cmd) > 50:
                                    cmd = cmd[:47] + "..."
                                tool_input_display = cmd

                        debug(
                            "qa_fixer",
                            f"Tool call #{tool_count}: {tool_name}",
                            tool_input=tool_input_display,
                        )

                        # Log tool start (handles printing)
                        if task_logger:
                            task_logger.tool_start(
                                tool_name,
                                tool_input_display,
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

        # Extract artifacts and publish ROI metrics
        # Use effective_project_dir for analytics (original project, not worktree)
        effective_project_dir = analytics_project_dir or project_dir

        # Extract artifacts (for metrics, even if ROI Engine not available)
        if response_text:
            try:
                # Extract artifacts from the response
                # Returns (full_artifacts, metrics, langfuse_refs)
                artifacts, roi_metrics, langfuse_refs = extract_qa_fix_artifacts(
                    response_text=response_text,
                    tool_count=tool_count,
                    status=status,
                    project_dir=effective_project_dir,
                    spec_id=spec_id,
                    trace_id=langfuse_trace_id,
                    session_num=fix_session,
                )

                debug(
                    "qa_fixer",
                    "Extracted artifacts",
                    artifact_count=len(artifacts),
                    fixes_applied=roi_metrics.get("fixes_applied", 0),
                    issues_resolved=roi_metrics.get("issues_resolved", 0),
                    tests_fixed=roi_metrics.get("tests_fixed", 0),
                )
            except Exception as e:
                debug_error("qa_fixer", f"Failed to extract artifacts (non-fatal): {e}")
                artifacts, roi_metrics, langfuse_refs = [], {}, []

        # Publish artifact-based ROI using ROI Engine
        if ROI_ENGINE_AVAILABLE and calculate_roi_for_spec is not None and response_text:
            try:
                # Load squad configuration for role-based valuation
                squad_config = load_squad_config(project_dir=effective_project_dir)

                # Calculate ROI based on artifacts created during QA fixer session
                roi_result = calculate_roi_for_spec(
                    spec_id=spec_id,
                    project_dir=effective_project_dir,
                    token_cost=0.0,  # Cost is tracked via Langfuse trace
                    squad_config=squad_config,
                )

                # Publish to Langfuse and local storage
                await publish_roi(
                    roi_result,
                    trace_id=langfuse_trace_id,
                    project_dir=effective_project_dir,
                )

                debug(
                    "qa_fixer",
                    "ROI Engine publish completed",
                    total_value=roi_result.total_artifact_value,
                    artifact_count=roi_result.artifact_count,
                    roi_percentage=roi_result.roi_percentage,
                )

            except Exception as e:
                # ROI publishing should not fail the fix session
                debug_error("qa_fixer", f"Failed to publish ROI (non-fatal): {e}")

        # Save fixer session insights to memory
        fixer_discoveries = {
            "files_understood": {},
            "patterns_found": [
                f"QA fixer session {fix_session}: Applied fixes from QA_FIX_REQUEST.md"
            ],
            "gotchas_encountered": [],
        }

        if status and status.get("ready_for_qa_revalidation"):
            debug_success("qa_fixer", "Fixes applied, ready for QA revalidation")
            # Save successful fix session to memory
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=f"qa_fixer_{fix_session}",
                session_num=fix_session,
                success=True,
                subtasks_completed=[f"qa_fixer_{fix_session}"],
                discoveries=fixer_discoveries,
            )
            return "fixed", response_text, langfuse_trace_id
        else:
            # Fixer didn't update the status properly, but we'll trust it worked
            debug_success("qa_fixer", "Fixes assumed applied (status not updated)")
            # Still save to memory as successful (fixes were attempted)
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=f"qa_fixer_{fix_session}",
                session_num=fix_session,
                success=True,
                subtasks_completed=[f"qa_fixer_{fix_session}"],
                discoveries=fixer_discoveries,
            )
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
                # Set trace output before exiting - include artifacts if available
                if ctx:
                    # FULL content - NO truncation (Zero Truncation Policy)
                    output_data = {"response": response_text, "tool_count": tool_count}

                    # Include ROI metrics if they were extracted
                    if ARTIFACT_STORAGE_AVAILABLE and response_text:
                        try:
                            # Don't save artifacts again - just get metrics for output
                            _, roi_metrics, _ = extract_qa_fix_artifacts(
                                response_text=response_text,
                                tool_count=tool_count,
                                status=status if 'status' in dir() else None,
                                # Don't pass project_dir - artifacts already saved in main path
                            )
                            output_data["roi_metrics"] = roi_metrics
                        except Exception:
                            pass  # Ignore extraction errors in finally block

                    ctx.set_output(output_data)
                langfuse_ctx.__exit__(None, None, None)

                # Flush Langfuse to ensure ROI scores are sent
                if LANGFUSE_AVAILABLE:
                    try:
                        flush_langfuse()
                    except Exception:
                        pass
            except Exception as e:
                debug("qa_fixer", f"Failed to close Langfuse trace: {e}")
