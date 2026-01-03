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
            client.create_score(
                trace_id=trace_id,
                name=f"artifact_{artifact_type}_value",
                value=float(value_usd),
                comment=f"Artifact created: {artifact.get('description', '')[:100]}",
            )

            # Also add to total value
            client.create_score(
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
                client.create_score(
                    trace_id=trace.id,
                    name=f"value_{category}_usd",
                    value=float(value_usd),
                    comment=f"Artifact: {artifact.get('description', '')[:100]}",
                )

                # Total value score
                client.create_score(
                    trace_id=trace.id,
                    name="total_value_usd",
                    value=float(value_usd),
                    comment=f"Artifact type: {artifact_type}",
                )

                # Artifact count
                client.create_score(
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

        # Return with structured metadata for extensions hook to detect already-saved artifacts
        # The hook checks artifact_id to avoid duplicate saves
        return {
            "content": [{"type": "text", "text": response_text.strip()}],
            # Metadata for extensions layer (prevents duplicate artifact saves)
            "artifact_id": result_info.get("artifact_id"),
            "artifact_type": artifact_type,
            "value_usd": value_usd,
            "format": format_type,
            "description": description,
        }

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

    # -------------------------------------------------------------------------
    # Tool: aggregate_artifacts_by_agent
    # -------------------------------------------------------------------------

    # Import the aggregation function
    try:
        from analytics.artifact_storage import get_artifacts_by_agent
        AGGREGATION_AVAILABLE = True
    except ImportError:
        AGGREGATION_AVAILABLE = False
        get_artifacts_by_agent = None

    @tool(
        "aggregate_artifacts_by_agent",
        """Get artifacts aggregated by agent type.

Groups all artifacts by their creating agent (planner, coder, qa_reviewer, qa_fixer, etc.)
and returns count, total value in USD, and artifact types for each agent.

Use this to understand:
- Which agents are generating the most valuable artifacts
- What types of artifacts each agent produces
- Total value contribution per agent

Optional date filtering allows analyzing specific time periods.

Example output:
{
  "planner": {"count": 5, "total_value_usd": 250, "types": ["diagram", "architecture_insight"]},
  "coder": {"count": 12, "total_value_usd": 480, "types": ["code_example", "bug_fix"]},
  "qa_reviewer": {"count": 8, "total_value_usd": 320, "types": ["security_finding", "recommendation"]}
}
""",
        {
            "date_from": str,
            "date_to": str,
        },
    )
    async def aggregate_artifacts_by_agent_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Aggregate artifacts by agent type."""
        date_from = args.get("date_from", "")
        date_to = args.get("date_to", "")

        if not AGGREGATION_AVAILABLE or not get_artifacts_by_agent:
            return {
                "content": [
                    {"type": "text", "text": "Error: Artifact aggregation not available."}
                ]
            }

        try:
            # Get aggregation results
            by_agent = get_artifacts_by_agent(
                project_dir=project_dir,
                date_from=date_from if date_from else None,
                date_to=date_to if date_to else None,
            )

            if not by_agent:
                return {
                    "content": [
                        {"type": "text", "text": "No artifacts found for aggregation."}
                    ]
                }

            # Calculate totals
            total_count = sum(data["count"] for data in by_agent.values())
            total_value = sum(data["total_value_usd"] for data in by_agent.values())

            # Format response
            lines = ["=== Artifacts by Agent Type ===", ""]

            if date_from or date_to:
                date_range = f"{date_from or 'start'} to {date_to or 'now'}"
                lines.append(f"Date Range: {date_range}")
                lines.append("")

            # Sort by total value descending
            sorted_agents = sorted(
                by_agent.items(),
                key=lambda x: x[1]["total_value_usd"],
                reverse=True
            )

            for agent_type, data in sorted_agents:
                lines.append(f"## {agent_type.upper()}")
                lines.append(f"  Count: {data['count']} artifacts")
                lines.append(f"  Value: ${data['total_value_usd']}")
                lines.append(f"  Types: {', '.join(data['types'])}")
                lines.append("")

            lines.append("--- Summary ---")
            lines.append(f"Total Artifacts: {total_count}")
            lines.append(f"Total Value: ${total_value}")
            lines.append(f"Agents: {len(by_agent)}")

            # Return both text and structured content
            return {
                "content": [{"type": "text", "text": "\n".join(lines)}],
                "structuredContent": {
                    "by_agent": by_agent,
                    "summary": {
                        "total_count": total_count,
                        "total_value_usd": total_value,
                        "agent_count": len(by_agent),
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error aggregating artifacts by agent: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error aggregating artifacts: {str(e)}"}
                ]
            }

    tools.append(aggregate_artifacts_by_agent_tool)

    # -------------------------------------------------------------------------
    # Tool: get_artifact_statistics
    # -------------------------------------------------------------------------

    # Import the comprehensive stats function
    try:
        from analytics.artifact_storage import get_comprehensive_artifact_stats
        STATS_AVAILABLE = True
    except ImportError:
        STATS_AVAILABLE = False
        get_comprehensive_artifact_stats = None

    @tool(
        "get_artifact_statistics",
        """Get comprehensive artifact statistics for the project.

Returns detailed statistics about all stored artifacts including:
- Total count and total value in USD
- Breakdown by artifact type (diagram, code_example, security_finding, etc.)
- Breakdown by dashboard tab (dev, techlead, ops, business)
- Breakdown by time period (last 7 days, last 30 days, all time)
- Top 5 most valuable artifacts
- Value distribution by type and tab

Use this to:
- Understand the ROI generated by Auto-Claude
- See which types of artifacts are being created most
- Identify the most valuable contributions
- Track artifact creation over time

Example output:
{
  "total_count": 45,
  "total_value_usd": 2500,
  "by_type": {"diagram": 10, "code_example": 15, "security_finding": 5, ...},
  "by_tab": {"dev": 20, "techlead": 15, "ops": 5, "business": 5},
  "by_period": {"last_7_days": 12, "last_30_days": 35, "all_time": 45},
  "top_valuable": [
    {"id": "art_xxx", "type": "security_finding", "value_usd": 200, "date": "2024-01-15"},
    ...
  ]
}
""",
        {},
    )
    async def get_artifact_statistics_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Get comprehensive artifact statistics."""
        if not STATS_AVAILABLE or not get_comprehensive_artifact_stats:
            return {
                "content": [
                    {"type": "text", "text": "Error: Artifact statistics not available."}
                ]
            }

        try:
            stats = get_comprehensive_artifact_stats(project_dir)

            # Format response text
            lines = ["=== Artifact Statistics ===", ""]

            # Overview
            lines.append("## Overview")
            lines.append(f"  Total Artifacts: {stats['total_count']}")
            lines.append(f"  Total Value: ${stats['total_value_usd']:.2f}")
            lines.append(f"  Last Updated: {stats.get('last_updated', 'N/A')}")
            lines.append("")

            # By Period
            lines.append("## By Time Period")
            by_period = stats.get("by_period", {})
            lines.append(f"  Last 7 Days: {by_period.get('last_7_days', 0)} artifacts")
            lines.append(f"  Last 30 Days: {by_period.get('last_30_days', 0)} artifacts")
            lines.append(f"  All Time: {by_period.get('all_time', 0)} artifacts")
            lines.append("")

            # By Tab
            lines.append("## By Dashboard Tab")
            by_tab = stats.get("by_tab", {})
            value_by_tab = stats.get("value_by_tab", {})
            for tab in ["dev", "techlead", "ops", "business"]:
                count = by_tab.get(tab, 0)
                value = value_by_tab.get(tab, 0)
                tab_name = TAB_NAMES.get(tab, tab)
                lines.append(f"  {tab_name}: {count} artifacts (${value:.2f})")
            lines.append("")

            # By Type (top 10)
            lines.append("## By Artifact Type (Top 10)")
            by_type = stats.get("by_type", {})
            value_by_type = stats.get("value_by_type", {})
            sorted_types = sorted(
                by_type.items(),
                key=lambda x: value_by_type.get(x[0], 0),
                reverse=True
            )[:10]
            for art_type, count in sorted_types:
                value = value_by_type.get(art_type, 0)
                lines.append(f"  {art_type}: {count} (${value:.2f})")
            lines.append("")

            # Top Valuable
            lines.append("## Top 5 Most Valuable")
            top_valuable = stats.get("top_valuable", [])
            for i, art in enumerate(top_valuable, 1):
                lines.append(f"  {i}. {art['type']} - ${art['value_usd']:.2f}")
                lines.append(f"     ID: {art['id']}, Date: {art['date']}")
            if not top_valuable:
                lines.append("  No artifacts with value found.")

            return {
                "content": [{"type": "text", "text": "\n".join(lines)}],
                "structuredContent": stats
            }

        except Exception as e:
            logger.error(f"Error getting artifact statistics: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error getting statistics: {str(e)}"}
                ]
            }

    tools.append(get_artifact_statistics_tool)

    # -------------------------------------------------------------------------
    # Tool: search_artifacts
    # -------------------------------------------------------------------------

    # Import the search function
    try:
        from analytics.artifact_storage import search_artifacts as storage_search_artifacts
        SEARCH_AVAILABLE = True
    except ImportError:
        SEARCH_AVAILABLE = False
        storage_search_artifacts = None

    @tool(
        "search_artifacts",
        """Search artifacts by content, description, and type.

Performs case-insensitive full-text search across all stored artifacts.
Returns matching artifacts sorted by relevance with previews and match highlights.

Search is performed on:
- artifact content (code, diagrams, findings, recommendations, etc.)
- artifact description
- artifact type name

Results include:
- Preview of the first 200 characters of content
- Highlighted snippet showing where the query matched
- Location of matches (content, description, or type)
- Relevance score (higher = more relevant)

Optional filters:
- artifact_types: Filter to specific types (e.g., ["security_finding", "diagram"])
- spec_id: Filter to artifacts from a specific spec
- limit: Maximum results to return (default: 50)

Examples:
  query: "SQL injection"       -> Find security findings about SQL injection
  query: "authentication"      -> Find all artifacts mentioning authentication
  query: "diagram"             -> Find all diagram artifacts (matches type)
  query: "TODO"                -> Find artifacts with TODO comments

Example response:
[
  {
    "id": "art_abc123",
    "type": "security_finding",
    "description": "SQL Injection vulnerability in login",
    "preview": "Found SQL injection vulnerability in...",
    "match_highlight": "...user input allows **SQL injection** attacks...",
    "match_locations": ["content", "description"],
    "relevance_score": 175
  }
]
""",
        {
            "query": str,
            "artifact_types": list,
            "spec_id": str,
            "limit": int,
        },
    )
    async def search_artifacts_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Search artifacts by content, description, and type."""
        query = args.get("query", "")
        artifact_types_filter = args.get("artifact_types", None)
        spec_id_filter = args.get("spec_id", "")
        limit = args.get("limit", 50)

        if not SEARCH_AVAILABLE or not storage_search_artifacts:
            return {
                "content": [
                    {"type": "text", "text": "Error: Artifact search not available."}
                ]
            }

        if not query or len(query.strip()) < 1:
            return {
                "content": [
                    {"type": "text", "text": "Error: Search query is required."}
                ]
            }

        try:
            # Perform search
            results = storage_search_artifacts(
                project_dir=project_dir,
                query=query,
                artifact_types=artifact_types_filter if artifact_types_filter else None,
                spec_id=spec_id_filter if spec_id_filter else None,
                limit=limit if limit else 50,
            )

            if not results:
                return {
                    "content": [
                        {"type": "text", "text": f"No artifacts found matching '{query}'."}
                    ]
                }

            # Format response text
            lines = [f"=== Search Results for '{query}' ===", ""]
            lines.append(f"Found {len(results)} matching artifact(s)")
            lines.append("")

            for i, result in enumerate(results, 1):
                lines.append(f"## {i}. {result['type']} (${result['value_usd']})")
                lines.append(f"   ID: {result['id']}")
                if result.get("description"):
                    lines.append(f"   Description: {result['description'][:100]}{'...' if len(result.get('description', '')) > 100 else ''}")
                lines.append(f"   Tab: {TAB_NAMES.get(result.get('tab', ''), result.get('tab', 'N/A'))}")
                lines.append(f"   Created: {result.get('created_at', 'N/A')[:10]}")
                lines.append(f"   Matched in: {', '.join(result.get('match_locations', []))}")
                if result.get("match_highlight"):
                    lines.append(f"   Match: {result['match_highlight']}")
                lines.append(f"   Relevance: {result.get('relevance_score', 0)}")
                lines.append("")

            return {
                "content": [{"type": "text", "text": "\n".join(lines)}],
                "structuredContent": {
                    "query": query,
                    "total_results": len(results),
                    "results": results,
                }
            }

        except Exception as e:
            logger.error(f"Error searching artifacts: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error searching artifacts: {str(e)}"}
                ]
            }

    tools.append(search_artifacts_tool)

    # -------------------------------------------------------------------------
    # Tool: export_artifacts
    # -------------------------------------------------------------------------

    # Import the export functions
    try:
        from analytics.artifact_storage import (
            export_artifacts_json as storage_export_json,
            export_artifacts_markdown as storage_export_markdown,
        )
        EXPORT_AVAILABLE = True
    except ImportError:
        EXPORT_AVAILABLE = False
        storage_export_json = None
        storage_export_markdown = None

    @tool(
        "export_artifacts",
        """Export artifacts to JSON or Markdown format.

