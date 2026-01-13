"""
Artifact Pydantic models for the ROI Engine API.

Contains models for artifact CRUD, search, statistics, and management.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
# Request Models
# ═══════════════════════════════════════════════════════════════


class ArtifactValuePreviewRequest(BaseModel):
    """Request to preview artifact value calculation."""

    artifact_type: str = Field(..., description="Type of artifact")
    seniority: str = Field("senior", description="Seniority level")
    project_dir: str | None = Field(None, description="Project directory for squad config")


# ═══════════════════════════════════════════════════════════════
# Response Models - Core
# ═══════════════════════════════════════════════════════════════


class ArtifactValueResponse(BaseModel):
    """Response for a single valued artifact."""

    artifact_id: str
    artifact_type: str
    role: str
    seniority: str
    hourly_rate: float
    estimated_hours: float
    calculated_value: float
    original_value: float
    value_source: str


class ArtifactListResponse(BaseModel):
    """Response for artifact listing."""

    artifacts: list[ArtifactValueResponse]
    total_count: int
    total_value: float


class ArtifactValuePreviewResponse(BaseModel):
    """Response for artifact value preview."""

    artifact_type: str
    role: str
    seniority: str
    estimated_hours: float
    hourly_rate: float
    calculated_value: float
    formula: str


class ArtifactTypesResponse(BaseModel):
    """Response for artifact types listing."""

    types: list[dict[str, Any]]
    total_count: int


# ═══════════════════════════════════════════════════════════════
# Response Models - Search
# ═══════════════════════════════════════════════════════════════


class ArtifactSearchResult(BaseModel):
    """Search result for an artifact."""

    artifact_id: str
    artifact_type: str
    content_preview: str
    description: str | None = None
    created_at: datetime
    spec_id: str | None = None
    value_usd: float = 0.0
    match_score: float = 1.0


class ArtifactSearchResponse(BaseModel):
    """Response for artifact search."""

    results: list[ArtifactSearchResult]
    total_count: int
    query: str


class LocalArtifactResponse(BaseModel):
    """Response for a local artifact."""

    id: str
    type: str
    content: str
    description: str | None = None
    value_usd: float = 0.0
    created_at: str
    spec_id: str | None = None
    trace_id: str | None = None
    storage_path: str


class LocalArtifactsListResponse(BaseModel):
    """Response for local artifacts listing."""

    artifacts: list[LocalArtifactResponse]
    total_count: int
    total_value: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Response Models - Statistics & Timeline
# ═══════════════════════════════════════════════════════════════


class ArtifactStatisticsResponse(BaseModel):
    """Aggregate artifact statistics."""

    total_artifacts: int = 0
    total_value: float = 0.0
    avg_value_per_artifact: float = 0.0
    by_type_count: dict[str, int] = {}
    by_type_value: dict[str, float] = {}
    by_role_count: dict[str, int] = {}
    by_role_value: dict[str, float] = {}
    most_valuable_type: str | None = None
    most_common_type: str | None = None
    period_start: str | None = None
    period_end: str | None = None


class ArtifactTimelinePoint(BaseModel):
    """Single point in artifact timeline."""

    date: str
    artifact_count: int = 0
    total_value: float = 0.0
    by_type: dict[str, int] = {}


class ArtifactTimelineResponse(BaseModel):
    """Artifact timeline response."""

    timeline: list[ArtifactTimelinePoint]
    period_start: str
    period_end: str
    total_artifacts: int = 0
    total_value: float = 0.0


class ArtifactsByRoleItem(BaseModel):
    """Artifacts grouped by role."""

    role: str
    role_description: str
    artifact_count: int = 0
    total_value: float = 0.0
    avg_value_per_artifact: float = 0.0
    artifact_types: list[str] = []
    top_artifacts: list[dict[str, Any]] = []


class ArtifactsByRoleResponse(BaseModel):
    """Response for artifacts grouped by role."""

    by_role: list[ArtifactsByRoleItem]
    total_artifacts: int = 0
    total_value: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Response Models - Management (Duplicates, Merge, Status, Quality)
# ═══════════════════════════════════════════════════════════════


class DuplicateArtifactPair(BaseModel):
    """A pair of potentially duplicate artifacts."""

    artifact_1_id: str
    artifact_1_type: str
    artifact_1_preview: str
    artifact_1_value: float = 0.0
    artifact_2_id: str
    artifact_2_type: str
    artifact_2_preview: str
    artifact_2_value: float = 0.0
    similarity_score: float = 0.0  # 0.0 to 1.0
    similarity_reason: str = ""  # Why they are similar


class DuplicatesResponse(BaseModel):
    """Response for finding duplicate artifacts."""

    duplicates: list[DuplicateArtifactPair]
    total_pairs: int = 0
    potential_savings: float = 0.0  # Value that could be deduplicated
    scan_timestamp: datetime
    artifacts_scanned: int = 0


class MergeArtifactsRequest(BaseModel):
    """Request to merge duplicate artifacts."""

    artifact_ids: list[str] = Field(..., min_length=2, description="IDs of artifacts to merge")
    keep_artifact_id: str = Field(..., description="ID of artifact to keep (others will be merged into this)")
    merge_content: bool = Field(False, description="Combine content from all artifacts")


class MergeArtifactsResponse(BaseModel):
    """Response for artifact merge operation."""

    success: bool
    merged_artifact_id: str
    merged_artifact_type: str
    merged_artifact_value: float = 0.0
    deleted_artifact_ids: list[str]
    deleted_count: int = 0
    message: str = ""


class UpdateStatusRequest(BaseModel):
    """Request to update artifact status."""

    status: str = Field(..., pattern="^(draft|complete)$", description="New status: 'draft' or 'complete'")


class UpdateStatusResponse(BaseModel):
    """Response for status update operation."""

    success: bool
    artifact_id: str
    old_status: str
    new_status: str
    value_change: float = 0.0  # Value added/removed from ROI calculations
    message: str = ""


class UpdateQualityRequest(BaseModel):
    """Request to update artifact quality score."""

    quality_score: float = Field(..., ge=0.0, le=1.0, description="Quality score between 0.0 and 1.0")


class UpdateQualityResponse(BaseModel):
    """Response for quality update operation."""

    success: bool
    artifact_id: str
    old_quality_score: float
    new_quality_score: float
    old_adjusted_value: float = 0.0
    new_adjusted_value: float = 0.0
    value_change: float = 0.0
    message: str = ""


class DeleteArtifactResponse(BaseModel):
    """Response for artifact deletion."""

    success: bool
    artifact_id: str
    artifact_type: str
    deleted_value: float = 0.0  # Value removed from ROI
    message: str = ""


# ═══════════════════════════════════════════════════════════════
# Response Models - Editor Panel
# ═══════════════════════════════════════════════════════════════


class UpdateContentRequest(BaseModel):
    """Request to update artifact content."""

    content: str = Field(..., min_length=1, description="New content for the artifact")
    append: bool = Field(False, description="If true, append to existing content instead of replacing")


class UpdateContentResponse(BaseModel):
    """Response for content update operation."""

    success: bool
    artifact_id: str
    content_length: int = 0
    previous_length: int = 0
    message: str = ""


class ContinueArtifactRequest(BaseModel):
    """Request to continue an artifact via LLM."""

    prompt: str = Field(
        default="Continue this artifact with more detail and completeness.",
        description="Prompt to guide the LLM continuation"
    )
    max_tokens: int = Field(1000, ge=100, le=4000, description="Maximum tokens for continuation")
    model: str = Field("claude-3-haiku-20240307", description="Model to use for continuation")


class ContinueArtifactResponse(BaseModel):
    """Response for artifact continuation."""

    success: bool
    artifact_id: str
    original_content: str
    continued_content: str
    added_content: str
    tokens_used: int = 0
    message: str = ""


class CompleteArtifactResponse(BaseModel):
    """Response for marking artifact as complete."""

    success: bool
    artifact_id: str
    old_status: str
    new_status: str = "complete"
    quality_score: float = 1.0
    calculated_value: float = 0.0
    adjusted_value: float = 0.0
    message: str = ""
