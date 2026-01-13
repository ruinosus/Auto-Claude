"""
Benchmark Routes - Benchmark and efficiency endpoints.

Endpoints:
- GET /benchmark/efficiency - Get benchmark efficiency metrics
- GET /benchmark/squad - Benchmark squad configurations
- GET /benchmark/projects - Benchmark multiple projects
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

from core import (
    ArtifactConsumer,
    get_langfuse_client,
    load_squad_config,
    valuate_artifacts,
)
from core.models import Role
from api.models import (
    BenchmarkEfficiencyResponse,
    ProjectBenchmarkResponse,
    ProjectMetrics,
    SquadBenchmarkResponse,
    SquadBenchmarkResult,
    SquadMemberConfig,
)


router = APIRouter(prefix="/benchmark", tags=["Benchmarks"])


# ═══════════════════════════════════════════════════════════════
# Phase 5E: Benchmark Efficiency Endpoint
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/efficiency",
    response_model=BenchmarkEfficiencyResponse,
    summary="Get benchmark efficiency",
    description="Get efficiency metrics and benchmarks",
)
async def get_benchmark_efficiency(
    project_dir: str = Query(..., description="Project directory path"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
) -> BenchmarkEfficiencyResponse:
    """Get benchmark efficiency metrics."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)
    client = get_langfuse_client()

    from_date = from_date or (datetime.now() - timedelta(days=30))
    to_date = to_date or datetime.now()

    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)

    # Get token/cost data
    breakdown = await client.get_cost_breakdown(from_date, to_date)
    daily_metrics = await client.get_daily_metrics(from_date, to_date)

    total_tokens = sum(m.total_tokens for m in daily_metrics)
    total_cost = breakdown.total
    total_value = sum(a.calculated_value for a in valued_artifacts)
    artifact_count = len(valued_artifacts)

    # Calculate days in period
    days_in_period = (to_date - from_date).days or 1

    # Core efficiency metrics
    tokens_per_artifact = total_tokens / artifact_count if artifact_count > 0 else 0
    cost_per_artifact = total_cost / artifact_count if artifact_count > 0 else 0
    cost_per_value = total_cost / total_value if total_value > 0 else 0
    value_per_token = total_value / total_tokens if total_tokens > 0 else 0

    # Time-based efficiency
    artifacts_per_day = artifact_count / days_in_period
    value_per_day = total_value / days_in_period

    # Industry benchmarks (hypothetical averages)
    industry_benchmarks = {
        "tokens_per_artifact": 50000,
        "cost_per_artifact": 0.50,
        "cost_per_value": 0.01,
    }

    vs_industry = {
        "tokens_per_artifact": ((industry_benchmarks["tokens_per_artifact"] - tokens_per_artifact) / industry_benchmarks["tokens_per_artifact"] * 100) if tokens_per_artifact > 0 else 0,
        "cost_per_artifact": ((industry_benchmarks["cost_per_artifact"] - cost_per_artifact) / industry_benchmarks["cost_per_artifact"] * 100) if cost_per_artifact > 0 else 0,
        "cost_per_value": ((industry_benchmarks["cost_per_value"] - cost_per_value) / industry_benchmarks["cost_per_value"] * 100) if cost_per_value > 0 else 0,
    }

    # Determine efficiency rank
    avg_vs_industry = sum(vs_industry.values()) / len(vs_industry)
    if avg_vs_industry > 30:
        efficiency_rank = "excellent"
    elif avg_vs_industry > 10:
        efficiency_rank = "good"
    elif avg_vs_industry > -10:
        efficiency_rank = "average"
    else:
        efficiency_rank = "below_average"

    return BenchmarkEfficiencyResponse(
        tokens_per_artifact=tokens_per_artifact,
        cost_per_artifact=cost_per_artifact,
        cost_per_value_dollar=cost_per_value,
        value_per_token=value_per_token,
        artifacts_per_day=artifacts_per_day,
        value_per_day=value_per_day,
        vs_industry_avg=vs_industry,
        efficiency_rank=efficiency_rank,
        period_start=from_date.strftime("%Y-%m-%d"),
        period_end=to_date.strftime("%Y-%m-%d"),
        sample_size=artifact_count,
    )


