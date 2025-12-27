"""
Claude Agent SDK Telemetry Integration
======================================

Provides hooks and utilities for capturing telemetry from Claude Agent SDK sessions.
Integrates with both the OTEL collector and local analytics.db storage.

Usage:
    from analytics.sdk_telemetry import (
        create_telemetry_hooks,
        TelemetryTracker,
        wrap_sdk_client
    )

    # Option 1: Add hooks to ClaudeAgentOptions
    options = ClaudeAgentOptions(
        hooks=create_telemetry_hooks(project_id="my-project"),
        ...
    )

    # Option 2: Use TelemetryTracker for manual tracking
    tracker = TelemetryTracker(project_id="my-project")
    await tracker.start()
    # ... run agent ...
    await tracker.finalize()

    # Option 3: Wrap an existing client
    wrapped_client = wrap_sdk_client(client, project_id="my-project")
"""

import asyncio
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class ToolCallRecord:
    """Record of a single tool call."""
    tool_name: str
    tool_input: Dict[str, Any]
    started_at: datetime
    ended_at: Optional[datetime] = None
    success: bool = True
    result_preview: Optional[str] = None
    duration_ms: int = 0


@dataclass
class MessageRecord:
    """Record of an API message with token usage."""
    message_id: str
    timestamp: datetime
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class SessionTelemetry:
    """Telemetry data for a single SDK session."""
    session_id: str
    project_id: str
    agent_type: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    model: str = "claude-sonnet-4-5"

    # Token totals
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_cost_usd: float = 0.0

    # Call records
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    messages: List[MessageRecord] = field(default_factory=list)

    # Deduplication
    seen_message_ids: set = field(default_factory=set)


