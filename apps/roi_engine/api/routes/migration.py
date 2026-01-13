"""
Migration Routes.

Migration Endpoints:
- POST /migrate - Migrate artifacts to ROI Engine format
  Re-valuate all artifacts using role-based calculation and add new fields.
  Supports dry-run mode for previewing changes without writing.
  Creates backup before migration by default.
"""

import json as json_lib
import shutil
from datetime import datetime as dt
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from core import (
    get_role_and_hours,
    load_squad_config,
    Seniority,
)
from api.models import (
    MigrationResponse,
    MigrationSummary,
    MigrationValueChange,
    MigrationValueSummary,
)


router = APIRouter(prefix="/migrate", tags=["Migration"])


@router.post(
    "",
    response_model=MigrationResponse,
    summary="Migrate artifacts to ROI Engine format",
    description="Re-valuate all artifacts using role-based calculation and add new fields",
)
async def migrate_artifacts_endpoint(
    project_dir: str = Query(..., description="Project directory path"),
    dry_run: bool = Query(False, description="Preview changes without writing"),
    create_backup: bool = Query(True, description="Create backup before migration"),
) -> MigrationResponse:
    """Migrate artifacts to ROI Engine format."""
    project_path = Path(project_dir)
    if not project_path.exists():
        raise HTTPException(status_code=400, detail=f"Project directory not found: {project_dir}")

    artifacts_dir = project_path / ".auto-claude" / "artifacts"
    index_file = artifacts_dir / "index.json"

    if not artifacts_dir.exists():
        return MigrationResponse(
            success=True,
            summary=MigrationSummary(),
            value_summary=MigrationValueSummary(),
            message="No artifacts directory found - nothing to migrate",
        )

    start_time = dt.now()
    value_changes: list[MigrationValueChange] = []
    errors: list[str] = []
    migrated = 0
    skipped = 0

    # Create backup if requested
    if create_backup and not dry_run:
        try:
            timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = project_path / ".auto-claude" / f"artifacts_backup_{timestamp}"
            shutil.copytree(artifacts_dir, backup_dir)
        except Exception as e:
            errors.append(f"Backup failed: {str(e)}")

    # Load squad config
    try:
        squad_config = load_squad_config(project_dir=project_path)
    except Exception:
        squad_config = load_squad_config()

    # Load index
    index = {"artifacts": {}, "by_spec": {}, "by_trace": {}, "by_date": {}}
    if index_file.exists():
        try:
            index = json_lib.loads(index_file.read_text())
        except json_lib.JSONDecodeError:
            pass

    # Find all artifact files
    artifact_files = list(artifacts_dir.rglob("art_*.json"))
    total_artifacts = len(artifact_files)

    # Migrate each artifact
    for artifact_file in artifact_files:
        artifact_id = artifact_file.stem

        try:
            artifact = json_lib.loads(artifact_file.read_text())
            old_value = artifact.get("value_usd", artifact.get("value", 0.0))

            # Skip if already migrated
            if artifact.get("migration_version"):
                skipped += 1
                continue

            # Get artifact type and calculate new value
            artifact_type = artifact.get("type", "unknown").lower()
            role, estimated_hours = get_role_and_hours(artifact_type)
            seniority = Seniority.SENIOR
            hourly_rate = squad_config.get_hourly_rate(role, seniority)
            calculated_value = hourly_rate * estimated_hours

            # Update artifact
            artifact.update({
                "role": role.value,
                "seniority": seniority.value,
                "hourly_rate": hourly_rate,
                "estimated_hours": estimated_hours,
                "calculated_value": calculated_value,
                "original_value": old_value,
                "value_source": "roi_engine_migration",
                "status": artifact.get("status", "complete"),
                "quality_score": artifact.get("quality_score", 1.0),
                "migrated_at": dt.now().isoformat(),
                "migration_version": "1.0.0",
                "value_usd": calculated_value,
            })

            # Write changes
            if not dry_run:
                artifact_file.write_text(json_lib.dumps(artifact, indent=2, default=str))

                # Update index
                if artifact_id in index.get("artifacts", {}):
                    index["artifacts"][artifact_id].update({
                        "value_usd": calculated_value,
                        "role": artifact["role"],
                        "status": artifact["status"],
                        "quality_score": artifact["quality_score"],
                    })

            # Track change
            change = calculated_value - old_value
            change_pct = (change / old_value * 100) if old_value > 0 else 0

            value_changes.append(MigrationValueChange(
                artifact_id=artifact_id,
                old_value=old_value,
                new_value=calculated_value,
                change=change,
                change_pct=change_pct,
            ))

            migrated += 1

        except Exception as e:
            errors.append(f"Error {artifact_id}: {str(e)}")

    # Save updated index
    if not dry_run and index:
        try:
            index_file.write_text(json_lib.dumps(index, indent=2, default=str))
        except Exception as e:
            errors.append(f"Failed to save index: {str(e)}")

    end_time = dt.now()
    duration = (end_time - start_time).total_seconds()

    # Calculate summaries
    total_old = sum(v.old_value for v in value_changes)
    total_new = sum(v.new_value for v in value_changes)
    avg_change_pct = (
        sum(v.change_pct for v in value_changes) / len(value_changes)
        if value_changes else 0
    )

    return MigrationResponse(
        success=len(errors) == 0,
        summary=MigrationSummary(
            total_artifacts=total_artifacts,
            migrated=migrated,
            skipped=skipped,
            errors=len(errors),
            duration_seconds=duration,
        ),
        value_summary=MigrationValueSummary(
            total_old_value=total_old,
            total_new_value=total_new,
            total_change=total_new - total_old,
            avg_change_pct=avg_change_pct,
        ),
        value_changes=value_changes,
        errors=errors,
        message=f"Migration {'preview' if dry_run else 'complete'}: {migrated} artifacts migrated, {skipped} skipped",
    )
