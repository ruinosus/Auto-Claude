"""
Roadmap generation orchestrator.

Coordinates all phases of the roadmap generation process.
"""

import asyncio
import json
from pathlib import Path

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

from .competitor_analyzer import CompetitorAnalyzer
from .executor import AgentExecutor, ScriptExecutor
from .graph_integration import GraphHintsProvider
from .phases import DiscoveryPhase, FeaturesPhase, ProjectIndexPhase


class RoadmapOrchestrator:
    """Orchestrates the roadmap creation process."""

    def __init__(
        self,
        project_dir: Path,
        output_dir: Path | None = None,
        model: str = "claude-sonnet-4-5-20250929",
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

            result = await publish_roadmap_roi(
                project_id=project_id,
                features_identified=features_identified,
                features_rejected=features_rejected,
                cost_usd=estimated_cost,
                tokens=estimated_tokens,
                model=self.model,
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
