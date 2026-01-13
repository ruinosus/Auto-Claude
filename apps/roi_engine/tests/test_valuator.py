"""
Tests for Artifact Valuator.

Tests cover:
- calculate_artifact_value with various artifact types
- Squad config integration and seniority overrides
- valuate_artifacts batch processing
- get_artifact_value_preview for UI
- compare_valuations for migration
"""

from datetime import datetime

from core.config import SquadConfigWrapper
from core.models import Role, Seniority
from core.valuator import (
    calculate_artifact_value,
    valuate_artifacts,
    get_artifact_value_preview,
    compare_valuations,
)


class TestCalculateArtifactValue:
    """Tests for calculate_artifact_value function."""

    def test_diagram_artifact_architect_role(self):
        """Diagram artifact is assigned to ARCHITECT role."""
        artifact = {
            "id": "art_001",
            "type": "diagram",
            "content": "graph TD\n  A --> B",
        }

        result = calculate_artifact_value(artifact)

        assert result.artifact_id == "art_001"
        assert result.artifact_type == "diagram"
        assert result.role == Role.ARCHITECT
        # Senior Architect: $125 * 1.2 = $150/hr, 2.0 hours = $300
        assert result.estimated_hours == 2.0
        assert result.hourly_rate == 150.0  # 125 * 1.2
        assert result.calculated_value == 300.0

    def test_code_example_developer_role(self):
        """Code example artifact is assigned to DEVELOPER role."""
        artifact = {
            "id": "art_002",
            "type": "code_example",
            "content": "def hello(): print('Hello')",
        }

        result = calculate_artifact_value(artifact)

        assert result.role == Role.DEVELOPER
        # Senior Developer: $125 * 1.0 = $125/hr, 1.0 hour = $125
        assert result.estimated_hours == 1.0
        assert result.hourly_rate == 125.0
        assert result.calculated_value == 125.0

    def test_spec_document_tech_lead_role(self):
        """Spec document is assigned to TECH_LEAD role."""
        artifact = {
            "id": "art_003",
            "type": "spec_document",
            "content": "# Feature Spec",
        }

        result = calculate_artifact_value(artifact)

        assert result.role == Role.TECH_LEAD
        # Senior Tech Lead: $125 * 1.15 = $143.75/hr, 3.0 hours = $431.25
        assert result.estimated_hours == 3.0
        assert result.hourly_rate == 143.75
        assert result.calculated_value == 431.25

    def test_test_case_qa_role(self):
        """Test case artifact is assigned to QA role."""
        artifact = {
            "id": "art_004",
            "type": "test_case",
            "content": "def test_feature(): assert True",
        }

        result = calculate_artifact_value(artifact)

        assert result.role == Role.QA
        # Senior QA: $125 * 0.9 = $112.50/hr, 0.5 hours = $56.25
        assert result.estimated_hours == 0.5
        assert result.hourly_rate == 112.5
        assert result.calculated_value == 56.25

    def test_security_finding_devops_role(self):
        """Security finding is assigned to DEVOPS role."""
        artifact = {
            "id": "art_005",
            "type": "security_finding",
            "content": "SQL injection vulnerability",
        }

        result = calculate_artifact_value(artifact)

        assert result.role == Role.DEVOPS
        # Senior DevOps: $125 * 1.1 = $137.50/hr, 1.0 hour = $137.50
        assert result.estimated_hours == 1.0
        assert result.hourly_rate == 137.5
        assert result.calculated_value == 137.5

    def test_recommendation_pm_role(self):
        """Recommendation artifact is assigned to PM role."""
        artifact = {
            "id": "art_006",
            "type": "recommendation",
            "content": "Recommend using React for frontend",
        }

        result = calculate_artifact_value(artifact)

        assert result.role == Role.PM
        # Senior PM: $125 * 0.95 = $118.75/hr, 1.0 hour = $118.75
        assert result.estimated_hours == 1.0
        assert result.hourly_rate == 118.75
        assert result.calculated_value == 118.75

    def test_unknown_artifact_type_default(self):
        """Unknown artifact type uses default (DEVELOPER, 1 hour)."""
        artifact = {
            "id": "art_007",
            "type": "unknown_custom_type",
            "content": "Some content",
        }

        result = calculate_artifact_value(artifact)

        assert result.role == Role.DEVELOPER
        assert result.estimated_hours == 1.0
        assert result.hourly_rate == 125.0
        assert result.calculated_value == 125.0

    def test_case_insensitive_type(self):
        """Artifact type matching is case-insensitive."""
        artifact = {
            "id": "art_008",
            "type": "DIAGRAM",
            "content": "content",
        }

        result = calculate_artifact_value(artifact)

        assert result.role == Role.ARCHITECT
        assert result.artifact_type == "diagram"

    def test_preserves_artifact_metadata(self):
        """Original artifact fields are preserved."""
        artifact = {
            "id": "art_009",
            "type": "code_example",
            "content": "code content here",
            "trace_id": "trace_123",
            "spec_id": "001-feature",
            "agent_type": "coder",
            "metadata": {"complexity": "high"},
        }

        result = calculate_artifact_value(artifact)

        assert result.artifact_id == "art_009"
        assert result.content == "code content here"
        assert result.trace_id == "trace_123"
        assert result.spec_id == "001-feature"
        assert result.agent_type == "coder"
        assert result.metadata == {"complexity": "high"}

    def test_parses_string_created_at(self):
        """Parses ISO format string for created_at."""
        artifact = {
            "id": "art_010",
            "type": "diagram",
            "content": "content",
            "created_at": "2024-06-15T14:30:00",
        }

        result = calculate_artifact_value(artifact)

        assert result.created_at == datetime(2024, 6, 15, 14, 30, 0)

    def test_preserves_original_value(self):
        """Original value_usd is preserved for comparison."""
        artifact = {
            "id": "art_011",
            "type": "diagram",
            "content": "content",
            "value_usd": 150,  # Original fixed value
        }

        result = calculate_artifact_value(artifact)

        assert result.original_value == 150
        assert result.calculated_value == 300.0  # New role-based value


