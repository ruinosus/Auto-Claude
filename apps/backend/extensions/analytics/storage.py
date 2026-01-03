"""
Artifact Storage Layer (Integrated)
====================================

This module is a WRAPPER around the main analytics/artifact_storage.py.
It provides the same API but delegates to the main storage to avoid duplication.

Why a wrapper?
--------------
The extensions layer needs to capture and store artifacts, but we don't want
to duplicate storage. By wrapping the main storage:
- All artifacts go to ONE location: .auto-claude/artifacts/
- No duplicate artifact IDs or indices
- ROI calculations are consistent
- Langfuse references point to the same artifacts

Storage Location:
    .auto-claude/artifacts/  (same as main analytics)
    NOT .auto-claude/ext-artifacts/  (deprecated)
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Flag to track if main storage is available
_main_storage_available = None


def _check_main_storage() -> bool:
    """Check if main analytics storage is available."""
    global _main_storage_available

    if _main_storage_available is not None:
        return _main_storage_available

    try:
        from analytics.artifact_storage import save_artifact as _main_save
        _main_storage_available = True
        logger.debug("Main analytics storage available")
    except ImportError:
        _main_storage_available = False
        logger.warning("Main analytics storage not available, using fallback")

    return _main_storage_available


def _get_project_dir(project_dir: Optional[str] = None) -> Path:
    """Get project directory as Path."""
    if project_dir:
        return Path(project_dir)
    return Path(os.environ.get("PROJECT_DIR", os.getcwd()))


def save_artifact(
    artifact_type: str,
    content: str,
    description: str,
    value_usd: float,
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    agent_type: str = "unknown",
    project_dir: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    format: str = "text",
) -> Optional[Dict[str, Any]]:
    """
    Save an artifact using the MAIN analytics storage.

    This is a wrapper that converts our API to the main storage API,
    ensuring all artifacts go to one location.

    Args:
        artifact_type: Type of artifact (diagram, pattern_discovered, etc.)
        content: FULL content - NO truncation
        description: Human-readable description
        value_usd: Calculated USD value
        trace_id: Langfuse trace ID
        spec_id: Spec ID if applicable
        agent_type: Agent that created the artifact
        project_dir: Project directory
        metadata: Additional metadata
        format: Content format (text, mermaid, json, markdown)

    Returns:
        Complete artifact dict if saved, None on error
    """
    project_path = _get_project_dir(project_dir)

    # Build artifact dict for main storage
    artifact = {
        "type": artifact_type,
        "format": format,
        "content": content,
        "value_usd": value_usd,
        "description": description,
        "metadata": metadata or {},
    }

    # Try main storage first
    if _check_main_storage():
        try:
            from analytics.artifact_storage import save_artifact as main_save, load_artifact as main_load

            artifact_id = main_save(
                artifact=artifact,
                project_dir=project_path,
                spec_id=spec_id,
                trace_id=trace_id,
                agent_type=agent_type,
            )

            if artifact_id:
                # Load the full artifact to return
                full_artifact = main_load(artifact_id, project_path)
                if full_artifact:
                    logger.info(f"Saved artifact {artifact_id} via main storage")
                    return full_artifact

                # If load failed, return minimal info
                return {
                    "id": artifact_id,
                    "type": artifact_type,
                    "format": format,
                    "content": content,
                    "value_usd": value_usd,
                    "description": description,
                    "trace_id": trace_id,
                    "spec_id": spec_id,
                    "agent_type": agent_type,
                }

        except Exception as e:
            logger.error(f"Failed to save via main storage: {e}")
            # Fall through to fallback

    # Fallback: just log (don't create duplicate storage)
    logger.warning(
        f"Main storage not available, artifact not saved: {artifact_type} "
        f"({len(content)} chars, ${value_usd:.2f})"
    )
    return None


def load_artifact(
    artifact_id: str,
    project_dir: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Load an artifact by ID using main storage.

    Args:
        artifact_id: The artifact ID
        project_dir: Project directory

    Returns:
        Full artifact dict or None if not found
    """
    if not _check_main_storage():
        logger.warning("Main storage not available")
        return None

    try:
        from analytics.artifact_storage import load_artifact as main_load

        project_path = _get_project_dir(project_dir)
        return main_load(artifact_id, project_path)

    except Exception as e:
        logger.error(f"Failed to load artifact {artifact_id}: {e}")
        return None


def list_artifacts(
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    agent_type: Optional[str] = None,
    date: Optional[str] = None,
    artifact_type: Optional[str] = None,
    project_dir: Optional[str] = None,
    include_content: bool = False,
) -> List[Dict[str, Any]]:
    """
    List artifacts with optional filters using main storage.

    Args:
        trace_id: Filter by Langfuse trace
        spec_id: Filter by spec ID
        agent_type: Filter by agent type
        date: Filter by date (YYYY-MM-DD)
        artifact_type: Filter by artifact type
        project_dir: Project directory
        include_content: If True, load full content (always True with main storage)

    Returns:
        List of artifact dicts
    """
    if not _check_main_storage():
        return []

    try:
        from analytics.artifact_storage import list_artifacts as main_list

        project_path = _get_project_dir(project_dir)

        # Main storage uses different parameter names
        artifact_types = [artifact_type] if artifact_type else None

        artifacts = main_list(
            project_dir=project_path,
            spec_id=spec_id,
            trace_id=trace_id,
            date_from=date,
            date_to=date,
            artifact_types=artifact_types,
            limit=1000,
        )

        # Apply agent_type filter (main storage doesn't have this directly)
        if agent_type:
            artifacts = [a for a in artifacts if a.get("agent_type") == agent_type]

        return artifacts

    except Exception as e:
        logger.error(f"Failed to list artifacts: {e}")
        return []


def get_artifacts_summary(
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    project_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get a summary of artifacts for Langfuse publishing.

    Uses main storage stats if available.
    If no trace_id/spec_id filters, returns summary for ALL artifacts.
    """
    if not _check_main_storage():
        return {
            "total_artifacts": 0,
            "total_value_usd": 0,
            "by_type": {},
            "artifacts": [],
        }

    try:
        from analytics.artifact_storage import list_artifacts as main_list

        project_path = _get_project_dir(project_dir)

        # Get artifacts - with or without filters
        artifacts = main_list(
            project_dir=project_path,
            spec_id=spec_id,
            trace_id=trace_id,
            limit=1000,
        )

        total_value = sum(a.get("value_usd", 0) for a in artifacts)
        by_type = {}

        for a in artifacts:
            t = a.get("type", "unknown")
            if t not in by_type:
                by_type[t] = {"count": 0, "value": 0}
            by_type[t]["count"] += 1
            by_type[t]["value"] += a.get("value_usd", 0)

        return {
            "total_artifacts": len(artifacts),
            "total_value_usd": round(total_value, 2),
            "by_type": by_type,
            "artifacts": [
                {
                    "id": a.get("id"),
                    "type": a.get("type"),
                    "value_usd": a.get("value_usd"),
                    "description": a.get("description"),
                }
                for a in artifacts
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get artifacts summary: {e}")
        return {
            "total_artifacts": 0,
            "total_value_usd": 0,
            "by_type": {},
            "artifacts": [],
        }
