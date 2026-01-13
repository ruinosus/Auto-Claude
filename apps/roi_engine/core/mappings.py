"""
Artifact to Role Mappings

This is the CORE configuration of the ROI Engine.
It maps each artifact type to:
1. The role that would produce this artifact
2. The estimated hours to produce it

Value Calculation:
  value = hourly_rate (from squad config) × estimated_hours (from this mapping)

Example:
  "diagram" → (ARCHITECT, 2.0 hours)
  With Senior Architect at $150/hr → $300 value
"""

from .models import Role


# Main mapping: artifact_type → (responsible_role, estimated_hours)
ARTIFACT_ROLE_MAP: dict[str, tuple[Role, float]] = {
    # ═══════════════════════════════════════════════════════════════
    # ARCHITECTURE ARTIFACTS → ARCHITECT
    # ═══════════════════════════════════════════════════════════════
    "diagram": (Role.ARCHITECT, 2.0),
    "architecture_insight": (Role.ARCHITECT, 1.5),
    "architecture_decision": (Role.ARCHITECT, 2.0),
    "system_design": (Role.ARCHITECT, 4.0),
    "adr": (Role.ARCHITECT, 3.0),
    "api_design": (Role.ARCHITECT, 2.5),
    "data_model": (Role.ARCHITECT, 2.0),
    "integration_design": (Role.ARCHITECT, 2.5),
    "sequence_diagram": (Role.ARCHITECT, 1.5),
    "component_diagram": (Role.ARCHITECT, 1.5),
    "deployment_diagram": (Role.ARCHITECT, 2.0),

    # ═══════════════════════════════════════════════════════════════
    # SPEC/PLANNING ARTIFACTS → TECH LEAD
    # ═══════════════════════════════════════════════════════════════
    "spec_document": (Role.TECH_LEAD, 3.0),
    "spec": (Role.TECH_LEAD, 3.0),
    "implementation_plan": (Role.TECH_LEAD, 2.5),
    "requirements": (Role.TECH_LEAD, 2.0),
    "requirements_document": (Role.TECH_LEAD, 2.0),
    "complexity_assessment": (Role.TECH_LEAD, 1.0),
    "context_discovery": (Role.TECH_LEAD, 1.5),
    "context": (Role.TECH_LEAD, 1.5),
    "tech_stack_analysis": (Role.TECH_LEAD, 1.5),
    "dependency_analysis": (Role.TECH_LEAD, 1.0),
    "risk_assessment": (Role.TECH_LEAD, 1.5),
    "subtask_definition": (Role.TECH_LEAD, 0.5),
    "pattern_discovery": (Role.TECH_LEAD, 1.0),
    "best_practice": (Role.TECH_LEAD, 0.75),

    # ═══════════════════════════════════════════════════════════════
    # CODE ARTIFACTS → DEVELOPER
    # ═══════════════════════════════════════════════════════════════
    "code_example": (Role.DEVELOPER, 1.0),
    "code": (Role.DEVELOPER, 1.0),
    "code_implementation": (Role.DEVELOPER, 1.5),
    "refactoring": (Role.DEVELOPER, 1.5),
    "bug_fix": (Role.DEVELOPER, 0.5),
    "commit": (Role.DEVELOPER, 0.25),
    "pr_description": (Role.DEVELOPER, 0.5),
    "code_review": (Role.DEVELOPER, 0.75),
    "migration_script": (Role.DEVELOPER, 1.5),
    "configuration": (Role.DEVELOPER, 0.5),
    "env_setup": (Role.DEVELOPER, 0.5),
    "gotcha_identified": (Role.DEVELOPER, 0.5),
    "structural_issue": (Role.DEVELOPER, 0.5),
    "conflict_resolution": (Role.DEVELOPER, 0.75),
    "merge_decision": (Role.DEVELOPER, 0.5),

    # ═══════════════════════════════════════════════════════════════
    # TEST/QA ARTIFACTS → QA
    # ═══════════════════════════════════════════════════════════════
    "test_case": (Role.QA, 0.5),
    "test": (Role.QA, 0.5),
    "test_suite": (Role.QA, 1.5),
    "qa_report": (Role.QA, 1.0),
    "qa_verdict": (Role.QA, 0.5),
    "qa_finding": (Role.QA, 0.75),
    "qa_fix": (Role.QA, 0.5),
    "test_suggestion": (Role.QA, 0.5),
    "acceptance_check": (Role.QA, 0.25),
    "regression_test": (Role.QA, 1.0),
    "test_plan": (Role.QA, 1.5),
    "pr_verdict": (Role.QA, 0.5),

    # ═══════════════════════════════════════════════════════════════
    # SECURITY/OPS ARTIFACTS → DEVOPS
    # ═══════════════════════════════════════════════════════════════
    "security_finding": (Role.DEVOPS, 1.0),
    "security_audit": (Role.DEVOPS, 2.0),
    "performance_insight": (Role.DEVOPS, 1.0),
    "performance_analysis": (Role.DEVOPS, 1.5),
    "deployment_plan": (Role.DEVOPS, 2.0),
    "ci_config": (Role.DEVOPS, 1.0),
    "infrastructure_code": (Role.DEVOPS, 2.0),
    "monitoring_setup": (Role.DEVOPS, 1.5),
    "alert_configuration": (Role.DEVOPS, 0.75),
    "container_config": (Role.DEVOPS, 1.0),
    "pipeline_config": (Role.DEVOPS, 1.5),

    # ═══════════════════════════════════════════════════════════════
    # BUSINESS ARTIFACTS → PM
    # ═══════════════════════════════════════════════════════════════
    "recommendation": (Role.PM, 1.0),
    "priority_assessment": (Role.PM, 0.75),
    "priority_decision": (Role.PM, 0.75),
    "cost_analysis": (Role.PM, 1.5),
    "roadmap_item": (Role.PM, 0.5),
    "feature_suggestion": (Role.PM, 0.5),
    "market_analysis": (Role.PM, 2.0),
    "competitor_insight": (Role.PM, 1.5),
    "user_story": (Role.PM, 0.5),
    "acceptance_criteria": (Role.PM, 0.5),
    "milestone": (Role.PM, 0.5),
    "target_audience": (Role.PM, 1.0),
    "market_gap": (Role.PM, 1.5),
    "idea": (Role.PM, 0.5),
    "analysis": (Role.PM, 1.0),

    # ═══════════════════════════════════════════════════════════════
    # DOCUMENTATION → TECH LEAD (cross-functional)
    # ═══════════════════════════════════════════════════════════════
    "documentation": (Role.TECH_LEAD, 1.5),
    "readme": (Role.TECH_LEAD, 1.0),
    "api_documentation": (Role.TECH_LEAD, 2.0),
    "changelog": (Role.TECH_LEAD, 0.5),
    "release_notes": (Role.TECH_LEAD, 0.75),
    "onboarding_guide": (Role.TECH_LEAD, 2.0),
    "troubleshooting_guide": (Role.TECH_LEAD, 1.5),
}


