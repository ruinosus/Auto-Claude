"""
Tests for ROI Engine Core Models.

Tests cover:
- Role and Seniority enums
- ArtifactValue dataclass with value calculation
- ROIResult dataclass and serialization
- ROISummary factory method
"""

from datetime import datetime

import pytest

from core.models import (
    Role,
    Seniority,
    ArtifactValue,
    ROIResult,
    ROISummary,
)


class TestRoleEnum:
    """Tests for Role enum."""

    def test_role_values(self):
        """All expected roles are defined."""
        assert Role.DEVELOPER.value == "developer"
        assert Role.QA.value == "qa"
        assert Role.DEVOPS.value == "devops"
        assert Role.PM.value == "pm"
        assert Role.ARCHITECT.value == "architect"
        assert Role.TECH_LEAD.value == "tech_lead"

    def test_role_count(self):
        """Six roles are defined."""
        assert len(Role) == 6


class TestSeniorityEnum:
    """Tests for Seniority enum."""

    def test_seniority_values(self):
        """All expected seniority levels are defined."""
        assert Seniority.JUNIOR.value == "junior"
        assert Seniority.MID.value == "mid"
        assert Seniority.SENIOR.value == "senior"
        assert Seniority.STAFF.value == "staff"
        assert Seniority.PRINCIPAL.value == "principal"

    def test_seniority_count(self):
        """Five seniority levels are defined."""
        assert len(Seniority) == 5


class TestArtifactValue:
    """Tests for ArtifactValue dataclass."""

    def test_basic_creation(self):
        """Create artifact with minimal required fields."""
        artifact = ArtifactValue(
            artifact_id="art_123",
            artifact_type="diagram",
            content="graph TD\n  A --> B",
        )
        assert artifact.artifact_id == "art_123"
        assert artifact.artifact_type == "diagram"
        assert artifact.content == "graph TD\n  A --> B"

    def test_default_values(self):
        """Default values are set correctly."""
        artifact = ArtifactValue(
            artifact_id="art_123",
            artifact_type="diagram",
            content="content",
        )
        assert artifact.trace_id is None
        assert artifact.spec_id is None
        assert artifact.agent_type == ""
        assert artifact.role == Role.DEVELOPER
        assert artifact.seniority == Seniority.SENIOR
        assert artifact.hourly_rate == 150.0
        assert artifact.estimated_hours == 1.0
        assert artifact.original_value == 0.0
        assert artifact.value_source == "default"
        assert artifact.metadata == {}

    def test_post_init_calculates_value(self):
        """Value is calculated from rate × hours in post_init."""
        artifact = ArtifactValue(
            artifact_id="art_123",
            artifact_type="diagram",
            content="content",
            hourly_rate=200.0,
            estimated_hours=2.5,
        )
        # 200 * 2.5 = 500
        assert artifact.calculated_value == 500.0

    def test_explicit_calculated_value_preserved(self):
        """Explicit calculated_value is preserved if non-zero."""
        artifact = ArtifactValue(
            artifact_id="art_123",
            artifact_type="diagram",
            content="content",
            hourly_rate=200.0,
            estimated_hours=2.5,
            calculated_value=999.0,
        )
        # Explicit value should be preserved
        assert artifact.calculated_value == 999.0

    def test_full_artifact_creation(self):
        """Create artifact with all fields."""
        created = datetime(2024, 1, 15, 10, 30, 0)
        artifact = ArtifactValue(
            artifact_id="art_full",
            artifact_type="spec_document",
            content="# Feature Spec\n\nThis is a spec.",
            trace_id="trace_abc",
            spec_id="001-feature",
            agent_type="planner",
            created_at=created,
            role=Role.TECH_LEAD,
            seniority=Seniority.STAFF,
            hourly_rate=175.0 * 1.15,  # Staff rate with tech lead multiplier
            estimated_hours=3.0,
            original_value=200,
            value_source="squad_config",
            metadata={"complexity": "high"},
        )
        assert artifact.spec_id == "001-feature"
        assert artifact.role == Role.TECH_LEAD
        assert artifact.seniority == Seniority.STAFF
        assert artifact.calculated_value == 175.0 * 1.15 * 3.0
        assert artifact.metadata["complexity"] == "high"


