"""
Artifact Creation Tools
=======================

MCP tools for agents to create structured artifacts directly.
Instead of generating free-form text that needs regex parsing,
agents call these tools to create concrete, typed artifacts.

Benefits:
- 100% reliable artifact structure (no parsing errors)
- Full content preserved (no truncation at extraction)
- Proper metadata attached (trace_id, project_id, etc.)
- Automatic local storage + Langfuse reference
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None

logger = logging.getLogger(__name__)

# =============================================================================
# Artifact Type Definitions
# =============================================================================
# Each artifact type has predefined base value and tab assignment

ARTIFACT_TYPES = {
    # -------------------------------------------------------------------------
    # DIAGRAMS & VISUALS
    # -------------------------------------------------------------------------
    "diagram": {
        "base_value": 150,
        "tab": "techlead",
        "description": "Architecture, flow, or sequence diagram",
        "formats": ["mermaid", "ascii", "plantuml"],
    },
    # -------------------------------------------------------------------------
    # CODE & IMPLEMENTATION
    # -------------------------------------------------------------------------
    "code_example": {
        "base_value": 25,
        "tab": "dev",
        "description": "Code snippet or implementation example",
        "formats": ["python", "typescript", "javascript", "go", "rust", "sql", "bash", "text"],
    },
    "refactoring": {
        "base_value": 100,
        "tab": "dev",
        "description": "Refactoring suggestion with before/after",
        "formats": ["markdown", "diff"],
    },
    "bug_fix": {
        "base_value": 100,
        "tab": "dev",
        "description": "Bug fix suggestion or solution",
        "formats": ["markdown", "text"],
    },
    "test_case": {
        "base_value": 75,
        "tab": "dev",
        "description": "Test case or testing strategy",
        "formats": ["markdown", "code"],
    },
    # -------------------------------------------------------------------------
    # SECURITY & OPS
    # -------------------------------------------------------------------------
    "security_finding": {
        "base_value": 200,
        "tab": "ops",
        "description": "Security vulnerability or concern",
        "formats": ["markdown", "text"],
    },
    "performance_insight": {
        "base_value": 150,
        "tab": "ops",
        "description": "Performance issue or optimization",
        "formats": ["markdown", "text"],
    },
    # -------------------------------------------------------------------------
    # ARCHITECTURE & DESIGN
    # -------------------------------------------------------------------------
    "architecture_insight": {
        "base_value": 125,
        "tab": "techlead",
        "description": "Architecture pattern or design decision",
        "formats": ["markdown", "text"],
    },
    "api_design": {
        "base_value": 100,
        "tab": "techlead",
        "description": "API design suggestion or schema",
        "formats": ["markdown", "json", "yaml", "openapi"],
    },
    "documentation": {
        "base_value": 50,
        "tab": "techlead",
        "description": "Documentation insight or improvement",
        "formats": ["markdown", "text"],
    },
    # -------------------------------------------------------------------------
    # BUSINESS & STRATEGY
    # -------------------------------------------------------------------------
    "recommendation": {
        "base_value": 50,
        "tab": "business",
        "description": "Strategic recommendation or suggestion",
        "formats": ["markdown", "text"],
    },
    "cost_analysis": {
        "base_value": 75,
        "tab": "business",
        "description": "Cost, ROI, or business impact analysis",
        "formats": ["markdown", "text"],
    },
    "priority_assessment": {
        "base_value": 75,
        "tab": "business",
        "description": "Priority or risk assessment",
        "formats": ["markdown", "text"],
    },
}

# Map tabs to readable names
TAB_NAMES = {
    "dev": "Developer",
    "techlead": "Tech Lead",
    "ops": "Operations",
    "business": "Business",
}

# Map artifact types to ROI activity types
ARTIFACT_TO_ACTIVITY = {
    "diagram": "diagram_generated",
    "code_example": "pattern_identified",
    "refactoring": "code_refactored",
    "bug_fix": "bug_identified",
    "test_case": "test_created",
    "security_finding": "security_issue_found",
    "performance_insight": "performance_issue_found",
    "architecture_insight": "architecture_decision",
    "api_design": "architecture_decision",
    "documentation": "documentation_created",
    "recommendation": "recommendation_made",
    "cost_analysis": "trade_off_analyzed",
    "priority_assessment": "priority_evaluated",
}

# Map tabs to ROI categories
TAB_TO_CATEGORY = {
    "dev": "execution",
    "techlead": "decision",
    "ops": "prevention",
    "business": "decision",
}


def calculate_artifact_value(
    artifact_type: str,
    content: str,
    complexity: str = "medium",
) -> int:
    """
    Calculate artifact value based on type, content length, and complexity.

    Args:
        artifact_type: The type of artifact
        content: The full content
        complexity: low, medium, or high

    Returns:
        Value in USD
    """
    if artifact_type not in ARTIFACT_TYPES:
        return 25  # Default minimum value

    base_value = ARTIFACT_TYPES[artifact_type]["base_value"]

    # Content length bonus (every 200 chars adds value)
    content_bonus = (len(content) // 200) * 5
    content_bonus = min(content_bonus, 100)  # Cap at $100 bonus

    # Complexity multiplier
    complexity_multipliers = {
        "low": 0.7,
        "medium": 1.0,
        "high": 1.5,
    }
    multiplier = complexity_multipliers.get(complexity, 1.0)

    total_value = int((base_value + content_bonus) * multiplier)
    return total_value


async def _publish_artifact_roi(
    artifact: dict,
    artifact_id: str,
    project_dir: Path,
    spec_dir: Path | None = None,
) -> str | None:
    """
    Publish artifact creation as ROI activity to Langfuse.

    This integrates artifact creation with the ROI tracking system,
    ensuring all artifacts contribute to measurable value.

    Returns:
        Status message or None if Langfuse unavailable
    """
    import os

    try:
        # Check if Langfuse is enabled
        if not os.environ.get("LANGFUSE_ENABLED", "").lower() == "true":
            return None

        from analytics.langfuse_integration import (
            get_langfuse_client,
            flush_langfuse,
            get_current_trace_id,
        )

        client = get_langfuse_client()
        if not client:
            return None

        # Map artifact type to activity type
        artifact_type = artifact.get("type", "unknown")
        activity_type = ARTIFACT_TO_ACTIVITY.get(artifact_type, "pattern_identified")

        # Get category from tab
        tab = artifact.get("tab", "dev")
        category = TAB_TO_CATEGORY.get(tab, "knowledge")

        # Get project name
        project_name = project_dir.name if project_dir else "unknown"

        # Get trace_id from thread-local storage (thread-safe for concurrent execution)
        # Falls back to environment variable for backwards compatibility
        trace_id = get_current_trace_id() or os.environ.get("LANGFUSE_TRACE_ID")

        value_usd = artifact.get("value_usd", 0)

        if trace_id:
            # Add score to existing trace
            client.score(
                trace_id=trace_id,
                name=f"artifact_{artifact_type}_value",
                value=float(value_usd),
                comment=f"Artifact created: {artifact.get('description', '')[:100]}",
            )

            # Also add to total value
            client.score(
                trace_id=trace_id,
                name="total_value_usd",
                value=float(value_usd),
                comment=f"Artifact: {artifact_type}",
            )

            flush_langfuse()
            return f"ROI added to trace {trace_id[:8]}..."

        else:
            # Create new trace for this artifact
            trace = client.trace(
                name=f"artifact-{artifact_type}",
                metadata={
                    "artifact_id": artifact_id,
                    "artifact_type": artifact_type,
                    "activity_type": activity_type,
                    "category": category,
                    "tab": tab,
                    "value_usd": value_usd,
                    "content_length": len(artifact.get("content", "")),
                    "project_id": project_name,
                    "roi_artifact": True,
                },
                tags=[
                    f"artifact:{artifact_type}",
                    f"tab:{tab}",
                    f"category:{category}",
                    f"project:{project_name}",
                    "roi",
                    "artifact",
                ],
                output={
                    "artifact_id": artifact_id,
                    "type": artifact_type,
                    "value_usd": value_usd,
                    "preview": artifact.get("content", "")[:200],
                },
            )

            if trace and trace.id:
                # Value score by category
                client.score(
                    trace_id=trace.id,
                    name=f"value_{category}_usd",
                    value=float(value_usd),
                    comment=f"Artifact: {artifact.get('description', '')[:100]}",
                )

                # Total value score
                client.score(
                    trace_id=trace.id,
                    name="total_value_usd",
                    value=float(value_usd),
                    comment=f"Artifact type: {artifact_type}",
                )

                # Artifact count
                client.score(
                    trace_id=trace.id,
                    name=f"artifact_{artifact_type}_count",
                    value=1.0,
                    comment=f"Created artifact: {artifact_id}",
                )

                flush_langfuse()
                return f"ROI trace created: {trace.id[:8]}..."

        return None

    except ImportError:
        logger.debug("Langfuse integration not available for ROI")
        return None
    except Exception as e:
        logger.warning(f"Failed to publish artifact ROI: {e}")
        return None


def create_artifact_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create artifact creation tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of artifact tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []

    # Import artifact storage functions
    try:
        from analytics.artifact_storage import (
            save_artifact_safe,
            create_langfuse_reference,
            _get_artifacts_dir,
        )
        STORAGE_AVAILABLE = True
    except ImportError:
        STORAGE_AVAILABLE = False
        logger.warning("Artifact storage not available")

    # -------------------------------------------------------------------------
    # Tool: create_artifact
    # -------------------------------------------------------------------------
    @tool(
        "create_artifact",
        """Create a concrete artifact with structured content.

