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
