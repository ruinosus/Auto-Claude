"""
ROI Aggregator

Aggregates valued artifacts into ROI results.
This is where the simple formula comes to life:

ROI = (Total Artifact Value - Token Cost) / Token Cost × 100%

The aggregator takes valued artifacts and produces:
- Total value by role
- Total value by artifact type
- Net value (value - cost)
- ROI percentage
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from .config import SquadConfigWrapper, load_squad_config
from .consumer import ArtifactConsumer
from .models import ArtifactStatus, ArtifactValue, ROIResult, Role
from .valuator import valuate_artifacts


def calculate_roi(
    artifacts: list[ArtifactValue],
    token_cost: float,
    scope: str = "unknown",
    scope_id: str = "unknown",
    squad_config_id: str | None = None,
    include_drafts: bool = False,
    use_adjusted_value: bool = True,
) -> ROIResult:
    """
    Calculate ROI from valued artifacts.

    The simple, clear ROI calculation:
    ROI = (Value Generated - Cost) / Cost × 100%

    By default, only COMPLETE artifacts are included and quality-adjusted
    values are used. This ensures ROI reflects actual delivered value.

    Args:
        artifacts: List of valued artifacts
        token_cost: Total token cost in USD
        scope: Scope type ("trace", "spec", "project")
        scope_id: Identifier for the scope
        squad_config_id: ID of squad config used
        include_drafts: If True, include DRAFT artifacts in calculation
        use_adjusted_value: If True, use quality-adjusted value

    Returns:
        ROIResult with complete ROI breakdown
    """
    # Filter for complete artifacts only (unless include_drafts is True)
    if include_drafts:
        filtered_artifacts = artifacts
    else:
        filtered_artifacts = [a for a in artifacts if a.is_complete]

    # Helper to get value based on setting
    def get_value(artifact: ArtifactValue) -> float:
        return artifact.adjusted_value if use_adjusted_value else artifact.calculated_value

    # Calculate totals using adjusted_value (quality-weighted)
    total_value = sum(get_value(a) for a in filtered_artifacts)
    net_value = total_value - token_cost
    roi_percentage = (net_value / token_cost * 100) if token_cost > 0 else 0

    # Group by role
    by_role: dict[str, float] = {}
    for artifact in filtered_artifacts:
        role_name = artifact.role.value
        by_role[role_name] = by_role.get(role_name, 0) + get_value(artifact)

    # Group by type
    by_type: dict[str, float] = {}
    for artifact in filtered_artifacts:
        by_type[artifact.artifact_type] = (
            by_type.get(artifact.artifact_type, 0) + get_value(artifact)
        )

    return ROIResult(
        scope=scope,
        scope_id=scope_id,
        total_artifact_value=total_value,
        artifact_count=len(filtered_artifacts),
        by_role=by_role,
        by_type=by_type,
        token_cost=token_cost,
        net_value=net_value,
        roi_percentage=roi_percentage,
        artifacts=filtered_artifacts,
        calculated_at=datetime.now(),
        squad_config_id=squad_config_id,
    )


def calculate_roi_for_spec(
    spec_id: str,
    project_dir: Path | str,
    token_cost: float = 0.0,
    squad_config: SquadConfigWrapper | None = None,
) -> ROIResult:
    """
    Calculate ROI for all artifacts in a spec.

    This is the main entry point for spec-level ROI calculation.

    Args:
        spec_id: Spec identifier (e.g., "001-feature")
        project_dir: Project directory path
        token_cost: Token cost in USD (from Langfuse or other source)
        squad_config: Squad configuration (or load from project)

    Returns:
        ROIResult for the spec
    """
    if squad_config is None:
        squad_config = load_squad_config(project_dir=project_dir)

    # Get artifacts from storage
    consumer = ArtifactConsumer(project_dir)
    raw_artifacts = consumer.get_artifacts_for_spec(spec_id)

    # Valuate artifacts
    valued_artifacts = valuate_artifacts(raw_artifacts, squad_config)

    # Calculate ROI
    return calculate_roi(
        artifacts=valued_artifacts,
        token_cost=token_cost,
        scope="spec",
        scope_id=spec_id,
        squad_config_id=squad_config.id,
    )


def calculate_roi_for_trace(
    trace_id: str,
    project_dir: Path | str,
    token_cost: float = 0.0,
    squad_config: SquadConfigWrapper | None = None,
) -> ROIResult:
    """
    Calculate ROI for all artifacts in a trace.

    Args:
        trace_id: Langfuse trace ID
        project_dir: Project directory path
        token_cost: Token cost in USD
        squad_config: Squad configuration

    Returns:
        ROIResult for the trace
    """
    if squad_config is None:
        squad_config = load_squad_config(project_dir=project_dir)

    consumer = ArtifactConsumer(project_dir)
    raw_artifacts = consumer.get_artifacts_for_trace(trace_id)
    valued_artifacts = valuate_artifacts(raw_artifacts, squad_config)

    return calculate_roi(
        artifacts=valued_artifacts,
        token_cost=token_cost,
        scope="trace",
        scope_id=trace_id,
        squad_config_id=squad_config.id,
    )


def calculate_roi_for_project(
    project_dir: Path | str,
    token_cost: float = 0.0,
    squad_config: SquadConfigWrapper | None = None,
) -> ROIResult:
    """
    Calculate ROI for all artifacts in a project.

    Args:
        project_dir: Project directory path
        token_cost: Total token cost in USD for entire project
        squad_config: Squad configuration

    Returns:
        ROIResult for the project
    """
    project_path = Path(project_dir)
    if squad_config is None:
        squad_config = load_squad_config(project_dir=project_path)

    consumer = ArtifactConsumer(project_path)
    raw_artifacts = consumer.get_all_artifacts()
    valued_artifacts = valuate_artifacts(raw_artifacts, squad_config)

    return calculate_roi(
        artifacts=valued_artifacts,
        token_cost=token_cost,
        scope="project",
        scope_id=str(project_path),
        squad_config_id=squad_config.id,
    )


def aggregate_by_role(
    artifacts: list[ArtifactValue],
    include_drafts: bool = False,
    use_adjusted_value: bool = True,
) -> dict[str, dict[str, Any]]:
    """
    Aggregate artifact values by role with detailed breakdown.

    Args:
        artifacts: List of valued artifacts
        include_drafts: If True, include DRAFT artifacts
        use_adjusted_value: If True, use quality-adjusted value

    Returns:
        Dict with role as key and {value, count, avg_value, artifacts} as value
    """
    # Filter for complete artifacts only
    filtered = artifacts if include_drafts else [a for a in artifacts if a.is_complete]

    def get_value(artifact: ArtifactValue) -> float:
        return artifact.adjusted_value if use_adjusted_value else artifact.calculated_value

    by_role: dict[str, dict[str, Any]] = {}

    for artifact in filtered:
        role_name = artifact.role.value
        if role_name not in by_role:
            by_role[role_name] = {
                "total_value": 0.0,
                "count": 0,
                "total_hours": 0.0,
                "artifact_types": {},
                "avg_quality": 0.0,
                "quality_sum": 0.0,
            }

        by_role[role_name]["total_value"] += get_value(artifact)
        by_role[role_name]["count"] += 1
        by_role[role_name]["total_hours"] += artifact.estimated_hours
        by_role[role_name]["quality_sum"] += artifact.quality_score

        # Track artifact types within role
        artifact_types = by_role[role_name]["artifact_types"]
        if artifact.artifact_type not in artifact_types:
            artifact_types[artifact.artifact_type] = 0
        artifact_types[artifact.artifact_type] += 1

    # Calculate averages
    for role_data in by_role.values():
        if role_data["count"] > 0:
            role_data["avg_value"] = role_data["total_value"] / role_data["count"]
            role_data["avg_hours"] = role_data["total_hours"] / role_data["count"]
            role_data["avg_quality"] = role_data["quality_sum"] / role_data["count"]
        del role_data["quality_sum"]  # Remove temp field

    return by_role


def aggregate_by_type(
    artifacts: list[ArtifactValue],
    include_drafts: bool = False,
    use_adjusted_value: bool = True,
) -> dict[str, dict[str, Any]]:
    """
    Aggregate artifact values by type with detailed breakdown.

    Args:
        artifacts: List of valued artifacts
        include_drafts: If True, include DRAFT artifacts
        use_adjusted_value: If True, use quality-adjusted value

    Returns:
        Dict with type as key and {value, count, role, avg_hours} as value
    """
    # Filter for complete artifacts only
    filtered = artifacts if include_drafts else [a for a in artifacts if a.is_complete]

    def get_value(artifact: ArtifactValue) -> float:
        return artifact.adjusted_value if use_adjusted_value else artifact.calculated_value

    by_type: dict[str, dict[str, Any]] = {}

    for artifact in filtered:
        if artifact.artifact_type not in by_type:
            by_type[artifact.artifact_type] = {
                "total_value": 0.0,
                "count": 0,
                "role": artifact.role.value,
                "estimated_hours": artifact.estimated_hours,
                "avg_quality": 0.0,
                "quality_sum": 0.0,
            }

        by_type[artifact.artifact_type]["total_value"] += get_value(artifact)
        by_type[artifact.artifact_type]["count"] += 1
        by_type[artifact.artifact_type]["quality_sum"] += artifact.quality_score

    # Calculate averages
    for type_data in by_type.values():
        if type_data["count"] > 0:
            type_data["avg_value"] = type_data["total_value"] / type_data["count"]
            type_data["avg_quality"] = type_data["quality_sum"] / type_data["count"]
        del type_data["quality_sum"]  # Remove temp field

    return by_type
