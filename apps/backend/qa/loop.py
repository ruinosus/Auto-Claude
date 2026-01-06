"""
QA Validation Loop Orchestration
=================================

Main QA loop that coordinates reviewer and fixer sessions until
approval or max iterations.
"""

import os
import time as time_module
from pathlib import Path

from core.client import create_client
from debug import debug, debug_error, debug_section, debug_success, debug_warning
from linear_updater import (
    LinearTaskState,
    is_linear_enabled,
    linear_qa_approved,
    linear_qa_max_iterations,
    linear_qa_rejected,
    linear_qa_started,
)
from phase_config import get_phase_model, get_phase_thinking_budget
from phase_event import ExecutionPhase, emit_phase
from progress import count_subtasks, is_build_complete
from security.constants import PROJECT_DIR_ENV_VAR
from task_logger import (
    LogPhase,
    get_task_logger,
)

from .criteria import (
    get_qa_iteration_count,
    get_qa_signoff_status,
    is_qa_approved,
)
from .fixer import run_qa_fixer_session
from .report import (
    create_manual_test_plan,
    escalate_to_human,
    get_iteration_history,
    get_recurring_issue_summary,
    has_recurring_issues,
    is_no_test_project,
    record_iteration,
)
from .reviewer import run_qa_agent_session

# ROI tracking (optional - graceful degradation if not available)
try:
    from analytics import get_analytics_storage, is_tracking_enabled
    ROI_TRACKING_AVAILABLE = True
except ImportError:
    ROI_TRACKING_AVAILABLE = False

# Langfuse ROI score publishing (optional - graceful degradation)
try:
    from analytics.roi_score_publisher import publish_roi_scores
    LANGFUSE_ROI_AVAILABLE = True
except ImportError:
    LANGFUSE_ROI_AVAILABLE = False

# Langfuse categorical/boolean scores (optional - graceful degradation)
try:
    from analytics.langfuse_integration import (
        save_build_result,
        save_qa_verdict,
        save_qa_first_attempt,
        is_langfuse_ready,
    )
    LANGFUSE_SCORES_AVAILABLE = True
except ImportError:
    LANGFUSE_SCORES_AVAILABLE = False

# Configuration
MAX_QA_ITERATIONS = 50
MAX_CONSECUTIVE_ERRORS = 3  # Stop after 3 consecutive errors without progress


def _save_qa_scores(trace_id: str | None, qa_passed: bool, qa_iteration: int) -> None:
    """Save categorical and boolean QA scores to Langfuse."""
    if not LANGFUSE_SCORES_AVAILABLE or not trace_id:
        return

    if not is_langfuse_ready():
        return

    try:
        # Save build result
        if qa_passed:
            save_build_result(trace_id, "success")
        else:
            save_build_result(trace_id, "failure")

        # Save QA verdict
        if qa_passed:
            save_qa_verdict(trace_id, "approved")
        else:
            save_qa_verdict(trace_id, "rejected")

        # Save first-attempt pass
        save_qa_first_attempt(trace_id, qa_passed and qa_iteration == 1)

        debug("qa_loop", f"Saved QA categorical scores to trace {trace_id}")
    except Exception as e:
        debug("qa_loop", f"Failed to save QA categorical scores: {e}")


# =============================================================================
# ROI TRACKING HELPERS
# =============================================================================


