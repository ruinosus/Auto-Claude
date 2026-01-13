"""
Cost Pydantic models for the ROI Engine API.

Contains models for cost analysis, billing, and cost avoidance.
"""

from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════════
# Daily & Hourly Cost Models
# ═══════════════════════════════════════════════════════════════


class DailyCostResponse(BaseModel):
    """Daily cost breakdown."""

    date: str
    trace_count: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0


class DailyCostListResponse(BaseModel):
    """List of daily costs."""

    daily_costs: list[DailyCostResponse]
    total_cost: float = 0.0
    period_start: str
    period_end: str


class HourlyCostResponse(BaseModel):
    """Hourly cost breakdown."""

    hour: str  # ISO format hour (YYYY-MM-DDTHH)
    trace_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0


class HourlyCostListResponse(BaseModel):
    """List of hourly costs."""

    hourly_costs: list[HourlyCostResponse]
    total_cost: float = 0.0
    period_start: str
    period_end: str


# ═══════════════════════════════════════════════════════════════
# Cost by Model & Agent Models
# ═══════════════════════════════════════════════════════════════


class CostByModelResponse(BaseModel):
    """Cost breakdown by model."""

    model: str
    trace_count: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0
    percentage: float = 0.0


class CostByModelListResponse(BaseModel):
    """List of costs by model."""

    models: list[CostByModelResponse]
    total_cost: float = 0.0
    period_start: str
    period_end: str


class CostByAgentResponse(BaseModel):
    """Cost breakdown by agent type."""

    agent_type: str
    trace_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_cost_per_trace: float = 0.0
    percentage: float = 0.0


class CostByAgentListResponse(BaseModel):
    """List of costs by agent."""

    agents: list[CostByAgentResponse]
    total_cost: float = 0.0
    period_start: str
    period_end: str


# ═══════════════════════════════════════════════════════════════
# Billing & Error Cost Models
# ═══════════════════════════════════════════════════════════════


class BillingResponse(BaseModel):
    """Billing summary response."""

    period_start: str
    period_end: str
    total_cost: float = 0.0
    total_tokens: int = 0
    trace_count: int = 0
    by_model: dict[str, float] = {}
    by_agent: dict[str, float] = {}
    by_date: dict[str, float] = {}


class ErrorCostResponse(BaseModel):
    """Error costs summary."""

    total_errors: int = 0
    total_error_cost: float = 0.0
    error_rate: float = 0.0  # percentage
    by_error_type: dict[str, int] = {}
    by_error_cost: dict[str, float] = {}
    period_start: str
    period_end: str


# ═══════════════════════════════════════════════════════════════
# Cost Avoidance Models
# ═══════════════════════════════════════════════════════════════


class CostAvoidanceSummaryResponse(BaseModel):
    """Cost avoidance summary."""

    total_artifact_value: float = 0.0
    total_token_cost: float = 0.0
    cost_avoided: float = 0.0  # value - cost
    efficiency_ratio: float = 0.0  # value / cost
    hours_saved: float = 0.0
    equivalent_salary_cost: float = 0.0  # What it would cost to hire humans
    period_start: str | None = None
    period_end: str | None = None


class CostAvoidanceByRoleItem(BaseModel):
    """Cost avoidance by role."""

    role: str
    role_description: str
    artifact_value: float = 0.0
    estimated_hours: float = 0.0
    hourly_rate: float = 0.0
    human_cost: float = 0.0  # hours * hourly_rate
    token_cost: float = 0.0
    cost_avoided: float = 0.0


class CostAvoidanceByRoleResponse(BaseModel):
    """Response for cost avoidance by role."""

    by_role: list[CostAvoidanceByRoleItem]
    total_human_cost: float = 0.0
    total_token_cost: float = 0.0
    total_cost_avoided: float = 0.0
