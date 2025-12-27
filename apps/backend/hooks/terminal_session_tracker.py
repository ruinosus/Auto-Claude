#!/usr/bin/env python3
"""
Claude Code Terminal Session Tracker Hook
==========================================

This script is called by Claude Code's SessionEnd hook to track
terminal token usage in the Auto Claude analytics database.

Installation:
1. Add to ~/.claude/settings.json or .claude/settings.json:

{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/apps/backend/hooks/terminal_session_tracker.py"
          }
        ]
      }
    ]
  }
}

2. Or use the install script:
   python3 apps/backend/hooks/install_terminal_hook.py

The hook receives session data via stdin as JSON with format:
{
  "session_id": "abc123",
  "transcript_path": "~/.claude/projects/.../session.jsonl",
  "cwd": "/path/to/project",
  "permission_mode": "default",
  "hook_event_name": "SessionEnd",
  "reason": "exit"
}

The transcript JSONL file contains messages with usage data.
"""

import json
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# Add backend path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


def get_project_id_from_cwd(cwd: str) -> str:
    """Extract project ID from working directory."""
    path = Path(cwd)
    return path.name


def get_analytics_db_path(cwd: str) -> str:
    """Get path to analytics database for the project."""
    project_dir = Path(cwd)
    return str(project_dir / ".auto-claude" / "analytics.db")


def parse_transcript_usage(transcript_path: str) -> dict:
    """
    Parse Claude Code transcript JSONL file to extract token usage.

    Returns:
        dict with input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens
    """
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "num_turns": 0,
        "model": "claude-sonnet-4-5",
    }

    transcript_file = Path(transcript_path).expanduser()

    if not transcript_file.exists():
        print(f"[TERMINAL_TRACKER] Transcript file not found: {transcript_path}", file=sys.stderr)
        return usage

    try:
        with open(transcript_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Only process assistant messages with usage data
                if msg.get("type") != "assistant":
                    continue

                message = msg.get("message", {})
                msg_usage = message.get("usage", {})

                if not msg_usage:
                    continue

                # Get model from message
                if message.get("model"):
                    usage["model"] = message["model"]

                # Accumulate token usage
                usage["input_tokens"] += msg_usage.get("input_tokens", 0) or 0
                usage["output_tokens"] += msg_usage.get("output_tokens", 0) or 0
                usage["cache_read_tokens"] += msg_usage.get("cache_read_input_tokens", 0) or 0
                usage["cache_creation_tokens"] += msg_usage.get("cache_creation_input_tokens", 0) or 0
                usage["num_turns"] += 1

    except Exception as e:
        print(f"[TERMINAL_TRACKER] Error parsing transcript: {e}", file=sys.stderr)

    return usage


async def track_terminal_session(session_data: dict) -> None:
    """Track terminal session in analytics database."""
    try:
        from analytics import (
            create_feature_tracker,
            FEATURE_TERMINAL,
            is_tracking_enabled,
        )
    except ImportError as e:
        print(f"[TERMINAL_TRACKER] Failed to import analytics: {e}", file=sys.stderr)
        return

    if not is_tracking_enabled():
        print("[TERMINAL_TRACKER] Tracking is disabled", file=sys.stderr)
        return

    # Extract session info from hook input
    cwd = session_data.get("cwd", os.getcwd())
    session_id = session_data.get("session_id", "unknown")
    transcript_path = session_data.get("transcript_path", "")
    reason = session_data.get("reason", "unknown")

    # Parse transcript file to get actual token usage
    usage = parse_transcript_usage(transcript_path) if transcript_path else {
        "input_tokens": 0, "output_tokens": 0,
        "cache_read_tokens": 0, "cache_creation_tokens": 0,
        "num_turns": 0, "model": "claude-sonnet-4-5"
    }

    input_tokens = usage["input_tokens"]
    output_tokens = usage["output_tokens"]
    cache_read_tokens = usage["cache_read_tokens"]
    cache_creation_tokens = usage["cache_creation_tokens"]
    num_turns = usage["num_turns"]
    model = usage["model"]

    # Skip if no tokens were used
    if input_tokens == 0 and output_tokens == 0:
        print(f"[TERMINAL_TRACKER] No token usage found for session {session_id}", file=sys.stderr)
        return

    # Get project info
    project_id = get_project_id_from_cwd(cwd)
    db_path = get_analytics_db_path(cwd)

    # Ensure .auto-claude directory exists
    auto_claude_dir = Path(cwd) / ".auto-claude"
    auto_claude_dir.mkdir(parents=True, exist_ok=True)

    # Create tracker
    tracker = create_feature_tracker(
        project_id=project_id,
        feature_type=FEATURE_TERMINAL,
        db_path=db_path,
        metadata={
            "claude_code_session_id": session_id,
            "num_turns": num_turns,
            "reason": reason,
            "transcript_path": transcript_path,
        }
    )

    # Start session
    await tracker.start_session()

    # Track usage from parsed transcript
    await tracker.track_usage(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_creation_tokens=cache_creation_tokens,
    )

    # Finalize
    await tracker.finalize()

    totals = tracker.get_totals()
    print(f"[TERMINAL_TRACKER] Session tracked: project={project_id}, "
          f"cost=${totals.get('total_cost_usd', 0):.4f}, "
          f"tokens={input_tokens}/{output_tokens}",
          file=sys.stderr)


def main():
    """Main entry point for hook."""
    try:
        # Read session data from stdin
        input_data = sys.stdin.read()

        if not input_data.strip():
            print("[TERMINAL_TRACKER] No input data received", file=sys.stderr)
            sys.exit(0)

        session_data = json.loads(input_data)

        # Run async tracking
        asyncio.run(track_terminal_session(session_data))

    except json.JSONDecodeError as e:
        print(f"[TERMINAL_TRACKER] Failed to parse JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[TERMINAL_TRACKER] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
