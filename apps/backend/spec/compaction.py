"""
Conversation Compaction Module
==============================

Summarizes phase outputs to maintain continuity between phases while
reducing token usage. After each phase completes, key findings are
summarized and passed as context to subsequent phases.
"""

from pathlib import Path

from core.auth import require_auth_token
from core.simple_client import create_simple_client

# Langfuse integration for tracing
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        trace_context,
        log_generation_in_current_trace,
        is_langfuse_ready,
        flush_langfuse,
    )
    LANGFUSE_AVAILABLE = True
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    trace_context = None
    _langfuse_init_result = False

# Legacy analytics tracking (backwards compatibility)
try:
    from analytics import (
        create_feature_tracker,
        FEATURE_INSIGHTS,
        is_tracking_enabled,
    )
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False


async def summarize_phase_output(
    phase_name: str,
    phase_output: str,
    model: str = "claude-sonnet-4-5-20250929",
    target_words: int = 500,
    project_dir: Path | None = None,
) -> tuple[str, str | None]:
    """
    Summarize phase output to a concise summary for subsequent phases.

    Uses Sonnet for cost efficiency since this is a simple summarization task.

    Args:
        phase_name: Name of the completed phase (e.g., 'discovery', 'requirements')
        phase_output: Full output content from the phase (file contents, decisions)
        model: Model to use for summarization (defaults to Sonnet for efficiency)
        target_words: Target summary length in words (~500-1000 recommended)
        project_dir: Project directory for analytics tracking (optional)

    Returns:
        Tuple of (summary_text, langfuse_trace_id)
    """
    # Validate auth token
    require_auth_token()

    # Initialize tracker
    tracker = None
    if TRACKING_AVAILABLE and is_tracking_enabled():
        try:
            project_id = project_dir.name if project_dir else Path.cwd().name
            db_path = str((project_dir or Path.cwd()) / ".auto-claude" / "analytics.db")
            tracker = create_feature_tracker(
                project_id=project_id,
                feature_type=FEATURE_INSIGHTS,
                db_path=db_path,
                metadata={"model": model, "operation": "phase_compaction", "phase": phase_name}
            )
        except Exception:
            tracker = None

    # Limit input size to avoid token overflow
    max_input_chars = 15000
    truncated_output = phase_output[:max_input_chars]
    if len(phase_output) > max_input_chars:
        truncated_output += "\n\n[... output truncated for summarization ...]"

    prompt = f"""Summarize the key findings from the "{phase_name}" phase in {target_words} words or less.

Focus on extracting ONLY the most critical information that subsequent phases need:
- Key decisions made and their rationale
- Critical files, components, or patterns identified
- Important constraints or requirements discovered
- Actionable insights for implementation

Be concise and use bullet points. Skip boilerplate and meta-commentary.

## Phase Output:
{truncated_output}

## Summary:
"""

    client = create_simple_client(
        agent_type="spec_compaction",
        model=model,
        system_prompt=(
            "You are a concise technical summarizer. Extract only the most "
            "critical information from phase outputs. Use bullet points. "
            "Focus on decisions, discoveries, and actionable insights."
        ),
    )

    # Check Langfuse availability
    use_langfuse = LANGFUSE_AVAILABLE and is_langfuse_ready()
    project_id = project_dir.name if project_dir else Path.cwd().name
    trace_name = f"compaction-{project_id}-{phase_name}"

    # Create Langfuse trace context if available
    trace_ctx = None
    langfuse_ctx_obj = None
    langfuse_trace_id = None
    if use_langfuse and trace_context:
        # Truncate prompt for trace input
        trace_input = prompt[:2000] + "..." if len(prompt) > 2000 else prompt
        trace_ctx = trace_context(
            name=trace_name,
            project_id=project_id,  # Required for data isolation filtering
            agent_type="phase_compaction",
            metadata={
                "phase_name": phase_name,
                "model": model,
                "target_words": target_words,
            },
            tags=["compaction", f"phase:{phase_name}"],
            input_data={"prompt": trace_input, "phase_name": phase_name},
        )
        langfuse_ctx_obj = trace_ctx.__enter__()
        if langfuse_ctx_obj:
            langfuse_trace_id = langfuse_ctx_obj.trace_id

    try:
        # Start tracking session
        if tracker:
            try:
                await tracker.start_session()
            except Exception:
                pass

        async with client:
            await client.query(prompt)
            response_text = ""
            total_input_tokens = 0
            total_output_tokens = 0

            async for msg in client.receive_response():
                msg_type = type(msg).__name__

                # Track message for analytics
                if tracker and msg_type in ("AssistantMessage", "ResultMessage"):
                    try:
                        await tracker.track_message(msg)
                    except Exception:
                        pass

                if hasattr(msg, "content"):
                    for block in msg.content:
                        if hasattr(block, "text"):
                            response_text += block.text

                # Extract usage for Langfuse
                if msg_type == "ResultMessage" and hasattr(msg, "usage") and msg.usage:
                    usage = msg.usage
                    if hasattr(usage, "input_tokens"):
                        total_input_tokens = usage.input_tokens
                    if hasattr(usage, "output_tokens"):
                        total_output_tokens = usage.output_tokens

            # Log to Langfuse if enabled
            if use_langfuse and LANGFUSE_AVAILABLE:
                try:
                    log_generation_in_current_trace(
                        name=f"compaction-{phase_name}",
                        model=model,
                        input_data=prompt[:500] + "..." if len(prompt) > 500 else prompt,
                        output_data=response_text[:1000] + "..." if len(response_text) > 1000 else response_text,
                        usage={
                            "input": total_input_tokens,
                            "output": total_output_tokens,
                            "total": total_input_tokens + total_output_tokens,
                        },
                        metadata={"phase_name": phase_name},
                    )
                except Exception:
                    pass

            # Finalize tracking
            if tracker:
                try:
                    await tracker.finalize()
                except Exception:
                    pass

            # Finalize Langfuse trace
            if trace_ctx:
                try:
                    # Set trace output before exiting
                    if langfuse_ctx_obj:
                        # FULL content - NO truncation (Zero Truncation Policy)
                        langfuse_ctx_obj.set_output({"response": response_text})
                    trace_ctx.__exit__(None, None, None)
                    flush_langfuse()
                except Exception:
                    pass

            return response_text.strip(), langfuse_trace_id
    except Exception as e:
        # Finalize tracking on error
        if tracker:
            try:
                await tracker.finalize()
            except Exception:
                pass
        # Finalize Langfuse trace on error
        if trace_ctx:
            try:
                trace_ctx.__exit__(None, None, None)
                flush_langfuse()
            except Exception:
                pass
        # Fallback: return truncated raw output on error
        # This ensures we don't block the pipeline if summarization fails
        fallback = phase_output[:2000]
        if len(phase_output) > 2000:
            fallback += "\n\n[... truncated ...]"
        return f"[Summarization failed: {e}]\n\n{fallback}", langfuse_trace_id


