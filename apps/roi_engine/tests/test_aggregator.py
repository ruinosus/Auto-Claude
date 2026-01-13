"""
Tests for ROI Aggregator.

Tests cover:
- calculate_roi with valued artifacts
- calculate_roi_for_spec integration with consumer
- aggregate_by_role detailed breakdown
- aggregate_by_type detailed breakdown
"""

import pytest

from core.aggregator import (
    calculate_roi,
    calculate_roi_for_spec,
    aggregate_by_role,
    aggregate_by_type,
)
from core.models import ArtifactValue, Role, Seniority


class TestCalculateROI:
    """Tests for calculate_roi function."""

    def test_empty_artifacts(self):
        """Empty artifacts list returns zero ROI."""
        result = calculate_roi(
            artifacts=[],
            token_cost=1.00,
            scope="spec",
            scope_id="001-test",
        )

        assert result.total_artifact_value == 0.0
        assert result.artifact_count == 0
        assert result.net_value == -1.00  # Lost the token cost
        assert result.roi_percentage == -100.0  # -100% (lost everything)
        assert result.by_role == {}
        assert result.by_type == {}

    def test_single_artifact(self):
        """Single artifact calculates correct ROI."""
        artifact = ArtifactValue(
            artifact_id="art_001",
            artifact_type="diagram",
            content="graph TD",
            role=Role.ARCHITECT,
            hourly_rate=150.0,
            estimated_hours=2.0,
            calculated_value=300.0,
        )

        result = calculate_roi(
            artifacts=[artifact],
            token_cost=0.50,
            scope="trace",
            scope_id="trace_123",
        )

        assert result.total_artifact_value == 300.0
        assert result.artifact_count == 1
        assert result.token_cost == 0.50
        assert result.net_value == 299.50
        assert result.roi_percentage == 59900.0  # (299.50 / 0.50) * 100

    def test_multiple_artifacts(self, sample_valued_artifacts):
        """Multiple artifacts are summed correctly."""
        result = calculate_roi(
            artifacts=sample_valued_artifacts,
            token_cost=0.85,
            scope="spec",
            scope_id="001-feature",
        )

        # 300 + 431.25 + 125 = 856.25
        assert result.total_artifact_value == 856.25
        assert result.artifact_count == 3
        assert result.net_value == 855.40  # 856.25 - 0.85
        assert round(result.roi_percentage, 2) == 100635.29  # (855.40 / 0.85) * 100

    def test_by_role_grouping(self, sample_valued_artifacts):
        """Artifacts are grouped by role correctly."""
        result = calculate_roi(
            artifacts=sample_valued_artifacts,
            token_cost=1.0,
            scope="spec",
            scope_id="001",
        )

        assert result.by_role["architect"] == 300.0
        assert result.by_role["tech_lead"] == 431.25
        assert result.by_role["developer"] == 125.0

    def test_by_type_grouping(self, sample_valued_artifacts):
        """Artifacts are grouped by type correctly."""
        result = calculate_roi(
            artifacts=sample_valued_artifacts,
            token_cost=1.0,
            scope="spec",
            scope_id="001",
        )

        assert result.by_type["diagram"] == 300.0
        assert result.by_type["spec_document"] == 431.25
        assert result.by_type["code_example"] == 125.0

    def test_zero_token_cost(self, sample_valued_artifacts):
        """Zero token cost doesn't cause division error."""
        result = calculate_roi(
            artifacts=sample_valued_artifacts,
            token_cost=0.0,
            scope="spec",
            scope_id="001",
        )

        assert result.roi_percentage == 0  # Avoid division by zero

    def test_negative_roi(self):
        """High cost vs low value produces negative ROI."""
        artifact = ArtifactValue(
            artifact_id="art_low",
            artifact_type="code_example",
            content="x = 1",
            calculated_value=10.0,  # Only $10 value
        )

        result = calculate_roi(
            artifacts=[artifact],
            token_cost=100.0,  # But cost $100
            scope="trace",
            scope_id="trace_001",
        )

        assert result.net_value == -90.0  # Lost $90
        assert result.roi_percentage == -90.0  # -90% ROI

    def test_scope_and_id_preserved(self):
        """Scope and scope_id are preserved in result."""
        result = calculate_roi(
            artifacts=[],
            token_cost=0.0,
            scope="project",
            scope_id="my-project",
        )

        assert result.scope == "project"
        assert result.scope_id == "my-project"

    def test_squad_config_id_preserved(self):
        """Squad config ID is preserved in result."""
        result = calculate_roi(
            artifacts=[],
            token_cost=0.0,
            scope="spec",
            scope_id="001",
            squad_config_id="custom-squad",
        )

        assert result.squad_config_id == "custom-squad"

    def test_artifacts_included_in_result(self, sample_valued_artifacts):
        """Valued artifacts are included in result."""
        result = calculate_roi(
            artifacts=sample_valued_artifacts,
            token_cost=0.50,
            scope="spec",
            scope_id="001",
        )

        assert result.artifacts == sample_valued_artifacts
        assert len(result.artifacts) == 3