Call this tool to create artifacts like diagrams, code examples, security findings,
recommendations, etc. The artifact will be saved locally with full content and
a reference will be sent to Langfuse for analytics.

IMPORTANT: Use this instead of just describing findings in text. Artifacts are
tracked for ROI and can be viewed in the dashboard.

Artifact types and their tabs:
- DEV: code_example, refactoring, bug_fix, test_case
- TECHLEAD: diagram, architecture_insight, api_design, documentation
- OPS: security_finding, performance_insight
- BUSINESS: recommendation, cost_analysis, priority_assessment

Example usage:
- Found security issue: type="security_finding", content="SQL injection in login..."
- Created diagram: type="diagram", format="mermaid", content="graph TD..."
- Code suggestion: type="code_example", format="python", content="def validate..."
- Recommendation: type="recommendation", content="Migrate to TypeScript for..."
""",
        {
            "artifact_type": str,
            "content": str,
            "description": str,
            "format": str,
            "complexity": str,
            "keywords": list,
        },
    )
    async def create_artifact(args: dict[str, Any]) -> dict[str, Any]:
        """Create a structured artifact."""
        artifact_type = args.get("artifact_type", "")
        content = args.get("content", "")
        description = args.get("description", "")
        format_type = args.get("format", "markdown")
        complexity = args.get("complexity", "medium")
        keywords = args.get("keywords", [])

        # Validate artifact type
        if artifact_type not in ARTIFACT_TYPES:
            available = sorted(ARTIFACT_TYPES.keys())
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Unknown artifact type '{artifact_type}'.\n\n"
                        f"Available types:\n"
                        + "\n".join(f"  - {t}: {ARTIFACT_TYPES[t]['description']}" for t in available),
                    }
                ]
            }

        # Validate content
        if not content or len(content.strip()) < 10:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: Content is too short. Provide meaningful content (at least 10 chars).",
                    }
                ]
            }

        # Calculate value
        value_usd = calculate_artifact_value(artifact_type, content, complexity)

        # Get tab from type definition
        tab = ARTIFACT_TYPES[artifact_type]["tab"]

        # Build artifact dict
        artifact = {
            "type": artifact_type,
            "format": format_type,
            "content": content,
            "value_usd": value_usd,
            "description": description or f"{artifact_type.replace('_', ' ').title()}",
            "tab": tab,
            "keywords": keywords,
            "complexity": complexity,
        }

        result_info = {
            "artifact_type": artifact_type,
            "tab": tab,
            "value_usd": value_usd,
            "content_length": len(content),
            "saved_locally": False,
            "langfuse_ref": False,
        }

        # Save artifact if storage is available
        if STORAGE_AVAILABLE:
            try:
                # Get trace_id from thread-local storage (thread-safe for concurrent execution)
                # Falls back to environment variable for backwards compatibility
                import os
                try:
                    from analytics.langfuse_integration import get_current_trace_id
                    trace_id = get_current_trace_id() or os.environ.get("LANGFUSE_TRACE_ID", None)
                except ImportError:
                    trace_id = os.environ.get("LANGFUSE_TRACE_ID", None)

                artifact_id = save_artifact_safe(
                    artifact=artifact,
                    project_dir=project_dir,
                    spec_id=spec_dir.name if spec_dir else None,
                    trace_id=trace_id,
                    agent_type="insights",
                    session_num=None,
                )

                if artifact_id:
                    result_info["saved_locally"] = True
                    result_info["artifact_id"] = artifact_id

                    # Create Langfuse reference
                    storage_path = str(
                        _get_artifacts_dir(project_dir)
                        / datetime.now().strftime("%Y-%m-%d")
                        / f"{artifact_id}.json"
                    )
                    ref = create_langfuse_reference(artifact, artifact_id, storage_path)
                    result_info["langfuse_ref"] = True
                    result_info["storage_path"] = storage_path

                    # Publish ROI to Langfuse
                    roi_result = await _publish_artifact_roi(
                        artifact=artifact,
                        artifact_id=artifact_id,
                        project_dir=project_dir,
                        spec_dir=spec_dir,
                    )
                    if roi_result:
                        result_info["roi_published"] = True
                        result_info["roi_status"] = roi_result

            except Exception as e:
                logger.error(f"Error saving artifact: {e}")
                result_info["save_error"] = str(e)

        # Build response
        status_icon = "✅" if result_info["saved_locally"] else "⚠️"
        roi_icon = "📊" if result_info.get("roi_published") else ""
        response_text = f"""
{status_icon} Artifact created successfully! {roi_icon}

