"""
ROI Engine Core

Artifact-based ROI calculation for Auto-Claude.

This module provides:
- ArtifactValue, ROIResult: Core data models
- calculate_artifact_value: Role-based artifact valuation
- calculate_roi_for_spec/trace/project: ROI aggregation
- publish_roi: Publishing to Langfuse and local storage

Example Usage:
    from roi_engine.core import (
        calculate_roi_for_spec,
        publish_roi,
        load_squad_config,
    )

    # Load squad configuration
    squad_config = load_squad_config(project_dir="/path/to/project")

    # Calculate ROI for a spec
    roi_result = calculate_roi_for_spec(
        spec_id="001-feature",
        project_dir="/path/to/project",
        token_cost=0.85,
        squad_config=squad_config,
    )

    # Publish results
    await publish_roi(
        roi_result,
        trace_id="trace_abc123",
        project_dir="/path/to/project",
    )

    print(f"ROI: {roi_result.roi_percentage:.1f}%")
    print(f"Value: ${roi_result.total_artifact_value:.2f}")
    print(f"Cost: ${roi_result.token_cost:.2f}")
"""

# Models
from .models import (
    ArtifactStatus,
    ArtifactValue,
    ROIResult,
    ROISummary,
    Role,
    Seniority,
)

# Configuration
from .config import (
    SquadConfigWrapper,
    load_squad_config,
    get_default_config,
    get_rate_table,
)

# Mappings
from .mappings import (
    ARTIFACT_ROLE_MAP,
    get_role_and_hours,
    get_all_artifact_types,
    get_artifacts_by_role,
    ROLE_DESCRIPTIONS,
)

# Valuator
from .valuator import (
    calculate_artifact_value,
    valuate_artifacts,
    get_artifact_value_preview,
    compare_valuations,
)

# Consumer
from .consumer import (
    ArtifactConsumer,
    create_consumer,
)

# Aggregator
from .aggregator import (
    calculate_roi,
    calculate_roi_for_spec,
    calculate_roi_for_trace,
    calculate_roi_for_project,
    aggregate_by_role,
    aggregate_by_type,
)

# Publisher
from .publisher import (
    publish_roi_to_langfuse,
    save_roi_locally,
    load_roi_locally,
    list_local_roi_results,
    publish_roi,
)

# Langfuse Client
from .langfuse_client import (
    LangfuseClient,
    get_langfuse_client,
    TraceFilter,
    TraceData,
    GenerationData,
    ScoreData,
    SessionData,
    DailyMetric,
    CostBreakdown,
)

__all__ = [
    # Models
    "ArtifactStatus",
    "ArtifactValue",
    "ROIResult",
    "ROISummary",
    "Role",
    "Seniority",
    # Configuration
    "SquadConfigWrapper",
    "load_squad_config",
    "get_default_config",
    "get_rate_table",
    # Mappings
    "ARTIFACT_ROLE_MAP",
    "get_role_and_hours",
    "get_all_artifact_types",
    "get_artifacts_by_role",
    "ROLE_DESCRIPTIONS",
    # Valuator
    "calculate_artifact_value",
    "valuate_artifacts",
    "get_artifact_value_preview",
    "compare_valuations",
    # Consumer
    "ArtifactConsumer",
    "create_consumer",
    # Aggregator
    "calculate_roi",
    "calculate_roi_for_spec",
    "calculate_roi_for_trace",
    "calculate_roi_for_project",
    "aggregate_by_role",
    "aggregate_by_type",
    # Publisher
    "publish_roi_to_langfuse",
    "save_roi_locally",
    "load_roi_locally",
    "list_local_roi_results",
    "publish_roi",
    # Langfuse Client
    "LangfuseClient",
    "get_langfuse_client",
    "TraceFilter",
    "TraceData",
    "GenerationData",
    "ScoreData",
    "SessionData",
    "DailyMetric",
    "CostBreakdown",
]

__version__ = "0.1.0"
