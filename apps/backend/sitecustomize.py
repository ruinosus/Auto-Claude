"""
Auto-Claude Extensions Loader (sitecustomize.py)
=================================================

This file is automatically executed by Python at startup when apps/backend
is on PYTHONPATH (which it always is for Auto-Claude processes).

It provides ZERO-INVASIVE instrumentation by checking for EXTENSIONS_ENABLED=true
and automatically registering patches before any other imports.

Why sitecustomize.py?
---------------------
Python automatically executes sitecustomize.py from any directory on sys.path
at interpreter startup, BEFORE any user code runs. This allows us to:

1. Register wrapt patches before the patched modules are imported
2. Initialize Langfuse analytics
3. Set up SDK hooks for artifact tracking

All without modifying ANY existing files in the codebase.

Usage:
------
Simply set EXTENSIONS_ENABLED=true in your environment:

    export EXTENSIONS_ENABLED=true
    export LANGFUSE_ENABLED=true
    # ... other Langfuse settings

Then run any Auto-Claude script normally:

    python run.py --spec 001
    python spec_runner.py --interactive

The extensions layer will be automatically activated.

Merge Safety:
-------------
This file is NEW and doesn't exist in upstream (AndyMik90/Auto-Claude).
It will never cause merge conflicts when syncing with upstream.
"""

import os
import sys

def _load_extensions():
    """
    Load extensions if enabled via environment variable.

    This runs BEFORE any other imports, allowing patches to be
    registered before the target modules are loaded.
    """
    # Check if extensions are enabled
    extensions_enabled = os.environ.get('EXTENSIONS_ENABLED', '').lower() in ('true', '1', 'yes')

    if not extensions_enabled:
        return

    # Don't load twice
    if hasattr(sys, '_extensions_loaded'):
        return

    # Always show when extensions are loading (for visibility)
    print("[Extensions] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("[Extensions] 🔌 Auto-Claude Extensions Layer Activating...")

    try:
        # Try to import and register patches
        from extensions.patches import register_all_patches
        patches_applied = register_all_patches()

        if patches_applied:
            # Mark as loaded to prevent double-loading
            sys._extensions_loaded = True
            print("[Extensions] ✅ Patches registered successfully")

            # Initialize analytics if available
            try:
                from extensions.analytics import init_analytics
                analytics_ready = init_analytics()
                if analytics_ready:
                    print("[Extensions] ✅ Langfuse analytics initialized")
                else:
                    print("[Extensions] ⚠️  Langfuse not ready (check LANGFUSE_* env vars)")
            except ImportError as e:
                print(f"[Extensions] ⚠️  Analytics not available: {e}")

            print("[Extensions] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        else:
            print("[Extensions] ⚠️  No patches were applied")
            print("[Extensions] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    except ImportError as e:
        # Extensions not installed
        print(f"[Extensions] ❌ Extensions not installed: {e}")
        print("[Extensions]    Run: pip install -r extensions/requirements.txt")
        print("[Extensions] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    except Exception as e:
        # Unexpected error - log it but don't crash
        print(f"[Extensions] ❌ Error loading extensions: {e}")
        print("[Extensions] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# Run on import (which happens at Python startup)
_load_extensions()
