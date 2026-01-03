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
    Publish ROI for a session.

    Uses the existing roi_publisher module.

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
        from analytics.roi_publisher import publish_feature_roi

        # Get collected artifacts
        artifacts = get_collected_artifacts(trace_id)

        # Map agent_type to feature_type
        feature_type_map = {
            "coder": "build_coder",
            "planner": "build_planner",
            "qa_reviewer": "build_qa_reviewer",
            "qa_fixer": "build_qa_fixer",
            "insights": "insights_chat",
            "spec_gatherer": "spec_gatherer",
            "spec_writer": "spec_writer",
        }
        feature_type = feature_type_map.get(agent_type, agent_type)

        # Get project ID
        import os
        project_id = os.environ.get("PROJECT_ID", os.path.basename(os.getcwd()))

        result = await publish_feature_roi(
            feature_type=feature_type,
            project_id=project_id,
            cost_usd=metrics.get("cost_usd", 0),
            tokens=metrics.get("tokens", 0),
            trace_id=trace_id,
            metrics=metrics,
            artifacts=[_to_langfuse_ref(a) for a in artifacts],
        )

        logger.info(f"Published ROI for {agent_type}: {result}")
        return result

    except ImportError as e:
        logger.warning(f"Could not import roi_publisher: {e}")
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
