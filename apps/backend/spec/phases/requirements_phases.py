"""
Requirements and Research Phase Implementations
================================================

Phases for requirements gathering, historical context, and research.
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING

from task_logger import LogEntryType, LogPhase

from .. import requirements, validator
from .models import MAX_RETRIES, PhaseResult, phase_span

if TYPE_CHECKING:
    pass


class RequirementsPhaseMixin:
    """Mixin for requirements and research phase methods."""

    async def phase_historical_context(self) -> PhaseResult:
        """Retrieve historical context from Graphiti knowledge graph (if enabled)."""
        from graphiti_providers import get_graph_hints, is_graphiti_enabled

        spec_id = self.spec_dir.name if hasattr(self, "spec_dir") else None
        project_id = str(self.project_dir) if hasattr(self, "project_dir") else None
        hints_file = self.spec_dir / "graph_hints.json"

        with phase_span(
            "historical_context",
            spec_id=spec_id,
            project_id=project_id,
            metadata={"graphiti_enabled": is_graphiti_enabled()},
        ) as span:
            if hints_file.exists():
                self.ui.print_status("graph_hints.json already exists", "success")
                self.task_logger.log(
                    "Historical context already available",
                    LogEntryType.SUCCESS,
                    LogPhase.PLANNING,
                )
                if span:
                    span.update(metadata={"cached": True})
                return PhaseResult("historical_context", True, [str(hints_file)], [], 0)

            if not is_graphiti_enabled():
                self.ui.print_status(
                    "Graphiti not enabled, skipping historical context", "info"
                )
                self.task_logger.log(
                    "Knowledge graph not configured, skipping",
                    LogEntryType.INFO,
                    LogPhase.PLANNING,
                )
                validator.create_empty_hints(
                    self.spec_dir,
                    enabled=False,
                    reason="Graphiti not configured",
                )
                if span:
                    span.update(metadata={"skipped": True, "reason": "graphiti_disabled"})
                return PhaseResult("historical_context", True, [str(hints_file)], [], 0)

            # Get graph hints for this task
            task_query = self.task_description or ""

            # If we have requirements, use the full task description
            req = requirements.load_requirements(self.spec_dir)
            if req:
                task_query = req.get("task_description", task_query)

            if not task_query:
                self.ui.print_status(
                    "No task description for graph query, skipping", "warning"
                )
                validator.create_empty_hints(
                    self.spec_dir,
                    enabled=True,
                    reason="No task description available",
                )
                if span:
                    span.update(metadata={"skipped": True, "reason": "no_task_description"})
                return PhaseResult("historical_context", True, [str(hints_file)], [], 0)

            self.ui.print_status("Querying Graphiti knowledge graph...", "progress")
            self.task_logger.log(
                "Searching knowledge graph for relevant context...",
                LogEntryType.INFO,
                LogPhase.PLANNING,
            )

            try:
                hints = await get_graph_hints(
                    query=task_query,
                    project_id=str(self.project_dir),
                    max_results=10,
                )

                # Save hints to file
                with open(hints_file, "w") as f:
                    json.dump(
                        {
                            "enabled": True,
                            "query": task_query,
                            "hints": hints,
                            "hint_count": len(hints),
                            "created_at": datetime.now().isoformat(),
                        },
                        f,
                        indent=2,
                    )

                if hints:
                    self.ui.print_status(f"Retrieved {len(hints)} graph hints", "success")
                    self.task_logger.log(
                        f"Found {len(hints)} relevant insights from past sessions",
                        LogEntryType.SUCCESS,
                        LogPhase.PLANNING,
                    )
                else:
                    self.ui.print_status("No relevant graph hints found", "info")

                if span:
                    span.update(metadata={"hint_count": len(hints)})

                return PhaseResult("historical_context", True, [str(hints_file)], [], 0)

            except Exception as e:
                self.ui.print_status(f"Graph query failed: {e}", "warning")
                validator.create_empty_hints(
                    self.spec_dir,
                    enabled=True,
                    reason=f"Error: {str(e)}",
                )
                if span:
                    span.update(metadata={"error": str(e)})
                return PhaseResult(
                    "historical_context", True, [str(hints_file)], [str(e)], 0
                )

    async def phase_requirements(self, interactive: bool = True) -> PhaseResult:
        """Gather requirements from user or task description."""
        spec_id = self.spec_dir.name if hasattr(self, "spec_dir") else None
        project_id = str(self.project_dir) if hasattr(self, "project_dir") else None
        requirements_file = self.spec_dir / "requirements.json"

        with phase_span(
            "requirements",
            spec_id=spec_id,
            project_id=project_id,
            metadata={"interactive": interactive},
        ) as span:
            if requirements_file.exists():
                self.ui.print_status("requirements.json already exists", "success")
                if span:
                    span.update(metadata={"cached": True})
                return PhaseResult("requirements", True, [str(requirements_file)], [], 0)

            # Non-interactive mode with task description
            if self.task_description and not interactive:
                req = requirements.create_requirements_from_task(self.task_description)
                requirements.save_requirements(self.spec_dir, req)
                self.ui.print_status(
                    "Created requirements.json from task description", "success"
                )
                task_preview = (
                    self.task_description[:100] + "..."
                    if len(self.task_description) > 100
                    else self.task_description
                )
                self.task_logger.log(
                    f"Task: {task_preview}",
                    LogEntryType.SUCCESS,
                    LogPhase.PLANNING,
                )
                if span:
                    span.update(metadata={"mode": "from_task_description"})
                return PhaseResult("requirements", True, [str(requirements_file)], [], 0)

            # Interactive mode
            if interactive:
                try:
                    self.task_logger.log(
                        "Gathering requirements interactively...",
                        LogEntryType.INFO,
                        LogPhase.PLANNING,
                    )
                    req = requirements.gather_requirements_interactively(self.ui)

                    # Update task description for subsequent phases
                    self.task_description = req["task_description"]

                    requirements.save_requirements(self.spec_dir, req)
                    self.ui.print_status("Created requirements.json", "success")
                    if span:
                        span.update(metadata={"mode": "interactive"})
                    return PhaseResult(
                        "requirements", True, [str(requirements_file)], [], 0
                    )
                except (KeyboardInterrupt, EOFError):
                    print()
                    self.ui.print_status("Requirements gathering cancelled", "warning")
                    if span:
                        span.update(metadata={"cancelled": True})
                    return PhaseResult("requirements", False, [], ["User cancelled"], 0)

            # Fallback: create minimal requirements
            req = requirements.create_requirements_from_task(
                self.task_description or "Unknown task"
            )
            requirements.save_requirements(self.spec_dir, req)
            self.ui.print_status("Created minimal requirements.json", "success")
            if span:
                span.update(metadata={"mode": "fallback_minimal"})
            return PhaseResult("requirements", True, [str(requirements_file)], [], 0)

    async def phase_research(self) -> PhaseResult:
        """Research external integrations and validate assumptions."""
        spec_id = self.spec_dir.name if hasattr(self, "spec_dir") else None
        project_id = str(self.project_dir) if hasattr(self, "project_dir") else None
        research_file = self.spec_dir / "research.json"
        requirements_file = self.spec_dir / "requirements.json"

        with phase_span(
            "research",
            spec_id=spec_id,
            project_id=project_id,
        ) as span:
            if research_file.exists():
                self.ui.print_status("research.json already exists", "success")
                if span:
                    span.update(metadata={"cached": True})
                return PhaseResult("research", True, [str(research_file)], [], 0)

            if not requirements_file.exists():
                self.ui.print_status(
                    "No requirements.json - skipping research phase", "warning"
                )
                validator.create_minimal_research(
                    self.spec_dir,
                    reason="No requirements file available",
                )
                if span:
                    span.update(metadata={"skipped": True, "reason": "no_requirements"})
                return PhaseResult("research", True, [str(research_file)], [], 0)

            errors = []
            for attempt in range(MAX_RETRIES):
                self.ui.print_status(
                    f"Running research agent (attempt {attempt + 1})...", "progress"
                )

                context_str = f"""
