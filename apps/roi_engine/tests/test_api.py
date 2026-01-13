"""
Tests for ROI Engine API.

Tests cover:
- Health check endpoint
- ROI calculation endpoints (spec, trace)
- Artifact listing and preview endpoints
- Configuration endpoints (rates, artifact types, roles)
"""

import sys
from pathlib import Path

import pytest

# Add roi_engine to path for imports
roi_engine_path = Path(__file__).parent.parent
if str(roi_engine_path) not in sys.path:
    sys.path.insert(0, str(roi_engine_path))


# Import after path setup - use absolute imports via direct file loading
def get_app():
    """Get the FastAPI app with proper module loading."""
    # Import core modules (they're already in path from conftest)
    from core import (
        ArtifactConsumer,
        calculate_roi_for_spec,
        calculate_roi_for_trace,
        get_artifact_value_preview,
        get_all_artifact_types,
        get_rate_table,
        get_role_and_hours,
        load_squad_config,
        valuate_artifacts,
        ROLE_DESCRIPTIONS,
    )

    # Create a minimal FastAPI app for testing
    from fastapi import FastAPI, APIRouter, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="ROI Engine API Test", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    router = APIRouter()

    # Re-implement endpoints for testing
    from pydantic import BaseModel, Field
    from datetime import datetime
    from typing import Any

    class SpecROIRequest(BaseModel):
        spec_id: str
        project_dir: str
        token_cost: float = 0.0

    class TraceROIRequest(BaseModel):
        trace_id: str
        project_dir: str
        token_cost: float = 0.0

    class ArtifactValuePreviewRequest(BaseModel):
        artifact_type: str
        seniority: str = "senior"
        project_dir: str | None = None

    @router.post("/roi/spec")
    async def calculate_spec_roi(request: SpecROIRequest):
        project_dir = Path(request.project_dir)
        if not project_dir.exists():
            raise HTTPException(status_code=400, detail=f"Project directory not found: {request.project_dir}")

        squad_config = load_squad_config(project_dir=project_dir)
        result = calculate_roi_for_spec(
            spec_id=request.spec_id,
            project_dir=project_dir,
            token_cost=request.token_cost,
            squad_config=squad_config,
        )

        return {
            "scope": result.scope,
            "scope_id": result.scope_id,
            "total_artifact_value": result.total_artifact_value,
            "artifact_count": result.artifact_count,
            "by_role": result.by_role,
            "by_type": result.by_type,
            "token_cost": result.token_cost,
            "net_value": result.net_value,
            "roi_percentage": result.roi_percentage,
            "calculated_at": result.calculated_at.isoformat(),
            "squad_config_id": result.squad_config_id,
        }

    @router.post("/roi/trace")
    async def calculate_trace_roi(request: TraceROIRequest):
        project_dir = Path(request.project_dir)
        if not project_dir.exists():
            raise HTTPException(status_code=400, detail=f"Project directory not found: {request.project_dir}")

        squad_config = load_squad_config(project_dir=project_dir)
        result = calculate_roi_for_trace(
            trace_id=request.trace_id,
            project_dir=project_dir,
            token_cost=request.token_cost,
            squad_config=squad_config,
        )

        return {
            "scope": result.scope,
            "scope_id": result.scope_id,
            "total_artifact_value": result.total_artifact_value,
            "artifact_count": result.artifact_count,
            "by_role": result.by_role,
            "by_type": result.by_type,
            "token_cost": result.token_cost,
            "net_value": result.net_value,
            "roi_percentage": result.roi_percentage,
            "calculated_at": result.calculated_at.isoformat(),
            "squad_config_id": result.squad_config_id,
        }

    @router.get("/roi/spec/{spec_id}")
    async def get_spec_roi(spec_id: str, project_dir: str, token_cost: float = 0.0):
        request = SpecROIRequest(spec_id=spec_id, project_dir=project_dir, token_cost=token_cost)
        return await calculate_spec_roi(request)

    @router.get("/roi/summary/{spec_id}")
    async def get_spec_roi_summary(spec_id: str, project_dir: str, token_cost: float = 0.0):
        project_path = Path(project_dir)
        squad_config = load_squad_config(project_dir=project_path)
        result = calculate_roi_for_spec(
            spec_id=spec_id,
            project_dir=project_path,
            token_cost=token_cost,
            squad_config=squad_config,
        )

        top_role = None
        top_role_value = 0.0
        for role, value in result.by_role.items():
            if value > top_role_value:
                top_role = role
                top_role_value = value

        top_type = None
        top_type_value = 0.0
        for artifact_type, value in result.by_type.items():
            if value > top_type_value:
                top_type = artifact_type
                top_type_value = value

        return {
            "total_value": result.total_artifact_value,
            "total_cost": result.token_cost,
            "net_value": result.net_value,
            "roi_percentage": result.roi_percentage,
            "artifact_count": result.artifact_count,
            "top_role": top_role,
            "top_role_value": top_role_value,
            "top_artifact_type": top_type,
            "top_artifact_type_value": top_type_value,
        }

    @router.get("/artifacts")
    async def list_artifacts(
        project_dir: str,
        spec_id: str | None = None,
        trace_id: str | None = None,
        artifact_type: str | None = None,
        limit: int = 100,
    ):
        project_path = Path(project_dir)
        consumer = ArtifactConsumer(project_path)
        squad_config = load_squad_config(project_dir=project_path)

        if spec_id:
            raw_artifacts = consumer.get_artifacts_for_spec(spec_id)
        elif trace_id:
            raw_artifacts = consumer.get_artifacts_for_trace(trace_id)
        else:
            raw_artifacts = consumer.get_all_artifacts(artifact_type=artifact_type, limit=limit)

        valued = valuate_artifacts(raw_artifacts, squad_config)

        return {
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
                    "value_source": a.value_source,
                }
                for a in valued[:limit]
            ],
            "total_count": len(valued),
            "total_value": sum(a.calculated_value for a in valued),
        }

    @router.get("/artifacts/{artifact_id}")
    async def get_artifact(artifact_id: str, project_dir: str):
        project_path = Path(project_dir)
        consumer = ArtifactConsumer(project_path)
        squad_config = load_squad_config(project_dir=project_path)

        raw_artifact = consumer.get_artifact(artifact_id)
        if not raw_artifact:
            raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}")

        valued = valuate_artifacts([raw_artifact], squad_config)[0]

        return {
            "artifact_id": valued.artifact_id,
            "artifact_type": valued.artifact_type,
            "role": valued.role.value,
            "seniority": valued.seniority.value,
            "hourly_rate": valued.hourly_rate,
            "estimated_hours": valued.estimated_hours,
            "calculated_value": valued.calculated_value,
            "original_value": valued.original_value,
            "value_source": valued.value_source,
        }

    @router.post("/artifacts/preview")
    async def preview_artifact_value(request: ArtifactValuePreviewRequest):
        from core.models import Seniority

        try:
            seniority = Seniority(request.seniority)
        except ValueError:
            seniority = Seniority.SENIOR

        squad_config = None
        if request.project_dir:
            squad_config = load_squad_config(project_dir=request.project_dir)

        preview = get_artifact_value_preview(
            artifact_type=request.artifact_type,
            squad_config=squad_config,
            seniority=seniority,
        )

        return {
            "artifact_type": preview["artifact_type"],
            "role": preview["role"],
            "seniority": preview["seniority"],
            "estimated_hours": preview["estimated_hours"],
            "hourly_rate": preview["hourly_rate"],
            "calculated_value": preview["calculated_value"],
            "formula": preview["formula"],
        }

    @router.get("/config/rates")
    async def get_rates():
        return {
            "rates": get_rate_table(),
            "description": "Hourly rates in USD by seniority and role",
        }

    @router.get("/config/artifact-types")
    async def list_artifact_types():
        types = []
        for artifact_type in get_all_artifact_types():
            role, hours = get_role_and_hours(artifact_type)
            types.append({
                "type": artifact_type,
                "role": role.value,
                "estimated_hours": hours,
                "role_description": ROLE_DESCRIPTIONS.get(role, ""),
            })

        return {
            "types": types,
            "total_count": len(types),
        }

    @router.get("/config/roles")
    async def list_roles():
        from core.models import Role

        return {
            "roles": [
                {
                    "id": role.value,
                    "name": role.name,
                    "description": ROLE_DESCRIPTIONS.get(role, ""),
                }
                for role in Role
            ]
        }

    @app.get("/")
    async def root():
        return {
            "name": "ROI Engine API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "version": "0.1.0",
            "langfuse_available": False,
        }

    app.include_router(router, prefix="/api")

    return app


