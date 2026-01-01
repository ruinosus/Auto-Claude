"""
Unified ROI Calculator
=======================

Calculates ROI for any Auto-Claude feature using the unified ROI model.

This calculator aggregates value from multiple dimensions:
- Execution value (direct work done)
- Decision value (strategic choices)
- Prevention value (problems avoided)
- Knowledge value (learning gained)

Usage:
    from analytics.unified_roi_calculator import UnifiedROICalculator

    calculator = UnifiedROICalculator(hourly_rate=150.0)

    # Calculate ROI for ideation
    roi = calculator.calculate_ideation_roi(
        feature_type=FeatureType.IDEATION_SECURITY,
        ideas_generated=5,
        high_impact_ideas=2,
        cost_usd=0.05,
        tokens=1000,
    )

    # Calculate ROI for roadmap
    roi = calculator.calculate_roadmap_roi(
        features_identified=10,
        features_rejected=3,
        cost_usd=0.10,
        tokens=2000,
    )
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .roi_model import (
    UnifiedROI,
    ValueType,
    FeatureType,
    CostMetrics,
    IdeationMetrics,
    RoadmapMetrics,
    SpecMetrics,
    BuildMetrics,
    GitHubMetrics,
    InsightsMetrics,
    MergeMetrics,
    DEFAULT_HOURLY_RATE,
    VALUE_MULTIPLIERS,
    TIME_SAVINGS,
    PREVENTION_VALUES,
    estimate_ideation_value,
    estimate_roadmap_value,
    estimate_github_value,
)

logger = logging.getLogger(__name__)


class UnifiedROICalculator:
    """
    Unified ROI calculator for all Auto-Claude features.

    Handles the complexity of calculating ROI across different feature types,
    each with their own value dimensions.
    """

    def __init__(
        self,
        hourly_rate: float = DEFAULT_HOURLY_RATE,
        avg_feature_cost: float = 5000.0,
    ):
        """
        Initialize the calculator.

        Args:
            hourly_rate: Developer hourly rate for time-based calculations
            avg_feature_cost: Average cost to implement a feature (for roadmap)
        """
        self.hourly_rate = hourly_rate
        self.avg_feature_cost = avg_feature_cost

    def calculate_ideation_roi(
        self,
        feature_type: FeatureType,
        ideas_generated: int,
        high_impact_ideas: int = 0,
        ideas_implemented: int = 0,
        cost_usd: float = 0.0,
        tokens: int = 0,
        duration_seconds: float = 0.0,
        model: str = "",
        spec_id: Optional[str] = None,
        project_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ) -> UnifiedROI:
        """
        Calculate ROI for ideation features.

        Ideation generates value through:
        - DECISION: Identifying what to focus on
        - PREVENTION: Finding security/performance issues early
        - KNOWLEDGE: Learning about the codebase
        """
        # Default high impact to 20% of ideas if not specified
        if high_impact_ideas == 0 and ideas_generated > 0:
            high_impact_ideas = max(1, ideas_generated // 5)

        # Calculate value breakdown
        value_breakdown = estimate_ideation_value(
            ideation_type=feature_type,
            ideas_count=ideas_generated,
            high_impact_count=high_impact_ideas,
            hourly_rate=self.hourly_rate,
        )

        # Create metrics
        ideation_metrics = IdeationMetrics(
            ideas_generated=ideas_generated,
            high_impact_ideas=high_impact_ideas,
            ideas_implemented=ideas_implemented,
            categories=categories or [],
        )

        # Create unified ROI
        roi = UnifiedROI(
            feature_type=feature_type,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
            cost=CostMetrics(
                total_tokens=tokens,
                total_cost_usd=cost_usd,
                duration_seconds=duration_seconds,
                model=model,
            ),
            value_breakdown=value_breakdown,
            ideation_metrics=ideation_metrics,
            confidence_score=0.7,  # Ideation has moderate confidence
            tags=["ideation", feature_type.value],
        )

        roi.calculate_total_value()
        roi.calculate_roi()

        return roi

    def calculate_roadmap_roi(
        self,
        features_identified: int,
        features_prioritized: int = 0,
        features_rejected: int = 0,
        competitor_insights: int = 0,
        cost_usd: float = 0.0,
        tokens: int = 0,
        duration_seconds: float = 0.0,
        model: str = "",
        spec_id: Optional[str] = None,
        project_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> UnifiedROI:
        """
        Calculate ROI for roadmap features.

        Roadmap generates value through:
        - DECISION: Prioritizing what to build first
        - PREVENTION: Deciding NOT to build low-value features
        - KNOWLEDGE: Understanding market and competitors
        """
        # Calculate value breakdown
        value_breakdown = estimate_roadmap_value(
            features_identified=features_identified,
            features_rejected=features_rejected,
            avg_feature_cost=self.avg_feature_cost,
            hourly_rate=self.hourly_rate,
        )

        # Create metrics
        roadmap_metrics = RoadmapMetrics(
            features_identified=features_identified,
            features_prioritized=features_prioritized,
            features_rejected=features_rejected,
            competitor_insights=competitor_insights,
        )

        # Determine feature type
        feature_type = FeatureType.ROADMAP_FEATURES
        if competitor_insights > 0:
            feature_type = FeatureType.ROADMAP_COMPETITOR

        # Create unified ROI
        roi = UnifiedROI(
            feature_type=feature_type,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
            cost=CostMetrics(
                total_tokens=tokens,
                total_cost_usd=cost_usd,
                duration_seconds=duration_seconds,
                model=model,
            ),
            value_breakdown=value_breakdown,
            roadmap_metrics=roadmap_metrics,
            confidence_score=0.6,  # Roadmap has lower confidence (strategic estimates)
            tags=["roadmap", feature_type.value],
        )

        roi.calculate_total_value()
        roi.calculate_roi()

        return roi

    def calculate_spec_roi(
        self,
        phases_completed: int,
        requirements_gathered: int = 0,
        complexity_level: str = "standard",
        refinement_iterations: int = 0,
        cost_usd: float = 0.0,
        tokens: int = 0,
        duration_seconds: float = 0.0,
        model: str = "",
        spec_id: Optional[str] = None,
        project_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> UnifiedROI:
        """
        Calculate ROI for spec creation.

        Spec generates value through:
        - EXECUTION: Time saved writing specs manually
        - DECISION: Clarity on what to build
        - PREVENTION: Less rework from unclear requirements
        """
        value_breakdown = {}

        # Time saved on spec writing
        spec_hours = TIME_SAVINGS["spec_writing"] / 60
        value_breakdown[ValueType.EXECUTION] = spec_hours * self.hourly_rate * 0.6

        # Decision value: clarity reduces scope creep
        complexity_multiplier = {"simple": 0.5, "standard": 1.0, "complex": 1.5}
        mult = complexity_multiplier.get(complexity_level, 1.0)
        value_breakdown[ValueType.DECISION] = requirements_gathered * 30 * mult

        # Prevention: fewer iterations = better spec quality
        if refinement_iterations <= 1:
            value_breakdown[ValueType.PREVENTION] = 200  # Good first-pass spec

        # Create metrics
        spec_metrics = SpecMetrics(
            phases_completed=phases_completed,
            requirements_gathered=requirements_gathered,
            complexity_level=complexity_level,
            refinement_iterations=refinement_iterations,
        )

        # Create unified ROI
        roi = UnifiedROI(
            feature_type=FeatureType.SPEC_WRITER,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
            cost=CostMetrics(
                total_tokens=tokens,
                total_cost_usd=cost_usd,
                duration_seconds=duration_seconds,
                model=model,
            ),
            value_breakdown=value_breakdown,
            spec_metrics=spec_metrics,
            confidence_score=0.75,
            tags=["spec", complexity_level],
        )

        roi.calculate_total_value()
        roi.calculate_roi()

        return roi

    def calculate_build_roi(
        self,
        lines_added: int,
        lines_removed: int,
        files_changed: int,
        qa_attempts: int = 0,
        qa_passed: bool = False,
        subtasks_completed: int = 0,
        subtasks_total: int = 0,
        cost_usd: float = 0.0,
        tokens: int = 0,
        duration_seconds: float = 0.0,
        model: str = "",
        spec_id: Optional[str] = None,
        project_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> UnifiedROI:
        """
        Calculate ROI for build (code generation).

        Build generates value through:
        - EXECUTION: Code written, dev hours saved
        - PREVENTION: QA catches bugs before production
        """
        value_breakdown = {}

        # Execution value: lines of code generated
        # Estimate: 20 lines per hour for a developer
        total_lines = lines_added + lines_removed
        estimated_dev_hours = total_lines / 20.0

        # Quality multiplier based on QA success
        quality_multiplier = 1.0
        if qa_passed:
            if qa_attempts <= 1:
                quality_multiplier = 1.2  # First-pass success bonus
            elif qa_attempts <= 3:
                quality_multiplier = 1.0
            else:
                quality_multiplier = 0.8  # Many attempts = lower quality
        else:
            quality_multiplier = 0.5  # QA failed

        value_breakdown[ValueType.EXECUTION] = (
            estimated_dev_hours * self.hourly_rate * quality_multiplier
        )

        # Prevention value: QA prevents bugs
        if qa_passed:
            bugs_prevented = max(1, files_changed // 2)  # Estimate
            value_breakdown[ValueType.PREVENTION] = (
                bugs_prevented * PREVENTION_VALUES["bug_medium"] * 0.1
            )

        # Create metrics
        build_metrics = BuildMetrics(
            lines_added=lines_added,
            lines_removed=lines_removed,
            files_changed=files_changed,
            subtasks_completed=subtasks_completed,
            subtasks_total=subtasks_total,
            qa_attempts=qa_attempts,
            qa_passed=qa_passed,
            first_pass_success=qa_passed and qa_attempts <= 1,
        )

        # Create unified ROI
        roi = UnifiedROI(
            feature_type=FeatureType.BUILD_CODER,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
            cost=CostMetrics(
                total_tokens=tokens,
                total_cost_usd=cost_usd,
                duration_seconds=duration_seconds,
                model=model,
            ),
            value_breakdown=value_breakdown,
            build_metrics=build_metrics,
            confidence_score=0.85 if qa_passed else 0.5,
            tags=["build", "coder"],
        )

        roi.calculate_total_value()
        roi.calculate_roi()

        return roi

    def calculate_github_roi(
        self,
        prs_reviewed: int = 0,
        issues_triaged: int = 0,
        issues_auto_fixed: int = 0,
        duplicates_detected: int = 0,
        spam_detected: int = 0,
        cost_usd: float = 0.0,
        tokens: int = 0,
        duration_seconds: float = 0.0,
        model: str = "",
        spec_id: Optional[str] = None,
        project_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> UnifiedROI:
        """
        Calculate ROI for GitHub automation.

        GitHub automation generates value through:
        - EXECUTION: Time saved on reviews and triage
        - DECISION: Auto-fixing issues
        - PREVENTION: Catching duplicates and spam
        """
        value_breakdown = estimate_github_value(
            prs_reviewed=prs_reviewed,
            issues_triaged=issues_triaged,
            issues_auto_fixed=issues_auto_fixed,
            hourly_rate=self.hourly_rate,
        )

        # Add prevention value for duplicates/spam
        value_breakdown[ValueType.PREVENTION] = (
            (duplicates_detected + spam_detected) * 20  # $20 per avoided duplicate
        )

        # Create metrics
        github_metrics = GitHubMetrics(
            prs_reviewed=prs_reviewed,
            issues_triaged=issues_triaged,
            issues_auto_fixed=issues_auto_fixed,
            duplicates_detected=duplicates_detected,
            spam_detected=spam_detected,
            estimated_review_time_saved_minutes=prs_reviewed * TIME_SAVINGS["pr_review"],
            estimated_triage_time_saved_minutes=issues_triaged * TIME_SAVINGS["issue_triage"],
        )

        # Determine feature type
        if prs_reviewed > 0:
            feature_type = FeatureType.GITHUB_PR_REVIEW
        elif issues_triaged > 0:
            feature_type = FeatureType.GITHUB_ISSUE_TRIAGE
        else:
            feature_type = FeatureType.GITHUB_BATCH_ISSUES

        # Create unified ROI
        roi = UnifiedROI(
            feature_type=feature_type,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
            cost=CostMetrics(
                total_tokens=tokens,
                total_cost_usd=cost_usd,
                duration_seconds=duration_seconds,
                model=model,
            ),
            value_breakdown=value_breakdown,
            github_metrics=github_metrics,
            confidence_score=0.8,
            tags=["github", feature_type.value],
        )

        roi.calculate_total_value()
        roi.calculate_roi()

        return roi

    def calculate_insights_roi(
        self,
        messages_exchanged: int,
        tasks_suggested: int = 0,
        tasks_accepted: int = 0,
        files_explored: int = 0,
        cost_usd: float = 0.0,
        tokens: int = 0,
        duration_seconds: float = 0.0,
        model: str = "",
        spec_id: Optional[str] = None,
        project_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        # Additional value metrics (detected from response)
        diagrams_generated: int = 0,
        security_insights: int = 0,
        recommendations_count: int = 0,
        code_explanations: int = 0,
    ) -> UnifiedROI:
        """
        Calculate ROI for insights/chat features.

        Insights generate value through:
        - KNOWLEDGE: Learning about the codebase, diagrams, code explanations
        - DECISION: Suggestions that lead to tasks, recommendations
        - PREVENTION: Security insights
        """
        value_breakdown = {}

        # Knowledge value: exploration time saved + diagrams + code explanations
        exploration_hours = TIME_SAVINGS["codebase_exploration"] / 60
        knowledge_value = exploration_hours * self.hourly_rate * 0.4 * (files_explored / 10)

        # Add diagram value ($150 per diagram - saves time understanding architecture)
        knowledge_value += diagrams_generated * 150

        # Add code explanation value ($25 per code block explained)
        knowledge_value += code_explanations * 25

        value_breakdown[ValueType.KNOWLEDGE] = knowledge_value

        # Decision value: tasks suggested and accepted + recommendations
        decision_value = 0
        if tasks_accepted > 0:
            decision_value += tasks_accepted * 100  # $100 per accepted task
        # Add recommendation value ($50 per recommendation made)
        decision_value += recommendations_count * 50
        if decision_value > 0:
            value_breakdown[ValueType.DECISION] = decision_value

        # Prevention value: security insights ($200 per security issue identified)
        if security_insights > 0:
            value_breakdown[ValueType.PREVENTION] = security_insights * 200

        # Create metrics
        insights_metrics = InsightsMetrics(
            messages_exchanged=messages_exchanged,
            tasks_suggested=tasks_suggested,
            tasks_accepted=tasks_accepted,
            files_explored=files_explored,
            estimated_exploration_time_saved_minutes=files_explored * 5,
        )

        # Create unified ROI
        roi = UnifiedROI(
            feature_type=FeatureType.INSIGHTS_CHAT,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
            cost=CostMetrics(
                total_tokens=tokens,
                total_cost_usd=cost_usd,
                duration_seconds=duration_seconds,
                model=model,
            ),
            value_breakdown=value_breakdown,
            insights_metrics=insights_metrics,
            confidence_score=0.6,
            tags=["insights", "chat"],
        )

        roi.calculate_total_value()
        roi.calculate_roi()

        return roi

    def calculate_merge_roi(
        self,
        conflicts_resolved: int,
        files_merged: int = 0,
        manual_intervention_avoided: int = 0,
        merge_decisions: int = 0,
        code_choices: int = 0,
        cost_usd: float = 0.0,
        tokens: int = 0,
        duration_seconds: float = 0.0,
        model: str = "",
        spec_id: Optional[str] = None,
        project_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> UnifiedROI:
        """
        Calculate ROI for merge conflict resolution.

        Merge resolution generates value through:
        - EXECUTION: Time saved resolving conflicts manually
        - DECISION: Merge strategy decisions (ours/theirs/combined)
        - PREVENTION: Avoiding manual intervention and merge errors
        """
        value_breakdown = {}

        # Execution value: time saved on conflict resolution
        # Each conflict takes ~20 minutes to resolve manually
        resolution_hours = (conflicts_resolved * TIME_SAVINGS["conflict_resolution"]) / 60
        value_breakdown[ValueType.EXECUTION] = resolution_hours * self.hourly_rate

        # Decision value: merge decisions and code choices
        # $75 per merge decision (ours/theirs/combined)
        # $50 per code choice made
        decision_value = (merge_decisions * 75) + (code_choices * 50)
        if decision_value > 0:
            value_breakdown[ValueType.DECISION] = decision_value

        # Prevention value: avoiding manual intervention
        # Manual intervention costs more time and has higher error risk
        if manual_intervention_avoided > 0:
            # Each avoided intervention saves ~30 minutes + reduces error risk
            prevention_hours = (manual_intervention_avoided * 30) / 60
            value_breakdown[ValueType.PREVENTION] = prevention_hours * self.hourly_rate * 0.5

        # Create metrics
        merge_metrics = MergeMetrics(
            conflicts_resolved=conflicts_resolved,
            files_merged=files_merged,
            manual_intervention_avoided=manual_intervention_avoided,
            merge_decisions=merge_decisions,
            code_choices=code_choices,
            estimated_resolution_time_saved_minutes=conflicts_resolved * TIME_SAVINGS["conflict_resolution"],
        )

        # Create unified ROI
        roi = UnifiedROI(
            feature_type=FeatureType.MERGE_RESOLVER,
            spec_id=spec_id,
            project_id=project_id,
            trace_id=trace_id,
            cost=CostMetrics(
                total_tokens=tokens,
                total_cost_usd=cost_usd,
                duration_seconds=duration_seconds,
                model=model,
            ),
            value_breakdown=value_breakdown,
            merge_metrics=merge_metrics,
            confidence_score=0.75,  # High confidence - measurable outcomes
            tags=["merge", "conflict_resolution"],
        )

        roi.calculate_total_value()
        roi.calculate_roi()

        return roi

    def aggregate_project_roi(
        self,
        roi_list: List[UnifiedROI],
    ) -> Dict[str, Any]:
        """
        Aggregate ROI across multiple features for a project summary.

        Returns:
            Dict with total ROI, breakdown by feature type, and by value type
        """
        total_cost = sum(r.cost.total_cost_usd for r in roi_list)
        total_value = sum(r.total_value_usd for r in roi_list)

        # Aggregate by feature type
        by_feature_type: Dict[str, Dict[str, float]] = {}
        for roi in roi_list:
            ft = roi.feature_type.value
            if ft not in by_feature_type:
                by_feature_type[ft] = {"cost": 0.0, "value": 0.0, "count": 0}
            by_feature_type[ft]["cost"] += roi.cost.total_cost_usd
            by_feature_type[ft]["value"] += roi.total_value_usd
            by_feature_type[ft]["count"] += 1

        # Aggregate by value type
        by_value_type: Dict[str, float] = {}
        for roi in roi_list:
            for vt, value in roi.value_breakdown.items():
                vt_name = vt.value
                by_value_type[vt_name] = by_value_type.get(vt_name, 0) + value

        # Calculate overall ROI
        overall_roi = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

        return {
            "total_cost_usd": total_cost,
            "total_value_usd": total_value,
            "net_value_usd": total_value - total_cost,
            "overall_roi_percentage": overall_roi,
            "feature_count": len(roi_list),
            "by_feature_type": by_feature_type,
            "by_value_type": by_value_type,
            "avg_confidence": sum(r.confidence_score for r in roi_list) / len(roi_list) if roi_list else 0,
        }