Type: {artifact_type}
Tab: {TAB_NAMES.get(tab, tab)}
Value: ${value_usd}
Content: {len(content)} chars
Format: {format_type}
"""

        if result_info.get("artifact_id"):
            response_text += f"ID: {result_info['artifact_id']}\n"

        if result_info.get("roi_published"):
            response_text += f"ROI: {result_info.get('roi_status', 'Published')}\n"

        if result_info.get("save_error"):
            response_text += f"\n⚠️ Storage warning: {result_info['save_error']}\n"

        return {"content": [{"type": "text", "text": response_text.strip()}]}

    tools.append(create_artifact)

    # -------------------------------------------------------------------------
    # Tool: list_artifact_types
    # -------------------------------------------------------------------------
    @tool(
        "list_artifact_types",
        "List all available artifact types with their values and tabs.",
        {"tab": str},
    )
    async def list_artifact_types(args: dict[str, Any]) -> dict[str, Any]:
        """List available artifact types."""
        tab_filter = args.get("tab", "").lower()

        lines = ["=== Available Artifact Types ===", ""]

        current_tab = None
        for atype, info in sorted(
            ARTIFACT_TYPES.items(), key=lambda x: (x[1]["tab"], x[0])
        ):
            tab = info["tab"]

            # Filter by tab if specified
            if tab_filter and tab != tab_filter:
                continue

            if tab != current_tab:
                if current_tab is not None:
                    lines.append("")
                lines.append(f"## {TAB_NAMES.get(tab, tab).upper()}")
                current_tab = tab

            lines.append(f"  {atype}: ${info['base_value']} base")
            lines.append(f"    {info['description']}")
            lines.append(f"    Formats: {', '.join(info['formats'])}")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    tools.append(list_artifact_types)

    # -------------------------------------------------------------------------
    # Tool: create_diagram
    # -------------------------------------------------------------------------
    def validate_mermaid_syntax(content: str) -> tuple[bool, str]:
        """
        Validate Mermaid diagram syntax.

        Returns:
            Tuple of (is_valid, error_message)
        """
        import re

        # Basic syntax checks for common Mermaid errors
        errors = []

        # Check for common mermaid diagram types
        valid_starts = [
            "graph", "flowchart", "sequenceDiagram", "classDiagram",
            "stateDiagram", "erDiagram", "gantt", "pie", "journey",
            "gitgraph", "mindmap", "timeline", "quadrantChart",
            "xychart", "block-beta", "sankey", "packet"
        ]

        first_line = content.strip().split('\n')[0].strip()
        has_valid_start = any(first_line.startswith(vs) for vs in valid_starts)

        if not has_valid_start:
            errors.append(f"Invalid diagram type. First line should start with one of: {', '.join(valid_starts[:5])}...")

        # Check for common syntax errors
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for 'style' statements - must have space between 'style' and node ID
            if re.match(r'^\s*style[A-Za-z]', line):
                errors.append(f"Line {i}: Missing space after 'style'. Use 'style {line.strip()[5:6]}' instead of 'style{line.strip()[5:6]}'")

            # Check for unclosed brackets in node definitions
            if '[' in line and ']' not in line and not any(c in line for c in ['-->',  '-->', '-.->',  '==>',  '---']):
                # May be multiline, skip
                pass

            # Check for mismatched quotes
            single_quotes = line.count("'")
            double_quotes = line.count('"')
            if single_quotes % 2 != 0:
                errors.append(f"Line {i}: Unmatched single quote")
            if double_quotes % 2 != 0:
                errors.append(f"Line {i}: Unmatched double quote")

        if errors:
            return False, "\n".join(errors[:5])  # Return first 5 errors

        return True, ""

    @tool(
        "create_diagram",
        """Create a diagram artifact (convenience wrapper for create_artifact).

