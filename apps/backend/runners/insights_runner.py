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
from debug import (
    debug,
    debug_detailed,
    debug_error,
    debug_section,
    debug_success,
)

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
    model: str = "claude-sonnet-4-5-20250929",
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
        client = ClaudeSDKClient(
            options=ClaudeAgentOptions(
                model=model,  # Use configured model
                system_prompt=system_prompt,
                allowed_tools=[
                    "Read",
                    "Glob",
                    "Grep",
                    "Skill",  # Enable Skills for insights generation
                ],
                # Load Skills from user and project directories
                setting_sources=["user", "project"],
                max_turns=30,  # Allow sufficient turns for codebase exploration
                cwd=str(project_path),
                env=sdk_env,  # Pass ANTHROPIC_BASE_URL, Azure Foundry vars, etc.
            )
        )

        # Create Langfuse trace context if available
        trace_ctx = None
        langfuse_ctx_obj = None
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

        # Use async context manager pattern
        async with client:
            # Send the query
            await client.query(full_prompt)

            # Stream the response
            response_text = ""
            current_tool = None

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

            # Finalize Langfuse trace
            if trace_ctx:
                try:
                    # Set trace output before exiting
                    if langfuse_ctx_obj:
                        trace_output = response_text[:3000] + "..." if len(response_text) > 3000 else response_text
                        langfuse_ctx_obj.set_output({"response": trace_output})
                    trace_ctx.__exit__(None, None, None)
                    flush_langfuse()
                    debug("insights_runner", "Langfuse trace finalized")
                except Exception as e:
                    debug_error("insights_runner", f"Failed to finalize Langfuse trace: {e}")

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
        default="claude-sonnet-4-5-20250929",
        help="Claude model ID (default: claude-sonnet-4-5-20250929)",
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
