"""
Ideation Runner - Main orchestration logic.

Orchestrates the ideation creation process through multiple phases:
1. Project Index - Analyze project structure
2. Context & Graph Hints - Gather context in parallel
3. Ideation Generation - Generate ideas in parallel
4. Merge - Combine all outputs
5. Save to Memory - Persist ideas to Graphiti for future context
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add auto-claude to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from debug import debug, debug_section, debug_success, debug_warning
from ui import Icons, box, icon, muted, print_section, print_status

# ROI Publishing
try:
    from analytics.roi_publisher import publish_ideation_roi
    ROI_PUBLISHER_AVAILABLE = True
except ImportError:
    ROI_PUBLISHER_AVAILABLE = False

# Artifact Storage
try:
    from analytics.artifact_storage import (
        save_artifact_safe,
        create_langfuse_reference,
        _get_artifacts_dir,
    )
    ARTIFACT_STORAGE_AVAILABLE = True
except ImportError:
    ARTIFACT_STORAGE_AVAILABLE = False
    save_artifact_safe = None
    create_langfuse_reference = None
    _get_artifacts_dir = None

from .config import IdeationConfigManager
from .generator import IDEATION_TYPE_LABELS
from .output_streamer import OutputStreamer
from .phase_executor import PhaseExecutor
from .project_index_phase import ProjectIndexPhase
from .types import IdeationPhaseResult

# Configuration
MAX_RETRIES = 3


class IdeationOrchestrator:
    """Orchestrates the ideation creation process."""

    def __init__(
        self,
        project_dir: Path,
        output_dir: Path | None = None,
        enabled_types: list[str] | None = None,
        include_roadmap_context: bool = True,
        include_kanban_context: bool = True,
        max_ideas_per_type: int = 5,
        model: str = "opus",  # Shorthand - resolved via API Profile if configured
        thinking_level: str = "medium",
        refresh: bool = False,
        append: bool = False,
    ):
        """Initialize the ideation orchestrator.

        Args:
            project_dir: Project directory to analyze
            output_dir: Output directory for ideation files (defaults to .auto-claude/ideation)
            enabled_types: List of ideation types to generate (defaults to all)
            include_roadmap_context: Include roadmap files in analysis
            include_kanban_context: Include kanban board in analysis
            max_ideas_per_type: Maximum ideas to generate per type
            model: Claude model to use
            thinking_level: Thinking level for extended reasoning
            refresh: Force regeneration of existing files
            append: Preserve existing ideas when merging
        """
        # Initialize configuration manager
        self.config_manager = IdeationConfigManager(
            project_dir=project_dir,
            output_dir=output_dir,
            enabled_types=enabled_types,
            include_roadmap_context=include_roadmap_context,
            include_kanban_context=include_kanban_context,
            max_ideas_per_type=max_ideas_per_type,
            model=model,
            thinking_level=thinking_level,
            refresh=refresh,
            append=append,
        )

        # Expose configuration for convenience
        self.project_dir = self.config_manager.project_dir
        self.output_dir = self.config_manager.output_dir
        self.model = self.config_manager.model
        self.refresh = self.config_manager.refresh
        self.append = self.config_manager.append
        self.enabled_types = self.config_manager.enabled_types
        self.max_ideas_per_type = self.config_manager.max_ideas_per_type

        # Initialize phase executor
        self.phase_executor = PhaseExecutor(
            output_dir=self.output_dir,
            generator=self.config_manager.generator,
            analyzer=self.config_manager.analyzer,
            prioritizer=self.config_manager.prioritizer,
            formatter=self.config_manager.formatter,
            enabled_types=self.enabled_types,
            max_ideas_per_type=self.max_ideas_per_type,
            refresh=self.refresh,
            append=self.append,
        )

        # Initialize project index phase
        self.project_index_phase = ProjectIndexPhase(
            self.project_dir, self.output_dir, self.refresh
        )

        # Initialize output streamer
        self.output_streamer = OutputStreamer()

    async def run(self) -> bool:
        """Run the complete ideation generation process.

        Returns:
            True if successful, False otherwise
        """
        debug_section("ideation_runner", "Starting Ideation Generation")
        debug(
            "ideation_runner",
            "Configuration",
            project_dir=str(self.project_dir),
            output_dir=str(self.output_dir),
            model=self.model,
            enabled_types=self.enabled_types,
            refresh=self.refresh,
            append=self.append,
        )

        print(
            box(
                f"Project: {self.project_dir}\n"
                f"Output: {self.output_dir}\n"
                f"Model: {self.model}\n"
                f"Types: {', '.join(self.enabled_types)}",
                title="IDEATION GENERATOR",
                style="heavy",
            )
        )

        results = []

        # Phase 1: Project Index
        debug("ideation_runner", "Starting Phase 1: Project Analysis")
        print_section("PHASE 1: PROJECT ANALYSIS", Icons.FOLDER)
        result = await self.project_index_phase.execute()
        results.append(result)
        if not result.success:
            print_status("Project analysis failed", "error")
            return False

        # Phase 2: Context & Graph Hints (in parallel)
        print_section("PHASE 2: CONTEXT & GRAPH HINTS (PARALLEL)", Icons.SEARCH)

        # Run context gathering and graph hints in parallel
        context_task = self.phase_executor.execute_context()
        hints_task = self.phase_executor.execute_graph_hints()
        context_result, hints_result = await asyncio.gather(context_task, hints_task)

        results.append(hints_result)
        results.append(context_result)

        if not context_result.success:
            print_status("Context gathering failed", "error")
            return False
        # Note: hints_result.success is always True (graceful degradation)

        # Phase 3: Run all ideation types IN PARALLEL
        debug(
            "ideation_runner",
            "Starting Phase 3: Generating Ideas",
            types=self.enabled_types,
            parallel=True,
        )
        print_section("PHASE 3: GENERATING IDEAS (PARALLEL)", Icons.SUBTASK)
        print_status(
            f"Starting {len(self.enabled_types)} ideation agents in parallel...",
            "progress",
        )

        # Create tasks for all enabled types
        ideation_tasks = [
            self.output_streamer.stream_ideation_result(
                ideation_type, self.phase_executor, MAX_RETRIES
            )
            for ideation_type in self.enabled_types
        ]

        # Run all ideation types concurrently
        ideation_results = await asyncio.gather(*ideation_tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(ideation_results):
            ideation_type = self.enabled_types[i]
            if isinstance(result, Exception):
                print_status(
                    f"{IDEATION_TYPE_LABELS[ideation_type]} ideation failed with exception: {result}",
                    "error",
                )
                results.append(
                    IdeationPhaseResult(
                        phase="ideation",
                        ideation_type=ideation_type,
                        success=False,
                        output_files=[],
                        ideas_count=0,
                        errors=[str(result)],
                        retries=0,
                    )
                )
            else:
                results.append(result)
                if result.success:
                    print_status(
                        f"{IDEATION_TYPE_LABELS[ideation_type]}: {result.ideas_count} ideas",
                        "success",
                    )
                else:
                    print_status(
                        f"{IDEATION_TYPE_LABELS[ideation_type]} ideation failed",
                        "warning",
                    )
                    for err in result.errors:
                        print(f"  {muted('Error:')} {err}")

        # Final Phase: Merge
        print_section("PHASE 4: MERGE & FINALIZE", Icons.SUCCESS)
        result = await self.phase_executor.execute_merge()
        results.append(result)

        # Phase 5: Save to Memory
        print_section("PHASE 5: SAVE TO MEMORY", Icons.GEAR)
        import sys
        print("[MEMORY DEBUG] Starting _save_to_memory...", file=sys.stderr, flush=True)
        memory_result = await self._save_to_memory()
        print(f"[MEMORY DEBUG] _save_to_memory returned: {memory_result}", file=sys.stderr, flush=True)

        # Phase 6: Publish ROI
        await self._publish_roi(results)

        # Summary
        self._print_summary()

        return True

    def _print_summary(self) -> None:
        """Print summary of ideation generation results."""
        ideation_file = self.output_dir / "ideation.json"
        if ideation_file.exists():
            with open(ideation_file) as f:
                ideation = json.load(f)

            ideas = ideation.get("ideas", [])
            summary = ideation.get("summary", {})
            by_type = summary.get("by_type", {})

            print(
                box(
                    f"Total Ideas: {len(ideas)}\n\n"
                    f"By Type:\n"
                    + "\n".join(
                        f"  {icon(Icons.ARROW_RIGHT)} {IDEATION_TYPE_LABELS.get(t, t)}: {c}"
                        for t, c in by_type.items()
                    )
                    + f"\n\nIdeation saved to: {ideation_file}",
                    title=f"{icon(Icons.SUCCESS)} IDEATION COMPLETE",
                    style="heavy",
                )
            )

    def _extract_ideation_artifacts(
        self,
        ideas: list[dict],
        trace_id: str | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """
        Extract artifacts from generated ideation ideas.

        Stores FULL artifact content locally, returns lightweight references for Langfuse.

        Artifacts extracted:
        - idea ($50 each) - each generated idea
        - recommendation ($75 each) - ideas with actionable recommendations
        - analysis_insight ($100 each) - ideas with deep analysis/strategic value

        Args:
            ideas: List of idea dictionaries from ideation.json
            trace_id: Langfuse trace ID for linking

        Returns:
            Tuple of (local_artifacts, langfuse_refs):
            - local_artifacts: Full artifacts for local processing
            - langfuse_refs: Truncated references for Langfuse
        """
        artifacts = []

        for idea in ideas:
            idea_type = idea.get("ideation_type", idea.get("type", "unknown"))
            title = idea.get("title", "Untitled")
            description = idea.get("description", "")
            priority = idea.get("priority", "medium").lower()
            complexity = idea.get("complexity", "medium")
            rationale = idea.get("rationale", "")

            # Build FULL content - no truncation
            content = f"# {title}\n\n"
            content += f"**Type**: {IDEATION_TYPE_LABELS.get(idea_type, idea_type)}\n"
            content += f"**Priority**: {priority.upper()}\n"
            content += f"**Complexity**: {complexity}\n\n"
            content += f"## Description\n{description}\n"

            if rationale:
                content += f"\n## Rationale\n{rationale}\n"

            # Include implementation hints if present
            implementation = idea.get("implementation_hints", idea.get("implementation", ""))
            if implementation:
                content += f"\n## Implementation\n{implementation}\n"

            # Include dependencies if present
            dependencies = idea.get("dependencies", [])
            if dependencies:
                content += "\n## Dependencies\n"
                for dep in dependencies:
                    content += f"- {dep}\n"

            # Determine artifact type and value based on idea characteristics
            if priority == "high" and len(description) > 200:
                # High priority with substantial description = analysis insight
                artifact_type = "analysis_insight"
                value_usd = 100
                tab = "business"
            elif any(kw in description.lower() for kw in ["recommend", "should", "consider", "improve", "enhance"]):
                # Contains recommendation language
                artifact_type = "recommendation"
                value_usd = 75
                tab = "business"
            else:
                # Standard idea
                artifact_type = "idea"
                value_usd = 50
                # Tab based on ideation type
                if idea_type in ["security_hardening"]:
                    tab = "ops"
                elif idea_type in ["ui_ux_improvements"]:
                    tab = "techlead"
                elif idea_type in ["code_improvements", "code_quality", "performance_optimizations"]:
                    tab = "dev"
                else:
                    tab = "business"

            artifacts.append({
                "type": artifact_type,
                "format": "markdown",
                "content": content,
                "value_usd": value_usd,
                "description": f"{IDEATION_TYPE_LABELS.get(idea_type, idea_type)}: {title}",
                "tab": tab,
                "metadata": {
                    "ideation_type": idea_type,
                    "title": title,
                    "priority": priority,
                    "complexity": complexity,
                },
            })

        # Save artifacts locally and create Langfuse references
        if ARTIFACT_STORAGE_AVAILABLE and save_artifact_safe and create_langfuse_reference and _get_artifacts_dir:
            langfuse_refs = []
            for artifact in artifacts:
                # Save full artifact locally
                artifact_id = save_artifact_safe(
                    artifact=artifact,
                    project_dir=self.project_dir,
                    spec_id=None,  # Ideation doesn't have spec_id
                    trace_id=trace_id,
                    agent_type="ideation",
                    session_num=None,
                )

                if artifact_id:
                    # Create lightweight reference for Langfuse
                    artifacts_dir = _get_artifacts_dir(self.project_dir)
                    storage_path = str(
                        (artifacts_dir / datetime.now().strftime("%Y-%m-%d") / f"{artifact_id}.json")
                    )
                    ref = create_langfuse_reference(artifact, artifact_id, storage_path)
                    langfuse_refs.append(ref)
                else:
                    # Fallback: if storage fails, include full artifact as ref
                    langfuse_refs.append(artifact)

            debug(
                "ideation_artifacts",
                f"Extracted {len(artifacts)} artifacts, stored {len(langfuse_refs)} refs",
                artifacts_count=len(artifacts),
            )
            return artifacts, langfuse_refs
        else:
            # No local storage available - return artifacts as both
            debug(
                "ideation_artifacts",
                "Artifact storage not available, returning full artifacts",
                artifacts_count=len(artifacts),
            )
            return artifacts, artifacts

    async def _publish_roi(self, results: list) -> None:
        """Publish ROI metrics for ideation session.

        Calculates and publishes ROI to Langfuse for each ideation type.
        Includes artifact extraction and storage for traceability.

        Args:
            results: List of IdeationPhaseResult objects
        """
        if not ROI_PUBLISHER_AVAILABLE:
            debug_warning("ideation_runner", "ROI publisher not available, skipping ROI publish")
            return

        print_section("PHASE 6: PUBLISH ROI", Icons.CHART)

        # Load ideation.json to get idea counts and priority breakdown
        ideation_file = self.output_dir / "ideation.json"
        if not ideation_file.exists():
            debug_warning("ideation_runner", "No ideation.json found, skipping ROI publish")
            return

        try:
            with open(ideation_file) as f:
                ideation_data = json.load(f)

            ideas = ideation_data.get("ideas", [])
            summary = ideation_data.get("summary", {})
            by_type = summary.get("by_type", {})

            # Calculate high impact ideas (priority = high)
            high_impact = sum(1 for idea in ideas if idea.get("priority", "").lower() == "high")

            # Estimate cost from results (sum up all successful phases)
            total_tokens = 0
            total_cost = 0.0
            total_duration = 0.0

            for result in results:
                if hasattr(result, "tokens") and result.tokens:
                    total_tokens += result.tokens
                if hasattr(result, "cost") and result.cost:
                    total_cost += result.cost
                if hasattr(result, "duration") and result.duration:
                    total_duration += result.duration

            # If we don't have cost data from results, estimate from token count
            # Typical pricing: ~$0.003 per 1K tokens for Claude Sonnet
            if total_cost == 0 and total_tokens > 0:
                total_cost = (total_tokens / 1000) * 0.003

            # Estimate based on average tokens per ideation type if we have no data
            if total_tokens == 0:
                total_tokens = len(self.enabled_types) * 2000  # ~2K tokens per type
                total_cost = (total_tokens / 1000) * 0.003

            # Publish ROI for the session
            project_id = self.project_dir.name

            # Extract artifacts from ALL ideas (pass None for trace_id, will be set per-type)
            all_artifacts, all_langfuse_refs = self._extract_ideation_artifacts(ideas, trace_id=None)

            # Track totals for summary
            total_roi_pct = 0
            total_value = 0
            successful_publishes = 0

            for ideation_type, count in by_type.items():
                # Count high impact ideas for this type
                type_high_impact = sum(
                    1 for idea in ideas
                    if idea.get("type") == ideation_type and idea.get("priority", "").lower() == "high"
                )

                # Filter artifacts for this type
                type_artifacts = [
                    a for a in all_artifacts
                    if a.get("metadata", {}).get("ideation_type") == ideation_type
                ]
                type_refs = [
                    r for r in all_langfuse_refs
                    if r.get("metadata", {}).get("ideation_type") == ideation_type
                ]

                # Calculate artifact value for this type
                type_artifact_value = sum(a.get("value_usd", 0) for a in type_artifacts)

                # Estimate cost per type (distribute evenly)
                type_cost = total_cost / len(by_type) if by_type else total_cost
                type_tokens = total_tokens // len(by_type) if by_type else total_tokens
                type_duration = total_duration / len(by_type) if by_type else 0.0

                try:
                    result = await publish_ideation_roi(
                        project_id=project_id,
                        ideation_type=ideation_type,
                        ideas_generated=count,
                        high_impact_ideas=type_high_impact,
                        cost_usd=type_cost,
                        tokens=type_tokens,
                        model=self.model,
                        duration_seconds=type_duration,
                    )

                    if result.get("success"):
                        roi_pct = result.get("roi_percentage", 0)
                        value = result.get("total_value_usd", 0)
                        total_roi_pct += roi_pct
                        total_value += value
                        successful_publishes += 1
                        print_status(
                            f"{IDEATION_TYPE_LABELS.get(ideation_type, ideation_type)}: "
                            f"ROI {roi_pct:.0f}% (${value:.2f} value, {len(type_artifacts)} artifacts)",
                            "success",
                        )
                        debug(
                            "ideation_roi",
                            f"Published ROI for {ideation_type}",
                            roi=roi_pct,
                            value=value,
                            cost=type_cost,
                            artifacts=len(type_artifacts),
                            artifact_value=type_artifact_value,
                        )
                    else:
                        debug_warning(
                            "ideation_roi",
                            f"Failed to publish ROI for {ideation_type}: {result.get('error')}",
                        )
                except Exception as e:
                    debug_warning("ideation_roi", f"Error publishing ROI for {ideation_type}: {e}")

            # Summary
            total_ideas = len(ideas)
            avg_roi = total_roi_pct / successful_publishes if successful_publishes > 0 else 0
            total_artifact_value = sum(a.get("value_usd", 0) for a in all_artifacts)

            print_status(
                f"ROI published for {len(by_type)} ideation types ({total_ideas} ideas, "
                f"{len(all_artifacts)} artifacts, ${total_artifact_value:.2f} artifact value)",
                "success",
            )

            debug(
                "ideation_roi_summary",
                "Ideation ROI summary",
                total_ideas=total_ideas,
                total_artifacts=len(all_artifacts),
                total_artifact_value=total_artifact_value,
                avg_roi=avg_roi,
                total_value=total_value,
                total_cost=total_cost,
            )

        except Exception as e:
            debug_warning("ideation_runner", f"Failed to publish ROI: {e}")
            print_status(f"ROI publish failed: {e}", "warning")

    async def _save_to_memory(self) -> bool:
        """Save ideation results to Graphiti memory for future context.

        This persists the generated ideas as episodic memory, allowing future
        sessions to reference what was ideated and learn from patterns.

        Returns:
            True if saved successfully, False otherwise
        """
        import os
        from graphiti_providers import is_graphiti_enabled

        # Debug: Write to log file for visibility
        log_file = self.output_dir / "memory_debug.log"
        def log(msg):
            with open(log_file, "a") as f:
                f.write(f"{msg}\n")

        log(f"=== Memory Save Debug - {datetime.now().isoformat()} ===")

        graphiti_enabled_env = os.environ.get("GRAPHITI_ENABLED", "NOT SET")
        llm_provider_env = os.environ.get("GRAPHITI_LLM_PROVIDER", "NOT SET")
        embedder_provider_env = os.environ.get("GRAPHITI_EMBEDDER_PROVIDER", "NOT SET")

        log(f"GRAPHITI_ENABLED={graphiti_enabled_env}")
        log(f"GRAPHITI_LLM_PROVIDER={llm_provider_env}")
        log(f"GRAPHITI_EMBEDDER_PROVIDER={embedder_provider_env}")

        graphiti_check = is_graphiti_enabled()
        log(f"is_graphiti_enabled() = {graphiti_check}")

        if not graphiti_check:
            log("SKIPPING - Graphiti not enabled")
            print_status(f"Graphiti not enabled (GRAPHITI_ENABLED={graphiti_enabled_env}), skipping memory save", "info")
            return False

        log("Graphiti IS enabled, continuing...")

        ideation_file = self.output_dir / "ideation.json"
        log(f"Looking for ideation file: {ideation_file}")
        log(f"File exists: {ideation_file.exists()}")

        if not ideation_file.exists():
            log("SKIPPING - No ideation file")
            print_status("No ideation file found to save", "warning")
            return False

        try:
            log("Loading ideation file...")
            with open(ideation_file) as f:
                ideation = json.load(f)

            ideas = ideation.get("ideas", [])
            log(f"Found {len(ideas)} ideas")

            if not ideas:
                log("SKIPPING - No ideas")
                print_status("No ideas to save to memory", "info")
                return False

            # Import GraphitiMemory
            log("Importing GraphitiMemory...")
            from graphiti_memory import GraphitiMemory, GroupIdMode
            log("Import successful")

            # Create memory instance with PROJECT mode for cross-session context
            log(f"Creating GraphitiMemory for project: {self.project_dir}")
            memory = GraphitiMemory(
                spec_dir=self.output_dir,
                project_dir=self.project_dir,
                group_id_mode=GroupIdMode.PROJECT,
            )
            log(f"Memory created, is_enabled={memory.is_enabled}, group_id={memory.group_id}")

            if not memory.is_enabled:
                log("SKIPPING - GraphitiMemory not enabled")
                print_status("GraphitiMemory not enabled", "warning")
                return False

            # Initialize memory
            log("Initializing memory...")
            initialized = await memory.initialize()
            log(f"Initialized: {initialized}")

            if not initialized:
                log("FAILED - Could not initialize")
                print_status("Failed to initialize GraphitiMemory", "warning")
                return False

            # Build episode content - summarize the ideation session
            summary = ideation.get("summary", {})
            by_type = summary.get("by_type", {})

            # Create a structured summary of ideation
            episode_content = f"""## Ideation Session - {datetime.now().strftime('%Y-%m-%d %H:%M')}

