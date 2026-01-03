"""
Artifact Capture Module
=======================

Captures artifacts from MCP tool outputs with FULL content.

TWO CAPTURE MODES:
==================

1. EXPLICIT MODE (Recommended, Default)
   - Agent uses MCP tools: create_artifact, create_diagram, report_security_finding
   - PostToolUse hook captures the STRUCTURED result from the tool
   - Reliable, predictable, agent-controlled
   - Requires well-structured system prompts that instruct agents to use tools

2. EXTRACTION MODE (Optional Fallback)
   - Regex-based extraction from tool outputs
   - Can catch artifacts that agent didn't explicitly create
   - Less reliable, may have false positives
   - Enable with ARTIFACT_EXTRACTION_ENABLED=true

The recommended approach is EXPLICIT MODE with system prompts that instruct
agents to use artifact tools when they discover something valuable.

Example system prompt addition:
    "When you discover a pattern, gotcha, or create a diagram,
     use the appropriate MCP tool to record it:
     - create_diagram for Mermaid/ASCII diagrams
     - report_security_finding for security issues
     - create_artifact for patterns, gotchas, insights"
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .value_engine import get_artifact_value, ValueAttribution
from .storage import save_artifact, get_artifacts_summary

logger = logging.getLogger(__name__)

# Check if extraction mode is enabled (default: False)
EXTRACTION_ENABLED = os.environ.get('ARTIFACT_EXTRACTION_ENABLED', '').lower() in ('true', '1', 'yes')


# =============================================================================
# EXPLICIT MODE: Capture from MCP Tool Results
# =============================================================================

# MCP tools that create artifacts (from agents/tools_pkg/models.py)
ARTIFACT_TOOLS = {
    "mcp__auto-claude__create_artifact",
    "mcp__auto-claude__create_diagram",
    "mcp__auto-claude__report_security_finding",
    "mcp__auto-claude__suggest_recommendation",
    "mcp__auto-claude__record_discovery",
    "mcp__auto-claude__record_gotcha",
}


def capture_from_mcp_tool_result(
    tool_name: str,
    tool_result: Dict[str, Any],
    agent_type: str = "unknown",
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    project_dir: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Capture artifact from an MCP tool result (EXPLICIT MODE).

    This is called when an agent EXPLICITLY uses an artifact creation tool.
    The tool result already contains structured artifact data.

    IMPORTANT: MCP tools (create_artifact, create_diagram, etc.) already save
    artifacts via analytics.artifact_storage. This function should NOT save
    again to avoid duplication. Instead, it returns the artifact info for
    tracking purposes only.

    Args:
        tool_name: Full MCP tool name (e.g., mcp__auto-claude__create_artifact)
        tool_result: Structured result from the tool with artifact_id, type, content
        agent_type: Type of agent that created the artifact
        trace_id: Langfuse trace ID
        spec_id: Spec ID if available
        project_dir: Project directory

    Returns:
        Artifact dict (already saved by tool) or None if not an artifact tool
    """
    # Only process artifact creation tools
    if tool_name not in ARTIFACT_TOOLS:
        return None

    # Extract artifact data from tool result
    artifact_id = tool_result.get("artifact_id")
    artifact_type = tool_result.get("artifact_type", "generic")
    content = tool_result.get("content", "")
    description = tool_result.get("description", f"Artifact from {tool_name}")
    format_type = tool_result.get("format", "text")
    value_usd = tool_result.get("value_usd", 0)

    # If content is a list (MCP content blocks), extract text
    if isinstance(content, list):
        content = "\n".join(
            block.get("text", str(block))
            for block in content
            if isinstance(block, dict)
        )

    if not content:
        logger.warning(f"Empty content from {tool_name}, skipping")
        return None

    # =========================================================================
    # CRITICAL: Check if artifact was already saved by the MCP tool
    # =========================================================================
    # MCP tools like create_artifact already save via analytics.artifact_storage.
    # If artifact_id exists in the result, the artifact is ALREADY saved.
    # We should NOT save again to avoid duplication.

    if artifact_id:
        # Artifact already saved by MCP tool - just return info for tracking
        logger.info(
            f"[EXPLICIT] Artifact already saved by {tool_name}: "
            f"{artifact_id} ({artifact_type}, ${value_usd:.2f})"
        )
        return {
            "id": artifact_id,
            "type": artifact_type,
            "format": format_type,
            "content": content,
            "description": description,
            "value_usd": value_usd,
            "trace_id": trace_id,
            "spec_id": spec_id,
            "agent_type": agent_type,
            "already_saved": True,  # Flag to indicate no duplicate save
        }

    # =========================================================================
    # Fallback: If no artifact_id, the tool didn't save it (unexpected)
    # In this case, we save via extensions storage (which delegates to main)
    # =========================================================================
    logger.warning(
        f"[EXPLICIT] No artifact_id from {tool_name}, saving via extensions storage"
    )

    # Calculate value if not provided
    if not value_usd:
        value_info = get_artifact_value(
            artifact_type=artifact_type,
            agent_type=agent_type,
        )
        value_usd = value_info["adjusted_value_usd"]

    metadata = tool_result.get("metadata", {})
    metadata["tool_name"] = tool_name
    metadata["agent_type"] = agent_type
    metadata["capture_mode"] = "explicit_fallback"

    # Save artifact with full content
    saved = save_artifact(
        artifact_type=artifact_type,
        content=content,
        description=description,
        value_usd=value_usd,
        trace_id=trace_id,
        spec_id=spec_id,
        agent_type=agent_type,
        project_dir=project_dir,
        metadata=metadata,
        format=format_type,
    )

    if saved:
        logger.info(
            f"[EXPLICIT] Saved artifact via fallback: "
            f"{artifact_type} (${value_usd:.2f})"
        )

    return saved


