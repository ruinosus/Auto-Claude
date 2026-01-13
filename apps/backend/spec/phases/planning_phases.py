"""
Planning and Validation Phase Implementations
==============================================

Phases for implementation planning and final validation.
"""

from typing import TYPE_CHECKING

from task_logger import LogEntryType, LogPhase

from .. import writer
from .models import MAX_RETRIES, PhaseResult, phase_span

if TYPE_CHECKING:
    pass


class PlanningPhaseMixin:
    """Mixin for planning and validation phase methods."""

    async def phase_planning(self) -> PhaseResult:
        """Create the implementation plan."""
        from ..validate_pkg.auto_fix import auto_fix_plan

        spec_id = self.spec_dir.name if hasattr(self, "spec_dir") else None
        project_id = str(self.project_dir) if hasattr(self, "project_dir") else None
        plan_file = self.spec_dir / "implementation_plan.json"

        with phase_span(
            "planning",
            spec_id=spec_id,
            project_id=project_id,
        ) as span:
            if plan_file.exists():
                result = self.spec_validator.validate_implementation_plan()
                if result.valid:
                    self.ui.print_status(
                        "implementation_plan.json already exists and is valid", "success"
                    )
                    if span:
                        span.update(metadata={"cached": True, "valid": True})
                    return PhaseResult("planning", True, [str(plan_file)], [], 0)
                self.ui.print_status("Plan exists but invalid, regenerating...", "warning")
                if span:
                    span.update(metadata={"regenerating": True})

            errors = []

            # Try Python script first (deterministic)
            self.ui.print_status("Trying planner.py (deterministic)...", "progress")
            success, output = self._run_script(
                "planner.py", ["--spec-dir", str(self.spec_dir)]
            )

            if success and plan_file.exists():
                result = self.spec_validator.validate_implementation_plan()
                if result.valid:
                    self.ui.print_status(
                        "Created valid implementation_plan.json via script", "success"
                    )
                    stats = writer.get_plan_stats(self.spec_dir)
                    if stats:
                        self.task_logger.log(
                            f"Implementation plan created with {stats.get('total_subtasks', 0)} subtasks",
                            LogEntryType.SUCCESS,
                            LogPhase.PLANNING,
                        )
                        if span:
                            span.update(metadata={
                                "method": "script",
                                "subtask_count": stats.get("total_subtasks", 0),
                            })
                    return PhaseResult("planning", True, [str(plan_file)], [], 0)
                else:
                    if auto_fix_plan(self.spec_dir):
                        result = self.spec_validator.validate_implementation_plan()
                        if result.valid:
                            self.ui.print_status(
                                "Auto-fixed implementation_plan.json", "success"
                            )
                            if span:
                                span.update(metadata={"method": "script", "auto_fixed": True})
                            return PhaseResult("planning", True, [str(plan_file)], [], 0)
                    errors.append(f"Script output invalid: {result.errors}")

            # Fall back to agent
            self.ui.print_status("Falling back to planner agent...", "progress")
            for attempt in range(MAX_RETRIES):
                self.ui.print_status(
                    f"Running planner agent (attempt {attempt + 1})...", "progress"
                )

                success, output, _ = await self.run_agent_fn(
                    "planner.md",
                    phase_name="planning",
                )

                if success and plan_file.exists():
                    result = self.spec_validator.validate_implementation_plan()
                    if result.valid:
                        self.ui.print_status(
                            "Created valid implementation_plan.json via agent", "success"
                        )
                        if span:
                            span.update(metadata={"method": "agent", "retries": attempt})
                        return PhaseResult("planning", True, [str(plan_file)], [], attempt)
                    else:
                        if auto_fix_plan(self.spec_dir):
                            result = self.spec_validator.validate_implementation_plan()
                            if result.valid:
                                self.ui.print_status(
                                    "Auto-fixed implementation_plan.json", "success"
                                )
                                if span:
                                    span.update(metadata={
                                        "method": "agent",
                                        "retries": attempt,
                                        "auto_fixed": True,
                                    })
                                return PhaseResult(
                                    "planning", True, [str(plan_file)], [], attempt
                                )
                        errors.append(f"Agent attempt {attempt + 1}: {result.errors}")
                        self.ui.print_status("Plan created but invalid", "error")
                else:
                    errors.append(f"Agent attempt {attempt + 1}: Did not create plan file")

            if span:
                span.update(metadata={"success": False, "errors": errors[:3]})
            return PhaseResult("planning", False, [], errors, MAX_RETRIES)

    async def phase_validation(self) -> PhaseResult:
        """Final validation of all spec files with auto-fix retry."""
        spec_id = self.spec_dir.name if hasattr(self, "spec_dir") else None
        project_id = str(self.project_dir) if hasattr(self, "project_dir") else None

        with phase_span(
            "validation",
            spec_id=spec_id,
            project_id=project_id,
        ) as span:
            for attempt in range(MAX_RETRIES):
                results = self.spec_validator.validate_all()
                all_valid = all(r.valid for r in results)

                for result in results:
                    if result.valid:
                        self.ui.print_status(f"{result.checkpoint}: PASS", "success")
                    else:
                        self.ui.print_status(f"{result.checkpoint}: FAIL", "error")
                    for err in result.errors:
                        print(f"    {self.ui.muted('Error:')} {err}")

                if all_valid:
                    print()
                    self.ui.print_status("All validation checks passed", "success")
                    if span:
                        span.update(metadata={
                            "valid": True,
                            "retries": attempt,
                            "checkpoints_passed": len(results),
                        })
                    return PhaseResult("validation", True, [], [], attempt)

                # If not valid, try to auto-fix with AI agent
                if attempt < MAX_RETRIES - 1:
                    print()
                    self.ui.print_status(
                        f"Attempting auto-fix (attempt {attempt + 1}/{MAX_RETRIES - 1})...",
                        "progress",
                    )

                    # Collect all errors for the fixer agent
                    error_details = []
                    for result in results:
                        if not result.valid:
                            error_details.append(
                                f"**{result.checkpoint}** validation failed:"
                            )
                            for err in result.errors:
                                error_details.append(f"  - {err}")
                            if result.fixes:
                                error_details.append("  Suggested fixes:")
                                for fix in result.fixes:
                                    error_details.append(f"    - {fix}")

                    context_str = f"""
**Spec Directory**: {self.spec_dir}

## Validation Errors to Fix

{chr(10).join(error_details)}

## Files in Spec Directory

The following files exist in the spec directory:
- context.json
- requirements.json
- spec.md
- implementation_plan.json
- project_index.json (if exists)

Read the failed files, understand the errors, and fix them.
"""
                    success, output, _ = await self.run_agent_fn(
                        "validation_fixer.md",
                        additional_context=context_str,
                        phase_name="validation",
                    )

                    if not success:
                        self.ui.print_status("Auto-fix agent failed", "warning")

            # All retries exhausted
            errors = [f"{r.checkpoint}: {err}" for r in results for err in r.errors]
            if span:
                span.update(metadata={
                    "valid": False,
                    "retries": MAX_RETRIES,
                    "errors": errors[:5],
                })
            return PhaseResult("validation", False, [], errors, MAX_RETRIES)
