"""
Pytest configuration and fixtures for ROI Engine tests.
"""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# Add the roi_engine to the path
roi_engine_path = Path(__file__).parent.parent
if str(roi_engine_path) not in sys.path:
    sys.path.insert(0, str(roi_engine_path))

from core.models import Role, Seniority, ArtifactValue, ROIResult


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with artifact storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Create .auto-claude/artifacts structure
        artifacts_dir = project_dir / ".auto-claude" / "artifacts"
        artifacts_dir.mkdir(parents=True)

        # Create index.json
        index = {
            "by_spec": {},
            "by_trace": {},
            "by_date": {},
            "by_type": {},
        }
        (artifacts_dir / "index.json").write_text(json.dumps(index))

        yield project_dir


@pytest.fixture
def sample_artifact_dict():
    """Sample artifact dictionary as stored in artifact_storage."""
    return {
        "id": "art_test123",
        "type": "diagram",
        "content": "graph TD\n  A[Start] --> B[End]",
        "description": "Test diagram",
        "value_usd": 150,
        "tab": "techlead",
        "format": "mermaid",
        "created_at": datetime.now().isoformat(),
        "spec_id": "001-test",
        "trace_id": "trace_abc123",
        "agent_type": "planner",
    }


@pytest.fixture
def sample_artifacts():
    """List of sample artifacts for testing aggregation."""
    return [
        {
            "id": "art_1",
            "type": "diagram",
            "content": "graph TD\n  A --> B",
            "description": "Architecture diagram",
            "value_usd": 150,
            "tab": "techlead",
            "spec_id": "001-test",
        },
        {
            "id": "art_2",
            "type": "spec_document",
            "content": "# Spec\n\nThis is a spec.",
            "description": "Feature spec",
            "value_usd": 200,
            "tab": "techlead",
            "spec_id": "001-test",
        },
        {
            "id": "art_3",
            "type": "code_example",
            "content": "def hello():\n    print('Hello')",
            "description": "Code example",
            "value_usd": 50,
            "tab": "dev",
            "spec_id": "001-test",
        },
        {
            "id": "art_4",
            "type": "test_case",
            "content": "def test_hello():\n    assert True",
            "description": "Test case",
            "value_usd": 75,
            "tab": "dev",
            "spec_id": "001-test",
        },
        {
            "id": "art_5",
            "type": "security_finding",
            "content": "SQL injection vulnerability found",
            "description": "Security issue",
            "value_usd": 200,
            "tab": "ops",
            "spec_id": "001-test",
        },
    ]


@pytest.fixture
def sample_valued_artifacts():
    """List of ArtifactValue objects for testing."""
    return [
        ArtifactValue(
            artifact_id="art_1",
            artifact_type="diagram",
            content="graph TD\n  A --> B",
            role=Role.ARCHITECT,
            seniority=Seniority.SENIOR,
            hourly_rate=150.0,
            estimated_hours=2.0,
            calculated_value=300.0,
            original_value=150,
        ),
        ArtifactValue(
            artifact_id="art_2",
            artifact_type="spec_document",
            content="# Spec",
            role=Role.TECH_LEAD,
            seniority=Seniority.SENIOR,
            hourly_rate=143.75,
            estimated_hours=3.0,
            calculated_value=431.25,
            original_value=200,
        ),
        ArtifactValue(
            artifact_id="art_3",
            artifact_type="code_example",
            content="def hello(): pass",
            role=Role.DEVELOPER,
            seniority=Seniority.SENIOR,
            hourly_rate=125.0,
            estimated_hours=1.0,
            calculated_value=125.0,
            original_value=50,
        ),
    ]


@pytest.fixture
def sample_squad_config():
    """Sample squad configuration dictionary."""
    return {
        "id": "test-squad",
        "name": "Test Squad",
        "default_seniority": "senior",
        "roles": {
            "developer": {"multiplier": 1.0},
            "qa": {"multiplier": 0.9},
            "devops": {"multiplier": 1.1},
            "pm": {"multiplier": 0.95},
            "architect": {"multiplier": 1.2},
            "tech_lead": {"multiplier": 1.15},
        },
        "seniority_rates": {
            "junior": 50,
            "mid": 75,
            "senior": 125,
            "staff": 175,
            "principal": 225,
        },
    }


@pytest.fixture
def temp_project_with_artifacts(temp_project_dir, sample_artifacts):
    """Create a temp project with artifacts in storage."""
    artifacts_dir = temp_project_dir / ".auto-claude" / "artifacts"
    today = datetime.now().strftime("%Y-%m-%d")
    day_dir = artifacts_dir / today
    day_dir.mkdir(parents=True, exist_ok=True)

    # Build index structure matching what ArtifactConsumer expects
    index = {
        "artifacts": {},  # Maps artifact_id -> artifact info with storage_path
        "by_spec": {"001-test": []},
        "by_trace": {},
        "by_date": {today: []},
        "by_type": {},
    }

    for artifact in sample_artifacts:
        artifact_id = artifact["id"]
        relative_path = f".auto-claude/artifacts/{today}/{artifact_id}.json"
        artifact_path = day_dir / f"{artifact_id}.json"

        # Add created_at if not present
        if "created_at" not in artifact:
            artifact["created_at"] = datetime.now().isoformat()

        artifact_path.write_text(json.dumps(artifact))

        # Add to main artifacts index with storage path
        index["artifacts"][artifact_id] = {
            "id": artifact_id,
            "type": artifact["type"],
            "storage_path": relative_path,
            "spec_id": artifact.get("spec_id", "001-test"),
            "value_usd": artifact.get("value_usd", 0),
        }

        # Update other indices
        index["by_spec"]["001-test"].append(artifact_id)
        index["by_date"][today].append(artifact_id)

        artifact_type = artifact["type"]
        if artifact_type not in index["by_type"]:
            index["by_type"][artifact_type] = []
        index["by_type"][artifact_type].append(artifact_id)

    # Save index
    (artifacts_dir / "index.json").write_text(json.dumps(index))

    return temp_project_dir
