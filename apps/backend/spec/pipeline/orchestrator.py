"""
Spec Orchestrator
=================

Main orchestration logic for spec creation with dynamic complexity adaptation.
"""

import json
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from analysis.analyzers import analyze_project
from core.workspace.models import SpecNumberLock
from phase_config import get_thinking_budget
from prompts_pkg.project_context import should_refresh_project_index
from review import run_review_checkpoint
from task_logger import (
    LogEntryType,
    LogPhase,
    get_task_logger,
)
from ui import (
    Icons,
    box,
    highlight,
    icon,
    muted,
    print_key_value,
    print_section,
    print_status,
)

from .. import complexity, phases, requirements
from ..compaction import (
    format_phase_summaries,
    gather_phase_outputs,
    summarize_phase_output,
)
from ..validate_pkg.spec_validator import SpecValidator
from .agent_runner import AgentRunner
from .models import (
    PHASE_DISPLAY,
    cleanup_orphaned_pending_folders,
    create_spec_dir,
    get_specs_dir,
    rename_spec_dir_from_requirements,
)

# ROI Publishing
try:
    from analytics.roi_publisher import publish_feature_roi
    ROI_PUBLISHER_AVAILABLE = True
except ImportError:
    ROI_PUBLISHER_AVAILABLE = False

# Langfuse integration for tracing
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        trace_context,
        is_langfuse_ready,
        flush_langfuse,
    )
    LANGFUSE_AVAILABLE = True
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    trace_context = None
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