Exports artifacts with optional filters to a file or returns the content directly.
Useful for generating reports, sharing artifacts, or archiving.

Formats:
- json: Structured JSON with full artifact data, summaries, and breakdowns
- markdown: Human-readable Markdown with emojis, tables, and organized sections

Filters:
- artifact_types: List of types to include (e.g., ["security_finding", "diagram"])
- date_from: Start date filter (YYYY-MM-DD)
- date_to: End date filter (YYYY-MM-DD)
- agent_type: Filter by creating agent (planner, coder, qa_reviewer, etc.)
- spec_id: Filter to a specific spec

Markdown options:
- include_content: Whether to include full artifact content (default: true)
- max_content_length: Max chars per artifact content, 0=unlimited (default: 2000)

If output_path is provided, saves to file and returns path.
If output_path is omitted, returns the content directly.

Examples:
  Export all to JSON file:
    format: "json"
    output_path: "/path/to/export.json"

  Export security findings to Markdown:
    format: "markdown"
    artifact_types: ["security_finding"]
    output_path: "/path/to/security-report.md"

  Get last 7 days as Markdown content:
    format: "markdown"
    date_from: "2026-01-01"
    (no output_path - returns content directly)
""",
        {
            "format": str,
            "output_path": str,
            "artifact_types": list,
            "date_from": str,
            "date_to": str,
            "agent_type": str,
            "spec_id": str,
            "include_content": bool,
            "max_content_length": int,
        },
    )
    async def export_artifacts_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Export artifacts to JSON or Markdown format."""
        export_format = args.get("format", "json").lower()
        output_path = args.get("output_path", "")
        artifact_types_filter = args.get("artifact_types", None)
        date_from = args.get("date_from", "")
        date_to = args.get("date_to", "")
        agent_type_filter = args.get("agent_type", "")
        spec_id_filter = args.get("spec_id", "")
        include_content = args.get("include_content", True)
        max_content_length = args.get("max_content_length", 2000)

        if not EXPORT_AVAILABLE:
            return {
                "content": [
                    {"type": "text", "text": "Error: Artifact export not available."}
                ]
            }

        # Validate format
        if export_format not in ["json", "markdown", "md"]:
            return {
                "content": [
                    {"type": "text", "text": f"Error: Invalid format '{export_format}'. Use 'json' or 'markdown'."}
                ]
            }

        try:
            from pathlib import Path as PathLib

            # Prepare output path
            out_path = PathLib(output_path) if output_path else None

            # Call appropriate export function
            if export_format == "json":
                result = storage_export_json(
                    project_dir=project_dir,
                    output_path=out_path,
                    artifact_types=artifact_types_filter if artifact_types_filter else None,
                    date_from=date_from if date_from else None,
                    date_to=date_to if date_to else None,
                    agent_type=agent_type_filter if agent_type_filter else None,
                    spec_id=spec_id_filter if spec_id_filter else None,
                )
            else:  # markdown or md
                result = storage_export_markdown(
                    project_dir=project_dir,
                    output_path=out_path,
                    artifact_types=artifact_types_filter if artifact_types_filter else None,
                    date_from=date_from if date_from else None,
                    date_to=date_to if date_to else None,
                    agent_type=agent_type_filter if agent_type_filter else None,
                    spec_id=spec_id_filter if spec_id_filter else None,
                    include_content=include_content,
                    max_content_length=max_content_length if max_content_length else 2000,
                )

            # Build response
            if "saved_to" in result:
                response_text = f"""
Export completed successfully!

Format: {export_format.upper()}
Saved to: {result['saved_to']}
Artifacts: {result['artifact_count']}
Total Value: ${result['total_value']:,.2f}
"""
                return {"content": [{"type": "text", "text": response_text.strip()}]}
            else:
                # Return content directly
                content = result.get("content", "")
                header = f"=== Export ({result['artifact_count']} artifacts, ${result['total_value']:,.2f}) ===\n\n"
                return {"content": [{"type": "text", "text": header + content}]}

        except Exception as e:
            logger.error(f"Error exporting artifacts: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error exporting artifacts: {str(e)}"}
                ]
            }

    tools.append(export_artifacts_tool)

    # =========================================================================
    # TAG MANAGEMENT TOOLS
    # =========================================================================

    # Import tag management functions
    try:
        from analytics.artifact_storage import (
            add_tag_to_artifact as storage_add_tag,
            remove_tag_from_artifact as storage_remove_tag,
            get_artifacts_by_tag as storage_get_by_tag,
            get_all_tags as storage_get_all_tags,
        )
        TAGS_AVAILABLE = True
    except ImportError:
        TAGS_AVAILABLE = False
        storage_add_tag = None
        storage_remove_tag = None
        storage_get_by_tag = None
        storage_get_all_tags = None

    # -------------------------------------------------------------------------
    # Tool: tag_artifact
    # -------------------------------------------------------------------------
    @tool(
        "tag_artifact",
        """Add or remove tags from an artifact.

Tags help organize and categorize artifacts for easy filtering and retrieval.
Tags are stored in lowercase and must be non-empty strings.

Actions:
- add: Add a tag to the artifact
- remove: Remove a tag from the artifact

Example usage:
  action: "add"
  artifact_id: "art_abc123def456"
  tag: "security"

Common tags: security, performance, architecture, bug, feature, documentation,
             refactoring, testing, critical, review-needed, approved
""",
        {
            "action": str,
            "artifact_id": str,
            "tag": str,
        },
    )
    async def tag_artifact_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Add or remove tags from an artifact."""
        action = args.get("action", "").lower()
        artifact_id = args.get("artifact_id", "")
        tag = args.get("tag", "")

        if not TAGS_AVAILABLE:
            return {
                "content": [
                    {"type": "text", "text": "Error: Tag management not available."}
                ]
            }

        if action not in ["add", "remove"]:
            return {
                "content": [
                    {"type": "text", "text": "Error: action must be 'add' or 'remove'."}
                ]
            }

        if not artifact_id:
            return {
                "content": [
                    {"type": "text", "text": "Error: artifact_id is required."}
                ]
            }

        if not tag or not tag.strip():
            return {
                "content": [
                    {"type": "text", "text": "Error: tag is required and cannot be empty."}
                ]
            }

        try:
            project_path = str(project_dir)
            tag = tag.strip().lower()

            if action == "add":
                success = storage_add_tag(project_path, artifact_id, tag)
                if success:
                    return {
                        "content": [
                            {"type": "text", "text": f"Tag '{tag}' added to artifact {artifact_id}"}
                        ]
                    }
                else:
                    return {
                        "content": [
                            {"type": "text", "text": f"Failed to add tag '{tag}' to artifact {artifact_id}. Artifact may not exist."}
                        ],
                        "isError": True
                    }
            else:  # remove
                success = storage_remove_tag(project_path, artifact_id, tag)
                if success:
                    return {
                        "content": [
                            {"type": "text", "text": f"Tag '{tag}' removed from artifact {artifact_id}"}
                        ]
                    }
                else:
                    return {
                        "content": [
                            {"type": "text", "text": f"Failed to remove tag '{tag}' from artifact {artifact_id}. Artifact may not exist."}
                        ],
                        "isError": True
                    }

        except Exception as e:
            logger.error(f"Error in tag_artifact: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error managing tag: {str(e)}"}
                ],
                "isError": True
            }

    tools.append(tag_artifact_tool)

    # -------------------------------------------------------------------------
    # Tool: get_artifacts_by_tag
    # -------------------------------------------------------------------------
    @tool(
        "get_artifacts_by_tag",
        """Get all artifacts that have a specific tag.