**Requirements File**: {requirements_file}
**Research Output**: {research_file}

Read the requirements.json to understand what integrations/libraries are needed.
Research each external dependency to validate:
- Correct package names
- Actual API patterns
- Configuration requirements
- Known issues or gotchas

Output your findings to research.json.
"""
                success, output, _ = await self.run_agent_fn(
                    "spec_researcher.md",
                    additional_context=context_str,
                    phase_name="research",
                )

                if success and research_file.exists():
                    self.ui.print_status("Created research.json", "success")
                    if span:
                        span.update(metadata={"retries": attempt, "agent_success": True})
                    return PhaseResult("research", True, [str(research_file)], [], attempt)

                if success and not research_file.exists():
                    validator.create_minimal_research(
                        self.spec_dir,
                        reason="Agent completed but created no findings",
                    )
                    if span:
                        span.update(metadata={"retries": attempt, "fallback": True})
                    return PhaseResult("research", True, [str(research_file)], [], attempt)

                errors.append(f"Attempt {attempt + 1}: Research agent failed")

            validator.create_minimal_research(
                self.spec_dir,
                reason="Research agent failed after retries",
            )
            if span:
                span.update(metadata={"retries": MAX_RETRIES, "fallback": True, "errors": errors[:3]})
            return PhaseResult("research", True, [str(research_file)], errors, MAX_RETRIES)