# ═══════════════════════════════════════════════════════════════
# Phase 5F: Advanced Benchmarking Endpoints
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/squad",
    response_model=SquadBenchmarkResponse,
    summary="Benchmark squad configurations",
    description="Compare different squad configurations for ROI optimization",
)
async def benchmark_squad(
    project_dir: str = Query(..., description="Project directory path"),
) -> SquadBenchmarkResponse:
    """Benchmark squad configurations."""
    project_path = Path(project_dir)
    consumer = ArtifactConsumer(project_path)
    squad_config = load_squad_config(project_dir=project_path)

    all_artifacts = consumer.get_all_artifacts(limit=10000)
    valued_artifacts = valuate_artifacts(all_artifacts, squad_config)

    # Analyze current squad based on artifacts
    roles_used: dict[str, dict] = {}
    for a in valued_artifacts:
        role = a.role.value
        if role not in roles_used:
            roles_used[role] = {
                "count": 0,
                "value": 0.0,
                "hourly_rate": a.hourly_rate,
                "types": set(),
            }
        roles_used[role]["count"] += 1
        roles_used[role]["value"] += a.calculated_value
        roles_used[role]["types"].add(a.artifact_type)

    # Build current squad config
    current_members = []
    total_hourly = 0.0
    for role, data in roles_used.items():
        try:
            role_enum = Role(role)
        except ValueError:
            continue

        member = SquadMemberConfig(
            role=role,
            seniority="senior",
            hourly_rate=data["hourly_rate"],
            artifact_types=list(data["types"]),
        )
        current_members.append(member)
        total_hourly += data["hourly_rate"]

    # Calculate daily value (assume 30 day period)
    daily_value = sum(a.calculated_value for a in valued_artifacts) / 30

    # Calculate estimated ROI (hypothetical 8hr day at hourly rates)
    daily_cost = total_hourly * 8
    estimated_roi = ((daily_value - daily_cost) / daily_cost * 100) if daily_cost > 0 else 0

    # Identify strengths/weaknesses
    strengths = []
    weaknesses = []

    # Check for role coverage
    expected_roles = {"developer", "architect", "qa", "tech_lead"}
    covered_roles = set(roles_used.keys())
    missing_roles = expected_roles - covered_roles

    if "architect" in covered_roles:
        strengths.append("Strong architectural coverage")
    if "qa" in covered_roles:
        strengths.append("Quality assurance in place")
    if missing_roles:
        weaknesses.append(f"Missing roles: {', '.join(missing_roles)}")

    # Check for role balance
    total_artifacts = len(valued_artifacts)
    if total_artifacts > 0:
        dev_ratio = roles_used.get("developer", {}).get("count", 0) / total_artifacts
        if dev_ratio > 0.7:
            weaknesses.append("Heavy developer focus - consider more planning/architecture")
        elif dev_ratio < 0.3:
            strengths.append("Balanced workload across roles")

    current_squad = SquadBenchmarkResult(
        config_name="current",
        total_hourly_cost=total_hourly,
        estimated_daily_value=daily_value,
        estimated_roi=estimated_roi,
        member_count=len(current_members),
        members=current_members,
        strengths=strengths,
        weaknesses=weaknesses,
    )

    # Generate alternative squad configurations
    alternatives = []

    # Alternative 1: Add architect if missing
    if "architect" not in covered_roles:
        alt_members = current_members.copy()
        alt_members.append(SquadMemberConfig(
            role="architect",
            seniority="senior",
            hourly_rate=180.0,
            artifact_types=["diagram", "architecture_insight", "system_design"],
        ))
        alt_hourly = total_hourly + 180.0
        alt_daily_value = daily_value * 1.2  # Estimated 20% improvement
        alt_roi = ((alt_daily_value - (alt_hourly * 8)) / (alt_hourly * 8) * 100) if alt_hourly > 0 else 0

        alternatives.append(SquadBenchmarkResult(
            config_name="add_architect",
            total_hourly_cost=alt_hourly,
            estimated_daily_value=alt_daily_value,
            estimated_roi=alt_roi,
            member_count=len(alt_members),
            members=alt_members,
            strengths=["Better architectural coverage", "More complete designs"],
            weaknesses=["Higher cost"],
        ))

    # Alternative 2: Lean team (reduce seniority)
    lean_members = []
    lean_hourly = 0.0
    for m in current_members:
        lean_member = SquadMemberConfig(
            role=m.role,
            seniority="mid",
            hourly_rate=m.hourly_rate * 0.7,
            artifact_types=m.artifact_types,
        )
        lean_members.append(lean_member)
        lean_hourly += lean_member.hourly_rate

    lean_daily_value = daily_value * 0.85  # Estimated 15% reduction
    lean_roi = ((lean_daily_value - (lean_hourly * 8)) / (lean_hourly * 8) * 100) if lean_hourly > 0 else 0

    alternatives.append(SquadBenchmarkResult(
        config_name="lean_team",
        total_hourly_cost=lean_hourly,
        estimated_daily_value=lean_daily_value,
        estimated_roi=lean_roi,
        member_count=len(lean_members),
        members=lean_members,
        strengths=["Lower cost", "Good for simpler projects"],
        weaknesses=["Reduced output quality", "Less expertise"],
    ))

    # Determine recommended squad
    all_squads = [current_squad] + alternatives
    best_squad = max(all_squads, key=lambda s: s.estimated_roi)
    recommended = best_squad.config_name if best_squad.config_name != "current" else None
    improvement = best_squad.estimated_roi - estimated_roi if recommended else 0

    return SquadBenchmarkResponse(
        current_squad=current_squad,
        alternative_squads=alternatives,
        recommended_squad=recommended,
        potential_roi_improvement=improvement,
    )