class TestCalculateArtifactValueWithConfig:
    """Tests for calculate_artifact_value with custom squad config."""

    def test_with_junior_seniority(self):
        """Junior seniority uses lower base rate."""
        artifact = {
            "id": "art_020",
            "type": "code_example",
            "content": "code",
        }
        config = SquadConfigWrapper(default_seniority=Seniority.JUNIOR)

        result = calculate_artifact_value(artifact, squad_config=config)

        # Junior Developer: $50 * 1.0 = $50/hr
        assert result.seniority == Seniority.JUNIOR
        assert result.hourly_rate == 50.0
        assert result.calculated_value == 50.0

    def test_with_principal_seniority(self):
        """Principal seniority uses higher base rate."""
        artifact = {
            "id": "art_021",
            "type": "diagram",
            "content": "architecture diagram",
        }
        config = SquadConfigWrapper(default_seniority=Seniority.PRINCIPAL)

        result = calculate_artifact_value(artifact, squad_config=config)

        # Principal Architect: $225 * 1.2 = $270/hr, 2 hours = $540
        assert result.seniority == Seniority.PRINCIPAL
        assert result.hourly_rate == 270.0
        assert result.calculated_value == 540.0

    def test_seniority_override(self):
        """Seniority override takes precedence over config."""
        artifact = {
            "id": "art_022",
            "type": "code_example",
            "content": "code",
        }
        config = SquadConfigWrapper(default_seniority=Seniority.JUNIOR)

        result = calculate_artifact_value(
            artifact,
            squad_config=config,
            seniority_override=Seniority.STAFF,
        )

        # Staff Developer (override): $175 * 1.0 = $175/hr
        assert result.seniority == Seniority.STAFF
        assert result.hourly_rate == 175.0

    def test_custom_stakeholder_rates(self):
        """Custom stakeholder rates override calculated rates."""
        artifact = {
            "id": "art_023",
            "type": "diagram",
            "content": "diagram",
        }
        config = SquadConfigWrapper(
            default_seniority=Seniority.SENIOR,
            stakeholder_rates={"senior_architect": 200.0},  # Custom rate
        )

        result = calculate_artifact_value(artifact, squad_config=config)

        # Custom rate overrides calculated $150
        assert result.hourly_rate == 200.0
        assert result.calculated_value == 400.0  # 200 * 2 hours

    def test_value_source_from_config(self):
        """Value source comes from config."""
        artifact = {"id": "art_024", "type": "code_example", "content": "code"}

        # Default config
        result_default = calculate_artifact_value(artifact)
        assert result_default.value_source == "default"

        # Project config
        config = SquadConfigWrapper(source="project")
        result_project = calculate_artifact_value(artifact, squad_config=config)
        assert result_project.value_source == "project"