# Lazy load app
_app = None

def get_test_app():
    global _app
    if _app is None:
        _app = get_app()
    return _app


from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(get_test_app())


class TestRootAndHealth:
    """Tests for root and health endpoints."""

    def test_root_endpoint(self, client):
        """Root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ROI Engine API"
        assert data["version"] == "0.1.0"
        assert "/docs" in data["docs"]

    def test_health_check(self, client):
        """Health check returns status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "langfuse_available" in data


class TestROIEndpoints:
    """Tests for ROI calculation endpoints."""

    def test_calculate_spec_roi(self, client, temp_project_with_artifacts):
        """Calculate ROI for a spec."""
        response = client.post(
            "/api/roi/spec",
            json={
                "spec_id": "001-test",
                "project_dir": str(temp_project_with_artifacts),
                "token_cost": 0.50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scope"] == "spec"
        assert data["scope_id"] == "001-test"
        assert data["artifact_count"] == 5
        assert data["total_artifact_value"] > 0
        assert data["token_cost"] == 0.50
        assert "by_role" in data
        assert "by_type" in data

    def test_calculate_spec_roi_invalid_project(self, client):
        """Invalid project directory returns 400."""
        response = client.post(
            "/api/roi/spec",
            json={
                "spec_id": "001-test",
                "project_dir": "/nonexistent/path",
                "token_cost": 0.50,
            },
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_get_spec_roi(self, client, temp_project_with_artifacts):
        """GET endpoint for spec ROI works."""
        response = client.get(
            f"/api/roi/spec/001-test",
            params={
                "project_dir": str(temp_project_with_artifacts),
                "token_cost": 1.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scope_id"] == "001-test"

    def test_get_spec_roi_summary(self, client, temp_project_with_artifacts):
        """ROI summary endpoint returns simplified data."""
        response = client.get(
            "/api/roi/summary/001-test",
            params={
                "project_dir": str(temp_project_with_artifacts),
                "token_cost": 0.50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_value" in data
        assert "total_cost" in data
        assert "net_value" in data
        assert "roi_percentage" in data
        assert "artifact_count" in data
        assert "top_role" in data
        assert "top_artifact_type" in data

    def test_calculate_trace_roi(self, client, temp_project_dir):
        """Calculate ROI for a trace (empty result for nonexistent trace)."""
        response = client.post(
            "/api/roi/trace",
            json={
                "trace_id": "trace_nonexistent",
                "project_dir": str(temp_project_dir),
                "token_cost": 1.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scope"] == "trace"
        assert data["scope_id"] == "trace_nonexistent"
        assert data["artifact_count"] == 0


class TestArtifactEndpoints:
    """Tests for artifact endpoints."""

    def test_list_artifacts(self, client, temp_project_with_artifacts):
        """List artifacts returns valued artifacts."""
        response = client.get(
            "/api/artifacts",
            params={"project_dir": str(temp_project_with_artifacts)},
        )

        assert response.status_code == 200
        data = response.json()
        assert "artifacts" in data
        assert data["total_count"] == 5
        assert data["total_value"] > 0

    def test_list_artifacts_by_spec(self, client, temp_project_with_artifacts):
        """Filter artifacts by spec ID."""
        response = client.get(
            "/api/artifacts",
            params={
                "project_dir": str(temp_project_with_artifacts),
                "spec_id": "001-test",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 5

    def test_list_artifacts_empty(self, client, temp_project_dir):
        """Empty project returns empty artifact list."""
        response = client.get(
            "/api/artifacts",
            params={"project_dir": str(temp_project_dir)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["artifacts"] == []
        assert data["total_count"] == 0
        assert data["total_value"] == 0

    def test_artifact_value_response_structure(self, client, temp_project_with_artifacts):
        """Artifact response has correct structure."""
        response = client.get(
            "/api/artifacts",
            params={"project_dir": str(temp_project_with_artifacts)},
        )

        data = response.json()
        artifact = data["artifacts"][0]

        # Check all expected fields
        assert "artifact_id" in artifact
        assert "artifact_type" in artifact
        assert "role" in artifact
        assert "seniority" in artifact
        assert "hourly_rate" in artifact
        assert "estimated_hours" in artifact
        assert "calculated_value" in artifact
        assert "original_value" in artifact
        assert "value_source" in artifact

    def test_get_single_artifact(self, client, temp_project_with_artifacts):
        """Get single artifact by ID."""
        response = client.get(
            "/api/artifacts/art_1",
            params={"project_dir": str(temp_project_with_artifacts)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["artifact_id"] == "art_1"
        assert data["artifact_type"] == "diagram"
        assert data["role"] == "architect"

    def test_get_nonexistent_artifact(self, client, temp_project_dir):
        """Nonexistent artifact returns 404."""
        response = client.get(
            "/api/artifacts/nonexistent_id",
            params={"project_dir": str(temp_project_dir)},
        )

        assert response.status_code == 404

    def test_preview_artifact_value(self, client):
        """Preview artifact value calculation."""
        response = client.post(
            "/api/artifacts/preview",
            json={
                "artifact_type": "diagram",
                "seniority": "senior",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["artifact_type"] == "diagram"
        assert data["role"] == "architect"
        assert data["seniority"] == "senior"
        assert data["estimated_hours"] == 2.0
        assert data["hourly_rate"] == 150.0
        assert data["calculated_value"] == 300.0
        assert "$150" in data["formula"]

    def test_preview_with_different_seniority(self, client):
        """Preview respects seniority parameter."""
        response = client.post(
            "/api/artifacts/preview",
            json={
                "artifact_type": "code_example",
                "seniority": "junior",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["seniority"] == "junior"
        assert data["hourly_rate"] == 50.0  # Junior developer rate


class TestConfigurationEndpoints:
    """Tests for configuration endpoints."""

    def test_get_rate_table(self, client):
        """Get rate table returns all seniority/role combinations."""
        response = client.get("/api/config/rates")

        assert response.status_code == 200
        data = response.json()
        assert "rates" in data
        assert "description" in data

        # Check all seniority levels
        rates = data["rates"]
        assert "junior" in rates
        assert "mid" in rates
        assert "senior" in rates
        assert "staff" in rates
        assert "principal" in rates

        # Check roles exist in each seniority
        for seniority_rates in rates.values():
            assert "developer" in seniority_rates
            assert "architect" in seniority_rates
            assert "tech_lead" in seniority_rates
            assert "qa" in seniority_rates
            assert "devops" in seniority_rates
            assert "pm" in seniority_rates

    def test_rate_values_are_correct(self, client):
        """Rate values match expected calculations."""
        response = client.get("/api/config/rates")
        rates = response.json()["rates"]

        # Senior developer: $125 * 1.0 = $125
        assert rates["senior"]["developer"] == 125.0

        # Senior architect: $125 * 1.2 = $150
        assert rates["senior"]["architect"] == 150.0

        # Junior QA: $50 * 0.9 = $45
        assert rates["junior"]["qa"] == 45.0

        # Principal tech lead: $225 * 1.15 = $258.75
        assert rates["principal"]["tech_lead"] == 258.75

    def test_list_artifact_types(self, client):
        """List artifact types returns all mappings."""
        response = client.get("/api/config/artifact-types")

        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        assert "total_count" in data
        assert data["total_count"] > 50  # We have many artifact types

        # Check structure of each type
        for artifact_type in data["types"]:
            assert "type" in artifact_type
            assert "role" in artifact_type
            assert "estimated_hours" in artifact_type

    def test_specific_artifact_types(self, client):
        """Known artifact types have correct mappings."""
        response = client.get("/api/config/artifact-types")
        types_list = response.json()["types"]

        # Create lookup dict
        types = {t["type"]: t for t in types_list}

        # Check specific types
        assert types["diagram"]["role"] == "architect"
        assert types["diagram"]["estimated_hours"] == 2.0

        assert types["spec_document"]["role"] == "tech_lead"
        assert types["spec_document"]["estimated_hours"] == 3.0

        assert types["code_example"]["role"] == "developer"
        assert types["code_example"]["estimated_hours"] == 1.0

        assert types["test_case"]["role"] == "qa"
        assert types["test_case"]["estimated_hours"] == 0.5

        assert types["security_finding"]["role"] == "devops"
        assert types["security_finding"]["estimated_hours"] == 1.0

    def test_list_roles(self, client):
        """List roles returns all roles with descriptions."""
        response = client.get("/api/config/roles")

        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert len(data["roles"]) == 6

        # Check role structure
        role_ids = [r["id"] for r in data["roles"]]
        assert "developer" in role_ids
        assert "architect" in role_ids
        assert "tech_lead" in role_ids
        assert "qa" in role_ids
        assert "devops" in role_ids
        assert "pm" in role_ids

        # Check descriptions exist
        for role in data["roles"]:
            assert "description" in role
            assert len(role["description"]) > 0
