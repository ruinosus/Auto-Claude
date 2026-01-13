"""
Artifact Collector
==================

Collects artifacts created during a session and prepares them for ROI calculation.

Features:
    - Collect artifacts by trace ID
    - Calculate total value
    - Prepare for Langfuse publishing
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Collected artifacts per trace
_collected_artifacts: Dict[str, List[Dict[str, Any]]] = {}


async def collect_session_artifacts(trace_id: str) -> List[Dict[str, Any]]:
    """
    Collect all artifacts created during a session.

    Uses the existing artifact_storage module to list artifacts
    associated with the trace ID.

    Args:
        trace_id: The trace ID to collect artifacts for

    Returns:
        List of artifact dictionaries
    """
    if not trace_id:
        return []

    try:
        from analytics.artifact_storage import list_artifacts

        # Get project directory from environment or cwd
        import os
        project_dir = os.environ.get("PROJECT_DIR", os.getcwd())

        artifacts = list_artifacts(
            project_dir=Path(project_dir),
            trace_id=trace_id,
        )

        # Store for later retrieval
        _collected_artifacts[trace_id] = artifacts

        logger.info(f"Collected {len(artifacts)} artifacts for trace {trace_id}")

        # Calculate total value
        total_value = sum(a.get("value_usd", 0) for a in artifacts)
        logger.debug(f"Total artifact value: ${total_value}")

        return artifacts

    except ImportError as e:
        logger.warning(f"Could not import artifact_storage: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to collect artifacts: {e}")
        return []


def get_collected_artifacts(trace_id: str) -> List[Dict[str, Any]]:
    """
    Get previously collected artifacts for a trace.

    Args:
        trace_id: The trace ID

    Returns:
        List of artifact dictionaries
    """
    return _collected_artifacts.get(trace_id, [])


async def publish_session_roi(
    trace_id: str,
    agent_type: str,
    metrics: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Publish ROI for a session using ROI Engine.

    Args:
        trace_id: The trace ID
        agent_type: Type of agent (coder, planner, etc.)
        metrics: Session metrics

    Returns:
        ROI result dictionary or None
    """
    if not trace_id:
        return None

    try:
        from roi_engine.core import calculate_roi_for_spec, load_squad_config, publish_roi

        # Get collected artifacts
        artifacts = get_collected_artifacts(trace_id)

        # Get project directory
        import os
        from pathlib import Path
        project_dir = Path(os.environ.get("PROJECT_DIR", os.getcwd()))
        project_id = project_dir.name

        # Use ROI Engine to calculate and publish ROI
        squad_config = load_squad_config(project_dir=project_dir)
        roi_result = calculate_roi_for_spec(
            spec_id=f"{agent_type}-{trace_id[:8]}",
            project_dir=project_dir,
            token_cost=metrics.get("cost_usd", 0),
            squad_config=squad_config,
        )
        await publish_roi(
            roi_result,
            trace_id=trace_id,
            project_dir=project_dir,
        )

        logger.info(f"Published ROI for {agent_type}: {roi_result.roi_percentage:.1f}%")
        return {
            "success": True,
            "roi_percentage": roi_result.roi_percentage,
            "total_value_usd": roi_result.total_artifact_value,
            "artifact_count": roi_result.artifact_count,
        }

    except ImportError as e:
        logger.warning(f"Could not import ROI Engine: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to publish ROI: {e}")
        return None


def _to_langfuse_ref(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert artifact to Langfuse reference format.

    Langfuse references are lightweight - full content is stored locally.
    """
    return {
        "artifact_id": artifact.get("id"),
        "type": artifact.get("type"),
        "value_usd": artifact.get("value_usd", 0),
        "storage_path": artifact.get("storage_path"),
        "description": artifact.get("description", "")[:100],  # Truncate
    }


def clear_collected_artifacts(trace_id: Optional[str] = None):
    """
    Clear collected artifacts.

    Args:
        trace_id: Specific trace to clear, or None to clear all
    """
    if trace_id:
        _collected_artifacts.pop(trace_id, None)
    else:
        _collected_artifacts.clear()