class TelemetryTracker:
    """
    Tracks telemetry from Claude Agent SDK sessions.

    Can be used standalone or integrated with SDK hooks.
    """

    def __init__(
        self,
        project_id: str,
        agent_type: str = "coder",
        db_path: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.project_id = project_id
        self.agent_type = agent_type
        self.db_path = db_path
        self.session_id = session_id or f"sdk_{uuid.uuid4().hex[:12]}"

        self.telemetry = SessionTelemetry(
            session_id=self.session_id,
            project_id=project_id,
            agent_type=agent_type,
            started_at=datetime.utcnow(),
        )

        self._storage = None
        self._current_tool: Optional[ToolCallRecord] = None
        self._lock = asyncio.Lock()

    async def _get_storage(self):
        """Lazy-load storage."""
        if self._storage is None:
            try:
                from analytics.storage import get_analytics_storage
                self._storage = get_analytics_storage(self.db_path)
            except ImportError:
                pass
        return self._storage

    async def start(self):
        """Start telemetry session."""
        self.telemetry.started_at = datetime.utcnow()
        print(f"[SDK_TELEMETRY] Started session {self.session_id}")

    async def track_tool_start(self, tool_name: str, tool_input: Dict[str, Any]):
        """Track the start of a tool call."""
        async with self._lock:
            self._current_tool = ToolCallRecord(
                tool_name=tool_name,
                tool_input=tool_input,
                started_at=datetime.utcnow(),
            )

    async def track_tool_end(
        self,
        tool_name: str,
        success: bool = True,
        result_preview: Optional[str] = None
    ):
        """Track the end of a tool call."""
        async with self._lock:
            if self._current_tool and self._current_tool.tool_name == tool_name:
                self._current_tool.ended_at = datetime.utcnow()
                self._current_tool.success = success
                self._current_tool.result_preview = result_preview
                self._current_tool.duration_ms = int(
                    (self._current_tool.ended_at - self._current_tool.started_at).total_seconds() * 1000
                )
                self.telemetry.tool_calls.append(self._current_tool)
                self._current_tool = None

    async def track_message(self, message: Any):
        """
        Track a message from the SDK response stream.

        Handles AssistantMessage and ResultMessage types.
        """
        async with self._lock:
            # Get message ID for deduplication
            message_id = getattr(message, 'id', None)
            if message_id and message_id in self.telemetry.seen_message_ids:
                return  # Already tracked
            if message_id:
                self.telemetry.seen_message_ids.add(message_id)

            # Check for usage data
            usage = getattr(message, 'usage', None)
            if not usage:
                return

            # Extract token counts
            if isinstance(usage, dict):
                input_tokens = usage.get('input_tokens', 0) or 0
                output_tokens = usage.get('output_tokens', 0) or 0
                cache_read = usage.get('cache_read_input_tokens', 0) or 0
                cache_creation = usage.get('cache_creation_input_tokens', 0) or 0
            else:
                input_tokens = getattr(usage, 'input_tokens', 0) or 0
                output_tokens = getattr(usage, 'output_tokens', 0) or 0
                cache_read = getattr(usage, 'cache_read_input_tokens', 0) or 0
                cache_creation = getattr(usage, 'cache_creation_input_tokens', 0) or 0

            # Get model
            model = getattr(message, 'model', self.telemetry.model)
            if model:
                self.telemetry.model = model

            # Calculate cost
            cost_usd = await self._calculate_cost(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read,
                cache_creation_tokens=cache_creation
            )

            # Record message
            record = MessageRecord(
                message_id=message_id or f"msg_{uuid.uuid4().hex[:8]}",
                timestamp=datetime.utcnow(),
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read,
                cache_creation_tokens=cache_creation,
                cost_usd=cost_usd,
            )
            self.telemetry.messages.append(record)

            # Update totals
            self.telemetry.total_input_tokens += input_tokens
            self.telemetry.total_output_tokens += output_tokens
            self.telemetry.total_cache_read_tokens += cache_read
            self.telemetry.total_cache_creation_tokens += cache_creation
            self.telemetry.total_cost_usd += cost_usd

            # Check for ResultMessage total_cost_usd (authoritative)
            result_cost = getattr(message, 'total_cost_usd', None)
            if result_cost and result_cost > self.telemetry.total_cost_usd:
                self.telemetry.total_cost_usd = result_cost

    async def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int,
        cache_creation_tokens: int
    ) -> float:
        """Calculate cost using pricing provider."""
        try:
            from analytics.pricing_provider import get_model_pricing
            pricing = await get_model_pricing(model)
            input_cost = (input_tokens / 1_000_000) * pricing.input_price
            output_cost = (output_tokens / 1_000_000) * pricing.output_price
            cache_read_cost = (cache_read_tokens / 1_000_000) * pricing.cache_read_price
            cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing.cache_write_price
            return input_cost + output_cost + cache_read_cost + cache_write_cost
        except Exception:
            # Fallback pricing (Sonnet 4.5)
            input_cost = (input_tokens / 1_000_000) * 3.0
            output_cost = (output_tokens / 1_000_000) * 15.0
            cache_read_cost = (cache_read_tokens / 1_000_000) * 0.30
            cache_write_cost = (cache_creation_tokens / 1_000_000) * 3.75
            return input_cost + output_cost + cache_read_cost + cache_write_cost

    async def finalize(self):
        """Finalize tracking and persist data."""
        self.telemetry.ended_at = datetime.utcnow()

        print(f"[SDK_TELEMETRY] Session {self.session_id} finalized:")
        print(f"  Model: {self.telemetry.model}")
        print(f"  Input tokens: {self.telemetry.total_input_tokens:,}")
        print(f"  Output tokens: {self.telemetry.total_output_tokens:,}")
        print(f"  Cache read: {self.telemetry.total_cache_read_tokens:,}")
        print(f"  Cache creation: {self.telemetry.total_cache_creation_tokens:,}")
        print(f"  Cost: ${self.telemetry.total_cost_usd:.4f}")
        print(f"  Tool calls: {len(self.telemetry.tool_calls)}")
        print(f"  Messages: {len(self.telemetry.messages)}")

        # Persist to storage
        await self._persist()

        # Send to OTEL collector (if running)
        await self._send_to_otel()

    async def _persist(self):
        """Persist session data to analytics.db."""
        try:
            storage = await self._get_storage()
            if not storage:
                return

            # Create feature session
            session_id = await storage.create_feature_session(
                project_id=self.project_id,
                feature_type=f"sdk_{self.agent_type}",
                started_at=self.telemetry.started_at,
                model=self.telemetry.model,
                metadata={
                    "session_id": self.session_id,
                    "agent_type": self.agent_type,
                    "tool_calls": len(self.telemetry.tool_calls),
                    "messages": len(self.telemetry.messages),
                }
            )

            # Record individual messages
            for msg in self.telemetry.messages:
                await storage.record_feature_message(
                    session_id=session_id,
                    message_id=msg.message_id,
                    timestamp=msg.timestamp,
                    model=msg.model,
                    input_tokens=msg.input_tokens,
                    output_tokens=msg.output_tokens,
                    cache_read_tokens=msg.cache_read_tokens,
                    cache_creation_tokens=msg.cache_creation_tokens,
                    cost_usd=msg.cost_usd,
                )

            # Update session totals
            await storage.update_feature_session_totals(
                session_id=session_id,
                ended_at=self.telemetry.ended_at or datetime.utcnow(),
                total_cost_usd=self.telemetry.total_cost_usd,
                total_input_tokens=self.telemetry.total_input_tokens,
                total_output_tokens=self.telemetry.total_output_tokens,
                model=self.telemetry.model,
            )

            print(f"[SDK_TELEMETRY] Persisted to analytics.db (session {session_id})")

        except Exception as e:
            print(f"[SDK_TELEMETRY] Failed to persist: {e}")

    async def _send_to_otel(self):
        """Send telemetry to OTEL collector if running."""
        otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if not otel_endpoint:
            return

        try:
            import aiohttp

            # Format as OTLP log record
            log_record = {
                "resourceLogs": [{
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "auto-claude-sdk"}},
                            {"key": "session.id", "value": {"stringValue": self.session_id}},
                        ]
                    },
                    "scopeLogs": [{
                        "logRecords": [{
                            "timeUnixNano": int(datetime.utcnow().timestamp() * 1e9),
                            "body": {"stringValue": "sdk_session_complete"},
                            "attributes": [
                                {"key": "event.name", "value": {"stringValue": "sdk_session"}},
                                {"key": "project_id", "value": {"stringValue": self.project_id}},
                                {"key": "agent_type", "value": {"stringValue": self.agent_type}},
                                {"key": "model", "value": {"stringValue": self.telemetry.model}},
                                {"key": "input_tokens", "value": {"intValue": str(self.telemetry.total_input_tokens)}},
                                {"key": "output_tokens", "value": {"intValue": str(self.telemetry.total_output_tokens)}},
                                {"key": "cache_read_tokens", "value": {"intValue": str(self.telemetry.total_cache_read_tokens)}},
                                {"key": "cache_creation_tokens", "value": {"intValue": str(self.telemetry.total_cache_creation_tokens)}},
                                {"key": "cost_usd", "value": {"doubleValue": self.telemetry.total_cost_usd}},
                                {"key": "tool_calls", "value": {"intValue": str(len(self.telemetry.tool_calls))}},
                            ]
                        }]
                    }]
                }]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{otel_endpoint}/v1/logs",
                    json=log_record,
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status == 200:
                        print(f"[SDK_TELEMETRY] Sent to OTEL collector")
                    else:
                        print(f"[SDK_TELEMETRY] OTEL send failed: {resp.status}")

        except Exception as e:
            # OTEL send is optional, don't fail
            pass

    def get_totals(self) -> Dict[str, Any]:
        """Get current session totals."""
        return {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "agent_type": self.agent_type,
            "model": self.telemetry.model,
            "total_input_tokens": self.telemetry.total_input_tokens,
            "total_output_tokens": self.telemetry.total_output_tokens,
            "total_cache_read_tokens": self.telemetry.total_cache_read_tokens,
            "total_cache_creation_tokens": self.telemetry.total_cache_creation_tokens,
            "total_cost_usd": self.telemetry.total_cost_usd,
            "tool_calls": len(self.telemetry.tool_calls),
            "messages": len(self.telemetry.messages),
        }


