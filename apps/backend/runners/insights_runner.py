#!/usr/bin/env python3
"""
Insights Runner - AI chat for codebase insights using Claude SDK

This script provides an AI-powered chat interface for asking questions
about a codebase. It can also suggest tasks based on the conversation.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
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

try:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    ClaudeAgentOptions = None
    ClaudeSDKClient = None

from core.auth import ensure_claude_code_oauth_token, get_auth_token, get_sdk_env_vars
from phase_config import resolve_model_id
from agents.tools_pkg.models import ROI_TOOLS, ARTIFACT_TOOLS
from agents.tools_pkg import create_auto_claude_mcp_server, is_tools_available
from debug import (
    debug,
    debug_detailed,
    debug_error,
    debug_section,
    debug_success,
)
from phase_config import resolve_model_id

# Import Langfuse integration for tracing
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        trace_context,
        log_generation_in_current_trace,
        is_langfuse_ready,
        flush_langfuse,
    )
    LANGFUSE_AVAILABLE = True
    # Initialize Langfuse early (idempotent - safe to call multiple times)
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    trace_context = None
    _langfuse_init_result = False

# Import legacy feature tracker for token tracking (backwards compatibility)
try:
    from analytics import (
        create_feature_tracker,
        FEATURE_INSIGHTS,
        is_tracking_enabled,
    )
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False

# Import ROI publisher
try:
    from analytics.roi_publisher import publish_insights_roi
    ROI_PUBLISHER_AVAILABLE = True
except ImportError:
    ROI_PUBLISHER_AVAILABLE = False

# Import artifact storage for local full content storage
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


def load_project_context(project_dir: str) -> str:
    """Load project context for the AI."""
    context_parts = []

    # Load project index if available (from .auto-claude - the installed instance)
    index_path = Path(project_dir) / ".auto-claude" / "project_index.json"
    if index_path.exists():
        try:
            with open(index_path) as f:
                index = json.load(f)
            # Summarize the index for context
            summary = {
                "project_root": index.get("project_root", ""),
                "project_type": index.get("project_type", "unknown"),
                "services": list(index.get("services", {}).keys()),
                "infrastructure": index.get("infrastructure", {}),
            }
            context_parts.append(
                f"## Project Structure\n```json\n{json.dumps(summary, indent=2)}\n```"
            )
        except Exception:
            pass

    # Load roadmap if available
    roadmap_path = Path(project_dir) / ".auto-claude" / "roadmap" / "roadmap.json"
    if roadmap_path.exists():
        try:
            with open(roadmap_path) as f:
                roadmap = json.load(f)
            # Summarize roadmap
            features = roadmap.get("features", [])
            feature_summary = [
                {"title": f.get("title", ""), "status": f.get("status", "")}
                for f in features[:10]
            ]
            context_parts.append(
                f"## Roadmap Features\n```json\n{json.dumps(feature_summary, indent=2)}\n```"
            )
        except Exception:
            pass

    # Load existing tasks
    tasks_path = Path(project_dir) / ".auto-claude" / "specs"
    if tasks_path.exists():
        try:
            task_dirs = [d for d in tasks_path.iterdir() if d.is_dir()]
            task_names = [d.name for d in task_dirs[:10]]
            if task_names:
                context_parts.append(
                    "## Existing Tasks/Specs\n- " + "\n- ".join(task_names)
                )
        except Exception:
            pass

    return (
        "\n\n".join(context_parts)
        if context_parts
        else "No project context available yet."
    )


def build_system_prompt(project_dir: str) -> str:
    """Build the system prompt for the insights agent."""
    context = load_project_context(project_dir)

    return f"""You are an AI assistant helping developers understand and work with their codebase.
You have access to the following project context:

{context}

Your capabilities:
1. Answer questions about the codebase structure, patterns, and architecture
2. Suggest improvements, features, or bug fixes based on the code
3. Help plan implementation of new features
4. Provide code examples and explanations

## ⚠️ MANDATORY: USE MCP TOOLS FOR ALL VALUABLE CONTENT ⚠️

**THIS IS NON-NEGOTIABLE:**
- Text output is NOT tracked, NOT billed, and NOT visible in the dashboard
- ONLY content created via MCP tool calls appears in analytics
- If you don't call a tool, the insight is LOST