Use this for architecture diagrams, flow charts, sequence diagrams, etc.
Automatically sets type="diagram" and appropriate metadata.

IMPORTANT: Mermaid syntax is validated before saving. If there are syntax errors,
you will receive an error message and must fix the syntax before retrying.

Common Mermaid syntax rules:
- 'style' must have a space before node ID: "style A fill:#fff" NOT "styleA fill:#fff"
- Quotes must be balanced
- Each diagram type has specific syntax requirements

Example:
  format: "mermaid"
  content: "graph TD\\n  A[Start] --> B[Process]\\n  B --> C[End]"
  description: "User authentication flow"
""",
        {
            "format": str,
            "content": str,
            "description": str,
        },
    )
    async def create_diagram(args: dict[str, Any]) -> dict[str, Any]:
        """Create a diagram artifact with validation."""
        format_type = args.get("format", "mermaid")
        content = args.get("content", "")

        # Validate Mermaid syntax before saving
        if format_type == "mermaid":
            is_valid, error_msg = validate_mermaid_syntax(content)
            if not is_valid:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"❌ Mermaid syntax error detected:\n\n{error_msg}\n\n"
                                    f"Please fix the syntax and try again. "
                                    f"Common issues:\n"
                                    f"- 'style X' must have space between 'style' and node ID\n"
                                    f"- Quotes must be balanced\n"
                                    f"- Check arrow syntax (-->, -.->)\n",
                        }
                    ]
                }

        return await create_artifact({
            "artifact_type": "diagram",
            "format": format_type,
            "content": content,
            "description": args.get("description", "Diagram"),
            "complexity": "high",  # Diagrams are high-value
            "keywords": ["diagram", "visual", "architecture"],
        })

    tools.append(create_diagram)

    # -------------------------------------------------------------------------
    # Tool: report_security_finding
    # -------------------------------------------------------------------------
    @tool(
        "report_security_finding",
        """Report a security finding (convenience wrapper for create_artifact).