class TestValuateArtifacts:
    """Tests for valuate_artifacts batch processing."""

    def test_empty_list(self):
        """Empty list returns empty list."""
        result = valuate_artifacts([])
        assert result == []

    def test_single_artifact(self):
        """Single artifact is processed correctly."""
        artifacts = [
            {"id": "art_030", "type": "diagram", "content": "graph TD"}
        ]

        result = valuate_artifacts(artifacts)

        assert len(result) == 1
        assert result[0].artifact_id == "art_030"
        assert result[0].role == Role.ARCHITECT

    def test_multiple_artifacts(self, sample_artifacts):
        """Multiple artifacts are all valuated."""
        result = valuate_artifacts(sample_artifacts)

        assert len(result) == 5
        # Check each artifact was processed
        types = [a.artifact_type for a in result]
        assert "diagram" in types
        assert "spec_document" in types
        assert "code_example" in types
        assert "test_case" in types
        assert "security_finding" in types

    def test_shared_config(self, sample_artifacts):
        """All artifacts use the same squad config."""
        config = SquadConfigWrapper(
            id="test-squad",
            default_seniority=Seniority.MID,
            source="test",
        )

        result = valuate_artifacts(sample_artifacts, squad_config=config)

        # All should have mid seniority
        for artifact in result:
            assert artifact.seniority == Seniority.MID
            assert artifact.value_source == "test"

    def test_seniority_override_all(self, sample_artifacts):
        """Seniority override applies to all artifacts."""
        result = valuate_artifacts(
            sample_artifacts,
            seniority_override=Seniority.PRINCIPAL,
        )

        for artifact in result:
            assert artifact.seniority == Seniority.PRINCIPAL


class TestGetArtifactValuePreview:
    """Tests for get_artifact_value_preview."""

    def test_diagram_preview(self):
        """Preview for diagram artifact type."""
        preview = get_artifact_value_preview("diagram")

        assert preview["artifact_type"] == "diagram"
        assert preview["role"] == "architect"
        assert preview["seniority"] == "senior"
        assert preview["estimated_hours"] == 2.0
        assert preview["hourly_rate"] == 150.0
        assert preview["calculated_value"] == 300.0
        assert "$150" in preview["formula"]
        assert "2" in preview["formula"]

    def test_preview_with_seniority(self):
        """Preview respects seniority parameter."""
        preview = get_artifact_value_preview("code_example", seniority=Seniority.STAFF)

        assert preview["seniority"] == "staff"
        assert preview["hourly_rate"] == 175.0  # Staff developer rate

    def test_preview_with_custom_config(self):
        """Preview respects custom squad config."""
        config = SquadConfigWrapper(
            stakeholder_rates={"senior_architect": 200.0}
        )

        preview = get_artifact_value_preview("diagram", squad_config=config)

        assert preview["hourly_rate"] == 200.0
        assert preview["calculated_value"] == 400.0

    def test_formula_format(self):
        """Formula shows rate × hours = value."""
        preview = get_artifact_value_preview("test_case")

        # QA: $112.50/hr × 0.5hr = $56.25
        assert preview["formula"] == "$112.5/hr × 0.5hr = $56.25"


class TestCompareValuations:
    """Tests for compare_valuations migration helper."""

    def test_compare_diagram(self):
        """Compare old fixed value vs new calculated value."""
        artifact = {
            "id": "art_050",
            "type": "diagram",
            "content": "architecture diagram",
            "value_usd": 150,  # Old fixed value
        }

        comparison = compare_valuations(artifact)

        assert comparison["artifact_id"] == "art_050"
        assert comparison["artifact_type"] == "diagram"
        assert comparison["original_value"] == 150
        assert comparison["calculated_value"] == 300.0
        assert comparison["difference"] == 150.0
        assert comparison["percentage_change"] == 100.0  # 100% increase
        assert comparison["role"] == "architect"
        assert comparison["seniority"] == "senior"

    def test_compare_code_example_decrease(self):
        """Comparison shows decrease in value."""
        artifact = {
            "id": "art_051",
            "type": "code_example",
            "content": "code",
            "value_usd": 200,  # Higher than calculated
        }

        comparison = compare_valuations(artifact)

        assert comparison["original_value"] == 200
        assert comparison["calculated_value"] == 125.0
        assert comparison["difference"] == -75.0
        assert comparison["percentage_change"] == -37.5  # 37.5% decrease

    def test_compare_zero_original_value(self):
        """Zero original value doesn't cause division error."""
        artifact = {
            "id": "art_052",
            "type": "diagram",
            "content": "content",
            "value_usd": 0,
        }

        comparison = compare_valuations(artifact)

        assert comparison["original_value"] == 0
        assert comparison["calculated_value"] == 300.0
        assert comparison["percentage_change"] == 0  # Avoid division by zero

    def test_compare_includes_calculation_details(self):
        """Comparison includes all calculation details."""
        artifact = {
            "id": "art_053",
            "type": "spec_document",
            "content": "spec content",
            "value_usd": 200,
        }

        comparison = compare_valuations(artifact)

        assert comparison["hourly_rate"] == 143.75
        assert comparison["estimated_hours"] == 3.0
        assert comparison["role"] == "tech_lead"
