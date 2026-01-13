"""
ROI Comparison Module
=====================

.. deprecated::
    This module is DEPRECATED. Use the ROI Engine instead:

    from roi_engine.core import calculate_roi_for_project

    The ROI Engine API provides comparison endpoints at:
    - GET /api/benchmark/squad - Compare squad configurations
    - GET /api/benchmark/project - Compare across projects
    - GET /api/benchmark/efficiency - Efficiency metrics

    See apps/roi_engine/ for the new implementation.
    This module will be removed in a future release.

LEGACY: Provides comparative ROI analysis between projects and market benchmarks.

Market benchmarks are based on:
- Forrester study: Average 370% ROI for AI coding tools
- GitHub study: Top performers see $10.30 value per $1 cost
- Industry median: 26% time saved with AI coding assistance
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Market Benchmark Constants
# =============================================================================

# Market benchmarks from research (Forrester, GitHub studies)
MARKET_BENCHMARKS = {
    "average_roi": 370,  # 370% ROI (Forrester study)
    "top_performers_roi": 1030,  # $10.30 per $1 (top 10% performers)
    "median_roi": 250,  # Median industry ROI
    "low_performers_roi": 100,  # Bottom 25% performers
    "median_time_saved_percent": 26,  # 26% time saved (median)
    "adoption_high_weekly_percent": 70,  # 70% weekly usage (high adoption)
    "adoption_medium_weekly_percent": 40,  # 40% weekly usage (medium)
}


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class ROIComparison:
    """ROI comparison result for a project against market benchmarks."""

    project_id: str
    roi_percentage: float
    cost_per_dollar_value: float  # $1 cost -> $X value
    break_even_days: Optional[int]
    vs_market_avg: float  # % above/below market average (positive = above)
    percentile: int  # Top X% (1 = top 1%, 100 = bottom)
    market_position: str  # "top_performer", "above_average", "average", "below_average"
    total_value_usd: float
    total_cost_usd: float
    net_value_usd: float
    calculated_at: datetime


@dataclass
class ProjectROIData:
    """Internal data structure for project ROI calculation."""

    project_id: str
    total_value_usd: float
    total_cost_usd: float
    roi_percentage: float
    trace_count: int
    first_trace_date: Optional[datetime]
    latest_trace_date: Optional[datetime]


@dataclass
class BreakEvenAnalysis:
    """Break-even analysis result."""

    project_id: str
    break_even_days: Optional[int]
    daily_value_rate: float
    daily_cost_rate: float
    cumulative_value: float
    cumulative_cost: float
    is_profitable: bool
    days_since_start: int
    projected_annual_roi: Optional[float]


# =============================================================================
# ROI Comparator Class
# =============================================================================


class ROIComparator:
    """
    Compare project ROI against market benchmarks and other projects.

    Usage:
        comparator = ROIComparator()

        # Compare single project to market
        comparison = comparator.compare_to_market(project_roi=450, ...)

        # Compare multiple projects
        comparisons = comparator.compare_projects([project_data1, project_data2])

        # Calculate break-even
        break_even = comparator.calculate_break_even(project_data)
    """

    def __init__(self, custom_benchmarks: Optional[Dict[str, float]] = None):
        """
        Initialize the comparator with optional custom benchmarks.

        Args:
            custom_benchmarks: Override default market benchmarks
        """
        self.benchmarks = {**MARKET_BENCHMARKS}
        if custom_benchmarks:
            self.benchmarks.update(custom_benchmarks)

    def compare_to_market(
        self,
        project_id: str,
        roi_percentage: float,
        total_value_usd: float = 0.0,
        total_cost_usd: float = 0.0,
        days_active: Optional[int] = None,
    ) -> ROIComparison:
        """
        Compare a project's ROI to market benchmarks.

        Args:
            project_id: Unique identifier for the project
            roi_percentage: The project's ROI percentage
            total_value_usd: Total value generated
            total_cost_usd: Total cost incurred
            days_active: Number of days the project has been active

        Returns:
            ROIComparison with market positioning data
        """
        market_avg = self.benchmarks["average_roi"]
        top_performers = self.benchmarks["top_performers_roi"]
        median_roi = self.benchmarks["median_roi"]
        low_performers = self.benchmarks["low_performers_roi"]

        # Calculate vs market average (percentage difference)
        if market_avg > 0:
            vs_market = ((roi_percentage - market_avg) / market_avg) * 100
        else:
            vs_market = 0.0

        # Calculate percentile (approximation based on distribution)
        percentile = self._calculate_percentile(roi_percentage)

        # Determine market position
        if roi_percentage >= top_performers:
            market_position = "top_performer"
        elif roi_percentage >= market_avg:
            market_position = "above_average"
        elif roi_percentage >= median_roi:
            market_position = "average"
        elif roi_percentage >= low_performers:
            market_position = "below_average"
        else:
            market_position = "needs_improvement"

        # Calculate cost per dollar value (value returned per $1 spent)
        if total_cost_usd > 0:
            cost_per_dollar = total_value_usd / total_cost_usd
        elif total_value_usd > 0:
            cost_per_dollar = float("inf")  # Infinite return (no cost)
        else:
            cost_per_dollar = 0.0

        # Calculate break-even days (if we have activity data)
        break_even_days = None
        if days_active and days_active > 0 and total_cost_usd > 0:
            daily_value = total_value_usd / days_active
            daily_cost = total_cost_usd / days_active
            if daily_value > daily_cost:
                # Already profitable
                break_even_days = 0
            elif daily_value > 0:
                # Days until break-even
                net_daily_gain = daily_value - daily_cost
                if net_daily_gain > 0:
                    remaining_deficit = total_cost_usd - total_value_usd
                    if remaining_deficit > 0:
                        break_even_days = int(remaining_deficit / net_daily_gain)
                    else:
                        break_even_days = 0

        net_value = total_value_usd - total_cost_usd

        return ROIComparison(
            project_id=project_id,
            roi_percentage=roi_percentage,
            cost_per_dollar_value=cost_per_dollar,
            break_even_days=break_even_days,
            vs_market_avg=round(vs_market, 1),
            percentile=percentile,
            market_position=market_position,
            total_value_usd=total_value_usd,
            total_cost_usd=total_cost_usd,
            net_value_usd=net_value,
            calculated_at=datetime.utcnow(),
        )

    def _calculate_percentile(self, roi_percentage: float) -> int:
        """
        Calculate approximate percentile based on ROI.

        This uses a simplified distribution model based on industry data:
        - Top 5%: ROI >= 1030% (top performers)
        - Top 25%: ROI >= 500%
        - Top 50%: ROI >= 370% (market average)
        - Top 75%: ROI >= 250% (median)
        - Bottom 25%: ROI < 100%
        """
        top_performers = self.benchmarks["top_performers_roi"]
        market_avg = self.benchmarks["average_roi"]
        median_roi = self.benchmarks["median_roi"]
        low_performers = self.benchmarks["low_performers_roi"]

        if roi_percentage >= top_performers:
            # Top 5%: Scale from 1-5 based on how far above top_performers
            excess = roi_percentage - top_performers
            # Every 200% above top_performers moves up 1 percentile
            percentile = max(1, 5 - int(excess / 200))
            return percentile
        elif roi_percentage >= market_avg:
            # 5-25%: Linear interpolation between market_avg and top_performers
            range_size = top_performers - market_avg
            position = (roi_percentage - market_avg) / range_size if range_size > 0 else 0
            return int(25 - (position * 20))  # 25 down to 5
        elif roi_percentage >= median_roi:
            # 25-50%: Linear interpolation between median and market_avg
            range_size = market_avg - median_roi
            position = (roi_percentage - median_roi) / range_size if range_size > 0 else 0
            return int(50 - (position * 25))  # 50 down to 25
        elif roi_percentage >= low_performers:
            # 50-75%: Linear interpolation between low_performers and median
            range_size = median_roi - low_performers
            position = (roi_percentage - low_performers) / range_size if range_size > 0 else 0
            return int(75 - (position * 25))  # 75 down to 50
        elif roi_percentage > 0:
            # 75-95%: Below low performers but positive
            position = roi_percentage / low_performers if low_performers > 0 else 0
            return int(95 - (position * 20))  # 95 down to 75
        else:
            # Bottom 5%: Negative or zero ROI
            return min(99, max(95, 99 - int(abs(roi_percentage) / 50)))

    def compare_projects(
        self, projects: List[ProjectROIData]
    ) -> List[ROIComparison]:
        """
        Compare multiple projects against each other and market benchmarks.

        Args:
            projects: List of project ROI data

        Returns:
            List of ROIComparison objects, sorted by ROI descending
        """
        if not projects:
            return []

        comparisons = []
        for project in projects:
            # Calculate days active if we have date info
            days_active = None
            if project.first_trace_date:
                delta = (project.latest_trace_date or datetime.utcnow()) - project.first_trace_date
                days_active = max(1, delta.days)

            comparison = self.compare_to_market(
                project_id=project.project_id,
                roi_percentage=project.roi_percentage,
                total_value_usd=project.total_value_usd,
                total_cost_usd=project.total_cost_usd,
                days_active=days_active,
            )
            comparisons.append(comparison)

        # Sort by ROI descending
        comparisons.sort(key=lambda c: c.roi_percentage, reverse=True)

        return comparisons

    def calculate_break_even(
        self, project: ProjectROIData
    ) -> BreakEvenAnalysis:
        """
        Calculate break-even analysis for a project.

        Determines:
        - Daily value and cost rates
        - Days until break-even (if not already profitable)
        - Projected annual ROI based on current trajectory

        Args:
            project: Project ROI data

        Returns:
            BreakEvenAnalysis with detailed break-even metrics
        """
        # Calculate days since start
        days_since_start = 1  # Minimum 1 day
        if project.first_trace_date:
            delta = (project.latest_trace_date or datetime.utcnow()) - project.first_trace_date
            days_since_start = max(1, delta.days)

        # Calculate daily rates
        daily_value = project.total_value_usd / days_since_start
        daily_cost = project.total_cost_usd / days_since_start

        # Determine profitability
        is_profitable = project.total_value_usd >= project.total_cost_usd

        # Calculate break-even days
        break_even_days = None
        if not is_profitable and daily_value > 0:
            net_daily_gain = daily_value - daily_cost
            if net_daily_gain > 0:
                remaining_deficit = project.total_cost_usd - project.total_value_usd
                break_even_days = int(remaining_deficit / net_daily_gain)
        elif is_profitable:
            break_even_days = 0

        # Project annual ROI
        projected_annual_roi = None
        if days_since_start > 0 and project.total_cost_usd > 0:
            # Extrapolate to 365 days
            projected_annual_value = daily_value * 365
            projected_annual_cost = daily_cost * 365
            if projected_annual_cost > 0:
                projected_annual_roi = (
                    (projected_annual_value - projected_annual_cost) / projected_annual_cost
                ) * 100

        return BreakEvenAnalysis(
            project_id=project.project_id,
            break_even_days=break_even_days,
            daily_value_rate=round(daily_value, 2),
            daily_cost_rate=round(daily_cost, 2),
            cumulative_value=project.total_value_usd,
            cumulative_cost=project.total_cost_usd,
            is_profitable=is_profitable,
            days_since_start=days_since_start,
            projected_annual_roi=round(projected_annual_roi, 1) if projected_annual_roi else None,
        )

    def get_market_benchmarks(self) -> Dict[str, float]:
        """Return the current market benchmarks."""
        return self.benchmarks.copy()

    def get_percentile_thresholds(self) -> Dict[str, Dict[str, float]]:
        """
        Return ROI thresholds for each percentile bracket.

        Useful for displaying benchmark reference lines on charts.
        """
        return {
            "top_5_percent": {
                "min_roi": self.benchmarks["top_performers_roi"],
                "label": "Top 5% Performers",
            },
            "top_25_percent": {
                "min_roi": self.benchmarks["average_roi"] + 100,  # ~470%
                "label": "Top 25%",
            },
            "market_average": {
                "min_roi": self.benchmarks["average_roi"],
                "label": "Market Average",
            },
            "median": {
                "min_roi": self.benchmarks["median_roi"],
                "label": "Industry Median",
            },
            "bottom_25_percent": {
                "min_roi": self.benchmarks["low_performers_roi"],
                "label": "Bottom 25%",
            },
        }


# =============================================================================
# Module-level convenience functions
# =============================================================================

_default_comparator: Optional[ROIComparator] = None


def get_comparator() -> ROIComparator:
    """Get or create the default ROI comparator."""
    global _default_comparator
    if _default_comparator is None:
        _default_comparator = ROIComparator()
    return _default_comparator


def compare_to_market(
    project_id: str,
    roi_percentage: float,
    total_value_usd: float = 0.0,
    total_cost_usd: float = 0.0,
    days_active: Optional[int] = None,
) -> ROIComparison:
    """
    Convenience function to compare a project to market benchmarks.

    See ROIComparator.compare_to_market for details.
    """
    return get_comparator().compare_to_market(
        project_id=project_id,
        roi_percentage=roi_percentage,
        total_value_usd=total_value_usd,
        total_cost_usd=total_cost_usd,
        days_active=days_active,
    )


def get_market_benchmarks() -> Dict[str, float]:
    """Get the default market benchmarks."""
    return MARKET_BENCHMARKS.copy()