Use this for security vulnerabilities, concerns, or recommendations.
Automatically sets type="security_finding" with high value.

Example:
  content: "SQL injection vulnerability in user login. The query uses string concatenation..."
  severity: "high"
  description: "SQL Injection in login endpoint"
""",
        {
            "content": str,
            "severity": str,
            "description": str,
        },
    )
    async def report_security_finding(args: dict[str, Any]) -> dict[str, Any]:
        """Report a security finding."""
        severity = args.get("severity", "medium")

        # Map severity to complexity for value calculation
        severity_to_complexity = {
            "low": "low",
            "medium": "medium",
            "high": "high",
            "critical": "high",
        }

        return await create_artifact({
            "artifact_type": "security_finding",
            "format": "markdown",
            "content": args.get("content", ""),
            "description": args.get("description", f"Security finding ({severity})"),
            "complexity": severity_to_complexity.get(severity, "medium"),
            "keywords": ["security", severity, "vulnerability"],
        })

    tools.append(report_security_finding)

    # -------------------------------------------------------------------------
    # Tool: suggest_recommendation
    # -------------------------------------------------------------------------
    @tool(
        "suggest_recommendation",
        """Create a recommendation artifact (convenience wrapper for create_artifact).

Use this for strategic recommendations, best practices, or suggestions.
Automatically sets type="recommendation".

Example:
  content: "Migrate the authentication system to OAuth 2.0 for better security and user experience..."
  priority: "high"
  description: "OAuth 2.0 migration recommendation"
