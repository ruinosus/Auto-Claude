"""
Artifacts Routes - Artifact management and valuation endpoints.

Endpoints:

Basic Artifact Operations (Phase 1):
- GET  /artifacts              - List valued artifacts with filtering
- GET  /artifacts/{artifact_id} - Get a single valued artifact
- POST /artifacts/preview      - Preview artifact value calculation

Artifact Search & Local Storage (Phase 5A):
- GET  /artifacts/search       - Full-text search across artifacts
- GET  /artifacts/local        - List artifacts from local storage

Artifact Analytics (Phase 5E):
- GET  /artifacts/statistics   - Get aggregate artifact statistics
- GET  /artifacts/timeline     - Get artifacts created over time
- GET  /artifacts/by-role      - Get artifacts grouped by role

Artifact Management (Phase 5H):
- GET  /artifacts/duplicates           - Find duplicate artifacts
- POST /artifacts/merge                - Merge duplicate artifacts
- PUT  /artifacts/{artifact_id}/status  - Update artifact status (draft/complete)
- PUT  /artifacts/{artifact_id}/quality - Update artifact quality score
- DELETE /artifacts/{artifact_id}      - Permanently delete an artifact

Artifact Editor Panel (Phase 5I):
- PUT  /artifacts/{artifact_id}/content  - Edit artifact content (replace or append)
- POST /artifacts/{artifact_id}/continue - Continue artifact via LLM
- POST /artifacts/{artifact_id}/complete - Mark artifact as complete
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from core import (
    ArtifactConsumer,
    get_artifact_value_preview,
    load_squad_config,
    valuate_artifacts,
    ROLE_DESCRIPTIONS,
)
from core.models import Role, Seniority
from api.models import (
    # Basic artifact models
    ArtifactListResponse,
    ArtifactValuePreviewRequest,
    ArtifactValuePreviewResponse,
    ArtifactValueResponse,
    # Phase 5A models
    ArtifactSearchResult,
    ArtifactSearchResponse,
    LocalArtifactResponse,
    LocalArtifactsListResponse,
    # Phase 5E models
    ArtifactStatisticsResponse,
    ArtifactTimelinePoint,
    ArtifactTimelineResponse,
    ArtifactsByRoleItem,
    ArtifactsByRoleResponse,
    # Phase 5H models
    DuplicateArtifactPair,
    DuplicatesResponse,
    MergeArtifactsRequest,
    MergeArtifactsResponse,
    UpdateStatusRequest,
    UpdateStatusResponse,
    UpdateQualityRequest,
    UpdateQualityResponse,
    DeleteArtifactResponse,
    # Phase 5I models
    UpdateContentRequest,
    UpdateContentResponse,
    ContinueArtifactRequest,
    ContinueArtifactResponse,
    CompleteArtifactResponse,
)


router = APIRouter(prefix="/artifacts", tags=["Artifacts"])


# ═══════════════════════════════════════════════════════════════
# Basic Artifact Operations
# ═══════════════════════════════════════════════════════════════


@router.get(
    "",
    response_model=ArtifactListResponse,
    summary="List valued artifacts",
    description="List artifacts with role-based valuations",
)
async def list_artifacts(
    project_dir: str = Query(..., description="Project directory path"),
    spec_id: str | None = Query(None, description="Filter by spec ID"),
    trace_id: str | None = Query(None, description="Filter by trace ID"),
    artifact_type: str | None = Query(None, description="Filter by artifact type"),
    limit: int = Query(100, description="Maximum number of artifacts"),
) -> ArtifactListResponse:
    """List artifacts with valuations."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)

    # Get artifacts based on filters
    if spec_id:
        raw_artifacts = consumer.get_artifacts_for_spec(spec_id)
    elif trace_id:
        raw_artifacts = consumer.get_artifacts_for_trace(trace_id)
    else:
        raw_artifacts = consumer.get_all_artifacts(
            artifact_type=artifact_type,
            limit=limit,
        )

    # Valuate artifacts
    valued = valuate_artifacts(raw_artifacts, squad_config)

    # Convert to response
    artifacts_response = [
        ArtifactValueResponse(
            artifact_id=a.artifact_id,
            artifact_type=a.artifact_type,
            role=a.role.value,
            seniority=a.seniority.value,
            hourly_rate=a.hourly_rate,
            estimated_hours=a.estimated_hours,
            calculated_value=a.calculated_value,
            original_value=a.original_value,
            value_source=a.value_source,
        )
        for a in valued[:limit]
    ]

    return ArtifactListResponse(
        artifacts=artifacts_response,
        total_count=len(valued),
        total_value=sum(a.calculated_value for a in valued),
    )