Returns a list of artifacts matching the specified tag.
Tags are case-insensitive.

Example:
  tag: "security"

Returns artifacts with that tag, including their full content.
""",
        {
            "tag": str,
        },
    )
    async def get_artifacts_by_tag_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Get artifacts by tag."""
        tag = args.get("tag", "")

        if not TAGS_AVAILABLE or not storage_get_by_tag:
            return {
                "content": [
                    {"type": "text", "text": "Error: Tag management not available."}
                ]
            }

        if not tag or not tag.strip():
            return {
                "content": [
                    {"type": "text", "text": "Error: tag is required."}
                ]
            }

        try:
            project_path = str(project_dir)
            tag = tag.strip().lower()

            artifacts = storage_get_by_tag(project_path, tag)

            if not artifacts:
                return {
                    "content": [
                        {"type": "text", "text": f"No artifacts found with tag '{tag}'."}
                    ]
                }

            # Format response
            lines = [f"=== Artifacts with tag '{tag}' ({len(artifacts)}) ===", ""]

            for art in artifacts:
                lines.append(f"ID: {art.get('id', 'unknown')}")
                lines.append(f"  Type: {art.get('type', 'unknown')} | Tab: {TAB_NAMES.get(art.get('tab', ''), art.get('tab', ''))}")
                lines.append(f"  Value: ${art.get('value_usd', 0)} | {art.get('created_at', '')[:10] if art.get('created_at') else 'N/A'}")
                lines.append(f"  Tags: {', '.join(art.get('metadata', {}).get('tags', []))}")
                content_preview = art.get("content", "")[:50]
                if len(art.get("content", "")) > 50:
                    content_preview += "..."
                lines.append(f"  Preview: {content_preview}")
                lines.append("")

            return {
                "content": [{"type": "text", "text": "\n".join(lines)}],
                "structuredContent": {
                    "tag": tag,
                    "count": len(artifacts),
                    "artifacts": artifacts
                }
            }

        except Exception as e:
            logger.error(f"Error getting artifacts by tag: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error getting artifacts by tag: {str(e)}"}
                ],
                "isError": True
            }

    tools.append(get_artifacts_by_tag_tool)

    # -------------------------------------------------------------------------
    # Tool: list_all_tags
    # -------------------------------------------------------------------------
    @tool(
        "list_all_tags",
        """List all unique tags used across all artifacts in the project.

Returns a sorted list of all tags that have been applied to any artifact.
Useful for discovering available tags for filtering.

No arguments required.
""",
        {},
    )
    async def list_all_tags_tool(args: dict[str, Any]) -> dict[str, Any]:
        """List all unique tags."""
        if not TAGS_AVAILABLE or not storage_get_all_tags:
            return {
                "content": [
                    {"type": "text", "text": "Error: Tag management not available."}
                ]
            }

        try:
            project_path = str(project_dir)
            tags = storage_get_all_tags(project_path)

            if not tags:
                return {
                    "content": [
                        {"type": "text", "text": "No tags found. Use tag_artifact to add tags to artifacts."}
                    ]
                }

            # Format response
            lines = [f"=== All Tags ({len(tags)}) ===", ""]
            for tag in tags:
                lines.append(f"  - {tag}")

            return {
                "content": [{"type": "text", "text": "\n".join(lines)}],
                "structuredContent": {
                    "count": len(tags),
                    "tags": tags
                }
            }

        except Exception as e:
            logger.error(f"Error listing all tags: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error listing tags: {str(e)}"}
                ],
                "isError": True
            }

    tools.append(list_all_tags_tool)

    # =========================================================================
    # CLEANUP AND RETENTION TOOLS
    # =========================================================================

    # Import cleanup functions
    try:
        from analytics.artifact_storage import (
            cleanup_old_artifacts as storage_cleanup_old,
            cleanup_by_type as storage_cleanup_by_type,
            get_cleanup_preview as storage_get_cleanup_preview,
            archive_artifacts as storage_archive_artifacts,
            restore_archived_artifact as storage_restore_archived,
            get_archived_artifacts as storage_get_archived,
        )
        CLEANUP_AVAILABLE = True
    except ImportError:
        CLEANUP_AVAILABLE = False
        storage_cleanup_old = None
        storage_cleanup_by_type = None
        storage_get_cleanup_preview = None
        storage_archive_artifacts = None
        storage_restore_archived = None
        storage_get_archived = None

    # -------------------------------------------------------------------------
    # Tool: cleanup_artifacts
    # -------------------------------------------------------------------------
    @tool(
        "cleanup_artifacts",
        """Clean up old artifacts by age or type.

IMPORTANT: By default this runs in dry_run mode (preview only).
Set dry_run=false to actually delete artifacts.

Cleanup modes:
1. By age: Delete artifacts older than N days
   - days: Number of days (default: 30)
   - dry_run: Preview only (default: true)

2. By type: Keep only the N most recent artifacts of a specific type
   - artifact_type: The type to clean up (e.g., "diagram", "code_example")
   - keep_latest: Number to keep (default: 10)
   - dry_run: Preview only (default: true)

Safety:
- ALWAYS runs in dry_run mode by default
- Review the preview before running with dry_run=false
- Consider using archive_artifacts instead of deleting

Examples:
  # Preview cleanup of artifacts older than 30 days
  days: 30

  # Actually delete artifacts older than 60 days
  days: 60
  dry_run: false

  # Preview keeping only 5 most recent diagrams
  artifact_type: "diagram"
  keep_latest: 5

  # Actually clean up, keeping 10 recent code_examples
  artifact_type: "code_example"
  keep_latest: 10
  dry_run: false
""",
        {
            "days": int,
            "artifact_type": str,
            "keep_latest": int,
            "dry_run": bool,
        },
    )
    async def cleanup_artifacts_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Clean up artifacts by age or type."""
        days = args.get("days", 30)
        artifact_type = args.get("artifact_type", "")
        keep_latest = args.get("keep_latest", 10)
        dry_run = args.get("dry_run", True)  # Default to dry run for safety

        if not CLEANUP_AVAILABLE:
            return {
                "content": [
                    {"type": "text", "text": "Error: Artifact cleanup not available."}
                ]
            }

        try:
            if artifact_type:
                # Cleanup by type
                result = storage_cleanup_by_type(
                    project_dir=project_dir,
                    artifact_type=artifact_type,
                    keep_latest=keep_latest,
                    dry_run=dry_run,
                )

                action_word = "Would delete" if dry_run else "Deleted"
                response_text = f"""
