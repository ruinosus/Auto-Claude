"""
Artifact Local Storage Module
=============================

Stores full artifact content locally to avoid truncation.
Langfuse receives only lightweight references with truncated previews.

Storage Structure:
    .auto-claude/
    └── artifacts/
        ├── index.json              # Quick lookup index
        └── {YYYY-MM-DD}/           # Organized by date
            ├── art_abc123.json     # Full artifact content
            └── art_def456.json

Usage:
    from analytics.artifact_storage import save_artifact, create_langfuse_reference

    # Save full artifact locally
    artifact_id = save_artifact(
        artifact={"type": "qa_finding", "content": full_content, ...},
        project_dir=project_dir,
        spec_id="001-add-auth",
        trace_id="langfuse_trace_xyz",
        agent_type="qa_reviewer",
    )

    # Create reference for Langfuse (truncated preview)
    ref = create_langfuse_reference(artifact, artifact_id, storage_path)
"""

import json
import logging
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Thread lock for index updates
_INDEX_LOCK = threading.Lock()

# Constants
ARTIFACTS_DIR = "artifacts"
INDEX_FILE = "index.json"
PREVIEW_LENGTH = 200  # Characters for Langfuse preview
ARTIFACT_ID_PREFIX = "art_"


class ArtifactStorageError(Exception):
    """Base exception for artifact storage operations."""
    pass


class ArtifactNotFoundError(ArtifactStorageError):
    """Raised when an artifact cannot be found."""
    pass


class ArtifactCorruptedError(ArtifactStorageError):
    """Raised when an artifact file is corrupted."""
    pass


def _get_artifacts_dir(project_dir: Path) -> Path:
    """Get the artifacts directory for a project."""
    return project_dir / ".auto-claude" / ARTIFACTS_DIR


def _get_date_dir(artifacts_dir: Path, date: str | None = None) -> Path:
    """Get the date-based subdirectory for artifacts."""
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return artifacts_dir / date


def _get_index_path(project_dir: Path) -> Path:
    """Get the path to the artifact index file."""
    return _get_artifacts_dir(project_dir) / INDEX_FILE


def _generate_artifact_id() -> str:
    """Generate a unique artifact ID."""
    return f"{ARTIFACT_ID_PREFIX}{uuid.uuid4().hex[:16]}"


def _atomic_write_json(filepath: Path, data: dict) -> None:
    """
    Write JSON file atomically using temp file + rename pattern.

    This ensures that if the write is interrupted, the original file
    is not corrupted.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory (required for atomic rename)
    fd, temp_path = tempfile.mkstemp(
        dir=str(filepath.parent),
        suffix=".tmp",
        prefix=".artifact_"
    )
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        # Atomic rename (works on same filesystem)
        os.replace(temp_path, filepath)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise


def _load_json_safe(filepath: Path) -> dict | None:
    """Load JSON file with error handling."""
    if not filepath.exists():
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load JSON from {filepath}: {e}")
        return None


def _load_index(project_dir: Path) -> dict:
    """Load the artifact index, creating empty one if needed."""
    index_path = _get_index_path(project_dir)
    index = _load_json_safe(index_path)

    if index is None:
        index = {
            "version": 1,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "artifacts": {},
            "by_spec": {},
            "by_date": {},
            "by_trace": {},
        }

    return index


def _save_index(project_dir: Path, index: dict) -> None:
    """Save the artifact index atomically."""
    index["last_updated"] = datetime.now(timezone.utc).isoformat()
    index_path = _get_index_path(project_dir)
    _atomic_write_json(index_path, index)


def _update_index(
    project_dir: Path,
    artifact_id: str,
    artifact_type: str,
    value_usd: float,
    date: str,
    spec_id: str | None,
    trace_id: str | None,
    storage_path: str,
) -> None:
    """Update the artifact index with new artifact metadata."""
    with _INDEX_LOCK:
        index = _load_index(project_dir)

        # Add to main artifacts dict
        index["artifacts"][artifact_id] = {
            "type": artifact_type,
            "value_usd": value_usd,
            "date": date,
            "spec_id": spec_id,
            "trace_id": trace_id,
            "storage_path": storage_path,
        }

        # Update by_date index
        if date not in index["by_date"]:
            index["by_date"][date] = []
        if artifact_id not in index["by_date"][date]:
            index["by_date"][date].append(artifact_id)

        # Update by_spec index
        if spec_id:
            if spec_id not in index["by_spec"]:
                index["by_spec"][spec_id] = []
            if artifact_id not in index["by_spec"][spec_id]:
                index["by_spec"][spec_id].append(artifact_id)

        # Update by_trace index
        if trace_id:
            if trace_id not in index["by_trace"]:
                index["by_trace"][trace_id] = []
            if artifact_id not in index["by_trace"][trace_id]:
                index["by_trace"][trace_id].append(artifact_id)

        _save_index(project_dir, index)


def save_artifact(
    artifact: dict[str, Any],
    project_dir: Path,
    spec_id: str | None = None,
    trace_id: str | None = None,
    agent_type: str | None = None,
    session_num: int | None = None,
) -> str:
    """
    Save an artifact with full content to local storage.

    Args:
        artifact: Artifact dict with type, content, value_usd, etc.
        project_dir: Project root directory
        spec_id: Optional spec ID (e.g., "001-add-auth")
        trace_id: Optional Langfuse trace ID
        agent_type: Agent that created the artifact (e.g., "qa_reviewer")
        session_num: Session number within the agent run

    Returns:
        Generated artifact ID

    Raises:
        ArtifactStorageError: If storage fails
    """
    try:
        # Generate ID and timestamp
        artifact_id = _generate_artifact_id()
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")

        # Build full artifact record
        full_artifact = {
            "id": artifact_id,
            "type": artifact.get("type", "unknown"),
            "format": artifact.get("format", "text"),
            "content": artifact.get("content", ""),  # FULL CONTENT - no truncation!
            "value_usd": artifact.get("value_usd", 0),
            "description": artifact.get("description", ""),
            "created_at": now.isoformat(),
            "trace_id": trace_id,
            "spec_id": spec_id,
            "project_id": project_dir.name if project_dir else None,
            "agent_type": agent_type,
            "session_num": session_num,
            "tab": artifact.get("tab"),
            "metadata": artifact.get("metadata", {}),
        }

        # Determine storage path
        artifacts_dir = _get_artifacts_dir(project_dir)
        date_dir = _get_date_dir(artifacts_dir, date_str)
        artifact_path = date_dir / f"{artifact_id}.json"

        # Save artifact file atomically
        _atomic_write_json(artifact_path, full_artifact)

        # Update index
        storage_path = str(artifact_path.relative_to(project_dir))
        _update_index(
            project_dir=project_dir,
            artifact_id=artifact_id,
            artifact_type=full_artifact["type"],
            value_usd=full_artifact["value_usd"],
            date=date_str,
            spec_id=spec_id,
            trace_id=trace_id,
            storage_path=storage_path,
        )

        logger.debug(f"Saved artifact {artifact_id} to {artifact_path}")
        return artifact_id

    except Exception as e:
        logger.error(f"Failed to save artifact: {e}")
        raise ArtifactStorageError(f"Failed to save artifact: {e}") from e


def save_artifact_safe(
    artifact: dict[str, Any],
    project_dir: Path,
    spec_id: str | None = None,
    trace_id: str | None = None,
    agent_type: str | None = None,
    session_num: int | None = None,
) -> str | None:
    """
    Save artifact without raising exceptions.

    Returns artifact_id on success, None on failure.
    Use this in contexts where storage failure should not break the main flow.
    """
    try:
        return save_artifact(
            artifact=artifact,
            project_dir=project_dir,
            spec_id=spec_id,
            trace_id=trace_id,
            agent_type=agent_type,
            session_num=session_num,
        )
    except Exception as e:
        logger.warning(f"Failed to save artifact (non-fatal): {e}")
        return None


def load_artifact(artifact_id: str, project_dir: Path) -> dict | None:
    """
    Load an artifact by ID from local storage.

    Args:
        artifact_id: The artifact ID (e.g., "art_abc123def456")
        project_dir: Project root directory

    Returns:
        Full artifact dict or None if not found
    """
    # First check index for storage path
    index = _load_index(project_dir)
    artifact_meta = index.get("artifacts", {}).get(artifact_id)

    if artifact_meta and "storage_path" in artifact_meta:
        artifact_path = project_dir / artifact_meta["storage_path"]
        artifact = _load_json_safe(artifact_path)
        if artifact:
            return artifact

    # Fallback: scan date directories
    artifacts_dir = _get_artifacts_dir(project_dir)
    if not artifacts_dir.exists():
        return None

    for date_dir in artifacts_dir.iterdir():
        if not date_dir.is_dir() or date_dir.name == INDEX_FILE:
            continue
        artifact_path = date_dir / f"{artifact_id}.json"
        if artifact_path.exists():
            return _load_json_safe(artifact_path)

    return None


def list_artifacts(
    project_dir: Path,
    spec_id: str | None = None,
    trace_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    artifact_types: list[str] | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    List artifacts with optional filters.

    Args:
        project_dir: Project root directory
        spec_id: Filter by spec ID
        trace_id: Filter by Langfuse trace ID
        date_from: Filter by start date (YYYY-MM-DD)
        date_to: Filter by end date (YYYY-MM-DD)
        artifact_types: Filter by artifact types
        limit: Maximum number of artifacts to return

    Returns:
        List of artifact dicts
    """
    index = _load_index(project_dir)

    # Determine which artifact IDs to load
    artifact_ids = set()

    if trace_id:
        artifact_ids = set(index.get("by_trace", {}).get(trace_id, []))
    elif spec_id:
        artifact_ids = set(index.get("by_spec", {}).get(spec_id, []))
    else:
        # All artifacts
        artifact_ids = set(index.get("artifacts", {}).keys())

    # Apply date filter
    if date_from or date_to:
        filtered_ids = set()
        for art_id in artifact_ids:
            art_meta = index.get("artifacts", {}).get(art_id, {})
            art_date = art_meta.get("date", "")
            if date_from and art_date < date_from:
                continue
            if date_to and art_date > date_to:
                continue
            filtered_ids.add(art_id)
        artifact_ids = filtered_ids

    # Apply type filter
    if artifact_types:
        filtered_ids = set()
        for art_id in artifact_ids:
            art_meta = index.get("artifacts", {}).get(art_id, {})
            if art_meta.get("type") in artifact_types:
                filtered_ids.add(art_id)
        artifact_ids = filtered_ids

    # Load artifacts (up to limit)
    artifacts = []
    for art_id in list(artifact_ids)[:limit]:
        artifact = load_artifact(art_id, project_dir)
        if artifact:
            artifacts.append(artifact)

    # Sort by created_at descending
    artifacts.sort(key=lambda a: a.get("created_at", ""), reverse=True)

    return artifacts