@router.get(
    "/projects",
    response_model=ProjectBenchmarkResponse,
    summary="Benchmark projects",
    description="Compare metrics across multiple projects",
)
async def benchmark_projects(
    project_dirs: list[str] = Query(..., description="List of project directory paths"),
) -> ProjectBenchmarkResponse:
    """Benchmark multiple projects."""
    projects = []
    all_rois = []
    all_artifact_values = []

    for project_dir in project_dirs:
        project_path = Path(project_dir)
        if not project_path.exists():
            continue

        consumer = ArtifactConsumer(project_path)
        squad_config = load_squad_config(project_dir=project_path)

        all_artifacts = consumer.get_all_artifacts(limit=10000)
        valued_artifacts = valuate_artifacts(all_artifacts, squad_config)

        total_value = sum(a.calculated_value for a in valued_artifacts)
        artifact_count = len(valued_artifacts)
        avg_value = total_value / artifact_count if artifact_count > 0 else 0

        # Estimate cost (would need Langfuse per-project, using estimate)
        estimated_cost = artifact_count * 0.05  # $0.05 per artifact estimate

        roi = ((total_value - estimated_cost) / estimated_cost * 100) if estimated_cost > 0 else 0

        # Get top types
        type_counts: dict[str, int] = {}
        for a in valued_artifacts:
            type_counts[a.artifact_type] = type_counts.get(a.artifact_type, 0) + 1
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        # Calculate artifacts per day (assume 30 days)
        artifacts_per_day = artifact_count / 30

        project = ProjectMetrics(
            project_id=project_path.name,
            project_name=project_path.name,
            total_artifacts=artifact_count,
            total_value=total_value,
            total_cost=estimated_cost,
            roi_percentage=roi,
            avg_artifact_value=avg_value,
            artifacts_per_day=artifacts_per_day,
            top_artifact_types=[t[0] for t in top_types],
            period_days=30,
        )
        projects.append(project)

        all_rois.append(roi)
        all_artifact_values.append(avg_value)

    # Find bests
    best_roi_project = None
    best_value_project = None
    most_productive_project = None

    if projects:
        best_roi_project = max(projects, key=lambda p: p.roi_percentage).project_id
        best_value_project = max(projects, key=lambda p: p.total_value).project_id
        most_productive_project = max(projects, key=lambda p: p.artifacts_per_day).project_id

    overall_avg_roi = sum(all_rois) / len(all_rois) if all_rois else 0
    overall_avg_value = sum(all_artifact_values) / len(all_artifact_values) if all_artifact_values else 0

    return ProjectBenchmarkResponse(
        projects=projects,
        best_roi_project=best_roi_project,
        best_value_project=best_value_project,
        most_productive_project=most_productive_project,
        overall_avg_roi=overall_avg_roi,
        overall_avg_artifact_value=overall_avg_value,
    )