=== Cleanup by Type: {artifact_type} ===

Mode: {"DRY RUN (preview only)" if dry_run else "ACTUAL DELETION"}
Type: {artifact_type}
Keep Latest: {keep_latest}

{action_word}: {result['deleted_count']} artifacts
Kept: {result['kept_count']} artifacts

{f"IDs that would be deleted:" if dry_run else "Deleted IDs:"}
{chr(10).join(f"  - {id}" for id in result['deleted_ids'][:20]) if result['deleted_ids'] else "  (none)"}
{f"  ... and {len(result['deleted_ids']) - 20} more" if len(result['deleted_ids']) > 20 else ""}
"""
                if dry_run:
                    response_text += "\nTo actually delete, run again with dry_run=false"

            else:
                # Cleanup by age
                result = storage_cleanup_old(
                    project_dir=project_dir,
                    days=days,
                    dry_run=dry_run,
                )

                action_word = "Would delete" if dry_run else "Deleted"
                freed_kb = result['freed_bytes'] / 1024
                response_text = f"""
=== Cleanup by Age ===

Mode: {"DRY RUN (preview only)" if dry_run else "ACTUAL DELETION"}
Cutoff: {days} days old

{action_word}: {result['deleted_count']} artifacts
{action_word.replace('delete', 'free')}: {freed_kb:.2f} KB