""",
        {
            "content": str,
            "priority": str,
            "description": str,
        },
    )
    async def suggest_recommendation(args: dict[str, Any]) -> dict[str, Any]:
        """Create a recommendation artifact."""
        priority = args.get("priority", "medium")

        # Map priority to complexity
        priority_to_complexity = {
            "low": "low",
            "medium": "medium",
            "high": "high",
        }

        return await create_artifact({
            "artifact_type": "recommendation",
            "format": "markdown",
            "content": args.get("content", ""),
            "description": args.get("description", f"Recommendation ({priority} priority)"),
            "complexity": priority_to_complexity.get(priority, "medium"),
            "keywords": ["recommendation", priority, "suggestion"],
        })

    tools.append(suggest_recommendation)

    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================

    # Import additional storage functions for CRUD
    try:
        from analytics.artifact_storage import (
            load_artifact,
            list_artifacts,
            update_artifact as storage_update_artifact,
            delete_artifact as storage_delete_artifact,
        )
        CRUD_AVAILABLE = True
    except ImportError:
        CRUD_AVAILABLE = False
        load_artifact = None
        list_artifacts = None
        storage_update_artifact = None
        storage_delete_artifact = None

    # -------------------------------------------------------------------------
    # Tool: get_artifact
    # -------------------------------------------------------------------------
    @tool(
        "get_artifact",
        """Get a specific artifact by ID.

Use this to retrieve the full content of an artifact you created earlier.

Example:
  artifact_id: "art_abc123def456"
""",
        {
            "artifact_id": str,
        },
    )
    async def get_artifact(args: dict[str, Any]) -> dict[str, Any]:
        """Get an artifact by ID."""
        artifact_id = args.get("artifact_id", "")

        if not CRUD_AVAILABLE or not load_artifact:
            return {
                "content": [
                    {"type": "text", "text": "Error: Artifact storage not available."}
                ]
            }

        if not artifact_id:
            return {
                "content": [
                    {"type": "text", "text": "Error: artifact_id is required."}
                ]
            }

        artifact = load_artifact(artifact_id, project_dir)

        if not artifact:
            return {
                "content": [
                    {"type": "text", "text": f"Error: Artifact '{artifact_id}' not found."}
                ]
            }

        # Format artifact for display
        content = artifact.get("content", "")
        response_text = f"""
=== Artifact: {artifact_id} ===

Type: {artifact.get('type', 'unknown')}
Tab: {TAB_NAMES.get(artifact.get('tab', ''), artifact.get('tab', ''))}
Value: ${artifact.get('value_usd', 0)}
Format: {artifact.get('format', 'text')}
Created: {artifact.get('created_at', 'unknown')}

--- Content ---
{content}
"""
        return {"content": [{"type": "text", "text": response_text.strip()}]}

    tools.append(get_artifact)

    # -------------------------------------------------------------------------
    # Tool: list_session_artifacts
    # -------------------------------------------------------------------------
    @tool(
        "list_session_artifacts",
        """List artifacts created in this session or by filters.

Use this to see what artifacts have been created.

Examples:
  - List all: no arguments
  - Filter by type: artifact_type="security_finding"
  - Filter by tab: tab="dev"
  - Limit results: limit=10
""",
        {
            "artifact_type": str,
            "tab": str,
            "limit": int,
        },
    )
    async def list_session_artifacts(args: dict[str, Any]) -> dict[str, Any]:
        """List artifacts with optional filters."""
        artifact_type = args.get("artifact_type", "")
        tab = args.get("tab", "")
        limit = args.get("limit", 20)

        if not CRUD_AVAILABLE or not list_artifacts:
            return {
                "content": [
                    {"type": "text", "text": "Error: Artifact storage not available."}
                ]
            }

        # Build type filter
        type_filter = [artifact_type] if artifact_type else None

        artifacts = list_artifacts(
            project_dir,
            artifact_types=type_filter,
            limit=limit,
        )

        # Filter by tab if specified
        if tab:
            artifacts = [a for a in artifacts if a.get("tab") == tab]

        if not artifacts:
            return {
                "content": [
                    {"type": "text", "text": "No artifacts found matching the filters."}
                ]
            }

        # Format artifact list
        lines = [f"=== Found {len(artifacts)} Artifact(s) ===", ""]

        for art in artifacts[:limit]:
            content_preview = art.get("content", "")[:50]
            if len(art.get("content", "")) > 50:
                content_preview += "..."

            lines.append(f"ID: {art.get('id', 'unknown')}")
            lines.append(f"  Type: {art.get('type', 'unknown')} | Tab: {TAB_NAMES.get(art.get('tab', ''), art.get('tab', ''))}")
            lines.append(f"  Value: ${art.get('value_usd', 0)} | {art.get('created_at', '')[:10]}")
            lines.append(f"  Preview: {content_preview}")
            lines.append("")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    tools.append(list_session_artifacts)

    # -------------------------------------------------------------------------
    # Tool: update_artifact
    # -------------------------------------------------------------------------
    @tool(
        "update_artifact",
        """Update an existing artifact.

