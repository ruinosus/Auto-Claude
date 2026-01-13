"""
Common/Base Pydantic models for the ROI Engine API.

Contains base models used across multiple domains:
- HealthResponse
- ErrorResponse
"""

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str
    langfuse_available: bool


class HealthCheckResponse(BaseModel):
    """Detailed health check response."""

    status: str = "ok"
    version: str = "0.1.0"
    langfuse_connected: bool = False
    artifact_storage_available: bool = False
    uptime_seconds: float = 0.0
    last_activity: datetime | None = None


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