{f"IDs that would be deleted:" if dry_run else "Deleted IDs:"}
{chr(10).join(f"  - {id}" for id in result['deleted_ids'][:20]) if result['deleted_ids'] else "  (none)"}
{f"  ... and {len(result['deleted_ids']) - 20} more" if len(result['deleted_ids']) > 20 else ""}
"""
                if dry_run:
                    response_text += "\nTo actually delete, run again with dry_run=false"

            return {
                "content": [{"type": "text", "text": response_text.strip()}],
                "structuredContent": result
            }

        except Exception as e:
            logger.error(f"Error in cleanup_artifacts: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error cleaning up artifacts: {str(e)}"}
                ],
                "isError": True
            }

    tools.append(cleanup_artifacts_tool)

    # -------------------------------------------------------------------------
    # Tool: archive_artifacts
    # -------------------------------------------------------------------------
    @tool(
        "archive_artifacts",
        """Archive specific artifacts.

Archived artifacts are MOVED (not deleted) to .auto-claude/artifacts/archive/
This preserves them while keeping the main storage clean.

Use this instead of deleting when you want to:
- Keep a backup of old artifacts
- Clean up without permanent deletion
- Be able to restore artifacts later

Args:
  artifact_ids: List of artifact IDs to archive

Example:
  artifact_ids: ["art_abc123", "art_def456"]

