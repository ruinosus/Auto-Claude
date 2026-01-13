"""
Phase Models and Constants
===========================

Data structures and constants for phase execution.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generator

# Maximum retry attempts for phase execution
MAX_RETRIES = 3

# Observability imports with graceful degradation
try:
    from analytics.langfuse_integration import (
        flush_langfuse,
        is_langfuse_ready,
        start_span,
    )

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

    def is_langfuse_ready() -> bool:
        return False

    def start_span(*args: Any, **kwargs: Any) -> Any:
        return None

    def flush_langfuse() -> None:
        pass


@dataclass
class PhaseResult:
    """Result of a phase execution."""

    phase: str
    success: bool
    output_files: list[str]
    errors: list[str]
    retries: int


@contextmanager
def phase_span(
    phase_name: str,
    spec_id: str | None = None,
    project_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Generator[Any, None, None]:
    """
    Context manager for tracking phase execution with observability.

    Args:
        phase_name: Name of the phase (e.g., "discovery", "context", "spec_writing")
        spec_id: Optional spec identifier for correlation
        project_id: Optional project identifier
        metadata: Additional metadata to attach to the span

    Yields:
        The span object if Langfuse is available, otherwise None
    """
    if LANGFUSE_AVAILABLE and is_langfuse_ready():
        span_metadata = {
            "phase": phase_name,
            "component": "spec_phases",
            **(metadata or {}),
        }
        if spec_id:
            span_metadata["spec_id"] = spec_id
        if project_id:
            span_metadata["project_id"] = project_id

        span = start_span(
            name=f"phase:{phase_name}",
            metadata=span_metadata,
        )
        try:
            yield span
        finally:
            if span:
                span.end()
            flush_langfuse()
    else:
        yield None
