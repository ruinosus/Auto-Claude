"""
ROI Engine Core Models

This module defines the core data structures for artifact-based ROI calculation.
The philosophy is simple: artifacts created by AI have value based on the human
role that would produce them and the time it would take.

Value = hourly_rate (from role + seniority) × estimated_hours (from artifact type)
ROI = (Total Artifact Value - Token Cost) / Token Cost × 100%
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Role(Enum):
    """Roles that produce artifacts in a squad."""

    DEVELOPER = "developer"
    QA = "qa"
    DEVOPS = "devops"
    PM = "pm"
    ARCHITECT = "architect"
    TECH_LEAD = "tech_lead"


class Seniority(Enum):
    """Seniority levels affecting hourly rates."""

    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"


class ArtifactStatus(Enum):
    """Status of an artifact indicating completeness.

    Only COMPLETE artifacts are included in ROI calculations.
    DRAFT artifacts are tracked but don't contribute to value until completed.
    """

    DRAFT = "draft"
    COMPLETE = "complete"


@dataclass
class ArtifactValue:
    """
    An artifact enriched with role-based value calculation.

    This is the core entity of the ROI Engine. It takes a raw artifact
    from storage and enriches it with:
    - The role that would produce this artifact
    - The hourly rate based on role + seniority
    - The estimated time to produce this artifact
    - The calculated value (rate × time)
    """

    # From existing artifact storage
    artifact_id: str
    artifact_type: str
    content: str
    trace_id: str | None = None
    spec_id: str | None = None
    agent_type: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    # Enriched by ROI Engine
    role: Role = Role.DEVELOPER
    seniority: Seniority = Seniority.SENIOR
    hourly_rate: float = 150.0
    estimated_hours: float = 1.0
    calculated_value: float = 0.0

    # Status and quality (Phase 5G)
    status: ArtifactStatus = ArtifactStatus.COMPLETE
    quality_score: float = 1.0  # 0.0 to 1.0

    # Metadata
    original_value: float = 0.0  # Original fixed value for comparison
    value_source: str = "default"  # "squad_config" or "default"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Calculate value if not set and validate quality_score."""
        if self.calculated_value == 0.0:
            self.calculated_value = self.hourly_rate * self.estimated_hours
        # Clamp quality_score to valid range
        self.quality_score = max(0.0, min(1.0, self.quality_score))

    @property
    def adjusted_value(self) -> float:
        """Calculate quality-adjusted value.

        Formula: value × (0.5 + quality_score × 0.5)
        - quality_score 0.0 → 50% of calculated_value
        - quality_score 1.0 → 100% of calculated_value

        This ensures even low-quality artifacts retain some value,
        while high-quality artifacts get full value.
        """
        return self.calculated_value * (0.5 + self.quality_score * 0.5)

    @property
    def is_complete(self) -> bool:
        """Check if artifact is complete and should be included in ROI."""
        return self.status == ArtifactStatus.COMPLETE


@dataclass
class ROIResult:
    """
    Aggregated ROI for a trace, spec, or project.

    This is the output of the ROI calculation - a complete summary
    of value generated vs cost incurred.
    """

    # Identification
    scope: str  # "trace", "spec", or "project"
    scope_id: str  # trace_id, spec_id, or project_id

    # Value breakdown
    total_artifact_value: float = 0.0
    artifact_count: int = 0
    by_role: dict[str, float] = field(default_factory=dict)
    by_type: dict[str, float] = field(default_factory=dict)

    # Cost
    token_cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0

    # ROI calculation
    net_value: float = 0.0
    roi_percentage: float = 0.0

    # Artifacts included
    artifacts: list[ArtifactValue] = field(default_factory=list)

    # Metadata
    calculated_at: datetime = field(default_factory=datetime.now)
    squad_config_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "scope": self.scope,
            "scope_id": self.scope_id,
            "total_artifact_value": self.total_artifact_value,
            "artifact_count": self.artifact_count,
            "by_role": self.by_role,
            "by_type": self.by_type,
            "token_cost": self.token_cost,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "net_value": self.net_value,
            "roi_percentage": self.roi_percentage,
            "calculated_at": self.calculated_at.isoformat(),
            "squad_config_id": self.squad_config_id,
        }


@dataclass
class ROISummary:
    """
    High-level ROI summary for dashboards.

    A simplified view of ROI metrics for display purposes.
    """

    total_value: float
    total_cost: float
    net_value: float
    roi_percentage: float
    artifact_count: int

    # Top contributors
    top_role: str | None = None
    top_role_value: float = 0.0
    top_artifact_type: str | None = None
    top_artifact_type_value: float = 0.0

    @classmethod
    def from_roi_result(cls, result: ROIResult) -> "ROISummary":
        """Create summary from full ROI result."""
        # Find top role
        top_role = None
        top_role_value = 0.0
        for role, value in result.by_role.items():
            if value > top_role_value:
                top_role = role
                top_role_value = value

        # Find top artifact type
        top_type = None
        top_type_value = 0.0
        for artifact_type, value in result.by_type.items():
            if value > top_type_value:
                top_type = artifact_type
                top_type_value = value

        return cls(
            total_value=result.total_artifact_value,
            total_cost=result.token_cost,
            net_value=result.net_value,
            roi_percentage=result.roi_percentage,
            artifact_count=result.artifact_count,
            top_role=top_role,
            top_role_value=top_role_value,
            top_artifact_type=top_type,
            top_artifact_type_value=top_type_value,
        )
