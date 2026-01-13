"""
Artifact Valuator

Transforms raw artifacts into valued artifacts using role-based calculation.

The core formula is simple:
  value = hourly_rate × estimated_hours

Where:
- hourly_rate comes from squad config (based on role + seniority)
- estimated_hours comes from ARTIFACT_ROLE_MAP (based on artifact type)

Example:
  Artifact type: "diagram"
  Role: ARCHITECT
  Seniority: SENIOR
  Hourly rate: $150/hr
  Estimated hours: 2.0
  Value: $300
"""

from datetime import datetime
from typing import Any

from .config import SquadConfigWrapper, load_squad_config
from .mappings import get_role_and_hours
from .models import ArtifactStatus, ArtifactValue, Role, Seniority


def calculate_artifact_value(
    artifact: dict[str, Any],
    squad_config: SquadConfigWrapper | None = None,
    seniority_override: Seniority | None = None,
) -> ArtifactValue:
    """
    Transform a raw artifact into a valued artifact.

    This is the core valuation function. It:
    1. Gets the role and time estimate from artifact type
    2. Gets the hourly rate from squad config
    3. Calculates: value = rate × time

    Args:
        artifact: Raw artifact dict from storage (must have 'type' key)
        squad_config: Squad configuration (or load default)
        seniority_override: Override the default seniority level

    Returns:
        ArtifactValue with calculated value
    """
    # Load config if not provided
    if squad_config is None:
        squad_config = load_squad_config()

    # Get artifact type
    artifact_type = artifact.get("type", "unknown").lower()

    # Get role and time estimate from mapping
    role, estimated_hours = get_role_and_hours(artifact_type)

    # Determine seniority
    seniority = seniority_override or squad_config.default_seniority

    # Get hourly rate from squad config
    hourly_rate = squad_config.get_hourly_rate(role, seniority)

    # Calculate value
    calculated_value = hourly_rate * estimated_hours

    # Parse created_at if string
    created_at = artifact.get("created_at")
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at)
        except ValueError:
            created_at = datetime.now()
    elif created_at is None:
        created_at = datetime.now()

    # Parse status (default to COMPLETE for backwards compatibility)
    raw_status = artifact.get("status", "complete").lower()
    if raw_status == "draft":
        status = ArtifactStatus.DRAFT
    else:
        status = ArtifactStatus.COMPLETE

    # Parse quality_score (default to 1.0 for backwards compatibility)
    quality_score = artifact.get("quality_score", 1.0)
    if not isinstance(quality_score, (int, float)):
        quality_score = 1.0
    quality_score = max(0.0, min(1.0, float(quality_score)))

    return ArtifactValue(
        artifact_id=artifact.get("id", artifact.get("artifact_id", "")),
        artifact_type=artifact_type,
        content=artifact.get("content", ""),
        trace_id=artifact.get("trace_id"),
        spec_id=artifact.get("spec_id"),
        agent_type=artifact.get("agent_type", ""),
        created_at=created_at,
        role=role,
        seniority=seniority,
        hourly_rate=hourly_rate,
        estimated_hours=estimated_hours,
        calculated_value=calculated_value,
        status=status,
        quality_score=quality_score,
        original_value=artifact.get("value_usd", artifact.get("value", 0.0)),
        value_source=squad_config.source,
        metadata=artifact.get("metadata", {}),
    )


def valuate_artifacts(
    artifacts: list[dict[str, Any]],
    squad_config: SquadConfigWrapper | None = None,
    seniority_override: Seniority | None = None,
) -> list[ArtifactValue]:
    """
    Valuate a list of raw artifacts.

    Args:
        artifacts: List of raw artifact dicts from storage
        squad_config: Squad configuration (loaded once for all)
        seniority_override: Override seniority for all artifacts

    Returns:
        List of ArtifactValue with calculated values
    """
    if squad_config is None:
        squad_config = load_squad_config()

    return [
        calculate_artifact_value(artifact, squad_config, seniority_override)
        for artifact in artifacts
    ]


def get_artifact_value_preview(
    artifact_type: str,
    squad_config: SquadConfigWrapper | None = None,
    seniority: Seniority = Seniority.SENIOR,
) -> dict[str, Any]:
    """
    Preview the value calculation for an artifact type.

    Useful for UI to show expected values before creation.

    Args:
        artifact_type: Type of artifact
        squad_config: Squad configuration
        seniority: Seniority level

    Returns:
        Dict with role, hours, rate, and calculated value
    """
    if squad_config is None:
        squad_config = load_squad_config()

    role, estimated_hours = get_role_and_hours(artifact_type)
    hourly_rate = squad_config.get_hourly_rate(role, seniority)
    calculated_value = hourly_rate * estimated_hours

    return {
        "artifact_type": artifact_type,
        "role": role.value,
        "seniority": seniority.value,
        "estimated_hours": estimated_hours,
        "hourly_rate": hourly_rate,
        "calculated_value": calculated_value,
        "formula": f"${hourly_rate}/hr × {estimated_hours}hr = ${calculated_value}",
    }


def compare_valuations(
    artifact: dict[str, Any],
    squad_config: SquadConfigWrapper | None = None,
) -> dict[str, Any]:
    """
    Compare original fixed value with role-based calculation.

    Useful for migration and validation.

    Args:
        artifact: Raw artifact dict with 'value_usd' field
        squad_config: Squad configuration

    Returns:
        Dict comparing original vs calculated value
    """
    valued = calculate_artifact_value(artifact, squad_config)

    original = valued.original_value
    calculated = valued.calculated_value
    difference = calculated - original
    percentage_change = (difference / original * 100) if original > 0 else 0

    return {
        "artifact_id": valued.artifact_id,
        "artifact_type": valued.artifact_type,
        "original_value": original,
        "calculated_value": calculated,
        "difference": difference,
        "percentage_change": percentage_change,
        "role": valued.role.value,
        "seniority": valued.seniority.value,
        "hourly_rate": valued.hourly_rate,
        "estimated_hours": valued.estimated_hours,
    }
