#!/usr/bin/env python3
"""
Artifact Migration Script

Migrates existing artifacts to the new ROI Engine format:
1. Re-valuates artifacts using role-based calculation
2. Adds status field (defaults to 'complete')
3. Adds quality_score field (defaults to 1.0)
4. Updates both storage files and index

Usage:
    python migrate_artifacts.py /path/to/project
    python migrate_artifacts.py /path/to/project --dry-run
    python migrate_artifacts.py /path/to/project --backup
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add paths for imports
_roi_engine_path = Path(__file__).parent.parent
_backend_path = _roi_engine_path.parent / "backend"
sys.path.insert(0, str(_roi_engine_path))
sys.path.insert(0, str(_backend_path))

from core import (
    load_squad_config,
    get_role_and_hours,
    Role,
    Seniority,
)


class MigrationReport:
    """Tracks migration statistics."""

    def __init__(self):
        self.total_artifacts = 0
        self.migrated_artifacts = 0
        self.skipped_artifacts = 0
        self.errors: list[str] = []
        self.value_changes: list[dict[str, Any]] = []
        self.start_time = datetime.now()
        self.end_time: datetime | None = None

    def add_migration(self, artifact_id: str, old_value: float, new_value: float):
        """Record a successful migration."""
        self.migrated_artifacts += 1
        self.value_changes.append({
            "artifact_id": artifact_id,
            "old_value": old_value,
            "new_value": new_value,
            "change": new_value - old_value,
            "change_pct": ((new_value - old_value) / old_value * 100) if old_value > 0 else 0,
        })

    def add_skip(self, artifact_id: str, reason: str):
        """Record a skipped artifact."""
        self.skipped_artifacts += 1
        self.errors.append(f"Skipped {artifact_id}: {reason}")

    def add_error(self, artifact_id: str, error: str):
        """Record an error."""
        self.errors.append(f"Error {artifact_id}: {error}")

    def finalize(self):
        """Mark migration as complete."""
        self.end_time = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0

        total_old_value = sum(v["old_value"] for v in self.value_changes)
        total_new_value = sum(v["new_value"] for v in self.value_changes)

        return {
            "summary": {
                "total_artifacts": self.total_artifacts,
                "migrated": self.migrated_artifacts,
                "skipped": self.skipped_artifacts,
                "errors": len([e for e in self.errors if e.startswith("Error")]),
                "duration_seconds": duration,
            },
            "value_summary": {
                "total_old_value": total_old_value,
                "total_new_value": total_new_value,
                "total_change": total_new_value - total_old_value,
                "avg_change_pct": (
                    sum(v["change_pct"] for v in self.value_changes) / len(self.value_changes)
                    if self.value_changes else 0
                ),
            },
            "value_changes": self.value_changes,
            "errors": self.errors,
            "timestamps": {
                "start": self.start_time.isoformat(),
                "end": self.end_time.isoformat() if self.end_time else None,
            },
        }

    def print_summary(self):
        """Print migration summary to console."""
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Total artifacts found: {self.total_artifacts}")
        print(f"Successfully migrated: {self.migrated_artifacts}")
        print(f"Skipped: {self.skipped_artifacts}")
        print(f"Errors: {len([e for e in self.errors if e.startswith('Error')])}")

        if self.value_changes:
            total_old = sum(v["old_value"] for v in self.value_changes)
            total_new = sum(v["new_value"] for v in self.value_changes)
            print(f"\nValue Changes:")
            print(f"  Old total value: ${total_old:,.2f}")
            print(f"  New total value: ${total_new:,.2f}")
            print(f"  Net change: ${total_new - total_old:,.2f}")

        if self.errors:
            print(f"\nIssues ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")

        print("=" * 60)


def backup_artifacts(project_dir: Path) -> Path:
    """Create a backup of the artifacts directory."""
    artifacts_dir = project_dir / ".auto-claude" / "artifacts"
    if not artifacts_dir.exists():
        raise FileNotFoundError(f"Artifacts directory not found: {artifacts_dir}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = project_dir / ".auto-claude" / f"artifacts_backup_{timestamp}"

    print(f"Creating backup at: {backup_dir}")
    shutil.copytree(artifacts_dir, backup_dir)
    print(f"Backup complete: {sum(1 for _ in backup_dir.rglob('*.json'))} files")

    return backup_dir


def calculate_new_value(
    artifact_type: str,
    squad_config,
    seniority: Seniority = Seniority.SENIOR,
) -> tuple[Role, float, float, float]:
    """
    Calculate new value for an artifact using role-based system.

    Returns:
        Tuple of (role, hourly_rate, estimated_hours, calculated_value)
    """
    role, estimated_hours = get_role_and_hours(artifact_type)
    hourly_rate = squad_config.get_hourly_rate(role, seniority)
    calculated_value = hourly_rate * estimated_hours

    return role, hourly_rate, estimated_hours, calculated_value


def migrate_artifact(
    artifact: dict[str, Any],
    squad_config,
    seniority: Seniority = Seniority.SENIOR,
) -> dict[str, Any]:
    """
    Migrate a single artifact to the new format.

    Adds/updates:
    - role: Based on artifact type mapping
    - seniority: From parameter or default
    - hourly_rate: From squad config
    - estimated_hours: From artifact type mapping
    - calculated_value: hourly_rate * estimated_hours
    - status: 'complete' (default for existing artifacts)
    - quality_score: 1.0 (default for existing artifacts)
    """
    artifact_type = artifact.get("type", "unknown").lower()

    # Calculate new role-based value
    role, hourly_rate, estimated_hours, calculated_value = calculate_new_value(
        artifact_type, squad_config, seniority
    )

    # Preserve original value for comparison
    original_value = artifact.get("value_usd", artifact.get("value", 0.0))

    # Update artifact with new fields
    artifact.update({
        # Role-based valuation
        "role": role.value,
        "seniority": seniority.value,
        "hourly_rate": hourly_rate,
        "estimated_hours": estimated_hours,
        "calculated_value": calculated_value,
        "original_value": original_value,
        "value_source": "roi_engine_migration",

        # New Phase 5G fields
        "status": artifact.get("status", "complete"),
        "quality_score": artifact.get("quality_score", 1.0),

        # Migration metadata
        "migrated_at": datetime.now().isoformat(),
        "migration_version": "1.0.0",
    })

    # Update value_usd to new calculated value
    artifact["value_usd"] = calculated_value

    return artifact


def migrate_artifacts(
    project_dir: Path,
    dry_run: bool = False,
    create_backup: bool = True,
) -> MigrationReport:
    """
    Migrate all artifacts in a project to the new ROI Engine format.

    Args:
        project_dir: Project root directory
        dry_run: If True, don't write changes
        create_backup: If True, backup before migration

    Returns:
        MigrationReport with statistics
    """
    report = MigrationReport()

    artifacts_dir = project_dir / ".auto-claude" / "artifacts"
    index_file = artifacts_dir / "index.json"

    if not artifacts_dir.exists():
        print(f"No artifacts directory found at: {artifacts_dir}")
        report.finalize()
        return report

    # Create backup if requested
    if create_backup and not dry_run:
        try:
            backup_artifacts(project_dir)
        except Exception as e:
            print(f"Warning: Backup failed: {e}")

    # Load squad config
    try:
        squad_config = load_squad_config(project_dir=project_dir)
        print(f"Loaded squad config: {squad_config.id}")
    except Exception as e:
        print(f"Warning: Could not load squad config, using defaults: {e}")
        squad_config = load_squad_config()

    # Load index
    index = {"artifacts": {}, "by_spec": {}, "by_trace": {}, "by_date": {}}
    if index_file.exists():
        try:
            index = json.loads(index_file.read_text())
        except json.JSONDecodeError:
            print("Warning: Could not parse index.json, will rebuild")

    # Find all artifact files
    artifact_files = list(artifacts_dir.rglob("art_*.json"))
    report.total_artifacts = len(artifact_files)

    print(f"\nFound {report.total_artifacts} artifacts to migrate")
    print(f"Dry run: {dry_run}")
    print("-" * 40)

    # Migrate each artifact
    for artifact_file in artifact_files:
        artifact_id = artifact_file.stem

        try:
            # Load artifact
            artifact = json.loads(artifact_file.read_text())
            old_value = artifact.get("value_usd", artifact.get("value", 0.0))

            # Skip if already migrated
            if artifact.get("migration_version"):
                report.add_skip(artifact_id, "Already migrated")
                continue

            # Migrate
            migrated = migrate_artifact(artifact, squad_config)
            new_value = migrated["calculated_value"]

            # Write changes
            if not dry_run:
                artifact_file.write_text(json.dumps(migrated, indent=2, default=str))

                # Update index
                if artifact_id in index.get("artifacts", {}):
                    index["artifacts"][artifact_id].update({
                        "value_usd": new_value,
                        "role": migrated["role"],
                        "status": migrated["status"],
                        "quality_score": migrated["quality_score"],
                    })

            report.add_migration(artifact_id, old_value, new_value)

            # Progress indicator
            if report.migrated_artifacts % 10 == 0:
                print(f"  Migrated {report.migrated_artifacts} artifacts...")

        except Exception as e:
            report.add_error(artifact_id, str(e))

    # Save updated index
    if not dry_run and index:
        try:
            index_file.write_text(json.dumps(index, indent=2, default=str))
            print(f"Updated index.json")
        except Exception as e:
            report.add_error("index.json", f"Failed to save: {e}")

    report.finalize()
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Migrate artifacts to ROI Engine format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview migration (no changes)
    python migrate_artifacts.py /path/to/project --dry-run

    # Run migration with backup
    python migrate_artifacts.py /path/to/project --backup

    # Run migration and save report
    python migrate_artifacts.py /path/to/project --output report.json
        """,
    )

    parser.add_argument(
        "project_dir",
        type=Path,
        help="Project directory containing .auto-claude/artifacts/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup before migration",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Save migration report to JSON file",
    )

    args = parser.parse_args()

    if not args.project_dir.exists():
        print(f"Error: Project directory not found: {args.project_dir}")
        sys.exit(1)

    print(f"Migrating artifacts in: {args.project_dir}")

    # Run migration
    report = migrate_artifacts(
        project_dir=args.project_dir,
        dry_run=args.dry_run,
        create_backup=args.backup,
    )

    # Print summary
    report.print_summary()

    # Save report if requested
    if args.output:
        args.output.write_text(json.dumps(report.to_dict(), indent=2))
        print(f"\nReport saved to: {args.output}")

    # Exit with error code if there were errors
    if report.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
