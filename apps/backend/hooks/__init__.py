"""
Claude Code Hooks Integration
==============================

This package provides automatic Claude Code hook configuration for
terminal token tracking. All terminal sessions are tracked in the
analytics database.

This is NOT optional - it's part of the production-ready tracking system.
"""

from .auto_configure import (
    configure_terminal_tracking,
    ensure_terminal_tracking,
    get_tracking_status,
)

__all__ = [
    "configure_terminal_tracking",
    "ensure_terminal_tracking",
    "get_tracking_status",
]
