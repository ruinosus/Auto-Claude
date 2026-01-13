"""
Planner Agent Module
====================

Handles follow-up planner sessions for adding new subtasks to completed specs.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from core.client import create_client
from phase_config import get_phase_model, get_phase_thinking_budget
from phase_event import ExecutionPhase, emit_phase
from task_logger import (
    LogPhase,
    get_task_logger,
)
from ui import (
    BuildState,
    Icons,
    StatusManager,
    bold,
    box,
    highlight,
    icon,
    muted,
    print_status,
)

from .session import run_agent_session

# Langfuse integration (optional - graceful degradation if not available)
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        is_langfuse_ready,
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
    from roi_engine.core import calculate_roi_for_spec, publish_roi, load_squad_config
    ROI_ENGINE_AVAILABLE = True
except ImportError:
    ROI_ENGINE_AVAILABLE = False

# Legacy ROI publisher fallback (deprecated - will be removed)
ROI_PUBLISHER_AVAILABLE = False  # Force use of ROI Engine

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


def extract_planner_artifacts(
    plan_data: dict | None,
    subtasks: list[dict],
    response_text: str = "",
    project_dir: Path | None = None,
    spec_id: str | None = None,
    trace_id: str | None = None,
    session_num: int | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Extract artifacts from a planning session.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    Args:
        plan_data: The implementation plan dictionary (if available)
        subtasks: List of subtask dictionaries from the plan
        response_text: Raw response text from the planner agent
        project_dir: Project root directory for local storage
        spec_id: Spec identifier for grouping artifacts
        trace_id: Langfuse trace ID for linking
        session_num: Session number

    Returns:
        Tuple of (artifacts list, langfuse_refs list)
    """
    artifacts = []

    # 1. Implementation plan artifact ($300) - the COMPLETE plan (no truncation!)
    if plan_data:
        artifacts.append({
            "type": "implementation_plan",
            "format": "json",
            "content": json.dumps(plan_data, indent=2),  # FULL CONTENT - no [:1000] truncation
            "value_usd": 300,
            "description": f"Implementation plan: {plan_data.get('feature', 'Unknown feature')}",
            "tab": "techlead",
        })

    # 2. Subtask definition artifacts ($50 each)
    for subtask in subtasks:
        subtask_desc = subtask.get("description", "")  # FULL CONTENT - no [:200] truncation
        artifacts.append({
            "type": "subtask_definition",
            "format": "text",
            "content": subtask_desc,
            "value_usd": 50,
            "description": f"Subtask: {subtask.get('id', 'unknown')}",
            "tab": "dev",
            "metadata": {
                "subtask_id": subtask.get("id"),
                "subtask_type": subtask.get("type"),
            },
        })

    # 3. Architecture decision artifacts ($200 each) - extract from response text
    architecture_keywords = [
        "architecture", "design pattern", "structure", "approach",
        "framework", "component", "module", "layer", "service"
    ]
    if response_text:
        sentences = re.split(r'[.!?\n]', response_text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(kw in sentence_lower for kw in architecture_keywords):
                if "decision" in sentence_lower or "choose" in sentence_lower or "use" in sentence_lower:
                    if len(sentence.strip()) > 40:
                        artifacts.append({
                            "type": "architecture_decision",
                            "format": "text",
                            "content": sentence.strip(),  # FULL CONTENT - no [:250] truncation
                            "value_usd": 200,
                            "description": "Architecture decision",
                            "tab": "techlead",
                        })
                        break  # Only extract one per session

    # 4. Risk assessment artifacts ($100 each) - extract from response text
    risk_keywords = [
        "risk", "potential issue", "concern", "challenge", "difficulty",
        "complexity", "dependency", "blocker", "caution", "warning"
    ]
    if response_text:
        sentences = re.split(r'[.!?\n]', response_text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(kw in sentence_lower for kw in risk_keywords):
                if len(sentence.strip()) > 30:
                    artifacts.append({
                        "type": "risk_assessment",
                        "format": "text",
                        "content": sentence.strip(),  # FULL CONTENT - no [:250] truncation
                        "value_usd": 100,
                        "description": "Risk assessment",
                        "tab": "ops",
                    })
                    break  # Only extract one per session

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
                agent_type="planner",
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


async def publish_planner_roi(
    project_dir: Path,
    spec_dir: Path,
    plan_data: dict | None,
    subtasks: list[dict],
    phases_count: int,
    response_text: str,
    trace_id: str | None,
    complexity_level: str = "standard",
) -> dict[str, Any] | None:
    """
    Publish ROI metrics for a planner session.

    Now uses ROI Engine for artifact-based ROI calculation.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory
        plan_data: The implementation plan dictionary
        subtasks: List of subtasks from the plan
        phases_count: Number of phases in the plan
        response_text: Raw response text from the planner
        trace_id: Langfuse trace ID (if available)
        complexity_level: Complexity level of the spec

    Returns:
        ROI result dictionary or None if publishing failed
    """
    if not ROI_ENGINE_AVAILABLE:
        logger.debug("ROI Engine not available, skipping ROI publish")
        return None

    try:
        project_id = project_dir.name
        spec_id = spec_dir.name

        # Extract artifacts - returns (full_artifacts, langfuse_refs)
        artifacts, langfuse_refs = extract_planner_artifacts(
            plan_data=plan_data,
            subtasks=subtasks,
            response_text=response_text,
            project_dir=project_dir,
            spec_id=spec_id,
            trace_id=trace_id,
            session_num=1,  # Planner is typically session 1
        )

        # Count risks identified from response text
        risks_identified = 0
        risk_keywords = ["risk", "concern", "challenge", "difficulty", "blocker"]
        if response_text:
            response_lower = response_text.lower()
            for kw in risk_keywords:
                risks_identified += response_lower.count(kw)
            risks_identified = min(risks_identified, 10)  # Cap at 10

        # Metrics for planner
        metrics = {
            "subtasks_created": len(subtasks),
            "phases_defined": phases_count,
            "risks_identified": risks_identified,
            "complexity_level": complexity_level,
            # Also include as build metrics since planner is part of build phase
            "subtasks_completed": 0,  # Planning phase - no subtasks completed yet
            "subtasks_total": len(subtasks),
            "files_changed": 0,
            "lines_added": 0,
            "lines_removed": 0,
        }

        # Calculate ROI using ROI Engine (artifact-based valuation)
        # Artifacts were already saved above, ROI Engine reads from storage
        squad_config = load_squad_config(project_dir)
        roi_result = calculate_roi_for_spec(
            spec_id=spec_id,
            project_dir=project_dir,
            token_cost=0.0,  # Cost tracked separately in session
            squad_config=squad_config,
        )

        # Publish to Langfuse and save locally
        publish_result = await publish_roi(
            roi_result,
            trace_id=trace_id,
            project_dir=project_dir,
        )

        # Build result dict for compatibility
        result = {
            "roi_percentage": roi_result.roi_percentage,
            "total_artifact_value": roi_result.total_artifact_value,
            "token_cost": roi_result.token_cost,
            "artifact_count": roi_result.artifact_count,
            "net_value": roi_result.net_value,
            "by_role": roi_result.by_role,
            "by_type": roi_result.by_type,
            "metrics": metrics,
            "langfuse_published": publish_result.get("langfuse_published", False),
        }

        # Save artifacts to file for traceability
        try:
            artifacts_dir = spec_dir / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            artifacts_file = artifacts_dir / f"planner_artifacts_{timestamp}.json"

            artifact_report = {
                "timestamp": datetime.now().isoformat(),
                "trace_id": trace_id,
                "spec_id": spec_id,
                "project_id": project_id,
                "metrics": metrics,
                "artifacts": artifacts,
                "total_value_usd": sum(a.get("value_usd", 0) for a in artifacts),
                "roi_result": result,
            }

            with open(artifacts_file, "w") as f:
                json.dump(artifact_report, f, indent=2, default=str)

            logger.debug(f"Planner artifacts saved to {artifacts_file}")
        except Exception as e:
            logger.warning(f"Failed to save planner artifacts: {e}")

        logger.info(
            f"Published planner ROI: {len(subtasks)} subtasks, "
            f"{phases_count} phases, {len(artifacts)} artifacts"
        )

        return result

    except Exception as e:
        logger.warning(f"Failed to publish planner ROI: {e}")
        return None


async def run_followup_planner(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    verbose: bool = False,
) -> bool:
    """
    Run the follow-up planner to add new subtasks to a completed spec.

    This is a simplified version of run_autonomous_agent that:
    1. Creates a client
    2. Loads the followup planner prompt
    3. Runs a single planning session
    4. Returns after the plan is updated (doesn't enter coding loop)

    The planner agent will:
    - Read FOLLOWUP_REQUEST.md for the new task
    - Read the existing implementation_plan.json
    - Add new phase(s) with pending subtasks
    - Update the plan status back to in_progress

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the completed spec
        model: Claude model to use
        verbose: Whether to show detailed output

    Returns:
        bool: True if planning completed successfully
    """
    from implementation_plan import ImplementationPlan
    from prompts import get_followup_planner_prompt

    # Initialize status manager for ccstatusline
    status_manager = StatusManager(project_dir)
    status_manager.set_active(spec_dir.name, BuildState.PLANNING)
    emit_phase(ExecutionPhase.PLANNING, "Follow-up planning")

    # Initialize task logger for persistent logging
    task_logger = get_task_logger(spec_dir)

    # Show header
    content = [
        bold(f"{icon(Icons.GEAR)} FOLLOW-UP PLANNER SESSION"),
        "",
        f"Spec: {highlight(spec_dir.name)}",
        muted("Adding follow-up work to completed spec."),
        "",
        muted("The agent will read your FOLLOWUP_REQUEST.md and add new subtasks."),
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print()

    # Start planning phase in task logger
    if task_logger:
        task_logger.start_phase(LogPhase.PLANNING, "Starting follow-up planning...")
        task_logger.set_session(1)

    # Create client with phase-specific model and thinking budget
    # Respects task_metadata.json configuration when no CLI override
    planning_model = get_phase_model(spec_dir, "planning", model)
    planning_thinking_budget = get_phase_thinking_budget(spec_dir, "planning")
    client = create_client(
        project_dir,
        spec_dir,
        planning_model,
        max_thinking_tokens=planning_thinking_budget,
    )

    # Generate follow-up planner prompt
    prompt = get_followup_planner_prompt(spec_dir)

    print_status("Running follow-up planner...", "progress")
    print()

    try:
        # Run single planning session
        async with client:
            status, response, trace_id = await run_agent_session(
                client, prompt, spec_dir, verbose, phase=LogPhase.PLANNING,
                spec_id=spec_dir.name,
                session_num=1,
                project_dir=project_dir,
                agent_type="planner",
            )

        # End planning phase in task logger
        if task_logger:
            task_logger.end_phase(
                LogPhase.PLANNING,
                success=(status != "error"),
                message="Follow-up planning session completed",
            )

        if status == "error":
            print()
            print_status("Follow-up planning failed", "error")
            status_manager.update(state=BuildState.ERROR)
            return False

        # Verify the plan was updated (should have pending subtasks now)
        plan_file = spec_dir / "implementation_plan.json"
        if plan_file.exists():
            plan = ImplementationPlan.load(plan_file)

            # Check if there are any pending subtasks
            all_subtasks = [c for p in plan.phases for c in p.subtasks]
            pending_subtasks = [c for c in all_subtasks if c.status.value == "pending"]

            if pending_subtasks:
                # Reset the plan status to in_progress (in case planner didn't)
                plan.reset_for_followup()
                await plan.async_save(plan_file)

                # Publish ROI metrics for the planning session
                try:
                    # Extract subtasks as dicts for ROI
                    subtasks_data = [
                        {"id": s.id, "description": s.description}
                        for s in all_subtasks
                    ]

                    # Load plan data as dict
                    with open(plan_file) as f:
                        plan_data = json.load(f)

                    # Determine complexity level from spec metadata
                    complexity_level = "standard"
                    task_metadata_file = spec_dir / "task_metadata.json"
                    if task_metadata_file.exists():
                        try:
                            with open(task_metadata_file) as f:
                                task_meta = json.load(f)
                                complexity_level = task_meta.get("complexity", "standard")
                        except Exception:
                            pass

                    await publish_planner_roi(
                        project_dir=project_dir,
                        spec_dir=spec_dir,
                        plan_data=plan_data,
                        subtasks=subtasks_data,
                        phases_count=len(plan.phases),
                        response_text=response,
                        trace_id=trace_id,
                        complexity_level=complexity_level,
                    )

                    # Flush Langfuse to ensure ROI is sent
                    if LANGFUSE_AVAILABLE and is_langfuse_ready():
                        flush_langfuse()

                except Exception as e:
                    logger.warning(f"Failed to publish planner ROI: {e}")

                print()
                content = [
                    bold(f"{icon(Icons.SUCCESS)} FOLLOW-UP PLANNING COMPLETE"),
                    "",
                    f"New pending subtasks: {highlight(str(len(pending_subtasks)))}",
                    f"Total subtasks: {len(all_subtasks)}",
                    "",
                    muted("Next steps:"),
                    f"  Run: {highlight(f'python auto-claude/run.py --spec {spec_dir.name}')}",
                ]
                print(box(content, width=70, style="heavy"))
                print()
                status_manager.update(state=BuildState.PAUSED)
                return True
            else:
                print()
                print_status(
                    "Warning: No pending subtasks found after planning", "warning"
                )
                print(muted("The planner may not have added new subtasks."))
                print(muted("Check implementation_plan.json manually."))
                status_manager.update(state=BuildState.PAUSED)
                return False
        else:
            print()
            print_status(
                "Error: implementation_plan.json not found after planning", "error"
            )
            status_manager.update(state=BuildState.ERROR)
            return False

    except Exception as e:
        print()
        print_status(f"Follow-up planning error: {e}", "error")
        if task_logger:
            task_logger.log_error(f"Follow-up planning error: {e}", LogPhase.PLANNING)
        status_manager.update(state=BuildState.ERROR)
        return False
