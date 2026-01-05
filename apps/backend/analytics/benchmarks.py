# apps/backend/analytics/benchmarks.py
"""
Team/Project Benchmarks Module
==============================

Provides internal benchmarks between teams and projects with best practices identification.
Also includes market benchmarks for external ROI comparison.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# Market Benchmarks (existing functionality)
# =============================================================================

Region = Literal['us', 'latam', 'eu']
Seniority = Literal['junior', 'mid', 'senior']


@dataclass
class Benchmark:
    region: Region
    seniority: Seniority
    hourly_rate: float
    minutes_per_line: float


# Industry benchmark data
HOURLY_RATES: Dict[str, Dict[str, float]] = {
    'us': {'junior': 50, 'mid': 85, 'senior': 130},
    'latam': {'junior': 25, 'mid': 45, 'senior': 75},
    'eu': {'junior': 40, 'mid': 70, 'senior': 110},
}

MINUTES_PER_LINE: Dict[str, float] = {
    'junior': 4.0,
    'mid': 2.5,
    'senior': 1.5,
}


# =============================================================================
# Project Benchmarks (new Module 6 functionality)
# =============================================================================

@dataclass
class ProjectBenchmark:
    """Benchmark data for a single project."""
    project_id: str
    total_roi: float
    avg_roi_per_spec: float
    total_value_generated: float
    total_cost: float
    specs_count: int
    success_rate: float  # % specs with positive ROI
    best_feature_type: str
    worst_feature_type: str
    rank: int
    # Additional metrics
    avg_qa_attempts: float = 0.0
    avg_iterations: float = 0.0
    total_hours_saved: float = 0.0
    avg_complexity: str = "medium"


@dataclass
class BestPractice:
    """A success pattern identified from top performers."""
    pattern: str
    description: str
    impact: str  # high, medium, low
    adoption_rate: float  # % of top performers using this
    examples: List[str] = field(default_factory=list)  # spec_ids demonstrating this
    category: str = "general"  # general, complexity, qa, agent, iteration


@dataclass
class PercentileComparison:
    """Comparison of a project against a specific percentile."""
    project_id: str
    percentile: int
    metrics: Dict[str, Any]  # metric_name -> {project_value, percentile_value, delta, status}


class BenchmarkService:
    """Service for both market and project benchmarks."""

    def __init__(self, langfuse_client=None):
        """
        Initialize the benchmark service.

        Args:
            langfuse_client: Optional Langfuse client for fetching real data.
                           If None, uses mock data for demonstration.
        """
        self.langfuse_client = langfuse_client
        self._project_cache: Dict[str, ProjectBenchmark] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)

    # =========================================================================
    # Market Benchmarks (existing functionality)
    # =========================================================================

    def get_benchmark(self, region: Region, seniority: Seniority) -> Benchmark:
        """Get benchmark for specific region and seniority."""
        return Benchmark(
            region=region,
            seniority=seniority,
            hourly_rate=HOURLY_RATES[region][seniority],
            minutes_per_line=MINUTES_PER_LINE[seniority]
        )

    def get_all_benchmarks(self) -> List[Benchmark]:
        """Get all available market benchmarks."""
        benchmarks = []
        for region in HOURLY_RATES:
            for seniority in HOURLY_RATES[region]:
                benchmarks.append(self.get_benchmark(region, seniority))
        return benchmarks

    def calculate_savings_vs_benchmark(
        self,
        actual_cost: float,
        lines_changed: int,
        region: Region,
        seniority: Seniority
    ) -> dict:
        """Calculate savings compared to a market benchmark."""
        benchmark = self.get_benchmark(region, seniority)

        # Calculate what it would cost with benchmark rates
        hours = (lines_changed * benchmark.minutes_per_line) / 60
        benchmark_cost = hours * benchmark.hourly_rate

        # Calculate savings
        savings = benchmark_cost - actual_cost
        savings_percent = (savings / benchmark_cost * 100) if benchmark_cost > 0 else 0

        return {
            'benchmark': benchmark,
            'benchmark_cost': benchmark_cost,
            'actual_cost': actual_cost,
            'savings': savings,
            'savings_percent': savings_percent,
            'hours_equivalent': hours
        }

    def get_percentile_ranking(
        self,
        roi_percent: float,
        all_rois: List[float]
    ) -> int:
        """Calculate percentile ranking for an ROI value."""
        if not all_rois:
            return 50  # Default to median

        count_below = sum(1 for r in all_rois if r < roi_percent)
        percentile = int((count_below / len(all_rois)) * 100)
        return percentile

    # =========================================================================
    # Project Benchmarks (new Module 6 functionality)
    # =========================================================================

    async def _fetch_project_data(self) -> List[Dict[str, Any]]:
        """
        Fetch project data from Langfuse or return mock data.

        Returns aggregated project metrics from ROI scores and traces.
        """
        if self.langfuse_client is None:
            # Return mock data for demonstration
            return self._get_mock_project_data()

        try:
            # Fetch ROI scores from Langfuse
            roi_scores = await self.langfuse_client.get_scores(name="roi_percentage")

            # Group by project_id
            project_data: Dict[str, Dict] = {}

            for score in roi_scores:
                trace = await self.langfuse_client.get_trace(score.trace_id)
                if not trace:
                    continue

                # Extract project_id from metadata
                project_id = trace.metadata.get("project_id", "unknown") if trace.metadata else "unknown"

                if project_id not in project_data:
                    project_data[project_id] = {
                        "project_id": project_id,
                        "specs": [],
                        "total_value": 0.0,
                        "total_cost": 0.0,
                        "roi_sum": 0.0,
                        "feature_types": {},
                        "qa_attempts_sum": 0,
                        "positive_roi_count": 0,
                    }

                # Get all scores for this trace
                trace_scores = await self.langfuse_client.get_scores(trace_id=score.trace_id)
                score_dict = {s.name: s.value for s in trace_scores}

                roi = score_dict.get("roi_percentage", 0)
                value = score_dict.get("total_value_usd", score_dict.get("business_value_usd", 0))
                cost = score_dict.get("total_cost_usd", score_dict.get("actual_cost_usd", 0))
                qa_attempts = int(score_dict.get("qa_attempts", 1))

                # Determine feature type
                feature_type = trace.metadata.get("feature_type", "build") if trace.metadata else "build"

                project_data[project_id]["specs"].append(score.trace_id)
                project_data[project_id]["total_value"] += value
                project_data[project_id]["total_cost"] += cost
                project_data[project_id]["roi_sum"] += roi
                project_data[project_id]["qa_attempts_sum"] += qa_attempts

                if roi > 0:
                    project_data[project_id]["positive_roi_count"] += 1

                # Track feature type performance
                if feature_type not in project_data[project_id]["feature_types"]:
                    project_data[project_id]["feature_types"][feature_type] = {"roi_sum": 0, "count": 0}
                project_data[project_id]["feature_types"][feature_type]["roi_sum"] += roi
                project_data[project_id]["feature_types"][feature_type]["count"] += 1

            return list(project_data.values())

        except Exception as e:
            logger.error(f"Failed to fetch project data from Langfuse: {e}")
            return self._get_mock_project_data()

    def _get_mock_project_data(self) -> List[Dict[str, Any]]:
        """Return mock project data for demonstration."""
        return [
            {
                "project_id": "auto-claude-fork",
                "specs": ["001-auth", "002-dashboard", "003-api"],
                "total_value": 15000.0,
                "total_cost": 45.50,
                "roi_sum": 32900.0,
                "feature_types": {
                    "build": {"roi_sum": 25000, "count": 2},
                    "insights": {"roi_sum": 7900, "count": 1},
                },
                "qa_attempts_sum": 5,
                "positive_roi_count": 3,
            },
            {
                "project_id": "my-saas-app",
                "specs": ["001-payment", "002-billing", "003-users", "004-reports"],
                "total_value": 22000.0,
                "total_cost": 68.20,
                "roi_sum": 32200.0,
                "feature_types": {
                    "build": {"roi_sum": 20000, "count": 3},
                    "roadmap": {"roi_sum": 12200, "count": 1},
                },
                "qa_attempts_sum": 7,
                "positive_roi_count": 4,
            },
            {
                "project_id": "mobile-app",
                "specs": ["001-auth", "002-profile"],
                "total_value": 8500.0,
                "total_cost": 32.10,
                "roi_sum": 26400.0,
                "feature_types": {
                    "build": {"roi_sum": 18000, "count": 1},
                    "ideation": {"roi_sum": 8400, "count": 1},
                },
                "qa_attempts_sum": 3,
                "positive_roi_count": 2,
            },
            {
                "project_id": "data-pipeline",
                "specs": ["001-ingestion"],
                "total_value": 5200.0,
                "total_cost": 28.75,
                "roi_sum": 18000.0,
                "feature_types": {
                    "build": {"roi_sum": 18000, "count": 1},
                },
                "qa_attempts_sum": 2,
                "positive_roi_count": 1,
            },
            {
                "project_id": "legacy-migration",
                "specs": ["001-db", "002-api", "003-ui", "004-tests", "005-docs"],
                "total_value": 35000.0,
                "total_cost": 125.80,
                "roi_sum": 27800.0,
                "feature_types": {
                    "build": {"roi_sum": 15000, "count": 3},
                    "insights": {"roi_sum": 8000, "count": 1},
                    "github": {"roi_sum": 4800, "count": 1},
                },
                "qa_attempts_sum": 12,
                "positive_roi_count": 4,
            },
        ]

    def _calculate_project_benchmarks(self, project_data: List[Dict[str, Any]]) -> List[ProjectBenchmark]:
        """Convert raw project data into ranked ProjectBenchmark objects."""
        benchmarks = []

        for data in project_data:
            specs_count = len(data["specs"])
            if specs_count == 0:
                continue

            # Calculate metrics
            total_roi = data["roi_sum"]
            avg_roi = total_roi / specs_count if specs_count > 0 else 0
            success_rate = (data["positive_roi_count"] / specs_count * 100) if specs_count > 0 else 0
            avg_qa = data["qa_attempts_sum"] / specs_count if specs_count > 0 else 0

            # Find best and worst feature types
            feature_types = data.get("feature_types", {})
            best_feature = "unknown"
            worst_feature = "unknown"
            best_roi = float("-inf")
            worst_roi = float("inf")

            for ft, ft_data in feature_types.items():
                ft_avg = ft_data["roi_sum"] / ft_data["count"] if ft_data["count"] > 0 else 0
                if ft_avg > best_roi:
                    best_roi = ft_avg
                    best_feature = ft
                if ft_avg < worst_roi:
                    worst_roi = ft_avg
                    worst_feature = ft

            benchmarks.append(ProjectBenchmark(
                project_id=data["project_id"],
                total_roi=total_roi,
                avg_roi_per_spec=avg_roi,
                total_value_generated=data["total_value"],
                total_cost=data["total_cost"],
                specs_count=specs_count,
                success_rate=success_rate,
                best_feature_type=best_feature,
                worst_feature_type=worst_feature,
                rank=0,  # Will be set after sorting
                avg_qa_attempts=avg_qa,
            ))

        return benchmarks

    async def get_project_rankings(
        self,
        metric: str = "roi",  # roi, value, success_rate
        period: str = "30d",
        limit: int = 10,
    ) -> List[ProjectBenchmark]:
        """
        Get projects ranked by specified metric.

        Args:
            metric: Ranking metric - 'roi', 'value', or 'success_rate'
            period: Time period filter - '7d', '30d', '90d', 'all'
            limit: Maximum number of results

        Returns:
            List of ProjectBenchmark objects sorted by the specified metric
        """
        # Fetch and calculate project data
        project_data = await self._fetch_project_data()
        benchmarks = self._calculate_project_benchmarks(project_data)

        # Sort by metric
        if metric == "roi":
            benchmarks.sort(key=lambda b: b.total_roi, reverse=True)
        elif metric == "value":
            benchmarks.sort(key=lambda b: b.total_value_generated, reverse=True)
        elif metric == "success_rate":
            benchmarks.sort(key=lambda b: b.success_rate, reverse=True)
        else:
            benchmarks.sort(key=lambda b: b.avg_roi_per_spec, reverse=True)

        # Assign ranks
        for i, benchmark in enumerate(benchmarks):
            benchmark.rank = i + 1

        return benchmarks[:limit]

    async def identify_best_practices(
        self,
        top_n: int = 10,
    ) -> List[BestPractice]:
        """
        Analyze top performers to identify success patterns.

        Looks for:
        - Average spec complexity
        - Common feature types
        - QA pass rate patterns
        - Average iterations
        - Specific agent usage patterns

        Args:
            top_n: Number of top projects to analyze

        Returns:
            List of identified best practices
        """
        # Get top performers
        rankings = await self.get_project_rankings(metric="roi", limit=top_n)

        if not rankings:
            return []

        practices = []

        # Analyze patterns
        # Pattern 1: Low QA attempts correlate with high ROI
        avg_qa = sum(p.avg_qa_attempts for p in rankings) / len(rankings)
        if avg_qa < 2.0:
            practices.append(BestPractice(
                pattern="low_qa_iterations",
                description="Top performers average less than 2 QA attempts per spec, indicating high-quality first implementations",
                impact="high",
                adoption_rate=sum(1 for p in rankings if p.avg_qa_attempts < 2.0) / len(rankings) * 100,
                examples=[p.project_id for p in rankings if p.avg_qa_attempts < 2.0][:3],
                category="qa",
            ))

        # Pattern 2: High success rate
        high_success = [p for p in rankings if p.success_rate >= 80]
        if len(high_success) >= len(rankings) * 0.5:
            practices.append(BestPractice(
                pattern="high_success_rate",
                description="Over 50% of top performers have 80%+ spec success rate (positive ROI)",
                impact="high",
                adoption_rate=len(high_success) / len(rankings) * 100,
                examples=[p.project_id for p in high_success][:3],
                category="general",
            ))

        # Pattern 3: Feature type diversity
        diverse_projects = [p for p in rankings if p.best_feature_type != p.worst_feature_type]
        if len(diverse_projects) >= len(rankings) * 0.6:
            practices.append(BestPractice(
                pattern="feature_diversity",
                description="Top performers use multiple feature types (build, insights, roadmap), not just code generation",
                impact="medium",
                adoption_rate=len(diverse_projects) / len(rankings) * 100,
                examples=[p.project_id for p in diverse_projects][:3],
                category="general",
            ))

        # Pattern 4: Build feature dominance
        build_dominant = [p for p in rankings if p.best_feature_type == "build"]
        if len(build_dominant) >= len(rankings) * 0.7:
            practices.append(BestPractice(
                pattern="build_focus",
                description="Most top performers achieve best ROI from build/implementation specs",
                impact="medium",
                adoption_rate=len(build_dominant) / len(rankings) * 100,
                examples=[p.project_id for p in build_dominant][:3],
                category="agent",
            ))

        # Pattern 5: Cost efficiency
        efficient = [p for p in rankings if p.total_value_generated > 0 and
                    (p.total_value_generated / p.total_cost if p.total_cost > 0 else 0) > 200]
        if efficient:
            practices.append(BestPractice(
                pattern="cost_efficiency",
                description="Top performers achieve over 200x value-to-cost ratio",
                impact="high",
                adoption_rate=len(efficient) / len(rankings) * 100,
                examples=[p.project_id for p in efficient][:3],
                category="general",
            ))

        # Pattern 6: Consistent spec delivery
        consistent = [p for p in rankings if p.specs_count >= 3]
        if len(consistent) >= len(rankings) * 0.5:
            practices.append(BestPractice(
                pattern="consistent_delivery",
                description="Top performers complete 3+ specs, showing consistent usage patterns",
                impact="medium",
                adoption_rate=len(consistent) / len(rankings) * 100,
                examples=[p.project_id for p in consistent][:3],
                category="iteration",
            ))

        return practices

    async def get_improvement_suggestions(
        self,
        project_id: str,
    ) -> List[str]:
        """
        Suggest improvements based on gap with top performers.

        Compares the project against top performers and identifies
        specific areas for improvement.

        Args:
            project_id: The project to analyze

        Returns:
            List of actionable improvement suggestions
        """
        suggestions = []

        # Get project data
        rankings = await self.get_project_rankings(metric="roi", limit=100)
        project = next((p for p in rankings if p.project_id == project_id), None)

        if not project:
            return ["No data available for this project. Complete some specs to enable benchmarking."]

        # Get top performers for comparison
        top_performers = rankings[:5] if len(rankings) >= 5 else rankings

        if not top_performers:
            return ["Insufficient benchmark data. More project data needed."]

        # Calculate averages of top performers
        avg_top_roi = sum(p.avg_roi_per_spec for p in top_performers) / len(top_performers)
        avg_top_success = sum(p.success_rate for p in top_performers) / len(top_performers)
        avg_top_qa = sum(p.avg_qa_attempts for p in top_performers) / len(top_performers)

        # Compare and suggest
        if project.avg_roi_per_spec < avg_top_roi * 0.5:
            suggestions.append(
                f"Your average ROI per spec ({project.avg_roi_per_spec:.0f}%) is below top performers "
                f"({avg_top_roi:.0f}%). Consider more strategic spec selection."
            )

        if project.success_rate < avg_top_success:
            suggestions.append(
                f"Your success rate ({project.success_rate:.0f}%) is below top performers "
                f"({avg_top_success:.0f}%). Focus on spec quality and clearer acceptance criteria."
            )

        if project.avg_qa_attempts > avg_top_qa * 1.5:
            suggestions.append(
                f"Your average QA attempts ({project.avg_qa_attempts:.1f}) is higher than top performers "
                f"({avg_top_qa:.1f}). Consider improving initial spec clarity and test coverage."
            )

        if project.specs_count < 3:
            suggestions.append(
                "Complete more specs to build momentum and establish patterns. "
                "Top performers typically run 3+ specs."
            )

        if project.best_feature_type == project.worst_feature_type:
            suggestions.append(
                "Diversify your feature usage. Top performers use multiple feature types "
                "(build, insights, roadmap) to maximize value."
            )

        if not suggestions:
            suggestions.append(
                f"You're performing well! Ranked #{project.rank}. "
                "Continue with current practices to maintain top performance."
            )

        return suggestions

    async def compare_to_percentile(
        self,
        project_id: str,
        percentile: int = 50,  # median
    ) -> PercentileComparison:
        """
        Compare project to specific percentile.

        Args:
            project_id: The project to compare
            percentile: Target percentile (50 = median)

        Returns:
            PercentileComparison with detailed metric comparisons
        """
        rankings = await self.get_project_rankings(metric="roi", limit=100)
        project = next((p for p in rankings if p.project_id == project_id), None)

        if not project or not rankings:
            return PercentileComparison(
                project_id=project_id,
                percentile=percentile,
                metrics={}
            )

        # Calculate percentile values
        def get_percentile_value(values: List[float], pct: int) -> float:
            if not values:
                return 0
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * pct / 100)
            idx = min(idx, len(sorted_vals) - 1)
            return sorted_vals[idx]

        metrics = {}

        # ROI comparison
        all_rois = [p.avg_roi_per_spec for p in rankings]
        pct_roi = get_percentile_value(all_rois, percentile)
        metrics["avg_roi_per_spec"] = {
            "project_value": project.avg_roi_per_spec,
            "percentile_value": pct_roi,
            "delta": project.avg_roi_per_spec - pct_roi,
            "status": "above" if project.avg_roi_per_spec > pct_roi else "below" if project.avg_roi_per_spec < pct_roi else "equal"
        }

        # Success rate comparison
        all_success = [p.success_rate for p in rankings]
        pct_success = get_percentile_value(all_success, percentile)
        metrics["success_rate"] = {
            "project_value": project.success_rate,
            "percentile_value": pct_success,
            "delta": project.success_rate - pct_success,
            "status": "above" if project.success_rate > pct_success else "below" if project.success_rate < pct_success else "equal"
        }

        # QA attempts comparison (lower is better)
        all_qa = [p.avg_qa_attempts for p in rankings]
        pct_qa = get_percentile_value(all_qa, percentile)
        metrics["avg_qa_attempts"] = {
            "project_value": project.avg_qa_attempts,
            "percentile_value": pct_qa,
            "delta": pct_qa - project.avg_qa_attempts,  # Inverted because lower is better
            "status": "above" if project.avg_qa_attempts < pct_qa else "below" if project.avg_qa_attempts > pct_qa else "equal"
        }

        # Value generated comparison
        all_values = [p.total_value_generated for p in rankings]
        pct_value = get_percentile_value(all_values, percentile)
        metrics["total_value_generated"] = {
            "project_value": project.total_value_generated,
            "percentile_value": pct_value,
            "delta": project.total_value_generated - pct_value,
            "status": "above" if project.total_value_generated > pct_value else "below" if project.total_value_generated < pct_value else "equal"
        }

        return PercentileComparison(
            project_id=project_id,
            percentile=percentile,
            metrics=metrics
        )