# =============================================================================
# EXTRACTION MODE: Optional Regex-Based Detection
# =============================================================================
# Only used when ARTIFACT_EXTRACTION_ENABLED=true
# This is a FALLBACK mechanism, not the primary capture method

@dataclass
class CapturedArtifact:
    """Represents a captured artifact before storage (extraction mode only)."""
    artifact_type: str
    content: str
    description: str
    format: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)


# Artifact Detection Patterns (only used in extraction mode)

# Mermaid diagram detection
MERMAID_PATTERNS = [
    r'```mermaid\s*([\s\S]*?)```',
    r'graph\s+(?:TB|TD|BT|RL|LR)\s*\n([\s\S]*?)(?=\n\n|\Z)',
    r'sequenceDiagram\s*([\s\S]*?)(?=\n\n|\Z)',
    r'classDiagram\s*([\s\S]*?)(?=\n\n|\Z)',
    r'flowchart\s+(?:TB|TD|BT|RL|LR)\s*([\s\S]*?)(?=\n\n|\Z)',
]

# ASCII diagram detection
ASCII_DIAGRAM_PATTERNS = [
    r'┌[─┬]+┐[\s\S]*?└[─┴]+┘',  # Box drawings
    r'\+[-+]+\+[\s\S]*?\+[-+]+\+',  # ASCII boxes
    r'│[\s\S]*?│',  # Vertical lines
    r'→.*→.*→',  # Flow arrows
    r'⟶.*⟶.*⟶',  # Unicode arrows
]

# Pattern/gotcha keyword detection
PATTERN_KEYWORDS = [
    'pattern:', 'pattern found:', 'discovered pattern:',
    'architectural pattern:', 'design pattern:',
    'best practice:', 'recommended approach:',
]

GOTCHA_KEYWORDS = [
    'gotcha:', 'warning:', 'caution:', 'pitfall:',
    'edge case:', 'watch out:', 'be careful:',
    'trap:', 'common mistake:', 'avoid:',
]

SECURITY_KEYWORDS = [
    'security:', 'vulnerability:', 'security issue:',
    'security risk:', 'cve:', 'owasp:',
    'injection:', 'xss:', 'csrf:', 'authentication:',
]


def detect_mermaid_diagrams(content: str) -> List[CapturedArtifact]:
    """Detect Mermaid diagrams in content."""
    artifacts = []

    for pattern in MERMAID_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            diagram_content = match.strip() if isinstance(match, str) else match[0].strip()
            if len(diagram_content) > 20:  # Minimum viable diagram
                artifacts.append(CapturedArtifact(
                    artifact_type="mermaid_diagram",
                    content=diagram_content,
                    description="Mermaid diagram extracted from tool output",
                    format="mermaid",
                    metadata={"source": "mermaid_pattern"}
                ))

    return artifacts


def detect_ascii_diagrams(content: str) -> List[CapturedArtifact]:
    """Detect ASCII art diagrams in content."""
    artifacts = []

    for pattern in ASCII_DIAGRAM_PATTERNS:
        matches = re.findall(pattern, content)
        for match in matches:
            if len(match) > 30:  # Minimum size for meaningful diagram
                artifacts.append(CapturedArtifact(
                    artifact_type="ascii_diagram",
                    content=match,
                    description="ASCII diagram extracted from tool output",
                    format="text",
                    metadata={"source": "ascii_pattern"}
                ))

    return artifacts


