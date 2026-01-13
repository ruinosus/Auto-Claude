"""
Quality Routes - Value breakdown and quality score endpoints.

Endpoints:
- GET /value/breakdown - Get detailed value breakdown by role, type, seniority, and spec
- GET /quality/scores - Get quality scores over time
- GET /quality/by-agent - Get quality scores by agent type
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

from core import (
    ArtifactConsumer,
    load_squad_config,
    valuate_artifacts,
)
from api.models import (
    QualityByAgentListResponse,
    QualityByAgentResponse,
    QualityScorePoint,
    QualityScoresResponse,
    ValueBreakdownItem,
    ValueBreakdownResponse,
)


router = APIRouter(prefix="", tags=["Quality"])


@router.get(
    "/value/breakdown",
    response_model=ValueBreakdownResponse,
    summary="Get value breakdown",
    description="Get detailed value breakdown by role, type, seniority, and spec",
)
async def get_value_breakdown(
    project_dir: str = Query(..., description="Project directory path"),
    spec_id: Optional[str] = Query(None, description="Filter by spec ID"),
) -> ValueBreakdownResponse:
    """Get detailed value breakdown."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)

    if spec_id:
        artifacts = consumer.get_artifacts_for_spec(spec_id)
    else:
        artifacts = consumer.get_all_artifacts(limit=10000)

    valued_artifacts = valuate_artifacts(artifacts, squad_config)
    total_value = sum(a.calculated_value for a in valued_artifacts)

    # By role
    by_role_dict: dict[str, dict] = {}
    for a in valued_artifacts:
        role = a.role.value
        if role not in by_role_dict:
            by_role_dict[role] = {"value": 0.0, "count": 0}
        by_role_dict[role]["value"] += a.calculated_value
        by_role_dict[role]["count"] += 1

    by_role = [
        ValueBreakdownItem(
            category=role,
            value=data["value"],
            percentage=(data["value"] / total_value * 100) if total_value > 0 else 0,
            count=data["count"],
        )
        for role, data in sorted(by_role_dict.items(), key=lambda x: x[1]["value"], reverse=True)
    ]

    # By type
    by_type_dict: dict[str, dict] = {}
    for a in valued_artifacts:
        artifact_type = a.artifact_type
        if artifact_type not in by_type_dict:
            by_type_dict[artifact_type] = {"value": 0.0, "count": 0}
        by_type_dict[artifact_type]["value"] += a.calculated_value
        by_type_dict[artifact_type]["count"] += 1

    by_type = [
        ValueBreakdownItem(
            category=artifact_type,
            value=data["value"],
            percentage=(data["value"] / total_value * 100) if total_value > 0 else 0,
            count=data["count"],
        )
        for artifact_type, data in sorted(by_type_dict.items(), key=lambda x: x[1]["value"], reverse=True)
    ]

    # By seniority
    by_seniority_dict: dict[str, dict] = {}
    for a in valued_artifacts:
        seniority = a.seniority.value
        if seniority not in by_seniority_dict:
            by_seniority_dict[seniority] = {"value": 0.0, "count": 0}
        by_seniority_dict[seniority]["value"] += a.calculated_value
        by_seniority_dict[seniority]["count"] += 1

    by_seniority = [
        ValueBreakdownItem(
            category=seniority,
            value=data["value"],
            percentage=(data["value"] / total_value * 100) if total_value > 0 else 0,
            count=data["count"],
        )
        for seniority, data in sorted(by_seniority_dict.items(), key=lambda x: x[1]["value"], reverse=True)
    ]

    # By spec
    by_spec_dict: dict[str, dict] = {}
    for a in valued_artifacts:
        spec = a.spec_id or "unknown"
        if spec not in by_spec_dict:
            by_spec_dict[spec] = {"value": 0.0, "count": 0}
        by_spec_dict[spec]["value"] += a.calculated_value
        by_spec_dict[spec]["count"] += 1

    by_spec = [
        ValueBreakdownItem(
            category=spec,
            value=data["value"],
            percentage=(data["value"] / total_value * 100) if total_value > 0 else 0,
            count=data["count"],
        )
        for spec, data in sorted(by_spec_dict.items(), key=lambda x: x[1]["value"], reverse=True)
    ]

    return ValueBreakdownResponse(
        total_value=total_value,
        by_role=by_role,
        by_type=by_type,
        by_seniority=by_seniority,
        by_spec=by_spec,
    )


