"""
ROI Engine - Artifact-based ROI Calculation for Auto-Claude.

This package provides role-based artifact valuation and ROI calculation.

Example:
    from roi_engine import calculate_roi_for_spec, load_squad_config

    squad_config = load_squad_config(project_dir="/path/to/project")
    roi = calculate_roi_for_spec("001-feature", "/path/to/project", 0.85, squad_config)
    print(f"ROI: {roi.roi_percentage:.1f}%")
"""

# Re-export from core for convenience
# Support both relative import (when installed) and absolute import (when running tests)
try:
    from .core import (
        # Models
        ArtifactValue,
        ROIResult,
        ROISummary,
        Role,
        Seniority,
        # Configuration
        SquadConfigWrapper,
        load_squad_config,
        get_default_config,
        get_rate_table,
        # Mappings
        ARTIFACT_ROLE_MAP,
        get_role_and_hours,
        get_all_artifact_types,
        get_artifacts_by_role,
        ROLE_DESCRIPTIONS,
        # Valuator
        calculate_artifact_value,
        valuate_artifacts,
        get_artifact_value_preview,
        compare_valuations,
        # Consumer
        ArtifactConsumer,
        create_consumer,
        # Aggregator
        calculate_roi,
        calculate_roi_for_spec,
        calculate_roi_for_trace,
        calculate_roi_for_project,
        aggregate_by_role,
        aggregate_by_type,
        # Publisher
        publish_roi_to_langfuse,
        save_roi_locally,
        load_roi_locally,
        list_local_roi_results,
        publish_roi,
    )
except ImportError:
    # Fallback for when running tests directly (not installed as package)
    from core import (
        # Models
        ArtifactValue,
        ROIResult,
        ROISummary,
        Role,
        Seniority,
        # Configuration
        SquadConfigWrapper,
        load_squad_config,
        get_default_config,
        get_rate_table,
        # Mappings
        ARTIFACT_ROLE_MAP,
        get_role_and_hours,
        get_all_artifact_types,
        get_artifacts_by_role,
        ROLE_DESCRIPTIONS,
        # Valuator
        calculate_artifact_value,
        valuate_artifacts,
        get_artifact_value_preview,
        compare_valuations,
        # Consumer
        ArtifactConsumer,
        create_consumer,
        # Aggregator
        calculate_roi,
        calculate_roi_for_spec,
        calculate_roi_for_trace,
        calculate_roi_for_project,
        aggregate_by_role,
        aggregate_by_type,
        # Publisher
        publish_roi_to_langfuse,
        save_roi_locally,
        load_roi_locally,
        list_local_roi_results,
        publish_roi,
    )

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Models
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
]