@router.post(
    "/preview",
    response_model=ArtifactValuePreviewResponse,
    summary="Preview artifact value",
    description="Preview value calculation for an artifact type",
)
async def preview_artifact_value(
    request: ArtifactValuePreviewRequest,
) -> ArtifactValuePreviewResponse:
    """Preview artifact value calculation."""
    try:
        seniority = Seniority(request.seniority)
    except ValueError:
        seniority = Seniority.SENIOR

    squad_config = None
    if request.project_dir:
        squad_config = load_squad_config(project_dir=request.project_dir)

    preview = get_artifact_value_preview(
        artifact_type=request.artifact_type,
        squad_config=squad_config,
        seniority=seniority,
    )

    return ArtifactValuePreviewResponse(
        artifact_type=preview["artifact_type"],
        role=preview["role"],
        seniority=preview["seniority"],
        estimated_hours=preview["estimated_hours"],
        hourly_rate=preview["hourly_rate"],
        calculated_value=preview["calculated_value"],
        formula=preview["formula"],
    )


# ═══════════════════════════════════════════════════════════════
# Phase 5A: Artifact Search & Local Storage
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/search",
    response_model=ArtifactSearchResponse,
    summary="Search artifacts",
    description="Full-text search across artifacts",
)
async def search_artifacts(
    query: str = Query(..., min_length=1, description="Search query"),
    project_dir: str = Query(..., description="Project directory path"),
    artifact_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
) -> ArtifactSearchResponse:
    """Search artifacts by content."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)

    all_artifacts = consumer.get_all_artifacts(
        artifact_type=artifact_type,
        limit=1000,  # Get more for search
    )

    # Simple search implementation
    query_lower = query.lower()
    results = []

    for artifact in all_artifacts:
        content = artifact.get("content", "")
        description = artifact.get("description", "")

        # Check if query matches content or description
        content_lower = content.lower() if content else ""
        description_lower = description.lower() if description else ""

        if query_lower in content_lower or query_lower in description_lower:
            # Calculate match score based on position and frequency
            match_score = 1.0
            if query_lower in description_lower:
                match_score += 0.5

            results.append(ArtifactSearchResult(
                artifact_id=artifact.get("id", ""),
                artifact_type=artifact.get("type", ""),
                content_preview=content[:200] if content else "",
                description=description,
                created_at=datetime.fromisoformat(artifact.get("created_at", datetime.now().isoformat())),
                spec_id=artifact.get("spec_id"),
                value_usd=artifact.get("value_usd", 0.0),
                match_score=match_score,
            ))

    # Sort by match score and limit
    results.sort(key=lambda x: x.match_score, reverse=True)
    results = results[:limit]

    return ArtifactSearchResponse(
        results=results,
        total_count=len(results),
        query=query,
    )


@router.get(
    "/local",
    response_model=LocalArtifactsListResponse,
    summary="List local artifacts",
    description="List artifacts from local storage",
)
async def list_local_artifacts(
    project_dir: str = Query(..., description="Project directory path"),
    spec_id: Optional[str] = Query(None, description="Filter by spec ID"),
    artifact_type: Optional[str] = Query(None, description="Filter by type"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
) -> LocalArtifactsListResponse:
    """List artifacts from local storage."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)

    if spec_id:
        artifacts = consumer.get_artifacts_for_spec(spec_id)
    else:
        artifacts = consumer.get_all_artifacts(
            artifact_type=artifact_type,
            limit=limit,
        )

    return LocalArtifactsListResponse(
        artifacts=[
            LocalArtifactResponse(
                id=a.get("id", ""),
                type=a.get("type", ""),
                content=a.get("content", "")[:500],  # Truncate for listing
                description=a.get("description"),
                value_usd=a.get("value_usd", 0.0),
                created_at=a.get("created_at", ""),
                spec_id=a.get("spec_id"),
                trace_id=a.get("trace_id"),
                storage_path=a.get("storage_path", ""),
            )
            for a in artifacts[:limit]
        ],
        total_count=len(artifacts),
        total_value=sum(a.get("value_usd", 0.0) for a in artifacts),
    )


