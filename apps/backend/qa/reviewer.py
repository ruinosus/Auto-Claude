"""
QA Reviewer Agent Session
==========================

Runs QA validation sessions to review implementation against
acceptance criteria.

Memory Integration:
- Retrieves past patterns, gotchas, and insights before QA session
- Saves QA findings (bugs, patterns, validation outcomes) after session
"""

import re
import time
from pathlib import Path
from typing import Any

# Memory integration for cross-session learning
from agents.memory_manager import get_graphiti_context, save_session_memory
from claude_agent_sdk import ClaudeSDKClient
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from prompts_pkg import get_qa_reviewer_prompt
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

# ROI publisher (optional - graceful degradation if not available)
try:
    from analytics.roi_publisher import publish_feature_roi
    ROI_PUBLISHER_AVAILABLE = True
except ImportError:
    ROI_PUBLISHER_AVAILABLE = False

# =============================================================================
# ARTIFACT EXTRACTION
# =============================================================================


def extract_qa_review_artifacts(
    response_text: str,
    qa_signoff: dict | None,
) -> list[dict[str, Any]]:
    """
    Extract QA review artifacts from response and signoff status.

    Artifacts extracted:
    - qa_finding ($100 each) - each finding in the report
    - qa_verdict ($50) - APPROVED/REJECTED decision
    - test_suggestion ($75) - suggestions for tests
    - acceptance_check ($25) - each criterion verified

    Args:
        response_text: The full response from the QA agent
        qa_signoff: The qa_signoff object from implementation_plan.json

    Returns:
        List of artifact dictionaries with type, content, value_usd, etc.
    """
    artifacts = []

    # Extract qa_verdict
    if qa_signoff:
        status = qa_signoff.get("status", "unknown")
        artifacts.append({
            "type": "qa_verdict",
            "format": "text",
            "content": status.upper(),
            "value_usd": 50,
            "description": f"QA verdict: {status.upper()}",
            "tab": "dev",
        })

        # Extract qa_findings from rejected issues
        issues_found = qa_signoff.get("issues_found", [])
        for i, issue in enumerate(issues_found):
            issue_title = issue.get("title", "Unknown issue")
            issue_type = issue.get("type", "unknown")
            issue_location = issue.get("location", "")
            fix_required = issue.get("fix_required", "")

            content = f"[{issue_type.upper()}] {issue_title}"
            if issue_location:
                content += f" at {issue_location}"
            if fix_required:
                content += f" - Fix: {fix_required}"

            artifacts.append({
                "type": "qa_finding",
                "format": "text",
                "content": content[:500],
                "value_usd": 100,
                "description": f"QA finding #{i+1}: {issue_type}",
                "severity": issue_type,
                "tab": "dev",
            })

        # Extract acceptance_check from tests_passed (approved case)
        tests_passed = qa_signoff.get("tests_passed", {})
        for test_type, result in tests_passed.items():
            artifacts.append({
                "type": "acceptance_check",
                "format": "text",
                "content": f"{test_type}: {result}",
                "value_usd": 25,
                "description": f"Test verification: {test_type}",
                "tab": "dev",
            })

    # Extract test_suggestions from response text using patterns
    # Look for test-related suggestions
    test_patterns = [
        r"(?:should|could|consider|recommend).*(?:add|write|create|implement).*(?:test|spec|assertion)",
        r"(?:test|spec) (?:for|to verify|to check|that covers)",
        r"(?:add|write|create) (?:a |an )?(?:unit |integration |e2e |end-to-end )?test",
        r"(?:missing|lack|need).*(?:test|coverage|spec)",
    ]

    sentences = re.split(r'[.!?\n]', response_text)
    test_suggestions_found = set()  # Use set to avoid duplicates

    for sentence in sentences:
        sentence_lower = sentence.lower().strip()
        if len(sentence_lower) < 20:
            continue

        for pattern in test_patterns:
            if re.search(pattern, sentence_lower, re.IGNORECASE):
                # Clean up the sentence
                clean_sentence = sentence.strip()[:300]
                if clean_sentence and clean_sentence not in test_suggestions_found:
                    test_suggestions_found.add(clean_sentence)
                    artifacts.append({
                        "type": "test_suggestion",
                        "format": "text",
                        "content": clean_sentence,
                        "value_usd": 75,
                        "description": "Test improvement suggestion",
                        "tab": "dev",
                    })
                break  # Only match once per sentence

    # Extract additional acceptance_checks from response text
    # Look for checkmarks or explicit verification statements
    check_patterns = [
        r"(?:\[x\]|\[X\]|✓|✔|PASS|passed)\s*(.+)",
        r"(?:verified|confirmed|checked|validated)\s*(?:that\s+)?(.+)",
        r"acceptance criteria.*(?:met|satisfied|fulfilled)",
    ]

    for sentence in sentences:
        for pattern in check_patterns:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                content = match.group(1) if match.lastindex else sentence
                content = content.strip()[:200]
                if content and len(content) > 10:
                    artifacts.append({
                        "type": "acceptance_check",
                        "format": "text",
                        "content": content,
                        "value_usd": 25,
                        "description": "Acceptance criteria check",
                        "tab": "dev",
                    })
                    break  # Only match once per sentence

    return artifacts


