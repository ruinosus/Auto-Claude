"""
Traces Routes - Trace and session endpoints.

Endpoints:
- GET /traces - List traces with optional filtering and pagination
- GET /traces/{trace_id} - Get detailed trace information including generations
- GET /sessions - List sessions with pagination
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from core import (
    get_langfuse_client,
    TraceFilter,
)
from api.models import (
    SessionListResponse,
    SessionResponse,
    TraceDetailResponse,
    TraceListResponse,
    TraceResponse,
)


router = APIRouter(prefix="", tags=["Traces"])


@router.get(
    "/traces",
    response_model=TraceListResponse,
    summary="List traces",
    description="List traces with optional filtering and pagination",
)
async def list_traces(
    spec_id: Optional[str] = Query(None, description="Filter by spec ID"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
    to_date: Optional[datetime] = Query(None, description="To timestamp"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> TraceListResponse:
    """List traces from Langfuse."""
    client = get_langfuse_client()

    filter = TraceFilter(
        spec_id=spec_id,
        agent_type=agent_type,
        from_timestamp=from_date,
        to_timestamp=to_date,
        limit=limit,
        offset=offset,
    )

    traces = await client.get_traces(filter)

    return TraceListResponse(
        traces=[
            TraceResponse(
                id=t.id,
                name=t.name,
                timestamp=t.timestamp,
                session_id=t.session_id,
                total_tokens=t.total_tokens,
                total_cost=t.total_cost,
                latency_ms=t.latency_ms,
                tags=t.tags,
                metadata=t.metadata,
            )
            for t in traces
        ],
        total_count=len(traces),
        offset=offset,
        limit=limit,
    )


@router.get(
    "/traces/{trace_id}",
    response_model=TraceDetailResponse,
    summary="Get trace details",
    description="Get detailed trace information including generations",
)
async def get_trace_detail(trace_id: str) -> TraceDetailResponse:
    """Get detailed trace information."""
    client = get_langfuse_client()

    trace = await client.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

    generations = await client.get_generations(trace_id)

    return TraceDetailResponse(
        id=trace.id,
        name=trace.name,
        timestamp=trace.timestamp,
        session_id=trace.session_id,
        total_tokens=trace.total_tokens,
        total_cost=trace.total_cost,
        latency_ms=trace.latency_ms,
        tags=trace.tags,
        metadata=trace.metadata,
        input=trace.input,
        output=trace.output,
        generations=[
            {
                "id": g.id,
                "name": g.name,
                "model": g.model,
                "timestamp": g.timestamp.isoformat(),
                "input_tokens": g.input_tokens,
                "output_tokens": g.output_tokens,
                "total_tokens": g.total_tokens,
                "cost": g.cost,
                "latency_ms": g.latency_ms,
            }
            for g in generations
        ],
    )


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List sessions",
    description="List sessions with pagination",
)
async def list_sessions(
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> SessionListResponse:
    """List sessions from Langfuse."""
    client = get_langfuse_client()

    sessions = await client.get_sessions(limit=limit, offset=offset)

    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                name=s.name,
                created_at=s.created_at,
                trace_count=s.trace_count,
                total_tokens=s.total_tokens,
                total_cost=s.total_cost,
            )
            for s in sessions
        ],
        total_count=len(sessions),
    )