# Global tracker for hook-based tracking
_active_tracker: Optional[TelemetryTracker] = None


def set_active_tracker(tracker: Optional[TelemetryTracker]):
    """Set the active tracker for hook-based tracking."""
    global _active_tracker
    _active_tracker = tracker


def get_active_tracker() -> Optional[TelemetryTracker]:
    """Get the active tracker."""
    return _active_tracker


async def pre_tool_use_hook(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    PreToolUse hook that tracks tool invocations.

    Add to ClaudeAgentOptions hooks to capture all tool calls.
    """
    tracker = get_active_tracker()
    if tracker:
        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})
        await tracker.track_tool_start(tool_name, tool_input)

    return {}  # Don't modify behavior


async def post_tool_use_hook(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    PostToolUse hook that tracks tool results.

    Add to ClaudeAgentOptions hooks to capture all tool results.
    """
    tracker = get_active_tracker()
    if tracker:
        tool_name = input_data.get("tool_name", "unknown")
        tool_response = input_data.get("tool_response", "")
        is_error = "error" in str(tool_response).lower()

        result_preview = str(tool_response)[:200] if tool_response else None
        await tracker.track_tool_end(tool_name, success=not is_error, result_preview=result_preview)

    return {}  # Don't modify behavior


def create_telemetry_hooks(
    project_id: str,
    agent_type: str = "coder",
    db_path: Optional[str] = None,
) -> Dict[str, List]:
    """
    Create telemetry hooks for ClaudeAgentOptions.

    Returns a hooks dict that can be merged with existing hooks:

        options = ClaudeAgentOptions(
            hooks=create_telemetry_hooks("my-project"),
            ...
        )

    Or merge with existing hooks:

        from claude_agent_sdk.types import HookMatcher
        telemetry_hooks = create_telemetry_hooks("my-project")
        options = ClaudeAgentOptions(
            hooks={
                "PreToolUse": [
                    HookMatcher(matcher="Bash", hooks=[security_hook]),
                    *telemetry_hooks["PreToolUse"],
                ],
                "PostToolUse": telemetry_hooks["PostToolUse"],
            },
            ...
        )
    """
    # Create and set the tracker
    tracker = TelemetryTracker(
        project_id=project_id,
        agent_type=agent_type,
        db_path=db_path,
    )
    set_active_tracker(tracker)

    try:
        from claude_agent_sdk.types import HookMatcher

        return {
            "PreToolUse": [
                HookMatcher(matcher=None, hooks=[pre_tool_use_hook]),
            ],
            "PostToolUse": [
                HookMatcher(matcher=None, hooks=[post_tool_use_hook]),
            ],
        }
    except ImportError:
        # Return empty hooks if SDK not available
        return {"PreToolUse": [], "PostToolUse": []}


def merge_hooks(base_hooks: Dict, telemetry_hooks: Dict) -> Dict:
    """
    Merge telemetry hooks with existing hooks.

    Preserves all existing hooks while adding telemetry tracking.
    """
    merged = {}

    for hook_type in ["PreToolUse", "PostToolUse"]:
        base = base_hooks.get(hook_type, [])
        telemetry = telemetry_hooks.get(hook_type, [])

        if isinstance(base, list):
            merged[hook_type] = [*base, *telemetry]
        else:
            merged[hook_type] = telemetry

    return merged


async def finalize_active_tracker():
    """Finalize and cleanup the active tracker."""
    tracker = get_active_tracker()
    if tracker:
        await tracker.finalize()
        set_active_tracker(None)


# Convenience function for quick integration
def enable_sdk_telemetry(
    project_id: str,
    agent_type: str = "coder",
    db_path: Optional[str] = None,
) -> TelemetryTracker:
    """
    Enable SDK telemetry tracking.

    Call this before creating a ClaudeSDKClient to enable tracking.
    Returns the tracker which should be finalized after the session.

    Usage:
        tracker = enable_sdk_telemetry("my-project")
        try:
            # ... run agent session ...
        finally:
            await tracker.finalize()
    """
    tracker = TelemetryTracker(
        project_id=project_id,
        agent_type=agent_type,
        db_path=db_path,
    )
    set_active_tracker(tracker)
    return tracker