def get_artifacts_by_trace(project_dir: Path, trace_id: str) -> list[dict]:
    """Get all artifacts for a specific Langfuse trace."""
    return list_artifacts(project_dir, trace_id=trace_id, limit=1000)


def get_artifacts_by_spec(project_dir: Path, spec_id: str) -> list[dict]:
    """Get all artifacts for a specific spec."""
    return list_artifacts(project_dir, spec_id=spec_id, limit=1000)


def update_artifact(
    artifact_id: str,
    project_dir: Path,
    updates: dict[str, Any],
) -> dict | None:
    """
    Update an existing artifact.

    Args:
        artifact_id: The artifact ID to update
        project_dir: Project root directory
        updates: Dict of fields to update (content, description, value_usd, etc.)

    Returns:
        Updated artifact dict or None if not found
    """
    # Load existing artifact
    artifact = load_artifact(artifact_id, project_dir)
    if not artifact:
        logger.warning(f"Artifact {artifact_id} not found for update")
        return None

    # Apply updates (only allowed fields)
    allowed_updates = {"content", "description", "value_usd", "format", "keywords", "complexity"}
    for key, value in updates.items():
        if key in allowed_updates:
            artifact[key] = value

    # Update timestamp
    artifact["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Find artifact file path
    index = _load_index(project_dir)
    artifact_meta = index.get("artifacts", {}).get(artifact_id)

    if not artifact_meta or "storage_path" not in artifact_meta:
        logger.warning(f"Cannot find storage path for artifact {artifact_id}")
        return None

    artifact_path = project_dir / artifact_meta["storage_path"]

    # Write updated artifact atomically
    temp_path = artifact_path.with_suffix(".tmp")
    try:
        with open(temp_path, "w") as f:
            json.dump(artifact, f, indent=2, default=str)
        temp_path.replace(artifact_path)

        # Update index metadata
        artifact_meta["value_usd"] = artifact.get("value_usd", 0)
        artifact_meta["updated_at"] = artifact["updated_at"]
        _save_index(project_dir, index)

        logger.info(f"Updated artifact {artifact_id}")
        return artifact

    except Exception as e:
        logger.error(f"Failed to update artifact {artifact_id}: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return None


def delete_artifact(artifact_id: str, project_dir: Path) -> bool:
    """
    Delete an artifact from local storage.

    Args:
        artifact_id: The artifact ID to delete
        project_dir: Project root directory

    Returns:
        True if deleted, False if not found or error
    """
    # Find artifact in index
    index = _load_index(project_dir)
    artifact_meta = index.get("artifacts", {}).get(artifact_id)

    if not artifact_meta:
        logger.warning(f"Artifact {artifact_id} not found in index")
        return False

    # Get storage path
    storage_path = artifact_meta.get("storage_path")
    if storage_path:
        artifact_path = project_dir / storage_path
        if artifact_path.exists():
            try:
                artifact_path.unlink()
                logger.info(f"Deleted artifact file: {artifact_path}")
            except Exception as e:
                logger.error(f"Failed to delete artifact file: {e}")
                return False

    # Remove from index
    trace_id = artifact_meta.get("trace_id")
    spec_id = artifact_meta.get("spec_id")

    # Remove from artifacts dict
    if artifact_id in index.get("artifacts", {}):
        del index["artifacts"][artifact_id]

    # Remove from by_trace index
    if trace_id and trace_id in index.get("by_trace", {}):
        if artifact_id in index["by_trace"][trace_id]:
            index["by_trace"][trace_id].remove(artifact_id)
        if not index["by_trace"][trace_id]:
            del index["by_trace"][trace_id]

    # Remove from by_spec index
    if spec_id and spec_id in index.get("by_spec", {}):
        if artifact_id in index["by_spec"][spec_id]:
            index["by_spec"][spec_id].remove(artifact_id)
        if not index["by_spec"][spec_id]:
            del index["by_spec"][spec_id]

    # Save updated index
    _save_index(project_dir, index)

    logger.info(f"Deleted artifact {artifact_id} from index")
    return True


def create_langfuse_reference(
    artifact: dict[str, Any],
    artifact_id: str,
    storage_path: str,
) -> dict:
    """
    Create a reference for Langfuse storage with FULL content.

    IMPORTANT: No truncation is applied - full content is always stored.
    This ensures artifacts like diagrams, code, and documentation are complete.

    Args:
        artifact: Full artifact dict
        artifact_id: Generated artifact ID
        storage_path: Relative path to local storage

    Returns:
        Reference dict for Langfuse with full content
    """
    content = artifact.get("content", "")
    content_str = content if isinstance(content, str) else str(content)

    return {
        "id": artifact_id,
        "type": artifact.get("type", "unknown"),
        "format": artifact.get("format", "text"),
        "value_usd": artifact.get("value_usd", 0),
        "description": artifact.get("description", ""),
        "content": content_str,  # FULL content - NO truncation
        "content_length": len(content_str),
        "storage_path": storage_path,
        "tab": artifact.get("tab"),
    }


def rebuild_index(project_dir: Path) -> dict:
    """
    Rebuild the artifact index from files on disk.

    Use this if the index becomes corrupted or out of sync.

    Args:
        project_dir: Project root directory

    Returns:
        Rebuilt index dict
    """
    logger.info(f"Rebuilding artifact index for {project_dir}")

    index = {
        "version": 1,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "artifacts": {},
        "by_spec": {},
        "by_date": {},
        "by_trace": {},
    }

    artifacts_dir = _get_artifacts_dir(project_dir)
    if not artifacts_dir.exists():
        _save_index(project_dir, index)
        return index

    # Scan all date directories
    for date_dir in artifacts_dir.iterdir():
        if not date_dir.is_dir() or date_dir.name.endswith(".json"):
            continue

        date_str = date_dir.name

        for artifact_file in date_dir.glob("art_*.json"):
            artifact = _load_json_safe(artifact_file)
            if not artifact:
                continue

            artifact_id = artifact.get("id", artifact_file.stem)
            artifact_type = artifact.get("type", "unknown")
            value_usd = artifact.get("value_usd", 0)
            spec_id = artifact.get("spec_id")
            trace_id = artifact.get("trace_id")
            storage_path = str(artifact_file.relative_to(project_dir))

            # Add to main index
            index["artifacts"][artifact_id] = {
                "type": artifact_type,
                "value_usd": value_usd,
                "date": date_str,
                "spec_id": spec_id,
                "trace_id": trace_id,
                "storage_path": storage_path,
            }

            # Update by_date
            if date_str not in index["by_date"]:
                index["by_date"][date_str] = []
            index["by_date"][date_str].append(artifact_id)

            # Update by_spec
            if spec_id:
                if spec_id not in index["by_spec"]:
                    index["by_spec"][spec_id] = []
                index["by_spec"][spec_id].append(artifact_id)

            # Update by_trace
            if trace_id:
                if trace_id not in index["by_trace"]:
                    index["by_trace"][trace_id] = []
                index["by_trace"][trace_id].append(artifact_id)

    _save_index(project_dir, index)
    logger.info(f"Rebuilt index with {len(index['artifacts'])} artifacts")

    return index


def get_artifact_stats(project_dir: Path) -> dict:
    """
    Get statistics about stored artifacts.

    Returns:
        Dict with counts and totals
    """
    index = _load_index(project_dir)

    total_value = sum(
        art.get("value_usd", 0)
        for art in index.get("artifacts", {}).values()
    )

    types_count = {}
    for art in index.get("artifacts", {}).values():
        art_type = art.get("type", "unknown")
        types_count[art_type] = types_count.get(art_type, 0) + 1

    return {
        "total_artifacts": len(index.get("artifacts", {})),
        "total_value_usd": total_value,
        "by_type": types_count,
        "by_date_count": len(index.get("by_date", {})),
        "by_spec_count": len(index.get("by_spec", {})),
        "last_updated": index.get("last_updated"),
    }


# =============================================================================
# TAG MANAGEMENT FUNCTIONS
# =============================================================================


def add_tag_to_artifact(project_path: str, artifact_id: str, tag: str) -> bool:
    """
    Add a tag to an artifact.

    Args:
        project_path: Path to the project directory
        artifact_id: The artifact ID to tag
        tag: The tag to add

    Returns:
        True if tag was added successfully, False otherwise
    """
    project_dir = Path(project_path)
    artifact = load_artifact(artifact_id, project_dir)
    if not artifact:
        logger.warning(f"Artifact {artifact_id} not found for tagging")
        return False

    # Initialize tags array if not present
    if "metadata" not in artifact:
        artifact["metadata"] = {}
    if "tags" not in artifact["metadata"]:
        artifact["metadata"]["tags"] = []

    # Add tag if not already present
    tag = tag.strip().lower()
    if tag and tag not in artifact["metadata"]["tags"]:
        artifact["metadata"]["tags"].append(tag)
        artifact["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Find artifact file path and save
        index = _load_index(project_dir)
        artifact_meta = index.get("artifacts", {}).get(artifact_id)
        if artifact_meta and "storage_path" in artifact_meta:
            artifact_path = project_dir / artifact_meta["storage_path"]
            try:
                _atomic_write_json(artifact_path, artifact)
                logger.info(f"Added tag '{tag}' to artifact {artifact_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to save artifact with tag: {e}")
                return False

    return tag in artifact.get("metadata", {}).get("tags", [])


def remove_tag_from_artifact(project_path: str, artifact_id: str, tag: str) -> bool:
    """
    Remove a tag from an artifact.

    Args:
        project_path: Path to the project directory
        artifact_id: The artifact ID to untag
        tag: The tag to remove

    Returns:
        True if tag was removed successfully, False otherwise
    """
    project_dir = Path(project_path)
    artifact = load_artifact(artifact_id, project_dir)
    if not artifact:
        logger.warning(f"Artifact {artifact_id} not found for untagging")
        return False

    # Check if tag exists
    tag = tag.strip().lower()
    tags = artifact.get("metadata", {}).get("tags", [])
    if tag not in tags:
        return True  # Tag doesn't exist, consider it a success

    # Remove tag
    artifact["metadata"]["tags"].remove(tag)
    artifact["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Find artifact file path and save
    index = _load_index(project_dir)
    artifact_meta = index.get("artifacts", {}).get(artifact_id)
    if artifact_meta and "storage_path" in artifact_meta:
        artifact_path = project_dir / artifact_meta["storage_path"]
        try:
            _atomic_write_json(artifact_path, artifact)
            logger.info(f"Removed tag '{tag}' from artifact {artifact_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save artifact after tag removal: {e}")
            return False

    return False


def get_artifacts_by_tag(project_path: str, tag: str) -> list[dict]:
    """
    Get all artifacts that have a specific tag.

    Args:
        project_path: Path to the project directory
        tag: The tag to filter by

    Returns:
        List of artifacts with the specified tag
    """
    project_dir = Path(project_path)
    tag = tag.strip().lower()

    # Load all artifacts
    all_artifacts = list_artifacts(project_dir, limit=10000)

    # Filter by tag
    tagged_artifacts = []
    for artifact in all_artifacts:
        artifact_tags = artifact.get("metadata", {}).get("tags", [])
        if tag in artifact_tags:
            tagged_artifacts.append(artifact)

    return tagged_artifacts


def get_all_tags(project_path: str) -> list[str]:
    """
    Get all unique tags used across all artifacts.

    Args:
        project_path: Path to the project directory

    Returns:
        Sorted list of unique tags
    """
    project_dir = Path(project_path)

    # Load all artifacts
    all_artifacts = list_artifacts(project_dir, limit=10000)

    # Collect all unique tags
    all_tags: set[str] = set()
    for artifact in all_artifacts:
        artifact_tags = artifact.get("metadata", {}).get("tags", [])
        all_tags.update(artifact_tags)

    return sorted(all_tags)


def get_comprehensive_artifact_stats(project_dir: Path) -> dict:
    """
    Get comprehensive statistics about stored artifacts.

    Returns:
        Dict with detailed breakdowns:
        - total_count: Total number of artifacts
        - total_value_usd: Total value in USD
        - by_type: Breakdown by artifact type
        - by_tab: Breakdown by dashboard tab (dev, techlead, ops, business)
        - by_period: Breakdown by time period (last_7_days, last_30_days, all_time)
        - top_valuable: Top 5 most valuable artifacts
    """
    from datetime import timedelta

    index = _load_index(project_dir)
    artifacts_data = index.get("artifacts", {})

    # Get current date for period calculations
    now = datetime.now(timezone.utc)
    seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    thirty_days_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    # Initialize counters
    total_count = len(artifacts_data)
    total_value = 0.0
    by_type: dict[str, int] = {}
    by_tab: dict[str, int] = {"dev": 0, "techlead": 0, "ops": 0, "business": 0}
    by_period = {"last_7_days": 0, "last_30_days": 0, "all_time": total_count}

    # Value by type and tab for additional insights
    value_by_type: dict[str, float] = {}
    value_by_tab: dict[str, float] = {"dev": 0.0, "techlead": 0.0, "ops": 0.0, "business": 0.0}

    # Track artifacts with value for top_valuable
    artifacts_with_value: list[tuple[str, str, float, str]] = []  # (id, type, value, date)

    # Map artifact types to tabs (same as in artifact.py)
    TYPE_TO_TAB = {
        "diagram": "techlead",
        "code_example": "dev",
        "refactoring": "dev",
        "bug_fix": "dev",
        "test_case": "dev",
        "security_finding": "ops",
        "performance_insight": "ops",
        "architecture_insight": "techlead",
        "api_design": "techlead",
        "documentation": "techlead",
        "recommendation": "business",
        "cost_analysis": "business",
        "priority_assessment": "business",
    }

    for artifact_id, art_meta in artifacts_data.items():
        art_type = art_meta.get("type", "unknown")
        value_usd = art_meta.get("value_usd", 0)
        art_date = art_meta.get("date", "")

        # Accumulate total value
        total_value += value_usd

        # Count by type
        by_type[art_type] = by_type.get(art_type, 0) + 1
        value_by_type[art_type] = value_by_type.get(art_type, 0) + value_usd

        # Count by tab
        tab = TYPE_TO_TAB.get(art_type, "dev")
        by_tab[tab] = by_tab.get(tab, 0) + 1
        value_by_tab[tab] = value_by_tab.get(tab, 0) + value_usd

        # Count by period
        if art_date >= seven_days_ago:
            by_period["last_7_days"] += 1
        if art_date >= thirty_days_ago:
            by_period["last_30_days"] += 1

        # Track for top valuable
        if value_usd > 0:
            artifacts_with_value.append((artifact_id, art_type, value_usd, art_date))

    # Sort by value descending and take top 5
    artifacts_with_value.sort(key=lambda x: x[2], reverse=True)
    top_valuable = [
        {
            "id": art_id,
            "type": art_type,
            "value_usd": value_usd,
            "date": art_date,
        }
        for art_id, art_type, value_usd, art_date in artifacts_with_value[:5]
    ]

    return {
        "total_count": total_count,
        "total_value_usd": total_value,
        "by_type": by_type,
        "by_tab": by_tab,
        "by_period": by_period,
        "top_valuable": top_valuable,
        # Additional insights
        "value_by_type": value_by_type,
        "value_by_tab": value_by_tab,
        "last_updated": index.get("last_updated"),
    }


def get_artifacts_by_agent(
    project_dir: Path,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, dict]:
    """
    Get artifacts aggregated by agent type.

    Groups artifacts by their agent_type (planner, coder, qa_reviewer, etc.)
    and returns count, total value, and artifact types for each agent.

    Args:
        project_dir: Project root directory
        date_from: Optional start date filter (YYYY-MM-DD)
        date_to: Optional end date filter (YYYY-MM-DD)

    Returns:
        Dict mapping agent_type to aggregation stats:
        {
            "planner": {"count": 5, "total_value_usd": 250, "types": ["diagram", "architecture_insight"]},
            "coder": {"count": 12, "total_value_usd": 480, "types": ["code_example", "bug_fix"]},
            ...
        }
    """
    # Load all artifacts with optional date filtering
    artifacts = list_artifacts(
        project_dir,
        date_from=date_from,
        date_to=date_to,
        limit=10000,  # High limit to get all artifacts
    )

    # Aggregate by agent_type
    by_agent: dict[str, dict] = {}

    for artifact in artifacts:
        agent_type = artifact.get("agent_type") or "unknown"
        artifact_type = artifact.get("type", "unknown")
        value_usd = artifact.get("value_usd", 0)

        if agent_type not in by_agent:
            by_agent[agent_type] = {
                "count": 0,
                "total_value_usd": 0,
                "types": set(),
            }

        by_agent[agent_type]["count"] += 1
        by_agent[agent_type]["total_value_usd"] += value_usd
        by_agent[agent_type]["types"].add(artifact_type)

    # Convert sets to sorted lists for JSON serialization
    for agent_data in by_agent.values():
        agent_data["types"] = sorted(agent_data["types"])

    return by_agent


def _highlight_match(text: str, query: str, context_chars: int = 30) -> str:
    """
    Find the match in text and return a snippet with context.

    Args:
        text: The text to search in
        query: The search query (case-insensitive)
        context_chars: Number of characters to include before/after match

    Returns:
        A snippet with the match highlighted using **markers**
    """
    if not text or not query:
        return ""

    text_lower = text.lower()
    query_lower = query.lower()

    match_idx = text_lower.find(query_lower)
    if match_idx == -1:
        return ""

    # Calculate snippet boundaries
    start = max(0, match_idx - context_chars)
    end = min(len(text), match_idx + len(query) + context_chars)

    # Extract snippet
    snippet = text[start:end]

    # Add ellipsis if truncated
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""

    # Highlight the match within the snippet
    match_start_in_snippet = match_idx - start
    match_end_in_snippet = match_start_in_snippet + len(query)

    highlighted = (
        snippet[:match_start_in_snippet] +
        "**" + snippet[match_start_in_snippet:match_end_in_snippet] + "**" +
        snippet[match_end_in_snippet:]
    )

    return prefix + highlighted + suffix


def _calculate_relevance_score(
    artifact: dict,
    query: str,
    content_match: bool,
    description_match: bool,
    type_match: bool,
) -> int:
    """
    Calculate a relevance score for sorting search results.

    Higher scores indicate more relevant matches.

    Args:
        artifact: The artifact dict
        query: The search query
        content_match: Whether the query was found in content
        description_match: Whether the query was found in description
        type_match: Whether the query was found in type

    Returns:
        Relevance score (higher is better)
    """
    score = 0
    query_lower = query.lower()

    # Type match is most specific (weighted heavily)
    if type_match:
        score += 100

    # Description match is valuable (weighted moderately)
    if description_match:
        score += 50
        # Bonus if description starts with query
        desc = artifact.get("description", "").lower()
        if desc.startswith(query_lower):
            score += 25

    # Content match (weighted based on how early it appears)
    if content_match:
        score += 25
        content = artifact.get("content", "")
        if isinstance(content, str):
            content_lower = content.lower()
            match_idx = content_lower.find(query_lower)
            if match_idx != -1:
                # Earlier matches score higher (first 500 chars get bonus)
                if match_idx < 500:
                    score += 25 - (match_idx // 20)

                # Multiple occurrences increase relevance
                occurrences = content_lower.count(query_lower)
                score += min(occurrences * 5, 25)  # Cap at 25 bonus

    # Recency bonus (more recent artifacts score slightly higher)
    created_at = artifact.get("created_at", "")
    if created_at:
        # Simple check: if created today, add small bonus
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if created_at.startswith(today):
            score += 10

    return score


def search_artifacts(
    project_dir: Path,
    query: str,
    artifact_types: list[str] | None = None,
    spec_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """
    Search artifacts by content, description, and type.

    Performs case-insensitive full-text search across:
    - artifact content
    - artifact description
    - artifact type

    Args:
        project_dir: Project root directory
        query: Search query string (case-insensitive)
        artifact_types: Optional list of artifact types to filter by
        spec_id: Optional spec ID to filter by
        limit: Maximum number of results to return (default: 50)

    Returns:
        List of matching artifacts with previews and match highlights,
        sorted by relevance score (most relevant first).

        Each result contains:
        - id: artifact ID
        - type: artifact type
        - description: artifact description
        - value_usd: artifact value
        - created_at: creation timestamp
        - preview: first 200 chars of content
        - match_highlight: snippet showing where query matched
        - match_locations: list of where matches were found (content/description/type)
        - relevance_score: score used for sorting
    """
    if not query or len(query.strip()) < 1:
        return []

    query = query.strip()
    query_lower = query.lower()

    # Load index to get artifact IDs
    index = _load_index(project_dir)

    # Determine which artifact IDs to search
    if spec_id:
        artifact_ids = set(index.get("by_spec", {}).get(spec_id, []))
    else:
        artifact_ids = set(index.get("artifacts", {}).keys())

    # Apply type filter from index metadata first (optimization)
    if artifact_types:
        filtered_ids = set()
        for art_id in artifact_ids:
            art_meta = index.get("artifacts", {}).get(art_id, {})
            if art_meta.get("type") in artifact_types:
                filtered_ids.add(art_id)
        artifact_ids = filtered_ids

    # Search through artifacts
    results = []

    for artifact_id in artifact_ids:
        artifact = load_artifact(artifact_id, project_dir)
        if not artifact:
            continue

        # Get searchable fields
        content = artifact.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        content_lower = content.lower()

        description = artifact.get("description", "")
        description_lower = description.lower()

        artifact_type = artifact.get("type", "")
        type_lower = artifact_type.lower()

        # Check for matches
        content_match = query_lower in content_lower
        description_match = query_lower in description_lower
        type_match = query_lower in type_lower

        # Skip if no matches
        if not (content_match or description_match or type_match):
            continue

        # Build match locations
        match_locations = []
        if content_match:
            match_locations.append("content")
        if description_match:
            match_locations.append("description")
        if type_match:
            match_locations.append("type")

        # Generate match highlight
        match_highlight = ""
        if content_match:
            match_highlight = _highlight_match(content, query)
        elif description_match:
            match_highlight = _highlight_match(description, query)
        elif type_match:
            match_highlight = f"Type: **{artifact_type}**"

        # Generate preview (first 200 chars of content)
        preview = content[:PREVIEW_LENGTH]
        if len(content) > PREVIEW_LENGTH:
            preview += "..."

        # Calculate relevance score
        relevance_score = _calculate_relevance_score(
            artifact=artifact,
            query=query,
            content_match=content_match,
            description_match=description_match,
            type_match=type_match,
        )

        # Build result
        results.append({
            "id": artifact_id,
            "type": artifact_type,
            "format": artifact.get("format", "text"),
            "description": description,
            "value_usd": artifact.get("value_usd", 0),
            "created_at": artifact.get("created_at", ""),
            "spec_id": artifact.get("spec_id"),
            "tab": artifact.get("tab"),
            "preview": preview,
            "match_highlight": match_highlight,
            "match_locations": match_locations,
            "relevance_score": relevance_score,
        })

    # Sort by relevance score (descending)
    results.sort(key=lambda x: x["relevance_score"], reverse=True)

    # Apply limit
    return results[:limit]


# =============================================================================
# CLEANUP AND RETENTION FUNCTIONS
# =============================================================================

ARCHIVE_DIR = "archive"


def _get_archive_dir(project_dir: Path) -> Path:
    """Get the archive directory for artifacts."""
    return _get_artifacts_dir(project_dir) / ARCHIVE_DIR


def _get_artifact_file_size(artifact_path: Path) -> int:
    """Get file size in bytes."""
    try:
        return artifact_path.stat().st_size
    except OSError:
        return 0


def cleanup_old_artifacts(
    project_dir: Path,
    days: int = 30,
    dry_run: bool = True,
) -> dict:
    """
    Delete artifacts older than X days.

    Args:
        project_dir: Project root directory
        days: Delete artifacts older than this many days (default: 30)
        dry_run: If True, only preview what would be deleted (default: True)

    Returns:
        Dict with cleanup results:
        - deleted_count: Number of artifacts deleted (or would be deleted)
        - freed_bytes: Bytes freed (or would be freed)
        - deleted_ids: List of artifact IDs deleted (or would be deleted)
        - dry_run: Whether this was a dry run
    """
    from datetime import timedelta

    artifacts_dir = _get_artifacts_dir(project_dir)
    if not artifacts_dir.exists():
        return {
            "deleted_count": 0,
            "freed_bytes": 0,
            "deleted_ids": [],
            "dry_run": dry_run,
        }

    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d")

    deleted_count = 0
    freed_bytes = 0
    deleted_ids = []

    # Load index for metadata lookup
    index = _load_index(project_dir)

    # Scan artifacts
    for artifact_id, artifact_meta in list(index.get("artifacts", {}).items()):
        art_date = artifact_meta.get("date", "")

        if art_date < cutoff_str:
            # This artifact is older than cutoff
            storage_path = artifact_meta.get("storage_path")
            if storage_path:
                artifact_path = project_dir / storage_path
                file_size = _get_artifact_file_size(artifact_path)

                deleted_ids.append(artifact_id)
                freed_bytes += file_size
                deleted_count += 1

                if not dry_run:
                    # Actually delete the file
                    if artifact_path.exists():
                        try:
                            artifact_path.unlink()
                            logger.info(f"Deleted artifact: {artifact_id}")
                        except Exception as e:
                            logger.warning(f"Failed to delete artifact file {artifact_path}: {e}")

    # Update index if not dry run
    if not dry_run and deleted_count > 0:
        with _INDEX_LOCK:
            index = _load_index(project_dir)
            for art_id in deleted_ids:
                art_meta = index.get("artifacts", {}).get(art_id)
                if art_meta:
                    # Remove from main artifacts dict
                    if art_id in index.get("artifacts", {}):
                        del index["artifacts"][art_id]

                    # Remove from by_date index
                    art_date = art_meta.get("date", "")
                    if art_date in index.get("by_date", {}):
                        if art_id in index["by_date"][art_date]:
                            index["by_date"][art_date].remove(art_id)
                        if not index["by_date"][art_date]:
                            del index["by_date"][art_date]

                    # Remove from by_spec index
                    spec_id = art_meta.get("spec_id")
                    if spec_id and spec_id in index.get("by_spec", {}):
                        if art_id in index["by_spec"][spec_id]:
                            index["by_spec"][spec_id].remove(art_id)
                        if not index["by_spec"][spec_id]:
                            del index["by_spec"][spec_id]

                    # Remove from by_trace index
                    trace_id = art_meta.get("trace_id")
                    if trace_id and trace_id in index.get("by_trace", {}):
                        if art_id in index["by_trace"][trace_id]:
                            index["by_trace"][trace_id].remove(art_id)
                        if not index["by_trace"][trace_id]:
                            del index["by_trace"][trace_id]

            _save_index(project_dir, index)
            logger.info(f"Cleaned up {deleted_count} old artifacts, freed {freed_bytes} bytes")

    return {
        "deleted_count": deleted_count,
        "freed_bytes": freed_bytes,
        "deleted_ids": deleted_ids,
        "dry_run": dry_run,
    }


def cleanup_by_type(
    project_dir: Path,
    artifact_type: str,
    keep_latest: int = 10,
    dry_run: bool = True,
) -> dict:
    """
    Keep only the N most recent artifacts of a type.

    Args:
        project_dir: Project root directory
        artifact_type: The artifact type to clean up (e.g., "diagram", "code_example")
        keep_latest: Number of most recent artifacts to keep (default: 10)
        dry_run: If True, only preview what would be deleted (default: True)

    Returns:
        Dict with cleanup results:
        - deleted_count: Number of artifacts deleted (or would be deleted)
        - kept_count: Number of artifacts kept
        - deleted_ids: List of artifact IDs deleted (or would be deleted)
        - dry_run: Whether this was a dry run
    """
    index = _load_index(project_dir)

    # Find all artifacts of this type
    type_artifacts = []
    for artifact_id, artifact_meta in index.get("artifacts", {}).items():
        if artifact_meta.get("type") == artifact_type:
            type_artifacts.append({
                "id": artifact_id,
                "date": artifact_meta.get("date", ""),
                "storage_path": artifact_meta.get("storage_path"),
            })

    # Sort by date descending (most recent first)
    type_artifacts.sort(key=lambda x: x["date"], reverse=True)

    # Determine which to keep and which to delete
    to_keep = type_artifacts[:keep_latest]
    to_delete = type_artifacts[keep_latest:]

    deleted_ids = [art["id"] for art in to_delete]
    deleted_count = len(deleted_ids)
    kept_count = len(to_keep)

    if not dry_run and deleted_count > 0:
        # Delete the files
        for art in to_delete:
            storage_path = art.get("storage_path")
            if storage_path:
                artifact_path = project_dir / storage_path
                if artifact_path.exists():
                    try:
                        artifact_path.unlink()
                        logger.info(f"Deleted artifact: {art['id']}")
                    except Exception as e:
                        logger.warning(f"Failed to delete artifact file {artifact_path}: {e}")

        # Update index
        with _INDEX_LOCK:
            index = _load_index(project_dir)
            for art_id in deleted_ids:
                art_meta = index.get("artifacts", {}).get(art_id)
                if art_meta:
                    # Remove from main artifacts dict
                    if art_id in index.get("artifacts", {}):
                        del index["artifacts"][art_id]

                    # Remove from by_date index
                    art_date = art_meta.get("date", "")
                    if art_date in index.get("by_date", {}):
                        if art_id in index["by_date"][art_date]:
                            index["by_date"][art_date].remove(art_id)
                        if not index["by_date"][art_date]:
                            del index["by_date"][art_date]

                    # Remove from by_spec index
                    spec_id_meta = art_meta.get("spec_id")
                    if spec_id_meta and spec_id_meta in index.get("by_spec", {}):
                        if art_id in index["by_spec"][spec_id_meta]:
                            index["by_spec"][spec_id_meta].remove(art_id)
                        if not index["by_spec"][spec_id_meta]:
                            del index["by_spec"][spec_id_meta]

                    # Remove from by_trace index
                    trace_id = art_meta.get("trace_id")
                    if trace_id and trace_id in index.get("by_trace", {}):
                        if art_id in index["by_trace"][trace_id]:
                            index["by_trace"][trace_id].remove(art_id)
                        if not index["by_trace"][trace_id]:
                            del index["by_trace"][trace_id]

            _save_index(project_dir, index)
            logger.info(f"Cleaned up {deleted_count} '{artifact_type}' artifacts, kept {kept_count}")

    return {
        "deleted_count": deleted_count,
        "kept_count": kept_count,
        "deleted_ids": deleted_ids,
        "dry_run": dry_run,
    }


def get_cleanup_preview(
    project_dir: Path,
    days: int = 30,
) -> dict:
    """
    Preview what would be deleted (dry run).

    Args:
        project_dir: Project root directory
        days: Preview artifacts older than this many days (default: 30)

    Returns:
        Dict with preview results:
        - would_delete: Number of artifacts that would be deleted
        - total_bytes: Total bytes that would be freed
        - artifacts: List of artifact summaries that would be deleted
    """
    from datetime import timedelta

    artifacts_dir = _get_artifacts_dir(project_dir)
    if not artifacts_dir.exists():
        return {
            "would_delete": 0,
            "total_bytes": 0,
            "artifacts": [],
        }

    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d")

    total_bytes = 0
    artifacts_to_delete = []

    # Load index
    index = _load_index(project_dir)

    # Find artifacts older than cutoff
    for artifact_id, artifact_meta in index.get("artifacts", {}).items():
        art_date = artifact_meta.get("date", "")

        if art_date < cutoff_str:
            storage_path = artifact_meta.get("storage_path")
            file_size = 0
            if storage_path:
                artifact_path = project_dir / storage_path
                file_size = _get_artifact_file_size(artifact_path)

            total_bytes += file_size

            artifacts_to_delete.append({
                "id": artifact_id,
                "type": artifact_meta.get("type", "unknown"),
                "date": art_date,
                "value_usd": artifact_meta.get("value_usd", 0),
                "size_bytes": file_size,
                "spec_id": artifact_meta.get("spec_id"),
            })

    # Sort by date ascending (oldest first)
    artifacts_to_delete.sort(key=lambda x: x["date"])

    return {
        "would_delete": len(artifacts_to_delete),
        "total_bytes": total_bytes,
        "artifacts": artifacts_to_delete,
        "cutoff_date": cutoff_str,
        "days": days,
    }


def archive_artifacts(
    project_dir: Path,
    artifact_ids: list[str],
) -> dict:
    """
    Move artifacts to archive directory.

    Archived artifacts are moved (not deleted) to .auto-claude/artifacts/archive/
    This preserves them while keeping the main storage clean.

    Args:
        project_dir: Project root directory
        artifact_ids: List of artifact IDs to archive

    Returns:
        Dict with archive results:
        - archived_count: Number of artifacts successfully archived
        - failed_count: Number of artifacts that failed to archive
        - archived_ids: List of successfully archived artifact IDs
        - failed_ids: List of artifact IDs that failed to archive
    """
    import shutil

    archive_dir = _get_archive_dir(project_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived_count = 0
    failed_count = 0
    archived_ids = []
    failed_ids = []

    # Load index
    index = _load_index(project_dir)

    for artifact_id in artifact_ids:
        artifact_meta = index.get("artifacts", {}).get(artifact_id)
        if not artifact_meta:
            logger.warning(f"Artifact {artifact_id} not found in index")
            failed_ids.append(artifact_id)
            failed_count += 1
            continue

        storage_path = artifact_meta.get("storage_path")
        if not storage_path:
            logger.warning(f"No storage path for artifact {artifact_id}")
            failed_ids.append(artifact_id)
            failed_count += 1
            continue

        artifact_path = project_dir / storage_path
        if not artifact_path.exists():
            logger.warning(f"Artifact file not found: {artifact_path}")
            failed_ids.append(artifact_id)
            failed_count += 1
            continue

        # Move to archive
        archive_path = archive_dir / f"{artifact_id}.json"
        try:
            shutil.move(str(artifact_path), str(archive_path))
            logger.info(f"Archived artifact {artifact_id} to {archive_path}")
            archived_ids.append(artifact_id)
            archived_count += 1
        except Exception as e:
            logger.error(f"Failed to archive artifact {artifact_id}: {e}")
            failed_ids.append(artifact_id)
            failed_count += 1
            continue

    # Update index for archived artifacts
    if archived_count > 0:
        with _INDEX_LOCK:
            index = _load_index(project_dir)
            for art_id in archived_ids:
                art_meta = index.get("artifacts", {}).get(art_id)
                if art_meta:
                    # Update storage path to archive location
                    archive_rel_path = str((archive_dir / f"{art_id}.json").relative_to(project_dir))
                    art_meta["storage_path"] = archive_rel_path
                    art_meta["archived"] = True
                    art_meta["archived_at"] = datetime.now(timezone.utc).isoformat()

            _save_index(project_dir, index)
            logger.info(f"Updated index for {archived_count} archived artifacts")

    return {
        "archived_count": archived_count,
        "failed_count": failed_count,
        "archived_ids": archived_ids,
        "failed_ids": failed_ids,
    }


def restore_archived_artifact(
    project_dir: Path,
    artifact_id: str,
) -> dict:
    """
    Restore an archived artifact back to active storage.

    Args:
        project_dir: Project root directory
        artifact_id: The artifact ID to restore

    Returns:
        Dict with restore result:
        - success: Whether the restore was successful
        - artifact_id: The artifact ID
        - message: Status message
    """
    import shutil

    archive_dir = _get_archive_dir(project_dir)
    archive_path = archive_dir / f"{artifact_id}.json"

    if not archive_path.exists():
        return {
            "success": False,
            "artifact_id": artifact_id,
            "message": f"Archived artifact not found: {artifact_id}",
        }

    # Load artifact to get its date for proper restoration
    artifact = _load_json_safe(archive_path)
    if not artifact:
        return {
            "success": False,
            "artifact_id": artifact_id,
            "message": f"Failed to load archived artifact: {artifact_id}",
        }

    # Determine destination date directory
    created_at = artifact.get("created_at", "")
    if created_at:
        date_str = created_at[:10]  # YYYY-MM-DD
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    artifacts_dir = _get_artifacts_dir(project_dir)
    date_dir = artifacts_dir / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    dest_path = date_dir / f"{artifact_id}.json"

    try:
        shutil.move(str(archive_path), str(dest_path))
        logger.info(f"Restored artifact {artifact_id} to {dest_path}")
    except Exception as e:
        logger.error(f"Failed to restore artifact {artifact_id}: {e}")
        return {
            "success": False,
            "artifact_id": artifact_id,
            "message": f"Failed to restore: {e}",
        }

    # Update index
    with _INDEX_LOCK:
        index = _load_index(project_dir)
        art_meta = index.get("artifacts", {}).get(artifact_id)
        if art_meta:
            art_meta["storage_path"] = str(dest_path.relative_to(project_dir))
            art_meta.pop("archived", None)
            art_meta.pop("archived_at", None)
            _save_index(project_dir, index)

    return {
        "success": True,
        "artifact_id": artifact_id,
        "message": f"Restored to {dest_path}",
    }


def get_archived_artifacts(project_dir: Path) -> list[dict]:
    """
    List all archived artifacts.

    Args:
        project_dir: Project root directory

    Returns:
        List of archived artifact summaries
    """
    archive_dir = _get_archive_dir(project_dir)
    if not archive_dir.exists():
        return []

    archived = []
    for artifact_file in archive_dir.glob("art_*.json"):
        artifact = _load_json_safe(artifact_file)
        if artifact:
            archived.append({
                "id": artifact.get("id", artifact_file.stem),
                "type": artifact.get("type", "unknown"),
                "description": artifact.get("description", ""),
                "value_usd": artifact.get("value_usd", 0),
                "created_at": artifact.get("created_at", ""),
                "archived_at": artifact.get("archived_at", ""),
                "spec_id": artifact.get("spec_id"),
            })

    # Sort by archived_at descending
    archived.sort(key=lambda x: x.get("archived_at", ""), reverse=True)
    return archived


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================

# Emoji mapping for artifact types (used in Markdown export)
ARTIFACT_TYPE_EMOJIS = {
    "security_finding": "🔒",
    "diagram": "📊",
    "code_example": "💻",
    "refactoring": "🔧",
    "bug_fix": "🐛",
    "test_case": "🧪",
    "performance_insight": "⚡",
    "architecture_insight": "🏗️",
    "api_design": "🔌",
    "documentation": "📝",
    "recommendation": "💡",
    "cost_analysis": "💰",
    "priority_assessment": "📋",
    "qa_finding": "✅",
    "insight": "🔍",
    "unknown": "📦",
}


def export_artifacts_json(
    project_dir: Path,
    output_path: Path | None = None,
    artifact_types: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    agent_type: str | None = None,
    spec_id: str | None = None,
) -> dict:
    """
    Export artifacts to JSON format.

    Args:
        project_dir: Project root directory
        output_path: Optional path to save JSON file. If None, returns content.
        artifact_types: Filter by artifact types
        date_from: Filter by start date (YYYY-MM-DD)
        date_to: Filter by end date (YYYY-MM-DD)
        agent_type: Filter by agent type (e.g., "qa_reviewer", "coder")
        spec_id: Filter by spec ID

    Returns:
        Dict with export result:
        - If output_path: {"saved_to": path, "artifact_count": N, "total_value": X}
        - If no output_path: {"content": json_string, "artifact_count": N, "total_value": X}
    """
    # Load artifacts with filters
    artifacts = list_artifacts(
        project_dir=project_dir,
        spec_id=spec_id,
        date_from=date_from,
        date_to=date_to,
        artifact_types=artifact_types,
        limit=10000,  # High limit for export
    )

    # Apply agent_type filter if provided
    if agent_type:
        artifacts = [a for a in artifacts if a.get("agent_type") == agent_type]

    # Calculate stats
    total_value = sum(a.get("value_usd", 0) for a in artifacts)

    # Build export structure
    export_data = {
        "export_info": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project": project_dir.name if project_dir else "unknown",
            "filters": {
                "artifact_types": artifact_types,
                "date_from": date_from,
                "date_to": date_to,
                "agent_type": agent_type,
                "spec_id": spec_id,
            },
        },
        "summary": {
            "total_artifacts": len(artifacts),
            "total_value_usd": total_value,
            "by_type": {},
            "by_agent": {},
            "by_tab": {},
        },
        "artifacts": artifacts,
    }

    # Calculate breakdowns
    for art in artifacts:
        art_type = art.get("type", "unknown")
        agent = art.get("agent_type", "unknown")
        tab = art.get("tab", "unknown")

        if art_type not in export_data["summary"]["by_type"]:
            export_data["summary"]["by_type"][art_type] = {"count": 0, "value": 0}
        export_data["summary"]["by_type"][art_type]["count"] += 1
        export_data["summary"]["by_type"][art_type]["value"] += art.get("value_usd", 0)

        if agent not in export_data["summary"]["by_agent"]:
            export_data["summary"]["by_agent"][agent] = {"count": 0, "value": 0}
        export_data["summary"]["by_agent"][agent]["count"] += 1
        export_data["summary"]["by_agent"][agent]["value"] += art.get("value_usd", 0)

        if tab not in export_data["summary"]["by_tab"]:
            export_data["summary"]["by_tab"][tab] = {"count": 0, "value": 0}
        export_data["summary"]["by_tab"][tab]["count"] += 1
        export_data["summary"]["by_tab"][tab]["value"] += art.get("value_usd", 0)

    # Output
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Exported {len(artifacts)} artifacts to {output_path}")
        return {
            "saved_to": str(output_path),
            "artifact_count": len(artifacts),
            "total_value": total_value,
        }
    else:
        content = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
        return {
            "content": content,
            "artifact_count": len(artifacts),
            "total_value": total_value,
        }


def export_artifacts_markdown(
    project_dir: Path,
    output_path: Path | None = None,
    artifact_types: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    agent_type: str | None = None,
    spec_id: str | None = None,
    include_content: bool = True,
    max_content_length: int = 2000,
) -> dict:
    """
    Export artifacts to Markdown format.

    Args:
        project_dir: Project root directory
        output_path: Optional path to save Markdown file. If None, returns content.
        artifact_types: Filter by artifact types
        date_from: Filter by start date (YYYY-MM-DD)
        date_to: Filter by end date (YYYY-MM-DD)
        agent_type: Filter by agent type (e.g., "qa_reviewer", "coder")
        spec_id: Filter by spec ID
        include_content: Whether to include full artifact content
        max_content_length: Max length for content preview (0 = unlimited)

    Returns:
        Dict with export result:
        - If output_path: {"saved_to": path, "artifact_count": N, "total_value": X}
        - If no output_path: {"content": markdown_string, "artifact_count": N, "total_value": X}
    """
    # Load artifacts with filters
    artifacts = list_artifacts(
        project_dir=project_dir,
        spec_id=spec_id,
        date_from=date_from,
        date_to=date_to,
        artifact_types=artifact_types,
        limit=10000,  # High limit for export
    )

    # Apply agent_type filter if provided
    if agent_type:
        artifacts = [a for a in artifacts if a.get("agent_type") == agent_type]

    # Calculate stats
    total_value = sum(a.get("value_usd", 0) for a in artifacts)

    # Build type breakdown
    by_type: dict[str, dict] = {}
    for art in artifacts:
        art_type = art.get("type", "unknown")
        if art_type not in by_type:
            by_type[art_type] = {"count": 0, "value": 0}
        by_type[art_type]["count"] += 1
        by_type[art_type]["value"] += art.get("value_usd", 0)

    # Generate date string
    generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build Markdown content
    lines = [
        "# Artifacts Export",
        "",
        f"Generated: {generated_date}",
        "",
    ]

    # Add filter info if any filters applied
    filters_applied = []
    if artifact_types:
        filters_applied.append(f"Types: {', '.join(artifact_types)}")
    if date_from or date_to:
        date_range = f"{date_from or 'start'} to {date_to or 'now'}"
        filters_applied.append(f"Date range: {date_range}")
    if agent_type:
        filters_applied.append(f"Agent: {agent_type}")
    if spec_id:
        filters_applied.append(f"Spec: {spec_id}")

    if filters_applied:
        lines.append("**Filters:**")
        for f in filters_applied:
            lines.append(f"- {f}")
        lines.append("")

    # Summary section
    lines.extend([
        "## Summary",
        f"- **Total:** {len(artifacts)} artifacts",
        f"- **Value:** ${total_value:,.2f}",
        "",
    ])

    # Type breakdown
    if by_type:
        lines.append("### By Type")
        lines.append("")
        lines.append("| Type | Count | Value |")
        lines.append("|------|-------|-------|")
        for art_type, stats in sorted(by_type.items(), key=lambda x: -x[1]["value"]):
            emoji = ARTIFACT_TYPE_EMOJIS.get(art_type, "📦")
            type_display = art_type.replace("_", " ").title()
            lines.append(f"| {emoji} {type_display} | {stats['count']} | ${stats['value']:,.2f} |")
        lines.append("")

    # Artifacts section
    lines.extend([
        "## Artifacts",
        "",
    ])

    # Group by tab for better organization
    by_tab: dict[str, list] = {}
    for art in artifacts:
        tab = art.get("tab", "other")
        if tab not in by_tab:
            by_tab[tab] = []
        by_tab[tab].append(art)

    tab_order = ["ops", "techlead", "dev", "business", "other"]
    tab_names = {
        "ops": "Operations",
        "techlead": "Tech Lead",
        "dev": "Developer",
        "business": "Business",
        "other": "Other",
    }

    for tab in tab_order:
        if tab not in by_tab:
            continue
        tab_artifacts = by_tab[tab]

        lines.extend([
            f"### {tab_names.get(tab, tab.title())} ({len(tab_artifacts)} artifacts)",
            "",
        ])

        for art in tab_artifacts:
            art_type = art.get("type", "unknown")
            emoji = ARTIFACT_TYPE_EMOJIS.get(art_type, "📦")
            type_display = art_type.replace("_", " ").title()

            lines.extend([
                f"#### {emoji} {type_display}",
                "",
                f"**ID:** `{art.get('id', 'unknown')}`",
                f"**Value:** ${art.get('value_usd', 0):,.2f}",
                f"**Agent:** {art.get('agent_type', 'unknown')}",
                f"**Created:** {art.get('created_at', 'unknown')[:10] if art.get('created_at') else 'unknown'}",
                "",
            ])

            if art.get("description"):
                lines.append(f"*{art['description']}*")
                lines.append("")

            if include_content and art.get("content"):
                content = art["content"]
                if max_content_length > 0 and len(content) > max_content_length:
                    content = content[:max_content_length] + "\n\n... (truncated)"

                # Determine code block language
                art_format = art.get("format", "text")
                if art_format in ["mermaid", "python", "typescript", "javascript", "sql", "bash", "json", "yaml"]:
                    lang = art_format
                elif art_format == "markdown":
                    lang = ""
                else:
                    lang = ""

                if lang:
                    lines.append(f"```{lang}")
                    lines.append(content)
                    lines.append("```")
                else:
                    lines.append(content)
                lines.append("")

            lines.append("---")
            lines.append("")

    # Join all lines
    markdown_content = "\n".join(lines)

    # Output
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        logger.info(f"Exported {len(artifacts)} artifacts to {output_path}")
        return {
            "saved_to": str(output_path),
            "artifact_count": len(artifacts),
            "total_value": total_value,
        }
    else:
        return {
            "content": markdown_content,
            "artifact_count": len(artifacts),
            "total_value": total_value,
        }