class TestROIResult:
    """Tests for ROIResult dataclass."""

    def test_basic_creation(self):
        """Create ROI result with minimal required fields."""
        result = ROIResult(
            scope="spec",
            scope_id="001-feature",
        )
        assert result.scope == "spec"
        assert result.scope_id == "001-feature"
        assert result.total_artifact_value == 0.0
        assert result.artifact_count == 0
        assert result.by_role == {}
        assert result.by_type == {}

    def test_full_result_creation(self, sample_valued_artifacts):
        """Create full ROI result with artifacts."""
        result = ROIResult(
            scope="spec",
            scope_id="001-test",
            total_artifact_value=856.25,  # 300 + 431.25 + 125
            artifact_count=3,
            by_role={
                Role.ARCHITECT.value: 300.0,
                Role.TECH_LEAD.value: 431.25,
                Role.DEVELOPER.value: 125.0,
            },
            by_type={
                "diagram": 300.0,
                "spec_document": 431.25,
                "code_example": 125.0,
            },
            token_cost=0.85,
            net_value=855.40,
            roi_percentage=100635.29,
            artifacts=sample_valued_artifacts,
        )
        assert result.total_artifact_value == 856.25
        assert result.artifact_count == 3
        assert len(result.artifacts) == 3
        assert result.roi_percentage > 100000

    def test_to_dict_serialization(self):
        """to_dict produces correct output for serialization."""
        result = ROIResult(
            scope="trace",
            scope_id="trace_123",
            total_artifact_value=500.0,
            artifact_count=2,
            by_role={"developer": 300.0, "architect": 200.0},
            by_type={"code_example": 300.0, "diagram": 200.0},
            token_cost=0.50,
            net_value=499.50,
            roi_percentage=99900.0,
            squad_config_id="default",
        )

        data = result.to_dict()

        assert data["scope"] == "trace"
        assert data["scope_id"] == "trace_123"
        assert data["total_artifact_value"] == 500.0
        assert data["artifact_count"] == 2
        assert data["by_role"]["developer"] == 300.0
        assert data["token_cost"] == 0.50
        assert data["net_value"] == 499.50
        assert data["roi_percentage"] == 99900.0
        assert "calculated_at" in data
        assert data["squad_config_id"] == "default"

    def test_to_dict_datetime_format(self):
        """to_dict formats datetime as ISO string."""
        fixed_time = datetime(2024, 6, 15, 14, 30, 45)
        result = ROIResult(
            scope="spec",
            scope_id="001",
            calculated_at=fixed_time,
        )

        data = result.to_dict()
        assert data["calculated_at"] == "2024-06-15T14:30:45"


class TestROISummary:
    """Tests for ROISummary dataclass."""

    def test_basic_creation(self):
        """Create summary with required fields."""
        summary = ROISummary(
            total_value=1000.0,
            total_cost=1.00,
            net_value=999.0,
            roi_percentage=99900.0,
            artifact_count=5,
        )
        assert summary.total_value == 1000.0
        assert summary.total_cost == 1.00
        assert summary.roi_percentage == 99900.0
        assert summary.top_role is None
        assert summary.top_artifact_type is None

    def test_from_roi_result_basic(self):
        """Create summary from ROI result."""
        result = ROIResult(
            scope="spec",
            scope_id="001",
            total_artifact_value=500.0,
            artifact_count=3,
            by_role={
                "architect": 200.0,
                "developer": 150.0,
                "tech_lead": 150.0,
            },
            by_type={
                "diagram": 200.0,
                "code_example": 150.0,
                "spec_document": 150.0,
            },
            token_cost=0.50,
            net_value=499.50,
            roi_percentage=99900.0,
        )

        summary = ROISummary.from_roi_result(result)

        assert summary.total_value == 500.0
        assert summary.total_cost == 0.50
        assert summary.net_value == 499.50
        assert summary.roi_percentage == 99900.0
        assert summary.artifact_count == 3
        assert summary.top_role == "architect"
        assert summary.top_role_value == 200.0
        assert summary.top_artifact_type == "diagram"
        assert summary.top_artifact_type_value == 200.0

    def test_from_roi_result_empty(self):
        """Create summary from empty ROI result."""
        result = ROIResult(
            scope="spec",
            scope_id="001",
            total_artifact_value=0.0,
            artifact_count=0,
            by_role={},
            by_type={},
            token_cost=0.0,
            net_value=0.0,
            roi_percentage=0.0,
        )

        summary = ROISummary.from_roi_result(result)

        assert summary.total_value == 0.0
        assert summary.artifact_count == 0
        assert summary.top_role is None
        assert summary.top_role_value == 0.0
        assert summary.top_artifact_type is None
        assert summary.top_artifact_type_value == 0.0

    def test_from_roi_result_single_contributor(self):
        """Summary identifies single role/type as top."""
        result = ROIResult(
            scope="trace",
            scope_id="trace_001",
            total_artifact_value=300.0,
            artifact_count=1,
            by_role={"developer": 300.0},
            by_type={"code_implementation": 300.0},
            token_cost=0.30,
            net_value=299.70,
            roi_percentage=99900.0,
        )

        summary = ROISummary.from_roi_result(result)

        assert summary.top_role == "developer"
        assert summary.top_role_value == 300.0
        assert summary.top_artifact_type == "code_implementation"
        assert summary.top_artifact_type_value == 300.0