Returns count of successfully archived artifacts and any failures.
""",
        {
            "artifact_ids": list,
        },
    )
    async def archive_artifacts_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Archive specific artifacts."""
        artifact_ids = args.get("artifact_ids", [])

        if not CLEANUP_AVAILABLE or not storage_archive_artifacts:
            return {
                "content": [
                    {"type": "text", "text": "Error: Artifact archiving not available."}
                ]
            }

        if not artifact_ids:
            return {
                "content": [
                    {"type": "text", "text": "Error: artifact_ids list is required."}
                ]
            }

        try:
            result = storage_archive_artifacts(
                project_dir=project_dir,
                artifact_ids=artifact_ids,
            )

            response_text = f"""
=== Archive Results ===

Archived: {result['archived_count']} artifacts
Failed: {result['failed_count']} artifacts

Archived IDs:
{chr(10).join(f"  - {id}" for id in result['archived_ids']) if result['archived_ids'] else "  (none)"}

{f"Failed IDs:{chr(10)}{chr(10).join(f'  - {id}' for id in result['failed_ids'])}" if result['failed_ids'] else ""}
"""
            return {
                "content": [{"type": "text", "text": response_text.strip()}],
                "structuredContent": result
            }

        except Exception as e:
            logger.error(f"Error archiving artifacts: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error archiving artifacts: {str(e)}"}
                ],
                "isError": True
            }

    tools.append(archive_artifacts_tool)

    # -------------------------------------------------------------------------
    # Tool: get_cleanup_preview
    # -------------------------------------------------------------------------
    @tool(
        "get_cleanup_preview",
        """Preview what would be deleted by cleanup.

Shows a detailed preview of artifacts that would be deleted if you run
cleanup_artifacts with dry_run=false.

Args:
  days: Preview artifacts older than this many days (default: 30)

Returns:
- Number of artifacts that would be deleted
- Total bytes that would be freed
- List of artifact summaries (ID, type, date, value, size)

Use this to review before running actual cleanup.
""",
        {
            "days": int,
        },
    )
    async def get_cleanup_preview_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Preview cleanup results."""
        days = args.get("days", 30)

        if not CLEANUP_AVAILABLE or not storage_get_cleanup_preview:
            return {
                "content": [
                    {"type": "text", "text": "Error: Cleanup preview not available."}
                ]
            }

        try:
            result = storage_get_cleanup_preview(
                project_dir=project_dir,
                days=days,
            )

            freed_kb = result['total_bytes'] / 1024
            response_text = f"""
