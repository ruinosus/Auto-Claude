"""
Auto Claude project initialization utilities.

Handles first-time setup of .auto-claude directory and ensures proper gitignore configuration.
Also configures Claude Code hooks for terminal token tracking.
"""

from pathlib import Path

# Terminal tracking hooks configuration
_terminal_tracking_initialized = False

# All entries that should be added to .gitignore for auto-claude projects
AUTO_CLAUDE_GITIGNORE_ENTRIES = [
    ".auto-claude/",
    ".auto-claude-security.json",
    ".auto-claude-status",
    ".claude_settings.json",
    ".worktrees/",
    ".security-key",
    "logs/security/",
]


def _entry_exists_in_gitignore(lines: list[str], entry: str) -> bool:
    """Check if an entry already exists in gitignore (handles trailing slash variations)."""
    entry_normalized = entry.rstrip("/")
    for line in lines:
        line_stripped = line.strip()
        # Match both "entry" and "entry/"
        if (
            line_stripped == entry
            or line_stripped == entry_normalized
            or line_stripped == entry_normalized + "/"
        ):
            return True
    return False


def ensure_gitignore_entry(project_dir: Path, entry: str = ".auto-claude/") -> bool:
    """
    Ensure an entry exists in the project's .gitignore file.

    Creates .gitignore if it doesn't exist.

    Args:
        project_dir: The project root directory
        entry: The gitignore entry to add (default: ".auto-claude/")

    Returns:
        True if entry was added, False if it already existed
    """
    gitignore_path = project_dir / ".gitignore"

    # Check if .gitignore exists and if entry is already present
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        lines = content.splitlines()

        if _entry_exists_in_gitignore(lines, entry):
            return False  # Already exists

        # Entry doesn't exist, append it
        # Ensure file ends with newline before adding our entry
        if content and not content.endswith("\n"):
            content += "\n"

        # Add a comment and the entry
        content += "\n# Auto Claude data directory\n"
        content += entry + "\n"

        gitignore_path.write_text(content)
        return True
    else:
        # Create new .gitignore with the entry
        content = "# Auto Claude data directory\n"
        content += entry + "\n"

        gitignore_path.write_text(content)
        return True


def ensure_all_gitignore_entries(project_dir: Path) -> list[str]:
    """
    Ensure all auto-claude related entries exist in the project's .gitignore file.

    Creates .gitignore if it doesn't exist.

    Args:
        project_dir: The project root directory

    Returns:
        List of entries that were added (empty if all already existed)
    """
    gitignore_path = project_dir / ".gitignore"
    added_entries: list[str] = []

    # Read existing content or start fresh
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        lines = content.splitlines()
    else:
        content = ""
        lines = []

    # Find entries that need to be added
    entries_to_add = [
        entry
        for entry in AUTO_CLAUDE_GITIGNORE_ENTRIES
        if not _entry_exists_in_gitignore(lines, entry)
    ]

    if not entries_to_add:
        return []

    # Build the new content to append
    # Ensure file ends with newline before adding our entries
    if content and not content.endswith("\n"):
        content += "\n"

    content += "\n# Auto Claude generated files\n"
    for entry in entries_to_add:
        content += entry + "\n"
        added_entries.append(entry)

    gitignore_path.write_text(content)
    return added_entries


def init_auto_claude_dir(project_dir: Path) -> tuple[Path, bool]:
    """
    Initialize the .auto-claude directory for a project.

    Creates the directory if needed and ensures all auto-claude files are in .gitignore.

    Args:
        project_dir: The project root directory

    Returns:
        Tuple of (auto_claude_dir path, gitignore_was_updated)
    """
    project_dir = Path(project_dir)
    auto_claude_dir = project_dir / ".auto-claude"

    # Create the directory if it doesn't exist
    dir_created = not auto_claude_dir.exists()
    auto_claude_dir.mkdir(parents=True, exist_ok=True)

    # Ensure all auto-claude entries are in .gitignore (only on first creation)
    gitignore_updated = False
    if dir_created:
        added = ensure_all_gitignore_entries(project_dir)
        gitignore_updated = len(added) > 0
    else:
        # Even if dir exists, check gitignore on first run
        # Use a marker file to track if we've already checked
        marker = auto_claude_dir / ".gitignore_checked"
        if not marker.exists():
            added = ensure_all_gitignore_entries(project_dir)
            gitignore_updated = len(added) > 0
            marker.touch()

    return auto_claude_dir, gitignore_updated


def get_auto_claude_dir(project_dir: Path, ensure_exists: bool = True) -> Path:
    """
    Get the .auto-claude directory path, optionally ensuring it exists.

    Args:
        project_dir: The project root directory
        ensure_exists: If True, create directory and update gitignore if needed

    Returns:
        Path to the .auto-claude directory
    """
    if ensure_exists:
        auto_claude_dir, _ = init_auto_claude_dir(project_dir)
        return auto_claude_dir

    return Path(project_dir) / ".auto-claude"


def ensure_terminal_tracking_hooks() -> bool:
    """
    Ensure Claude Code hooks are configured for terminal token tracking.

    This is called automatically during application initialization to ensure
    all terminal sessions are tracked. This is NOT optional - it's part of
    the production-ready tracking system.

    Returns:
        True if hooks are properly configured
    """
    global _terminal_tracking_initialized

    if _terminal_tracking_initialized:
        return True

    try:
        from hooks.auto_configure import ensure_terminal_tracking
        result = ensure_terminal_tracking()
        _terminal_tracking_initialized = result
        return result
    except ImportError:
        # Hooks module not available - this shouldn't happen in production
        return False


def init_app() -> dict:
    """
    Initialize the Auto Claude application.

    This is the main initialization function that should be called on app startup.
    It configures all necessary components including terminal token tracking.

    Returns:
        dict with initialization status
    """
    status = {
        "terminal_tracking": False,
        "analytics_enabled": False,
    }

    # Configure terminal tracking hooks
    status["terminal_tracking"] = ensure_terminal_tracking_hooks()

    # Check if analytics is enabled
    try:
        from analytics import is_tracking_enabled
        status["analytics_enabled"] = is_tracking_enabled()
    except ImportError:
        pass

    return status


def get_terminal_tracking_status() -> dict:
    """
    Get the current status of terminal tracking configuration.

    Returns:
        dict with detailed status information
    """
    try:
        from hooks.auto_configure import get_tracking_status
        return get_tracking_status()
    except ImportError:
        return {
            "error": "hooks module not available",
            "hook_installed": False
        }


def repair_gitignore(project_dir: Path) -> list[str]:
    """
    Repair an existing project's .gitignore to include all auto-claude entries.

    This is useful for projects created before all entries were being added,
    or when gitignore entries were manually removed.

    Also resets the .gitignore_checked marker to allow future updates.

    Args:
        project_dir: The project root directory

    Returns:
        List of entries that were added (empty if all already existed)
    """
    project_dir = Path(project_dir)
    auto_claude_dir = project_dir / ".auto-claude"

    # Remove the marker file so future checks will also run
    marker = auto_claude_dir / ".gitignore_checked"
    if marker.exists():
        marker.unlink()

    # Add all missing entries
    added = ensure_all_gitignore_entries(project_dir)

    # Re-create the marker
    if auto_claude_dir.exists():
        marker.touch()

    return added
