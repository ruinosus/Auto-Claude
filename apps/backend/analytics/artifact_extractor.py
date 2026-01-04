"""
Unified Artifact Extraction Framework

This module provides a standardized pattern for extracting artifacts across all
runners and agents. It eliminates code duplication and ensures consistent
artifact quality.

Usage:
    from analytics.artifact_extractor import ArtifactExtractor, ArtifactBuilder

    # Create extractor for a specific domain
    extractor = ArtifactExtractor(
        project_dir=project_dir,
        agent_type="roadmap_generator",
        trace_id=trace_id,
        spec_id=spec_id,
    )

    # Build artifacts using the fluent API
    artifacts = []
    artifacts.append(
        ArtifactBuilder("roadmap_feature")
        .with_title("Health Check Endpoint")
        .with_priority("must")
        .with_description("Add /health endpoint...")
        .with_rationale("Critical for production...")
        .with_acceptance_criteria([...])
        .with_user_stories([...])
        .with_dependencies([...])
        .for_tab("business")
        .build()
    )

    # Save and get references
    full_artifacts, langfuse_refs = extractor.save_all(artifacts)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


# =============================================================================
# ARTIFACT TYPE REGISTRY
# =============================================================================

@dataclass
class ArtifactTypeConfig:
    """Configuration for an artifact type."""
    base_value: int
    max_value: int
    default_tab: str
    format: str = "markdown"
    description_template: str = "{type}: {title}"


# Central registry of all artifact types and their configurations
ARTIFACT_TYPE_REGISTRY: dict[str, ArtifactTypeConfig] = {
    # Roadmap artifacts
    "roadmap_vision": ArtifactTypeConfig(100, 100, "business", "markdown", "Strategic product vision"),
    "roadmap_phase": ArtifactTypeConfig(75, 100, "ops", "markdown", "Phase: {title}"),
    "roadmap_feature": ArtifactTypeConfig(50, 150, "business", "markdown", "Feature: {title}"),
    "roadmap_item": ArtifactTypeConfig(100, 150, "business", "markdown", "Roadmap item: {title}"),
    "priority_decision": ArtifactTypeConfig(25, 75, "business", "markdown", "Priority rationale: {title}"),
    "dependency_insight": ArtifactTypeConfig(75, 75, "techlead", "markdown", "Dependency analysis"),
    "milestone": ArtifactTypeConfig(50, 75, "ops", "markdown", "Milestone: {title}"),
    "target_audience": ArtifactTypeConfig(50, 50, "business", "text", "Target audience analysis"),

    # Competitor artifacts
    "competitor_insight": ArtifactTypeConfig(75, 100, "ops", "text", "Competitor: {title}"),
    "market_gap": ArtifactTypeConfig(100, 100, "ops", "text", "Market gap: {title}"),

    # Ideation artifacts
    "idea": ArtifactTypeConfig(50, 75, "business", "markdown", "Idea: {title}"),
    "recommendation": ArtifactTypeConfig(75, 100, "business", "markdown", "Recommendation: {title}"),
    "analysis_insight": ArtifactTypeConfig(100, 125, "business", "markdown", "Analysis: {title}"),

    # Insight artifacts
    "pattern_discovered": ArtifactTypeConfig(100, 150, "techlead", "markdown", "Pattern: {title}"),
    "gotcha_identified": ArtifactTypeConfig(150, 200, "dev", "markdown", "Gotcha: {title}"),
    "best_practice": ArtifactTypeConfig(75, 100, "techlead", "markdown", "Best practice: {title}"),
    "lesson_learned": ArtifactTypeConfig(50, 75, "dev", "markdown", "Lesson: {title}"),
    "file_insight": ArtifactTypeConfig(25, 50, "dev", "text", "File insight: {title}"),

    # Spec artifacts
    "spec_document": ArtifactTypeConfig(500, 500, "techlead", "markdown", "Specification document"),
    "requirement_captured": ArtifactTypeConfig(50, 75, "business", "text", "Requirement: {title}"),
    "acceptance_criterion": ArtifactTypeConfig(25, 50, "dev", "text", "Acceptance criterion: {title}"),
    "context_discovered": ArtifactTypeConfig(75, 100, "techlead", "json", "Context discovery"),
    "complexity_assessment": ArtifactTypeConfig(100, 100, "techlead", "json", "Complexity: {title}"),
    "implementation_plan": ArtifactTypeConfig(200, 300, "techlead", "markdown", "Implementation plan"),

    # QA artifacts
    "qa_verdict": ArtifactTypeConfig(75, 100, "dev", "markdown", "QA verdict: {title}"),
    "qa_finding": ArtifactTypeConfig(50, 100, "dev", "markdown", "QA finding: {title}"),
    "test_suggestion": ArtifactTypeConfig(50, 75, "dev", "markdown", "Test suggestion: {title}"),
    "acceptance_check": ArtifactTypeConfig(25, 50, "dev", "text", "Acceptance check: {title}"),
    "fix_applied": ArtifactTypeConfig(100, 150, "dev", "markdown", "Fix applied: {title}"),
    "issue_resolution": ArtifactTypeConfig(75, 100, "dev", "markdown", "Issue resolved: {title}"),
    "test_fix": ArtifactTypeConfig(50, 75, "dev", "markdown", "Test fix: {title}"),

    # Planner artifacts
    "subtask_definition": ArtifactTypeConfig(75, 100, "techlead", "markdown", "Subtask: {title}"),
    "architecture_decision": ArtifactTypeConfig(150, 200, "techlead", "markdown", "Architecture: {title}"),
    "risk_assessment": ArtifactTypeConfig(100, 150, "techlead", "markdown", "Risk: {title}"),

    # Coder artifacts
    "code_implementation": ArtifactTypeConfig(100, 200, "dev", "markdown", "Implementation: {title}"),
    "commit_summary": ArtifactTypeConfig(50, 75, "dev", "text", "Commit: {title}"),
    "refactoring": ArtifactTypeConfig(75, 150, "dev", "markdown", "Refactoring: {title}"),
    "test_written": ArtifactTypeConfig(75, 100, "dev", "markdown", "Test: {title}"),

    # GitHub/GitLab artifacts
    "pr_verdict": ArtifactTypeConfig(100, 150, "dev", "markdown", "PR verdict: {title}"),
    "pr_finding": ArtifactTypeConfig(50, 100, "dev", "markdown", "PR finding: {title}"),
    "structural_issue": ArtifactTypeConfig(75, 125, "techlead", "markdown", "Structural issue: {title}"),
    "blocker": ArtifactTypeConfig(100, 150, "dev", "markdown", "Blocker: {title}"),
    "pr_summary": ArtifactTypeConfig(75, 100, "dev", "markdown", "PR summary"),
    "ai_triage": ArtifactTypeConfig(50, 75, "dev", "markdown", "Triage: {title}"),

    # Merge artifacts
    "conflict_resolution": ArtifactTypeConfig(100, 150, "dev", "markdown", "Conflict resolved: {title}"),
    "merge_decision": ArtifactTypeConfig(75, 100, "techlead", "markdown", "Merge decision: {title}"),
    "code_choice": ArtifactTypeConfig(50, 75, "dev", "markdown", "Code choice: {title}"),
}


TabType = Literal["business", "techlead", "dev", "ops"]


# =============================================================================
# ARTIFACT BUILDER - Fluent API for constructing rich artifacts
# =============================================================================

@dataclass
class ArtifactBuilder:
    """
    Fluent builder for constructing high-quality artifacts.

    Usage:
        artifact = (
            ArtifactBuilder("roadmap_feature")
            .with_title("Health Check Endpoint")
            .with_priority("must")
            .with_description("Add /health endpoint...")
            .with_rationale("Critical for production deployments...")
            .with_acceptance_criteria(["GET /health returns 200", "..."])
            .with_user_stories(["As a DevOps engineer, I want..."])
            .with_dependencies(["feature-2"])
            .for_tab("business")
            .build()
        )
    """

    artifact_type: str
    _title: str = ""
    _description: str = ""
    _rationale: str = ""
    _priority: str = ""
    _complexity: str = ""
    _impact: str = ""
    _status: str = ""
    _phase: str = ""
    _effort: str = ""
    _acceptance_criteria: list[str] = field(default_factory=list)
    _user_stories: list[str] = field(default_factory=list)
    _dependencies: list[str] = field(default_factory=list)
    _custom_content: str = ""
    _custom_sections: dict[str, str] = field(default_factory=dict)
    _metadata: dict[str, Any] = field(default_factory=dict)
    _tab: TabType | None = None
    _value_override: int | None = None

    def with_title(self, title: str) -> "ArtifactBuilder":
        self._title = title
        return self

    def with_description(self, description: str) -> "ArtifactBuilder":
        self._description = description
        return self

    def with_rationale(self, rationale: str) -> "ArtifactBuilder":
        """Strategic rationale explaining WHY this matters."""
        self._rationale = rationale
        return self

    def with_priority(self, priority: str) -> "ArtifactBuilder":
        self._priority = priority
        return self

    def with_complexity(self, complexity: str) -> "ArtifactBuilder":
        self._complexity = complexity
        return self

    def with_impact(self, impact: str) -> "ArtifactBuilder":
        self._impact = impact
        return self

    def with_status(self, status: str) -> "ArtifactBuilder":
        self._status = status
        return self

    def with_phase(self, phase: str) -> "ArtifactBuilder":
        self._phase = phase
        return self

    def with_effort(self, effort: str) -> "ArtifactBuilder":
        self._effort = effort
        return self

    def with_acceptance_criteria(self, criteria: list[str]) -> "ArtifactBuilder":
        """Acceptance criteria defining WHAT success looks like."""
        self._acceptance_criteria = criteria
        return self

    def with_user_stories(self, stories: list[str]) -> "ArtifactBuilder":
        """User stories explaining WHO benefits."""
        self._user_stories = stories
        return self

    def with_dependencies(self, deps: list[str]) -> "ArtifactBuilder":
        """Dependencies explaining WHAT must come first."""
        self._dependencies = deps
        return self

    def with_custom_content(self, content: str) -> "ArtifactBuilder":
        """Set custom pre-formatted content (bypasses automatic content generation)."""
        self._custom_content = content
        return self

    def with_section(self, name: str, content: str) -> "ArtifactBuilder":
        """Add a custom section to the artifact."""
        self._custom_sections[name] = content
        return self

    def with_metadata(self, key: str, value: Any) -> "ArtifactBuilder":
        """Add custom metadata."""
        self._metadata[key] = value
        return self

    def for_tab(self, tab: TabType) -> "ArtifactBuilder":
        """Override the default tab assignment."""
        self._tab = tab
        return self

    def with_value(self, value: int) -> "ArtifactBuilder":
        """Override the calculated value."""
        self._value_override = value
        return self

    def _build_content(self) -> str:
        """Build rich markdown content from all fields."""
        if self._custom_content:
            return self._custom_content

        content = ""

        # Title as H1
        if self._title:
            content += f"# {self._title}\n\n"

        # Priority/classification bar
        classification_parts = []
        if self._priority:
            classification_parts.append(f"**Priority:** {self._priority.upper()}")
        if self._complexity:
            classification_parts.append(f"**Complexity:** {self._complexity}")
        if self._impact:
            classification_parts.append(f"**Impact:** {self._impact}")
        if self._status:
            classification_parts.append(f"**Status:** {self._status}")

        if classification_parts:
            content += " | ".join(classification_parts) + "\n\n"

        # Phase context
        if self._phase:
            content += f"**Phase:** {self._phase}\n\n"

        # Description section
        if self._description:
            content += f"## Description\n\n{self._description}\n\n"

        # Strategic Rationale - WHY this matters
        if self._rationale:
            content += f"## Strategic Rationale\n\n{self._rationale}\n\n"

        # User Stories - WHO benefits
        if self._user_stories:
            content += "## User Stories\n\n"
            for story in self._user_stories:
                content += f"- {story}\n"
            content += "\n"

        # Acceptance Criteria - WHAT success looks like
        if self._acceptance_criteria:
            content += "## Acceptance Criteria\n\n"
            for i, criterion in enumerate(self._acceptance_criteria):
                content += f"{i+1}. {criterion}\n"
            content += "\n"

        # Dependencies - WHAT must come first
        if self._dependencies:
            content += "## Dependencies\n\n"
            for dep in self._dependencies:
                content += f"- Requires: **{dep}**\n"
            content += "\n"

        # Effort
        if self._effort:
            content += f"**Estimated Effort:** {self._effort}\n\n"

        # Custom sections
        for section_name, section_content in self._custom_sections.items():
            content += f"## {section_name}\n\n{section_content}\n\n"

        return content.strip()

    def _calculate_value(self, config: ArtifactTypeConfig) -> int:
        """Calculate artifact value based on content richness."""
        if self._value_override is not None:
            return self._value_override

        value = config.base_value

        # Bonus for rich content
        if self._acceptance_criteria:
            value += 25
        if self._user_stories:
            value += 25
        if self._rationale:
            value += 15
        if self._dependencies:
            value += 10

        return min(value, config.max_value)

    def _determine_tab(self, config: ArtifactTypeConfig) -> TabType:
        """Determine appropriate tab based on content."""
        if self._tab:
            return self._tab

        # Smart tab assignment based on priority/complexity
        if self._priority and self._priority.lower() in ["must", "critical", "high"]:
            return "business"
        if self._complexity and self._complexity.lower() in ["high", "very_high"]:
            return "techlead"

        return config.default_tab  # type: ignore

    def build(self) -> dict[str, Any]:
        """Build the final artifact dictionary."""
        config = ARTIFACT_TYPE_REGISTRY.get(
            self.artifact_type,
            ArtifactTypeConfig(50, 100, "dev", "markdown", "{type}: {title}")
        )

        content = self._build_content()
        value = self._calculate_value(config)
        tab = self._determine_tab(config)

        # Build description from template
        description = config.description_template.format(
            type=self.artifact_type.replace("_", " ").title(),
            title=self._title or "Untitled"
        )

        # Build comprehensive metadata
        metadata = {
            "title": self._title,
            "priority": self._priority,
            "complexity": self._complexity,
            "impact": self._impact,
            "status": self._status,
            "phase": self._phase,
            "has_acceptance_criteria": bool(self._acceptance_criteria),
            "has_user_stories": bool(self._user_stories),
            "has_rationale": bool(self._rationale),
            "dependency_count": len(self._dependencies),
            **self._metadata,
        }

        # Filter out empty values
        metadata = {k: v for k, v in metadata.items() if v}

        return {
            "type": self.artifact_type,
            "format": config.format,
            "content": content,
            "value_usd": value,
            "description": description,
            "tab": tab,
            "metadata": metadata,
        }


# =============================================================================
# ARTIFACT EXTRACTOR - Unified save/reference pattern
# =============================================================================

class ArtifactExtractor:
    """
    Unified artifact extractor that handles saving and Langfuse reference creation.

    This eliminates the ~25 lines of duplicated code that appears in 12+ extraction functions.

    Usage:
        extractor = ArtifactExtractor(
            project_dir=project_dir,
            agent_type="roadmap_generator",
            trace_id=trace_id,
            spec_id=spec_id,
        )

        artifacts = [...]  # Build artifacts using ArtifactBuilder
        full_artifacts, langfuse_refs = extractor.save_all(artifacts)
    """

    def __init__(
        self,
        project_dir: Path | None = None,
        agent_type: str = "unknown",
        trace_id: str | None = None,
        spec_id: str | None = None,
        session_num: int | None = None,
    ):
        self.project_dir = project_dir
        self.agent_type = agent_type
        self.trace_id = trace_id
        self.spec_id = spec_id
        self.session_num = session_num

        # Try to import storage functions
        self._storage_available = False
        self._save_artifact_safe = None
        self._create_langfuse_reference = None
        self._get_artifacts_dir = None

        try:
            from analytics.artifact_storage import (
                save_artifact_safe,
                create_langfuse_reference,
                _get_artifacts_dir,
            )
            self._storage_available = True
            self._save_artifact_safe = save_artifact_safe
            self._create_langfuse_reference = create_langfuse_reference
            self._get_artifacts_dir = _get_artifacts_dir
        except ImportError:
            logger.warning("Artifact storage not available")

    def save_all(
        self,
        artifacts: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Save all artifacts and create Langfuse references.

        Args:
            artifacts: List of artifact dictionaries (from ArtifactBuilder.build())

        Returns:
            Tuple of (full_artifacts, langfuse_refs):
            - full_artifacts: Complete artifacts with all content
            - langfuse_refs: Lightweight references for Langfuse
        """
        if not self._storage_available or not self.project_dir:
            # No storage - return artifacts as both
            logger.debug(f"Storage unavailable, returning {len(artifacts)} artifacts as-is")
            return artifacts, artifacts

        langfuse_refs = []

        for artifact in artifacts:
            # Save full artifact locally
            artifact_id = self._save_artifact_safe(
                artifact=artifact,
                project_dir=self.project_dir,
                spec_id=self.spec_id,
                trace_id=self.trace_id,
                agent_type=self.agent_type,
                session_num=self.session_num,
            )

            if artifact_id:
                # Create lightweight reference for Langfuse
                artifacts_dir = self._get_artifacts_dir(self.project_dir)
                storage_path = str(
                    (artifacts_dir / datetime.now().strftime("%Y-%m-%d") / f"{artifact_id}.json")
                )
                ref = self._create_langfuse_reference(artifact, artifact_id, storage_path)
                langfuse_refs.append(ref)
            else:
                # Fallback: if storage fails, include full artifact as ref
                langfuse_refs.append(artifact)

        logger.debug(
            f"Extracted {len(artifacts)} artifacts, created {len(langfuse_refs)} refs"
        )
        return artifacts, langfuse_refs


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def build_feature_artifact(
    title: str,
    description: str = "",
    priority: str = "medium",
    rationale: str = "",
    acceptance_criteria: list[str] | None = None,
    user_stories: list[str] | None = None,
    dependencies: list[str] | None = None,
    complexity: str = "",
    impact: str = "",
    status: str = "",
    phase: str = "",
) -> dict[str, Any]:
    """
    Convenience function to build a feature artifact with common fields.

    This replaces the manual dict construction in extraction functions.
    """
    builder = (
        ArtifactBuilder("roadmap_feature")
        .with_title(title)
        .with_description(description)
        .with_priority(priority)
    )

    if rationale:
        builder.with_rationale(rationale)
    if acceptance_criteria:
        builder.with_acceptance_criteria(acceptance_criteria)
    if user_stories:
        builder.with_user_stories(user_stories)
    if dependencies:
        builder.with_dependencies(dependencies)
    if complexity:
        builder.with_complexity(complexity)
    if impact:
        builder.with_impact(impact)
    if status:
        builder.with_status(status)
    if phase:
        builder.with_phase(phase)

    return builder.build()


def build_insight_artifact(
    artifact_type: str,
    content: str,
    title: str = "",
    value_override: int | None = None,
) -> dict[str, Any]:
    """
    Convenience function to build an insight artifact (pattern, gotcha, lesson).
    """
    builder = (
        ArtifactBuilder(artifact_type)
        .with_title(title)
        .with_custom_content(content)
    )

    if value_override:
        builder.with_value(value_override)

    return builder.build()


def build_qa_artifact(
    artifact_type: str,
    title: str,
    description: str,
    severity: str = "",
    file_path: str = "",
    line_number: int | None = None,
    fix_required: bool = False,
) -> dict[str, Any]:
    """
    Convenience function to build a QA artifact.
    """
    builder = (
        ArtifactBuilder(artifact_type)
        .with_title(title)
        .with_description(description)
    )

    if severity:
        builder.with_metadata("severity", severity)
    if file_path:
        builder.with_metadata("file_path", file_path)
    if line_number:
        builder.with_metadata("line_number", line_number)
    if fix_required:
        builder.with_metadata("fix_required", fix_required)

    return builder.build()