### Summary
Generated {len(ideas)} ideas across {len(by_type)} categories.

### Ideas by Type
"""
            for idea_type, count in by_type.items():
                type_label = IDEATION_TYPE_LABELS.get(idea_type, idea_type)
                episode_content += f"- **{type_label}**: {count} ideas\n"

            # Add top ideas from each category
            episode_content += "\n### Top Ideas\n"
            ideas_by_type: dict[str, list] = {}
            for idea in ideas:
                idea_type = idea.get("ideation_type", "unknown")
                if idea_type not in ideas_by_type:
                    ideas_by_type[idea_type] = []
                ideas_by_type[idea_type].append(idea)

            for idea_type, type_ideas in ideas_by_type.items():
                type_label = IDEATION_TYPE_LABELS.get(idea_type, idea_type)
                episode_content += f"\n#### {type_label}\n"
                # Add top 3 ideas from each type
                for idea in type_ideas[:3]:
                    title = idea.get("title", "Untitled")
                    description = idea.get("description", "")[:200]
                    priority = idea.get("priority", "medium")
                    episode_content += f"- [{priority.upper()}] **{title}**: {description}...\n"

            # Save as episodic memory
            debug("ideation_memory", "Saving ideation to memory", ideas_count=len(ideas))

            # Use session_num=0 to indicate this is an ideation session (not a build session)
            insights = {
                "type": "ideation_session",
                "content": episode_content,
                "total_ideas": len(ideas),
                "by_type": by_type,
                "enabled_types": self.enabled_types,
                "model": self.model,
                "timestamp": datetime.now().isoformat(),
            }

            log("Saving session insights...")
            result = await memory.save_session_insights(
                session_num=0,  # 0 indicates ideation, not a build session
                insights=insights,
            )
            log(f"Save result: {result}")

            await memory.close()
            log("Memory closed")

            log(f"SUCCESS - Saved {len(ideas)} ideas to memory")
            debug_success("ideation_memory", f"Saved {len(ideas)} ideas to memory")
            print_status(f"Saved {len(ideas)} ideas to memory", "success")
            return True

        except ImportError as e:
            import traceback
            log(f"IMPORT ERROR: {e}")
            log(traceback.format_exc())
            debug_warning("ideation_memory", f"GraphitiMemory not available: {e}")
            print_status(f"Memory packages not available: {e}", "warning")
            return False
        except Exception as e:
            import traceback
            log(f"EXCEPTION: {e}")
            log(traceback.format_exc())
            debug_warning("ideation_memory", f"Failed to save to memory: {e}")
            print_status(f"Failed to save to memory: {e}", "warning")
            return False
