"""
Agent Session Management
========================

Handles running agent sessions and post-session processing including
memory updates, recovery tracking, and Linear integration.
"""

import logging
from pathlib import Path
from typing import Optional

from claude_agent_sdk import ClaudeSDKClient
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from insight_extractor import extract_session_insights
from linear_updater import (
    linear_subtask_completed,
    linear_subtask_failed,
)
from progress import (
    count_subtasks_detailed,
    is_build_complete,
)
from recovery import RecoveryManager
from security.tool_input_validator import get_safe_tool_input
from task_logger import (
    LogEntryType,
    LogPhase,
    get_task_logger,
)
from ui import (
    StatusManager,
    muted,
    print_key_value,
    print_status,
)

from .memory_manager import save_session_memory
from .utils import (
    find_subtask_in_plan,
    get_commit_count,
    get_latest_commit,
    load_implementation_plan,
    sync_plan_to_source,
)

# Analytics tracking (optional - graceful degradation if not available)
try:
    from analytics import UsageTracker, get_analytics_storage, is_tracking_enabled
    from analytics.roi_tracker import create_roi_tracker, ROITracker
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

# ROI Publisher for feature-level ROI tracking
try:
    from analytics.roi_publisher import publish_feature_roi
    from analytics.roi_score_publisher import get_git_diff_stats
    ROI_PUBLISHER_AVAILABLE = True
except ImportError:
    ROI_PUBLISHER_AVAILABLE = False

# Langfuse integration (optional - graceful degradation if not available)
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        is_langfuse_ready,
        trace_context,
        log_generation_in_current_trace,
        get_current_trace_id,
        get_trace_url,
        flush_langfuse,
    )
    LANGFUSE_AVAILABLE = True
    # Initialize Langfuse early (idempotent - safe to call multiple times)
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    _langfuse_init_result = False

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

logger = logging.getLogger(__name__)


