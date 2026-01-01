"""
Main orchestrator for AI-powered project analysis.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .analyzers import AnalyzerFactory
from .cache_manager import CacheManager
from .claude_client import CLAUDE_SDK_AVAILABLE, ClaudeAnalysisClient
from .cost_estimator import CostEstimator
from .models import AnalyzerType
from .result_parser import ResultParser
from .summary_printer import SummaryPrinter

# Import Langfuse integration for tracing
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        trace_context,
        is_langfuse_ready,
        flush_langfuse,
    )
    LANGFUSE_AVAILABLE = True
    # Initialize Langfuse early (idempotent - safe to call multiple times)
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    trace_context = None
    _langfuse_init_result = False

# Import ROI publisher
try:
    from analytics.roi_publisher import publish_feature_roi
    ROI_PUBLISHER_AVAILABLE = True
except ImportError:
    ROI_PUBLISHER_AVAILABLE = False


def extract_analyzer_artifacts(insights: dict[str, Any]) -> list[dict]:
    """
    Extract valuable artifacts from AI analyzer results.

    Args:
        insights: Analysis results from all analyzers

    Returns:
        List of artifact dictionaries with type, value, content, etc.
    """
    artifacts = []

    # Process each analyzer result
    for analyzer_name, result in insights.items():
        # Skip non-analyzer entries
        if analyzer_name in ["analysis_timestamp", "project_dir", "cost_estimate", "overall_score"]:
            continue

        # Skip errors
        if not isinstance(result, dict) or "error" in result:
            continue

        # Extract architecture insights
        if analyzer_name == "architecture":
            for insight in result.get("insights", []):
                if isinstance(insight, str) and len(insight) > 20:
                    artifacts.append({
                        "type": "architecture_insight",
                        "format": "text",
                        "content": insight[:500],
                        "value_usd": 200,
                        "description": "Architecture insight",
                        "tab": "techlead",
                        "analyzer": analyzer_name,
                    })

            # Extract patterns as architecture insights
            for pattern in result.get("patterns", []):
                if isinstance(pattern, dict):
                    pattern_text = pattern.get("name", "") or pattern.get("description", "")
                elif isinstance(pattern, str):
                    pattern_text = pattern
                else:
                    continue
                if pattern_text and len(pattern_text) > 10:
                    artifacts.append({
                        "type": "architecture_insight",
                        "format": "text",
                        "content": pattern_text[:500],
                        "value_usd": 200,
                        "description": "Architecture pattern",
                        "tab": "techlead",
                        "analyzer": analyzer_name,
                    })

        # Extract tech debt items
        if analyzer_name == "code_quality" or analyzer_name == "tech_debt":
            for debt_item in result.get("debt_items", result.get("issues", [])):
                if isinstance(debt_item, dict):
                    debt_text = debt_item.get("description", "") or debt_item.get("message", "")
                elif isinstance(debt_item, str):
                    debt_text = debt_item
                else:
                    continue
                if debt_text and len(debt_text) > 20:
                    artifacts.append({
                        "type": "tech_debt_item",
                        "format": "text",
                        "content": debt_text[:500],
                        "value_usd": 100,
                        "description": "Technical debt item",
                        "tab": "dev",
                        "analyzer": analyzer_name,
                    })

        # Extract security findings
        if analyzer_name == "security":
            for finding in result.get("findings", result.get("vulnerabilities", [])):
                if isinstance(finding, dict):
                    finding_text = finding.get("description", "") or finding.get("message", "")
                    severity = finding.get("severity", "medium")
                elif isinstance(finding, str):
                    finding_text = finding
                    severity = "medium"
                else:
                    continue
                if finding_text and len(finding_text) > 20:
                    # Higher value for high/critical severity
                    value = 250 if severity in ["high", "critical"] else 150
                    artifacts.append({
                        "type": "security_audit",
                        "format": "text",
                        "content": finding_text[:500],
                        "value_usd": value,
                        "description": f"Security finding ({severity})",
                        "tab": "ops",
                        "analyzer": analyzer_name,
                        "severity": severity,
                    })

        # Extract performance bottlenecks
        if analyzer_name == "performance":
            for bottleneck in result.get("bottlenecks", result.get("issues", [])):
                if isinstance(bottleneck, dict):
                    bottleneck_text = bottleneck.get("description", "") or bottleneck.get("message", "")
                elif isinstance(bottleneck, str):
                    bottleneck_text = bottleneck
                else:
                    continue
                if bottleneck_text and len(bottleneck_text) > 20:
                    artifacts.append({
                        "type": "performance_bottleneck",
                        "format": "text",
                        "content": bottleneck_text[:500],
                        "value_usd": 150,
                        "description": "Performance bottleneck",
                        "tab": "ops",
                        "analyzer": analyzer_name,
                    })

        # Extract code quality score
        score = result.get("score")
        if score is not None and analyzer_name == "code_quality":
            artifacts.append({
                "type": "code_quality_score",
                "format": "numeric",
                "content": str(score),
                "value_usd": 50,
                "description": f"Code quality score: {score}/100",
                "tab": "dev",
                "analyzer": analyzer_name,
                "score": score,
            })

        # Extract recommendations from any analyzer
        for rec in result.get("recommendations", []):
            if isinstance(rec, dict):
                rec_text = rec.get("description", "") or rec.get("text", "")
            elif isinstance(rec, str):
                rec_text = rec
            else:
                continue
            if rec_text and len(rec_text) > 20:
                artifacts.append({
                    "type": "recommendation",
                    "format": "text",
                    "content": rec_text[:500],
                    "value_usd": 75,
                    "description": f"Recommendation from {analyzer_name}",
                    "tab": "techlead",
                    "analyzer": analyzer_name,
                })

    return artifacts


class AIAnalyzerRunner:
    """Orchestrates AI-powered project analysis."""

    def __init__(self, project_dir: Path, project_index: dict[str, Any]):
        """
        Initialize AI analyzer.

        Args:
            project_dir: Root directory of project
            project_index: Output from programmatic analyzer (analyzer.py)
        """
        self.project_dir = project_dir
        self.project_index = project_index
        self.cache_manager = CacheManager(project_dir / ".auto-claude" / "ai_cache")
        self.cost_estimator = CostEstimator(project_dir, project_index)
        self.result_parser = ResultParser()
        self.summary_printer = SummaryPrinter()

    async def run_full_analysis(
        self, skip_cache: bool = False, selected_analyzers: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Run all AI analyzers.

        Args:
            skip_cache: If True, ignore cached results
            selected_analyzers: If provided, only run these analyzers

        Returns:
            Complete AI insights
        """
        self._print_header()

        # Check for cached analysis
        cached_result = self.cache_manager.get_cached_result(skip_cache)
        if cached_result:
            return cached_result

        if not CLAUDE_SDK_AVAILABLE:
            print("✗ Claude Agent SDK not available. Cannot run AI analysis.")
            return {"error": "Claude SDK not installed"}

        # Estimate cost before running
        cost_estimate = self.cost_estimator.estimate_cost()
        self.summary_printer.print_cost_estimate(cost_estimate.__dict__)

        # Initialize results
        insights = {
            "analysis_timestamp": datetime.now().isoformat(),
            "project_dir": str(self.project_dir),
            "cost_estimate": cost_estimate.__dict__,
        }

        # Determine which analyzers to run
        analyzers_to_run = self._get_analyzers_to_run(selected_analyzers)

        # Prepare Langfuse trace context
        use_langfuse = LANGFUSE_AVAILABLE and is_langfuse_ready()
        project_id = self.project_dir.name
        trace_name = f"ai-analyzer-{project_id}"
        trace_ctx = None
        langfuse_ctx_obj = None
        langfuse_trace_id = None
        start_time = time.time()

        try:
            # Create Langfuse trace context if available
            if use_langfuse and trace_context:
                trace_ctx = trace_context(
                    name=trace_name,
                    project_id=project_id,
                    agent_type="ai_analyzer",
                    metadata={
                        "analyzers": analyzers_to_run,
                        "cost_estimate": cost_estimate.__dict__,
                    },
                    tags=["ai_analyzer", f"project:{project_id}"],
                    input_data={
                        "project_dir": str(self.project_dir),
                        "analyzers_count": len(analyzers_to_run),
                    },
                )
                langfuse_ctx_obj = trace_ctx.__enter__()
                if langfuse_ctx_obj and hasattr(langfuse_ctx_obj, 'trace_id'):
                    langfuse_trace_id = langfuse_ctx_obj.trace_id

            # Run each analyzer
            await self._run_analyzers(analyzers_to_run, insights)

            # Calculate overall score
            insights["overall_score"] = self._calculate_overall_score(
                analyzers_to_run, insights
            )

            # Cache results
            self.cache_manager.save_result(insights)
            print(f"\n📊 Overall Score: {insights['overall_score']}/100")

            # Publish ROI metrics
            if ROI_PUBLISHER_AVAILABLE:
                try:
                    duration_seconds = time.time() - start_time

                    # Extract artifacts from analysis results
                    artifacts = extract_analyzer_artifacts(insights)

                    # Count artifact types for metrics
                    architecture_insights = sum(1 for a in artifacts if a["type"] == "architecture_insight")
                    tech_debt_items = sum(1 for a in artifacts if a["type"] == "tech_debt_item")
                    security_findings = sum(1 for a in artifacts if a["type"] == "security_audit")
                    performance_bottlenecks = sum(1 for a in artifacts if a["type"] == "performance_bottleneck")
                    code_quality_scores = sum(1 for a in artifacts if a["type"] == "code_quality_score")
                    recommendations = sum(1 for a in artifacts if a["type"] == "recommendation")

                    # Calculate total artifact value
                    total_artifact_value = sum(a.get("value_usd", 0) for a in artifacts)

                    # Estimate tokens and cost (from cost estimate)
                    estimated_tokens = cost_estimate.estimated_tokens if hasattr(cost_estimate, 'estimated_tokens') else 0
                    estimated_cost = cost_estimate.estimated_cost_usd if hasattr(cost_estimate, 'estimated_cost_usd') else 0.0

                    await publish_feature_roi(
                        feature_type="ai_analyzer",
                        project_id=project_id,
                        cost_usd=estimated_cost,
                        tokens=estimated_tokens,
                        duration_seconds=duration_seconds,
                        trace_id=langfuse_trace_id,
                        metrics={
                            "analyzers_run": len(analyzers_to_run),
                            "overall_score": insights.get("overall_score", 0),
                            "architecture_insights": architecture_insights,
                            "tech_debt_items": tech_debt_items,
                            "security_findings": security_findings,
                            "performance_bottlenecks": performance_bottlenecks,
                            "code_quality_scores": code_quality_scores,
                            "recommendations": recommendations,
                            "total_artifacts": len(artifacts),
                            "total_artifact_value_usd": total_artifact_value,
                        },
                    )
                except Exception as e:
                    # Don't break the main flow if ROI publishing fails
                    print(f"Warning: Failed to publish ROI metrics: {e}")

            # Finalize Langfuse trace
            if trace_ctx and langfuse_ctx_obj:
                try:
                    langfuse_ctx_obj.set_output({
                        "overall_score": insights.get("overall_score", 0),
                        "analyzers_completed": len(analyzers_to_run),
                        "artifacts_extracted": len(artifacts) if 'artifacts' in dir() else 0,
                    })
                    trace_ctx.__exit__(None, None, None)
                    flush_langfuse()
                except Exception:
                    pass

            return insights

        except Exception as e:
            # Ensure trace is closed on error
            if trace_ctx:
                try:
                    trace_ctx.__exit__(type(e), e, e.__traceback__)
                    flush_langfuse()
                except Exception:
                    pass
            raise

    def _print_header(self) -> None:
        """Print analysis header."""
        print("\n" + "=" * 60)
        print("  AI-ENHANCED PROJECT ANALYSIS")
        print("=" * 60 + "\n")

    def _get_analyzers_to_run(self, selected_analyzers: list[str] | None) -> list[str]:
        """
        Determine which analyzers to run.

        Args:
            selected_analyzers: User-selected analyzers or None for all

        Returns:
            List of analyzer names to run
        """
        if selected_analyzers:
            # Validate selected analyzers
            valid_analyzers = []
            for name in selected_analyzers:
                if name not in AnalyzerType.all_analyzers():
                    print(f"⚠️  Unknown analyzer: {name}, skipping...")
                else:
                    valid_analyzers.append(name)
            return valid_analyzers

        return AnalyzerType.all_analyzers()

    async def _run_analyzers(
        self, analyzers_to_run: list[str], insights: dict[str, Any]
    ) -> None:
        """
        Run all specified analyzers.

        Args:
            analyzers_to_run: List of analyzer names to run
            insights: Dictionary to store results
        """
        for analyzer_name in analyzers_to_run:
            print(f"\n🤖 Running {analyzer_name.replace('_', ' ').title()} Analyzer...")
            start_time = time.time()

            try:
                result = await self._run_single_analyzer(analyzer_name)
                insights[analyzer_name] = result

                duration = time.time() - start_time
                score = result.get("score", 0)
                print(f"   ✓ Completed in {duration:.1f}s (score: {score}/100)")

            except Exception as e:
                print(f"   ✗ Error: {e}")
                insights[analyzer_name] = {"error": str(e)}

    async def _run_single_analyzer(self, analyzer_name: str) -> dict[str, Any]:
        """
        Run a specific AI analyzer.

        Args:
            analyzer_name: Name of the analyzer to run

        Returns:
            Analysis result dictionary
        """
        # Create analyzer instance
        analyzer = AnalyzerFactory.create(analyzer_name, self.project_index)

        # Get prompt and default result
        prompt = analyzer.get_prompt()
        default_result = analyzer.get_default_result()

        # Run Claude query
        client = ClaudeAnalysisClient(self.project_dir)
        response, _trace_id = await client.run_analysis_query(prompt)

        # Parse and return result
        return self.result_parser.parse_json_response(response, default_result)

    def _calculate_overall_score(
        self, analyzers_to_run: list[str], insights: dict[str, Any]
    ) -> int:
        """
        Calculate overall score from individual analyzer scores.

        Args:
            analyzers_to_run: List of analyzers that were run
            insights: Analysis results

        Returns:
            Overall score (0-100)
        """
        scores = [
            insights[name].get("score", 0)
            for name in analyzers_to_run
            if name in insights and "error" not in insights[name]
        ]

        return sum(scores) // len(scores) if scores else 0

    def print_summary(self, insights: dict[str, Any]) -> None:
        """
        Print a summary of the AI insights.

        Args:
            insights: Analysis results dictionary
        """
        self.summary_printer.print_summary(insights)
