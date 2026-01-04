"""
Roadmap generation orchestrator.

Coordinates all phases of the roadmap generation process.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from client import create_client
from debug import debug, debug_error, debug_section, debug_success, debug_warning
from init import init_auto_claude_dir
from phase_config import get_thinking_budget, resolve_model_id
from ui import Icons, box, icon, muted, print_section, print_status

# ROI Publishing
try:
    from analytics.roi_publisher import publish_roadmap_roi
    ROI_PUBLISHER_AVAILABLE = True
except ImportError:
    ROI_PUBLISHER_AVAILABLE = False

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

from .competitor_analyzer import CompetitorAnalyzer
from .executor import AgentExecutor, ScriptExecutor
from .graph_integration import GraphHintsProvider
from .phases import DiscoveryPhase, FeaturesPhase, ProjectIndexPhase


# =============================================================================
# ARTIFACT EXTRACTION
# =============================================================================


def extract_roadmap_artifacts(
    roadmap: dict[str, Any],
    project_dir: Path | None = None,
    trace_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Extract HIGH-QUALITY roadmap artifacts from the generated roadmap.

    This function extracts RICH content from roadmap data, including:
    - Strategic rationale and justifications
    - Acceptance criteria and user stories
    - Dependencies and relationships
    - Phase context and milestones

    Artifacts extracted:
    - roadmap_vision ($100) - strategic vision with audience context
    - roadmap_phase ($75 each) - phase with milestones and feature list
    - roadmap_feature ($50-150) - feature with full context (value scales with richness)
    - priority_decision ($25-75) - prioritization rationale with impact analysis
    - dependency_insight ($50) - cross-feature dependency analysis

    Args:
        roadmap: The roadmap dict from roadmap.json
        project_dir: Project root directory for local storage
        trace_id: Langfuse trace ID for linking

    Returns:
        Tuple of (local_artifacts, langfuse_refs):
        - local_artifacts: Full artifacts for local processing
        - langfuse_refs: Truncated references for Langfuse
    """
    artifacts = []

    # Build lookup maps for enrichment
    phases_by_id = {p.get("id"): p for p in roadmap.get("phases", []) if isinstance(p, dict)}
    features_by_id = {f.get("id"): f for f in roadmap.get("features", []) if isinstance(f, dict)}

    # =========================================================================
    # VISION ARTIFACT - Enriched with target audience
    # =========================================================================
    vision = roadmap.get("vision", "")
    target_audience = roadmap.get("target_audience", {})

    if vision:
        vision_content = f"# Strategic Vision\n\n{vision}\n"

        # Enrich with target audience context
        if isinstance(target_audience, dict) and target_audience:
            primary = target_audience.get("primary", "")
            secondary = target_audience.get("secondary", [])
            if primary:
                vision_content += f"\n## Target Audience\n\n**Primary:** {primary}\n"
            if secondary:
                secondary_list = secondary if isinstance(secondary, list) else [secondary]
                vision_content += f"\n**Secondary:**\n"
                for s in secondary_list:
                    vision_content += f"- {s}\n"

        # Add project context
        project_name = roadmap.get("project_name", "")
        if project_name:
            vision_content = f"**Project:** {project_name}\n\n{vision_content}"

        artifacts.append({
            "type": "roadmap_vision",
            "format": "markdown",
            "content": vision_content,
            "value_usd": 100,
            "description": "Strategic product vision with target audience",
            "tab": "business",
            "metadata": {
                "project_name": project_name,
                "has_audience": bool(target_audience),
            },
        })

    # =========================================================================
    # PHASE ARTIFACTS - Enriched with milestones and feature context
    # =========================================================================
    phases = roadmap.get("phases", [])
    for i, phase in enumerate(phases):
        if not isinstance(phase, dict):
            continue

        phase_id = phase.get("id", f"phase-{i+1}")
        phase_name = phase.get("name", f"Phase {i+1}")
        phase_description = phase.get("description", "")
        phase_status = phase.get("status", "planned")
        phase_order = phase.get("order", i + 1)
        phase_feature_ids = phase.get("features", [])
        milestones = phase.get("milestones", [])

        # Build rich phase content
        content = f"# {phase_name}\n\n"
        content += f"**Order:** {phase_order} | **Status:** {phase_status}\n\n"

        if phase_description:
            content += f"## Overview\n\n{phase_description}\n\n"

        # Add milestones with full detail
        if milestones:
            content += "## Milestones\n\n"
            for j, milestone in enumerate(milestones):
                if isinstance(milestone, dict):
                    m_title = milestone.get("title", f"Milestone {j+1}")
                    m_desc = milestone.get("description", "")
                    m_status = milestone.get("status", "planned")
                    m_features = milestone.get("features", [])

                    content += f"### {m_title}\n"
                    content += f"**Status:** {m_status}\n\n"
                    if m_desc:
                        content += f"{m_desc}\n\n"
                    if m_features:
                        content += "**Features included:**\n"
                        for fid in m_features:
                            feat = features_by_id.get(fid, {})
                            f_title = feat.get("title", feat.get("name", fid))
                            f_priority = feat.get("priority", "")
                            content += f"- {f_title}"
                            if f_priority:
                                content += f" [{f_priority.upper()}]"
                            content += "\n"
                        content += "\n"

        # List all features in this phase
        if phase_feature_ids:
            content += "## Features in This Phase\n\n"
            for fid in phase_feature_ids:
                feat = features_by_id.get(fid, {})
                if feat:
                    f_title = feat.get("title", feat.get("name", fid))
                    f_priority = feat.get("priority", "unknown")
                    f_impact = feat.get("impact", "")
                    f_complexity = feat.get("complexity", "")
                    content += f"- **{f_title}** [{f_priority.upper()}]"
                    if f_impact:
                        content += f" - Impact: {f_impact}"
                    if f_complexity:
                        content += f", Complexity: {f_complexity}"
                    content += "\n"

        artifacts.append({
            "type": "roadmap_phase",
            "format": "markdown",
            "content": content,
            "value_usd": 75,
            "description": f"Phase {phase_order}: {phase_name}",
            "tab": "ops",
            "metadata": {
                "phase_id": phase_id,
                "phase_index": i,
                "phase_name": phase_name,
                "phase_order": phase_order,
                "status": phase_status,
                "feature_count": len(phase_feature_ids),
                "milestone_count": len(milestones),
            },
        })

    # =========================================================================
    # FEATURE ARTIFACTS - Full rich content with all available data
    # =========================================================================
    features = roadmap.get("features", [])
    for i, feature in enumerate(features):
        if not isinstance(feature, dict):
            continue

        # Extract ALL available fields
        feature_id = feature.get("id", f"feature-{i+1}")
        feature_name = feature.get("title", feature.get("name", f"Feature {i+1}"))
        feature_desc = feature.get("description", "")
        feature_rationale = feature.get("rationale", "")
        feature_priority = feature.get("priority", "unknown")
        feature_complexity = feature.get("complexity", "")
        feature_impact = feature.get("impact", "")
        feature_status = feature.get("status", "")
        feature_phase_id = feature.get("phase_id", "")
        feature_dependencies = feature.get("dependencies", [])
        acceptance_criteria = feature.get("acceptance_criteria", [])
        user_stories = feature.get("user_stories", [])

        # Calculate value based on content richness
        base_value = 50
        if acceptance_criteria:
            base_value += 25  # Rich acceptance criteria adds value
        if user_stories:
            base_value += 25  # User stories add value
        if feature_rationale:
            base_value += 25  # Strategic rationale adds value
        if feature_dependencies:
            base_value += 25  # Dependency awareness adds value

        # Build RICH feature content
        content = f"# {feature_name}\n\n"

        # Priority and classification bar
        content += f"**Priority:** {feature_priority.upper()}"
        if feature_complexity:
            content += f" | **Complexity:** {feature_complexity}"
        if feature_impact:
            content += f" | **Impact:** {feature_impact}"
        if feature_status:
            content += f" | **Status:** {feature_status}"
        content += "\n\n"

        # Phase context
        if feature_phase_id:
            phase = phases_by_id.get(feature_phase_id, {})
            phase_name = phase.get("name", feature_phase_id)
            content += f"**Phase:** {phase_name}\n\n"

        # Description
        if feature_desc:
            content += f"## Description\n\n{feature_desc}\n\n"

        # Strategic Rationale - WHY this matters
        if feature_rationale:
            content += f"## Strategic Rationale\n\n{feature_rationale}\n\n"

        # User Stories - WHO benefits
        if user_stories:
            content += "## User Stories\n\n"
            for story in user_stories:
                content += f"- {story}\n"
            content += "\n"

        # Acceptance Criteria - WHAT success looks like
        if acceptance_criteria:
            content += "## Acceptance Criteria\n\n"
            for j, criterion in enumerate(acceptance_criteria):
                content += f"{j+1}. {criterion}\n"
            content += "\n"

        # Dependencies - WHAT must come first
        if feature_dependencies:
            content += "## Dependencies\n\n"
            for dep_id in feature_dependencies:
                dep_feat = features_by_id.get(dep_id, {})
                dep_name = dep_feat.get("title", dep_feat.get("name", dep_id))
                content += f"- Requires: **{dep_name}**\n"
            content += "\n"

        # Determine appropriate tab
        if feature_priority in ["must", "critical"]:
            tab = "business"  # High priority = business visibility
        elif feature_complexity in ["high", "very_high"]:
            tab = "techlead"  # High complexity = tech lead visibility
        else:
            tab = "ops"  # Default to ops

        artifacts.append({
            "type": "roadmap_feature",
            "format": "markdown",
            "content": content,
            "value_usd": min(base_value, 150),  # Cap at 150
            "description": f"Feature: {feature_name} [{feature_priority.upper()}]",
            "tab": tab,
            "metadata": {
                "feature_id": feature_id,
                "feature_index": i,
                "feature_name": feature_name,
                "priority": feature_priority,
                "complexity": feature_complexity,
                "impact": feature_impact,
                "status": feature_status,
                "phase_id": feature_phase_id,
                "has_acceptance_criteria": bool(acceptance_criteria),
                "has_user_stories": bool(user_stories),
                "has_rationale": bool(feature_rationale),
                "dependency_count": len(feature_dependencies),
            },
        })

    # =========================================================================
    # PRIORITY DECISION ARTIFACTS - Strategic rationale with context
    # =========================================================================
    for feature in features:
        if not isinstance(feature, dict):
            continue

        rationale = feature.get("rationale", "")
        if not rationale:
            continue

        feature_name = feature.get("title", feature.get("name", "Unknown"))
        priority = feature.get("priority", "unknown")
        impact = feature.get("impact", "")
        complexity = feature.get("complexity", "")

        # Build richer priority decision content
        content = f"# Priority Decision: {feature_name}\n\n"
        content += f"**Priority Level:** {priority.upper()}\n"
        if impact:
            content += f"**Expected Impact:** {impact}\n"
        if complexity:
            content += f"**Implementation Complexity:** {complexity}\n"
        content += f"\n## Rationale\n\n{rationale}\n"

        # Calculate value based on priority level
        priority_values = {
            "must": 75,
            "critical": 75,
            "should": 50,
            "could": 35,
            "wont": 25,
        }
        value = priority_values.get(priority.lower(), 25)

        artifacts.append({
            "type": "priority_decision",
            "format": "markdown",
            "content": content,
            "value_usd": value,
            "description": f"Priority rationale: {feature_name} [{priority.upper()}]",
            "tab": "business",
            "metadata": {
                "feature_name": feature_name,
                "priority": priority,
                "impact": impact,
                "complexity": complexity,
            },
        })

    # =========================================================================
    # DEPENDENCY INSIGHT ARTIFACT - Cross-feature dependency analysis
    # =========================================================================
    dependency_map = {}
    for feature in features:
        if not isinstance(feature, dict):
            continue
        deps = feature.get("dependencies", [])
        if deps:
            feature_name = feature.get("title", feature.get("name", "Unknown"))
            dependency_map[feature_name] = []
            for dep_id in deps:
                dep_feat = features_by_id.get(dep_id, {})
                dep_name = dep_feat.get("title", dep_feat.get("name", dep_id))
                dependency_map[feature_name].append(dep_name)

    if dependency_map:
        dep_content = "# Feature Dependency Analysis\n\n"
        dep_content += "This document maps dependencies between roadmap features to help with implementation sequencing.\n\n"

        # Find features with no dependencies (can start immediately)
        all_features = {f.get("title", f.get("name", "")) for f in features if isinstance(f, dict)}
        dependent_features = set(dependency_map.keys())
        independent_features = all_features - dependent_features

        if independent_features:
            dep_content += "## Independent Features (No Dependencies)\n\n"
            dep_content += "These features can be started immediately:\n\n"
            for feat in sorted(independent_features):
                if feat:
                    dep_content += f"- {feat}\n"
            dep_content += "\n"

        dep_content += "## Dependency Chain\n\n"
        for feat, deps in sorted(dependency_map.items()):
            dep_content += f"### {feat}\n\n"
            dep_content += "**Requires:**\n"
            for dep in deps:
                dep_content += f"- {dep}\n"
            dep_content += "\n"

        artifacts.append({
            "type": "dependency_insight",
            "format": "markdown",
            "content": dep_content,
            "value_usd": 75,
            "description": "Cross-feature dependency analysis",
            "tab": "techlead",
            "metadata": {
                "total_dependencies": sum(len(deps) for deps in dependency_map.values()),
                "features_with_deps": len(dependency_map),
                "independent_features": len(independent_features),
            },
        })

    # Save artifacts locally and create Langfuse references
    if ARTIFACT_STORAGE_AVAILABLE and project_dir:
        langfuse_refs = []
        for artifact in artifacts:
            # Save full artifact locally
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_dir,
                spec_id=None,  # Roadmap is project-level, not spec-specific
                trace_id=trace_id,
                agent_type="roadmap_generator",
                session_num=None,
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


