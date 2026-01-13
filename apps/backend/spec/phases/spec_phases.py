"""
Spec Writing and Critique Phase Implementations
================================================

Phases for spec document creation and quality assurance.
"""

import json
from typing import TYPE_CHECKING

from .. import validator, writer
from .models import MAX_RETRIES, PhaseResult, phase_span

if TYPE_CHECKING:
    pass


class SpecPhaseMixin:
    """Mixin for spec writing and critique phase methods."""

    async def phase_quick_spec(self) -> PhaseResult:
        """Quick spec for simple tasks - combines context and spec in one step."""
        spec_id = self.spec_dir.name if hasattr(self, "spec_dir") else None
        project_id = str(self.project_dir) if hasattr(self, "project_dir") else None
        spec_file = self.spec_dir / "spec.md"
        plan_file = self.spec_dir / "implementation_plan.json"

        with phase_span(
            "quick_spec",
            spec_id=spec_id,
            project_id=project_id,
            metadata={"complexity": "simple"},
        ) as span:
            if spec_file.exists() and plan_file.exists():
                self.ui.print_status("Quick spec already exists", "success")
                if span:
                    span.update(metadata={"cached": True})
                return PhaseResult(
                    "quick_spec", True, [str(spec_file), str(plan_file)], [], 0
                )

            errors = []
            for attempt in range(MAX_RETRIES):
                self.ui.print_status(
                    f"Running quick spec agent (attempt {attempt + 1})...", "progress"
                )

                context_str = f"""
**Task**: {self.task_description}
**Spec Directory**: {self.spec_dir}
**Complexity**: SIMPLE (1-2 files expected)

This is a SIMPLE task. Create a minimal spec and implementation plan directly.
No research or extensive analysis needed.

Create:
1. A concise spec.md with just the essential sections
2. A simple implementation_plan.json with 1-2 subtasks
"""
                success, output, _ = await self.run_agent_fn(
                    "spec_quick.md",
                    additional_context=context_str,
                    phase_name="quick_spec",
                )

                if success and spec_file.exists():
                    # Create minimal plan if agent didn't
                    if not plan_file.exists():
                        writer.create_minimal_plan(self.spec_dir, self.task_description)

                    self.ui.print_status("Quick spec created", "success")
                    if span:
                        span.update(metadata={"retries": attempt, "agent_success": True})
                    return PhaseResult(
                        "quick_spec", True, [str(spec_file), str(plan_file)], [], attempt
                    )

                errors.append(f"Attempt {attempt + 1}: Quick spec agent failed")

            if span:
                span.update(metadata={"success": False, "errors": errors[:3]})
            return PhaseResult("quick_spec", False, [], errors, MAX_RETRIES)

    async def phase_spec_writing(self) -> PhaseResult:
        """Write the spec.md document."""
        spec_id = self.spec_dir.name if hasattr(self, "spec_dir") else None
        project_id = str(self.project_dir) if hasattr(self, "project_dir") else None
        spec_file = self.spec_dir / "spec.md"

        with phase_span(
            "spec_writing",
            spec_id=spec_id,
            project_id=project_id,
        ) as span:
            if spec_file.exists():
                result = self.spec_validator.validate_spec_document()
                if result.valid:
                    self.ui.print_status("spec.md already exists and is valid", "success")
                    if span:
                        span.update(metadata={"cached": True, "valid": True})
                    return PhaseResult("spec_writing", True, [str(spec_file)], [], 0)
                self.ui.print_status(
                    "spec.md exists but has issues, regenerating...", "warning"
                )
                if span:
                    span.update(metadata={"regenerating": True, "validation_errors": result.errors[:3]})

            errors = []
            for attempt in range(MAX_RETRIES):
                self.ui.print_status(
                    f"Running spec writer (attempt {attempt + 1})...", "progress"
                )

                success, output, _ = await self.run_agent_fn(
                    "spec_writer.md",
                    phase_name="spec_writing",
                )

                if success and spec_file.exists():
                    result = self.spec_validator.validate_spec_document()
                    if result.valid:
                        self.ui.print_status("Created valid spec.md", "success")
                        if span:
                            span.update(metadata={"retries": attempt, "valid": True})
                        return PhaseResult(
                            "spec_writing", True, [str(spec_file)], [], attempt
                        )
                    else:
                        errors.append(
                            f"Attempt {attempt + 1}: Spec invalid - {result.errors}"
                        )
                        self.ui.print_status(
                            f"Spec created but invalid: {result.errors}", "error"
                        )
                else:
                    errors.append(f"Attempt {attempt + 1}: Agent did not create spec.md")

            if span:
                span.update(metadata={"success": False, "errors": errors[:3]})
            return PhaseResult("spec_writing", False, [], errors, MAX_RETRIES)

    async def phase_self_critique(self) -> PhaseResult:
        """Self-critique the spec using extended thinking."""
        spec_id = self.spec_dir.name if hasattr(self, "spec_dir") else None
        project_id = str(self.project_dir) if hasattr(self, "project_dir") else None
        spec_file = self.spec_dir / "spec.md"
        research_file = self.spec_dir / "research.json"
        critique_file = self.spec_dir / "critique_report.json"

        with phase_span(
            "self_critique",
            spec_id=spec_id,
            project_id=project_id,
            metadata={"uses_extended_thinking": True},
        ) as span:
            if not spec_file.exists():
                self.ui.print_status("No spec.md to critique", "error")
                if span:
                    span.update(metadata={"error": "no_spec_file"})
                return PhaseResult(
                    "self_critique", False, [], ["spec.md does not exist"], 0
                )

            if critique_file.exists():
                with open(critique_file) as f:
                    critique = json.load(f)
                    if critique.get("issues_fixed", False) or critique.get(
                        "no_issues_found", False
                    ):
                        self.ui.print_status("Self-critique already completed", "success")
                        if span:
                            span.update(metadata={"cached": True})
                        return PhaseResult(
                            "self_critique", True, [str(critique_file)], [], 0
                        )

            errors = []
            for attempt in range(MAX_RETRIES):
                self.ui.print_status(
                    f"Running self-critique agent (attempt {attempt + 1})...", "progress"
                )

                context_str = f"""
**Spec File**: {spec_file}
**Research File**: {research_file}
**Critique Output**: {critique_file}

Use EXTENDED THINKING (ultrathink) to deeply analyze the spec.md:

1. **Technical Accuracy**: Do code examples match the research findings?
2. **Completeness**: Are all requirements covered? Edge cases handled?
3. **Consistency**: Do package names, APIs, and patterns match throughout?
4. **Feasibility**: Is the implementation approach realistic?

For each issue found:
- Fix it directly in spec.md
- Document what was fixed in critique_report.json

Output critique_report.json with:
{{
  "issues_found": [...],
  "issues_fixed": true/false,
  "no_issues_found": true/false,
  "critique_summary": "..."
}}
"""
                success, output, _ = await self.run_agent_fn(
                    "spec_critic.md",
                    additional_context=context_str,
                    phase_name="self_critique",
                )

                if success:
                    if not critique_file.exists():
                        validator.create_minimal_critique(
                            self.spec_dir,
                            reason="Agent completed without explicit issues",
                        )

                    result = self.spec_validator.validate_spec_document()
                    if result.valid:
                        self.ui.print_status(
                            "Self-critique completed, spec is valid", "success"
                        )
                        if span:
                            span.update(metadata={"retries": attempt, "valid": True})
                        return PhaseResult(
                            "self_critique", True, [str(critique_file)], [], attempt
                        )
                    else:
                        self.ui.print_status(
                            f"Spec invalid after critique: {result.errors}", "warning"
                        )
                        errors.append(
                            f"Attempt {attempt + 1}: Spec still invalid after critique"
                        )
                else:
                    errors.append(f"Attempt {attempt + 1}: Critique agent failed")

            validator.create_minimal_critique(
                self.spec_dir,
                reason="Critique failed after retries",
            )
            if span:
                span.update(metadata={"fallback": True, "errors": errors[:3]})
            return PhaseResult(
                "self_critique", True, [str(critique_file)], errors, MAX_RETRIES
            )
