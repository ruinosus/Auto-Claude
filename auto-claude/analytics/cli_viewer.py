#!/usr/bin/env python3
"""
CLI Analytics Viewer
====================

Simple CLI tool to view analytics data from SQLite database.

Usage:
    python -m analytics.cli_viewer summary           # Show all specs
    python -m analytics.cli_viewer spec 001-feature  # Show specific spec
"""

import sys
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime


def get_db_path() -> Path:
    """Get default analytics database path."""
    return Path.cwd() / ".auto-claude" / "analytics.db"


def format_cost(cost_usd: float) -> str:
    """Format cost with dollar sign and 4 decimal places."""
    return f"${cost_usd:.4f}"


def format_tokens(tokens: int) -> str:
    """Format token count with thousands separator."""
    return f"{tokens:,}"


def format_datetime(dt_str: Optional[str]) -> str:
    """Format datetime string for display."""
    if not dt_str:
        return "N/A"

    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return dt_str


def show_summary(db_path: Optional[str] = None):
    """Show summary of all specs."""
    if db_path is None:
        db_path = str(get_db_path())

    db_file = Path(db_path)

    if not db_file.exists():
        print(f"❌ Analytics database not found: {db_path}")
        print("   Run Auto-Claude to generate analytics data first.")
        return

    conn = sqlite3.connect(str(db_file))
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all spec totals
        cursor.execute("""
            SELECT * FROM spec_totals
            ORDER BY last_updated DESC
        """)

        specs = cursor.fetchall()

        if not specs:
            print("No analytics data yet.")
            return

        # Header
        print("\nAuto-Claude Analytics Summary")
        print("=" * 80)
        print()

        # Table header
        print(f"{'Spec ID':<20} {'Sessions':<10} {'Cost':<12} {'Input Tokens':<15} {'Output Tokens':<15}")
        print("-" * 80)

        # Table rows
        total_cost = 0.0
        total_sessions = 0
        total_input = 0
        total_output = 0

        for spec in specs:
            print(f"{spec['spec_id']:<20} "
                  f"{spec['total_conversations']:<10} "
                  f"{format_cost(spec['total_cost_usd']):<12} "
                  f"{format_tokens(spec['total_input_tokens']):<15} "
                  f"{format_tokens(spec['total_output_tokens']):<15}")

            total_cost += spec['total_cost_usd']
            total_sessions += spec['total_conversations']
            total_input += spec['total_input_tokens']
            total_output += spec['total_output_tokens']

        # Totals
        print("-" * 80)
        print(f"{'TOTAL':<20} "
              f"{total_sessions:<10} "
              f"{format_cost(total_cost):<12} "
              f"{format_tokens(total_input):<15} "
              f"{format_tokens(total_output):<15}")

        print()
    finally:
        conn.close()


def show_spec(spec_id: str, db_path: Optional[str] = None):
    """Show detailed view of specific spec."""
    if db_path is None:
        db_path = str(get_db_path())

    db_file = Path(db_path)

    if not db_file.exists():
        print(f"Error: Database not found at {db_file}")
        return

    conn = sqlite3.connect(str(db_file))
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get spec totals
        cursor.execute("""
            SELECT * FROM spec_totals
            WHERE spec_id = ?
        """, (spec_id,))

        spec_total = cursor.fetchone()

        if not spec_total:
            print(f"No data found for spec: {spec_id}")
            return

        # Header
        print(f"\nSpec: {spec_id}")
        print("=" * 80)
        print()

        # Summary stats
        print(f"Total Sessions:    {spec_total['total_conversations']}")
        print(f"Total Messages:    {spec_total['total_messages']}")
        print(f"Total Cost:        {format_cost(spec_total['total_cost_usd'])}")
        print(f"Total Input:       {format_tokens(spec_total['total_input_tokens'])} tokens")
        print(f"Total Output:      {format_tokens(spec_total['total_output_tokens'])} tokens")
        print(f"Last Updated:      {format_datetime(spec_total['last_updated'])}")
        print()

        # Get conversations
        cursor.execute("""
            SELECT * FROM conversations
            WHERE spec_id = ?
            ORDER BY session_number
        """, (spec_id,))

        conversations = cursor.fetchall()

        if conversations:
            print("Sessions:")
            print("-" * 80)

            for conv in conversations:
                print(f"\nSession #{conv['session_number']} - {conv['phase'].upper()}")
                print(f"  Started:       {format_datetime(conv['started_at'])}")
                print(f"  Ended:         {format_datetime(conv['ended_at'])}")
                print(f"  Model:         {conv['model'] or 'N/A'}")
                print(f"  Cost:          {format_cost(conv['total_cost_usd'] or 0.0)}")
                print(f"  Input Tokens:  {format_tokens(conv['total_input_tokens'] or 0)}")
                print(f"  Output Tokens: {format_tokens(conv['total_output_tokens'] or 0)}")

                # Get message count for this conversation
                cursor.execute("""
                    SELECT COUNT(*) as count FROM messages
                    WHERE conversation_id = ?
                """, (conv['id'],))

                msg_count = cursor.fetchone()['count']
                print(f"  Messages:      {msg_count}")

        print()
    finally:
        conn.close()


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m analytics.cli_viewer summary           # Show all specs")
        print("  python -m analytics.cli_viewer spec <spec-id>    # Show specific spec")
        sys.exit(1)

    command = sys.argv[1]

    if command == "summary":
        show_summary()
    elif command == "spec":
        if len(sys.argv) < 3:
            print("Error: spec command requires spec-id argument")
            print("Usage: python -m analytics.cli_viewer spec <spec-id>")
            sys.exit(1)

        spec_id = sys.argv[2]
        show_spec(spec_id)
    else:
        print(f"Unknown command: {command}")
        print("Valid commands: summary, spec")
        sys.exit(1)


if __name__ == "__main__":
    main()