def extract_coder_artifacts(
    subtask: dict,
    commit_message: str | None,
    diff_stats: dict,
    success: bool,
    project_dir: Path | None = None,
    spec_id: str | None = None,
    trace_id: str | None = None,
    session_num: int | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Extract artifacts from coder session for ROI tracking.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    Args:
        subtask: The subtask that was worked on
        commit_message: Git commit message (if any)
        diff_stats: Git diff stats with lines_added, lines_removed, files_changed
        success: Whether the subtask was completed successfully
        project_dir: Project root directory for local storage
        spec_id: Spec identifier for grouping artifacts
        trace_id: Langfuse trace ID for linking
        session_num: Session number

    Returns:
        Tuple of (artifacts list, langfuse_refs list)
    """
    artifacts = []
    subtask_desc = subtask.get("description", "subtask")

    # Code implementation artifact ($200)
    if success and diff_stats.get("lines_added", 0) > 0:
        artifacts.append({
            "type": "code_implementation",
            "format": "code",
            "content": f"Implemented: {subtask_desc}",  # FULL CONTENT - no [:200] truncation
            "value_usd": 200,
            "description": f"Code implementation (+{diff_stats.get('lines_added', 0)} lines)",
            "tab": "dev",
            "metadata": {
                "lines_added": diff_stats.get("lines_added", 0),
                "lines_removed": diff_stats.get("lines_removed", 0),
                "files_changed": diff_stats.get("files_changed", 0),
            },
        })

    # Commit summary artifact ($25 each)
    if commit_message:
        artifacts.append({
            "type": "commit_summary",
            "format": "text",
            "content": commit_message,  # FULL CONTENT - no [:500] truncation
            "value_usd": 25,
            "description": "Git commit",
            "tab": "dev",
        })

    # Refactoring artifact ($150) - detect from commit message or file changes
    if commit_message:
        refactor_keywords = ["refactor", "clean", "restructure", "reorganize", "simplify", "extract"]
        if any(kw in commit_message.lower() for kw in refactor_keywords):
            artifacts.append({
                "type": "refactoring",
                "format": "text",
                "content": f"Refactoring: {commit_message}",  # FULL CONTENT - no [:200] truncation
                "value_usd": 150,
                "description": "Code refactoring",
                "tab": "techlead",
            })

    # Test written artifact ($100) - detect from commit message or subtask
    subtask_desc_lower = subtask_desc.lower()
    if commit_message:
        test_keywords = ["test", "spec", "unittest", "pytest", "jest", "mocha"]
        if any(kw in commit_message.lower() for kw in test_keywords) or any(kw in subtask_desc_lower for kw in test_keywords):
            artifacts.append({
                "type": "test_written",
                "format": "text",
                "content": f"Tests: {commit_message}",  # FULL CONTENT - no [:200] truncation
                "value_usd": 100,
                "description": "Test code added",
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
                agent_type="coder",
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

        return artifacts, langfuse_refs
    else:
        # No local storage available - return artifacts as both
        return artifacts, artifacts


async def publish_coder_roi(
    project_dir: Path,
    spec_dir: Path,
    subtask_id: str,
    subtask: dict,
    commit_before: str | None,
    commit_after: str | None,
    trace_id: str | None,
    success: bool,
) -> None:
    """
    Publish ROI metrics for a coder session.

    Args:
        project_dir: Project directory for git operations
        spec_dir: Spec directory
        subtask_id: The subtask ID
        subtask: The subtask dict
        commit_before: Commit hash before session
        commit_after: Commit hash after session
        trace_id: Langfuse trace ID (if available)
        success: Whether the subtask was completed
    """
    if not ROI_PUBLISHER_AVAILABLE:
        logger.debug("ROI publisher not available, skipping coder ROI")
        return

    try:
        # Get git diff stats
        diff_stats = get_git_diff_stats(project_dir, commit_before)

        # Get commit message if there was a new commit
        commit_message = None
        if commit_after and commit_after != commit_before:
            import subprocess
            try:
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%s", commit_after],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    commit_message = result.stdout.strip()
            except Exception:
                pass

        # Extract artifacts - returns (full_artifacts, langfuse_refs)
        spec_id = spec_dir.name
        artifacts, langfuse_refs = extract_coder_artifacts(
            subtask=subtask,
            commit_message=commit_message,
            diff_stats=diff_stats,
            success=success,
            project_dir=project_dir,
            spec_id=spec_id,
            trace_id=trace_id,
            session_num=1,  # session_num not available here, use 1 as default
        )

        # Count commits made
        commits_made = 1 if commit_after and commit_after != commit_before else 0

        # Count tests written (simple heuristic from artifacts)
        tests_written = len([a for a in artifacts if a["type"] == "test_written"])

        # Get project_id from spec_dir parent or project_dir
        project_id = project_dir.name

        # Publish ROI with Langfuse refs (truncated previews, not full content)
        await publish_feature_roi(
            feature_type="coder",
            project_id=project_id,
            cost_usd=0.0,  # Cost is tracked at trace level, we just track metrics here
            tokens=0,  # Tokens tracked at trace level
            metrics={
                "files_changed": diff_stats.get("files_changed", 0),
                "lines_added": diff_stats.get("lines_added", 0),
                "lines_removed": diff_stats.get("lines_removed", 0),
                "commits_made": commits_made,
                "tests_written": tests_written,
                "subtasks_completed": 1 if success else 0,
                "subtasks_total": 1,
            },
            spec_id=spec_id,
            trace_id=trace_id,
            artifacts=langfuse_refs,  # Pass refs with storage_path for Langfuse
        )

        logger.info(
            f"Coder ROI published: +{diff_stats.get('lines_added', 0)} -{diff_stats.get('lines_removed', 0)} "
            f"files={diff_stats.get('files_changed', 0)} commits={commits_made} "
            f"artifacts={len(artifacts)}"
        )

    except Exception as e:
        logger.warning(f"Failed to publish coder ROI: {e}")


async def post_session_processing(
    spec_dir: Path,
    project_dir: Path,
    subtask_id: str,
    session_num: int,
    commit_before: str | None,
    commit_count_before: int,
    recovery_manager: RecoveryManager,
    linear_enabled: bool = False,
    status_manager: StatusManager | None = None,
    source_spec_dir: Path | None = None,
    trace_id: str | None = None,
) -> bool:
    """
    Process session results and update memory automatically.

    This runs in Python (100% reliable) instead of relying on agent compliance.

    Args:
        spec_dir: Spec directory containing memory/
        project_dir: Project root for git operations
        subtask_id: The subtask that was being worked on
        session_num: Current session number
        commit_before: Git commit hash before session
        commit_count_before: Number of commits before session
        recovery_manager: Recovery manager instance
        linear_enabled: Whether Linear integration is enabled
        status_manager: Optional status manager for ccstatusline
        source_spec_dir: Original spec directory (for syncing back from worktree)
        trace_id: Langfuse trace ID for ROI tracking (optional)

    Returns:
        True if subtask was completed successfully
    """
    print()
    print(muted("--- Post-Session Processing ---"))

    # Sync implementation plan back to source (for worktree mode)
    if sync_plan_to_source(spec_dir, source_spec_dir):
        print_status("Implementation plan synced to main project", "success")

    # Check if implementation plan was updated
    plan = load_implementation_plan(spec_dir)
    if not plan:
        print("  Warning: Could not load implementation plan")
        return False

    subtask = find_subtask_in_plan(plan, subtask_id)
    if not subtask:
        print(f"  Warning: Subtask {subtask_id} not found in plan")
        return False

    subtask_status = subtask.get("status", "pending")

    # Check for new commits
    commit_after = get_latest_commit(project_dir)
    commit_count_after = get_commit_count(project_dir)
    new_commits = commit_count_after - commit_count_before

    print_key_value("Subtask status", subtask_status)
    print_key_value("New commits", str(new_commits))

    if subtask_status == "completed":
        # Success! Record the attempt and good commit
        print_status(f"Subtask {subtask_id} completed successfully", "success")

        # Update status file
        if status_manager:
            subtasks = count_subtasks_detailed(spec_dir)
            status_manager.update_subtasks(
                completed=subtasks["completed"],
                total=subtasks["total"],
                in_progress=0,
            )

        # Record successful attempt
        recovery_manager.record_attempt(
            subtask_id=subtask_id,
            session=session_num,
            success=True,
            approach=f"Implemented: {subtask.get('description', 'subtask')[:100]}",
        )

        # Record good commit for rollback safety
        if commit_after and commit_after != commit_before:
            recovery_manager.record_good_commit(commit_after, subtask_id)
            print_status(f"Recorded good commit: {commit_after[:8]}", "success")

        # Record Linear session result (if enabled)
        if linear_enabled:
            # Get progress counts for the comment
            subtasks_detail = count_subtasks_detailed(spec_dir)
            await linear_subtask_completed(
                spec_dir=spec_dir,
                subtask_id=subtask_id,
                completed_count=subtasks_detail["completed"],
                total_count=subtasks_detail["total"],
            )
            print_status("Linear progress recorded", "success")

        # Extract rich insights from session (LLM-powered analysis)
        try:
            extracted_insights = await extract_session_insights(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                commit_before=commit_before,
                commit_after=commit_after,
                success=True,
                recovery_manager=recovery_manager,
            )
            insight_count = len(extracted_insights.get("file_insights", []))
            pattern_count = len(extracted_insights.get("patterns_discovered", []))
            if insight_count > 0 or pattern_count > 0:
                print_status(
                    f"Extracted {insight_count} file insights, {pattern_count} patterns",
                    "success",
                )
        except Exception as e:
            logger.warning(f"Insight extraction failed: {e}")
            extracted_insights = None

        # Save session memory (Graphiti=primary, file-based=fallback)
        try:
            save_success, storage_type = await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                success=True,
                subtasks_completed=[subtask_id],
                discoveries=extracted_insights,
            )
            if save_success:
                if storage_type == "graphiti":
                    print_status("Session saved to Graphiti memory", "success")
                else:
                    print_status(
                        "Session saved to file-based memory (fallback)", "info"
                    )
            else:
                print_status("Failed to save session memory", "warning")
        except Exception as e:
            logger.warning(f"Error saving session memory: {e}")
            print_status("Memory save failed", "warning")

        # Publish coder ROI metrics (non-blocking, wrapped in try/except)
        try:
            await publish_coder_roi(
                project_dir=project_dir,
                spec_dir=spec_dir,
                subtask_id=subtask_id,
                subtask=subtask,
                commit_before=commit_before,
                commit_after=commit_after,
                trace_id=trace_id,
                success=True,
            )
        except Exception as e:
            logger.debug(f"Coder ROI publishing failed (non-critical): {e}")

        return True

    elif subtask_status == "in_progress":
        # Session ended without completion
        print_status(f"Subtask {subtask_id} still in progress", "warning")

        recovery_manager.record_attempt(
            subtask_id=subtask_id,
            session=session_num,
            success=False,
            approach="Session ended with subtask in_progress",
            error="Subtask not marked as completed",
        )

        # Still record commit if one was made (partial progress)
        if commit_after and commit_after != commit_before:
            recovery_manager.record_good_commit(commit_after, subtask_id)
            print_status(
                f"Recorded partial progress commit: {commit_after[:8]}", "info"
            )

        # Record Linear session result (if enabled)
        if linear_enabled:
            attempt_count = recovery_manager.get_attempt_count(subtask_id)
            await linear_subtask_failed(
                spec_dir=spec_dir,
                subtask_id=subtask_id,
                attempt=attempt_count,
                error_summary="Session ended without completion",
            )

        # Extract insights even from failed sessions (valuable for future attempts)
        try:
            extracted_insights = await extract_session_insights(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                commit_before=commit_before,
                commit_after=commit_after,
                success=False,
                recovery_manager=recovery_manager,
            )
        except Exception as e:
            logger.debug(f"Insight extraction failed for incomplete session: {e}")
            extracted_insights = None

        # Save failed session memory (to track what didn't work)
        try:
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                success=False,
                subtasks_completed=[],
                discoveries=extracted_insights,
            )
        except Exception as e:
            logger.debug(f"Failed to save incomplete session memory: {e}")

        return False

    else:
        # Subtask still pending or failed
        print_status(
            f"Subtask {subtask_id} not completed (status: {subtask_status})", "error"
        )

        recovery_manager.record_attempt(
            subtask_id=subtask_id,
            session=session_num,
            success=False,
            approach="Session ended without progress",
            error=f"Subtask status is {subtask_status}",
        )

        # Record Linear session result (if enabled)
        if linear_enabled:
            attempt_count = recovery_manager.get_attempt_count(subtask_id)
            await linear_subtask_failed(
                spec_dir=spec_dir,
                subtask_id=subtask_id,
                attempt=attempt_count,
                error_summary=f"Subtask status: {subtask_status}",
            )

        # Extract insights even from completely failed sessions
        try:
            extracted_insights = await extract_session_insights(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                commit_before=commit_before,
                commit_after=commit_after,
                success=False,
                recovery_manager=recovery_manager,
            )
        except Exception as e:
            logger.debug(f"Insight extraction failed for failed session: {e}")
            extracted_insights = None

        # Save failed session memory (to track what didn't work)
        try:
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=subtask_id,
                session_num=session_num,
                success=False,
                subtasks_completed=[],
                discoveries=extracted_insights,
            )
        except Exception as e:
            logger.debug(f"Failed to save failed session memory: {e}")

        return False


async def run_agent_session(
    client: ClaudeSDKClient,
    message: str,
    spec_dir: Path,
    verbose: bool = False,
    phase: LogPhase = LogPhase.CODING,
    spec_id: str | None = None,
    session_num: int = 1,
    project_dir: Path | None = None,
    analytics_project_dir: Path | None = None,
    agent_type: str = "coder",
) -> tuple[str, str, str | None]:
    """
    Run a single agent session using Claude Agent SDK.

    Args:
        client: Claude SDK client
        message: The prompt to send
        spec_dir: Spec directory path
        verbose: Whether to show detailed output
        phase: Current execution phase for logging
        spec_id: Spec identifier for analytics tracking
        session_num: Session number for analytics tracking
        project_dir: Project directory for git operations (may be worktree)
        analytics_project_dir: Original project directory for analytics DB (use when in worktree)
        agent_type: Type of agent (planner, coder, qa_reviewer, qa_fixer)

    Returns:
        (status, response_text, trace_id) where status is:
        - "continue" if agent should continue working
        - "complete" if all subtasks complete
        - "error" if an error occurred
        trace_id is the Langfuse trace ID (or None if not available)
    """
    debug_section("session", f"Agent Session - {phase.value}")
    debug(
        "session",
        "Starting agent session",
        spec_dir=str(spec_dir),
        phase=phase.value,
        prompt_length=len(message),
        prompt_preview=message[:200] + "..." if len(message) > 200 else message,
    )
    print("Sending prompt to Claude Agent SDK...\n")

    # Get task logger for this spec
    task_logger = get_task_logger(spec_dir)
    current_tool = None
    message_count = 0
    tool_count = 0
    generation_count = 0

    # Langfuse trace ID (will be set if Langfuse is enabled)
    langfuse_trace_id: str | None = None

    # Initialize analytics tracking (if available and enabled)
    usage_tracker = None
    storage = None  # Initialize storage outside try block to ensure it's always defined
    # Use analytics_project_dir for DB path (original project, not worktree)
    effective_analytics_dir = analytics_project_dir or project_dir
    if ANALYTICS_AVAILABLE and is_tracking_enabled() and spec_id and effective_analytics_dir:
        try:
            # Determine database path - use original project dir for correct location
            db_path = str(effective_analytics_dir / ".auto-claude" / "analytics.db")
            storage = get_analytics_storage(db_path)

            # Map LogPhase to analytics phase
            phase_map = {
                LogPhase.PLANNING: "planning",
                LogPhase.CODING: "coding",
                LogPhase.VALIDATION: "validation",
            }
            analytics_phase = phase_map.get(phase, "coding")

            usage_tracker = UsageTracker(
                spec_id=spec_id,
                session_num=session_num,
                phase=analytics_phase,
                storage=storage
            )
            await usage_tracker.start_conversation()
            debug("session", "Analytics tracking initialized", spec_id=spec_id, db_path=db_path)
        except Exception as e:
            logger.warning(f"Failed to initialize analytics tracking: {e}")
            usage_tracker = None

    # ROI tracking (if analytics available)
    roi_tracker: Optional[ROITracker] = None
    if ANALYTICS_AVAILABLE and is_tracking_enabled() and spec_id and effective_analytics_dir and storage:
        try:
            roi_tracker = await create_roi_tracker(spec_id, effective_analytics_dir, storage)
            debug("session", "ROI tracking initialized", spec_id=spec_id)
        except Exception as e:
            logger.warning(f"Failed to initialize ROI tracking: {e}")
            roi_tracker = None

    # Prepare Langfuse trace context
    use_langfuse = LANGFUSE_AVAILABLE and is_langfuse_ready() and spec_id
    trace_name = f"spec-{spec_id}-{agent_type}-s{session_num}" if spec_id else f"{agent_type}-session"

    # Map LogPhase to agent phase string
    phase_str_map = {
        LogPhase.PLANNING: "planning",
        LogPhase.CODING: "coding",
        LogPhase.VALIDATION: "validation",
    }
    phase_str = phase_str_map.get(phase, "coding")

    try:
        # Create Langfuse trace context if available
        trace_ctx = None
        langfuse_ctx_obj = None
        # Derive project_id from analytics_project_dir (original project) for data isolation
        # Use analytics_project_dir because project_dir may be a worktree with spec name
        effective_project_dir = analytics_project_dir or project_dir
        project_id = effective_project_dir.name if effective_project_dir else None
        if use_langfuse:
            # Truncate message for trace input (keep it readable but not too long)
            trace_input = message[:2000] + "..." if len(message) > 2000 else message
            trace_ctx = trace_context(
                name=trace_name,
                spec_id=spec_id,
                project_id=project_id,
                agent_type=agent_type,
                metadata={
                    "phase": phase_str,
                    "session_num": session_num,
                    "project_dir": str(project_dir) if project_dir else None,
                },
                tags=[f"phase:{phase_str}"],
                input_data={"prompt": trace_input, "agent_type": agent_type},
            )
            langfuse_ctx_obj = trace_ctx.__enter__()
            langfuse_trace_id = get_current_trace_id()
            if langfuse_trace_id:
                debug("session", "Langfuse trace created", trace_id=langfuse_trace_id)
                trace_url = get_trace_url(langfuse_trace_id)
                if trace_url:
                    print(f"  Langfuse: {trace_url}\n")

        # Send the query
        debug("session", "Sending query to Claude SDK...")
        await client.query(message)
        debug_success("session", "Query sent successfully")

        # Collect response text and show tool use
        response_text = ""
        debug("session", "Starting to receive response stream...")
        async for msg in client.receive_response():
            msg_type = type(msg).__name__
            message_count += 1
            debug_detailed(
                "session",
                f"Received message #{message_count}",
                msg_type=msg_type,
            )

            # Handle AssistantMessage (text and tool use)
            if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                # Track message for analytics (if enabled)
                if usage_tracker:
                    try:
                        await usage_tracker.track_message(msg)
                    except Exception as e:
                        logger.debug(f"Analytics tracking failed for message: {e}")

                # Log generation to Langfuse (if enabled and has usage data)
                if use_langfuse and hasattr(msg, "usage") and msg.usage:
                    try:
                        generation_count += 1
                        usage = msg.usage
                        model = getattr(msg, "model", "claude-sonnet-4-5")

                        # Extract usage data
                        if isinstance(usage, dict):
                            input_tokens = usage.get("input_tokens", 0)
                            output_tokens = usage.get("output_tokens", 0)
                            cache_read = usage.get("cache_read_input_tokens", 0)
                            cache_creation = usage.get("cache_creation_input_tokens", 0)
                        else:
                            input_tokens = getattr(usage, "input_tokens", 0)
                            output_tokens = getattr(usage, "output_tokens", 0)
                            cache_read = getattr(usage, "cache_read_input_tokens", 0)
                            cache_creation = getattr(usage, "cache_creation_input_tokens", 0)

                        # Log generation
                        log_generation_in_current_trace(
                            name=f"generation-{generation_count}",
                            model=model,
                            input_data=f"[{agent_type} prompt - {len(message)} chars]",
                            output_data=f"[response chunk {generation_count}]",
                            usage={
                                "input": input_tokens,
                                "output": output_tokens,
                                "total": input_tokens + output_tokens,
                                "cache_read": cache_read,
                                "cache_creation": cache_creation,
                            },
                            metadata={
                                "message_id": getattr(msg, "id", None),
                                "phase": phase_str,
                            }
                        )
                    except Exception as e:
                        logger.debug(f"Langfuse generation logging failed: {e}")

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
                                phase,
                                print_to_console=False,
                            )
                    elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                        tool_name = block.name
                        tool_input_display = None
                        tool_count += 1

                        # Safely extract tool input (handles None, non-dict, etc.)
                        inp = get_safe_tool_input(block)

                        # Extract meaningful tool input for display
                        if inp:
                            if "pattern" in inp:
                                tool_input_display = f"pattern: {inp['pattern']}"
                            elif "file_path" in inp:
                                fp = inp["file_path"]
                                if len(fp) > 50:
                                    fp = "..." + fp[-47:]
                                tool_input_display = fp
                            elif "command" in inp:
                                cmd = inp["command"]
                                if len(cmd) > 50:
                                    cmd = cmd[:47] + "..."
                                tool_input_display = cmd
                            elif "path" in inp:
                                tool_input_display = inp["path"]

                        debug(
                            "session",
                            f"Tool call #{tool_count}: {tool_name}",
                            tool_input=tool_input_display,
                            full_input=str(inp)[:500] if inp else None,
                        )

                        # Log tool start (handles printing too)
                        if task_logger:
                            task_logger.tool_start(
                                tool_name,
                                tool_input_display,
                                phase,
                                print_to_console=True,
                            )
                        else:
                            print(f"\n[Tool: {tool_name}]", flush=True)

                        if verbose and hasattr(block, "input"):
                            input_str = str(block.input)
                            if len(input_str) > 300:
                                print(f"   Input: {input_str[:300]}...", flush=True)
                            else:
                                print(f"   Input: {input_str}", flush=True)
                        current_tool = tool_name

            # Handle UserMessage (tool results)
            elif msg_type == "UserMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "ToolResultBlock":
                        result_content = getattr(block, "content", "")
                        is_error = getattr(block, "is_error", False)

                        # Check if command was blocked by security hook
                        if "blocked" in str(result_content).lower():
                            debug_error(
                                "session",
                                f"Tool BLOCKED: {current_tool}",
                                result=str(result_content)[:300],
                            )
                            print(f"   [BLOCKED] {result_content}", flush=True)
                            if task_logger and current_tool:
                                task_logger.tool_end(
                                    current_tool,
                                    success=False,
                                    result="BLOCKED",
                                    detail=str(result_content),
                                    phase=phase,
                                )
                        elif is_error:
                            # Show errors (truncated)
                            error_str = str(result_content)[:500]
                            debug_error(
                                "session",
                                f"Tool error: {current_tool}",
                                error=error_str[:200],
                            )
                            print(f"   [Error] {error_str}", flush=True)
                            if task_logger and current_tool:
                                # Store full error in detail for expandable view
                                task_logger.tool_end(
                                    current_tool,
                                    success=False,
                                    result=error_str[:100],
                                    detail=str(result_content),
                                    phase=phase,
                                )
                        else:
                            # Tool succeeded
                            debug_detailed(
                                "session",
                                f"Tool success: {current_tool}",
                                result_length=len(str(result_content)),
                            )
                            if verbose:
                                result_str = str(result_content)[:200]
                                print(f"   [Done] {result_str}", flush=True)
                            else:
                                print("   [Done]", flush=True)
                            if task_logger and current_tool:
                                # Store full result in detail for expandable view (only for certain tools)
                                # Skip storing for very large outputs like Glob results
                                detail_content = None
                                if current_tool in (
                                    "Read",
                                    "Grep",
                                    "Bash",
                                    "Edit",
                                    "Write",
                                ):
                                    result_str = str(result_content)
                                    # Only store if not too large (detail truncation happens in logger)
                                    if (
                                        len(result_str) < 50000
                                    ):  # 50KB max before truncation
                                        detail_content = result_str
                                task_logger.tool_end(
                                    current_tool,
                                    success=True,
                                    detail=detail_content,
                                    phase=phase,
                                )

                        current_tool = None

        print("\n" + "-" * 70 + "\n")

        # Check if build is complete
        if is_build_complete(spec_dir):
            debug_success(
                "session",
                "Session completed - build is complete",
                message_count=message_count,
                tool_count=tool_count,
                response_length=len(response_text),
                langfuse_trace_id=langfuse_trace_id,
            )
            return "complete", response_text, langfuse_trace_id

        debug_success(
            "session",
            "Session completed - continuing",
            message_count=message_count,
            tool_count=tool_count,
            response_length=len(response_text),
            langfuse_trace_id=langfuse_trace_id,
        )
        return "continue", response_text, langfuse_trace_id

    except Exception as e:
        debug_error(
            "session",
            f"Session error: {e}",
            exception_type=type(e).__name__,
            message_count=message_count,
            tool_count=tool_count,
        )
        print(f"Error during agent session: {e}")
        if task_logger:
            task_logger.log_error(f"Session error: {e}", phase)
        return "error", str(e), langfuse_trace_id

    finally:
        # Finalize analytics tracking
        if usage_tracker:
            try:
                await usage_tracker.finalize()
                debug("session", "Analytics tracking finalized",
                      cost=f"${usage_tracker.total_cost_usd:.4f}",
                      input_tokens=usage_tracker.total_input_tokens,
                      output_tokens=usage_tracker.total_output_tokens)
            except Exception as e:
                logger.debug(f"Failed to finalize analytics tracking: {e}")

        # Finalize ROI tracking
        if roi_tracker:
            try:
                total_cost = usage_tracker.total_cost_usd if usage_tracker else 0
                total_tokens = (
                    (usage_tracker.total_input_tokens + usage_tracker.total_output_tokens)
                    if usage_tracker else 0
                )
                await roi_tracker.finalize(total_cost, total_tokens)
                debug("session", "ROI tracking finalized")
            except Exception as e:
                logger.debug(f"Failed to finalize ROI tracking: {e}")

        # Close Langfuse trace context
        if use_langfuse and trace_ctx:
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
                debug("session", "Langfuse trace finalized", trace_id=langfuse_trace_id)
            except Exception as e:
                logger.debug(f"Failed to finalize Langfuse trace: {e}")