=== Cleanup Preview ===

Cutoff: {days} days (before {result.get('cutoff_date', 'N/A')})
Would Delete: {result['would_delete']} artifacts
Would Free: {freed_kb:.2f} KB

Artifacts to delete (oldest first):
"""
            for art in result.get('artifacts', [])[:30]:
                size_kb = art.get('size_bytes', 0) / 1024
                response_text += f"\n  {art['id']}"
                response_text += f"\n    Type: {art['type']} | Date: {art['date']} | Value: ${art.get('value_usd', 0)} | Size: {size_kb:.1f}KB"
                if art.get('spec_id'):
                    response_text += f" | Spec: {art['spec_id']}"

            if len(result.get('artifacts', [])) > 30:
                response_text += f"\n\n  ... and {len(result['artifacts']) - 30} more artifacts"

            if result['would_delete'] > 0:
                response_text += "\n\nTo delete these, run cleanup_artifacts with dry_run=false"

            return {
                "content": [{"type": "text", "text": response_text.strip()}],
                "structuredContent": result
            }

        except Exception as e:
            logger.error(f"Error getting cleanup preview: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error getting cleanup preview: {str(e)}"}
                ],
                "isError": True
            }

    tools.append(get_cleanup_preview_tool)

    # -------------------------------------------------------------------------
    # Tool: list_archived_artifacts
    # -------------------------------------------------------------------------
    @tool(
        "list_archived_artifacts",
        """List all archived artifacts.

