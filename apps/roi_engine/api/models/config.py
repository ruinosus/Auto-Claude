"""
Configuration Pydantic models for the ROI Engine API.

Contains models for rate tables and configuration.
"""

from pydantic import BaseModel


class RateTableResponse(BaseModel):
    """Response for rate table."""

    rates: dict[str, dict[str, float]]
    description: str = "Hourly rates by seniority and role"
