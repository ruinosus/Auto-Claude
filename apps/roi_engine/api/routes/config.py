"""
Configuration & Health Routes.

Configuration Endpoints:
- GET /config/rates - Get rate table with hourly rates by seniority and role
- GET /config/artifact-types - List all artifact types with their role mappings
- GET /config/roles - List all roles with descriptions

Health & Activity Endpoints:
- GET /health - Check API health and connected services
- GET /activity/recent - Get recent activity events
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from core import (
    ArtifactConsumer,
    get_all_artifact_types,
    get_langfuse_client,
    get_rate_table,
    get_role_and_hours,
    ROLE_DESCRIPTIONS,
    TraceFilter,
)
from api.models import (
    ActivityEvent,
    ArtifactTypesResponse,
    HealthCheckResponse,
    RateTableResponse,
    RecentActivityResponse,
)


# Track startup time for uptime calculation
_startup_time = time.time()

# Configuration router with /config prefix
router = APIRouter(prefix="/config", tags=["Configuration"])

# Health router at root level (no prefix)
health_router = APIRouter(tags=["Health"])


# ═══════════════════════════════════════════════════════════════
# Configuration Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/rates",
    response_model=RateTableResponse,
    summary="Get rate table",
    description="Get hourly rates by seniority and role",
)
async def get_rates() -> RateTableResponse:
    """Get the complete rate table."""
    return RateTableResponse(
        rates=get_rate_table(),
        description="Hourly rates in USD by seniority and role",
    )


@router.get(
    "/artifact-types",
    response_model=ArtifactTypesResponse,
    summary="List artifact types",
    description="List all artifact types with their role mappings",
)
async def list_artifact_types() -> ArtifactTypesResponse:
    """List all artifact types."""
    types = []
    for artifact_type in get_all_artifact_types():
        role, hours = get_role_and_hours(artifact_type)
        types.append({
            "type": artifact_type,
            "role": role.value,
            "estimated_hours": hours,
            "role_description": ROLE_DESCRIPTIONS.get(role, ""),
        })

    return ArtifactTypesResponse(
        types=types,
        total_count=len(types),
    )


@router.get(
    "/roles",
    summary="List roles",
    description="List all roles with descriptions",
)
async def list_roles() -> dict[str, Any]:
    """List all roles."""
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


# ═══════════════════════════════════════════════════════════════
# Health & Activity Endpoints
# ═══════════════════════════════════════════════════════════════


@health_router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check API health and connected services",
)
async def health_check() -> HealthCheckResponse:
    """Check API health."""
    client = get_langfuse_client()

    return HealthCheckResponse(
        status="ok",
        version="0.1.0",
        langfuse_connected=client.is_configured(),
        artifact_storage_available=True,  # Always true if we got here
        uptime_seconds=time.time() - _startup_time,
        last_activity=datetime.now(),
    )


@health_router.get(
    "/activity/recent",
    response_model=RecentActivityResponse,
    summary="Get recent activity",
    description="Get recent activity events",
)
async def get_recent_activity(
    project_dir: str = Query(..., description="Project directory path"),
    limit: int = Query(20, ge=1, le=100, description="Max events"),
) -> RecentActivityResponse:
    """Get recent activity events."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    client = get_langfuse_client()

    events = []

    # Get recent artifacts
    artifacts = consumer.get_all_artifacts(limit=limit)
    for artifact in artifacts:
        events.append(ActivityEvent(
            event_type="artifact_created",
            timestamp=datetime.fromisoformat(artifact.get("created_at", datetime.now().isoformat())),
            description=f"Created {artifact.get('type', 'artifact')}: {artifact.get('description', '')[:50]}",
            spec_id=artifact.get("spec_id"),
            trace_id=artifact.get("trace_id"),
            value=artifact.get("value_usd"),
            metadata={"artifact_id": artifact.get("id")},
        ))

    # Get recent traces
    traces = await client.get_traces(TraceFilter(limit=limit))
    for trace in traces:
        events.append(ActivityEvent(
            event_type="trace_completed",
            timestamp=trace.timestamp,
            description=f"Trace: {trace.name}",
            trace_id=trace.id,
            value=trace.total_cost,
            metadata={"tokens": trace.total_tokens},
        ))

    # Sort by timestamp and limit
    events.sort(key=lambda x: x.timestamp, reverse=True)
    events = events[:limit]

    return RecentActivityResponse(
        events=events,
        total_count=len(events),
    )