**FOR EVERY valuable finding, you MUST call one of these tools:**

| Content Type | Tool to Use |
|--------------|-------------|
| Diagrams (mermaid, flowchart, sequence, etc.) | `create_diagram` |
| Documentation, explanations, summaries | `create_artifact` with type="documentation" |
| Code examples, snippets | `create_artifact` with type="code_example" |
| Recommendations, suggestions | `suggest_recommendation` |
| Security issues, vulnerabilities | `report_security_finding` |
| Architecture insights | `create_artifact` with type="architecture_insight" |
| API designs | `create_artifact` with type="api_design" |
| Performance insights | `create_artifact` with type="performance_insight" |

## Creating Artifacts (CRITICAL RULES)

1. **ALWAYS CALL THE TOOL** - Never just write text. Call the appropriate MCP tool.
2. **FULL CONTENT ONLY** - Each artifact must contain COMPLETE, SELF-CONTAINED content.
3. **ONE ARTIFACT = ONE COMPLETE FINDING** - If you have 5 points, create ONE artifact with all 5 points.
4. **NO FRAGMENTS** - An artifact with just "Implement logging" is useless. Include FULL explanation.
5. **QUALITY OVER QUANTITY** - 3 comprehensive artifacts > 10 tiny fragments.

## Tool Usage Examples

**DIAGRAM (MANDATORY for any visual):**
```
create_diagram(
  content="graph TB\\n    A[Client] --> B[Server]\\n    B --> C[Database]",
  format="mermaid",
  description="High-level architecture diagram"
)
```

**DOCUMENTATION:**
```
create_artifact(
  artifact_type="documentation",
  content="## Project Overview\\n\\nThis project implements...\\n\\n### Key Components\\n1. **Server** - Handles...\\n2. **Database** - Stores...",
  description="Comprehensive project documentation"
)
```

**RECOMMENDATION:**
```
suggest_recommendation(
  content="## Authentication Improvements\\n\\n1. **JWT refresh tokens** - Current tokens...\\n2. **Rate limiting** - Prevent brute force...\\n\\n### Implementation Steps:\\n1. Install package...\\n2. Create endpoint...",
  description="Security recommendations for authentication"
)
```

## Artifact Types by Dashboard Tab

- **DEV**: code_example, refactoring, bug_fix, test_case
- **TECHLEAD**: diagram, architecture_insight, api_design, documentation
- **OPS**: security_finding, performance_insight
- **BUSINESS**: recommendation, cost_analysis, priority_assessment

## ❌ WRONG (Do NOT do this):

```
Here is the architecture:
- Component A handles requests
- Component B stores data
```
↑ This is just TEXT - not tracked, not visible!

## ✅ CORRECT (Always do this):

```
create_artifact(
  artifact_type="documentation",
  content="## Architecture Overview\\n\\n- **Component A** - Handles requests...\\n- **Component B** - Stores data...",
  description="Architecture documentation"
)
```
↑ This calls the tool - tracked, visible, billed!

## Task Suggestions

When the user asks you to create a task, wants to turn the conversation into a task, or when you believe creating a task would be helpful, output a task suggestion in this exact format on a SINGLE LINE:
__TASK_SUGGESTION__:{{"title": "Task title here", "description": "Detailed description of what the task involves", "metadata": {{"category": "feature", "complexity": "medium", "impact": "medium"}}}}

Valid categories: feature, bug_fix, refactoring, documentation, security, performance, ui_ux, infrastructure, testing
Valid complexity: trivial, small, medium, large, complex
Valid impact: low, medium, high, critical

Be conversational and helpful. Focus on providing actionable insights and clear explanations.
Keep responses concise but informative."""


async def run_with_sdk(
    project_dir: str,
    message: str,
    history: list,
    model: str = "sonnet",  # Shorthand - resolved via API Profile if configured
    thinking_level: str = "medium",
) -> None:
    """Run the chat using Claude SDK with streaming."""
    # Resolve model for Azure Foundry mode (maps to deployment names)
    model = resolve_model_id(model)

    if not SDK_AVAILABLE:
        print("Claude SDK not available, falling back to simple mode", file=sys.stderr)
        run_simple(project_dir, message, history)
        return

    if not get_auth_token():
        print(
            "No authentication token found, falling back to simple mode",
            file=sys.stderr,
        )
        run_simple(project_dir, message, history)
        return

    # Ensure SDK can find the token
    ensure_claude_code_oauth_token()

    system_prompt = build_system_prompt(project_dir)
    project_path = Path(project_dir).resolve()

    # Build conversation context from history
    conversation_context = ""
    for msg in history[:-1]:  # Exclude the latest message
        role = "User" if msg.get("role") == "user" else "Assistant"
        conversation_context += f"\n{role}: {msg['content']}\n"

    # Build the full prompt with conversation history
    full_prompt = message
    if conversation_context.strip():
        full_prompt = f"""Previous conversation:
{conversation_context}

