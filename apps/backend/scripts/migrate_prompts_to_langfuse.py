#!/usr/bin/env python3
"""
Migrate Prompts to Langfuse
===========================

This script uploads all prompts from apps/backend/prompts/*.md to Langfuse
with proper versioning and labels.

Usage:
    python scripts/migrate_prompts_to_langfuse.py [--dry-run] [--label production]
"""

import argparse
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv(backend_path / ".env")


def migrate_prompts(dry_run: bool = False, label: str = "production"):
    """Migrate all prompts to Langfuse."""
    try:
        from langfuse import Langfuse
    except ImportError:
        print("ERROR: langfuse package not installed. Run: pip install langfuse")
        return False

    # Check environment variables
    if not os.environ.get("LANGFUSE_PUBLIC_KEY") or not os.environ.get("LANGFUSE_SECRET_KEY"):
        print("ERROR: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set")
        return False

    client = Langfuse()

    if not client.auth_check():
        print("ERROR: Langfuse authentication failed. Check your API keys.")
        return False

    prompts_dir = backend_path / "prompts"
    if not prompts_dir.exists():
        print(f"ERROR: Prompts directory not found: {prompts_dir}")
        return False

    migrated = 0
    failed = 0
    skipped = 0

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating prompts to Langfuse")
    print(f"Source: {prompts_dir}")
    print(f"Label: {label}")
    print("-" * 60)

    for prompt_file in sorted(prompts_dir.glob("*.md")):
        prompt_name = f"{prompt_file.stem}-agent"
        content = prompt_file.read_text(encoding="utf-8")

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {prompt_file.name}")
        print(f"  -> Langfuse name: {prompt_name}")
        print(f"  -> Content length: {len(content)} chars")

        if dry_run:
            migrated += 1
            continue

        try:
            # Create or update prompt in Langfuse
            client.create_prompt(
                name=prompt_name,
                prompt=content,
                labels=[label],
                type="text",
            )
            print(f"  [OK] SUCCESS: Created/updated {prompt_name}")
            migrated += 1
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                print(f"  [SKIP] SKIPPED: {prompt_name} already exists")
                skipped += 1
            else:
                print(f"  [FAIL] FAILED: {e}")
                failed += 1

    print("\n" + "-" * 60)
    print(f"{'[DRY RUN] ' if dry_run else ''}Migration complete:")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped:  {skipped}")
    print(f"  Failed:   {failed}")

    return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description="Migrate prompts from local files to Langfuse",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Dry run - show what would be done
    python scripts/migrate_prompts_to_langfuse.py --dry-run

    # Migrate with production label
    python scripts/migrate_prompts_to_langfuse.py --label production

    # Migrate with development label
    python scripts/migrate_prompts_to_langfuse.py --label development
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--label",
        default="production",
        choices=["production", "staging", "development"],
        help="Label for prompts (default: production)"
    )

    args = parser.parse_args()

    success = migrate_prompts(dry_run=args.dry_run, label=args.label)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