# ═══════════════════════════════════════════════════════════════
# Phase 5E: Artifact Analytics (statistics, timeline, by-role)
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/statistics",
    response_model=ArtifactStatisticsResponse,
    summary="Get artifact statistics",
    description="Get aggregate artifact statistics",
)
async def get_artifact_statistics(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> ArtifactStatisticsResponse:
    """Get aggregate artifact statistics."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)

    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)

    # Filter by date if provided
    if from_date or to_date:
        filtered = []
        for a in valued_artifacts:
            if a.created_at:
                if from_date and a.created_at < from_date:
                    continue
                if to_date and a.created_at > to_date:
                    continue
            filtered.append(a)
        valued_artifacts = filtered

    total_value = sum(a.calculated_value for a in valued_artifacts)
    total_count = len(valued_artifacts)
    avg_value = total_value / total_count if total_count > 0 else 0

    # Group by type
    by_type_count: dict[str, int] = {}
    by_type_value: dict[str, float] = {}
    for a in valued_artifacts:
        by_type_count[a.artifact_type] = by_type_count.get(a.artifact_type, 0) + 1
        by_type_value[a.artifact_type] = by_type_value.get(a.artifact_type, 0) + a.calculated_value

    # Group by role
    by_role_count: dict[str, int] = {}
    by_role_value: dict[str, float] = {}
    for a in valued_artifacts:
        role = a.role.value
        by_role_count[role] = by_role_count.get(role, 0) + 1
        by_role_value[role] = by_role_value.get(role, 0) + a.calculated_value

    # Find most valuable and common types
    most_valuable_type = max(by_type_value.items(), key=lambda x: x[1])[0] if by_type_value else None
    most_common_type = max(by_type_count.items(), key=lambda x: x[1])[0] if by_type_count else None

    return ArtifactStatisticsResponse(
        total_artifacts=total_count,
        total_value=total_value,
        avg_value_per_artifact=avg_value,
        by_type_count=by_type_count,
        by_type_value=by_type_value,
        by_role_count=by_role_count,
        by_role_value=by_role_value,
        most_valuable_type=most_valuable_type,
        most_common_type=most_common_type,
        period_start=from_date.strftime("%Y-%m-%d") if from_date else None,
        period_end=to_date.strftime("%Y-%m-%d") if to_date else None,
    )


@router.get(
    "/timeline",
    response_model=ArtifactTimelineResponse,
    summary="Get artifact timeline",
    description="Get artifacts created over time",
)
async def get_artifact_timeline(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> ArtifactTimelineResponse:
    """Get artifact timeline."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)

    from_dt = from_date or (datetime.now() - timedelta(days=30))
    to_dt = to_date or datetime.now()

    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)

    # Group by date
    by_date: dict[str, dict] = {}
    for a in valued_artifacts:
        if a.created_at:
            date_key = a.created_at.strftime("%Y-%m-%d")
            if date_key not in by_date:
                by_date[date_key] = {
                    "count": 0,
                    "value": 0.0,
                    "by_type": {},
                }
            by_date[date_key]["count"] += 1
            by_date[date_key]["value"] += a.calculated_value
            by_date[date_key]["by_type"][a.artifact_type] = by_date[date_key]["by_type"].get(a.artifact_type, 0) + 1

    # Build timeline for all dates in range
    timeline = []
    current_date = from_dt
    total_artifacts = 0
    total_value = 0.0

    while current_date <= to_dt:
        date_key = current_date.strftime("%Y-%m-%d")
        data = by_date.get(date_key, {"count": 0, "value": 0.0, "by_type": {}})

        timeline.append(ArtifactTimelinePoint(
            date=date_key,
            artifact_count=data["count"],
            total_value=data["value"],
            by_type=data["by_type"],
        ))

        total_artifacts += data["count"]
        total_value += data["value"]
        current_date += timedelta(days=1)

    return ArtifactTimelineResponse(
        timeline=timeline,
        period_start=from_dt.strftime("%Y-%m-%d"),
        period_end=to_dt.strftime("%Y-%m-%d"),
        total_artifacts=total_artifacts,
        total_value=total_value,
    )