# Default fallback for unknown artifact types
DEFAULT_ROLE = Role.DEVELOPER
DEFAULT_HOURS = 1.0


def get_role_and_hours(artifact_type: str) -> tuple[Role, float]:
    """
    Get the role and estimated hours for an artifact type.

    Args:
        artifact_type: The type of artifact (e.g., "diagram", "code_example")

    Returns:
        Tuple of (Role, estimated_hours)
    """
    return ARTIFACT_ROLE_MAP.get(
        artifact_type.lower(),
        (DEFAULT_ROLE, DEFAULT_HOURS)
    )


def get_all_artifact_types() -> list[str]:
    """Get list of all known artifact types."""
    return list(ARTIFACT_ROLE_MAP.keys())


def get_artifacts_by_role(role: Role) -> list[tuple[str, float]]:
    """
    Get all artifact types for a specific role.

    Returns:
        List of (artifact_type, estimated_hours) tuples
    """
    return [
        (artifact_type, hours)
        for artifact_type, (r, hours) in ARTIFACT_ROLE_MAP.items()
        if r == role
    ]


# Role descriptions for UI
ROLE_DESCRIPTIONS = {
    Role.ARCHITECT: "Creates system designs, diagrams, and architectural decisions",
    Role.TECH_LEAD: "Creates specs, plans, and technical documentation",
    Role.DEVELOPER: "Creates code, implementations, and fixes",
    Role.QA: "Creates tests, QA reports, and quality assessments",
    Role.DEVOPS: "Creates deployment plans, security audits, and infrastructure",
    Role.PM: "Creates roadmaps, priorities, and business analysis",
}
