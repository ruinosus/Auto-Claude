"""
AI-powered idea generation.

Uses Claude agents to generate ideas of different types:
- Code improvements
- UI/UX improvements
- Documentation gaps
- Security hardening
- Performance optimizations
- Code quality
"""

import sys
from pathlib import Path
from typing import Optional

# Add auto-claude to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client import create_client
from phase_config import get_thinking_budget
from ui import print_status
from debug import debug, debug_error

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
    # Initialize Langfuse early (idempotent)
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    trace_context = None
    _langfuse_init_result = False

# Import legacy feature tracker for token tracking (backwards compatibility)
try:
    from analytics import (
        create_feature_tracker,
        FEATURE_IDEATION,
        is_tracking_enabled,
    )
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False

# Ideation types
IDEATION_TYPES = [
    "code_improvements",
    "ui_ux_improvements",
    "documentation_gaps",
    "security_hardening",
    "performance_optimizations",
    "code_quality",
]

IDEATION_TYPE_LABELS = {
    "code_improvements": "Code Improvements",
    "ui_ux_improvements": "UI/UX Improvements",
    "documentation_gaps": "Documentation Gaps",
    "security_hardening": "Security Hardening",
    "performance_optimizations": "Performance Optimizations",
    "code_quality": "Code Quality & Refactoring",
}

IDEATION_TYPE_PROMPTS = {
    "code_improvements": "ideation_code_improvements.md",
    "ui_ux_improvements": "ideation_ui_ux.md",
    "documentation_gaps": "ideation_documentation.md",
    "security_hardening": "ideation_security.md",
    "performance_optimizations": "ideation_performance.md",
    "code_quality": "ideation_code_quality.md",
}


