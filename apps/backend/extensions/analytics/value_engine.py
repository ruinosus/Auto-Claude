"""
Value Attribution Engine
========================

Maps artifact types and actions to USD values.
Based on the unified ROI calculator pattern from the main analytics module.

Value Dimensions:
    - EXECUTION: Direct work completed (time saved, code written)
    - DECISION: Strategic choices enabled (prioritization, scope)
    - PREVENTION: Problems avoided (bugs fixed, rework prevented)
    - KNOWLEDGE: Learning gained (patterns, gotchas documented)
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ValueDimension(Enum):
    """Categories of value contribution."""
    EXECUTION = "execution"      # Direct work: time saved, code written
    DECISION = "decision"        # Strategic: prioritization, clarity
    PREVENTION = "prevention"    # Problems avoided: bugs, rework
    KNOWLEDGE = "knowledge"      # Learning: patterns, gotchas


@dataclass
class ArtifactValue:
    """Value definition for an artifact type."""
    base_value_usd: float
    dimension: ValueDimension
    description: str
    confidence: float = 0.8  # Default confidence


# Artifact type to value mapping
# Based on analysis of insight_runner and roi_publisher
ARTIFACT_VALUES: Dict[str, ArtifactValue] = {
    # Diagrams - High value for visualization
    "diagram": ArtifactValue(
        base_value_usd=150.0,
        dimension=ValueDimension.KNOWLEDGE,
        description="Architecture/flow diagram",
        confidence=0.85,
    ),
    "mermaid_diagram": ArtifactValue(
        base_value_usd=150.0,
        dimension=ValueDimension.KNOWLEDGE,
        description="Mermaid diagram",
        confidence=0.85,
    ),
    "ascii_diagram": ArtifactValue(
        base_value_usd=100.0,
        dimension=ValueDimension.KNOWLEDGE,
        description="ASCII art diagram",
        confidence=0.80,
    ),

    # Patterns and insights - High value for reusability
    "pattern_discovered": ArtifactValue(
        base_value_usd=100.0,
        dimension=ValueDimension.KNOWLEDGE,
        description="Architectural/coding pattern identified",
        confidence=0.80,
    ),
    "gotcha_identified": ArtifactValue(
        base_value_usd=150.0,
        dimension=ValueDimension.PREVENTION,
        description="Pitfall/trap/edge case documented",
        confidence=0.85,
    ),
    "lesson_learned": ArtifactValue(
        base_value_usd=50.0,
        dimension=ValueDimension.KNOWLEDGE,
        description="Implementation lesson/outcome",
        confidence=0.70,
    ),

    # Recommendations and best practices
    "recommendation": ArtifactValue(
        base_value_usd=75.0,
        dimension=ValueDimension.DECISION,
        description="Actionable recommendation",
        confidence=0.75,
    ),
    "best_practice": ArtifactValue(
        base_value_usd=75.0,
        dimension=ValueDimension.KNOWLEDGE,
        description="Best practice documented",
        confidence=0.80,
    ),

    # Security findings - Very high value
    "security_finding": ArtifactValue(
        base_value_usd=200.0,
        dimension=ValueDimension.PREVENTION,
        description="Security vulnerability identified",
        confidence=0.90,
    ),
    "security_recommendation": ArtifactValue(
        base_value_usd=150.0,
        dimension=ValueDimension.PREVENTION,
        description="Security improvement suggestion",
        confidence=0.85,
    ),

    # Code artifacts
    "code_snippet": ArtifactValue(
        base_value_usd=50.0,
        dimension=ValueDimension.EXECUTION,
        description="Reusable code snippet",
        confidence=0.75,
    ),
    "code_explanation": ArtifactValue(
        base_value_usd=30.0,
        dimension=ValueDimension.KNOWLEDGE,
        description="Code explanation/documentation",
        confidence=0.70,
    ),

    # File insights
    "file_insight": ArtifactValue(
        base_value_usd=25.0,
        dimension=ValueDimension.KNOWLEDGE,
        description="File-specific finding",
        confidence=0.70,
    ),

    # Generic artifacts
    "generic": ArtifactValue(
        base_value_usd=25.0,
        dimension=ValueDimension.KNOWLEDGE,
        description="Generic artifact",
        confidence=0.60,
    ),
    "unknown": ArtifactValue(
        base_value_usd=10.0,
        dimension=ValueDimension.KNOWLEDGE,
        description="Unknown artifact type",
        confidence=0.50,
    ),
}


# Agent type confidence multipliers
AGENT_CONFIDENCE: Dict[str, float] = {
    "coder": 0.85,           # High - direct measurable output
    "planner": 0.75,         # Medium-high - strategic but clear
    "qa_reviewer": 0.80,     # High - quality validation
    "qa_fixer": 0.85,        # High - direct fixes
    "insight_extractor": 0.70,  # Medium - analytical
    "spec_gatherer": 0.70,   # Medium - requirements
    "spec_writer": 0.75,     # Medium-high - documentation
    "ideation": 0.65,        # Medium - exploratory
    "roadmap": 0.60,         # Lower - strategic/estimated
    "insights": 0.70,        # Medium - analytical
    "unknown": 0.50,         # Low - unknown source
}


def get_artifact_value(
    artifact_type: str,
    agent_type: str = "unknown",
    custom_value: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate the value of an artifact.

    Args:
        artifact_type: Type of artifact (diagram, pattern_discovered, etc.)
        agent_type: Type of agent that created it
        custom_value: Override value if provided

    Returns:
        Dict with value breakdown:
            - base_value_usd: Base value before adjustments
            - adjusted_value_usd: After confidence adjustment
            - dimension: Value dimension (execution, knowledge, etc.)
            - confidence: Combined confidence score
            - description: Human-readable description
    """
    # Get artifact value definition
    artifact_def = ARTIFACT_VALUES.get(
        artifact_type,
        ARTIFACT_VALUES["unknown"]
    )

    # Get agent confidence multiplier
    agent_confidence = AGENT_CONFIDENCE.get(agent_type, 0.50)

    # Calculate combined confidence
    combined_confidence = artifact_def.confidence * agent_confidence

    # Calculate adjusted value
    base_value = custom_value if custom_value is not None else artifact_def.base_value_usd
    adjusted_value = base_value * combined_confidence

    return {
        "base_value_usd": base_value,
        "adjusted_value_usd": round(adjusted_value, 2),
        "dimension": artifact_def.dimension.value,
        "confidence": round(combined_confidence, 3),
        "description": artifact_def.description,
        "artifact_type": artifact_type,
        "agent_type": agent_type,
    }