def extract_competitor_artifacts(
    competitor_data: dict[str, Any],
    project_dir: Path | None = None,
    trace_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Extract competitor analysis artifacts.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    Artifacts extracted:
    - competitor_insight ($75) - each competitor analyzed
    - market_gap ($100) - identified market opportunities

    Args:
        competitor_data: The competitor analysis data
        project_dir: Project root directory for local storage
        trace_id: Langfuse trace ID for linking

    Returns:
        Tuple of (local_artifacts, langfuse_refs)
    """
    artifacts = []

    # Extract competitor insights
    competitors = competitor_data.get("competitors", [])
    for i, competitor in enumerate(competitors):
        if isinstance(competitor, dict):
            name = competitor.get("name", f"Competitor {i+1}")
            strengths = competitor.get("strengths", [])
            weaknesses = competitor.get("weaknesses", [])
            differentiation = competitor.get("differentiation", "")

            content = f"**{name}**"
            if strengths:
                strengths_list = strengths if isinstance(strengths, list) else [strengths]
                content += f"\n\nStrengths:\n" + "\n".join(f"- {s}" for s in strengths_list)
            if weaknesses:
                weaknesses_list = weaknesses if isinstance(weaknesses, list) else [weaknesses]
                content += f"\n\nWeaknesses:\n" + "\n".join(f"- {w}" for w in weaknesses_list)
            if differentiation:
                content += f"\n\nDifferentiation: {differentiation}"

            artifacts.append({
                "type": "competitor_insight",
                "format": "text",
                "content": content,  # FULL CONTENT
                "value_usd": 75,
                "description": f"Competitor: {name}",
                "tab": "ops",
                "metadata": {
                    "competitor_name": name,
                },
            })

    # Extract market gaps
    gaps = competitor_data.get("market_gaps", competitor_data.get("gaps", []))
    for gap in gaps:
        if isinstance(gap, dict):
            gap_title = gap.get("title", gap.get("name", "Market Opportunity"))
            gap_desc = gap.get("description", "")
            gap_opportunity = gap.get("opportunity", "")

            content = f"**{gap_title}**"
            if gap_desc:
                content += f"\n\n{gap_desc}"
            if gap_opportunity:
                content += f"\n\nOpportunity: {gap_opportunity}"

            artifacts.append({
                "type": "market_gap",
                "format": "text",
                "content": content,
                "value_usd": 100,
                "description": f"Market gap: {gap_title}",
                "tab": "ops",
            })
        elif isinstance(gap, str) and gap:
            artifacts.append({
                "type": "market_gap",
                "format": "text",
                "content": gap,
                "value_usd": 100,
                "description": "Market gap identified",
                "tab": "ops",
            })

    # Save artifacts locally and create Langfuse references
    if ARTIFACT_STORAGE_AVAILABLE and project_dir:
        langfuse_refs = []
        for artifact in artifacts:
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_dir,
                spec_id=None,
                trace_id=trace_id,
                agent_type="competitor_analyzer",
                session_num=None,
            )

            if artifact_id:
                artifacts_dir = _get_artifacts_dir(project_dir)
                storage_path = str(
                    (artifacts_dir / artifact_id).relative_to(project_dir)
                    if artifacts_dir.exists()
                    else f".auto-claude/artifacts/{artifact_id}.json"
                )
                ref = create_langfuse_reference(artifact, artifact_id, storage_path)
                langfuse_refs.append(ref)
            else:
                langfuse_refs.append(artifact)

        return artifacts, langfuse_refs
    else:
        return artifacts, artifacts


# =============================================================================
# ORCHESTRATOR
# =============================================================================


class RoadmapOrchestrator:
    """Orchestrates the roadmap creation process."""

    def __init__(
        self,
        project_dir: Path,
        output_dir: Path | None = None,
        model: str = "sonnet",  # Changed from "opus" (fix #433)
        thinking_level: str = "medium",
        refresh: bool = False,
        enable_competitor_analysis: bool = False,
        refresh_competitor_analysis: bool = False,
    ):
        self.project_dir = Path(project_dir)
        # Resolve model for Azure Foundry mode (maps to deployment names)
        self.model = resolve_model_id(model)
        self.thinking_level = thinking_level
        self.thinking_budget = get_thinking_budget(thinking_level)
        self.refresh = refresh
        self.enable_competitor_analysis = enable_competitor_analysis
        self.refresh_competitor_analysis = refresh_competitor_analysis

        # Always initialize .auto-claude directory and ensure it's in .gitignore
        # This is needed for analytics tracking even if custom output_dir is provided
        init_auto_claude_dir(self.project_dir)

        # Default output to project's .auto-claude directory (installed instance)
        # Note: auto-claude/ is source code, .auto-claude/ is the installed instance
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.project_dir / ".auto-claude" / "roadmap"

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize executors
        self.script_executor = ScriptExecutor(self.project_dir)
        self.agent_executor = AgentExecutor(
            self.project_dir,
            self.output_dir,
            self.model,
            create_client,
            self.thinking_budget,
        )

        # Initialize phase handlers
        self.graph_hints_provider = GraphHintsProvider(
            self.output_dir, self.project_dir, self.refresh
        )
        # Competitor analyzer refreshes if either general refresh or specific competitor refresh
        competitor_should_refresh = self.refresh or self.refresh_competitor_analysis
        self.competitor_analyzer = CompetitorAnalyzer(
            self.output_dir, competitor_should_refresh, self.agent_executor
        )
        self.project_index_phase = ProjectIndexPhase(
            self.output_dir, self.refresh, self.script_executor
        )
        self.discovery_phase = DiscoveryPhase(
            self.output_dir, self.refresh, self.agent_executor
        )
        self.features_phase = FeaturesPhase(
            self.output_dir, self.refresh, self.agent_executor
        )

        debug_section("roadmap_orchestrator", "Roadmap Orchestrator Initialized")
        debug(
            "roadmap_orchestrator",
            "Configuration",
            project_dir=str(self.project_dir),
            output_dir=str(self.output_dir),
            model=self.model,
            refresh=self.refresh,
        )

    async def run(self) -> bool:
        """Run the complete roadmap generation process with optional competitor analysis."""
        debug_section("roadmap_orchestrator", "Starting Roadmap Generation")
        debug(
            "roadmap_orchestrator",
            "Run configuration",
            project_dir=str(self.project_dir),
            output_dir=str(self.output_dir),
            model=self.model,
            refresh=self.refresh,
        )

        print(
            box(
                f"Project: {self.project_dir}\n"
                f"Output: {self.output_dir}\n"
                f"Model: {self.model}\n"
                f"Competitor Analysis: {'enabled' if self.enable_competitor_analysis else 'disabled'}",
                title="ROADMAP GENERATOR",
                style="heavy",
            )
        )
        results = []

        # Phase 1: Project Index & Graph Hints (in parallel)
        debug(
            "roadmap_orchestrator",
            "Starting Phase 1: Project Analysis & Graph Hints (parallel)",
        )
        print_section("PHASE 1: PROJECT ANALYSIS & GRAPH HINTS", Icons.FOLDER)

        # Run project index and graph hints in parallel
        index_task = self.project_index_phase.execute()
        hints_task = self.graph_hints_provider.retrieve_hints()
        index_result, hints_result = await asyncio.gather(index_task, hints_task)

        results.append(index_result)
        results.append(hints_result)

        debug(
            "roadmap_orchestrator",
            "Phase 1 complete",
            index_success=index_result.success,
            hints_success=hints_result.success,
        )

        if not index_result.success:
            debug_error(
                "roadmap_orchestrator",
                "Project analysis failed - aborting roadmap generation",
            )
            print_status("Project analysis failed", "error")
            return False
        # Note: hints_result.success is always True (graceful degradation)

        # Phase 2: Discovery
        debug("roadmap_orchestrator", "Starting Phase 2: Project Discovery")
        print_section("PHASE 2: PROJECT DISCOVERY", Icons.SEARCH)
        result = await self.discovery_phase.execute()
        results.append(result)
        if not result.success:
            debug_error(
                "roadmap_orchestrator",
                "Discovery failed - aborting roadmap generation",
                errors=result.errors,
            )
            print_status("Discovery failed", "error")
            for err in result.errors:
                print(f"  {muted('Error:')} {err}")
            return False
        debug_success("roadmap_orchestrator", "Phase 2 complete")

        # Phase 2.5: Competitor Analysis (optional, runs after discovery)
        print_section("PHASE 2.5: COMPETITOR ANALYSIS", Icons.SEARCH)
        competitor_result = await self.competitor_analyzer.analyze(
            enabled=self.enable_competitor_analysis
        )
        results.append(competitor_result)
        # Note: competitor_result.success is always True (graceful degradation)

        # Phase 3: Feature Generation
        debug("roadmap_orchestrator", "Starting Phase 3: Feature Generation")
        print_section("PHASE 3: FEATURE GENERATION", Icons.SUBTASK)
        result = await self.features_phase.execute()
        results.append(result)
        if not result.success:
            debug_error(
                "roadmap_orchestrator",
                "Feature generation failed - aborting",
                errors=result.errors,
            )
            print_status("Feature generation failed", "error")
            for err in result.errors:
                print(f"  {muted('Error:')} {err}")
            return False
        debug_success("roadmap_orchestrator", "Phase 3 complete")

        # Phase 4: Publish ROI
        await self._publish_roi()

        # Summary
        self._print_summary()
        return True

    async def _publish_roi(self) -> None:
        """Publish ROI metrics for roadmap generation.

        Calculates the value of strategic planning and prioritization.
        Extracts artifacts and stores them locally, passes refs to Langfuse.
        """
        if not ROI_PUBLISHER_AVAILABLE:
            debug_warning("roadmap_orchestrator", "ROI publisher not available")
            return

        print_section("PHASE 4: PUBLISH ROI", Icons.CHART)

        roadmap_file = self.output_dir / "roadmap.json"
        if not roadmap_file.exists():
            debug_warning("roadmap_orchestrator", "No roadmap.json found")
            return

        try:
            with open(roadmap_file) as f:
                roadmap = json.load(f)

            features = roadmap.get("features", [])
            phases = roadmap.get("phases", [])

            # Count features by status
            features_identified = len(features)
            features_rejected = sum(
                1 for f in features
                if f.get("status", "").lower() in ["rejected", "deferred", "wont_do"]
            )

            # Estimate cost (typical roadmap generation uses ~10K tokens)
            estimated_tokens = 10000
            estimated_cost = (estimated_tokens / 1000) * 0.003  # $0.003 per 1K tokens

            project_id = self.project_dir.name

            # Extract roadmap artifacts - stores full content locally
            # Returns (full_artifacts, langfuse_refs)
            all_artifacts = []
            all_refs = []

            # Extract roadmap artifacts (vision, phases, features)
            roadmap_artifacts, roadmap_refs = extract_roadmap_artifacts(
                roadmap=roadmap,
                project_dir=self.project_dir,
                trace_id=None,  # No trace context in orchestrator
            )
            all_artifacts.extend(roadmap_artifacts)
            all_refs.extend(roadmap_refs)

            # Extract competitor artifacts if available
            competitor_file = self.output_dir / "competitor_analysis.json"
            if competitor_file.exists():
                try:
                    with open(competitor_file) as f:
                        competitor_data = json.load(f)
                    competitor_artifacts, competitor_refs = extract_competitor_artifacts(
                        competitor_data=competitor_data,
                        project_dir=self.project_dir,
                        trace_id=None,
                    )
                    all_artifacts.extend(competitor_artifacts)
                    all_refs.extend(competitor_refs)
                except Exception as e:
                    debug_warning(
                        "roadmap_orchestrator",
                        f"Failed to extract competitor artifacts: {e}",
                    )

            # Calculate total artifact value (use full artifacts for value)
            total_artifact_value = sum(a.get("value_usd", 0) for a in all_artifacts)

            # Publish ROI with Langfuse refs (truncated previews, not full content)
            result = await publish_roadmap_roi(
                project_id=project_id,
                features_identified=features_identified,
                features_rejected=features_rejected,
                cost_usd=estimated_cost,
                tokens=estimated_tokens,
                model=self.model,
                artifacts=all_refs,  # Pass refs for Langfuse
            )

            if result.get("success"):
                roi_pct = result.get("roi_percentage", 0)
                value = result.get("total_value_usd", 0)
                print_status(
                    f"Roadmap ROI: {roi_pct:.0f}% (${value:.2f} value from {features_identified} features)",
                    "success",
                )
                debug(
                    "roadmap_roi",
                    "Published roadmap ROI",
                    roi=roi_pct,
                    value=value,
                    features=features_identified,
                    rejected=features_rejected,
                    artifacts_count=len(all_artifacts),
                    artifact_value=total_artifact_value,
                    phases_count=len(phases),
                )

                # Log artifact storage info if available
                if ARTIFACT_STORAGE_AVAILABLE and all_artifacts:
                    debug(
                        "roadmap_roi",
                        "Artifacts stored locally",
                        roadmap_artifacts=len(roadmap_artifacts),
                        competitor_artifacts=len(all_artifacts) - len(roadmap_artifacts),
                        storage_dir=str(self.project_dir / ".auto-claude" / "artifacts"),
                    )
            else:
                debug_warning(
                    "roadmap_roi",
                    f"Failed to publish ROI: {result.get('error')}",
                )

        except Exception as e:
            debug_warning("roadmap_orchestrator", f"Failed to publish ROI: {e}")
            print_status(f"ROI publish failed: {e}", "warning")

    def _print_summary(self):
        """Print the final roadmap generation summary."""
        roadmap_file = self.output_dir / "roadmap.json"
        if not roadmap_file.exists():
            return

        with open(roadmap_file) as f:
            roadmap = json.load(f)

        features = roadmap.get("features", [])
        phases = roadmap.get("phases", [])

        # Count by priority
        priority_counts = {}
        for f in features:
            p = f.get("priority", "unknown")
            priority_counts[p] = priority_counts.get(p, 0) + 1

        debug_success(
            "roadmap_orchestrator",
            "Roadmap generation complete",
            phase_count=len(phases),
            feature_count=len(features),
            priority_breakdown=priority_counts,
        )

        print(
            box(
                f"Vision: {roadmap.get('vision', 'N/A')}\n"
                f"Phases: {len(phases)}\n"
                f"Features: {len(features)}\n\n"
                f"Priority breakdown:\n"
                + "\n".join(
                    f"  {icon(Icons.ARROW_RIGHT)} {p.upper()}: {c}"
                    for p, c in priority_counts.items()
                )
                + f"\n\nRoadmap saved to: {roadmap_file}",
                title=f"{icon(Icons.SUCCESS)} ROADMAP GENERATED",
                style="heavy",
            )
        )