class IdeationGenerator:
    """Generates ideas using AI agents."""

    def __init__(
        self,
        project_dir: Path,
        output_dir: Path,
        model: str = "claude-opus-4-5-20251101",
        thinking_level: str = "medium",
        max_ideas_per_type: int = 5,
    ):
        self.project_dir = Path(project_dir)
        self.output_dir = Path(output_dir)
        self.model = model
        self.thinking_level = thinking_level
        self.thinking_budget = get_thinking_budget(thinking_level)
        self.max_ideas_per_type = max_ideas_per_type
        self.prompts_dir = Path(__file__).parent.parent / "prompts"

        # Generate a project ID from the project directory
        self.project_id = self.project_dir.name

        # Check Langfuse availability
        self.langfuse_enabled = LANGFUSE_AVAILABLE and is_langfuse_ready()
        debug(
            "ideation_generator",
            "Langfuse integration status",
            langfuse_available=LANGFUSE_AVAILABLE,
            langfuse_ready=self.langfuse_enabled,
        )

        # Legacy feature tracker for token usage (backwards compatibility)
        self.tracker = None
        if TRACKING_AVAILABLE and is_tracking_enabled():
            db_path = str(self.project_dir / ".auto-claude" / "analytics.db")
            self.tracker = create_feature_tracker(
                project_id=self.project_id,
                feature_type=FEATURE_IDEATION if TRACKING_AVAILABLE else "ideation",
                db_path=db_path,
                metadata={"model": self.model, "thinking_level": self.thinking_level}
            )
            debug("ideation_generator", "Legacy feature tracker initialized", project_id=self.project_id)

    async def run_agent(
        self,
        prompt_file: str,
        additional_context: str = "",
    ) -> tuple[bool, str]:
        """Run an agent with the given prompt."""
        prompt_path = self.prompts_dir / prompt_file

        if not prompt_path.exists():
            return False, f"Prompt not found: {prompt_path}"

        # Load prompt
        prompt = prompt_path.read_text()

        # Add context
        prompt += f"\n\n---\n\n**Output Directory**: {self.output_dir}\n"
        prompt += f"**Project Directory**: {self.project_dir}\n"
        prompt += f"**Max Ideas**: {self.max_ideas_per_type}\n"

        if additional_context:
            prompt += f"\n{additional_context}\n"

        # Create client with thinking budget
        client = create_client(
            self.project_dir,
            self.output_dir,
            self.model,
            max_thinking_tokens=self.thinking_budget,
        )

        # Start legacy tracking session if tracker is available
        if self.tracker:
            try:
                self.tracker.update_metadata("prompt_file", prompt_file)
                await self.tracker.start_session()
                debug("ideation_generator", "Legacy feature tracking session started")
            except Exception as e:
                debug_error("ideation_generator", f"Failed to start tracking session: {e}")

        # Derive ideation type from prompt file name
        ideation_type = prompt_file.replace(".md", "").replace("ideation_", "")
        trace_name = f"ideation-{self.project_id}-{ideation_type}"

        # Create Langfuse trace context if available
        # IMPORTANT: project_id MUST be passed as parameter (not in metadata) for data isolation
        trace_ctx = None
        langfuse_ctx_obj = None
        if self.langfuse_enabled and trace_context:
            # Truncate prompt for trace input
            trace_input = prompt[:2000] + "..." if len(prompt) > 2000 else prompt
            trace_ctx = trace_context(
                name=trace_name,
                project_id=self.project_id,  # Required for data isolation filtering
                agent_type=f"ideation_{ideation_type}",
                metadata={
                    "prompt_file": prompt_file,
                    "model": self.model,
                    "thinking_level": self.thinking_level,
                    "max_ideas": self.max_ideas_per_type,
                },
                tags=["ideation", f"type:{ideation_type}"],
                input_data={"prompt": trace_input, "ideation_type": ideation_type},
            )
            langfuse_ctx_obj = trace_ctx.__enter__()
            if langfuse_ctx_obj:
                debug("ideation_generator", f"Langfuse trace created: {trace_name}, ctx={langfuse_ctx_obj}")
            else:
                debug_error("ideation_generator", f"Langfuse trace context is None for: {trace_name}")

        try:
            async with client:
                await client.query(prompt)

                response_text = ""
                total_input_tokens = 0
                total_output_tokens = 0

                async for msg in client.receive_response():
                    msg_type = type(msg).__name__

                    # Track message usage if tracker is available
                    if self.tracker and msg_type == "AssistantMessage":
                        try:
                            await self.tracker.track_message(msg)
                        except Exception as e:
                            debug_error("ideation_generator", f"Failed to track message: {e}")

                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            block_type = type(block).__name__
                            if block_type == "TextBlock" and hasattr(block, "text"):
                                response_text += block.text
                                print(block.text, end="", flush=True)
                            elif block_type == "ToolUseBlock" and hasattr(
                                block, "name"
                            ):
                                print(f"\n[Tool: {block.name}]", flush=True)

                    # Track result message for final totals
                    if msg_type == "ResultMessage":
                        if self.tracker:
                            try:
                                await self.tracker.track_message(msg)
                            except Exception as e:
                                debug_error("ideation_generator", f"Failed to track result: {e}")

                        # Extract usage for Langfuse
                        if hasattr(msg, "usage") and msg.usage:
                            usage = msg.usage
                            if hasattr(usage, "input_tokens"):
                                total_input_tokens = usage.input_tokens
                            if hasattr(usage, "output_tokens"):
                                total_output_tokens = usage.output_tokens

                print()

                # Log to Langfuse if enabled
                if self.langfuse_enabled and LANGFUSE_AVAILABLE:
                    debug(
                        "ideation_generator",
                        "Attempting to log generation to Langfuse",
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                        langfuse_ctx=langfuse_ctx_obj,
                    )
                    try:
                        result = log_generation_in_current_trace(
                            name=f"ideation-{ideation_type}",
                            model=self.model,
                            input_data=prompt[:500] + "..." if len(prompt) > 500 else prompt,
                            output_data=response_text[:1000] + "..." if len(response_text) > 1000 else response_text,
                            usage={
                                "input": total_input_tokens,
                                "output": total_output_tokens,
                                "total": total_input_tokens + total_output_tokens,
                            },
                            metadata={"prompt_file": prompt_file},
                        )
                        if result:
                            debug("ideation_generator", "Logged generation to Langfuse successfully", gen=str(result))
                        else:
                            debug_error("ideation_generator", "log_generation_in_current_trace returned None")
                    except Exception as e:
                        debug_error("ideation_generator", f"Failed to log to Langfuse: {e}")

                # Finalize legacy tracking
                if self.tracker:
                    try:
                        await self.tracker.finalize()
                        totals = self.tracker.get_totals()
                        debug(
                            "ideation_generator",
                            "Legacy feature tracking finalized",
                            total_cost_usd=totals.get("total_cost_usd", 0),
                            total_input_tokens=totals.get("total_input_tokens", 0),
                            total_output_tokens=totals.get("total_output_tokens", 0),
                        )
                    except Exception as e:
                        debug_error("ideation_generator", f"Failed to finalize tracking: {e}")

                # Finalize Langfuse trace
                if trace_ctx:
                    try:
                        # Set trace output before closing
                        if langfuse_ctx_obj:
                            # FULL content - NO truncation (Zero Truncation Policy)
                            langfuse_ctx_obj.set_output({
                                "response": response_text,
                                "total_input_tokens": total_input_tokens,
                                "total_output_tokens": total_output_tokens,
                            })
                        trace_ctx.__exit__(None, None, None)
                        flush_langfuse()
                        debug("ideation_generator", "Langfuse trace finalized")
                    except Exception as e:
                        debug_error("ideation_generator", f"Failed to finalize Langfuse: {e}")

                return True, response_text

        except Exception as e:
            # Still try to finalize tracking on error
            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass
            # Still try to finalize Langfuse trace on error
            if trace_ctx:
                try:
                    if langfuse_ctx_obj:
                        langfuse_ctx_obj.set_output({"error": str(e)})
                    trace_ctx.__exit__(None, None, None)
                    flush_langfuse()
                except Exception:
                    pass
            return False, str(e)

    async def run_recovery_agent(
        self,
        output_file: Path,
        ideation_type: str,
        error: str,
        current_content: str,
    ) -> bool:
        """Run a recovery agent to fix validation errors in the output file."""

        # Truncate content if too long
        max_content_length = 8000
        if len(current_content) > max_content_length:
            current_content = current_content[:max_content_length] + "\n... (truncated)"

        recovery_prompt = f"""# Ideation Output Recovery

The ideation output file failed validation. Your task is to fix it.

## Error
{error}

## Expected Format
The output file must be valid JSON with the following structure:

```json
{{
  "{ideation_type}": [
    {{
      "id": "...",
      "type": "{ideation_type}",
      "title": "...",
      "description": "...",
      ... other fields ...
    }}
  ]
}}
```

**CRITICAL**: The top-level key MUST be `"{ideation_type}"` (not "ideas" or anything else).

## Current File Content
File: {output_file}

```json
{current_content}
```

## Your Task
1. Read the current file content above
2. Identify what's wrong based on the error message
3. Fix the JSON structure to match the expected format
4. Write the corrected content to {output_file}

Common fixes:
- If the key is "ideas", rename it to "{ideation_type}"
- If the JSON is invalid, fix the syntax errors
- If there are no ideas, ensure the array has at least one idea object

Write the fixed JSON to the file now.
"""

        client = create_client(
            self.project_dir,
            self.output_dir,
            self.model,
            max_thinking_tokens=self.thinking_budget,
        )

        # Start tracking session if tracker is available
        if self.tracker:
            try:
                self.tracker.update_metadata("recovery_type", ideation_type)
                await self.tracker.start_session()
            except Exception as e:
                debug_error("ideation_generator", f"Failed to start recovery tracking: {e}")

        try:
            async with client:
                await client.query(recovery_prompt)

                async for msg in client.receive_response():
                    msg_type = type(msg).__name__

                    # Track message usage if tracker is available
                    if self.tracker and msg_type == "AssistantMessage":
                        try:
                            await self.tracker.track_message(msg)
                        except Exception:
                            pass

                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            block_type = type(block).__name__
                            if block_type == "TextBlock" and hasattr(block, "text"):
                                print(block.text, end="", flush=True)
                            elif block_type == "ToolUseBlock" and hasattr(
                                block, "name"
                            ):
                                print(f"\n[Recovery Tool: {block.name}]", flush=True)

                    # Track result message for final totals
                    if self.tracker and msg_type == "ResultMessage":
                        try:
                            await self.tracker.track_message(msg)
                        except Exception:
                            pass

                print()

                # Finalize tracking
                if self.tracker:
                    try:
                        await self.tracker.finalize()
                    except Exception:
                        pass

                return True

        except Exception as e:
            print_status(f"Recovery agent error: {e}", "error")
            # Still try to finalize tracking on error
            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass
            return False

    def get_prompt_file(self, ideation_type: str) -> str | None:
        """Get the prompt file for a specific ideation type."""
        return IDEATION_TYPE_PROMPTS.get(ideation_type)

    def get_type_label(self, ideation_type: str) -> str:
        """Get the human-readable label for an ideation type."""
        return IDEATION_TYPE_LABELS.get(ideation_type, ideation_type)
