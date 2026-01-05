"""
Cost Avoidance Tracking Module
==============================

Track costs avoided through bug prevention, security fixes, and rework avoidance.
This module captures the value of issues prevented, not just issues fixed.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CostAvoidanceType(Enum):
    """Types of cost avoidance events."""

    BUG_IN_PRODUCTION = "bug_production"  # $500-5000
    SECURITY_BREACH = "security_breach"  # $5000-50000
    REWORK_AVOIDED = "rework_avoided"  # 30% of feature cost
    DUPLICATE_FEATURE = "duplicate_feature"  # 100% of feature cost
    WRONG_ARCHITECTURE = "wrong_architecture"  # 50% of project cost


class Severity(Enum):
    """Severity levels for cost avoidance events."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Cost avoidance values by type and severity (in USD)
AVOIDANCE_VALUES: Dict[str, float] = {
    # Bug in production costs
    "bug_production_critical": 5000.0,
    "bug_production_high": 2500.0,
    "bug_production_medium": 1000.0,
    "bug_production_low": 300.0,
    # Security breach costs
    "security_breach_critical": 50000.0,
    "security_breach_high": 25000.0,
    "security_breach_medium": 10000.0,
    "security_breach_low": 2000.0,
    # Rework costs (percentage multipliers, multiply by feature cost)
    "rework_avoided_critical": 0.50,
    "rework_avoided_high": 0.40,
    "rework_avoided_medium": 0.30,
    "rework_avoided_low": 0.15,
    # Duplicate feature (percentage of feature cost)
    "duplicate_feature_critical": 1.0,
    "duplicate_feature_high": 0.80,
    "duplicate_feature_medium": 0.60,
    "duplicate_feature_low": 0.30,
    # Wrong architecture (percentage of project cost)
    "wrong_architecture_critical": 0.60,
    "wrong_architecture_high": 0.40,
    "wrong_architecture_medium": 0.25,
    "wrong_architecture_low": 0.10,
}


def calculate_avoidance_value(
    avoidance_type: CostAvoidanceType,
    severity: Severity,
    base_cost: Optional[float] = None,
) -> float:
    """
    Calculate the estimated cost avoided based on type and severity.

    Args:
        avoidance_type: The type of cost avoidance
        severity: The severity level
        base_cost: For percentage-based types (rework, duplicate, architecture),
                   provide the base cost to calculate from

    Returns:
        Estimated cost avoided in USD
    """
    key = f"{avoidance_type.value}_{severity.value}"
    value = AVOIDANCE_VALUES.get(key, 0.0)

    # For types that use percentage multipliers
    if avoidance_type in (
        CostAvoidanceType.REWORK_AVOIDED,
        CostAvoidanceType.DUPLICATE_FEATURE,
        CostAvoidanceType.WRONG_ARCHITECTURE,
    ):
        if base_cost is not None and base_cost > 0:
            return value * base_cost
        # Default base costs if not provided
        default_base_costs = {
            CostAvoidanceType.REWORK_AVOIDED: 2000.0,  # Assume $2000 feature
            CostAvoidanceType.DUPLICATE_FEATURE: 3000.0,  # Assume $3000 feature
            CostAvoidanceType.WRONG_ARCHITECTURE: 10000.0,  # Assume $10000 project
        }
        return value * default_base_costs.get(avoidance_type, 1000.0)

    return value