Current question: {message}"""

    debug(
        "insights_runner",
        "Using model configuration",
        model=model,
        thinking_level=thinking_level,
    )

    # Initialize feature tracker for token usage
    tracker = None
    if TRACKING_AVAILABLE and is_tracking_enabled():
        project_id = project_path.name
        db_path = str(project_path / ".auto-claude" / "analytics.db")
        tracker = create_feature_tracker(
            project_id=project_id,
            feature_type=FEATURE_INSIGHTS,
            db_path=db_path,
            metadata={"model": model, "thinking_level": thinking_level}
        )
        debug("insights_runner", "Feature tracker initialized", project_id=project_id)

    # Start tracking session if tracker is available
    if tracker:
        try:
            await tracker.start_session()
            debug("insights_runner", "Feature tracking session started")
        except Exception as e:
            debug_error("insights_runner", f"Failed to start tracking session: {e}")

    # Prepare Langfuse trace context
    use_langfuse = LANGFUSE_AVAILABLE and is_langfuse_ready()
    project_id = project_path.name
    trace_name = f"insights-{project_id}"

    try:
        # Create Claude SDK client with appropriate settings for insights
        # Pass Azure Foundry env vars to SDK subprocess
        sdk_env = get_sdk_env_vars()

        # Create Langfuse trace context FIRST to get trace_id for SDK subprocess
        # This is critical for artifact tracking - MCP tools need the trace_id
        trace_ctx = None
        langfuse_ctx_obj = None
        langfuse_trace_id = None
        if use_langfuse and trace_context:
            # Truncate prompt for trace input
            trace_input = full_prompt[:2000] + "..." if len(full_prompt) > 2000 else full_prompt
            trace_ctx = trace_context(
                name=trace_name,
                project_id=project_id,  # Required for data isolation filtering
                agent_type="insights",
                metadata={
                    "model": model,
                    "thinking_level": thinking_level,
                    "history_length": len(history),
                },
                tags=["insights", f"project:{project_id}"],
                input_data={"prompt": trace_input, "history_length": len(history)},
            )
            langfuse_ctx_obj = trace_ctx.__enter__()
            debug("insights_runner", "Langfuse trace created", trace_name=trace_name)

            # Get trace_id for SDK subprocess and artifact storage loading
            # NOTE: trace_context now automatically sets trace_id in thread-local storage
            # for MCP tools, so we only need to pass it to SDK subprocess and capture it
            if langfuse_ctx_obj and hasattr(langfuse_ctx_obj, 'trace_id'):
                langfuse_trace_id = langfuse_ctx_obj.trace_id
                sdk_env["LANGFUSE_TRACE_ID"] = langfuse_trace_id  # For SDK subprocess
                debug("insights_runner", "Captured trace_id for SDK and storage", trace_id=langfuse_trace_id)

        # Setup MCP servers for ROI tracking (if tools are available)
        mcp_servers = {}
        roi_tools_enabled = False

        if is_tools_available():
            try:
                insights_roi_dir = project_path / ".auto-claude" / "insights"
                insights_roi_dir.mkdir(parents=True, exist_ok=True)

                auto_claude_mcp = create_auto_claude_mcp_server(insights_roi_dir, project_path)
                if auto_claude_mcp:
                    mcp_servers["auto-claude"] = auto_claude_mcp
                    roi_tools_enabled = True
                    debug("insights_runner", "Auto-claude MCP server enabled for ROI tracking")
            except Exception as e:
                debug_error("insights_runner", f"Failed to create ROI MCP server: {e}")
                # Continue without ROI tools
        else:
            debug("insights_runner", "ROI tools not available (SDK tools not installed)")

        # Build allowed tools list
        allowed_tools = ["Read", "Glob", "Grep"]
        if roi_tools_enabled:
            allowed_tools.extend(ROI_TOOLS)
            allowed_tools.extend(ARTIFACT_TOOLS)

        client = ClaudeSDKClient(
            options=ClaudeAgentOptions(
                model=resolve_model_id(model),  # Resolve via API Profile if configured
                system_prompt=system_prompt,
                allowed_tools=allowed_tools,
                mcp_servers=mcp_servers if mcp_servers else None,  # Only pass if we have servers
                # Removed setting_sources to avoid loading skills/MCP servers
                # that can cause initialization timeouts
                max_turns=30,  # Allow sufficient turns for codebase exploration
                cwd=str(project_path),
                env=sdk_env,  # Pass ANTHROPIC_BASE_URL, Azure Foundry vars, LANGFUSE_TRACE_ID
            )
        )

        # Use async context manager pattern
        async with client:
            # Send the query
            await client.query(full_prompt)

            # Stream the response
            response_text = ""
            current_tool = None
            tools_used_count = 0  # Track number of tools used for ROI calculation

            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                debug_detailed("insights_runner", "Received message", msg_type=msg_type)

                # Track message usage if tracker is available
                if tracker and msg_type == "AssistantMessage":
                    try:
                        await tracker.track_message(msg)
                    except Exception as e:
                        debug_error("insights_runner", f"Failed to track message: {e}")

                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        block_type = type(block).__name__
                        debug_detailed(
                            "insights_runner", "Processing block", block_type=block_type
                        )
                        if block_type == "TextBlock" and hasattr(block, "text"):
                            text = block.text
                            debug_detailed(
                                "insights_runner", "Text block", text_length=len(text)
                            )
                            # Print text with newline to ensure proper line separation for parsing
                            print(text, flush=True)
                            response_text += text
                        elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                            # Emit tool start marker for UI feedback
                            tool_name = block.name
                            tool_input = ""

                            # Extract a brief description of what the tool is doing
                            if hasattr(block, "input") and block.input:
                                inp = block.input
                                if isinstance(inp, dict):
                                    if "pattern" in inp:
                                        tool_input = f"pattern: {inp['pattern']}"
                                    elif "file_path" in inp:
                                        # Shorten path for display
                                        fp = inp["file_path"]
                                        if len(fp) > 50:
                                            fp = "..." + fp[-47:]
                                        tool_input = fp
                                    elif "path" in inp:
                                        tool_input = inp["path"]

                            current_tool = tool_name
                            tools_used_count += 1  # Increment for ROI calculation
                            print(
                                f"__TOOL_START__:{json.dumps({'name': tool_name, 'input': tool_input})}",
                                flush=True,
                            )

                elif msg_type == "ToolResult":
                    # Tool finished executing
                    if current_tool:
                        print(
                            f"__TOOL_END__:{json.dumps({'name': current_tool})}",
                            flush=True,
                        )
                        current_tool = None

                # Track result message for final totals
                if msg_type == "ResultMessage":
                    if tracker:
                        try:
                            await tracker.track_message(msg)
                        except Exception as e:
                            debug_error("insights_runner", f"Failed to track result: {e}")

                    # Log to Langfuse if enabled
                    if use_langfuse and hasattr(msg, "usage") and msg.usage:
                        try:
                            usage = msg.usage
                            if isinstance(usage, dict):
                                input_tokens = usage.get("input_tokens", 0)
                                output_tokens = usage.get("output_tokens", 0)
                            else:
                                input_tokens = getattr(usage, "input_tokens", 0)
                                output_tokens = getattr(usage, "output_tokens", 0)

                            log_generation_in_current_trace(
                                name="insights-generation",
                                model=model,
                                input_data=message[:500] + "..." if len(message) > 500 else message,
                                output_data=response_text[:1000] + "..." if len(response_text) > 1000 else response_text,
                                usage={
                                    "input": input_tokens,
                                    "output": output_tokens,
                                    "total": input_tokens + output_tokens,
                                },
                                metadata={"thinking_level": thinking_level},
                            )
                            debug("insights_runner", "Logged generation to Langfuse")
                        except Exception as e:
                            debug_error("insights_runner", f"Failed to log to Langfuse: {e}")

            # Ensure we have a newline at the end
            if response_text and not response_text.endswith("\n"):
                print()

            debug(
                "insights_runner",
                "Response complete",
                response_length=len(response_text),
            )

            # Finalize tracking
            if tracker:
                try:
                    await tracker.finalize()
                    totals = tracker.get_totals()
                    debug(
                        "insights_runner",
                        "Feature tracking finalized",
                        total_cost_usd=totals.get("total_cost_usd", 0),
                        total_input_tokens=totals.get("total_input_tokens", 0),
                        total_output_tokens=totals.get("total_output_tokens", 0),
                    )
                except Exception as e:
                    debug_error("insights_runner", f"Failed to finalize tracking: {e}")

            # NOTE: langfuse_trace_id was captured earlier when creating the trace context
            # and passed to the SDK subprocess via LANGFUSE_TRACE_ID env var
            # This ensures MCP tools can link artifacts to the correct trace

            # Publish ROI metrics BEFORE closing the trace (so scores attach to trace)
            if ROI_PUBLISHER_AVAILABLE:
                try:
                    # Count task suggestions in response
                    tasks_suggested = response_text.count("__TASK_SUGGESTION__")

                    # Get token usage from tracker or estimate
                    total_tokens = 0
                    total_cost = 0.0
                    if tracker:
                        totals = tracker.get_totals()
                        total_tokens = totals.get("total_input_tokens", 0) + totals.get("total_output_tokens", 0)
                        total_cost = totals.get("total_cost_usd", 0)
                    else:
                        # Estimate if no tracker
                        total_tokens = len(response_text) // 4  # ~4 chars per token
                        total_cost = (total_tokens / 1000) * 0.003

                    # Count tool uses (files explored) - use tracked counter
                    files_explored = tools_used_count

                    # Extract additional value metrics from response WITH TRACEABILITY
                    response_lower = response_text.lower()
                    import re

                    # Detect diagrams (mermaid, ascii art, etc.) - comprehensive detection
                    mermaid_types = ["mermaid", "flowchart", "sequenceDiagram", "graph", "classDiagram", "stateDiagram", "erDiagram", "gantt", "pie", "journey"]
                    diagrams_generated = sum(
                        response_text.lower().count(f"```{dtype.lower()}") for dtype in mermaid_types
                    ) + response_text.count("```ascii") + response_text.count("```diagram")

                    diagram_types = []
                    for dtype in mermaid_types:
                        if f"```{dtype.lower()}" in response_text.lower() or f"```{dtype}" in response_text:
                            diagram_types.append("mermaid")
                            break
                    if "```ascii" in response_text:
                        diagram_types.append("ascii")
                    if "```diagram" in response_text:
                        diagram_types.append("diagram")

                    # Detect security insights WITH CONTEXT
                    security_keywords = ["security", "vulnerability", "xss", "sql injection", "csrf", "authentication", "authorization"]
                    security_matches = [kw for kw in security_keywords if kw in response_lower]
                    security_insights = len(security_matches)

                    # Detect recommendations WITH CONTEXT - extract FULL PARAGRAPHS
                    recommendation_patterns = ["recommend", "suggestion", "should consider", "best practice", "improvement"]
                    recommendations_found = []

                    # Split by paragraphs (double newlines or markdown sections)
                    paragraphs = re.split(r'\n\n+|\n(?=#+\s)', response_text)
                    paragraphs = [p.strip() for p in paragraphs if p.strip()]

                    # Also keep sentences for fine-grained extraction
                    sentences = re.split(r'(?<=[.!?])\s+', response_text)
                    sentences = [s.strip() for s in sentences if s.strip()]

                    for para in paragraphs:
                        para_lower = para.lower()
                        for pattern in recommendation_patterns:
                            if pattern in para_lower and len(para) > 50:
                                recommendations_found.append(para)
                                break
                    recommendations_count = len(recommendations_found)

                    # Detect code explanations (code blocks in response)
                    code_explanations = response_text.count("```")

                    # Load ARTIFACTS from local storage (created by MCP tools during session)
                    # This avoids duplicating artifacts that were already created via tools
                    artifacts = []
                    langfuse_refs = []

                    if ARTIFACT_STORAGE_AVAILABLE and project_path and langfuse_trace_id:
                        try:
                            from analytics.artifact_storage import list_artifacts
                            # Load artifacts created during this trace
                            stored_artifacts = list_artifacts(
                                project_dir=project_path,
                                trace_id=langfuse_trace_id,
                            )
                            if stored_artifacts:
                                artifacts = stored_artifacts
                                debug("insights_runner", f"Loaded {len(artifacts)} artifacts from storage for trace {langfuse_trace_id[:8]}...")

                                # Create Langfuse refs for stored artifacts
                                for artifact in artifacts:
                                    artifact_id = artifact.get("id", "")
                                    storage_path = str(_get_artifacts_dir(project_path) / datetime.now().strftime("%Y-%m-%d") / f"{artifact_id}.json")
                                    ref = create_langfuse_reference(artifact, artifact_id, storage_path)
                                    langfuse_refs.append(ref)
                        except Exception as e:
                            debug_error("insights_runner", f"Failed to load artifacts from storage: {e}")

                    # NO REGEX FALLBACK - Artifacts MUST come from MCP tools
                    # The agent is instructed to use create_artifact, create_diagram, etc.
                    # If no artifacts were created via tools, we simply have no artifacts
                    if not artifacts:
                        debug("insights_runner", "No artifacts created via MCP tools - agent should use create_artifact/create_diagram tools")
                    else:
                        # Artifacts already loaded from storage, create Langfuse refs if not done
                        if not langfuse_refs and ARTIFACT_STORAGE_AVAILABLE:
                            for artifact in artifacts:
                                langfuse_refs.append(artifact)  # Full content already stored

                    # Calculate value attribution from REAL artifact values (not regex estimates)
                    # Group artifacts by type and sum their actual values
                    artifact_values_by_type = {}
                    for artifact in artifacts:
                        art_type = artifact.get("type", "unknown")
                        art_value = artifact.get("value_usd", 0)
                        if art_type not in artifact_values_by_type:
                            artifact_values_by_type[art_type] = {"count": 0, "total_value": 0, "items": []}
                        artifact_values_by_type[art_type]["count"] += 1
                        artifact_values_by_type[art_type]["total_value"] += art_value
                        artifact_values_by_type[art_type]["items"].append({
                            "id": artifact.get("id"),
                            "value": art_value,
                            "description": artifact.get("description", "")[:100],
                        })

                    # Calculate diagram values from stored artifacts (overrides regex count)
                    diagram_info = artifact_values_by_type.get("diagram", {"count": 0, "total_value": 0})

                    # Calculate security values from stored artifacts
                    security_info = artifact_values_by_type.get("security_finding", {"count": 0, "total_value": 0})

                    # Calculate recommendation values from stored artifacts
                    recommendation_info = artifact_values_by_type.get("recommendation", {"count": 0, "total_value": 0})

                    # Calculate code example values from stored artifacts
                    code_info = artifact_values_by_type.get("code_example", {"count": 0, "total_value": 0})

                    # Build value attribution details for traceability using REAL artifact values
                    # IMPORTANT: Only count values from REAL artifacts (MCP tools)
                    # Regex estimates are kept for debugging but don't contribute to total_value
                    # This ensures value_breakdown in UI aligns with actual artifacts list
                    value_attribution = {
                        "diagrams": {
                            "count": diagram_info["count"],  # Only count real artifacts
                            "regex_detected": diagrams_generated,  # Keep for debugging
                            "types": diagram_types,
                            "value_per_item": 150,  # Base value, actual may vary
                            "total_value": diagram_info["total_value"],  # Only real artifact values
                            "from_artifacts": diagram_info["count"] > 0,
                        },
                        "security_insights": {
                            "count": security_info["count"],  # Only count real artifacts
                            "regex_detected": security_insights,  # Keep for debugging
                            "keywords_found": security_matches,
                            "value_per_item": 200,
                            "total_value": security_info["total_value"],  # Only real artifact values
                            "from_artifacts": security_info["count"] > 0,
                        },
                        "recommendations": {
                            "count": recommendation_info["count"],  # Only count real artifacts
                            "regex_detected": recommendations_count,  # Keep for debugging
                            "samples": recommendations_found[:5],
                            "value_per_item": 50,
                            "total_value": recommendation_info["total_value"],  # Only real artifact values
                            "from_artifacts": recommendation_info["count"] > 0,
                        },
                        "code_explanations": {
                            "count": code_info["count"],  # Only count real artifacts
                            "regex_detected": code_explanations,  # Keep for debugging
                            "value_per_item": 25,
                            "total_value": code_info["total_value"],  # Only real artifact values
                            "from_artifacts": code_info["count"] > 0,
                        },
                        "files_explored": {
                            "count": files_explored,
                            "value_contribution": "knowledge base calculation",
                        },
                        "artifacts": langfuse_refs,  # FULL content - no truncation
                        "total_artifacts": len(langfuse_refs),
                        "artifact_values_by_type": artifact_values_by_type,  # Full breakdown for debugging
                    }

                    # Save value attribution to physical file for traceability
                    from datetime import datetime as dt
                    insights_dir = project_path / ".auto-claude" / "insights"
                    insights_dir.mkdir(parents=True, exist_ok=True)

                    # Create activity report file
                    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
                    activity_file = insights_dir / f"activity_{timestamp}.json"

                    activity_report = {
                        "timestamp": dt.now().isoformat(),
                        "trace_id": langfuse_trace_id,
                        "project_id": project_id,
                        "model": model,
                        "cost_usd": total_cost,
                        "tokens": total_tokens,
                        "value_attribution": value_attribution,
                        "total_value_usd": sum(
                            v.get("total_value", 0) for v in value_attribution.values()
                            if isinstance(v, dict) and "total_value" in v
                        ),
                        "query_summary": message[:200] + "..." if len(message) > 200 else message,
                        "response_summary": response_text[:500] + "..." if len(response_text) > 500 else response_text,
                    }

                    try:
                        with open(activity_file, "w") as f:
                            json.dump(activity_report, f, indent=2, default=str)
                        debug("insights_runner", f"Activity saved to {activity_file}")

                        # Update index file for easy lookup
                        index_file = insights_dir / "activities_index.json"
                        index_data = []
                        if index_file.exists():
                            try:
                                with open(index_file) as f:
                                    index_data = json.load(f)
                            except Exception:
                                index_data = []

                        index_data.append({
                            "file": activity_file.name,
                            "timestamp": activity_report["timestamp"],
                            "trace_id": langfuse_trace_id,
                            "total_value_usd": activity_report["total_value_usd"],
                            "cost_usd": total_cost,
                            "activities_detected": {
                                "diagrams": diagrams_generated,
                                "security_insights": security_insights,
                                "recommendations": recommendations_count,
                                "code_explanations": code_explanations,
                                "files_explored": files_explored,
                            }
                        })

                        with open(index_file, "w") as f:
                            json.dump(index_data, f, indent=2, default=str)

                    except Exception as e:
                        debug_error("insights_runner", f"Failed to save activity file: {e}")

                    # Use publish_feature_roi for richer metrics
                    from analytics.roi_publisher import publish_feature_roi

                    await publish_feature_roi(
                        feature_type="insights_chat",
                        project_id=project_id,
                        cost_usd=total_cost,
                        tokens=total_tokens,
                        model=model,
                        trace_id=langfuse_trace_id,  # Pass trace_id to attach scores to same trace
                        metrics={
                            "messages_exchanged": 1,
                            "tasks_suggested": tasks_suggested,
                            "tasks_accepted": 0,
                            "files_explored": files_explored,
                            # Additional value metrics (detected from response)
                            "diagrams_generated": diagrams_generated,
                            "security_insights": security_insights,
                            "recommendations_count": recommendations_count,
                            "code_explanations": code_explanations,
                        },
                    )

                    debug(
                        "insights_runner",
                        "ROI published",
                        trace_id=langfuse_trace_id,
                        tasks=tasks_suggested,
                        files=files_explored,
                        diagrams=diagrams_generated,
                        security=security_insights,
                        recommendations=recommendations_count,
                    )
                except Exception as e:
                    debug_error("insights_runner", f"Failed to publish ROI: {e}")

            # Finalize Langfuse trace (AFTER publishing ROI scores)
            if trace_ctx:
                try:
                    # Set trace output before exiting - include value attribution for traceability
                    if langfuse_ctx_obj:
                        # FULL response - NO truncation
                        # Include value attribution if ROI was published
                        output_data = {"response": response_text}
                        # Check if value_attribution exists (defined in ROI_PUBLISHER_AVAILABLE block)
                        try:
                            if value_attribution:
                                output_data["value_attribution"] = value_attribution
                                output_data["total_calculated_value"] = sum(
                                    v.get("total_value", 0) for v in value_attribution.values()
                                    if isinstance(v, dict) and "total_value" in v
                                )
                        except NameError:
                            # value_attribution not defined if ROI publishing was skipped
                            pass
                        langfuse_ctx_obj.set_output(output_data)
                    trace_ctx.__exit__(None, None, None)
                    flush_langfuse()
                    debug("insights_runner", "Langfuse trace finalized")
                except Exception as e:
                    debug_error("insights_runner", f"Failed to finalize Langfuse trace: {e}")
                # NOTE: trace_context now handles cleanup of trace_id in thread-local storage

    except Exception as e:
        print(f"Error using Claude SDK: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        # Still try to finalize tracking on error
        if tracker:
            try:
                await tracker.finalize()
            except Exception:
                pass
        # Still try to finalize Langfuse trace on error
        if use_langfuse and trace_ctx:
            try:
                trace_ctx.__exit__(None, None, None)
                flush_langfuse()
            except Exception:
                pass
        run_simple(project_dir, message, history)


def run_simple(project_dir: str, message: str, history: list) -> None:
    """Simple fallback mode without SDK - uses subprocess to call claude CLI."""
    import subprocess

    system_prompt = build_system_prompt(project_dir)

    # Build conversation context
    conversation_context = ""
    for msg in history[:-1]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        conversation_context += f"\n{role}: {msg['content']}\n"

    # Create the full prompt
    full_prompt = f"""{system_prompt}

