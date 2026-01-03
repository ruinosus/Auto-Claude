"""
ROI Activity Tracking Tools
============================

Tools for agents to report activities that contribute to ROI.
Instead of agents estimating dollar values, they report structured activities
that are converted to value using predefined rules.

This follows the Activity-Based Value Attribution pattern where:
1. Agent performs an action
2. Agent reports the activity type with objective metrics
3. System calculates value based on predefined rules
4. Value is persisted to Langfuse for ROI tracking
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None

logger = logging.getLogger(__name__)

# =============================================================================
# Activity Type Definitions
# =============================================================================
# Each activity type has:
# - category: execution | decision | prevention | knowledge
# - base_value: Base value in USD for this activity
# - unit: How the value scales (per_file, per_item, etc.)
# - description: Human-readable description

ACTIVITY_TYPES = {
    # -------------------------------------------------------------------------
    # EXECUTION: Direct code/implementation work
    # -------------------------------------------------------------------------
    "file_created": {
        "category": "execution",
        "base_value": 50.0,
        "unit": "per_file",
        "description": "Created a new file",
    },
    "file_modified": {
        "category": "execution",
        "base_value": 30.0,
        "unit": "per_file",
        "description": "Modified an existing file",
    },
    "test_created": {
        "category": "execution",
        "base_value": 75.0,
        "unit": "per_test",
        "description": "Created a test file or test case",
    },
    "code_refactored": {
        "category": "execution",
        "base_value": 100.0,
        "unit": "per_refactor",
        "description": "Refactored code for better maintainability",
    },
    "bug_fixed": {
        "category": "execution",
        "base_value": 150.0,
        "unit": "per_bug",
        "description": "Fixed a bug in the code",
    },
    "feature_implemented": {
        "category": "execution",
        "base_value": 200.0,
        "unit": "per_feature",
        "description": "Implemented a new feature",
    },
    # -------------------------------------------------------------------------
    # DECISION: Strategic choices and prioritization
    # -------------------------------------------------------------------------
    "recommendation_made": {
        "category": "decision",
        "base_value": 100.0,
        "unit": "per_item",
        "description": "Made a recommendation or suggestion",
    },
    "priority_evaluated": {
        "category": "decision",
        "base_value": 50.0,
        "unit": "per_item",
        "description": "Evaluated and prioritized items",
    },
    "architecture_decision": {
        "category": "decision",
        "base_value": 250.0,
        "unit": "per_decision",
        "description": "Made an architectural decision",
    },
    "trade_off_analyzed": {
        "category": "decision",
        "base_value": 75.0,
        "unit": "per_analysis",
        "description": "Analyzed trade-offs between options",
    },
    "roadmap_item_created": {
        "category": "decision",
        "base_value": 150.0,
        "unit": "per_item",
        "description": "Created a roadmap item or milestone",
    },
    # -------------------------------------------------------------------------
    # PREVENTION: Issues avoided, bugs caught, security findings
    # -------------------------------------------------------------------------
    "bug_identified": {
        "category": "prevention",
        "base_value": 300.0,
        "unit": "per_bug",
        "description": "Identified a bug before it reached production",
    },
    "security_issue_found": {
        "category": "prevention",
        "base_value": 1000.0,
        "unit": "per_issue",
        "description": "Found a security vulnerability",
    },
    "improvement_suggested": {
        "category": "prevention",
        "base_value": 50.0,
        "unit": "per_item",
        "description": "Suggested an improvement",
    },
    "performance_issue_found": {
        "category": "prevention",
        "base_value": 200.0,
        "unit": "per_issue",
        "description": "Found a performance issue",
    },
    "code_smell_identified": {
        "category": "prevention",
        "base_value": 25.0,
        "unit": "per_item",
        "description": "Identified a code smell or anti-pattern",
    },
    "test_failure_prevented": {
        "category": "prevention",
        "base_value": 100.0,
        "unit": "per_test",
        "description": "Prevented a test from failing",
    },
    # -------------------------------------------------------------------------
    # KNOWLEDGE: Insights, documentation, understanding
    # -------------------------------------------------------------------------
    "question_answered": {
        "category": "knowledge",
        "base_value": 25.0,
        "unit": "per_question",
        "description": "Answered a question about the codebase",
    },
    "diagram_generated": {
        "category": "knowledge",
        "base_value": 150.0,
        "unit": "per_diagram",
        "description": "Generated a diagram (architecture, flow, etc.)",
    },
    "codebase_explored": {
        "category": "knowledge",
        "base_value": 10.0,
        "unit": "per_file",
        "description": "Explored and analyzed codebase files",
    },
    "documentation_created": {
        "category": "knowledge",
        "base_value": 100.0,
        "unit": "per_doc",
        "description": "Created documentation",
    },
    "pattern_identified": {
        "category": "knowledge",
        "base_value": 75.0,
        "unit": "per_pattern",
        "description": "Identified a pattern or convention in the codebase",
    },
    "dependency_analyzed": {
        "category": "knowledge",
        "base_value": 50.0,
        "unit": "per_dependency",
        "description": "Analyzed a dependency or library",
    },
    "spec_created": {
        "category": "knowledge",
        "base_value": 200.0,
        "unit": "per_spec",
        "description": "Created a specification document",
    },
    "context_gathered": {
        "category": "knowledge",
        "base_value": 30.0,
        "unit": "per_context",
        "description": "Gathered context for a task",
    },
}

# Valid categories for validation
VALID_CATEGORIES = ["execution", "decision", "prevention", "knowledge"]


def get_activity_value(
    activity_type: str,
    count: int = 1,
    complexity_multiplier: float = 1.0,
) -> tuple[float, str]:
    """
    Calculate the value for an activity based on predefined rules.

    Args:
        activity_type: The type of activity from ACTIVITY_TYPES
        count: Number of items (for per_* unit types)
        complexity_multiplier: Optional multiplier for complexity (0.5-2.0)

    Returns:
        Tuple of (value_usd, category)
    """
    if activity_type not in ACTIVITY_TYPES:
        logger.warning(f"Unknown activity type: {activity_type}")
        return 0.0, "unknown"

    activity = ACTIVITY_TYPES[activity_type]
    base_value = activity["base_value"]
    category = activity["category"]

    # Clamp complexity multiplier to reasonable range
    complexity_multiplier = max(0.5, min(2.0, complexity_multiplier))

    # Calculate total value
    value = base_value * count * complexity_multiplier

    return value, category


def create_roi_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create ROI tracking tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of ROI tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []

    # -------------------------------------------------------------------------
    # Tool: report_activity
    # -------------------------------------------------------------------------
    @tool(
        "report_activity",
        """Report a completed activity for ROI tracking.

