"""
Feature usage tracker for Claude Agent SDK sessions.

Tracks token consumption and costs for feature-based sessions
(roadmap, ideation, insights, github, changelog, etc.) separately
from spec-based sessions.
"""

from typing import Optional, Set, Dict, Any
from datetime import datetime
import uuid

from .pricing_provider import get_model_pricing
from .storage import AnalyticsStorage, get_analytics_storage, is_tracking_enabled
from .otel_exporter import get_otel_exporter, is_otel_enabled


# Feature type constants
FEATURE_ROADMAP = 'roadmap'
FEATURE_IDEATION = 'ideation'
FEATURE_INSIGHTS = 'insights'
FEATURE_PR_REVIEW = 'pr_review'
FEATURE_ISSUE_TRIAGE = 'issue_triage'
FEATURE_AUTOFIX = 'autofix'
FEATURE_CHANGELOG = 'changelog'


class FeatureUsageTracker:
    """
    Tracks token usage and costs for feature sessions.

    Similar to UsageTracker but designed for non-spec features like
    roadmap, ideation, insights, and GitHub automation.

    Features:
    - Deduplicates messages with same ID
    - Enriches data with feature-specific metadata
    - Calculates costs using models.dev pricing
    - Async writes to minimize performance impact
    """

    def __init__(
        self,
        project_id: str,
        feature_type: str,
        storage: Optional[AnalyticsStorage] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.project_id = project_id
        self.feature_type = feature_type
        self.storage = storage or get_analytics_storage()
        self.metadata = metadata or {}

        # Deduplication
        self.message_ids_seen: Set[str] = set()

        # Context
        self.session_id: Optional[int] = None
        self.primary_model: Optional[str] = None

        # Session totals
        self.session_start = datetime.utcnow()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0

    async def start_session(self) -> int:
        """Initialize feature session tracking. Returns session_id."""
        if not is_tracking_enabled():
            return -1

        self.session_id = await self.storage.create_feature_session(
            project_id=self.project_id,
            feature_type=self.feature_type,
            started_at=self.session_start,
            model=self.primary_model,
            metadata=self.metadata
        )

        # Track session start in OTel
        if is_otel_enabled():
            try:
                otel_exporter = get_otel_exporter()
                otel_exporter.start_session()
            except Exception:
                pass

        return self.session_id

    async def track_message(self, message):
        """
        Track token usage from Claude Agent SDK message.

        Accepts:
        - AssistantMessage (with usage data)
        - ResultMessage (with total cost)
        """
        if not is_tracking_enabled():
            return

        # Import here to avoid circular dependency
        try:
            from claude_agent_sdk import AssistantMessage, ResultMessage
        except ImportError:
            # Fallback: check message type by attributes
            if hasattr(message, 'usage') and hasattr(message, 'id'):
                await self._track_assistant_message(message)
            elif hasattr(message, 'total_cost_usd'):
                await self._track_result_message(message)
            return

        # AssistantMessage: individual message-level tracking
        if isinstance(message, AssistantMessage):
            await self._track_assistant_message(message)

        # ResultMessage: session-level totals
        elif isinstance(message, ResultMessage):
            await self._track_result_message(message)

    async def _track_assistant_message(self, message):
        """Track individual assistant message."""
        if not hasattr(message, 'usage') or not message.usage:
            return

        # Skip duplicates (same message ID reported multiple times)
        if hasattr(message, 'id') and message.id in self.message_ids_seen:
            return

        if hasattr(message, 'id'):
            self.message_ids_seen.add(message.id)

        # Extract usage data
        usage = message.usage
        if isinstance(usage, dict):
            input_tokens = usage.get('input_tokens', 0) or 0
            output_tokens = usage.get('output_tokens', 0) or 0
            cache_read = usage.get('cache_read_input_tokens', 0) or 0
            cache_creation = usage.get('cache_creation_input_tokens', 0) or 0
        else:
            # Handle object-style usage
            input_tokens = getattr(usage, 'input_tokens', 0) or 0
            output_tokens = getattr(usage, 'output_tokens', 0) or 0
            cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
            cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0

        # Get model
        model = getattr(message, 'model', 'claude-sonnet-4-5')
        if not self.primary_model:
            self.primary_model = model

        # Calculate cost
        cost_usd = await self._calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation
        )

        # Record message-level data
        if self.session_id and self.session_id > 0:
            message_id = getattr(message, 'id', f'feat_{uuid.uuid4().hex[:12]}')
            await self.storage.record_feature_message(
                session_id=self.session_id,
                message_id=message_id,
                timestamp=datetime.utcnow(),
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read,
                cache_creation_tokens=cache_creation,
                cost_usd=cost_usd
            )

        # Update session totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost_usd

        # Export to OpenTelemetry (if enabled)
        if is_otel_enabled():
            try:
                otel_exporter = get_otel_exporter()
                otel_exporter.record_message(
                    spec_id=f"feature:{self.feature_type}:{self.project_id}",
                    phase=self.feature_type,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd
                )
            except Exception:
                # Don't fail tracking if OTel export fails
                pass

    async def _track_result_message(self, message):
        """Track final result message with totals."""
        if not self.session_id or self.session_id < 0:
            return

        total_cost = getattr(message, 'total_cost_usd', None) or self.total_cost_usd

        await self.storage.update_feature_session_totals(
            session_id=self.session_id,
            ended_at=datetime.utcnow(),
            total_cost_usd=total_cost,
            total_input_tokens=self.total_input_tokens,
            total_output_tokens=self.total_output_tokens,
            model=self.primary_model,
            metadata=self.metadata
        )

    async def track_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0
    ):
        """
        Directly track token usage (for runners that don't use SDK messages).

        This is useful for Python runners that manually track token usage
        from raw API responses.
        """
        if not is_tracking_enabled():
            return

        if not self.primary_model:
            self.primary_model = model

        # Calculate cost
        cost_usd = await self._calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_creation_tokens=cache_creation_tokens
        )

        # Record message-level data
        if self.session_id and self.session_id > 0:
            message_id = f'feat_{uuid.uuid4().hex[:12]}'
            await self.storage.record_feature_message(
                session_id=self.session_id,
                message_id=message_id,
                timestamp=datetime.utcnow(),
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cost_usd=cost_usd
            )

        # Update session totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost_usd

        # Export to OpenTelemetry (if enabled)
        if is_otel_enabled():
            try:
                otel_exporter = get_otel_exporter()
                otel_exporter.record_message(
                    spec_id=f"feature:{self.feature_type}:{self.project_id}",
                    phase=self.feature_type,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd
                )
            except Exception:
                pass

    def update_metadata(self, key: str, value: Any):
        """Update session metadata."""
        self.metadata[key] = value

    async def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int,
        cache_creation_tokens: int
    ) -> float:
        """Calculate cost in USD using models.dev pricing."""
        # Fetch pricing (cached or from API)
        pricing = await get_model_pricing(model)

        # Calculate costs (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing.input_price
        output_cost = (output_tokens / 1_000_000) * pricing.output_price
        cache_read_cost = (cache_read_tokens / 1_000_000) * pricing.cache_read_price
        cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing.cache_write_price

        total = input_cost + output_cost + cache_read_cost + cache_write_cost

        return total

    async def finalize(self):
        """Finalize tracking and export to JSON."""
        if not is_tracking_enabled():
            return

        if not self.session_id or self.session_id < 0:
            return

        # Update final totals
        await self.storage.update_feature_session_totals(
            session_id=self.session_id,
            ended_at=datetime.utcnow(),
            total_cost_usd=self.total_cost_usd,
            total_input_tokens=self.total_input_tokens,
            total_output_tokens=self.total_output_tokens,
            model=self.primary_model,
            metadata=self.metadata
        )

        # Calculate session duration
        duration_seconds = (datetime.utcnow() - self.session_start).total_seconds()

        # Export session metrics to OTel
        if is_otel_enabled():
            try:
                otel_exporter = get_otel_exporter()
                otel_exporter.record_session(
                    spec_id=f"feature:{self.feature_type}:{self.project_id}",
                    phase=self.feature_type,
                    total_cost_usd=self.total_cost_usd,
                    duration_seconds=duration_seconds
                )
                otel_exporter.end_session()
            except Exception:
                pass

        # Export to JSON backup
        from pathlib import Path
        json_path = Path(f".auto-claude/analytics/features/{self.project_id}.json")
        await self.storage.export_feature_sessions_to_json(self.project_id, json_path)

    def get_totals(self) -> Dict[str, Any]:
        """Get current session totals."""
        return {
            'project_id': self.project_id,
            'feature_type': self.feature_type,
            'session_id': self.session_id,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_cost_usd': self.total_cost_usd,
            'model': self.primary_model,
            'duration_seconds': (datetime.utcnow() - self.session_start).total_seconds()
        }


def create_feature_tracker(
    project_id: str,
    feature_type: str,
    db_path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> FeatureUsageTracker:
    """
    Factory function to create a feature usage tracker.

    Args:
        project_id: The project ID
        feature_type: Type of feature (roadmap, ideation, insights, etc.)
        db_path: Optional path to analytics database
        metadata: Optional metadata for the session

    Returns:
        FeatureUsageTracker instance
    """
    storage = get_analytics_storage(db_path)
    return FeatureUsageTracker(
        project_id=project_id,
        feature_type=feature_type,
        storage=storage,
        metadata=metadata
    )