async def _update_qa_roi(
    project_dir: Path,
    spec_id: str,
    qa_passed: bool,
    qa_attempts: int,
    analytics_project_dir: Path | None = None,
    trace_id: str | None = None,
):
    """Update ROI record with QA attempt results and publish to Langfuse."""
    # Use analytics_project_dir for DB path (original project, not worktree)
    effective_dir = analytics_project_dir or project_dir

    # 1. Update local analytics storage (if available)
    if ROI_TRACKING_AVAILABLE and is_tracking_enabled():
        try:
            from datetime import datetime

            db_path = str(effective_dir / ".auto-claude" / "analytics.db")
            storage = get_analytics_storage(db_path)

            # Get existing ROI data
            existing = await storage.get_spec_roi(spec_id)

            if existing:
                # Update existing record
                existing['qa_attempts'] = qa_attempts
                existing['qa_passed'] = qa_passed
                if qa_passed:
                    existing['completed_at'] = datetime.utcnow().isoformat()
                await storage.save_spec_roi(spec_id, existing)
            else:
                # Create new record with just QA data
                await storage.save_spec_roi(spec_id, {
                    'project_id': effective_dir.name,  # Use original project directory name (not worktree)
                    'qa_attempts': qa_attempts,
                    'qa_passed': qa_passed,
                    'completed_at': datetime.utcnow().isoformat() if qa_passed else None
                })
        except Exception as e:
            # Don't fail QA loop if ROI tracking fails
            debug("qa_loop", f"Failed to update local ROI tracking: {e}")

    # 2. Publish ROI scores to Langfuse (if available)
    if LANGFUSE_ROI_AVAILABLE:
        try:
            result = await publish_roi_scores(
                spec_id=spec_id,
                project_dir=effective_dir,
                qa_attempts=qa_attempts,
                qa_passed=qa_passed,
                trace_id=trace_id,  # Pass trace_id directly to avoid search
            )
            if result.get('success'):
                debug(
                    "qa_loop",
                    f"Published ROI scores to Langfuse",
                    trace_id=result.get('trace_id'),
                    roi_percentage=result.get('roi_percentage'),
                    business_value=result.get('business_value_usd'),
                )
            else:
                debug("qa_loop", f"Failed to publish ROI scores: {result.get('error')}")
        except Exception as e:
            # Don't fail QA loop if Langfuse publishing fails
            debug("qa_loop", f"Failed to publish ROI scores to Langfuse: {e}")


# =============================================================================
# QA VALIDATION LOOP
# =============================================================================