@dataclass
class ValueAttribution:
    """Breakdown of value by category."""
    execution_value: float = 0.0
    decision_value: float = 0.0
    prevention_value: float = 0.0
    knowledge_value: float = 0.0
    total_value: float = 0.0
    artifact_count: int = 0
    artifacts_by_type: Dict[str, int] = field(default_factory=dict)
    confidence_score: float = 0.0

    def add_artifact(self, value_info: Dict[str, Any]):
        """Add an artifact's value to the attribution."""
        value = value_info["adjusted_value_usd"]
        dimension = value_info["dimension"]
        artifact_type = value_info["artifact_type"]

        # Add to appropriate dimension
        if dimension == "execution":
            self.execution_value += value
        elif dimension == "decision":
            self.decision_value += value
        elif dimension == "prevention":
            self.prevention_value += value
        elif dimension == "knowledge":
            self.knowledge_value += value

        self.total_value += value
        self.artifact_count += 1

        # Track by type
        if artifact_type not in self.artifacts_by_type:
            self.artifacts_by_type[artifact_type] = 0
        self.artifacts_by_type[artifact_type] += 1

        # Update average confidence
        if self.artifact_count == 1:
            self.confidence_score = value_info["confidence"]
        else:
            # Running average
            self.confidence_score = (
                (self.confidence_score * (self.artifact_count - 1) + value_info["confidence"])
                / self.artifact_count
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "execution_value": round(self.execution_value, 2),
            "decision_value": round(self.decision_value, 2),
            "prevention_value": round(self.prevention_value, 2),
            "knowledge_value": round(self.knowledge_value, 2),
            "total_value": round(self.total_value, 2),
            "artifact_count": self.artifact_count,
            "artifacts_by_type": self.artifacts_by_type,
            "confidence_score": round(self.confidence_score, 3),
        }