def detect_patterns(content: str) -> List[CapturedArtifact]:
    """Detect architectural/coding patterns in content."""
    artifacts = []
    content_lower = content.lower()

    for keyword in PATTERN_KEYWORDS:
        if keyword in content_lower:
            # Extract the pattern context (paragraph containing keyword)
            idx = content_lower.index(keyword)
            # Get surrounding context (500 chars before and after)
            start = max(0, idx - 100)
            end = min(len(content), idx + 500)
            pattern_content = content[start:end].strip()

            if len(pattern_content) > 50:
                artifacts.append(CapturedArtifact(
                    artifact_type="pattern_discovered",
                    content=pattern_content,
                    description=f"Pattern discovered: {keyword.replace(':', '').strip()}",
                    format="markdown",
                    metadata={"keyword": keyword, "source": "keyword_detection"}
                ))
                break  # One pattern per keyword type

    return artifacts


def detect_gotchas(content: str) -> List[CapturedArtifact]:
    """Detect gotchas and edge cases in content."""
    artifacts = []
    content_lower = content.lower()

    for keyword in GOTCHA_KEYWORDS:
        if keyword in content_lower:
            idx = content_lower.index(keyword)
            start = max(0, idx - 50)
            end = min(len(content), idx + 400)
            gotcha_content = content[start:end].strip()

            if len(gotcha_content) > 30:
                artifacts.append(CapturedArtifact(
                    artifact_type="gotcha_identified",
                    content=gotcha_content,
                    description=f"Gotcha identified: {keyword.replace(':', '').strip()}",
                    format="markdown",
                    metadata={"keyword": keyword, "source": "keyword_detection"}
                ))
                break

    return artifacts


def detect_security_findings(content: str) -> List[CapturedArtifact]:
    """Detect security-related findings in content."""
    artifacts = []
    content_lower = content.lower()

    for keyword in SECURITY_KEYWORDS:
        if keyword in content_lower:
            idx = content_lower.index(keyword)
            start = max(0, idx - 50)
            end = min(len(content), idx + 500)
            security_content = content[start:end].strip()

            if len(security_content) > 50:
                artifacts.append(CapturedArtifact(
                    artifact_type="security_finding",
                    content=security_content,
                    description=f"Security finding: {keyword.replace(':', '').strip()}",
                    format="markdown",
                    metadata={"keyword": keyword, "source": "keyword_detection"}
                ))
                break

    return artifacts


def detect_code_snippets(content: str) -> List[CapturedArtifact]:
    """Detect code snippets with language tags."""
    artifacts = []

    # Match code blocks with language tags
    pattern = r'```(\w+)\s*([\s\S]*?)```'
    matches = re.findall(pattern, content)

    for lang, code in matches:
        if lang.lower() not in ['mermaid', 'text', 'output', 'bash', 'shell']:
            if len(code.strip()) > 50:
                artifacts.append(CapturedArtifact(
                    artifact_type="code_snippet",
                    content=code.strip(),
                    description=f"Code snippet ({lang})",
                    format=lang,
                    metadata={"language": lang, "source": "code_block"}
                ))

    return artifacts


def detect_recommendations(content: str) -> List[CapturedArtifact]:
    """Detect recommendations and best practices."""
    artifacts = []

    recommendation_patterns = [
        r'(?:recommendation|suggest|recommend):\s*([^\n]+(?:\n(?!\n)[^\n]+)*)',
        r'(?:best practice|tip):\s*([^\n]+(?:\n(?!\n)[^\n]+)*)',
    ]

    for pattern in recommendation_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if len(match) > 30:
                artifacts.append(CapturedArtifact(
                    artifact_type="recommendation",
                    content=match.strip(),
                    description="Recommendation extracted from tool output",
                    format="text",
                    metadata={"source": "recommendation_pattern"}
                ))

    return artifacts


# =============================================================================
# Main Capture Functions
# =============================================================================

def extract_artifacts_from_content(content: str) -> List[CapturedArtifact]:
    """
    Extract all artifacts from content using regex patterns.

    ONLY USED when ARTIFACT_EXTRACTION_ENABLED=true.
    This is a fallback mechanism - prefer EXPLICIT MODE via MCP tools.
    """
    if not EXTRACTION_ENABLED:
        return []

    if not content or len(content) < 20:
        return []

    artifacts = []

    # Run all detectors
    artifacts.extend(detect_mermaid_diagrams(content))
    artifacts.extend(detect_ascii_diagrams(content))
    artifacts.extend(detect_patterns(content))
    artifacts.extend(detect_gotchas(content))
    artifacts.extend(detect_security_findings(content))
    artifacts.extend(detect_code_snippets(content))
    artifacts.extend(detect_recommendations(content))

    # Deduplicate by content hash
    seen_content = set()
    unique_artifacts = []
    for artifact in artifacts:
        content_hash = hash(artifact.content[:100])  # First 100 chars for dedup
        if content_hash not in seen_content:
            seen_content.add(content_hash)
            unique_artifacts.append(artifact)

    if unique_artifacts:
        logger.info(f"[EXTRACTION] Found {len(unique_artifacts)} artifacts via regex")

    return unique_artifacts


