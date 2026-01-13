"""
Artifact Consumer

Consumes artifacts from the existing artifact storage system.
This is the bridge between the existing MCP tools/extractors and the ROI Engine.

The consumer DOES NOT create artifacts - it reads what was already created
by the existing system and feeds them to the valuator.
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add backend to path for imports
_backend_path = Path(__file__).parent.parent.parent / "backend"
if str(_backend_path) not in sys.path:
    sys.path.insert(0, str(_backend_path))


class ArtifactConsumer:
    """
    Consumes artifacts from the existing artifact storage.

    This class reads artifacts that were created by:
    - MCP tools (create_artifact, create_diagram, etc.)
    - Extraction functions (extract_planner_artifacts, etc.)

    The artifacts are stored in .auto-claude/artifacts/ by the existing system.
    """

    def __init__(self, project_dir: Path | str):
        """
        Initialize consumer with project directory.

        Args:
            project_dir: Project root directory
        """
        self.project_dir = Path(project_dir)
        self.artifacts_dir = self.project_dir / ".auto-claude" / "artifacts"
        self.index_file = self.artifacts_dir / "index.json"
        self._index: dict[str, Any] | None = None

    def _load_index(self) -> dict[str, Any]:
        """Load the artifact index from disk."""
        if self._index is not None:
            return self._index

        if not self.index_file.exists():
            self._index = {"artifacts": {}, "by_spec": {}, "by_trace": {}, "by_date": {}}
            return self._index

        try:
            self._index = json.loads(self.index_file.read_text())
            return self._index
        except (json.JSONDecodeError, OSError):
            self._index = {"artifacts": {}, "by_spec": {}, "by_trace": {}, "by_date": {}}
            return self._index

    def _load_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        """Load a single artifact by ID."""
        index = self._load_index()
        artifact_info = index.get("artifacts", {}).get(artifact_id)

        if not artifact_info:
            return None

        storage_path = artifact_info.get("storage_path")
        if not storage_path:
            return artifact_info  # Return index info if no storage path

        # Load full artifact from storage
        full_path = self.project_dir / storage_path
        if not full_path.exists():
            return artifact_info

        try:
            return json.loads(full_path.read_text())
        except (json.JSONDecodeError, OSError):
            return artifact_info

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        """
        Get a single artifact by ID.

        Args:
            artifact_id: Artifact ID (e.g., "art_abc123...")

        Returns:
            Artifact dict or None if not found
        """
        return self._load_artifact(artifact_id)

    def get_artifacts_for_spec(self, spec_id: str) -> list[dict[str, Any]]:
        """
        Get all artifacts created for a spec.

        Args:
            spec_id: Spec ID (e.g., "001-feature")

        Returns:
            List of artifact dicts
        """
        index = self._load_index()
        artifact_ids = index.get("by_spec", {}).get(spec_id, [])

        artifacts = []
        for artifact_id in artifact_ids:
            artifact = self._load_artifact(artifact_id)
            if artifact:
                artifacts.append(artifact)

        return artifacts

    def get_artifacts_for_trace(self, trace_id: str) -> list[dict[str, Any]]:
        """
        Get all artifacts created in a trace.

        Args:
            trace_id: Langfuse trace ID

        Returns:
            List of artifact dicts
        """
        index = self._load_index()
        artifact_ids = index.get("by_trace", {}).get(trace_id, [])

        artifacts = []
        for artifact_id in artifact_ids:
            artifact = self._load_artifact(artifact_id)
            if artifact:
                artifacts.append(artifact)

        return artifacts

    def get_artifacts_for_date(self, date_str: str) -> list[dict[str, Any]]:
        """
        Get all artifacts created on a specific date.

        Args:
            date_str: Date string (YYYY-MM-DD)

        Returns:
            List of artifact dicts
        """
        index = self._load_index()
        artifact_ids = index.get("by_date", {}).get(date_str, [])

        artifacts = []
        for artifact_id in artifact_ids:
            artifact = self._load_artifact(artifact_id)
            if artifact:
                artifacts.append(artifact)

        return artifacts

    def get_all_artifacts(
        self,
        artifact_type: str | None = None,
        agent_type: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get all artifacts with optional filters.

        Args:
            artifact_type: Filter by artifact type (e.g., "diagram")
            agent_type: Filter by agent type (e.g., "planner")
            limit: Maximum number of artifacts to return

        Returns:
            List of artifact dicts
        """
        index = self._load_index()
        all_artifact_ids = list(index.get("artifacts", {}).keys())

        artifacts = []
        for artifact_id in all_artifact_ids:
            artifact = self._load_artifact(artifact_id)
            if not artifact:
                continue

            # Apply filters
            if artifact_type and artifact.get("type") != artifact_type:
                continue
            if agent_type and artifact.get("agent_type") != agent_type:
                continue

            artifacts.append(artifact)

            if limit and len(artifacts) >= limit:
                break

        return artifacts

    def get_artifact_count(self) -> int:
        """Get total number of artifacts."""
        index = self._load_index()
        return len(index.get("artifacts", {}))

    def get_artifacts_summary(self) -> dict[str, Any]:
        """
        Get summary statistics about stored artifacts.

        Returns:
            Dict with counts by type, agent, date, etc.
        """
        index = self._load_index()
        artifacts = index.get("artifacts", {})

        by_type: dict[str, int] = {}
        by_agent: dict[str, int] = {}
        total_original_value = 0.0

        for artifact_info in artifacts.values():
            # Count by type
            artifact_type = artifact_info.get("type", "unknown")
            by_type[artifact_type] = by_type.get(artifact_type, 0) + 1

            # Count by agent
            agent_type = artifact_info.get("agent_type", "unknown")
            by_agent[agent_type] = by_agent.get(agent_type, 0) + 1

            # Sum original values
            total_original_value += artifact_info.get("value_usd", 0.0)

        return {
            "total_count": len(artifacts),
            "by_type": by_type,
            "by_agent": by_agent,
            "by_spec_count": len(index.get("by_spec", {})),
            "by_trace_count": len(index.get("by_trace", {})),
            "total_original_value": total_original_value,
        }

    def refresh_index(self) -> None:
        """Clear cached index and reload from disk."""
        self._index = None
        self._load_index()

    def _save_index(self) -> bool:
        """Save the artifact index to disk."""
        if self._index is None:
            return False

        try:
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
            self.index_file.write_text(json.dumps(self._index, indent=2, default=str))
            return True
        except OSError:
            return False

    def get_artifact_by_id(self, artifact_id: str) -> dict[str, Any] | None:
        """
        Alias for get_artifact. Get a single artifact by ID.

        Args:
            artifact_id: Artifact ID (e.g., "art_abc123...")

        Returns:
            Artifact dict or None if not found
        """
        return self.get_artifact(artifact_id)

    def update_artifact(self, artifact_id: str, updates: dict[str, Any]) -> bool:
        """
        Update an artifact with new values.

        Args:
            artifact_id: Artifact ID to update
            updates: Dict of fields to update

        Returns:
            True if successful, False otherwise
        """
        index = self._load_index()
        artifact_info = index.get("artifacts", {}).get(artifact_id)

        if not artifact_info:
            return False

        # Get storage path
        storage_path = artifact_info.get("storage_path")
        if not storage_path:
            # Update in index only
            index["artifacts"][artifact_id].update(updates)
            return self._save_index()

        # Load full artifact from storage
        full_path = self.project_dir / storage_path
        if not full_path.exists():
            return False

        try:
            artifact = json.loads(full_path.read_text())
            artifact.update(updates)

            # Save back to storage
            full_path.write_text(json.dumps(artifact, indent=2, default=str))

            # Also update index info if relevant fields changed
            index_fields = ["type", "value_usd", "status", "quality_score"]
            for field in index_fields:
                if field in updates:
                    index["artifacts"][artifact_id][field] = updates[field]

            self._save_index()
            return True
        except (json.JSONDecodeError, OSError):
            return False

    def delete_artifact(self, artifact_id: str) -> bool:
        """
        Delete an artifact.

        Args:
            artifact_id: Artifact ID to delete

        Returns:
            True if successful, False otherwise
        """
        index = self._load_index()
        artifact_info = index.get("artifacts", {}).get(artifact_id)

        if not artifact_info:
            return False

        # Remove from storage file
        storage_path = artifact_info.get("storage_path")
        if storage_path:
            full_path = self.project_dir / storage_path
            if full_path.exists():
                try:
                    full_path.unlink()
                except OSError:
                    pass  # Continue even if file deletion fails

        # Remove from index
        if artifact_id in index.get("artifacts", {}):
            del index["artifacts"][artifact_id]

        # Remove from by_spec
        spec_id = artifact_info.get("spec_id")
        if spec_id and spec_id in index.get("by_spec", {}):
            if artifact_id in index["by_spec"][spec_id]:
                index["by_spec"][spec_id].remove(artifact_id)

        # Remove from by_trace
        trace_id = artifact_info.get("trace_id")
        if trace_id and trace_id in index.get("by_trace", {}):
            if artifact_id in index["by_trace"][trace_id]:
                index["by_trace"][trace_id].remove(artifact_id)

        # Remove from by_date
        created_at = artifact_info.get("created_at", "")
        if created_at:
            date_str = created_at[:10]  # YYYY-MM-DD
            if date_str in index.get("by_date", {}):
                if artifact_id in index["by_date"][date_str]:
                    index["by_date"][date_str].remove(artifact_id)

        return self._save_index()


def create_consumer(project_dir: Path | str) -> ArtifactConsumer:
    """Factory function to create an ArtifactConsumer."""
    return ArtifactConsumer(project_dir)