@router.get(
    "/by-role",
    response_model=ArtifactsByRoleResponse,
    summary="Get artifacts by role",
    description="Get artifacts grouped by role",
)
async def get_artifacts_by_role(
    project_dir: str = Query(..., description="Project directory path"),
    limit_per_role: int = Query(5, ge=1, le=20, description="Max artifacts per role"),
) -> ArtifactsByRoleResponse:
    """Get artifacts grouped by role."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)

    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)

    # Group by role
    by_role_data: dict[str, dict] = {}
    for a in valued_artifacts:
        role = a.role.value
        if role not in by_role_data:
            by_role_data[role] = {
                "count": 0,
                "value": 0.0,
                "types": set(),
                "artifacts": [],
            }
        by_role_data[role]["count"] += 1
        by_role_data[role]["value"] += a.calculated_value
        by_role_data[role]["types"].add(a.artifact_type)
        by_role_data[role]["artifacts"].append({
            "artifact_id": a.artifact_id,
            "artifact_type": a.artifact_type,
            "value": a.calculated_value,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    # Build response
    by_role = []
    total_artifacts = 0
    total_value = 0.0

    for role, data in sorted(by_role_data.items(), key=lambda x: x[1]["value"], reverse=True):
        try:
            role_enum = Role(role)
            role_desc = ROLE_DESCRIPTIONS.get(role_enum, "")
        except ValueError:
            role_desc = ""

        # Sort artifacts by value and take top N
        top_artifacts = sorted(data["artifacts"], key=lambda x: x["value"], reverse=True)[:limit_per_role]

        by_role.append(ArtifactsByRoleItem(
            role=role,
            role_description=role_desc,
            artifact_count=data["count"],
            total_value=data["value"],
            avg_value_per_artifact=data["value"] / data["count"] if data["count"] > 0 else 0,
            artifact_types=list(data["types"]),
            top_artifacts=top_artifacts,
        ))

        total_artifacts += data["count"]
        total_value += data["value"]

    return ArtifactsByRoleResponse(
        by_role=by_role,
        total_artifacts=total_artifacts,
        total_value=total_value,
    )


# ═══════════════════════════════════════════════════════════════
# Phase 5H: Artifact Management Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/duplicates",
    response_model=DuplicatesResponse,
    summary="Find duplicate artifacts",
    description="Scan artifacts to find potential duplicates based on content similarity",
)
async def find_duplicate_artifacts(
    project_dir: str = Query(..., description="Project directory path"),
    similarity_threshold: float = Query(0.8, ge=0.5, le=1.0, description="Minimum similarity score to consider duplicate"),
    spec_id: Optional[str] = Query(None, description="Filter to specific spec"),
) -> DuplicatesResponse:
    """Find duplicate/similar artifacts."""
    project_path = Path(project_dir)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail=f"Project directory not found: {project_dir}")

    consumer = ArtifactConsumer(project_path)

    if spec_id:
        raw_artifacts = consumer.get_artifacts_for_spec(spec_id)
    else:
        raw_artifacts = consumer.get_all_artifacts()

    # Simple duplicate detection based on content similarity
    duplicates: list[DuplicateArtifactPair] = []
    potential_savings = 0.0
    artifacts_scanned = len(raw_artifacts)

    # Compare each pair of artifacts
    for i, art1 in enumerate(raw_artifacts):
        for art2 in raw_artifacts[i + 1:]:
            # Skip different types
            if art1.get("type") != art2.get("type"):
                continue

            content1 = art1.get("content", "")
            content2 = art2.get("content", "")

            # Simple similarity: check if one contains the other or they're very similar
            similarity = 0.0
            reason = ""

            # Exact match
            if content1 == content2:
                similarity = 1.0
                reason = "Exact content match"
            # One contains the other
            elif content1 in content2 or content2 in content1:
                longer = max(len(content1), len(content2))
                shorter = min(len(content1), len(content2))
                similarity = shorter / longer if longer > 0 else 0
                reason = "One artifact contains the other"
            # Check for significant overlap (first 200 chars match)
            elif len(content1) >= 200 and len(content2) >= 200:
                if content1[:200] == content2[:200]:
                    similarity = 0.85
                    reason = "Similar content beginning"

            if similarity >= similarity_threshold:
                value1 = art1.get("value_usd", 0.0)
                value2 = art2.get("value_usd", 0.0)

                duplicates.append(DuplicateArtifactPair(
                    artifact_1_id=art1.get("id", ""),
                    artifact_1_type=art1.get("type", "unknown"),
                    artifact_1_preview=content1[:100] + "..." if len(content1) > 100 else content1,
                    artifact_1_value=value1,
                    artifact_2_id=art2.get("id", ""),
                    artifact_2_type=art2.get("type", "unknown"),
                    artifact_2_preview=content2[:100] + "..." if len(content2) > 100 else content2,
                    artifact_2_value=value2,
                    similarity_score=similarity,
                    similarity_reason=reason,
                ))
                # Potential savings is the lesser value (could be merged)
                potential_savings += min(value1, value2)

    return DuplicatesResponse(
        duplicates=duplicates,
        total_pairs=len(duplicates),
        potential_savings=potential_savings,
        scan_timestamp=datetime.now(),
        artifacts_scanned=artifacts_scanned,
    )


@router.post(
    "/merge",
    response_model=MergeArtifactsResponse,
    summary="Merge duplicate artifacts",
    description="Merge multiple artifacts into one, keeping the specified artifact",
)
async def merge_artifacts(
    request: MergeArtifactsRequest,
    project_dir: str = Query(..., description="Project directory path"),
) -> MergeArtifactsResponse:
    """Merge duplicate artifacts."""
    project_path = Path(project_dir)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail=f"Project directory not found: {project_dir}")

    consumer = ArtifactConsumer(project_path)

    # Validate keep_artifact_id is in the list
    if request.keep_artifact_id not in request.artifact_ids:
        raise HTTPException(
            status_code=400,
            detail=f"keep_artifact_id '{request.keep_artifact_id}' must be in artifact_ids list"
        )

    # Get all artifacts
    keep_artifact = None
    artifacts_to_delete = []

    for artifact_id in request.artifact_ids:
        artifact = consumer.get_artifact_by_id(artifact_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

        if artifact_id == request.keep_artifact_id:
            keep_artifact = artifact
        else:
            artifacts_to_delete.append(artifact)

    if keep_artifact is None:
        raise HTTPException(status_code=404, detail=f"Keep artifact not found: {request.keep_artifact_id}")

    # Merge content if requested
    merged_content = keep_artifact.get("content", "")
    if request.merge_content:
        for art in artifacts_to_delete:
            art_content = art.get("content", "")
            if art_content and art_content not in merged_content:
                merged_content += f"\n\n--- Merged from {art.get('id', 'unknown')} ---\n\n{art_content}"

    # Delete the other artifacts
    deleted_ids = []
    for art in artifacts_to_delete:
        art_id = art.get("id", "")
        success = consumer.delete_artifact(art_id)
        if success:
            deleted_ids.append(art_id)

    # Update the kept artifact with merged content if needed
    if request.merge_content and merged_content != keep_artifact.get("content", ""):
        consumer.update_artifact(request.keep_artifact_id, {"content": merged_content})

    return MergeArtifactsResponse(
        success=True,
        merged_artifact_id=request.keep_artifact_id,
        merged_artifact_type=keep_artifact.get("type", "unknown"),
        merged_artifact_value=keep_artifact.get("value_usd", 0.0),
        deleted_artifact_ids=deleted_ids,
        deleted_count=len(deleted_ids),
        message=f"Successfully merged {len(deleted_ids)} artifacts into {request.keep_artifact_id}",
    )


# ═══════════════════════════════════════════════════════════════
# Single Artifact by ID (MUST be after all /path routes!)
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/{artifact_id}",
    response_model=ArtifactValueResponse,
    summary="Get a single valued artifact",
)
async def get_artifact(
    artifact_id: str,
    project_dir: str = Query(..., description="Project directory path"),
) -> ArtifactValueResponse:
    """Get a single artifact with valuation."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)

    raw_artifact = consumer.get_artifact(artifact_id)
    if not raw_artifact:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    valued = valuate_artifacts([raw_artifact], squad_config)[0]

    return ArtifactValueResponse(
        artifact_id=valued.artifact_id,
        artifact_type=valued.artifact_type,
        role=valued.role.value,
        seniority=valued.seniority.value,
        hourly_rate=valued.hourly_rate,
        estimated_hours=valued.estimated_hours,
        calculated_value=valued.calculated_value,
        original_value=valued.original_value,
        value_source=valued.value_source,
    )


