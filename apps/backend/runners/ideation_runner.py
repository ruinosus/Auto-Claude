#!/usr/bin/env python3
"""
Ideation Creation Orchestrator (Facade)
========================================

This is a facade that maintains backward compatibility with the original
ideation_runner.py interface while delegating to the refactored modular
components in the ideation/ package.

AI-powered ideation generation for projects.
Analyzes project context, existing features, and generates three types of ideas:
1. Low-Hanging Fruit - Quick wins building on existing patterns
2. UI/UX Improvements - Visual and interaction enhancements
3. High-Value Features - Strategic features for target users

Usage:
    python auto-claude/ideation_runner.py --project /path/to/project
    python auto-claude/ideation_runner.py --project /path/to/project --types low_hanging_fruit,high_value_features
    python auto-claude/ideation_runner.py --project /path/to/project --refresh
"""

import asyncio
import sys
from pathlib import Path

# Add auto-claude to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file from auto-claude/ directory
from dotenv import load_dotenv

env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Clean up conflicting env vars (Foundry vs standard mode)
from core.auth import cleanup_conflicting_env_vars
cleanup_conflicting_env_vars()

# Import from refactored modules
from ideation import (
    IdeationConfig,
    IdeationOrchestrator,
    IdeationPhaseResult,
)
from ideation.generator import IDEATION_TYPE_LABELS, IDEATION_TYPES

# Graceful imports for artifact storage
try:
    from analytics.artifact_storage import (
        save_artifact_safe,
        create_langfuse_reference,
        _get_artifacts_dir,
    )
    ARTIFACT_STORAGE_AVAILABLE = True
except ImportError:
    ARTIFACT_STORAGE_AVAILABLE = False
    save_artifact_safe = None
    create_langfuse_reference = None
    _get_artifacts_dir = None

# Graceful imports for ROI publishing
try:
    from analytics.roi_publisher import publish_ideation_roi
    ROI_PUBLISHER_AVAILABLE = True
except ImportError:
    ROI_PUBLISHER_AVAILABLE = False
    publish_ideation_roi = None

# =============================================================================
# ARTIFACT EXTRACTION
# =============================================================================


