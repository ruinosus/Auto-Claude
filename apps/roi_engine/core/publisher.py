"""
ROI Publisher

Publishes ROI results to Langfuse as scores.
Also handles local persistence of ROI results.

The publisher creates multiple scores in Langfuse:
- artifact_based_roi: Main ROI percentage
- total_artifact_value: Sum of all artifact values
- token_cost: Cost incurred
- net_value: Value - Cost
- value_by_{role}: Value contributed by each role
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import ROIResult

# Try to import Langfuse integration from backend
_backend_path = Path(__file__).parent.parent.parent / "backend"
if str(_backend_path) not in sys.path:
    sys.path.insert(0, str(_backend_path))

try:
    from analytics.langfuse_integration import (
        is_langfuse_ready,
        flush_langfuse,
    )
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

    def is_langfuse_ready() -> bool:
        return False

    def flush_langfuse() -> None:
        pass


def publish_roi_to_langfuse(
    roi_result: ROIResult,
    trace_id: str,
) -> bool:
    """
    Publish ROI scores to a Langfuse trace.

    Creates multiple scores:
    - artifact_based_roi: Main ROI percentage
    - total_artifact_value: Total value generated
    - token_cost: Cost incurred
    - net_value: Net value (value - cost)
    - artifact_count: Number of artifacts
    - value_by_{role}: Value by each role

    Args:
        roi_result: Calculated ROI result
        trace_id: Langfuse trace ID to attach scores to

    Returns:
        True if successful, False otherwise
    """
    if not LANGFUSE_AVAILABLE or not is_langfuse_ready():
        return False

    try:
        # Import here to avoid issues if Langfuse not configured
        from langfuse import Langfuse

        langfuse = Langfuse()

        # Main ROI score
        langfuse.score(
            trace_id=trace_id,
            name="artifact_based_roi",
            value=roi_result.roi_percentage,
            data_type="NUMERIC",
            comment=f"ROI based on {roi_result.artifact_count} artifacts",
        )

        # Value breakdown scores
        langfuse.score(
            trace_id=trace_id,
            name="total_artifact_value",
            value=roi_result.total_artifact_value,
            data_type="NUMERIC",
        )

        langfuse.score(
            trace_id=trace_id,
            name="token_cost",
            value=roi_result.token_cost,
            data_type="NUMERIC",
        )

        langfuse.score(
            trace_id=trace_id,
            name="net_value",
            value=roi_result.net_value,
            data_type="NUMERIC",
        )

        langfuse.score(
            trace_id=trace_id,
            name="artifact_count",
            value=float(roi_result.artifact_count),
            data_type="NUMERIC",
        )

        # Per-role value scores
        for role, value in roi_result.by_role.items():
            langfuse.score(
                trace_id=trace_id,
                name=f"value_by_{role}",
                value=value,
                data_type="NUMERIC",
            )

        # Flush to ensure delivery
        flush_langfuse()

        return True

    except Exception:
        return False


def save_roi_locally(
    roi_result: ROIResult,
    project_dir: Path | str,
    filename: str | None = None,
) -> Path:
    """
    Save ROI result to local JSON file.

    Args:
        roi_result: Calculated ROI result
        project_dir: Project directory
        filename: Optional custom filename

    Returns:
        Path to saved file
    """
    project_path = Path(project_dir)
    roi_dir = project_path / ".auto-claude" / "roi"
    roi_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"roi_{roi_result.scope}_{roi_result.scope_id}_{timestamp}.json"

    file_path = roi_dir / filename

    # Prepare data for serialization
    data = {
        **roi_result.to_dict(),
        "artifacts": [
            {
                "artifact_id": a.artifact_id,
                "artifact_type": a.artifact_type,
                "role": a.role.value,
                "seniority": a.seniority.value,
                "hourly_rate": a.hourly_rate,
                "estimated_hours": a.estimated_hours,
                "calculated_value": a.calculated_value,
                "original_value": a.original_value,
            }
            for a in roi_result.artifacts
        ],
    }

    file_path.write_text(json.dumps(data, indent=2, default=str))
    return file_path


def load_roi_locally(file_path: Path | str) -> dict[str, Any] | None:
    """
    Load ROI result from local JSON file.

    Args:
        file_path: Path to ROI JSON file

    Returns:
        ROI data dict or None if not found
    """
    path = Path(file_path)
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def list_local_roi_results(
    project_dir: Path | str,
    scope: str | None = None,
) -> list[dict[str, Any]]:
    """
    List all locally saved ROI results.

    Args:
        project_dir: Project directory
        scope: Optional filter by scope ("trace", "spec", "project")

    Returns:
        List of ROI result summaries
    """
    project_path = Path(project_dir)
    roi_dir = project_path / ".auto-claude" / "roi"

    if not roi_dir.exists():
        return []

    results = []
    for file_path in roi_dir.glob("roi_*.json"):
        data = load_roi_locally(file_path)
        if data:
            if scope and data.get("scope") != scope:
                continue
            results.append({
                "file": str(file_path),
                "scope": data.get("scope"),
                "scope_id": data.get("scope_id"),
                "roi_percentage": data.get("roi_percentage"),
                "total_artifact_value": data.get("total_artifact_value"),
                "token_cost": data.get("token_cost"),
                "calculated_at": data.get("calculated_at"),
            })

    # Sort by calculated_at descending
    results.sort(key=lambda x: x.get("calculated_at", ""), reverse=True)
    return results


async def publish_roi(
    roi_result: ROIResult,
    trace_id: str | None = None,
    project_dir: Path | str | None = None,
    save_local: bool = True,
    publish_langfuse: bool = True,
) -> dict[str, Any]:
    """
    Publish ROI result to both Langfuse and local storage.

    Args:
        roi_result: Calculated ROI result
        trace_id: Langfuse trace ID (required for Langfuse publishing)
        project_dir: Project directory (required for local saving)
        save_local: Whether to save locally
        publish_langfuse: Whether to publish to Langfuse

    Returns:
        Dict with publishing results
    """
    result = {
        "langfuse_published": False,
        "local_saved": False,
        "local_path": None,
    }

    if publish_langfuse and trace_id:
        result["langfuse_published"] = publish_roi_to_langfuse(roi_result, trace_id)

    if save_local and project_dir:
        path = save_roi_locally(roi_result, project_dir)
        result["local_saved"] = True
        result["local_path"] = str(path)

    return result
