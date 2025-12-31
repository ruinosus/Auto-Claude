"""
Langfuse API Client
===================

Wrapper for Langfuse API v3 to fetch traces, generations, and scores.
Uses the Langfuse Python SDK for data access.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TraceFilter:
    """Filter options for trace queries."""
    spec_id: Optional[str] = None
    project_id: Optional[str] = None
    agent_type: Optional[str] = None
    tags: Optional[List[str]] = None
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
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
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
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoreData:
    """Score data structure."""
    id: str
    name: str
    value: float
    trace_id: str
    comment: Optional[str] = None
    timestamp: Optional[datetime] = None


class LangfuseAPIClient:
    """
    Client for accessing Langfuse data via its Python SDK v3.

    Provides methods to fetch traces, generations, and scores
    for analytics and ROI calculation.
    """

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        host: str = "http://localhost:3001",
    ):
        self.public_key = public_key
        self.secret_key = secret_key
        self.host = host
        self._client = None
        self._initialized = False

        # Try to initialize the client
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

            # Verify authentication
            if self._client.auth_check():
                self._initialized = True
                logger.info("Langfuse API client authenticated successfully")
            else:
                logger.error("Langfuse authentication failed")

        except ImportError:
            logger.error("Langfuse package not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse client: {e}")

    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return self._initialized and self._client is not None

    async def get_traces(self, filter: Optional[TraceFilter] = None) -> List[TraceData]:
        """
        Fetch traces from Langfuse with optional filtering.

        Uses Langfuse v3 API: client.api.trace.list()

        Args:
            filter: Optional filter criteria

        Returns:
            List of TraceData objects
        """
        if not self.is_configured():
            logger.warning("Langfuse client not configured")
            return []

        filter = filter or TraceFilter()

        try:
            # Build query parameters for v3 API
            # Note: v3 API doesn't support offset, only limit and page-based pagination
            kwargs = {
                "limit": filter.limit,
            }

            # Add tag filter if specified (v3 uses 'tags' parameter)
            if filter.tags:
                kwargs["tags"] = filter.tags

            # Fetch traces using v3 API
            response = self._client.api.trace.list(**kwargs)

            traces = []
            for trace in response.data:
                # Get metadata
                metadata = getattr(trace, "metadata", {}) or {}

                # Get trace-level attributes (set by trace_context)
                trace_user_id = getattr(trace, "user_id", None)
                trace_session_id = getattr(trace, "session_id", None)

                # Filter by project_id (check metadata OR user_id for compatibility)
                # trace_context() sets user_id=project_id at trace level
                if filter.project_id:
                    metadata_project = metadata.get("project_id")
                    if metadata_project != filter.project_id and trace_user_id != filter.project_id:
                        continue

                # Filter by spec_id (check metadata OR session_id for compatibility)
                # trace_context() sets session_id=spec_id at trace level
                if filter.spec_id:
                    metadata_spec = metadata.get("spec_id")
                    if metadata_spec != filter.spec_id and trace_session_id != filter.spec_id:
                        continue

                # Filter by agent_type
                if filter.agent_type and metadata.get("agent_type") != filter.agent_type:
                    continue

                # Filter by timestamp (handle timezone-aware vs naive comparison)
                trace_time = getattr(trace, "timestamp", None)
                if trace_time:
                    # Make filter timestamps timezone-aware if trace_time is aware
                    from_ts = filter.from_timestamp
                    to_ts = filter.to_timestamp
                    if trace_time.tzinfo is not None:
                        from datetime import timezone
                        if from_ts and from_ts.tzinfo is None:
                            from_ts = from_ts.replace(tzinfo=timezone.utc)
                        if to_ts and to_ts.tzinfo is None:
                            to_ts = to_ts.replace(tzinfo=timezone.utc)
                    if from_ts and trace_time < from_ts:
                        continue
                    if to_ts and trace_time > to_ts:
                        continue

                # Get metrics directly from trace (v3 provides these)
                total_cost = getattr(trace, "total_cost", 0) or 0
                latency_ms = getattr(trace, "latency", 0) or 0

                # Try to get total_tokens directly from trace first (v3 SDK)
                # The API may provide this at trace level for efficiency
                total_tokens = 0
                generation_count = 0

                # Check for totalTokens or total_tokens on trace object
                direct_tokens = (
                    getattr(trace, "totalTokens", None) or
                    getattr(trace, "total_tokens", None) or
                    getattr(trace, "usage_total_tokens", None)
                )
                if direct_tokens:
                    total_tokens = direct_tokens

                # Check for usage object on trace
                trace_usage = getattr(trace, "usage", None)
                if trace_usage and not total_tokens:
                    total_tokens = (
                        getattr(trace_usage, "total", 0) or
                        getattr(trace_usage, "totalTokens", 0) or
                        (getattr(trace_usage, "input", 0) or 0) + (getattr(trace_usage, "output", 0) or 0)
                    )

                # Fallback: count generations from observations if available
                observations = getattr(trace, "observations", []) or []
                for obs in observations:
                    if getattr(obs, "type", "") == "GENERATION":
                        generation_count += 1
                        if not total_tokens:  # Only sum if we don't have trace-level tokens
                            usage = getattr(obs, "usage", None)
                            if usage:
                                obs_tokens = (
                                    getattr(usage, "total", 0) or
                                    getattr(usage, "totalTokens", 0) or
                                    (getattr(usage, "input", 0) or 0) + (getattr(usage, "output", 0) or 0)
                                )
                                total_tokens += obs_tokens or 0

                # If still no tokens but we have cost, estimate tokens from cost
                # Claude pricing: ~$3/1M input, ~$15/1M output, average ~$6/1M
                if not total_tokens and total_cost > 0:
                    # Rough estimate: $6 per 1M tokens average
                    estimated_tokens = int(total_cost / 0.000006)
                    total_tokens = estimated_tokens
                    logger.debug(f"Estimated {estimated_tokens} tokens from cost ${total_cost}")

                traces.append(TraceData(
                    id=trace.id,
                    name=getattr(trace, "name", "") or "",
                    timestamp=trace_time or datetime.utcnow(),
                    metadata=metadata,
                    tags=getattr(trace, "tags", []) or [],
                    input=getattr(trace, "input", None),
                    output=getattr(trace, "output", None),
                    session_id=getattr(trace, "session_id", None),
                    user_id=getattr(trace, "user_id", None),
                    total_tokens=total_tokens,
                    total_cost=total_cost,
                    latency_ms=latency_ms,
                    generation_count=generation_count,
                ))

            return traces

        except Exception as e:
            logger.error(f"Failed to fetch traces: {e}")
            return []

    async def get_trace(self, trace_id: str) -> Optional[TraceData]:
        """
        Fetch a single trace by ID with full details.

        Uses Langfuse v3 API: client.api.trace.get()

        Args:
            trace_id: The trace ID

        Returns:
            TraceData or None if not found
        """
        if not self.is_configured():
            return None

        try:
            # Use v3 API
            trace = self._client.api.trace.get(trace_id)
            if not trace:
                return None

            metadata = getattr(trace, "metadata", {}) or {}

            # Get metrics directly from trace
            total_cost = getattr(trace, "total_cost", 0) or 0
            latency_ms = getattr(trace, "latency", 0) or 0

            # Try to get total_tokens directly from trace first
            total_tokens = 0
            generation_count = 0

            # Check for totalTokens or total_tokens on trace object
            direct_tokens = (
                getattr(trace, "totalTokens", None) or
                getattr(trace, "total_tokens", None) or
                getattr(trace, "usage_total_tokens", None)
            )
            if direct_tokens:
                total_tokens = direct_tokens

            # Check for usage object on trace
            trace_usage = getattr(trace, "usage", None)
            if trace_usage and not total_tokens:
                total_tokens = (
                    getattr(trace_usage, "total", 0) or
                    getattr(trace_usage, "totalTokens", 0) or
                    (getattr(trace_usage, "input", 0) or 0) + (getattr(trace_usage, "output", 0) or 0)
                )

            # Count generations from observations
            observations = getattr(trace, "observations", []) or []
            for obs in observations:
                if getattr(obs, "type", "") == "GENERATION":
                    generation_count += 1
                    if not total_tokens:  # Only sum if we don't have trace-level tokens
                        usage = getattr(obs, "usage", None)
                        if usage:
                            obs_tokens = (
                                getattr(usage, "total", 0) or
                                getattr(usage, "totalTokens", 0) or
                                (getattr(usage, "input", 0) or 0) + (getattr(usage, "output", 0) or 0)
                            )
                            total_tokens += obs_tokens or 0

            # If still no tokens but we have cost, estimate tokens from cost
            if not total_tokens and total_cost > 0:
                estimated_tokens = int(total_cost / 0.000006)
                total_tokens = estimated_tokens

            return TraceData(
                id=trace.id,
                name=getattr(trace, "name", "") or "",
                timestamp=getattr(trace, "timestamp", datetime.utcnow()),
                metadata=metadata,
                tags=getattr(trace, "tags", []) or [],
                input=getattr(trace, "input", None),
                output=getattr(trace, "output", None),
                session_id=getattr(trace, "session_id", None),
                user_id=getattr(trace, "user_id", None),
                total_tokens=total_tokens,
                total_cost=total_cost,
                latency_ms=latency_ms,
                generation_count=generation_count,
            )

        except Exception as e:
            logger.error(f"Failed to fetch trace {trace_id}: {e}")
            return None

    async def get_generations(
        self,
        trace_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[GenerationData]:
        """
        Fetch generations (LLM calls) from Langfuse.

        Uses Langfuse v3 API via trace observations.

        Args:
            trace_id: Optional trace ID to filter by
            limit: Maximum number of results

        Returns:
            List of GenerationData objects
        """
        if not self.is_configured():
            return []

        try:
            if trace_id:
                # Get trace and extract observations
                trace = self._client.api.trace.get(trace_id)
                if not trace:
                    return []
                observations = getattr(trace, "observations", []) or []
            else:
                # Get observations directly
                response = self._client.api.observations.get_many(limit=limit)
                observations = response.data if hasattr(response, 'data') else []

            generations = []
            for obs in observations:
                if getattr(obs, "type", "") != "GENERATION":
                    continue

                usage = getattr(obs, "usage", None)
                input_tokens = 0
                output_tokens = 0
                if usage:
                    input_tokens = getattr(usage, "input", 0) or 0
                    output_tokens = getattr(usage, "output", 0) or 0

                generations.append(GenerationData(
                    id=obs.id,
                    name=getattr(obs, "name", "") or "",
                    model=getattr(obs, "model", "unknown") or "unknown",
                    timestamp=getattr(obs, "start_time", datetime.utcnow()),
                    input=getattr(obs, "input", None),
                    output=getattr(obs, "output", None),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    cost=getattr(obs, "calculated_total_cost", 0) or 0,
                    latency_ms=getattr(obs, "latency", 0) or 0,
                    metadata=getattr(obs, "metadata", {}) or {},
                ))

                if len(generations) >= limit:
                    break

            return generations

        except Exception as e:
            logger.error(f"Failed to fetch generations: {e}")
            return []

    async def get_scores(
        self,
        trace_id: Optional[str] = None,
        name: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ScoreData]:
        """
        Fetch scores from Langfuse.

        Uses Langfuse v3 score_v_2 API for efficient querying.

        Args:
            trace_id: Optional trace ID to filter by
            name: Optional score name to filter by
            project_id: Optional project ID to filter by (for project isolation)
            limit: Maximum number of results

        Returns:
            List of ScoreData objects
        """
        if not self.is_configured():
            return []

        try:
            scores = []

            if trace_id:
                # Get scores from specific trace using score_v_2 API
                response = self._client.api.score_v_2.get(trace_id=trace_id, limit=limit)
                for score in response.data:
                    if name and score.name != name:
                        continue
                    scores.append(ScoreData(
                        id=score.id,
                        name=score.name,
                        value=score.value,
                        trace_id=score.trace_id,
                        comment=getattr(score, "comment", None),
                        timestamp=getattr(score, "timestamp", None),
                    ))
            else:
                # Use score_v_2.get API for efficient querying
                # Note: user_id in score_v_2 maps to trace.user_id which we set to project_id
                kwargs = {"limit": limit}
                if name:
                    kwargs["name"] = name
                if project_id:
                    # Filter by user_id which trace_context() sets to project_id
                    kwargs["user_id"] = project_id

                response = self._client.api.score_v_2.get(**kwargs)
                for score in response.data:
                    scores.append(ScoreData(
                        id=score.id,
                        name=score.name,
                        value=score.value,
                        trace_id=score.trace_id,
                        comment=getattr(score, "comment", None),
                        timestamp=getattr(score, "timestamp", None),
                    ))

            return scores[:limit]

        except Exception as e:
            logger.error(f"Failed to fetch scores: {e}")
            return []

    async def get_sessions_for_spec(self, spec_id: str) -> List[TraceData]:
        """
        Get all sessions (traces) for a specific spec.

        Args:
            spec_id: The spec identifier

        Returns:
            List of traces for this spec
        """
        filter = TraceFilter(
            spec_id=spec_id,
            tags=[f"spec:{spec_id}"],
            limit=100,
        )
        return await self.get_traces(filter)

    async def get_cost_summary(
        self,
        from_timestamp: Optional[datetime] = None,
        to_timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get cost summary for a time period.

        Args:
            from_timestamp: Start of period
            to_timestamp: End of period

        Returns:
            Cost summary dict
        """
        if not self.is_configured():
            return {"total_cost": 0, "total_tokens": 0, "generation_count": 0}

        # Default to last 30 days
        if not from_timestamp:
            from_timestamp = datetime.utcnow() - timedelta(days=30)
        if not to_timestamp:
            to_timestamp = datetime.utcnow()

        filter = TraceFilter(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            limit=100,  # Langfuse v3 max limit is 100
        )

        traces = await self.get_traces(filter)

        total_cost = sum(t.total_cost for t in traces)
        total_tokens = sum(t.total_tokens for t in traces)
        generation_count = sum(t.generation_count for t in traces)

        # Group by agent type
        by_agent = {}
        for trace in traces:
            agent_type = trace.metadata.get("agent_type", "unknown")
            if agent_type not in by_agent:
                by_agent[agent_type] = {"cost": 0, "tokens": 0, "count": 0}
            by_agent[agent_type]["cost"] += trace.total_cost
            by_agent[agent_type]["tokens"] += trace.total_tokens
            by_agent[agent_type]["count"] += 1

        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "generation_count": generation_count,
            "trace_count": len(traces),
            "by_agent_type": by_agent,
            "period": {
                "from": from_timestamp.isoformat(),
                "to": to_timestamp.isoformat(),
            },
        }