@router.put(
    "/{artifact_id}/status",
    response_model=UpdateStatusResponse,
    summary="Update artifact status",
    description="Update artifact status to draft or complete",
)
async def update_artifact_status(
    artifact_id: str,
    request: UpdateStatusRequest,
    project_dir: str = Query(..., description="Project directory path"),
) -> UpdateStatusResponse:
    """Update artifact status (draft/complete)."""
    project_path = Path(project_dir)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail=f"Project directory not found: {project_dir}")

    consumer = ArtifactConsumer(project_path)
    artifact = consumer.get_artifact_by_id(artifact_id)

    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    old_status = artifact.get("status", "complete")
    new_status = request.status

    # Calculate value change
    value = artifact.get("value_usd", 0.0)
    value_change = 0.0

    # If changing from draft to complete, artifact now contributes to ROI
    if old_status == "draft" and new_status == "complete":
        value_change = value
    # If changing from complete to draft, artifact no longer contributes
    elif old_status == "complete" and new_status == "draft":
        value_change = -value

    # Update the artifact
    success = consumer.update_artifact(artifact_id, {"status": new_status})

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update artifact status")

    return UpdateStatusResponse(
        success=True,
        artifact_id=artifact_id,
        old_status=old_status,
        new_status=new_status,
        value_change=value_change,
        message=f"Status updated from '{old_status}' to '{new_status}'",
    )


