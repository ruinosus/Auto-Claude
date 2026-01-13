"""
ROI Engine API Routes Package.

This package contains modular route files organized by domain:
- roi.py: ROI calculation endpoints
- artifacts.py: Artifact CRUD and management endpoints
- costs.py: Cost analysis and billing endpoints
- quality.py: Quality scores and value breakdown endpoints
- traces.py: Trace and session endpoints
- benchmarks.py: Benchmarking endpoints
- forecasts.py: Forecasting endpoints
- time_saved.py: Time saved metrics endpoints
- satisfaction.py: Satisfaction survey endpoints
- migration.py: Migration endpoints
- config.py: Configuration and health endpoints
- metrics.py: Hourly and error metrics endpoints
"""

from .roi import router as roi_router
from .artifacts import router as artifacts_router
from .costs import router as costs_router
from .quality import router as quality_router
from .traces import router as traces_router
from .benchmarks import router as benchmarks_router
from .forecasts import router as forecasts_router
from .time_saved import router as time_saved_router
from .satisfaction import router as satisfaction_router
from .migration import router as migration_router
from .config import router as config_router, health_router
from .metrics import router as metrics_router

__all__ = [
    "roi_router",
    "artifacts_router",
    "costs_router",
    "quality_router",
    "traces_router",
    "benchmarks_router",
    "forecasts_router",
    "time_saved_router",
    "satisfaction_router",
    "migration_router",
    "config_router",
    "health_router",
    "metrics_router",
]
