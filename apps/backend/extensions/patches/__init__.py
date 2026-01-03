"""
Patches Registry
================

Central registry for all wrapt patches.
Must be called BEFORE importing any patched modules.

Patches applied:
    - core.client.create_client: Adds Langfuse tracing + PostToolUse hooks
    - agents.session.run_agent_session: Adds session tracking

All patches use wrapt for safe monkey patching that:
    - Preserves function signatures
    - Maintains introspection
    - Works with post-import hooks
"""

import logging

logger = logging.getLogger(__name__)

_patches_registered = False
_patch_results = {}


def register_all_patches() -> bool:
    """
    Register all patches.

    Must be called BEFORE any imports of patched modules.

    Returns:
        True if all patches registered successfully, False otherwise.
    """
    global _patches_registered, _patch_results

    if _patches_registered:
        logger.debug("Patches already registered, skipping")
        return True

    all_success = True

    # Register each patch
    patches = [
        ("client", _register_client_patch),
        ("session", _register_session_patch),
        ("hooks", _register_hooks),
    ]

    for name, register_func in patches:
        try:
            success = register_func()
            _patch_results[name] = success
            if not success:
                all_success = False
                logger.warning(f"Patch '{name}' returned False")
        except Exception as e:
            _patch_results[name] = False
            all_success = False
            logger.error(f"Failed to register patch '{name}': {e}")

    _patches_registered = True
    return all_success


def _register_client_patch() -> bool:
    """Register create_client patch."""
    try:
        from .client import patch_create_client
        return patch_create_client()
    except ImportError as e:
        logger.warning(f"Could not import client patch: {e}")
        return False


def _register_session_patch() -> bool:
    """Register run_agent_session patch."""
    try:
        from .session import patch_run_agent_session
        return patch_run_agent_session()
    except ImportError as e:
        logger.warning(f"Could not import session patch: {e}")
        return False


def _register_hooks() -> bool:
    """Register SDK hooks configuration."""
    try:
        from .hooks import register_hooks
        return register_hooks()
    except ImportError as e:
        logger.warning(f"Could not import hooks: {e}")
        return False


def get_patch_results() -> dict:
    """Get results of all patch registrations."""
    return _patch_results.copy()


def is_patched(name: str) -> bool:
    """Check if a specific patch was applied."""
    return _patch_results.get(name, False)
