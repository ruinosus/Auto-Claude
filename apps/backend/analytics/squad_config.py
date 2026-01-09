"""
Squad Configuration for ROI Calculations
=========================================

Dataclasses for squad-based ROI configuration loaded from frontend settings.
Squads allow organizations to define team compositions with configurable
ROI calculation parameters.

This module provides:
- SquadConfig: Complete squad configuration with all configurable values
- TimeSavingsConfig: Time savings estimates per activity
- PreventionValuesConfig: Cost estimates for prevented issues
- QualityMultipliersConfig: Quality-based ROI adjustments
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from enum import Enum


class Seniority(Enum):
    """Seniority levels for team members."""
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"


class Role(Enum):
    """Role types for team members."""
    DEVELOPER = "developer"
    QA = "qa"
    DEVOPS = "devops"
    PM = "pm"
    ARCHITECT = "architect"
    TECH_LEAD = "tech_lead"


def create_stakeholder_key(seniority: str, role: str) -> str:
    """Create a stakeholder key from seniority and role."""
    return f"{seniority}_{role}"


@dataclass
class TimeSavingsConfig:
    """
    Time savings estimates per activity (in minutes).

    These values represent the estimated time saved by using AI assistance
    compared to manual execution of each activity.
    """
    pr_review: int = 30
    issue_triage: int = 10
    idea_generation: int = 60
    roadmap_planning: int = 120
    spec_writing: int = 180
    codebase_exploration: int = 45
    conflict_resolution: int = 20

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary for serialization."""
        return {
            "pr_review": self.pr_review,
            "issue_triage": self.issue_triage,
            "idea_generation": self.idea_generation,
            "roadmap_planning": self.roadmap_planning,
            "spec_writing": self.spec_writing,
            "codebase_exploration": self.codebase_exploration,
            "conflict_resolution": self.conflict_resolution,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimeSavingsConfig":
        """Create from dictionary (handles camelCase from frontend)."""
        return cls(
            pr_review=data.get("prReview", data.get("pr_review", 30)),
            issue_triage=data.get("issueTriage", data.get("issue_triage", 10)),
            idea_generation=data.get("ideaGeneration", data.get("idea_generation", 60)),
            roadmap_planning=data.get("roadmapPlanning", data.get("roadmap_planning", 120)),
            spec_writing=data.get("specWriting", data.get("spec_writing", 180)),
            codebase_exploration=data.get("codebaseExploration", data.get("codebase_exploration", 45)),
            conflict_resolution=data.get("conflictResolution", data.get("conflict_resolution", 20)),
        )


@dataclass
class PreventionValuesConfig:
    """
    Prevention values (estimated cost of bugs/issues in production).

    These values represent the estimated cost of issues that could reach
    production if not caught by AI-assisted review.
    """
    security_critical: float = 10000.0
    security_high: float = 5000.0
    security_medium: float = 1000.0
    performance_critical: float = 5000.0
    performance_high: float = 2000.0
    bug_critical: float = 3000.0
    bug_high: float = 1000.0
    bug_medium: float = 300.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization."""
        return {
            "security_critical": self.security_critical,
            "security_high": self.security_high,
            "security_medium": self.security_medium,
            "performance_critical": self.performance_critical,
            "performance_high": self.performance_high,
            "bug_critical": self.bug_critical,
            "bug_high": self.bug_high,
            "bug_medium": self.bug_medium,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreventionValuesConfig":
        """Create from dictionary (handles camelCase from frontend)."""
        return cls(
            security_critical=data.get("securityCritical", data.get("security_critical", 10000.0)),
            security_high=data.get("securityHigh", data.get("security_high", 5000.0)),
            security_medium=data.get("securityMedium", data.get("security_medium", 1000.0)),
            performance_critical=data.get("performanceCritical", data.get("performance_critical", 5000.0)),
            performance_high=data.get("performanceHigh", data.get("performance_high", 2000.0)),
            bug_critical=data.get("bugCritical", data.get("bug_critical", 3000.0)),
            bug_high=data.get("bugHigh", data.get("bug_high", 1000.0)),
            bug_medium=data.get("bugMedium", data.get("bug_medium", 300.0)),
        )


@dataclass
class QualityMultipliersConfig:
    """
    Quality multipliers for ROI adjustments.

    Values are percentages (e.g., 0.30 = +30%, -0.30 = -30%).
    These multipliers adjust the final ROI based on quality indicators.
    """
    first_pass_qa_bonus: float = 0.30
    second_pass_qa_bonus: float = 0.15
    qa_failed_penalty: float = -0.30
    has_tests_bonus: float = 0.20
    has_docs_bonus: float = 0.10
    has_types_bonus: float = 0.10
    high_coverage_bonus: float = 0.15
    medium_coverage_bonus: float = 0.05
    many_lint_errors_penalty: float = -0.10
    rework_penalty: float = -0.20

    # Clamp values for final multiplier
    min_multiplier: float = 0.5
    max_multiplier: float = 2.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization."""
        return {
            "first_pass_qa_bonus": self.first_pass_qa_bonus,
            "second_pass_qa_bonus": self.second_pass_qa_bonus,
            "qa_failed_penalty": self.qa_failed_penalty,
            "has_tests_bonus": self.has_tests_bonus,
            "has_docs_bonus": self.has_docs_bonus,
            "has_types_bonus": self.has_types_bonus,
            "high_coverage_bonus": self.high_coverage_bonus,
            "medium_coverage_bonus": self.medium_coverage_bonus,
            "many_lint_errors_penalty": self.many_lint_errors_penalty,
            "rework_penalty": self.rework_penalty,
            "min_multiplier": self.min_multiplier,
            "max_multiplier": self.max_multiplier,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityMultipliersConfig":
        """Create from dictionary (handles camelCase from frontend)."""
        return cls(
            first_pass_qa_bonus=data.get("firstPassQaBonus", data.get("first_pass_qa_bonus", 0.30)),
            second_pass_qa_bonus=data.get("secondPassQaBonus", data.get("second_pass_qa_bonus", 0.15)),
            qa_failed_penalty=data.get("qaFailedPenalty", data.get("qa_failed_penalty", -0.30)),
            has_tests_bonus=data.get("hasTestsBonus", data.get("has_tests_bonus", 0.20)),
            has_docs_bonus=data.get("hasDocsBonus", data.get("has_docs_bonus", 0.10)),
            has_types_bonus=data.get("hasTypesBonus", data.get("has_types_bonus", 0.10)),
            high_coverage_bonus=data.get("highCoverageBonus", data.get("high_coverage_bonus", 0.15)),
            medium_coverage_bonus=data.get("mediumCoverageBonus", data.get("medium_coverage_bonus", 0.05)),
            many_lint_errors_penalty=data.get("manyLintErrorsPenalty", data.get("many_lint_errors_penalty", -0.10)),
            rework_penalty=data.get("reworkPenalty", data.get("rework_penalty", -0.20)),
            min_multiplier=data.get("minMultiplier", data.get("min_multiplier", 0.5)),
            max_multiplier=data.get("maxMultiplier", data.get("max_multiplier", 2.0)),
        )


@dataclass
class SquadConfig:
    """
    Complete squad configuration for ROI calculations.

    A squad represents a team with specific hourly rates, time savings estimates,
    prevention values, and quality multipliers.
    """
    id: str
    name: str
    description: str = ""
    stakeholder_rates: Dict[str, float] = field(default_factory=dict)
    default_hourly_rate: float = 150.0
    time_savings: TimeSavingsConfig = field(default_factory=TimeSavingsConfig)
    prevention_values: PreventionValuesConfig = field(default_factory=PreventionValuesConfig)
    quality_multipliers: QualityMultipliersConfig = field(default_factory=QualityMultipliersConfig)
    feature_multipliers: Dict[str, float] = field(default_factory=dict)

    def get_hourly_rate(
        self,
        seniority: Optional[str] = None,
        role: Optional[str] = None
    ) -> float:
        """
        Get hourly rate for a stakeholder type.

        Args:
            seniority: Seniority level (junior, mid, senior, staff, principal)
            role: Role type (developer, qa, devops, pm, architect, tech_lead)

        Returns:
            Hourly rate for the stakeholder type, or default rate if not found.
        """
        if seniority and role:
            key = create_stakeholder_key(seniority, role)
            if key in self.stakeholder_rates:
                return self.stakeholder_rates[key]
        return self.default_hourly_rate

    def get_time_savings(self, activity: str) -> int:
        """
        Get time savings for a specific activity.

        Args:
            activity: Activity name (pr_review, spec_writing, etc.)

        Returns:
            Time savings in minutes for the activity.
        """
        time_savings_dict = self.time_savings.to_dict()
        return time_savings_dict.get(activity, 30)  # Default 30 minutes

    def get_prevention_value(self, category: str) -> float:
        """
        Get prevention value for a specific category.

        Args:
            category: Category name (security_critical, bug_high, etc.)

        Returns:
            Prevention value in USD for the category.
        """
        prevention_dict = self.prevention_values.to_dict()
        return prevention_dict.get(category, 1000.0)  # Default $1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "stakeholderRates": self.stakeholder_rates,
            "defaultHourlyRate": self.default_hourly_rate,
            "timeSavings": {
                "prReview": self.time_savings.pr_review,
                "issueTriage": self.time_savings.issue_triage,
                "ideaGeneration": self.time_savings.idea_generation,
                "roadmapPlanning": self.time_savings.roadmap_planning,
                "specWriting": self.time_savings.spec_writing,
                "codebaseExploration": self.time_savings.codebase_exploration,
                "conflictResolution": self.time_savings.conflict_resolution,
            },
            "preventionValues": {
                "securityCritical": self.prevention_values.security_critical,
                "securityHigh": self.prevention_values.security_high,
                "securityMedium": self.prevention_values.security_medium,
                "performanceCritical": self.prevention_values.performance_critical,
                "performanceHigh": self.prevention_values.performance_high,
                "bugCritical": self.prevention_values.bug_critical,
                "bugHigh": self.prevention_values.bug_high,
                "bugMedium": self.prevention_values.bug_medium,
            },
            "qualityMultipliers": {
                "firstPassQaBonus": self.quality_multipliers.first_pass_qa_bonus,
                "secondPassQaBonus": self.quality_multipliers.second_pass_qa_bonus,
                "qaFailedPenalty": self.quality_multipliers.qa_failed_penalty,
                "hasTestsBonus": self.quality_multipliers.has_tests_bonus,
                "hasDocsBonus": self.quality_multipliers.has_docs_bonus,
                "hasTypesBonus": self.quality_multipliers.has_types_bonus,
                "highCoverageBonus": self.quality_multipliers.high_coverage_bonus,
                "mediumCoverageBonus": self.quality_multipliers.medium_coverage_bonus,
                "manyLintErrorsPenalty": self.quality_multipliers.many_lint_errors_penalty,
                "reworkPenalty": self.quality_multipliers.rework_penalty,
            },
            "featureMultipliers": self.feature_multipliers,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SquadConfig":
        """
        Create SquadConfig from dictionary (JSON parsed).

        Handles both camelCase (from frontend) and snake_case keys.

        Args:
            data: Dictionary with squad configuration

        Returns:
            SquadConfig instance
        """
        time_savings_data = data.get("timeSavings", data.get("time_savings", {}))
        prevention_values_data = data.get("preventionValues", data.get("prevention_values", {}))
        quality_multipliers_data = data.get("qualityMultipliers", data.get("quality_multipliers", {}))

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            stakeholder_rates=data.get("stakeholderRates", data.get("stakeholder_rates", {})),
            default_hourly_rate=data.get("defaultHourlyRate", data.get("default_hourly_rate", 150.0)),
            time_savings=TimeSavingsConfig.from_dict(time_savings_data) if time_savings_data else TimeSavingsConfig(),
            prevention_values=PreventionValuesConfig.from_dict(prevention_values_data) if prevention_values_data else PreventionValuesConfig(),
            quality_multipliers=QualityMultipliersConfig.from_dict(quality_multipliers_data) if quality_multipliers_data else QualityMultipliersConfig(),
            feature_multipliers=data.get("featureMultipliers", data.get("feature_multipliers", {})),
        )


# Default squad configuration (matches current hardcoded values)
DEFAULT_SQUAD_CONFIG = SquadConfig(
    id="default",
    name="Default",
    description="Default squad configuration with standard values",
    default_hourly_rate=150.0,
)


def generate_default_stakeholder_rates() -> Dict[str, float]:
    """
    Generate default stakeholder rates for all seniority x role combinations.

    Returns:
        Dictionary mapping stakeholder keys to hourly rates.
    """
    rates: Dict[str, float] = {}

    # Base rates by seniority
    seniority_base_rates = {
        "junior": 50,
        "mid": 75,
        "senior": 125,
        "staff": 175,
        "principal": 225,
    }

    # Role multipliers (relative to developer baseline)
    role_multipliers = {
        "developer": 1.0,
        "qa": 0.9,
        "devops": 1.1,
        "pm": 0.95,
        "architect": 1.2,
        "tech_lead": 1.15,
    }

    for seniority, base_rate in seniority_base_rates.items():
        for role, multiplier in role_multipliers.items():
            key = create_stakeholder_key(seniority, role)
            rates[key] = round(base_rate * multiplier)

    return rates
