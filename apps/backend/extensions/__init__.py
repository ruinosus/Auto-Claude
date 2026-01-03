"""
Auto-Claude Extensions Layer
=============================

Zero-invasive instrumentation for Auto-Claude.
Adds Langfuse tracing, ROI tracking, and artifact collection
WITHOUT modifying upstream files.

Usage:
    python -m extensions.instrument run.py --spec 001
    python -m extensions.instrument spec_runner.py --interactive

Inspired by:
    - OpenTelemetry zero-code instrumentation
    - wrapt safe monkey patching
    - pytest pluggy hooks
"""

__version__ = "1.0.0"

from .instrument import instrument

__all__ = ["instrument", "__version__"]