Previous conversation:
{conversation_context}

User: {message}
Assistant:"""

    try:
        # Try to use claude CLI with --print for simple output
        result = subprocess.run(
            ["claude", "--print", "-p", full_prompt],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=120,
        )

        if result.returncode == 0:
            print(result.stdout)
        else:
            # Fallback response if claude CLI fails
            print(
                f"I apologize, but I encountered an issue processing your request. "
                f"Please ensure Claude CLI is properly configured.\n\n"
                f"Your question was: {message}\n\n"
                f"Based on the project context available, I can help you with:\n"
                f"- Understanding the codebase structure\n"
                f"- Suggesting improvements\n"
                f"- Planning new features\n\n"
                f"Please try again or check your Claude CLI configuration."
            )

    except subprocess.TimeoutExpired:
        print("Request timed out. Please try a shorter query.")
    except FileNotFoundError:
        print("Claude CLI not found. Please ensure it is installed and in your PATH.")
    except Exception as e:
        print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Insights AI Chat Runner")
    parser.add_argument("--project-dir", required=True, help="Project directory path")
    parser.add_argument("--message", required=True, help="User message")
    parser.add_argument("--history", default="[]", help="JSON conversation history")
    parser.add_argument(
        "--history-file", help="Path to JSON file containing conversation history"
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        help="Model to use (haiku, sonnet, opus, or full model ID)",
    )
    parser.add_argument(
        "--thinking-level",
        default="medium",
        choices=["none", "low", "medium", "high", "ultrathink"],
        help="Thinking level for extended reasoning (default: medium)",
    )
    args = parser.parse_args()

    debug_section("insights_runner", "Starting Insights Chat")

    project_dir = args.project_dir
    user_message = args.message
    model = args.model
    thinking_level = args.thinking_level

    debug(
        "insights_runner",
        "Arguments",
        project_dir=project_dir,
        message_length=len(user_message),
        model=model,
        thinking_level=thinking_level,
    )

    # Load history from file if provided, otherwise parse inline JSON
    try:
        if args.history_file:
            debug(
                "insights_runner", "Loading history from file", file=args.history_file
            )
            with open(args.history_file, encoding="utf-8") as f:
                history = json.load(f)
            debug_detailed(
                "insights_runner",
                "Loaded history from file",
                history_length=len(history),
            )
        else:
            history = json.loads(args.history)
            debug_detailed(
                "insights_runner", "Parsed inline history", history_length=len(history)
            )
    except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
        debug_error("insights_runner", f"Failed to load history: {e}")
        history = []

    # Run the async SDK function
    debug("insights_runner", "Running SDK query")
    asyncio.run(run_with_sdk(project_dir, user_message, history, model, thinking_level))
    debug_success("insights_runner", "Query completed")


if __name__ == "__main__":
    main()
