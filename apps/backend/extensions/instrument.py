#!/usr/bin/env python3
"""
Auto-Claude Instrumentation Entry Point
========================================

Similar to `opentelemetry-instrument`, this module wraps any Auto-Claude
script with instrumentation BEFORE any imports happen.

Usage:
    python -m extensions.instrument run.py --spec 001
    python -m extensions.instrument spec_runner.py --interactive
    python -m extensions.instrument runners/insights_runner.py --project-dir .

How it works:
    1. Registers wrapt patches for core modules (client, session)
    2. Adds SDK hooks for tool tracking
    3. Executes the target script with instrumentation active
    4. Collects metrics and artifacts automatically

No upstream files are modified!
"""

import sys
import os
import runpy
from pathlib import Path


def instrument():
    """
    Main instrumentation entry point.

    Applies patches BEFORE executing the target script,
    ensuring all imports get the instrumented versions.
    """
    # Validate arguments
    if len(sys.argv) < 2:
        print("Auto-Claude Instrumentation Layer")
        print()
        print("Usage:")
        print("    python -m extensions.instrument <script.py> [args...]")
        print()
        print("Examples:")
        print("    python -m extensions.instrument run.py --spec 001")
        print("    python -m extensions.instrument spec_runner.py --interactive")
        print("    python -m extensions.instrument runners/insights_runner.py --project-dir .")
        print()
        sys.exit(1)

    script = sys.argv[1]

    # Check if script exists
    script_path = Path(script)
    if not script_path.exists():
        # Try relative to apps/backend
        backend_path = Path(__file__).parent.parent
        script_path = backend_path / script
        if not script_path.exists():
            print(f"Error: Script not found: {script}")
            sys.exit(1)

    script_path = script_path.resolve()

    # Print banner
    print()
    print("=" * 60)
    print("  Auto-Claude Instrumentation Layer")
    print("=" * 60)
    print(f"  Script: {script_path.name}")
    print(f"  Args:   {' '.join(sys.argv[2:]) if len(sys.argv) > 2 else '(none)'}")
    print()

    # 1. Register all patches BEFORE any imports
    try:
        from extensions.patches import register_all_patches
        patches_applied = register_all_patches()
        if patches_applied:
            print("  [OK] Patches registered")
        else:
            print("  [WARN] Some patches failed to register")
    except ImportError as e:
        print(f"  [WARN] Could not register patches: {e}")
    except Exception as e:
        print(f"  [ERROR] Patch registration failed: {e}")

    # 2. Initialize analytics
    try:
        from extensions.analytics import init_analytics
        analytics_ready = init_analytics()
        if analytics_ready:
            print("  [OK] Analytics initialized (Langfuse)")
        else:
            print("  [INFO] Analytics disabled (Langfuse not configured)")
    except ImportError as e:
        print(f"  [WARN] Could not initialize analytics: {e}")
    except Exception as e:
        print(f"  [ERROR] Analytics initialization failed: {e}")

    print("=" * 60)
    print()

    # 3. Prepare to run target script
    # Remove 'instrument' from sys.argv so target script sees correct args
    sys.argv = sys.argv[1:]

    # Add script's directory to path
    sys.path.insert(0, str(script_path.parent))

    # 4. Execute target script
    try:
        runpy.run_path(str(script_path), run_name="__main__")
    except SystemExit:
        # Script called sys.exit(), that's fine
        raise
    except Exception as e:
        print(f"\n[Extensions] Script error: {e}")
        raise
    finally:
        # 5. Finalize analytics
        try:
            from extensions.analytics import finalize_analytics
            finalize_analytics()
        except Exception:
            pass  # Best effort


def main():
    """CLI entry point."""
    instrument()


if __name__ == "__main__":
    main()
