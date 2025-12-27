#!/usr/bin/env python3
"""
Claude Code Hooks Auto-Configuration
=====================================

Automatically configures Claude Code hooks for terminal token tracking.
This module is called during application initialization to ensure
all terminal sessions are tracked in the analytics database.

This is NOT optional - it's part of the production-ready tracking system.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Add backend path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


def get_user_settings_path() -> Path:
    """Get path to user-level Claude Code settings."""
    return Path.home() / ".claude" / "settings.json"


def get_project_settings_path(project_dir: Optional[Path] = None) -> Path:
    """Get path to project-level Claude Code settings."""
    base = project_dir or Path.cwd()
    return base / ".claude" / "settings.json"


def get_hook_script_path() -> str:
    """Get absolute path to the terminal session tracker script."""
    return str(Path(__file__).parent / "terminal_session_tracker.py")


def load_settings(settings_path: Path) -> dict:
    """Load existing settings or return empty dict."""
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_settings(settings_path: Path, settings: dict) -> bool:
    """Save settings to file. Returns True on success."""
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        return True
    except IOError:
        return False


def is_hook_installed(settings: dict, hook_script_path: str) -> bool:
    """Check if terminal tracking hook is already installed."""
    if "hooks" not in settings:
        return False

    session_end_hooks = settings["hooks"].get("SessionEnd", [])
    for hook_config in session_end_hooks:
        if isinstance(hook_config, dict):
            for hook in hook_config.get("hooks", []):
                if "terminal_session_tracker.py" in hook.get("command", ""):
                    return True
    return False


def add_terminal_tracking_hook(settings: dict, hook_script_path: str) -> dict:
    """Add terminal tracking hook to settings."""
    if "hooks" not in settings:
        settings["hooks"] = {}

    if "SessionEnd" not in settings["hooks"]:
        settings["hooks"]["SessionEnd"] = []

    # Add our hook
    new_hook = {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": f"python3 {hook_script_path}"
            }
        ]
    }
    settings["hooks"]["SessionEnd"].append(new_hook)

    return settings


def configure_terminal_tracking(
    project_dir: Optional[Path] = None,
    install_user_level: bool = True,
    install_project_level: bool = False,
    verbose: bool = False
) -> dict:
    """
    Configure Claude Code hooks for terminal token tracking.

    This function is called automatically during application initialization.

    Args:
        project_dir: Project directory for project-level hooks
        install_user_level: Install to ~/.claude/settings.json (default: True)
        install_project_level: Install to .claude/settings.json (default: False)
        verbose: Print status messages

    Returns:
        dict with installation status
    """
    result = {
        "success": True,
        "user_level": {"installed": False, "already_installed": False, "error": None},
        "project_level": {"installed": False, "already_installed": False, "error": None},
    }

    hook_script_path = get_hook_script_path()

    # Verify hook script exists
    if not Path(hook_script_path).exists():
        result["success"] = False
        result["error"] = f"Hook script not found: {hook_script_path}"
        return result

    # Make hook script executable
    try:
        os.chmod(hook_script_path, 0o755)
    except OSError:
        pass  # May fail on Windows, but that's ok

    # Install user-level hook
    if install_user_level:
        user_settings_path = get_user_settings_path()
        try:
            settings = load_settings(user_settings_path)

            if is_hook_installed(settings, hook_script_path):
                result["user_level"]["already_installed"] = True
                if verbose:
                    print(f"[HOOKS] Terminal tracking already installed (user-level)")
            else:
                settings = add_terminal_tracking_hook(settings, hook_script_path)
                if save_settings(user_settings_path, settings):
                    result["user_level"]["installed"] = True
                    if verbose:
                        print(f"[HOOKS] Terminal tracking installed (user-level)")
                else:
                    result["user_level"]["error"] = "Failed to save settings"

        except Exception as e:
            result["user_level"]["error"] = str(e)
            result["success"] = False

    # Install project-level hook
    if install_project_level and project_dir:
        project_settings_path = get_project_settings_path(project_dir)
        try:
            settings = load_settings(project_settings_path)

            if is_hook_installed(settings, hook_script_path):
                result["project_level"]["already_installed"] = True
                if verbose:
                    print(f"[HOOKS] Terminal tracking already installed (project-level)")
            else:
                settings = add_terminal_tracking_hook(settings, hook_script_path)
                if save_settings(project_settings_path, settings):
                    result["project_level"]["installed"] = True
                    if verbose:
                        print(f"[HOOKS] Terminal tracking installed (project-level)")
                else:
                    result["project_level"]["error"] = "Failed to save settings"

        except Exception as e:
            result["project_level"]["error"] = str(e)

    return result


def ensure_terminal_tracking() -> bool:
    """
    Ensure terminal tracking is configured.

    Called automatically during app initialization.
    Returns True if tracking is properly configured.
    """
    result = configure_terminal_tracking(
        install_user_level=True,
        install_project_level=False,
        verbose=False
    )

    return result["success"] and (
        result["user_level"]["installed"] or
        result["user_level"]["already_installed"]
    )


def get_tracking_status() -> dict:
    """
    Get current terminal tracking configuration status.

    Returns:
        dict with status information
    """
    hook_script_path = get_hook_script_path()
    user_settings_path = get_user_settings_path()

    status = {
        "hook_script_exists": Path(hook_script_path).exists(),
        "hook_script_path": hook_script_path,
        "user_settings_path": str(user_settings_path),
        "user_settings_exists": user_settings_path.exists(),
        "hook_installed": False,
    }

    if status["user_settings_exists"]:
        settings = load_settings(user_settings_path)
        status["hook_installed"] = is_hook_installed(settings, hook_script_path)

    return status


# Auto-configure on module import (for production use)
_initialized = False

def init():
    """Initialize terminal tracking. Called once on first import."""
    global _initialized
    if not _initialized:
        _initialized = True
        ensure_terminal_tracking()


# Don't auto-init on import to avoid side effects during testing
# Call init() explicitly or use ensure_terminal_tracking()