def extract_spec_artifacts(
    spec_dir: Path,
    project_dir: Path | None = None,
    trace_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Extract artifacts from spec directory with value attribution.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    Artifacts are concrete outputs that have measurable value:
    - spec_document ($500) - Complete spec.md document
    - diagram ($150 each) - Mermaid diagrams extracted from spec
    - requirement_captured ($50 each) - Each requirement from requirements.json
    - acceptance_criterion ($25 each) - Each acceptance criterion
    - context_discovered ($75) - Context from context.json
    - complexity_assessment ($100) - Complexity evaluation
    - implementation_plan ($200) - Plan summary

    Args:
        spec_dir: Path to the spec directory
        project_dir: Project root directory for local storage
        trace_id: Langfuse trace ID for linking

    Returns:
        Tuple of (artifacts list, langfuse_refs list)
    """
    from datetime import datetime

    artifacts = []
    spec_id = spec_dir.name if spec_dir else None

    # Extract spec.md as artifact ($500 value)
    spec_file = spec_dir / "spec.md"
    if spec_file.exists():
        try:
            spec_content = spec_file.read_text()

            # FULL CONTENT - no truncation
            artifacts.append({
                "type": "spec_document",
                "format": "markdown",
                "content": spec_content,  # FULL CONTENT - no truncation!
                "value_usd": 500,
                "description": "Complete specification document",
                "tab": "techlead",
                "file": str(spec_file),
            })

            # NOTE: Diagrams should be created via MCP tools by spec agents
            # NO regex extraction here - diagrams come from artifact storage
            # The spec.md contains diagrams for human readability only

        except Exception:
            pass

    # Extract requirements as artifacts ($50 each)
    requirements_file = spec_dir / "requirements.json"
    if requirements_file.exists():
        try:
            with open(requirements_file) as f:
                req_data = json.load(f)

            # Each user requirement is an artifact
            user_requirements = req_data.get("user_requirements", [])
            for i, req in enumerate(user_requirements):
                artifacts.append({
                    "type": "requirement_captured",
                    "format": "text",
                    "content": req,  # FULL CONTENT - no truncation!
                    "value_usd": 50,
                    "description": f"User requirement #{i+1}",
                    "tab": "business",
                })

            # Each acceptance criterion is an artifact
            acceptance_criteria = req_data.get("acceptance_criteria", [])
            for i, criterion in enumerate(acceptance_criteria):
                artifacts.append({
                    "type": "acceptance_criterion",
                    "format": "text",
                    "content": criterion,  # FULL CONTENT - no truncation!
                    "value_usd": 25,
                    "description": f"Acceptance criterion #{i+1}",
                    "tab": "dev",
                })

        except Exception:
            pass

    # Extract context as artifact ($75 value)
    context_file = spec_dir / "context.json"
    if context_file.exists():
        try:
            with open(context_file) as f:
                context_data = json.load(f)

            # Context discovery is valuable - store FULL context
            files_discovered = context_data.get("relevant_files", [])
            patterns_found = context_data.get("patterns", [])

            artifacts.append({
                "type": "context_discovered",
                "format": "json",
                "content": json.dumps({
                    "files_count": len(files_discovered),
                    "patterns_count": len(patterns_found),
                    "files": files_discovered,  # FULL LIST - no truncation!
                    "patterns": patterns_found,  # FULL LIST - no truncation!
                }, indent=2),
                "value_usd": 75,
                "description": f"Discovered {len(files_discovered)} relevant files and {len(patterns_found)} patterns",
                "tab": "techlead",
                "files_count": len(files_discovered),
            })

        except Exception:
            pass

    # Extract complexity assessment as artifact ($100 value)
    complexity_file = spec_dir / "complexity_assessment.json"
    if complexity_file.exists():
        try:
            with open(complexity_file) as f:
                complexity_data = json.load(f)

            complexity_level = complexity_data.get("complexity", "standard")
            confidence = complexity_data.get("confidence", 0)
            reasoning = complexity_data.get("reasoning", "")

            artifacts.append({
                "type": "complexity_assessment",
                "format": "json",
                "content": json.dumps({
                    "complexity": complexity_level,
                    "confidence": confidence,
                    "reasoning": reasoning,  # FULL CONTENT - no truncation!
                }, indent=2),
                "value_usd": 100,
                "description": f"Complexity: {complexity_level.upper()} (confidence: {confidence:.0%})",
                "tab": "techlead",
                "complexity_level": complexity_level,
            })

        except Exception:
            pass

    # Extract implementation plan as artifact (if exists)
    plan_file = spec_dir / "implementation_plan.json"
    if plan_file.exists():
        try:
            with open(plan_file) as f:
                plan_data = json.load(f)

            subtasks = plan_data.get("subtasks", [])
            if subtasks:
                artifacts.append({
                    "type": "implementation_plan",
                    "format": "json",
                    "content": json.dumps(plan_data, indent=2),  # FULL PLAN - no truncation!
                    "value_usd": 200,
                    "description": f"Implementation plan with {len(subtasks)} subtasks",
                    "tab": "dev",
                    "subtasks_count": len(subtasks),
                })

        except Exception:
            pass

    # Save artifacts locally and create Langfuse references
    langfuse_refs = []
    if ARTIFACT_STORAGE_AVAILABLE and project_dir:
        for artifact in artifacts:
            # Save full artifact locally
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_dir,
                spec_id=spec_id,
                trace_id=trace_id,
                agent_type="spec_creation",
                session_num=None,
            )

            if artifact_id:
                # Create lightweight reference for Langfuse
                storage_path = str(
                    _get_artifacts_dir(project_dir)
                    / datetime.now().strftime("%Y-%m-%d")
                    / f"{artifact_id}.json"
                )
                ref = create_langfuse_reference(artifact, artifact_id, storage_path)
                langfuse_refs.append(ref)
            else:
                # Fallback: use artifact as-is with FULL content
                langfuse_refs.append(artifact)
    else:
        # No storage available, use FULL content
        for artifact in artifacts:
            langfuse_refs.append(artifact)

    return artifacts, langfuse_refs


class SpecOrchestrator:
    """Orchestrates the spec creation process with dynamic complexity adaptation."""

    def __init__(
        self,
        project_dir: Path,
        task_description: str | None = None,
        spec_name: str | None = None,
        spec_dir: Path
        | None = None,  # Use existing spec directory (for UI integration)
        model: str = "claude-sonnet-4-5-20250929",
        thinking_level: str = "medium",  # Thinking level for extended thinking
        complexity_override: str | None = None,  # Force a specific complexity
        use_ai_assessment: bool = True,  # Use AI for complexity assessment (vs heuristics)
    ):
        """Initialize the spec orchestrator.

        Args:
            project_dir: The project root directory
            task_description: Optional task description
            spec_name: Optional spec name (for existing specs)
            spec_dir: Optional existing spec directory (for UI integration)
            model: The model to use for agent execution
            thinking_level: Thinking level (none, low, medium, high, ultrathink)
            complexity_override: Force a specific complexity level
            use_ai_assessment: Whether to use AI for complexity assessment
        """
        self.project_dir = Path(project_dir)
        self.task_description = task_description
        self.model = model
        self.thinking_level = thinking_level
        self.complexity_override = complexity_override
        self.use_ai_assessment = use_ai_assessment

        # Get the appropriate specs directory (within the project)
        self.specs_dir = get_specs_dir(self.project_dir)

        # Clean up orphaned pending folders before creating new spec
        cleanup_orphaned_pending_folders(self.specs_dir)

        # Complexity assessment (populated during run)
        self.assessment: complexity.ComplexityAssessment | None = None

        # Create/use spec directory
        if spec_dir:
            # Use provided spec directory (from UI)
            self.spec_dir = Path(spec_dir)
            self.spec_dir.mkdir(parents=True, exist_ok=True)
        elif spec_name:
            self.spec_dir = self.specs_dir / spec_name
            self.spec_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Use lock for coordinated spec numbering across worktrees
            with SpecNumberLock(self.project_dir) as lock:
                self.spec_dir = create_spec_dir(self.specs_dir, lock)
                # Create directory inside lock to ensure atomicity
                self.spec_dir.mkdir(parents=True, exist_ok=True)
        self.validator = SpecValidator(self.spec_dir)

        # Agent runner (initialized when needed)
        self._agent_runner: AgentRunner | None = None

        # Phase summaries for conversation compaction
        # Stores summaries from completed phases to provide context to subsequent phases
        self._phase_summaries: dict[str, str] = {}

        # Collect trace IDs from agent sessions for ROI publishing
        self._trace_ids: list[str] = []

    def _get_agent_runner(self) -> AgentRunner:
        """Get or create the agent runner.

        Returns:
            The agent runner instance
        """
        if self._agent_runner is None:
            task_logger = get_task_logger(self.spec_dir)
            self._agent_runner = AgentRunner(
                self.project_dir, self.spec_dir, self.model, task_logger
            )
        return self._agent_runner

    async def _run_agent(
        self,
        prompt_file: str,
        additional_context: str = "",
        interactive: bool = False,
        phase_name: str | None = None,
    ) -> tuple[bool, str, str | None]:
        """Run an agent with the given prompt.

        Args:
            prompt_file: The prompt file to use
            additional_context: Additional context to add
            interactive: Whether to run in interactive mode
            phase_name: Name of the phase (for thinking budget lookup)

        Returns:
            Tuple of (success, response_text, langfuse_trace_id)
        """
        runner = self._get_agent_runner()

        # Use user's configured thinking level for all spec phases
        thinking_budget = get_thinking_budget(self.thinking_level)

        # Format prior phase summaries for context
        prior_summaries = format_phase_summaries(self._phase_summaries)

        success, response, trace_id = await runner.run_agent(
            prompt_file,
            additional_context,
            interactive,
            thinking_budget=thinking_budget,
            prior_phase_summaries=prior_summaries if prior_summaries else None,
        )

        # Collect trace_id for ROI publishing
        if trace_id:
            self._trace_ids.append(trace_id)

        return success, response, trace_id

    async def _store_phase_summary(self, phase_name: str) -> None:
        """Summarize and store phase output for subsequent phases.

        Args:
            phase_name: Name of the completed phase
        """
        try:
            # Gather outputs from this phase
            phase_output = gather_phase_outputs(self.spec_dir, phase_name)
            if not phase_output:
                return

            # Summarize the output
            summary, _trace_id = await summarize_phase_output(
                phase_name,
                phase_output,
                model="claude-sonnet-4-5-20250929",  # Use Sonnet for efficiency
                target_words=500,
                project_dir=self.project_dir,  # Pass project dir for analytics tracking
            )

            if summary:
                self._phase_summaries[phase_name] = summary

        except Exception as e:
            # Don't fail the pipeline if summarization fails
            print_status(f"Phase summarization skipped: {e}", "warning")

    async def _ensure_fresh_project_index(self) -> None:
        """Ensure project_index.json is up-to-date before spec creation.

        Uses smart caching: only regenerates if dependency files (package.json,
        pyproject.toml, etc.) have been modified since the last index generation.
        This ensures QA agents receive accurate project capability information
        for dynamic MCP tool injection.
        """
        index_file = self.project_dir / ".auto-claude" / "project_index.json"

        if should_refresh_project_index(self.project_dir):
            if index_file.exists():
                print_status(
                    "Project dependencies changed, refreshing index...", "progress"
                )
            else:
                print_status("Generating project index...", "progress")

            try:
                # Regenerate project index
                analyze_project(self.project_dir, index_file)
                print_status("Project index updated", "success")
            except Exception as e:
                print_status(f"Project index refresh failed: {e}", "warning")
                # Don't fail spec creation if indexing fails - continue with cached/missing
        else:
            if index_file.exists():
                print_status("Using cached project index", "info")
            # If no index exists and no refresh needed, that's fine - capabilities will be empty

    async def run(self, interactive: bool = True, auto_approve: bool = False) -> bool:
        """Run the spec creation process with dynamic phase selection.

        Args:
            interactive: Whether to run in interactive mode for requirements gathering
            auto_approve: Whether to skip human review checkpoint and auto-approve

        Returns:
            True if spec creation and review completed successfully, False otherwise
        """
        # Import UI module for use in phases
        import ui

        # Initialize task logger for planning phase
        task_logger = get_task_logger(self.spec_dir)
        task_logger.start_phase(LogPhase.PLANNING, "Starting spec creation process")

        print(
            box(
                f"Spec Directory: {self.spec_dir}\n"
                f"Project: {self.project_dir}"
                + (f"\nTask: {self.task_description}" if self.task_description else ""),
                title="SPEC CREATION ORCHESTRATOR",
                style="heavy",
            )
        )

        # Smart cache: refresh project index if dependency files have changed
        await self._ensure_fresh_project_index()

        # Create phase executor
        phase_executor = phases.PhaseExecutor(
            project_dir=self.project_dir,
            spec_dir=self.spec_dir,
            task_description=self.task_description,
            spec_validator=self.validator,
            run_agent_fn=self._run_agent,
            task_logger=task_logger,
            ui_module=ui,
        )

        results = []
        phase_num = 0

        def run_phase(name: str, phase_fn: Callable) -> phases.PhaseResult:
            """Run a phase with proper numbering and display.

            Args:
                name: The phase name
                phase_fn: The phase function to execute

            Returns:
                The phase result
            """
            nonlocal phase_num
            phase_num += 1
            display_name, display_icon = PHASE_DISPLAY.get(
                name, (name.upper(), Icons.GEAR)
            )
            print_section(f"PHASE {phase_num}: {display_name}", display_icon)
            task_logger.log(
                f"Starting phase {phase_num}: {display_name}", LogEntryType.INFO
            )
            return phase_fn()

        # === PHASE 1: DISCOVERY ===
        result = await run_phase("discovery", phase_executor.phase_discovery)
        results.append(result)
        if not result.success:
            print_status("Discovery failed", "error")
            task_logger.end_phase(
                LogPhase.PLANNING, success=False, message="Discovery failed"
            )
            return False
        # Store summary for subsequent phases (compaction)
        await self._store_phase_summary("discovery")

        # === PHASE 2: REQUIREMENTS GATHERING ===
        result = await run_phase(
            "requirements", lambda: phase_executor.phase_requirements(interactive)
        )
        results.append(result)
        if not result.success:
            print_status("Requirements gathering failed", "error")
            task_logger.end_phase(
                LogPhase.PLANNING,
                success=False,
                message="Requirements gathering failed",
            )
            return False
        # Store summary for subsequent phases (compaction)
        await self._store_phase_summary("requirements")

        # Rename spec folder with better name from requirements
        rename_spec_dir_from_requirements(self.spec_dir)

        # Update task description from requirements
        req = requirements.load_requirements(self.spec_dir)
        if req:
            self.task_description = req.get("task_description", self.task_description)
            # Update phase executor's task description
            phase_executor.task_description = self.task_description

        # === CREATE LINEAR TASK (if enabled) ===
        await self._create_linear_task_if_enabled()

        # === PHASE 3: AI COMPLEXITY ASSESSMENT ===
        result = await run_phase(
            "complexity_assessment",
            lambda: self._phase_complexity_assessment_with_requirements(),
        )
        results.append(result)
        if not result.success:
            print_status("Complexity assessment failed", "error")
            task_logger.end_phase(
                LogPhase.PLANNING, success=False, message="Complexity assessment failed"
            )
            return False

        # Map of all available phases
        all_phases = {
            "historical_context": phase_executor.phase_historical_context,
            "research": phase_executor.phase_research,
            "context": phase_executor.phase_context,
            "spec_writing": phase_executor.phase_spec_writing,
            "self_critique": phase_executor.phase_self_critique,
            "planning": phase_executor.phase_planning,
            "validation": phase_executor.phase_validation,
            "quick_spec": phase_executor.phase_quick_spec,
        }

        # Get remaining phases to run based on complexity
        all_phases_to_run = self.assessment.phases_to_run()
        phases_to_run = [
            p for p in all_phases_to_run if p not in ["discovery", "requirements"]
        ]

        print()
        print(
            f"  Running {highlight(self.assessment.complexity.value.upper())} workflow"
        )
        print(f"  {muted('Remaining phases:')} {', '.join(phases_to_run)}")
        print()

        phases_executed = ["discovery", "requirements", "complexity_assessment"]
        for phase_name in phases_to_run:
            if phase_name not in all_phases:
                print_status(f"Unknown phase: {phase_name}, skipping", "warning")
                continue

            result = await run_phase(phase_name, all_phases[phase_name])
            results.append(result)
            phases_executed.append(phase_name)

            # Store summary for subsequent phases (compaction)
            if result.success:
                await self._store_phase_summary(phase_name)

            if not result.success:
                print()
                print_status(
                    f"Phase '{phase_name}' failed after {result.retries} retries",
                    "error",
                )
                print(f"  {muted('Errors:')}")
                for err in result.errors:
                    print(f"    {icon(Icons.ARROW_RIGHT)} {err}")
                print()
                print_status(
                    "Spec creation incomplete. Fix errors and retry.", "warning"
                )
                task_logger.log(
                    f"Phase '{phase_name}' failed: {'; '.join(result.errors)}",
                    LogEntryType.ERROR,
                )
                task_logger.end_phase(
                    LogPhase.PLANNING,
                    success=False,
                    message=f"Phase {phase_name} failed",
                )
                return False

        # Summary
        self._print_completion_summary(results, phases_executed)

        # End planning phase successfully
        task_logger.end_phase(
            LogPhase.PLANNING, success=True, message="Spec creation complete"
        )

        # Publish ROI metrics
        await self._publish_roi(phases_executed)

        # === HUMAN REVIEW CHECKPOINT ===
        return self._run_review_checkpoint(auto_approve)

    async def _create_linear_task_if_enabled(self) -> None:
        """Create a Linear task if Linear integration is enabled."""
        from linear_updater import create_linear_task, is_linear_enabled

        if not is_linear_enabled():
            return

        print_status("Creating Linear task...", "progress")
        linear_state = await create_linear_task(
            spec_dir=self.spec_dir,
            title=self.task_description or self.spec_dir.name,
            description=f"Auto-build spec: {self.spec_dir.name}",
        )
        if linear_state:
            print_status(f"Linear task created: {linear_state.task_id}", "success")
        else:
            print_status("Linear task creation failed (continuing without)", "warning")

    async def _phase_complexity_assessment_with_requirements(
        self,
    ) -> phases.PhaseResult:
        """Assess complexity after requirements are gathered (with full context).

        Returns:
            The phase result
        """
        task_logger = get_task_logger(self.spec_dir)
        assessment_file = self.spec_dir / "complexity_assessment.json"
        requirements_file = self.spec_dir / "requirements.json"

        # Load requirements for full context
        requirements_context = self._load_requirements_context(requirements_file)

        if self.complexity_override:
            # Manual override
            self.assessment = self._create_override_assessment()
        elif self.use_ai_assessment:
            # Run AI assessment
            self.assessment = await self._run_ai_assessment(task_logger)
        else:
            # Use heuristic assessment
            self.assessment = self._heuristic_assessment()
            self._print_assessment_info()

        # Show what phases will run
        self._print_phases_to_run()

        # Save assessment
        if not assessment_file.exists():
            complexity.save_assessment(self.spec_dir, self.assessment)

        return phases.PhaseResult(
            "complexity_assessment", True, [str(assessment_file)], [], 0
        )

    def _load_requirements_context(self, requirements_file: Path) -> str:
        """Load requirements context from file.

        Args:
            requirements_file: Path to the requirements file

        Returns:
            Formatted requirements context string
        """
        if not requirements_file.exists():
            return ""

        with open(requirements_file) as f:
            req = json.load(f)
            self.task_description = req.get("task_description", self.task_description)
            return f"""
**Task Description**: {req.get("task_description", "Not provided")}
**Workflow Type**: {req.get("workflow_type", "Not specified")}
**Services Involved**: {", ".join(req.get("services_involved", []))}
**User Requirements**:
{chr(10).join(f"- {r}" for r in req.get("user_requirements", []))}
**Acceptance Criteria**:
{chr(10).join(f"- {c}" for c in req.get("acceptance_criteria", []))}
**Constraints**:
{chr(10).join(f"- {c}" for c in req.get("constraints", []))}
"""

    def _create_override_assessment(self) -> complexity.ComplexityAssessment:
        """Create a complexity assessment from manual override.

        Returns:
            The complexity assessment
        """
        comp = complexity.Complexity(self.complexity_override)
        assessment = complexity.ComplexityAssessment(
            complexity=comp,
            confidence=1.0,
            reasoning=f"Manual override: {self.complexity_override}",
        )
        print_status(f"Complexity override: {comp.value.upper()}", "success")
        return assessment

    async def _run_ai_assessment(self, task_logger) -> complexity.ComplexityAssessment:
        """Run AI-based complexity assessment.

        Args:
            task_logger: The task logger instance

        Returns:
            The complexity assessment
        """
        print_status("Running AI complexity assessment...", "progress")
        task_logger.log(
            "Analyzing task complexity with AI...",
            LogEntryType.INFO,
            LogPhase.PLANNING,
        )
        assessment = await complexity.run_ai_complexity_assessment(
            self.spec_dir,
            self.task_description,
            self._run_agent,
        )

        if assessment:
            self._print_assessment_info(assessment)
            return assessment
        else:
            # Fall back to heuristic assessment
            print_status(
                "AI assessment failed, falling back to heuristics...", "warning"
            )
            return self._heuristic_assessment()

    def _print_assessment_info(
        self, assessment: complexity.ComplexityAssessment | None = None
    ) -> None:
        """Print complexity assessment information.

        Args:
            assessment: The assessment to print (defaults to self.assessment)
        """
        if assessment is None:
            assessment = self.assessment

        print_status(
            f"AI assessed complexity: {highlight(assessment.complexity.value.upper())}",
            "success",
        )
        print_key_value("Confidence", f"{assessment.confidence:.0%}")
        print_key_value("Reasoning", assessment.reasoning)

        if assessment.needs_research:
            print(f"  {muted(icon(Icons.ARROW_RIGHT) + ' Research phase enabled')}")
        if assessment.needs_self_critique:
            print(
                f"  {muted(icon(Icons.ARROW_RIGHT) + ' Self-critique phase enabled')}"
            )

    def _print_phases_to_run(self) -> None:
        """Print the list of phases that will be executed."""
        phase_list = self.assessment.phases_to_run()
        print()
        print(f"  Phases to run ({highlight(str(len(phase_list)))}):")
        for i, phase in enumerate(phase_list, 1):
            print(f"    {i}. {phase}")

    def _heuristic_assessment(self) -> complexity.ComplexityAssessment:
        """Fall back to heuristic-based complexity assessment.

        Returns:
            The complexity assessment
        """
        project_index = {}
        auto_build_index = self.project_dir / "auto-claude" / "project_index.json"
        if auto_build_index.exists():
            with open(auto_build_index) as f:
                project_index = json.load(f)

        analyzer = complexity.ComplexityAnalyzer(project_index)
        return analyzer.analyze(self.task_description or "")

    def _print_completion_summary(
        self, results: list[phases.PhaseResult], phases_executed: list[str]
    ) -> None:
        """Print the completion summary.

        Args:
            results: List of phase results
            phases_executed: List of executed phase names
        """
        files_created = []
        for r in results:
            for f in r.output_files:
                files_created.append(Path(f).name)

        print(
            box(
                f"Complexity: {self.assessment.complexity.value.upper()}\n"
                f"Phases run: {len(phases_executed) + 1}\n"
                f"Spec saved to: {self.spec_dir}\n\n"
                f"Files created:\n"
                + "\n".join(f"  {icon(Icons.SUCCESS)} {f}" for f in files_created),
                title=f"{icon(Icons.SUCCESS)} SPEC CREATION COMPLETE",
                style="heavy",
            )
        )

    async def _publish_roi(self, phases_executed: list[str]) -> None:
        """Publish ROI metrics for spec creation with artifact extraction.

        Extracts artifacts from the spec directory and publishes comprehensive
        ROI metrics including:
        - phases_completed: Number of phases executed
        - requirements_count: Number of requirements captured
        - complexity_level: Assessed complexity (simple/standard/complex)
        - context_files_found: Number of relevant files discovered

        Args:
            phases_executed: List of phases that were executed
        """
        if not ROI_PUBLISHER_AVAILABLE:
            return

        try:
            project_id = self.project_dir.name
            complexity_level = self.assessment.complexity.value if self.assessment else "standard"

            # Use the last collected trace_id for ROI attachment
            trace_id = self._trace_ids[-1] if self._trace_ids else None

            # Extract artifacts from spec directory
            # Now returns (artifacts, langfuse_refs) - artifacts have full content,
            # langfuse_refs have truncated previews
            artifacts, langfuse_refs = extract_spec_artifacts(
                self.spec_dir,
                project_dir=self.project_dir,
                trace_id=trace_id,
            )

            # Count metrics from artifacts
            requirements_count = sum(
                1 for a in artifacts if a.get("type") in ("requirement_captured", "acceptance_criterion")
            )
            context_files_found = 0
            for a in artifacts:
                if a.get("type") == "context_discovered":
                    context_files_found = a.get("files_count", 0)
                    break

            # Calculate total artifact value
            total_artifact_value = sum(a.get("value_usd", 0) for a in artifacts)

            result = await publish_feature_roi(
                feature_type="spec_creation",  # Use specific feature type for spec creation pipeline
                project_id=project_id,
                cost_usd=0.0,  # Will be calculated from traces
                tokens=0,
                metrics={
                    "phases_completed": len(phases_executed),
                    "complexity_level": complexity_level,
                    "requirements_count": requirements_count,
                    "context_files_found": context_files_found,
                    "requirements_gathered": requirements_count,  # For ROI calculator compatibility
                    "artifacts_count": len(artifacts),
                    "artifacts_value_usd": total_artifact_value,
                },
                spec_id=self.spec_dir.name,
                trace_id=trace_id,  # Pass trace_id for Langfuse score attachment
            )

            if result.get("success"):
                roi_pct = result.get("roi_percentage", 0)
                value = result.get("total_value_usd", 0)
                print_status(
                    f"Spec ROI: {roi_pct:.0f}% (${value:.2f} value from {len(phases_executed)} phases)",
                    "success",
                )
                if artifacts:
                    print_status(
                        f"Artifacts: {len(artifacts)} extracted (${total_artifact_value:.0f} value)",
                        "info",
                    )

            # Save artifacts to file for traceability
            await self._save_artifacts_report(artifacts, phases_executed, trace_id)

        except Exception as e:
            print_status(f"ROI publish failed: {e}", "warning")

    async def _save_artifacts_report(
        self,
        artifacts: list[dict[str, Any]],
        phases_executed: list[str],
        trace_id: str | None,
    ) -> None:
        """Save artifacts report to spec directory for traceability.

        Args:
            artifacts: List of extracted artifacts
            phases_executed: List of phases that were executed
            trace_id: Langfuse trace ID if available
        """
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "trace_id": trace_id,
                "spec_id": self.spec_dir.name,
                "project_id": self.project_dir.name,
                "complexity_level": self.assessment.complexity.value if self.assessment else "standard",
                "phases_executed": phases_executed,
                "phases_count": len(phases_executed),
                "artifacts": artifacts,
                "artifacts_count": len(artifacts),
                "total_value_usd": sum(a.get("value_usd", 0) for a in artifacts),
                "value_breakdown": {},
            }

            # Calculate value breakdown by artifact type
            for artifact in artifacts:
                artifact_type = artifact.get("type", "unknown")
                value = artifact.get("value_usd", 0)
                if artifact_type not in report["value_breakdown"]:
                    report["value_breakdown"][artifact_type] = {"count": 0, "total_value": 0}
                report["value_breakdown"][artifact_type]["count"] += 1
                report["value_breakdown"][artifact_type]["total_value"] += value

            # Save to spec directory
            report_file = self.spec_dir / "roi_artifacts.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, default=str)

        except Exception:
            # Don't fail if saving report fails
            pass

    def _run_review_checkpoint(self, auto_approve: bool) -> bool:
        """Run the human review checkpoint.

        Args:
            auto_approve: Whether to auto-approve without human review

        Returns:
            True if approved, False otherwise
        """
        print()
        print_section("HUMAN REVIEW CHECKPOINT", Icons.SEARCH)

        try:
            review_state = run_review_checkpoint(
                spec_dir=self.spec_dir,
                auto_approve=auto_approve,
            )

            if not review_state.is_approved():
                print()
                print_status("Build will not proceed without approval.", "warning")
                return False

        except SystemExit as e:
            if e.code != 0:
                return False
            return False
        except KeyboardInterrupt:
            print()
            print_status("Review interrupted. Run again to continue.", "info")
            return False

        return True

    # Backward compatibility methods for tests
    def _generate_spec_name(self, task_description: str) -> str:
        """Generate a spec name from task description (backward compatibility).

        This method is kept for backward compatibility with existing tests.
        The functionality has been moved to models.generate_spec_name.

        Args:
            task_description: The task description

        Returns:
            Generated spec name
        """
        from .models import generate_spec_name

        return generate_spec_name(task_description)

    def _rename_spec_dir_from_requirements(self) -> bool:
        """Rename spec directory from requirements (backward compatibility).

        This method is kept for backward compatibility with existing tests.
        The functionality has been moved to models.rename_spec_dir_from_requirements.

        Returns:
            True if successful or not needed, False on error
        """
        result = rename_spec_dir_from_requirements(self.spec_dir)
        # Update self.spec_dir if it was renamed
        if result and self.spec_dir.name.endswith("-pending"):
            # Find the renamed directory
            parent = self.spec_dir.parent
            prefix = self.spec_dir.name[:4]  # e.g., "001-"
            for candidate in parent.iterdir():
                if (
                    candidate.name.startswith(prefix)
                    and "pending" not in candidate.name
                ):
                    self.spec_dir = candidate
                    break
        return result