async def run_qa_validation_loop(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    verbose: bool = False,
    analytics_project_dir: Path | None = None,
) -> bool:
    """
    Run the full QA validation loop.

    This is the self-validating loop:
    1. QA Agent reviews
    2. If rejected → Fixer Agent fixes
    3. QA Agent re-reviews
    4. Loop until approved or max iterations

    Enhanced with:
    - Iteration tracking with detailed history
    - Recurring issue detection (3+ occurrences → human escalation)
    - No-test project handling

    Args:
        project_dir: Project root directory (may be worktree)
        spec_dir: Spec directory
        model: Claude model to use
        verbose: Whether to show detailed output
        analytics_project_dir: Original project directory for analytics DB (use when in worktree)

    Returns:
        True if QA approved, False otherwise
    """
    # Set environment variable for security hooks to find the correct project directory
    # This is needed because os.getcwd() may return the wrong directory in worktree mode
    os.environ[PROJECT_DIR_ENV_VAR] = str(project_dir.resolve())

    debug_section("qa_loop", "QA Validation Loop")
    debug(
        "qa_loop",
        "Starting QA validation loop",
        project_dir=str(project_dir),
        spec_dir=str(spec_dir),
        model=model,
        max_iterations=MAX_QA_ITERATIONS,
    )

    print("\n" + "=" * 70)
    print("  QA VALIDATION LOOP")
    print("  Self-validating quality assurance")
    print("=" * 70)

    # Initialize task logger for the validation phase
    task_logger = get_task_logger(spec_dir)

    # Verify build is complete
    if not is_build_complete(spec_dir):
        debug_warning("qa_loop", "Build is not complete, cannot run QA")
        print("\n❌ Build is not complete. Cannot run QA validation.")
        completed, total = count_subtasks(spec_dir)
        debug("qa_loop", "Build progress", completed=completed, total=total)
        print(f"   Progress: {completed}/{total} subtasks completed")
        return False

    # Emit phase event at start of QA validation (before any early returns)
    emit_phase(ExecutionPhase.QA_REVIEW, "Starting QA validation")

    # Check if there's pending human feedback that needs to be processed
    fix_request_file = spec_dir / "QA_FIX_REQUEST.md"
    has_human_feedback = fix_request_file.exists()

    # Check if already approved - but if there's human feedback, we need to process it first
    if is_qa_approved(spec_dir) and not has_human_feedback:
        debug_success("qa_loop", "Build already approved by QA")
        print("\n✅ Build already approved by QA.")
        return True

    # If there's human feedback, we need to run the fixer first before re-validating
    if has_human_feedback:
        debug(
            "qa_loop",
            "Human feedback detected - will run fixer first",
            fix_request_file=str(fix_request_file),
        )
        emit_phase(ExecutionPhase.QA_FIXING, "Processing human feedback")
        print("\n📝 Human feedback detected. Running QA Fixer first...")

        # Get model and thinking budget for fixer (uses QA phase config)
        qa_model = get_phase_model(spec_dir, "qa", model)
        fixer_thinking_budget = get_phase_thinking_budget(spec_dir, "qa")

        fix_client = create_client(
            project_dir,
            spec_dir,
            qa_model,
            agent_type="qa_fixer",
            max_thinking_tokens=fixer_thinking_budget,
        )

        async with fix_client:
            fix_status, fix_response, _ = await run_qa_fixer_session(
                fix_client,
                spec_dir,
                0,
                False,  # iteration 0 for human feedback
                analytics_project_dir=analytics_project_dir,  # Original project for analytics
            )

        if fix_status == "error":
            debug_error("qa_loop", f"Fixer error: {fix_response[:200]}")
            print(f"\n❌ Fixer encountered error: {fix_response}")
            return False

        debug_success("qa_loop", "Human feedback fixes applied")
        print("\n✅ Fixes applied based on human feedback. Running QA validation...")

        # Remove the fix request file after processing
        try:
            fix_request_file.unlink()
            debug("qa_loop", "Removed processed QA_FIX_REQUEST.md")
        except OSError:
            pass  # Ignore if file removal fails

    # Check for no-test projects
    if is_no_test_project(spec_dir, project_dir):
        print("\n⚠️  No test framework detected in project.")
        print("Creating manual test plan...")
        manual_plan = create_manual_test_plan(spec_dir, spec_dir.name)
        print(f"📝 Manual test plan created: {manual_plan}")
        print("\nNote: Automated testing will be limited for this project.")

    # Start validation phase in task logger
    if task_logger:
        task_logger.start_phase(LogPhase.VALIDATION, "Starting QA validation...")

    # Check Linear integration status
    linear_task = None
    if is_linear_enabled():
        linear_task = LinearTaskState.load(spec_dir)
        if linear_task and linear_task.task_id:
            print(f"Linear task: {linear_task.task_id}")
            # Update Linear to "In Review" when QA starts
            await linear_qa_started(spec_dir)
            print("Linear task moved to 'In Review'")

    qa_iteration = get_qa_iteration_count(spec_dir)
    consecutive_errors = 0
    last_error_context = None  # Track error for self-correction feedback
    trace_id = None  # Will hold the last trace ID from QA sessions

    while qa_iteration < MAX_QA_ITERATIONS:
        qa_iteration += 1
        iteration_start = time_module.time()

        debug_section("qa_loop", f"QA Iteration {qa_iteration}")
        debug(
            "qa_loop",
            f"Starting iteration {qa_iteration}/{MAX_QA_ITERATIONS}",
            iteration=qa_iteration,
            max_iterations=MAX_QA_ITERATIONS,
        )

        print(f"\n--- QA Iteration {qa_iteration}/{MAX_QA_ITERATIONS} ---")
        emit_phase(
            ExecutionPhase.QA_REVIEW, f"Running QA review iteration {qa_iteration}"
        )

        # Run QA reviewer with phase-specific model and thinking budget
        qa_model = get_phase_model(spec_dir, "qa", model)
        qa_thinking_budget = get_phase_thinking_budget(spec_dir, "qa")
        debug(
            "qa_loop",
            "Creating client for QA reviewer session...",
            model=qa_model,
            thinking_budget=qa_thinking_budget,
        )
        client = create_client(
            project_dir,
            spec_dir,
            qa_model,
            agent_type="qa_reviewer",
            max_thinking_tokens=qa_thinking_budget,
        )

        async with client:
            debug("qa_loop", "Running QA reviewer agent session...")
            status, response, trace_id = await run_qa_agent_session(
                client,
                project_dir,  # Pass project_dir for capability-based tool injection
                spec_dir,
                qa_iteration,
                MAX_QA_ITERATIONS,
                verbose,
                previous_error=last_error_context,  # Pass error context for self-correction
                analytics_project_dir=analytics_project_dir,  # Original project for analytics
            )
            if trace_id:
                debug("qa_loop", f"QA reviewer trace: {trace_id}")

        iteration_duration = time_module.time() - iteration_start
        debug(
            "qa_loop",
            "QA reviewer session completed",
            status=status,
            duration_seconds=f"{iteration_duration:.1f}",
            response_length=len(response),
        )

        if status == "approved":
            emit_phase(ExecutionPhase.COMPLETE, "QA validation passed")
            # Reset error tracking on success
            consecutive_errors = 0
            last_error_context = None

            # Record successful iteration
            debug_success(
                "qa_loop",
                "QA APPROVED",
                iteration=qa_iteration,
                duration=f"{iteration_duration:.1f}s",
            )
            record_iteration(spec_dir, qa_iteration, "approved", [], iteration_duration)

            print("\n" + "=" * 70)
            print("  ✅ QA APPROVED")
            print("=" * 70)
            print("\nAll acceptance criteria verified.")
            print("The implementation is production-ready.")
            print("\nNext steps:")
            print("  1. Review the auto-claude/* branch")
            print("  2. Create a PR and merge to main")

            # End validation phase successfully
            if task_logger:
                task_logger.end_phase(
                    LogPhase.VALIDATION,
                    success=True,
                    message="QA validation passed - all criteria met",
                )

            # Update Linear: QA approved, awaiting human review
            if linear_task and linear_task.task_id:
                await linear_qa_approved(spec_dir)
                print("\nLinear: Task marked as QA approved, awaiting human review")

            # Update ROI tracking with QA result (use trace_id from QA session)
            spec_id = spec_dir.name
            await _update_qa_roi(project_dir, spec_id, qa_passed=True, qa_attempts=qa_iteration, analytics_project_dir=analytics_project_dir, trace_id=trace_id)

            # Save categorical scores to Langfuse
            _save_qa_scores(trace_id, qa_passed=True, qa_iteration=qa_iteration)

            return True

        elif status == "rejected":
            # Reset error tracking on valid response (rejected is a valid response)
            consecutive_errors = 0
            last_error_context = None

            debug_warning(
                "qa_loop",
                "QA REJECTED",
                iteration=qa_iteration,
                duration=f"{iteration_duration:.1f}s",
            )
            print(f"\n❌ QA found issues. Iteration {qa_iteration}/{MAX_QA_ITERATIONS}")

            # Get issues from QA report
            qa_status = get_qa_signoff_status(spec_dir)
            current_issues = qa_status.get("issues_found", []) if qa_status else []
            debug(
                "qa_loop",
                "Issues found by QA",
                issue_count=len(current_issues),
                issues=current_issues[:3] if current_issues else [],  # Show first 3
            )

            # Record rejected iteration
            record_iteration(
                spec_dir, qa_iteration, "rejected", current_issues, iteration_duration
            )

            # Check for recurring issues
            history = get_iteration_history(spec_dir)
            has_recurring, recurring_issues = has_recurring_issues(
                current_issues, history
            )

            if has_recurring:
                from .report import RECURRING_ISSUE_THRESHOLD

                debug_error(
                    "qa_loop",
                    "Recurring issues detected - escalating to human",
                    recurring_count=len(recurring_issues),
                    threshold=RECURRING_ISSUE_THRESHOLD,
                )
                print(
                    f"\n⚠️  Recurring issues detected ({len(recurring_issues)} issue(s) appeared {RECURRING_ISSUE_THRESHOLD}+ times)"
                )
                print("Escalating to human review due to recurring issues...")

                # Create escalation file
                await escalate_to_human(spec_dir, recurring_issues, qa_iteration)

                # End validation phase
                if task_logger:
                    task_logger.end_phase(
                        LogPhase.VALIDATION,
                        success=False,
                        message=f"QA escalated to human after {qa_iteration} iterations due to recurring issues",
                    )

                # Update Linear
                if linear_task and linear_task.task_id:
                    await linear_qa_max_iterations(spec_dir, qa_iteration)
                    print(
                        "\nLinear: Task marked as needing human intervention (recurring issues)"
                    )

                # Update ROI tracking with QA result (recurring issues - failed)
                spec_id = spec_dir.name
                await _update_qa_roi(project_dir, spec_id, qa_passed=False, qa_attempts=qa_iteration, analytics_project_dir=analytics_project_dir, trace_id=trace_id)

                # Save categorical scores to Langfuse
                _save_qa_scores(trace_id, qa_passed=False, qa_iteration=qa_iteration)

                return False

            # Record rejection in Linear
            if linear_task and linear_task.task_id:
                issues_count = len(current_issues)
                await linear_qa_rejected(spec_dir, issues_count, qa_iteration)

            if qa_iteration >= MAX_QA_ITERATIONS:
                print("\n⚠️  Maximum QA iterations reached.")
                print("Escalating to human review.")
                break

            # Run fixer with phase-specific thinking budget
            fixer_thinking_budget = get_phase_thinking_budget(spec_dir, "qa")
            debug(
                "qa_loop",
                "Starting QA fixer session...",
                model=qa_model,
                thinking_budget=fixer_thinking_budget,
            )
            emit_phase(ExecutionPhase.QA_FIXING, "Fixing QA issues")
            print("\nRunning QA Fixer Agent...")

            fix_client = create_client(
                project_dir,
                spec_dir,
                qa_model,
                agent_type="qa_fixer",
                max_thinking_tokens=fixer_thinking_budget,
            )

            async with fix_client:
                fix_status, fix_response, fix_trace_id = await run_qa_fixer_session(
                    fix_client, spec_dir, qa_iteration, verbose,
                    analytics_project_dir=analytics_project_dir,  # Original project for analytics
                )
                if fix_trace_id:
                    debug("qa_loop", f"QA fixer trace: {fix_trace_id}")

            debug(
                "qa_loop",
                "QA fixer session completed",
                fix_status=fix_status,
                response_length=len(fix_response),
            )

            if fix_status == "error":
                debug_error("qa_loop", f"Fixer error: {fix_response[:200]}")
                print(f"\n❌ Fixer encountered error: {fix_response}")
                record_iteration(
                    spec_dir,
                    qa_iteration,
                    "error",
                    [{"title": "Fixer error", "description": fix_response}],
                )
                break

            debug_success("qa_loop", "Fixes applied, re-running QA validation")
            print("\n✅ Fixes applied. Re-running QA validation...")

        elif status == "error":
            consecutive_errors += 1
            debug_error(
                "qa_loop",
                f"QA session error: {response[:200]}",
                consecutive_errors=consecutive_errors,
                max_consecutive=MAX_CONSECUTIVE_ERRORS,
            )
            print(f"\n❌ QA error: {response}")
            print(
                f"   Consecutive errors: {consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}"
            )
            record_iteration(
                spec_dir,
                qa_iteration,
                "error",
                [{"title": "QA error", "description": response}],
            )

            # Build error context for self-correction in next iteration
            last_error_context = {
                "error_type": "missing_implementation_plan_update",
                "error_message": response,
                "consecutive_errors": consecutive_errors,
                "expected_action": "You MUST update implementation_plan.json with a qa_signoff object containing 'status': 'approved' or 'status': 'rejected'",
                "file_path": str(spec_dir / "implementation_plan.json"),
            }

            # Check if we've hit max consecutive errors
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                debug_error(
                    "qa_loop",
                    f"Max consecutive errors ({MAX_CONSECUTIVE_ERRORS}) reached - escalating to human",
                )
                print(
                    f"\n⚠️  {MAX_CONSECUTIVE_ERRORS} consecutive errors without progress."
                )
                print(
                    "The QA agent is unable to properly update implementation_plan.json."
                )
                print("Escalating to human review.")

                # End validation phase as failed
                if task_logger:
                    task_logger.end_phase(
                        LogPhase.VALIDATION,
                        success=False,
                        message=f"QA agent failed {MAX_CONSECUTIVE_ERRORS} consecutive times - unable to update implementation_plan.json",
                    )

                # Update ROI tracking with QA result (max errors - failed)
                spec_id = spec_dir.name
                await _update_qa_roi(project_dir, spec_id, qa_passed=False, qa_attempts=qa_iteration, analytics_project_dir=analytics_project_dir, trace_id=trace_id)

                # Save categorical scores to Langfuse
                _save_qa_scores(trace_id, qa_passed=False, qa_iteration=qa_iteration)

                return False

            print("Retrying with error feedback...")

    # Max iterations reached without approval
    emit_phase(ExecutionPhase.FAILED, "QA validation incomplete")
    debug_error(
        "qa_loop",
        "QA VALIDATION INCOMPLETE - max iterations reached",
        iterations=qa_iteration,
        max_iterations=MAX_QA_ITERATIONS,
    )
    print("\n" + "=" * 70)
    print("  ⚠️  QA VALIDATION INCOMPLETE")
    print("=" * 70)
    print(f"\nReached maximum iterations ({MAX_QA_ITERATIONS}) without approval.")
    print("\nRemaining issues require human review:")

    # Show iteration summary
    history = get_iteration_history(spec_dir)
    summary = get_recurring_issue_summary(history)
    debug(
        "qa_loop",
        "QA loop final summary",
        total_iterations=len(history),
        total_issues=summary.get("total_issues", 0),
        unique_issues=summary.get("unique_issues", 0),
    )
    if summary["total_issues"] > 0:
        print("\n📊 Iteration Summary:")
        print(f"   Total iterations: {len(history)}")
        print(f"   Total issues found: {summary['total_issues']}")
        print(f"   Unique issues: {summary['unique_issues']}")
        if summary.get("most_common"):
            print("   Most common issues:")
            for issue in summary["most_common"][:3]:
                print(f"     - {issue['title']} ({issue['occurrences']} occurrences)")

    # End validation phase as failed
    if task_logger:
        task_logger.end_phase(
            LogPhase.VALIDATION,
            success=False,
            message=f"QA validation incomplete after {qa_iteration} iterations",
        )

    # Show the fix request file if it exists
    fix_request_file = spec_dir / "QA_FIX_REQUEST.md"
    if fix_request_file.exists():
        print(f"\nSee: {fix_request_file}")

    qa_report_file = spec_dir / "qa_report.md"
    if qa_report_file.exists():
        print(f"See: {qa_report_file}")

    # Update Linear: max iterations reached, needs human intervention
    if linear_task and linear_task.task_id:
        await linear_qa_max_iterations(spec_dir, qa_iteration)
        print("\nLinear: Task marked as needing human intervention")

    # Update ROI tracking with QA result (max iterations - failed)
    spec_id = spec_dir.name
    await _update_qa_roi(project_dir, spec_id, qa_passed=False, qa_attempts=qa_iteration, analytics_project_dir=analytics_project_dir, trace_id=trace_id)

    # Save categorical scores to Langfuse
    _save_qa_scores(trace_id, qa_passed=False, qa_iteration=qa_iteration)

    print("\nManual intervention required.")
    return False