def extract_ideation_artifacts(
    ideas: list[dict],
    project_dir: Path | None = None,
    trace_id: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Extract artifacts from generated ideation ideas.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    Artifacts extracted:
    - idea ($50 each) - each generated idea
    - recommendation ($75 each) - ideas with actionable recommendations
    - analysis_insight ($100 each) - ideas with deep analysis/strategic value

    Args:
        ideas: List of idea dictionaries from ideation.json
        project_dir: Project root directory for local storage
        trace_id: Langfuse trace ID for linking

    Returns:
        Tuple of (local_artifacts, langfuse_refs):
        - local_artifacts: Full artifacts for local processing
        - langfuse_refs: Truncated references for Langfuse (or full artifacts if storage unavailable)
    """
    from datetime import datetime

    artifacts = []

    for idea in ideas:
        idea_type = idea.get("ideation_type", idea.get("type", "unknown"))
        title = idea.get("title", "Untitled")
        description = idea.get("description", "")
        priority = idea.get("priority", "medium").lower()
        complexity = idea.get("complexity", "medium")
        rationale = idea.get("rationale", "")

        # Build FULL content - no truncation
        content = f"# {title}\n\n"
        content += f"**Type**: {IDEATION_TYPE_LABELS.get(idea_type, idea_type)}\n"
        content += f"**Priority**: {priority.upper()}\n"
        content += f"**Complexity**: {complexity}\n\n"
        content += f"## Description\n{description}\n"

        if rationale:
            content += f"\n## Rationale\n{rationale}\n"

        # Include implementation hints if present
        implementation = idea.get("implementation_hints", idea.get("implementation", ""))
        if implementation:
            content += f"\n## Implementation\n{implementation}\n"

        # Include dependencies if present
        dependencies = idea.get("dependencies", [])
        if dependencies:
            content += f"\n## Dependencies\n"
            for dep in dependencies:
                content += f"- {dep}\n"

        # Determine artifact type and value based on idea characteristics
        if priority == "high" and len(description) > 200:
            # High priority with substantial description = analysis insight
            artifact_type = "analysis_insight"
            value_usd = 100
            tab = "business"
        elif any(kw in description.lower() for kw in ["recommend", "should", "consider", "improve", "enhance"]):
            # Contains recommendation language
            artifact_type = "recommendation"
            value_usd = 75
            tab = "business"
        else:
            # Standard idea
            artifact_type = "idea"
            value_usd = 50
            # Tab based on ideation type
            if idea_type in ["security_hardening"]:
                tab = "ops"
            elif idea_type in ["ui_ux_improvements"]:
                tab = "techlead"
            elif idea_type in ["code_improvements", "code_quality", "performance_optimizations"]:
                tab = "dev"
            else:
                tab = "business"

        artifacts.append({
            "type": artifact_type,
            "format": "markdown",
            "content": content,
            "value_usd": value_usd,
            "description": f"{IDEATION_TYPE_LABELS.get(idea_type, idea_type)}: {title}",
            "tab": tab,
            "metadata": {
                "ideation_type": idea_type,
                "title": title,
                "priority": priority,
                "complexity": complexity,
            },
        })

    # Save artifacts locally and create Langfuse references
    if ARTIFACT_STORAGE_AVAILABLE and project_dir and save_artifact_safe and create_langfuse_reference and _get_artifacts_dir:
        langfuse_refs = []
        for artifact in artifacts:
            # Save full artifact locally
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_dir,
                spec_id=None,  # Ideation doesn't have spec_id
                trace_id=trace_id,
                agent_type="ideation",
                session_num=None,
            )

            if artifact_id:
                # Create lightweight reference for Langfuse
                artifacts_dir = _get_artifacts_dir(project_dir)
                storage_path = str(
                    (artifacts_dir / datetime.now().strftime("%Y-%m-%d") / f"{artifact_id}.json")
                )
                ref = create_langfuse_reference(artifact, artifact_id, storage_path)
                langfuse_refs.append(ref)
            else:
                # Fallback: if storage fails, include full artifact as ref
                langfuse_refs.append(artifact)

        return artifacts, langfuse_refs
    else:
        # No local storage available - return artifacts as both
        return artifacts, artifacts


# Re-export for backward compatibility
__all__ = [
    "IdeationOrchestrator",
    "IdeationConfig",
    "IdeationPhaseResult",
    "IDEATION_TYPES",
    "IDEATION_TYPE_LABELS",
    "extract_ideation_artifacts",
    "ARTIFACT_STORAGE_AVAILABLE",
    "ROI_PUBLISHER_AVAILABLE",
]


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="AI-powered ideation generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for ideation files (default: project/auto-claude/ideation)",
    )
    parser.add_argument(
        "--types",
        type=str,
        help=f"Comma-separated ideation types to run (options: {','.join(IDEATION_TYPES)})",
    )
    parser.add_argument(
        "--no-roadmap",
        action="store_true",
        help="Don't include roadmap context",
    )
    parser.add_argument(
        "--no-kanban",
        action="store_true",
        help="Don't include kanban context",
    )
    parser.add_argument(
        "--max-ideas",
        type=int,
        default=5,
        help="Maximum ideas per type (default: 5)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="sonnet",  # Changed from "opus" (fix #433)
        help="Model to use (haiku, sonnet, opus, or full model ID)",
    )
    parser.add_argument(
        "--thinking-level",
        type=str,
        default="medium",
        choices=["none", "low", "medium", "high", "ultrathink"],
        help="Thinking level for extended reasoning (default: medium)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force regeneration even if ideation exists",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append new ideas to existing session instead of replacing",
    )

    args = parser.parse_args()

    # Validate project directory
    project_dir = args.project.resolve()
    if not project_dir.exists():
        print(f"Error: Project directory does not exist: {project_dir}")
        sys.exit(1)

    # Parse types
    enabled_types = None
    if args.types:
        enabled_types = [t.strip() for t in args.types.split(",")]
        invalid_types = [t for t in enabled_types if t not in IDEATION_TYPES]
        if invalid_types:
            print(f"Error: Invalid ideation types: {invalid_types}")
            print(f"Valid types: {IDEATION_TYPES}")
            sys.exit(1)

    orchestrator = IdeationOrchestrator(
        project_dir=project_dir,
        output_dir=args.output,
        enabled_types=enabled_types,
        include_roadmap_context=not args.no_roadmap,
        include_kanban_context=not args.no_kanban,
        max_ideas_per_type=args.max_ideas,
        model=args.model,
        thinking_level=args.thinking_level,
        refresh=args.refresh,
        append=args.append,
    )

    try:
        success = asyncio.run(orchestrator.run())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nIdeation generation interrupted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