Shows artifacts that have been moved to the archive directory.
Archived artifacts can be restored using restore_archived_artifact.

No arguments required.
""",
        {},
    )
    async def list_archived_artifacts_tool(args: dict[str, Any]) -> dict[str, Any]:
        """List archived artifacts."""
        if not CLEANUP_AVAILABLE or not storage_get_archived:
            return {
                "content": [
                    {"type": "text", "text": "Error: Archive listing not available."}
                ]
            }

        try:
            archived = storage_get_archived(project_dir)

            if not archived:
                return {
                    "content": [
                        {"type": "text", "text": "No archived artifacts found."}
                    ]
                }

            response_text = f"=== Archived Artifacts ({len(archived)}) ===\n"

            for art in archived[:50]:
                response_text += f"\n{art['id']}"
                response_text += f"\n  Type: {art['type']} | Value: ${art.get('value_usd', 0)}"
                response_text += f"\n  Created: {art.get('created_at', 'N/A')[:10] if art.get('created_at') else 'N/A'}"
                response_text += f"\n  Archived: {art.get('archived_at', 'N/A')[:10] if art.get('archived_at') else 'N/A'}"
                if art.get('description'):
                    response_text += f"\n  Description: {art['description'][:50]}..."
                response_text += "\n"

            if len(archived) > 50:
                response_text += f"\n... and {len(archived) - 50} more archived artifacts"

            return {
                "content": [{"type": "text", "text": response_text.strip()}],
                "structuredContent": {
                    "count": len(archived),
                    "artifacts": archived
                }
            }

        except Exception as e:
            logger.error(f"Error listing archived artifacts: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error listing archived artifacts: {str(e)}"}
                ],
                "isError": True
            }

    tools.append(list_archived_artifacts_tool)

    # -------------------------------------------------------------------------
    # Tool: restore_archived_artifact
    # -------------------------------------------------------------------------
    @tool(
        "restore_archived_artifact",
        """Restore an archived artifact back to active storage.

Moves an artifact from the archive back to its original date directory.
The artifact will be available again in searches and listings.

Args:
  artifact_id: The artifact ID to restore

Example:
  artifact_id: "art_abc123def456"
""",
        {
            "artifact_id": str,
        },
    )
    async def restore_archived_artifact_tool(args: dict[str, Any]) -> dict[str, Any]:
        """Restore an archived artifact."""
        artifact_id = args.get("artifact_id", "")

        if not CLEANUP_AVAILABLE or not storage_restore_archived:
            return {
                "content": [
                    {"type": "text", "text": "Error: Archive restoration not available."}
                ]
            }

        if not artifact_id:
            return {
                "content": [
                    {"type": "text", "text": "Error: artifact_id is required."}
                ]
            }

        try:
            result = storage_restore_archived(
                project_dir=project_dir,
                artifact_id=artifact_id,
            )

            if result['success']:
                return {
                    "content": [
                        {"type": "text", "text": f"Artifact {artifact_id} restored successfully.\n{result['message']}"}
                    ]
                }
            else:
                return {
                    "content": [
                        {"type": "text", "text": f"Failed to restore artifact: {result['message']}"}
                    ],
                    "isError": True
                }

        except Exception as e:
            logger.error(f"Error restoring archived artifact: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error restoring artifact: {str(e)}"}
                ],
                "isError": True
            }

    tools.append(restore_archived_artifact_tool)

    return tools