@dataclass
class CostAvoidanceEvent:
    """Represents a single cost avoidance event."""

    type: CostAvoidanceType
    severity: Severity
    estimated_cost_avoided: float
    confidence: float  # 0.0 to 1.0
    detected_by: str  # qa_reviewer, security_scan, ideation, spec_creation, etc.
    trace_id: str
    id: str = field(default_factory=lambda: f"cae_{uuid.uuid4().hex[:12]}")
    artifact_id: Optional[str] = None
    spec_id: Optional[str] = None
    project_id: Optional[str] = None
    description: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for storage."""
        return {
            "id": self.id,
            "type": self.type.value,
            "severity": self.severity.value,
            "estimated_cost_avoided": self.estimated_cost_avoided,
            "confidence": self.confidence,
            "detected_by": self.detected_by,
            "trace_id": self.trace_id,
            "artifact_id": self.artifact_id,
            "spec_id": self.spec_id,
            "project_id": self.project_id,
            "description": self.description,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostAvoidanceEvent":
        """Create event from dictionary."""
        return cls(
            id=data.get("id", f"cae_{uuid.uuid4().hex[:12]}"),
            type=CostAvoidanceType(data["type"]),
            severity=Severity(data["severity"]),
            estimated_cost_avoided=data["estimated_cost_avoided"],
            confidence=data["confidence"],
            detected_by=data["detected_by"],
            trace_id=data["trace_id"],
            artifact_id=data.get("artifact_id"),
            spec_id=data.get("spec_id"),
            project_id=data.get("project_id"),
            description=data.get("description"),
            evidence=data.get("evidence", {}),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.utcnow(),
        )


@dataclass
class CostAvoidanceSummary:
    """Summary of cost avoidance data for a project."""

    total_cost_avoided: float
    event_count: int
    by_type: Dict[str, float]
    by_severity: Dict[str, float]
    by_detector: Dict[str, float]
    avg_confidence: float
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    events: List[CostAvoidanceEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "total_cost_avoided": self.total_cost_avoided,
            "event_count": self.event_count,
            "by_type": self.by_type,
            "by_severity": self.by_severity,
            "by_detector": self.by_detector,
            "avg_confidence": self.avg_confidence,
            "period_start": self.period_start.isoformat()
            if self.period_start
            else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "events": [e.to_dict() for e in self.events],
        }


class CostAvoidanceTracker:
    """
    Tracks cost avoidance events and provides aggregation.

    Stores events in a local JSON file within the project's .auto-claude directory.
    """

    def __init__(self, project_dir: Path):
        """
        Initialize the cost avoidance tracker.

        Args:
            project_dir: Root directory of the project
        """
        self.project_dir = Path(project_dir)
        self.storage_dir = self.project_dir / ".auto-claude" / "analytics"
        self.events_file = self.storage_dir / "cost_avoidance_events.json"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure storage directory exists."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _load_events(self) -> List[CostAvoidanceEvent]:
        """Load events from storage file."""
        if not self.events_file.exists():
            return []

        try:
            with open(self.events_file, "r") as f:
                data = json.load(f)
                return [CostAvoidanceEvent.from_dict(e) for e in data.get("events", [])]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Error loading cost avoidance events: {e}")
            return []

    def _save_events(self, events: List[CostAvoidanceEvent]) -> None:
        """Save events to storage file."""
        try:
            data = {"events": [e.to_dict() for e in events]}
            with open(self.events_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cost avoidance events: {e}")

    def record_event(self, event: CostAvoidanceEvent) -> str:
        """
        Record a cost avoidance event.

        Args:
            event: The event to record

        Returns:
            The event ID
        """
        events = self._load_events()
        events.append(event)
        self._save_events(events)

        logger.info(
            f"Recorded cost avoidance event: {event.type.value} "
            f"(${event.estimated_cost_avoided:.2f}, {event.severity.value})"
        )

        return event.id

    def record_bug_prevention(
        self,
        severity: Severity,
        detected_by: str,
        trace_id: str,
        description: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        confidence: float = 0.8,
        spec_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
    ) -> str:
        """
        Record a bug prevention event.

        Convenience method for the common case of preventing a bug.
        """
        estimated_cost = calculate_avoidance_value(
            CostAvoidanceType.BUG_IN_PRODUCTION, severity
        )

        event = CostAvoidanceEvent(
            type=CostAvoidanceType.BUG_IN_PRODUCTION,
            severity=severity,
            estimated_cost_avoided=estimated_cost,
            confidence=confidence,
            detected_by=detected_by,
            trace_id=trace_id,
            spec_id=spec_id,
            artifact_id=artifact_id,
            description=description,
            evidence=evidence or {},
            project_id=self.project_dir.name,
        )

        return self.record_event(event)

    def record_security_fix(
        self,
        severity: Severity,
        detected_by: str,
        trace_id: str,
        vulnerability_type: Optional[str] = None,
        description: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        confidence: float = 0.85,
        spec_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
    ) -> str:
        """
        Record a security fix event.

        Convenience method for security-related cost avoidance.
        """
        estimated_cost = calculate_avoidance_value(
            CostAvoidanceType.SECURITY_BREACH, severity
        )

        event_evidence = evidence or {}
        if vulnerability_type:
            event_evidence["vulnerability_type"] = vulnerability_type

        event = CostAvoidanceEvent(
            type=CostAvoidanceType.SECURITY_BREACH,
            severity=severity,
            estimated_cost_avoided=estimated_cost,
            confidence=confidence,
            detected_by=detected_by,
            trace_id=trace_id,
            spec_id=spec_id,
            artifact_id=artifact_id,
            description=description,
            evidence=event_evidence,
            project_id=self.project_dir.name,
        )

        return self.record_event(event)

    def record_rework_avoided(
        self,
        severity: Severity,
        detected_by: str,
        trace_id: str,
        feature_cost: Optional[float] = None,
        description: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        confidence: float = 0.7,
        spec_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
    ) -> str:
        """
        Record a rework avoidance event.

        Used when catching issues during spec/ideation that would have required rework.
        """
        estimated_cost = calculate_avoidance_value(
            CostAvoidanceType.REWORK_AVOIDED, severity, feature_cost
        )

        event = CostAvoidanceEvent(
            type=CostAvoidanceType.REWORK_AVOIDED,
            severity=severity,
            estimated_cost_avoided=estimated_cost,
            confidence=confidence,
            detected_by=detected_by,
            trace_id=trace_id,
            spec_id=spec_id,
            artifact_id=artifact_id,
            description=description,
            evidence=evidence or {},
            project_id=self.project_dir.name,
        )

        return self.record_event(event)

    def get_events(
        self,
        days: Optional[int] = None,
        avoidance_type: Optional[CostAvoidanceType] = None,
        severity: Optional[Severity] = None,
        spec_id: Optional[str] = None,
    ) -> List[CostAvoidanceEvent]:
        """
        Get cost avoidance events with optional filtering.

        Args:
            days: Only include events from the last N days
            avoidance_type: Filter by type
            severity: Filter by severity
            spec_id: Filter by spec ID

        Returns:
            List of matching events
        """
        events = self._load_events()

        if days is not None:
            cutoff = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            from datetime import timedelta

            cutoff = cutoff - timedelta(days=days)
            events = [e for e in events if e.created_at >= cutoff]

        if avoidance_type is not None:
            events = [e for e in events if e.type == avoidance_type]

        if severity is not None:
            events = [e for e in events if e.severity == severity]

        if spec_id is not None:
            events = [e for e in events if e.spec_id == spec_id]

        return sorted(events, key=lambda e: e.created_at, reverse=True)

    def get_summary(
        self,
        days: int = 30,
        spec_id: Optional[str] = None,
    ) -> CostAvoidanceSummary:
        """
        Get aggregated cost avoidance summary.

        Args:
            days: Number of days to include (default 30)
            spec_id: Optional spec ID to filter by

        Returns:
            Aggregated summary of cost avoidance data
        """
        events = self.get_events(days=days, spec_id=spec_id)

        if not events:
            return CostAvoidanceSummary(
                total_cost_avoided=0.0,
                event_count=0,
                by_type={},
                by_severity={},
                by_detector={},
                avg_confidence=0.0,
                events=[],
            )

        # Calculate aggregates
        total_cost = sum(e.estimated_cost_avoided for e in events)
        avg_confidence = sum(e.confidence for e in events) / len(events)

        by_type: Dict[str, float] = {}
        by_severity: Dict[str, float] = {}
        by_detector: Dict[str, float] = {}

        for event in events:
            type_key = event.type.value
            by_type[type_key] = by_type.get(type_key, 0.0) + event.estimated_cost_avoided

            severity_key = event.severity.value
            by_severity[severity_key] = (
                by_severity.get(severity_key, 0.0) + event.estimated_cost_avoided
            )

            by_detector[event.detected_by] = (
                by_detector.get(event.detected_by, 0.0) + event.estimated_cost_avoided
            )

        # Determine period
        dates = [e.created_at for e in events]
        period_start = min(dates) if dates else None
        period_end = max(dates) if dates else None

        return CostAvoidanceSummary(
            total_cost_avoided=total_cost,
            event_count=len(events),
            by_type=by_type,
            by_severity=by_severity,
            by_detector=by_detector,
            avg_confidence=avg_confidence,
            period_start=period_start,
            period_end=period_end,
            events=events,
        )


# =============================================================================
# Module-level convenience functions
# =============================================================================

_tracker_cache: Dict[str, CostAvoidanceTracker] = {}


def get_tracker(project_dir: Path) -> CostAvoidanceTracker:
    """
    Get or create a cost avoidance tracker for a project.

    Args:
        project_dir: Root directory of the project

    Returns:
        CostAvoidanceTracker instance for the project
    """
    key = str(project_dir)
    if key not in _tracker_cache:
        _tracker_cache[key] = CostAvoidanceTracker(project_dir)
    return _tracker_cache[key]


def record_bug_prevention(
    project_dir: Path,
    severity: str,
    detected_by: str,
    trace_id: str,
    description: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
    confidence: float = 0.8,
    spec_id: Optional[str] = None,
    artifact_id: Optional[str] = None,
) -> str:
    """
    Record a bug prevention event.

    Module-level convenience function.
    """
    tracker = get_tracker(project_dir)
    severity_enum = Severity(severity.lower()) if isinstance(severity, str) else severity
    return tracker.record_bug_prevention(
        severity=severity_enum,
        detected_by=detected_by,
        trace_id=trace_id,
        description=description,
        evidence=evidence,
        confidence=confidence,
        spec_id=spec_id,
        artifact_id=artifact_id,
    )


def record_security_fix(
    project_dir: Path,
    severity: str,
    detected_by: str,
    trace_id: str,
    vulnerability_type: Optional[str] = None,
    description: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
    confidence: float = 0.85,
    spec_id: Optional[str] = None,
    artifact_id: Optional[str] = None,
) -> str:
    """
    Record a security fix event.

    Module-level convenience function.
    """
    tracker = get_tracker(project_dir)
    severity_enum = Severity(severity.lower()) if isinstance(severity, str) else severity
    return tracker.record_security_fix(
        severity=severity_enum,
        detected_by=detected_by,
        trace_id=trace_id,
        vulnerability_type=vulnerability_type,
        description=description,
        evidence=evidence,
        confidence=confidence,
        spec_id=spec_id,
        artifact_id=artifact_id,
    )


def get_cost_avoidance_summary(
    project_dir: Path,
    days: int = 30,
    spec_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get cost avoidance summary for a project.

    Module-level convenience function.

    Returns:
        Dictionary with summary data
    """
    tracker = get_tracker(project_dir)
    summary = tracker.get_summary(days=days, spec_id=spec_id)
    return summary.to_dict()