# =============================================================================
# QA REVIEWER SESSION
# =============================================================================


async def run_qa_agent_session(
    client: ClaudeSDKClient,
    project_dir: Path,
    spec_dir: Path,
    qa_session: int,
    max_iterations: int,
    verbose: bool = False,
    previous_error: dict | None = None,
    analytics_project_dir: Path | None = None,
) -> tuple[str, str, str | None]:
    """
    Run a QA reviewer agent session.

    Args:
        client: Claude SDK client
        project_dir: Project root directory (for capability detection)
        spec_dir: Spec directory
        qa_session: QA iteration number
        max_iterations: Maximum number of QA iterations
        verbose: Whether to show detailed output
        previous_error: Error context from previous iteration for self-correction
        analytics_project_dir: Original project directory for analytics (use when in worktree)

    Returns:
        (status, response_text, langfuse_trace_id) where status is:
        - "approved" if QA approves
        - "rejected" if QA finds issues
        - "error" if an error occurred
    """
    debug_section("qa_reviewer", f"QA Reviewer Session {qa_session}")
    debug(
        "qa_reviewer",
        "Starting QA reviewer session",
        spec_dir=str(spec_dir),
        qa_session=qa_session,
        max_iterations=max_iterations,
    )

    print(f"\n{'=' * 70}")
    print(f"  QA REVIEWER SESSION {qa_session}")
    print("  Validating all acceptance criteria...")
    print(f"{'=' * 70}\n")

    # Get task logger for streaming markers
    task_logger = get_task_logger(spec_dir)
    current_tool = None
    message_count = 0
    tool_count = 0

    # Load QA prompt with dynamically-injected project-specific MCP tools
    # This includes Electron validation for Electron apps, Puppeteer for web, etc.
    prompt = get_qa_reviewer_prompt(spec_dir, project_dir)
    debug_detailed(
        "qa_reviewer",
        "Loaded QA reviewer prompt with project-specific tools",
        prompt_length=len(prompt),
        project_dir=str(project_dir),
    )

    # Retrieve memory context for QA (past patterns, gotchas, validation insights)
    qa_memory_context = await get_graphiti_context(
        spec_dir,
        project_dir,
        {
            "description": "QA validation and acceptance criteria review",
            "id": f"qa_reviewer_{qa_session}",
        },
    )
    if qa_memory_context:
        prompt += "\n\n" + qa_memory_context
        print("✓ Memory context loaded for QA reviewer")
        debug_success("qa_reviewer", "Graphiti memory context loaded for QA")

    # Add session context
    prompt += f"\n\n---\n\n**QA Session**: {qa_session}\n"
    prompt += f"**Max Iterations**: {max_iterations}\n"

    # Add error context for self-correction if previous iteration failed
    if previous_error:
        debug(
            "qa_reviewer",
            "Adding error context for self-correction",
            error_type=previous_error.get("error_type"),
            consecutive_errors=previous_error.get("consecutive_errors"),
        )
        prompt += f"""

---

## ⚠️ CRITICAL: PREVIOUS ITERATION FAILED - SELF-CORRECTION REQUIRED

The previous QA session failed with the following error:

**Error**: {previous_error.get("error_message", "Unknown error")}
**Consecutive Failures**: {previous_error.get("consecutive_errors", 1)}

### What Went Wrong

You did NOT update the `implementation_plan.json` file with the required `qa_signoff` object.

### Required Action

After completing your QA review, you MUST:

1. **Read the current implementation_plan.json**:
   ```bash
   cat {spec_dir}/implementation_plan.json
   ```

2. **Update it with your qa_signoff** by editing the JSON file to add/update the `qa_signoff` field:

   If APPROVED:
   ```json
   {{
     "qa_signoff": {{
       "status": "approved",
       "timestamp": "[current ISO timestamp]",
       "qa_session": {qa_session},
       "report_file": "qa_report.md",
       "tests_passed": {{"unit": "X/Y", "integration": "X/Y", "e2e": "X/Y"}},
       "verified_by": "qa_agent"
     }}
   }}
   ```

   If REJECTED:
   ```json
   {{
     "qa_signoff": {{
       "status": "rejected",
       "timestamp": "[current ISO timestamp]",
       "qa_session": {qa_session},
       "issues_found": [
         {{"type": "critical", "title": "[issue]", "location": "[file:line]", "fix_required": "[description]"}}
       ],
       "fix_request_file": "QA_FIX_REQUEST.md"
     }}
   }}
   ```

3. **Use the Edit tool or Write tool** to update the file. The file path is:
   `{spec_dir}/implementation_plan.json`

### FAILURE TO DO THIS WILL CAUSE ANOTHER ERROR

This is attempt {previous_error.get("consecutive_errors", 1) + 1}. If you fail to update implementation_plan.json again, the QA process will be escalated to human review.

---

"""
        print(
            f"\n⚠️  Retry with self-correction context (attempt {previous_error.get('consecutive_errors', 1) + 1})"
        )

    # Initialize Langfuse trace context
    spec_id = spec_dir.name
    langfuse_trace_id = None
    langfuse_ctx = None
    # Derive project_id from analytics_project_dir (original project) for data isolation
    # Use analytics_project_dir because project_dir may be a worktree with spec name
    effective_project_dir = analytics_project_dir or project_dir
    project_id = effective_project_dir.name if effective_project_dir else None

    # Create Langfuse trace if available
    if LANGFUSE_AVAILABLE and is_langfuse_ready():
        trace_name = get_session_trace_name(spec_id, "qa_reviewer", qa_session)
        # Truncate prompt for trace input
        trace_input = prompt[:2000] + "..." if len(prompt) > 2000 else prompt
        langfuse_ctx = trace_context(
            name=trace_name,
            spec_id=spec_id,
            project_id=project_id,
            agent_type="qa_reviewer",
            metadata={
                "qa_session": qa_session,
                "max_iterations": max_iterations,
                "has_previous_error": previous_error is not None,
            },
            tags=["qa", "reviewer"],
            input_data={"prompt": trace_input, "qa_session": qa_session},
        )
        ctx = langfuse_ctx.__enter__()
        if ctx:
            langfuse_trace_id = ctx.trace_id
            debug("qa_reviewer", f"Langfuse trace created: {langfuse_trace_id}")

    try:
        start_time = time.time()
        debug("qa_reviewer", "Sending query to Claude SDK...")
        await client.query(prompt)
        debug_success("qa_reviewer", "Query sent successfully")

        response_text = ""
        generation_count = 0
        debug("qa_reviewer", "Starting to receive response stream...")
        async for msg in client.receive_response():
            msg_type = type(msg).__name__
            message_count += 1
            debug_detailed(
                "qa_reviewer",
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
                                name=f"qa-reviewer-gen-{generation_count}",
                                model=getattr(client, "model", "claude-sonnet-4-5-20250929"),
                                input_data=prompt[:500] if generation_count == 1 else f"[continuation {generation_count}]",
                                output_data=block.text[:1000] if len(block.text) > 1000 else block.text,
                                usage=usage,
                                metadata={"qa_session": qa_session, "generation": generation_count}
                            )
                    elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                        tool_name = block.name
                        tool_input_display = None
                        tool_count += 1

                        # Safely extract tool input (handles None, non-dict, etc.)
                        inp = get_safe_tool_input(block)

                        # Extract tool input for display
                        if inp:
                            if "file_path" in inp:
                                fp = inp["file_path"]
                                if len(fp) > 50:
                                    fp = "..." + fp[-47:]
                                tool_input_display = fp
                            elif "pattern" in inp:
                                tool_input_display = f"pattern: {inp['pattern']}"

                        debug(
                            "qa_reviewer",
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
                            print(f"\n[QA Tool: {tool_name}]", flush=True)

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
                                "qa_reviewer",
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
                                "qa_reviewer",
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

        # Check the QA result from implementation_plan.json
        status = get_qa_signoff_status(spec_dir)
        duration_seconds = time.time() - start_time
        debug(
            "qa_reviewer",
            "QA session completed",
            message_count=message_count,
            tool_count=tool_count,
            response_length=len(response_text),
            qa_status=status.get("status") if status else "unknown",
            duration_seconds=duration_seconds,
        )

        # Publish ROI metrics (wrapped in try/except to not break QA)
        if ROI_PUBLISHER_AVAILABLE and project_id:
            try:
                # Extract artifacts from the QA review
                artifacts = extract_qa_review_artifacts(response_text, status)

                # Count metrics from status and artifacts
                findings_count = len(status.get("issues_found", [])) if status else 0
                criteria_checked = len([a for a in artifacts if a["type"] == "acceptance_check"])
                suggestions_count = len([a for a in artifacts if a["type"] == "test_suggestion"])
                verdict = status.get("status", "unknown") if status else "unknown"
                qa_passed = verdict == "approved"

                # Estimate cost and tokens (simplified - actual tracking would come from SDK)
                # Estimate ~4 chars per token, rough estimate for ROI calculation
                estimated_tokens = len(response_text) // 4 + len(prompt) // 4
                estimated_cost = (estimated_tokens / 1000) * 0.003  # Rough cost estimate

                # Calculate total artifact value
                total_artifact_value = sum(a.get("value_usd", 0) for a in artifacts)

                # Publish ROI
                roi_result = await publish_feature_roi(
                    feature_type="qa_reviewer",
                    project_id=project_id,
                    cost_usd=estimated_cost,
                    tokens=estimated_tokens,
                    metrics={
                        "qa_attempts": qa_session,
                        "qa_passed": qa_passed,
                        "findings_count": findings_count,
                        "criteria_checked": criteria_checked,
                        "suggestions_count": suggestions_count,
                        "verdict": verdict,
                        "tool_count": tool_count,
                        "artifacts_count": len(artifacts),
                        "artifact_value_usd": total_artifact_value,
                    },
                    duration_seconds=duration_seconds,
                    model=getattr(client, "model", "claude-sonnet-4-5-20250929"),
                    spec_id=spec_id,
                    trace_id=langfuse_trace_id,
                )

                debug(
                    "qa_reviewer",
                    "ROI published",
                    trace_id=langfuse_trace_id,
                    artifacts_count=len(artifacts),
                    artifact_value=total_artifact_value,
                    roi_percentage=roi_result.get("roi_percentage", 0),
                )

            except Exception as e:
                # ROI publishing should never break QA
                debug_error("qa_reviewer", f"Failed to publish ROI (non-fatal): {e}")

        # Save QA session insights to memory
        qa_discoveries = {
            "files_understood": {},
            "patterns_found": [],
            "gotchas_encountered": [],
        }

        if status and status.get("status") == "approved":
            debug_success("qa_reviewer", "QA APPROVED")
            qa_discoveries["patterns_found"].append(
                f"QA session {qa_session}: All acceptance criteria validated successfully"
            )
            # Save successful QA session to memory
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=f"qa_reviewer_{qa_session}",
                session_num=qa_session,
                success=True,
                subtasks_completed=[f"qa_reviewer_{qa_session}"],
                discoveries=qa_discoveries,
            )
            return "approved", response_text, langfuse_trace_id
        elif status and status.get("status") == "rejected":
            debug_error("qa_reviewer", "QA REJECTED")
            # Extract issues found for memory
            issues = status.get("issues_found", [])
            for issue in issues:
                qa_discoveries["gotchas_encountered"].append(
                    f"QA Issue ({issue.get('type', 'unknown')}): {issue.get('title', 'No title')} at {issue.get('location', 'unknown')}"
                )
            # Save rejected QA session to memory (learning from failures)
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=f"qa_reviewer_{qa_session}",
                session_num=qa_session,
                success=False,
                subtasks_completed=[],
                discoveries=qa_discoveries,
            )
            return "rejected", response_text, langfuse_trace_id
        else:
            # Agent didn't update the status properly - provide detailed error
            debug_error(
                "qa_reviewer",
                "QA agent did not update implementation_plan.json",
                message_count=message_count,
                tool_count=tool_count,
                response_preview=response_text[:500] if response_text else "empty",
            )

            # Build informative error message for feedback loop
            error_details = []
            if message_count == 0:
                error_details.append("No messages received from agent")
            if tool_count == 0:
                error_details.append("No tools were used by agent")
            if not response_text:
                error_details.append("Agent produced no output")

            error_msg = "QA agent did not update implementation_plan.json"
            if error_details:
                error_msg += f" ({'; '.join(error_details)})"

            return "error", error_msg, langfuse_trace_id

    except Exception as e:
        debug_error(
            "qa_reviewer",
            f"QA session exception: {e}",
            exception_type=type(e).__name__,
        )
        print(f"Error during QA session: {e}")
        if task_logger:
            task_logger.log_error(f"QA session error: {e}", LogPhase.VALIDATION)
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
                debug("qa_reviewer", f"Failed to close Langfuse trace: {e}")
