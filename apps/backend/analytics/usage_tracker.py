"""
Token usage tracker for Claude Agent SDK sessions.

Tracks token consumption and costs at message and conversation levels,
with deduplication and context enrichment (spec, session, subtask, phase).
"""

from typing import Optional, Set
from datetime import datetime

from phase_config import resolve_model_id
from .pricing_provider import get_model_pricing
from .storage import AnalyticsStorage
from .otel_exporter import get_otel_exporter, is_otel_enabled


class UsageTracker:
    """
    Tracks token usage and costs during Claude Agent SDK sessions.

    Features:
    - Deduplicates messages with same ID
    - Enriches data with context (spec, session, subtask, phase)
    - Calculates costs using models.dev pricing
    - Async writes to minimize performance impact
    """

    def __init__(
        self,
        spec_id: str,
        session_num: int,
        phase: str,
        storage: AnalyticsStorage
    ):
        self.spec_id = spec_id
        self.session_num = session_num
        self.phase = phase  # planning, coding, validation
        self.storage = storage

        # Deduplication
        self.message_ids_seen: Set[str] = set()

        # Context
        self.current_subtask_id: Optional[str] = None
        self.conversation_id: Optional[int] = None
        self.primary_model: Optional[str] = None

        # Session totals
        self.session_start = datetime.utcnow()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0

    async def track_message(self, message):
        """
        Track token usage from Claude Agent SDK message.

        Accepts:
        - AssistantMessage (with usage data)
        - ResultMessage (with total cost)
        """
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

        # ResultMessage: conversation-level totals
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
        model = getattr(message, 'model', None) or resolve_model_id("sonnet")
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
        if self.conversation_id:
            message_id = getattr(message, 'id', f'msg_{datetime.utcnow().timestamp()}')
            await self.storage.record_message(
                conversation_id=self.conversation_id,
                message_id=message_id,
                subtask_id=self.current_subtask_id,
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
                    spec_id=self.spec_id,
                    phase=self.phase,
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
        # Record final conversation totals
        if self.conversation_id:
            total_cost = getattr(message, 'total_cost_usd', None) or self.total_cost_usd

            await self.storage.update_conversation_totals(
                conversation_id=self.conversation_id,
                ended_at=datetime.utcnow(),
                total_cost_usd=total_cost,
                total_input_tokens=self.total_input_tokens,
                total_output_tokens=self.total_output_tokens,
                model=self.primary_model
            )

    async def start_conversation(self) -> int:
        """Initialize conversation tracking. Returns conversation_id."""
        self.conversation_id = await self.storage.create_conversation(
            spec_id=self.spec_id,
            session_number=self.session_num,
            phase=self.phase,
            started_at=self.session_start
        )

        # Track session start in OTel
        if is_otel_enabled():
            try:
                otel_exporter = get_otel_exporter()
                otel_exporter.start_session()
            except Exception:
                pass

        return self.conversation_id

    def set_subtask(self, subtask_id: str):
        """Update current subtask context."""
        self.current_subtask_id = subtask_id

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
        if not self.conversation_id:
            return

        # Update final totals if not already done
        await self.storage.update_conversation_totals(
            conversation_id=self.conversation_id,
            ended_at=datetime.utcnow(),
            total_cost_usd=self.total_cost_usd,
            total_input_tokens=self.total_input_tokens,
            total_output_tokens=self.total_output_tokens,
            model=self.primary_model
        )

        # Calculate session duration
        duration_seconds = (datetime.utcnow() - self.session_start).total_seconds()

        # Export session metrics to OTel
        if is_otel_enabled():
            try:
                otel_exporter = get_otel_exporter()
                otel_exporter.record_session(
                    spec_id=self.spec_id,
                    phase=self.phase,
                    total_cost_usd=self.total_cost_usd,
                    duration_seconds=duration_seconds
                )
                otel_exporter.end_session()
            except Exception:
                pass

        # Export to JSON backup
        from pathlib import Path
        json_path = Path(f".auto-claude/specs/{self.spec_id}/memory/usage.json")
        await self.storage.export_to_json(self.spec_id, json_path)
