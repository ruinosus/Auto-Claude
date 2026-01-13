"""
Langfuse Client for ROI Engine.

Provides access to Langfuse traces, generations, and scores for ROI calculation.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


def parse_datetime(value: Union[str, datetime, None]) -> datetime:
    """Parse a datetime value that might be a string or datetime object."""
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Handle ISO format strings
        try:
            # Try parsing with timezone
            if value.endswith('Z'):
                value = value[:-1] + '+00:00'
            return datetime.fromisoformat(value)
        except ValueError:
            # Fallback for other formats
            try:
                from dateutil.parser import parse as dateutil_parse
                return dateutil_parse(value)
            except ImportError:
                logger.warning(f"Could not parse datetime string: {value}")
                return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


@dataclass
class TraceFilter:
    """Filter options for trace queries."""
    spec_id: Optional[str] = None
    project_id: Optional[str] = None  # Maps to user_id in Langfuse (more reliable than tags)
    agent_type: Optional[str] = None
    tags: Optional[list[str]] = None
    user_id: Optional[str] = None  # Direct user_id filter for Langfuse
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None
    limit: int = 50
    offset: int = 0


@dataclass
class TraceData:
    """Trace data structure."""
    id: str
    name: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    input: Optional[Any] = None
    output: Optional[Any] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    # Computed fields
    total_tokens: int = 0
    total_cost: float = 0.0
    latency_ms: float = 0.0
    generation_count: int = 0


@dataclass
class GenerationData:
    """Generation (LLM call) data structure."""
    id: str
    name: str
    model: str
    timestamp: datetime
    input: Optional[Any] = None
    output: Optional[Any] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoreData:
    """Score data structure."""
    id: str
    name: str
    value: float
    trace_id: str
    comment: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class SessionData:
    """Session data structure."""
    id: str
    name: str
    created_at: datetime
    trace_count: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0


@dataclass
class DailyMetric:
    """Daily metric data structure."""
    date: str
    trace_count: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0


@dataclass
class CostBreakdown:
    """Cost breakdown by category."""
    by_model: dict[str, float] = field(default_factory=dict)
    by_agent: dict[str, float] = field(default_factory=dict)
    by_date: dict[str, float] = field(default_factory=dict)
    total: float = 0.0


class LangfuseClient:
    """
    Client for accessing Langfuse data via its Python SDK.

    Provides methods to fetch traces, generations, and scores
    for ROI calculation and analytics.
    """

    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY", "")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY", "")
        self.host = host or os.getenv("LANGFUSE_HOST", "http://localhost:3001")
        self._client = None
        self._initialized = False

        self._init_client()

    def _init_client(self):
        """Initialize the Langfuse client."""
        if not self.public_key or not self.secret_key:
            logger.warning("Langfuse API keys not provided")
            return

        try:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host,
            )

            if self._client.auth_check():
                self._initialized = True
                logger.info("Langfuse client initialized successfully")
            else:
                logger.error("Langfuse authentication failed")

        except ImportError:
            logger.warning("Langfuse package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse client: {e}")

    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return self._initialized and self._client is not None

    async def get_traces(self, filter: Optional[TraceFilter] = None) -> list[TraceData]:
        """Fetch traces from Langfuse with optional filtering.

        Automatically paginates if requested limit exceeds Langfuse max (100).
        """
        if not self.is_configured():
            return []

        filter = filter or TraceFilter()

        # Langfuse max limit per request is 100
        LANGFUSE_MAX_LIMIT = 100
        requested_limit = filter.limit

        try:
            all_traces: list[TraceData] = []
            page = 1

            # Calculate starting page from offset
            if filter.offset > 0:
                page = (filter.offset // LANGFUSE_MAX_LIMIT) + 1

            while len(all_traces) < requested_limit:
                # Build query parameters
                params = {
                    "limit": min(LANGFUSE_MAX_LIMIT, requested_limit - len(all_traces)),
                    "page": page,
                }

                if filter.from_timestamp:
                    params["from_timestamp"] = filter.from_timestamp
                if filter.to_timestamp:
                    params["to_timestamp"] = filter.to_timestamp
                if filter.tags:
                    params["tags"] = filter.tags
                # Use user_id for filtering (project_id is stored as user_id in Langfuse)
                if filter.user_id:
                    params["user_id"] = filter.user_id

                # Fetch traces using SDK (list is the correct method in newer Langfuse SDK)
                result = self._client.api.trace.list(**params)

                if not result.data:
                    # No more data
                    break

                for trace in result.data:
                    all_traces.append(TraceData(
                        id=trace.id,
                        name=trace.name or "",
                        timestamp=parse_datetime(trace.timestamp),
                        metadata=trace.metadata or {},
                        tags=trace.tags or [],
                        session_id=getattr(trace, 'session_id', None),
                        user_id=getattr(trace, 'user_id', None),
                        total_tokens=getattr(trace, 'total_tokens', 0) or 0,
                        total_cost=getattr(trace, 'total_cost', 0.0) or 0.0,
                        latency_ms=getattr(trace, 'latency', 0.0) or 0.0,
                    ))

                # Check if we got less than requested (no more pages)
                if len(result.data) < params["limit"]:
                    break

                page += 1

            return all_traces[:requested_limit]

        except Exception as e:
            logger.error(f"Failed to fetch traces: {e}")
            return []

    async def get_trace(self, trace_id: str) -> Optional[TraceData]:
        """Fetch a single trace by ID."""
        if not self.is_configured():
            return None

        try:
            trace = self._client.api.trace.get(trace_id)
            if not trace:
                return None

            return TraceData(
                id=trace.id,
                name=trace.name or "",
                timestamp=parse_datetime(trace.timestamp),
                metadata=trace.metadata or {},
                tags=trace.tags or [],
                input=trace.input,
                output=trace.output,
                session_id=getattr(trace, 'session_id', None),
                user_id=getattr(trace, 'user_id', None),
                total_tokens=getattr(trace, 'total_tokens', 0) or 0,
                total_cost=getattr(trace, 'total_cost', 0.0) or 0.0,
                latency_ms=getattr(trace, 'latency', 0.0) or 0.0,
            )

        except Exception as e:
            logger.error(f"Failed to fetch trace {trace_id}: {e}")
            return None

    async def get_generations(self, trace_id: str) -> list[GenerationData]:
        """Fetch generations for a trace."""
        if not self.is_configured():
            return []

        try:
            # Fetch observations for this trace using get_many (correct Langfuse v3 API)
            result = self._client.api.observations.get_many(trace_id=trace_id, type="GENERATION")
            if not result or not result.data:
                return []

            generations = []
            for obs in result.data:
                # Usage is a Pydantic model in Langfuse v3, access attributes directly
                usage = getattr(obs, 'usage', None)
                input_tokens = getattr(usage, 'input', 0) or 0 if usage else 0
                output_tokens = getattr(usage, 'output', 0) or 0 if usage else 0
                total_tokens = getattr(usage, 'total', 0) or 0 if usage else 0

                generations.append(GenerationData(
                    id=obs.id,
                    name=getattr(obs, 'name', '') or "",
                    model=getattr(obs, 'model', '') or "",
                    timestamp=parse_datetime(getattr(obs, 'start_time', None)),
                    input=getattr(obs, 'input', None),
                    output=getattr(obs, 'output', None),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=getattr(obs, 'calculated_total_cost', 0.0) or 0.0,
                    latency_ms=getattr(obs, 'latency', 0.0) or 0.0,
                    metadata=getattr(obs, 'metadata', {}) or {},
                ))

            return generations

        except Exception as e:
            logger.error(f"Failed to fetch generations for trace {trace_id}: {e}")
            return []

    async def get_sessions(self, limit: int = 50, offset: int = 0) -> list[SessionData]:
        """Fetch sessions from Langfuse."""
        if not self.is_configured():
            return []

        try:
            result = self._client.api.sessions.list(limit=limit, page=1 if offset == 0 else (offset // limit) + 1)

            sessions = []
            for session in result.data:
                sessions.append(SessionData(
                    id=session.id,
                    name=getattr(session, 'name', session.id) or session.id,
                    created_at=parse_datetime(getattr(session, 'created_at', None)),
                    trace_count=getattr(session, 'trace_count', 0) or 0,
                    total_tokens=getattr(session, 'total_tokens', 0) or 0,
                    total_cost=getattr(session, 'total_cost', 0.0) or 0.0,
                ))

            return sessions

        except Exception as e:
            logger.error(f"Failed to fetch sessions: {e}")
            return []

    async def get_daily_metrics(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        project_id: Optional[str] = None,
    ) -> list[DailyMetric]:
        """Calculate daily metrics from traces.

        Args:
            from_date: Start date filter
            to_date: End date filter
            project_id: Project identifier to filter traces by tag 'project:{project_id}'
        """
        if not self.is_configured():
            return []

        from_date = from_date or (datetime.now() - timedelta(days=30))
        to_date = to_date or datetime.now()

        try:
            # Filter by user_id (project_id is stored as user_id in Langfuse)
            filter = TraceFilter(
                from_timestamp=from_date,
                to_timestamp=to_date,
                user_id=project_id,
                limit=1000,
            )
            traces = await self.get_traces(filter)

            # Aggregate by date
            daily: dict[str, DailyMetric] = {}

            for trace in traces:
                date_key = trace.timestamp.strftime("%Y-%m-%d")

                if date_key not in daily:
                    daily[date_key] = DailyMetric(date=date_key)

                daily[date_key].trace_count += 1
                daily[date_key].total_tokens += trace.total_tokens
                daily[date_key].total_cost += trace.total_cost

            # Sort by date
            return sorted(daily.values(), key=lambda x: x.date)

        except Exception as e:
            logger.error(f"Failed to calculate daily metrics: {e}")
            return []

    async def get_cost_breakdown(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        project_id: Optional[str] = None,
    ) -> CostBreakdown:
        """Get cost breakdown by model, agent, and date.

        Args:
            from_date: Start date filter
            to_date: End date filter
            project_id: Project identifier to filter traces by user_id
        """
        if not self.is_configured():
            return CostBreakdown()

        from_date = from_date or (datetime.now() - timedelta(days=30))
        to_date = to_date or datetime.now()

        try:
            # Filter by user_id (project_id is stored as user_id in Langfuse)
            filter = TraceFilter(
                from_timestamp=from_date,
                to_timestamp=to_date,
                user_id=project_id,
                limit=1000,
            )
            traces = await self.get_traces(filter)

            breakdown = CostBreakdown()

            for trace in traces:
                # By date
                date_key = trace.timestamp.strftime("%Y-%m-%d")
                breakdown.by_date[date_key] = breakdown.by_date.get(date_key, 0.0) + trace.total_cost

                # By agent type (from metadata or name)
                agent_type = trace.metadata.get("agent_type", "unknown")
                if agent_type == "unknown" and trace.name:
                    # Try to extract from trace name
                    for known_agent in ["planner", "coder", "qa_reviewer", "qa_fixer", "writer", "researcher"]:
                        if known_agent in trace.name.lower():
                            agent_type = known_agent
                            break
                breakdown.by_agent[agent_type] = breakdown.by_agent.get(agent_type, 0.0) + trace.total_cost

                breakdown.total += trace.total_cost

            # Get model breakdown from generations
            for trace in traces[:100]:  # Limit to avoid too many API calls
                generations = await self.get_generations(trace.id)
                for gen in generations:
                    model = gen.model or "unknown"
                    breakdown.by_model[model] = breakdown.by_model.get(model, 0.0) + gen.cost

            return breakdown

        except Exception as e:
            logger.error(f"Failed to get cost breakdown: {e}")
            return CostBreakdown()


# Singleton instance
_client: Optional[LangfuseClient] = None


def get_langfuse_client() -> LangfuseClient:
    """Get or create the Langfuse client singleton."""
    global _client
    if _client is None:
        _client = LangfuseClient()
    return _client