Call this tool after completing meaningful work to track the value generated.
The system will automatically calculate the value based on the activity type.

Common activity types:
- EXECUTION: file_created, file_modified, test_created, bug_fixed, feature_implemented
- DECISION: recommendation_made, architecture_decision, priority_evaluated
- PREVENTION: bug_identified, security_issue_found, improvement_suggested
- KNOWLEDGE: question_answered, diagram_generated, documentation_created, codebase_explored

Example usage:
- After generating an architecture diagram: activity_type="diagram_generated", count=1
- After answering 3 questions about the codebase: activity_type="question_answered", count=3
- After identifying 2 bugs during review: activity_type="bug_identified", count=2
- After creating a spec: activity_type="spec_created", count=1""",
        {
            "activity_type": str,
            "description": str,
            "count": int,
            "artifacts": list,
            "complexity": str,
        },
    )
    async def report_activity(args: dict[str, Any]) -> dict[str, Any]:
        """Report an activity for ROI tracking."""
        activity_type = args.get("activity_type", "")
        description = args.get("description", "")
        count = args.get("count", 1)
        artifacts = args.get("artifacts", [])
        complexity = args.get("complexity", "medium")  # low, medium, high

        # Validate activity type
        if activity_type not in ACTIVITY_TYPES:
            available = sorted(ACTIVITY_TYPES.keys())
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Unknown activity type '{activity_type}'.\n\n"
                        f"Available types:\n"
                        + "\n".join(f"  - {t}" for t in available),
                    }
                ]
            }

        # Map complexity to multiplier
        complexity_multipliers = {
            "low": 0.7,
            "medium": 1.0,
            "high": 1.5,
        }
        complexity_multiplier = complexity_multipliers.get(complexity, 1.0)

        # Calculate value
        value, category = get_activity_value(
            activity_type, count, complexity_multiplier
        )

        # Build activity record
        activity_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "activity_type": activity_type,
            "category": category,
            "description": description,
            "count": count,
            "complexity": complexity,
            "complexity_multiplier": complexity_multiplier,
            "value_usd": value,
            "artifacts": artifacts,
            "base_value": ACTIVITY_TYPES[activity_type]["base_value"],
            "unit": ACTIVITY_TYPES[activity_type]["unit"],
        }

        # Save to local file
        activities_file = spec_dir / "roi_activities.json"
        try:
            if activities_file.exists():
                with open(activities_file) as f:
                    activities = json.load(f)
            else:
                activities = {"activities": [], "total_value_usd": 0.0}

            activities["activities"].append(activity_record)
            activities["total_value_usd"] = sum(
                a.get("value_usd", 0) for a in activities["activities"]
            )
            activities["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Calculate category totals
            category_totals = {"execution": 0.0, "decision": 0.0, "prevention": 0.0, "knowledge": 0.0}
            for a in activities["activities"]:
                cat = a.get("category", "knowledge")
                category_totals[cat] = category_totals.get(cat, 0.0) + a.get("value_usd", 0.0)
            activities["category_totals"] = category_totals

            with open(activities_file, "w") as f:
                json.dump(activities, f, indent=2)

            # Also try to publish to Langfuse if available
            langfuse_result = await _publish_to_langfuse(
                activity_record, spec_dir, project_dir
            )

            result_text = (
                f"Activity recorded successfully!\n\n"
                f"Type: {activity_type}\n"
                f"Category: {category}\n"
                f"Count: {count}\n"
                f"Complexity: {complexity} ({complexity_multiplier}x)\n"
                f"Value: ${value:.2f}\n"
                f"Session Total: ${activities['total_value_usd']:.2f}\n"
            )

            if langfuse_result:
                result_text += f"\nLangfuse: {langfuse_result}"

            return {"content": [{"type": "text", "text": result_text}]}

        except Exception as e:
            logger.error(f"Error saving activity: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error saving activity: {e}"}
                ]
            }

    tools.append(report_activity)

    # -------------------------------------------------------------------------
    # Tool: get_activity_summary
    # -------------------------------------------------------------------------
    @tool(
        "get_activity_summary",
        "Get a summary of all activities recorded in this session.",
        {},
    )
    async def get_activity_summary(args: dict[str, Any]) -> dict[str, Any]:
        """Get summary of recorded activities."""
        activities_file = spec_dir / "roi_activities.json"

        if not activities_file.exists():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "No activities recorded yet in this session.",
                    }
                ]
            }

        try:
            with open(activities_file) as f:
                data = json.load(f)

            activities = data.get("activities", [])
            total_value = data.get("total_value_usd", 0.0)
            category_totals = data.get("category_totals", {})

            if not activities:
                return {
                    "content": [
                        {"type": "text", "text": "No activities recorded yet."}
                    ]
                }

            summary_lines = [
                f"=== Activity Summary ===",
                f"Total Activities: {len(activities)}",
                f"Total Value: ${total_value:.2f}",
                f"",
                f"By Category:",
            ]

            for cat, val in sorted(category_totals.items()):
                if val > 0:
                    summary_lines.append(f"  {cat.capitalize()}: ${val:.2f}")

            summary_lines.append("")
            summary_lines.append("Recent Activities:")

            for activity in activities[-5:]:
                summary_lines.append(
                    f"  - {activity['activity_type']}: ${activity['value_usd']:.2f} "
                    f"({activity.get('description', '')[:30]}...)"
                )

            return {
                "content": [{"type": "text", "text": "\n".join(summary_lines)}]
            }

        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error reading activities: {e}"}
                ]
            }

    tools.append(get_activity_summary)

    # -------------------------------------------------------------------------
    # Tool: list_activity_types
    # -------------------------------------------------------------------------
    @tool(
        "list_activity_types",
        "List all available activity types and their values.",
        {"category": str},
    )
    async def list_activity_types(args: dict[str, Any]) -> dict[str, Any]:
        """List available activity types."""
        category_filter = args.get("category", "").lower()

        lines = ["=== Available Activity Types ===", ""]

        current_category = None
        for activity_type, info in sorted(
            ACTIVITY_TYPES.items(), key=lambda x: (x[1]["category"], x[0])
        ):
            cat = info["category"]

            # Filter by category if specified
            if category_filter and cat != category_filter:
                continue

            if cat != current_category:
                if current_category is not None:
                    lines.append("")
                lines.append(f"## {cat.upper()}")
                current_category = cat

            lines.append(
                f"  {activity_type}: ${info['base_value']:.0f} {info['unit']}"
            )
            lines.append(f"    {info['description']}")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    tools.append(list_activity_types)

    return tools


async def _publish_to_langfuse(
    activity_record: dict,
    spec_dir: Path,
    project_dir: Path,
) -> Optional[str]:
    """
    Publish activity to Langfuse for persistent ROI tracking.

    Returns status message or None if Langfuse is not available.
    """
    try:
        # Check if Langfuse is enabled
        if not os.environ.get("LANGFUSE_ENABLED", "").lower() == "true":
            return None

        # Import Langfuse integration
        from analytics.langfuse_integration import (
            get_langfuse_client,
            flush_langfuse,
        )

        client = get_langfuse_client()
        if not client:
            return None

        # Get project name for tagging
        project_name = project_dir.name if project_dir else "unknown"

        # Create a trace for this activity
        trace = client.trace(
            name=f"activity-{activity_record['activity_type']}",
            metadata={
                "activity_type": activity_record["activity_type"],
                "category": activity_record["category"],
                "count": activity_record["count"],
                "complexity": activity_record["complexity"],
                "value_usd": activity_record["value_usd"],
                "project_id": project_name,
                "roi_activity": True,
            },
            tags=[
                f"activity:{activity_record['activity_type']}",
                f"category:{activity_record['category']}",
                f"project:{project_name}",
                "roi",
            ],
        )

        # Create scores for ROI tracking
        if trace and trace.id:
            # Value score
            client.create_score(
                trace_id=trace.id,
                name=f"value_{activity_record['category']}_usd",
                value=activity_record["value_usd"],
                comment=f"Auto-reported by agent: {activity_record['description'][:100]}",
            )

            # Total value score
            client.create_score(
                trace_id=trace.id,
                name="total_value_usd",
                value=activity_record["value_usd"],
                comment=f"Activity: {activity_record['activity_type']}",
            )

            # Activity count score
            client.create_score(
                trace_id=trace.id,
                name=f"activity_{activity_record['activity_type']}_count",
                value=float(activity_record["count"]),
                comment=f"Count of {activity_record['activity_type']} activities",
            )

            flush_langfuse()
            return f"Published to trace {trace.id[:8]}..."

        return None

    except ImportError:
        logger.debug("Langfuse integration not available")
        return None
    except Exception as e:
        logger.warning(f"Failed to publish to Langfuse: {e}")
        return None