class TestCalculateROIForSpec:
    """Tests for calculate_roi_for_spec integration."""

    def test_with_artifacts_in_storage(self, temp_project_with_artifacts):
        """Calculates ROI from artifacts in storage."""
        result = calculate_roi_for_spec(
            spec_id="001-test",
            project_dir=temp_project_with_artifacts,
            token_cost=0.50,
        )

        assert result.scope == "spec"
        assert result.scope_id == "001-test"
        assert result.artifact_count == 5  # From sample_artifacts fixture
        assert result.total_artifact_value > 0

    def test_with_no_artifacts(self, temp_project_dir):
        """Empty spec returns zero value."""
        result = calculate_roi_for_spec(
            spec_id="nonexistent-spec",
            project_dir=temp_project_dir,
            token_cost=1.0,
        )

        assert result.artifact_count == 0
        assert result.total_artifact_value == 0.0
        assert result.roi_percentage == -100.0  # All cost, no value

    def test_values_based_on_artifact_types(self, temp_project_with_artifacts):
        """Values are calculated based on artifact types."""
        result = calculate_roi_for_spec(
            spec_id="001-test",
            project_dir=temp_project_with_artifacts,
            token_cost=0.0,
        )

        # Check that roles are properly assigned
        # From sample_artifacts: diagram, spec_document, code_example, test_case, security_finding
        assert "architect" in result.by_role  # diagram
        assert "tech_lead" in result.by_role  # spec_document
        assert "developer" in result.by_role  # code_example
        assert "qa" in result.by_role  # test_case
        assert "devops" in result.by_role  # security_finding


class TestAggregateByRole:
    """Tests for aggregate_by_role function."""

    def test_empty_list(self):
        """Empty list returns empty dict."""
        result = aggregate_by_role([])
        assert result == {}

    def test_single_artifact(self):
        """Single artifact creates single role entry."""
        artifact = ArtifactValue(
            artifact_id="art_001",
            artifact_type="diagram",
            content="graph",
            role=Role.ARCHITECT,
            estimated_hours=2.0,
            calculated_value=300.0,
        )

        result = aggregate_by_role([artifact])

        assert len(result) == 1
        assert "architect" in result
        assert result["architect"]["total_value"] == 300.0
        assert result["architect"]["count"] == 1
        assert result["architect"]["total_hours"] == 2.0
        assert result["architect"]["avg_value"] == 300.0
        assert result["architect"]["avg_hours"] == 2.0

    def test_multiple_artifacts_same_role(self):
        """Multiple artifacts for same role are aggregated."""
        artifacts = [
            ArtifactValue(
                artifact_id="art_1",
                artifact_type="diagram",
                content="a",
                role=Role.ARCHITECT,
                estimated_hours=2.0,
                calculated_value=300.0,
            ),
            ArtifactValue(
                artifact_id="art_2",
                artifact_type="system_design",
                content="b",
                role=Role.ARCHITECT,
                estimated_hours=4.0,
                calculated_value=600.0,
            ),
        ]

        result = aggregate_by_role(artifacts)

        assert len(result) == 1
        assert result["architect"]["total_value"] == 900.0
        assert result["architect"]["count"] == 2
        assert result["architect"]["total_hours"] == 6.0
        assert result["architect"]["avg_value"] == 450.0
        assert result["architect"]["avg_hours"] == 3.0

    def test_multiple_roles(self, sample_valued_artifacts):
        """Artifacts are grouped by their roles."""
        result = aggregate_by_role(sample_valued_artifacts)

        assert len(result) == 3  # architect, tech_lead, developer
        assert "architect" in result
        assert "tech_lead" in result
        assert "developer" in result

    def test_artifact_types_tracked(self):
        """Artifact types within each role are tracked."""
        artifacts = [
            ArtifactValue(
                artifact_id="art_1",
                artifact_type="diagram",
                content="a",
                role=Role.ARCHITECT,
                calculated_value=300.0,
            ),
            ArtifactValue(
                artifact_id="art_2",
                artifact_type="diagram",
                content="b",
                role=Role.ARCHITECT,
                calculated_value=300.0,
            ),
            ArtifactValue(
                artifact_id="art_3",
                artifact_type="system_design",
                content="c",
                role=Role.ARCHITECT,
                calculated_value=600.0,
            ),
        ]

        result = aggregate_by_role(artifacts)

        assert result["architect"]["artifact_types"]["diagram"] == 2
        assert result["architect"]["artifact_types"]["system_design"] == 1


class TestAggregateByType:
    """Tests for aggregate_by_type function."""

    def test_empty_list(self):
        """Empty list returns empty dict."""
        result = aggregate_by_type([])
        assert result == {}

    def test_single_artifact(self):
        """Single artifact creates single type entry."""
        artifact = ArtifactValue(
            artifact_id="art_001",
            artifact_type="diagram",
            content="graph",
            role=Role.ARCHITECT,
            estimated_hours=2.0,
            calculated_value=300.0,
        )

        result = aggregate_by_type([artifact])

        assert len(result) == 1
        assert "diagram" in result
        assert result["diagram"]["total_value"] == 300.0
        assert result["diagram"]["count"] == 1
        assert result["diagram"]["role"] == "architect"
        assert result["diagram"]["estimated_hours"] == 2.0
        assert result["diagram"]["avg_value"] == 300.0

    def test_multiple_same_type(self):
        """Multiple artifacts of same type are aggregated."""
        artifacts = [
            ArtifactValue(
                artifact_id="art_1",
                artifact_type="diagram",
                content="a",
                role=Role.ARCHITECT,
                calculated_value=300.0,
            ),
            ArtifactValue(
                artifact_id="art_2",
                artifact_type="diagram",
                content="b",
                role=Role.ARCHITECT,
                calculated_value=350.0,
            ),
        ]

        result = aggregate_by_type(artifacts)

        assert result["diagram"]["total_value"] == 650.0
        assert result["diagram"]["count"] == 2
        assert result["diagram"]["avg_value"] == 325.0

    def test_different_types(self, sample_valued_artifacts):
        """Different artifact types are tracked separately."""
        result = aggregate_by_type(sample_valued_artifacts)

        assert len(result) == 3
        assert "diagram" in result
        assert "spec_document" in result
        assert "code_example" in result

        # Each type has correct values
        assert result["diagram"]["total_value"] == 300.0
        assert result["spec_document"]["total_value"] == 431.25
        assert result["code_example"]["total_value"] == 125.0
