#!/usr/bin/env python3
"""
Claude Code Terminal Hook Installer
====================================

Installs the terminal session tracking hook into Claude Code's settings.

Usage:
    python3 install_terminal_hook.py [--user|--project]

Options:
    --user     Install to user settings (~/.claude/settings.json)
    --project  Install to project settings (.claude/settings.json)

Default: --user
"""

import argparse
import json
import os
import sys
from pathlib import Path


def get_user_settings_path() -> Path:
    """Get path to user-level Claude Code settings."""
    return Path.home() / ".claude" / "settings.json"


def get_project_settings_path() -> Path:
    """Get path to project-level Claude Code settings."""
    return Path.cwd() / ".claude" / "settings.json"


def get_hook_script_path() -> str:
    """Get absolute path to the terminal session tracker script."""
    return str(Path(__file__).parent / "terminal_session_tracker.py")


def load_settings(settings_path: Path) -> dict:
    """Load existing settings or return empty dict."""
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {settings_path}, starting fresh")
            return {}
    return {}


def save_settings(settings_path: Path, settings: dict) -> None:
    """Save settings to file."""
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
    print(f"Settings saved to {settings_path}")


def install_hook(settings: dict, hook_script_path: str) -> dict:
    """Add terminal tracking hook to settings."""
    # Ensure hooks structure exists
    if "hooks" not in settings:
        settings["hooks"] = {}

    # Check if SessionEnd hook already exists
    if "SessionEnd" not in settings["hooks"]:
        settings["hooks"]["SessionEnd"] = []

    session_end_hooks = settings["hooks"]["SessionEnd"]

    # Check if our hook is already installed
    hook_command = f"python3 {hook_script_path}"
    for hook_config in session_end_hooks:
        if isinstance(hook_config, dict):
            for hook in hook_config.get("hooks", []):
                if hook.get("command", "").endswith("terminal_session_tracker.py"):
                    print("Terminal tracking hook already installed!")
                    return settings

    # Add our hook
    new_hook = {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": hook_command
            }
        ]
    }
    session_end_hooks.append(new_hook)

    print("Terminal tracking hook added to SessionEnd hooks")
    return settings


def install_stop_hook(settings: dict, hook_script_path: str) -> dict:
    """Add Stop hook for per-response tracking (optional)."""
    if "hooks" not in settings:
        settings["hooks"] = {}

    if "Stop" not in settings["hooks"]:
        settings["hooks"]["Stop"] = []

    # For Stop hook, we use a different script for per-response tracking
    # This is optional and more granular
    return settings


def main():
    parser = argparse.ArgumentParser(
        description="Install Claude Code terminal tracking hook"
    )
    parser.add_argument(
        "--user",
        action="store_true",
        default=True,
        help="Install to user settings (default)"
    )
    parser.add_argument(
        "--project",
        action="store_true",
        help="Install to project settings"
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the terminal tracking hook"
    )

    args = parser.parse_args()

    # Determine settings path
    if args.project:
        settings_path = get_project_settings_path()
        scope = "project"
    else:
        settings_path = get_user_settings_path()
        scope = "user"

    print(f"Installing terminal tracking hook ({scope} settings)")
    print(f"Settings file: {settings_path}")

    # Get hook script path
    hook_script_path = get_hook_script_path()
    print(f"Hook script: {hook_script_path}")

    # Verify hook script exists
    if not Path(hook_script_path).exists():
        print(f"Error: Hook script not found at {hook_script_path}")
        sys.exit(1)

    # Make hook script executable
    os.chmod(hook_script_path, 0o755)

    # Load existing settings
    settings = load_settings(settings_path)

    if args.uninstall:
        # Remove hook
        if "hooks" in settings and "SessionEnd" in settings["hooks"]:
            original_len = len(settings["hooks"]["SessionEnd"])
            settings["hooks"]["SessionEnd"] = [
                h for h in settings["hooks"]["SessionEnd"]
                if not any(
                    "terminal_session_tracker.py" in hook.get("command", "")
                    for hook in h.get("hooks", [])
                )
            ]
            if len(settings["hooks"]["SessionEnd"]) < original_len:
                print("Terminal tracking hook removed")
                save_settings(settings_path, settings)
            else:
                print("Hook not found in settings")
        else:
            print("No hooks found in settings")
        return

    # Install hook
    settings = install_hook(settings, hook_script_path)

    # Save settings
    save_settings(settings_path, settings)

    print("\n" + "=" * 60)
    print("Installation complete!")
    print("=" * 60)
    print("""
The terminal tracking hook is now installed. It will:

1. Track token usage for each Claude Code terminal session
2. Save data to .auto-claude/analytics.db in your project
3. Appear in the Analytics/ROI dashboard

To verify installation, check your settings file:
  cat """ + str(settings_path) + """

To test, run a Claude Code session and check the analytics:
  sqlite3 .auto-claude/analytics.db "SELECT * FROM feature_sessions WHERE feature_type='terminal'"

To uninstall:
  python3 """ + __file__ + """ --uninstall
""")


if __name__ == "__main__":
    main()