def format_phase_summaries(summaries: dict[str, str]) -> str:
    """
    Format accumulated phase summaries for injection into agent context.

    Args:
        summaries: Dict mapping phase names to their summaries

    Returns:
        Formatted string suitable for agent context injection
    """
    if not summaries:
        return ""

    formatted_parts = ["## Context from Previous Phases\n"]
    for phase_name, summary in summaries.items():
        formatted_parts.append(
            f"### {phase_name.replace('_', ' ').title()}\n{summary}\n"
        )

    return "\n".join(formatted_parts)


def gather_phase_outputs(spec_dir: Path, phase_name: str) -> str:
    """
    Gather output files from a completed phase for summarization.

    Args:
        spec_dir: Path to the spec directory
        phase_name: Name of the completed phase

    Returns:
        Concatenated content of phase output files
    """
    outputs = []

    # Map phases to their expected output files
    phase_outputs: dict[str, list[str]] = {
        "discovery": ["context.json"],
        "requirements": ["requirements.json"],
        "research": ["research.json"],
        "context": ["context.json"],
        "quick_spec": ["spec.md"],
        "spec_writing": ["spec.md"],
        "self_critique": ["spec.md", "critique_notes.md"],
        "planning": ["implementation_plan.json"],
        "validation": [],  # No output files to summarize
    }

    output_files = phase_outputs.get(phase_name, [])

    for filename in output_files:
        file_path = spec_dir / filename
        if file_path.exists():
            try:
                content = file_path.read_text()
                # Limit individual file size
                if len(content) > 10000:
                    content = content[:10000] + "\n\n[... file truncated ...]"
                outputs.append(f"**{filename}**:\n```\n{content}\n```")
            except Exception:
                pass  # Skip files that can't be read

    return "\n\n".join(outputs) if outputs else ""
