"""
ROI Engine REST API.

Provides FastAPI endpoints for ROI calculation and artifact valuation.

Usage:
    # Run as standalone API server
    uvicorn roi_engine.api.app:app --host 0.0.0.0 --port 8002

    # Or use the app directly
    from roi_engine.api import app
"""

from .app import app
from .models import (
    ROIRequest,
    SpecROIRequest,
    TraceROIRequest,
    ArtifactValuePreviewRequest,
    ArtifactValueResponse,
    ROIResponse,
    ROISummaryResponse,
    ArtifactListResponse,
    ArtifactValuePreviewResponse,
    RateTableResponse,
    ArtifactTypesResponse,
    HealthResponse,
    ErrorResponse,
)

__all__ = [
    # App
    "app",
    # Request models
    "ROIRequest",
    "SpecROIRequest",
    "TraceROIRequest",
    "ArtifactValuePreviewRequest",
    # Response models
    "ArtifactValueResponse",
    "ROIResponse",
    "ROISummaryResponse",
    "ArtifactListResponse",
    "ArtifactValuePreviewResponse",
    "RateTableResponse",
    "ArtifactTypesResponse",
    "HealthResponse",
    "ErrorResponse",
]