@router.put(
    "/{artifact_id}/quality",
    response_model=UpdateQualityResponse,
    summary="Update artifact quality score",
    description="Set quality score for an artifact (0.0-1.0)",
)
async def update_artifact_quality(
    artifact_id: str,
    request: UpdateQualityRequest,
    project_dir: str = Query(..., description="Project directory path"),
) -> UpdateQualityResponse:
    """Update artifact quality score."""
    project_path = Path(project_dir)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail=f"Project directory not found: {project_dir}")

    consumer = ArtifactConsumer(project_path)
    artifact = consumer.get_artifact_by_id(artifact_id)

    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    old_quality = artifact.get("quality_score", 1.0)
    new_quality = request.quality_score
    base_value = artifact.get("value_usd", 0.0)

    # Calculate adjusted values using formula: value * (0.5 + quality * 0.5)
    old_adjusted = base_value * (0.5 + old_quality * 0.5)
    new_adjusted = base_value * (0.5 + new_quality * 0.5)
    value_change = new_adjusted - old_adjusted

    # Update the artifact
    success = consumer.update_artifact(artifact_id, {"quality_score": new_quality})

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update artifact quality")

    return UpdateQualityResponse(
        success=True,
        artifact_id=artifact_id,
        old_quality_score=old_quality,
        new_quality_score=new_quality,
        old_adjusted_value=old_adjusted,
        new_adjusted_value=new_adjusted,
        value_change=value_change,
        message=f"Quality score updated from {old_quality:.2f} to {new_quality:.2f}",
    )


@router.delete(
    "/{artifact_id}",
    response_model=DeleteArtifactResponse,
    summary="Delete an artifact",
    description="Permanently delete an artifact",
)
async def delete_artifact(
    artifact_id: str,
    project_dir: str = Query(..., description="Project directory path"),
) -> DeleteArtifactResponse:
    """Delete an artifact."""
    project_path = Path(project_dir)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail=f"Project directory not found: {project_dir}")

    consumer = ArtifactConsumer(project_path)
    artifact = consumer.get_artifact_by_id(artifact_id)

    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    artifact_type = artifact.get("type", "unknown")
    deleted_value = artifact.get("value_usd", 0.0)

    # Delete the artifact
    success = consumer.delete_artifact(artifact_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete artifact")

    return DeleteArtifactResponse(
        success=True,
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        deleted_value=deleted_value,
        message=f"Artifact '{artifact_id}' deleted successfully",
    )


# ═══════════════════════════════════════════════════════════════
# Phase 5I: Artifact Editor Panel Endpoints
# ═══════════════════════════════════════════════════════════════


@router.put(
    "/{artifact_id}/content",
    response_model=UpdateContentResponse,
    summary="Edit artifact content",
    description="Update the content of an artifact (replace or append)",
)
async def update_artifact_content(
    artifact_id: str,
    request: UpdateContentRequest,
    project_dir: str = Query(..., description="Project directory path"),
) -> UpdateContentResponse:
    """Edit artifact content."""
    project_path = Path(project_dir)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail=f"Project directory not found: {project_dir}")

    consumer = ArtifactConsumer(project_path)
    artifact = consumer.get_artifact_by_id(artifact_id)

    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    old_content = artifact.get("content", "")
    previous_length = len(old_content)

    # Determine new content
    if request.append:
        new_content = old_content + "\n\n" + request.content
    else:
        new_content = request.content

    # Update the artifact
    success = consumer.update_artifact(artifact_id, {"content": new_content})

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update artifact content")

    return UpdateContentResponse(
        success=True,
        artifact_id=artifact_id,
        content_length=len(new_content),
        previous_length=previous_length,
        message=f"Content {'appended' if request.append else 'replaced'} successfully",
    )