@router.get(
    "/quality/scores",
    response_model=QualityScoresResponse,
    summary="Get quality scores",
    description="Get quality scores over time",
)
async def get_quality_scores(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> QualityScoresResponse:
    """Get quality scores over time."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)

    from_date = from_date or (datetime.now() - timedelta(days=30))
    to_date = to_date or datetime.now()

    all_artifacts = consumer.get_all_artifacts(limit=10000)

    # Group by date and calculate quality scores
    by_date: dict[str, dict] = {}
    for artifact in all_artifacts:
        created_at = artifact.get("created_at")
        if created_at:
            date_key = datetime.fromisoformat(created_at).strftime("%Y-%m-%d")
            if date_key not in by_date:
                by_date[date_key] = {
                    "scores": [],
                    "count": 0,
                    "high_quality": 0,
                    "low_quality": 0,
                }

            # Quality score from artifact metadata or default based on complexity
            quality = artifact.get("quality_score", 0.7)  # Default 0.7
            if artifact.get("complexity") == "high":
                quality = min(quality + 0.1, 1.0)

            by_date[date_key]["scores"].append(quality)
            by_date[date_key]["count"] += 1
            if quality >= 0.8:
                by_date[date_key]["high_quality"] += 1
            elif quality < 0.5:
                by_date[date_key]["low_quality"] += 1

    # Build scores timeline
    scores = []
    all_scores = []
    current_date = from_date

    while current_date <= to_date:
        date_key = current_date.strftime("%Y-%m-%d")
        data = by_date.get(date_key, {"scores": [], "count": 0, "high_quality": 0, "low_quality": 0})

        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        all_scores.extend(data["scores"])

        scores.append(QualityScorePoint(
            date=date_key,
            avg_quality_score=avg_score,
            artifact_count=data["count"],
            high_quality_count=data["high_quality"],
            low_quality_count=data["low_quality"],
        ))

        current_date += timedelta(days=1)

    overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0

    # Determine trend
    quality_trend = "stable"
    if len(scores) >= 7:
        first_half = [s.avg_quality_score for s in scores[:len(scores)//2] if s.avg_quality_score > 0]
        second_half = [s.avg_quality_score for s in scores[len(scores)//2:] if s.avg_quality_score > 0]
        if first_half and second_half:
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            if second_avg > first_avg * 1.05:
                quality_trend = "improving"
            elif second_avg < first_avg * 0.95:
                quality_trend = "declining"

    return QualityScoresResponse(
        scores=scores,
        period_start=from_date.strftime("%Y-%m-%d"),
        period_end=to_date.strftime("%Y-%m-%d"),
        overall_avg_quality=overall_avg,
        quality_trend=quality_trend,
    )


@router.get(
    "/quality/by-agent",
    response_model=QualityByAgentListResponse,
    summary="Get quality by agent",
    description="Get quality scores by agent type",
)
async def get_quality_by_agent(
    project_dir: str = Query(..., description="Project directory path"),
) -> QualityByAgentListResponse:
    """Get quality scores by agent type."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)

    all_artifacts = consumer.get_all_artifacts(limit=10000)

    # Group by agent type
    by_agent: dict[str, dict] = {}
    for artifact in all_artifacts:
        agent_type = artifact.get("agent_type", "unknown")
        if agent_type not in by_agent:
            by_agent[agent_type] = {
                "scores": [],
                "count": 0,
                "high_quality": 0,
            }

        quality = artifact.get("quality_score", 0.7)
        by_agent[agent_type]["scores"].append(quality)
        by_agent[agent_type]["count"] += 1
        if quality >= 0.8:
            by_agent[agent_type]["high_quality"] += 1

    agents = []
    all_scores = []

    for agent_type, data in sorted(by_agent.items(), key=lambda x: sum(x[1]["scores"]) / len(x[1]["scores"]) if x[1]["scores"] else 0, reverse=True):
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        high_pct = (data["high_quality"] / data["count"] * 100) if data["count"] > 0 else 0
        all_scores.extend(data["scores"])

        agents.append(QualityByAgentResponse(
            agent_type=agent_type,
            avg_quality_score=avg_score,
            artifact_count=data["count"],
            high_quality_percentage=high_pct,
        ))

    overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0

    return QualityByAgentListResponse(
        agents=agents,
        overall_avg_quality=overall_avg,
    )