Use this to modify an artifact you created earlier - fix typos, add details,
change the value, etc.

Updatable fields: content, description, value_usd, format, keywords, complexity

Example:
  artifact_id: "art_abc123def456"
  content: "Updated content with more details..."
  description: "Improved description"
""",
        {
            "artifact_id": str,
            "content": str,
            "description": str,
            "value_usd": int,
            "format": str,
            "complexity": str,
        },
    )
    async def update_artifact_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Update an existing artifact."""
        artifact_id = args.get("artifact_id", "")

        if not CRUD_AVAILABLE or not storage_update_artifact:
            return {
                "content": [
                    {"type": "text", "text": "Error: Artifact storage not available."}
                ]
            }

        if not artifact_id:
            return {
                "content": [
                    {"type": "text", "text": "Error: artifact_id is required."}
                ]
            }

        # Build updates dict from provided args
        updates = {}
        if "content" in args and args["content"]:
            updates["content"] = args["content"]
        if "description" in args and args["description"]:
            updates["description"] = args["description"]
        if "value_usd" in args and args["value_usd"]:
            updates["value_usd"] = args["value_usd"]
        if "format" in args and args["format"]:
            updates["format"] = args["format"]
        if "complexity" in args and args["complexity"]:
            updates["complexity"] = args["complexity"]

        if not updates:
            return {
                "content": [
                    {"type": "text", "text": "Error: No update fields provided. Provide at least one of: content, description, value_usd, format, complexity"}
                ]
            }

        updated_artifact = storage_update_artifact(artifact_id, project_dir, updates)

        if not updated_artifact:
            return {
                "content": [
                    {"type": "text", "text": f"Error: Failed to update artifact '{artifact_id}'. It may not exist."}
                ]
            }

        response_text = f"""
✅ Artifact updated successfully!

ID: {artifact_id}
Type: {updated_artifact.get('type', 'unknown')}
Value: ${updated_artifact.get('value_usd', 0)}
Updated: {updated_artifact.get('updated_at', 'now')}

Updated fields: {', '.join(updates.keys())}
"""
        return {"content": [{"type": "text", "text": response_text.strip()}]}

    tools.append(update_artifact_tool)

    # -------------------------------------------------------------------------
    # Tool: delete_artifact
    # -------------------------------------------------------------------------
    @tool(
        "delete_artifact",
        """Delete an artifact.

Use this to remove an artifact that was created by mistake or is no longer needed.
This action cannot be undone.

Example:
  artifact_id: "art_abc123def456"
  confirm: true
""",
        {
            "artifact_id": str,
            "confirm": bool,
        },
    )
    async def delete_artifact_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Delete an artifact."""
        artifact_id = args.get("artifact_id", "")
        confirm = args.get("confirm", False)

        if not CRUD_AVAILABLE or not storage_delete_artifact:
            return {
                "content": [
                    {"type": "text", "text": "Error: Artifact storage not available."}
                ]
            }

        if not artifact_id:
            return {
                "content": [
                    {"type": "text", "text": "Error: artifact_id is required."}
                ]
            }

        if not confirm:
            return {
                "content": [
                    {"type": "text", "text": f"⚠️ To delete artifact '{artifact_id}', call this tool again with confirm=true.\nThis action cannot be undone."}
                ]
            }

        success = storage_delete_artifact(artifact_id, project_dir)

        if not success:
            return {
                "content": [
                    {"type": "text", "text": f"Error: Failed to delete artifact '{artifact_id}'. It may not exist."}
                ]
            }

        return {
            "content": [
                {"type": "text", "text": f"🗑️ Artifact '{artifact_id}' deleted successfully."}
            ]
        }

    tools.append(delete_artifact_tool)

    return tools