def capture_from_tool_result(
    tool_name: str,
    tool_result: Any,
    agent_type: str = "unknown",
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    project_dir: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], ValueAttribution]:
    """
    Capture artifacts from a tool result.

    This is the MAIN entry point called from PostToolUse hooks.

    Processing order:
    1. EXPLICIT MODE: Check if this is an artifact creation tool
    2. EXTRACTION MODE: If enabled, run regex detection on output

    Args:
        tool_name: Name of the MCP tool that was called
        tool_result: The result from the tool (string or dict)
        agent_type: Type of agent (coder, planner, qa_reviewer, etc.)
        trace_id: Langfuse trace ID for linking
        spec_id: Spec ID if available
        project_dir: Project directory for storage

    Returns:
        Tuple of (list of saved artifacts, value attribution summary)
    """
    saved_artifacts = []
    value_attribution = ValueAttribution()

    # ===========================================
    # 1. EXPLICIT MODE: Check for artifact tools
    # ===========================================
    if isinstance(tool_result, dict) and tool_name in ARTIFACT_TOOLS:
        saved = capture_from_mcp_tool_result(
            tool_name=tool_name,
            tool_result=tool_result,
            agent_type=agent_type,
            trace_id=trace_id,
            spec_id=spec_id,
            project_dir=project_dir,
        )
        if saved:
            saved_artifacts.append(saved)
            value_info = get_artifact_value(
                artifact_type=saved.get("type", "generic"),
                agent_type=agent_type,
            )
            value_attribution.add_artifact(value_info)
        return saved_artifacts, value_attribution

    # ===========================================
    # 2. EXTRACTION MODE: Optional regex fallback
    # ===========================================
    if not EXTRACTION_ENABLED:
        return saved_artifacts, value_attribution

    # Convert tool result to string for analysis
    if isinstance(tool_result, dict):
        content = str(tool_result.get('content', tool_result.get('output', str(tool_result))))
    elif isinstance(tool_result, str):
        content = tool_result
    else:
        content = str(tool_result)

    # Extract artifacts via regex
    captured = extract_artifacts_from_content(content)

    if not captured:
        return saved_artifacts, value_attribution

    # Process and save each extracted artifact
    for artifact in captured:
        value_info = get_artifact_value(
            artifact_type=artifact.artifact_type,
            agent_type=agent_type,
        )

        artifact.metadata["tool_name"] = tool_name
        artifact.metadata["agent_type"] = agent_type
        artifact.metadata["capture_mode"] = "extraction"

        saved = save_artifact(
            artifact_type=artifact.artifact_type,
            content=artifact.content,
            description=artifact.description,
            value_usd=value_info["adjusted_value_usd"],
            trace_id=trace_id,
            spec_id=spec_id,
            agent_type=agent_type,
            project_dir=project_dir,
            metadata=artifact.metadata,
            format=artifact.format,
        )

        if saved:
            saved_artifacts.append(saved)
            value_attribution.add_artifact(value_info)
            logger.info(
                f"[EXTRACTION] Captured artifact: {artifact.artifact_type} "
                f"(${value_info['adjusted_value_usd']:.2f})"
            )

    return saved_artifacts, value_attribution


def capture_from_agent_output(
    agent_output: str,
    agent_type: str,
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    project_dir: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], ValueAttribution]:
    """
    Capture artifacts from agent final output.

    This can be called at the end of an agent session to capture
    any artifacts from the final response.

    NOTE: Only works if ARTIFACT_EXTRACTION_ENABLED=true
    Otherwise, agents should use MCP tools to create artifacts explicitly.
    """
    if not EXTRACTION_ENABLED:
        logger.debug("Extraction mode disabled, skipping agent output capture")
        return [], ValueAttribution()

    return capture_from_tool_result(
        tool_name="agent_output",
        tool_result=agent_output,
        agent_type=agent_type,
        trace_id=trace_id,
        spec_id=spec_id,
        project_dir=project_dir,
    )


# =============================================================================
# Summary Functions
# =============================================================================

def get_session_artifacts_summary(
    trace_id: Optional[str] = None,
    spec_id: Optional[str] = None,
    project_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get a summary of artifacts captured during a session.

    This is useful for publishing to Langfuse at the end of a trace.
    """
    return get_artifacts_summary(
        trace_id=trace_id,
        spec_id=spec_id,
        project_dir=project_dir,
    )