@router.post(
    "/{artifact_id}/continue",
    response_model=ContinueArtifactResponse,
    summary="Continue artifact via LLM",
    description="Use an LLM to continue/expand the artifact content",
)
async def continue_artifact(
    artifact_id: str,
    request: ContinueArtifactRequest,
    project_dir: str = Query(..., description="Project directory path"),
) -> ContinueArtifactResponse:
    """Continue artifact content using LLM."""
    project_path = Path(project_dir)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail=f"Project directory not found: {project_dir}")

    consumer = ArtifactConsumer(project_path)
    artifact = consumer.get_artifact_by_id(artifact_id)

    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    original_content = artifact.get("content", "")
    artifact_type = artifact.get("type", "unknown")

    # Try to use Anthropic API for continuation
    try:
        import anthropic
        import os

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="ANTHROPIC_API_KEY not configured. Cannot use LLM continuation."
            )

        client = anthropic.Anthropic(api_key=api_key)

        # Build the prompt
        system_prompt = f"""You are an expert assistant helping to continue and expand artifacts.
The artifact type is: {artifact_type}
Your task is to continue the existing content naturally and coherently.
Maintain the same style, tone, and formatting as the original content.
Only output the continuation - do not repeat the original content."""

        user_prompt = f"""{request.prompt}

Current artifact content:
---
{original_content}
---

Please continue this artifact:"""

        message = client.messages.create(
            model=request.model,
            max_tokens=request.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        added_content = message.content[0].text
        continued_content = original_content + "\n\n" + added_content
        tokens_used = message.usage.input_tokens + message.usage.output_tokens

        # Update the artifact with continued content
        consumer.update_artifact(artifact_id, {"content": continued_content})

        return ContinueArtifactResponse(
            success=True,
            artifact_id=artifact_id,
            original_content=original_content,
            continued_content=continued_content,
            added_content=added_content,
            tokens_used=tokens_used,
            message=f"Artifact continued successfully using {request.model}",
        )

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Anthropic library not installed. Cannot use LLM continuation."
        )
    except Exception as e:
        if "anthropic" in str(type(e).__module__):
            raise HTTPException(status_code=503, detail=f"Anthropic API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error continuing artifact: {str(e)}")


@router.post(
    "/{artifact_id}/complete",
    response_model=CompleteArtifactResponse,
    summary="Mark artifact as complete",
    description="Mark a draft artifact as complete, making it count towards ROI",
)
async def complete_artifact(
    artifact_id: str,
    project_dir: str = Query(..., description="Project directory path"),
    quality_score: float = Query(1.0, ge=0.0, le=1.0, description="Quality score to assign"),
) -> CompleteArtifactResponse:
    """Mark artifact as complete."""
    project_path = Path(project_dir)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail=f"Project directory not found: {project_dir}")

    consumer = ArtifactConsumer(project_path)
    artifact = consumer.get_artifact_by_id(artifact_id)

    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

    old_status = artifact.get("status", "draft")
    base_value = artifact.get("value_usd", 0.0)

    # Update status and quality
    updates = {
        "status": "complete",
        "quality_score": quality_score,
    }
    success = consumer.update_artifact(artifact_id, updates)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to complete artifact")

    # Calculate adjusted value: value * (0.5 + quality * 0.5)
    adjusted_value = base_value * (0.5 + quality_score * 0.5)

    return CompleteArtifactResponse(
        success=True,
        artifact_id=artifact_id,
        old_status=old_status,
        new_status="complete",
        quality_score=quality_score,
        calculated_value=base_value,
        adjusted_value=adjusted_value,
        message=f"Artifact marked as complete with quality score {quality_score:.2f}",
    )
