"""
Migration Pydantic models for the ROI Engine API.

Contains models for artifact migration operations.
"""

from pydantic import BaseModel


class MigrationValueChange(BaseModel):
    """Value change for a single artifact during migration."""

    artifact_id: str
    old_value: float = 0.0
    new_value: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0


class MigrationSummary(BaseModel):
    """Summary statistics for migration."""

    total_artifacts: int = 0
    migrated: int = 0
    skipped: int = 0
    errors: int = 0
    duration_seconds: float = 0.0


class MigrationValueSummary(BaseModel):
    """Value summary for migration."""

    total_old_value: float = 0.0
    total_new_value: float = 0.0
    total_change: float = 0.0
    avg_change_pct: float = 0.0


class MigrationResponse(BaseModel):
    """Response for artifact migration operation."""

    success: bool
    summary: MigrationSummary
    value_summary: MigrationValueSummary
    value_changes: list[MigrationValueChange] = []
    errors: list[str] = []
    message: str = ""
