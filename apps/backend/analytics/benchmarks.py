# apps/backend/analytics/benchmarks.py
"""Market benchmarks for ROI comparison (G15)"""

from dataclasses import dataclass
from typing import Dict, Literal

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


class BenchmarkService:
    """Service for market benchmark comparisons"""

    def get_benchmark(self, region: Region, seniority: Seniority) -> Benchmark:
        """Get benchmark for specific region and seniority"""
        return Benchmark(
            region=region,
            seniority=seniority,
            hourly_rate=HOURLY_RATES[region][seniority],
            minutes_per_line=MINUTES_PER_LINE[seniority]
        )

    def get_all_benchmarks(self) -> list[Benchmark]:
        """Get all available benchmarks"""
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
        """Calculate savings compared to a benchmark"""
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
        all_rois: list[float]
    ) -> int:
        """Calculate percentile ranking for an ROI value"""
        if not all_rois:
            return 50  # Default to median

        count_below = sum(1 for r in all_rois if r < roi_percent)
        percentile = int((count_below / len(all_rois)) * 100)
        return percentile
