"""
AI Resolver
===========

Core conflict resolution logic using AI.

This module provides the AIResolver class that coordinates the
resolution of conflicts using AI with minimal context.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any, Dict, List, Optional

from ..types import (
    ConflictRegion,
    ConflictSeverity,
    MergeDecision,
    MergeResult,
    MergeStrategy,
    TaskSnapshot,
)
from .context import ConflictContext
from .language_utils import infer_language, locations_overlap
from .parsers import extract_batch_code_blocks, extract_code_block
from .prompts import (
    SYSTEM_PROMPT,
    format_batch_merge_prompt,
    format_merge_prompt,
)

logger = logging.getLogger(__name__)

# Import Langfuse integration for tracing
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        trace_context,
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

# ROI Engine for artifact-based ROI calculation (replaces legacy roi_publisher)
try:
    from roi_engine.core import calculate_roi_for_spec, load_squad_config, publish_roi
    ROI_ENGINE_AVAILABLE = True
except ImportError:
    ROI_ENGINE_AVAILABLE = False

# Legacy flag for backwards compatibility
ROI_PUBLISHER_AVAILABLE = ROI_ENGINE_AVAILABLE

# Artifact storage (optional - graceful degradation if not available)
try:
    from analytics.artifact_storage import (
        save_artifact_safe,
        create_langfuse_reference,
        _get_artifacts_dir,
    )
    ARTIFACT_STORAGE_AVAILABLE = True
except ImportError:
    ARTIFACT_STORAGE_AVAILABLE = False


def extract_merge_artifacts(
    resolutions: List[MergeResult],
    project_dir: Optional[Any] = None,
    spec_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extract artifacts from merge resolutions for ROI tracking.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    Artifacts extracted:
    - conflict_resolution ($150 each) - full merged code for each conflict
    - merge_decision ($75 each) - decision with full merged content
    - code_choice ($50 each) - each code block in merged content

    Args:
        resolutions: List of MergeResult objects from conflict resolution
        project_dir: Project root directory for local storage
        spec_id: Spec identifier for grouping artifacts
        trace_id: Langfuse trace ID for linking

    Returns:
        Tuple of (local_artifacts, langfuse_refs):
        - local_artifacts: Full artifacts for local processing
        - langfuse_refs: Truncated references for Langfuse (or full artifacts if storage unavailable)
    """
    artifacts = []

    for resolution in resolutions:
        # Extract conflict_resolution artifacts ($150 each) - FULL merged code
        for conflict in resolution.conflicts_resolved:
            # Build FULL content with merged code, not just description
            content_parts = [
                f"## Conflict Resolution: {conflict.file_path}",
                f"**Location:** {conflict.location}",
                f"**Severity:** {conflict.severity.value if conflict.severity else 'unknown'}",
                f"**Reason:** {conflict.reason or 'conflict'}",
            ]

            # Include the FULL merged content if available
            if resolution.merged_content:
                content_parts.append("\n### Merged Code:")
                content_parts.append(f"```\n{resolution.merged_content}\n```")

            artifacts.append({
                "type": "conflict_resolution",
                "format": "merge",
                "content": "\n".join(content_parts),  # FULL CONTENT - no truncation!
                "value_usd": 150,
                "description": f"AI resolved conflict: {conflict.reason[:100] if conflict.reason else 'conflict'}",
                "tab": "dev",
                "metadata": {
                    "file_path": conflict.file_path,
                    "location": conflict.location,
                    "severity": conflict.severity.value if conflict.severity else "unknown",
                    "tasks_involved": list(conflict.tasks_involved) if conflict.tasks_involved else [],
                },
            })

        # Extract merge_decision artifacts ($75 each) - include FULL merged content
        if resolution.decision in [MergeDecision.AI_MERGED, MergeDecision.KEEP_OURS,
                                   MergeDecision.KEEP_THEIRS, MergeDecision.COMBINED]:
            decision_name = resolution.decision.value if hasattr(resolution.decision, 'value') else str(resolution.decision)

            # Build FULL content with decision details and merged code
            content_parts = [
                f"## Merge Decision: {decision_name}",
                f"**File:** {resolution.file_path}",
                f"**Explanation:** {resolution.explanation or 'N/A'}",
            ]

            if resolution.merged_content:
                content_parts.append("\n### Result:")
                content_parts.append(f"```\n{resolution.merged_content}\n```")

            artifacts.append({
                "type": "merge_decision",
                "format": "decision",
                "content": "\n".join(content_parts),  # FULL CONTENT - no truncation!
                "value_usd": 75,
                "description": f"Merge strategy: {decision_name}",
                "tab": "dev",
                "metadata": {
                    "decision": decision_name,
                    "file_path": resolution.file_path,
                    "conflicts_resolved_count": len(resolution.conflicts_resolved),
                    "conflicts_remaining_count": len(resolution.conflicts_remaining),
                },
            })

        # Extract code_choice artifacts ($50 each) from merged content - FULL code blocks
        if resolution.merged_content:
            # Extract full code blocks from merged content
            code_blocks = re.findall(r'```(\w+)?\n(.*?)```', resolution.merged_content, re.DOTALL)
            for i, (lang, code) in enumerate(code_blocks):
                # Build FULL content with the actual code
                content_parts = [
                    f"## Code Choice #{i+1}",
                    f"**File:** {resolution.file_path}",
                    f"**Language:** {lang or 'text'}",
                    "\n### Code:",
                    f"```{lang or ''}\n{code}\n```",
                ]

                artifacts.append({
                    "type": "code_choice",
                    "format": lang or "text",
                    "content": "\n".join(content_parts),  # FULL CONTENT - no truncation!
                    "value_usd": 50,
                    "description": f"AI selected code ({lang or 'text'})",
                    "tab": "dev",
                    "metadata": {
                        "file_path": resolution.file_path,
                        "language": lang or "text",
                        "choice_index": i + 1,
                        "code_length": len(code),
                    },
                })

    # Save artifacts locally and create Langfuse references
    if ARTIFACT_STORAGE_AVAILABLE and project_dir:
        from pathlib import Path
        project_path = Path(project_dir) if not isinstance(project_dir, Path) else project_dir

        langfuse_refs = []
        for artifact in artifacts:
            # Save full artifact locally
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_path,
                spec_id=spec_id,
                trace_id=trace_id,
                agent_type="merge_resolver",
                session_num=None,
            )

            if artifact_id:
                # Create lightweight reference for Langfuse
                artifacts_dir = _get_artifacts_dir(project_path)
                storage_path = str(
                    (artifacts_dir / artifact_id).relative_to(project_path)
                    if artifacts_dir.exists()
                    else f".auto-claude/artifacts/{artifact_id}.json"
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

# Type for the AI call function
AICallFunction = Callable[[str, str], str]


class AIResolver:
    """
    Resolves conflicts using AI with minimal context.

    This class:
    1. Builds minimal conflict context
    2. Creates focused prompts
    3. Calls AI and parses response
    4. Returns MergeResult with merged code

    Usage:
        resolver = AIResolver(ai_call_fn)
        result = resolver.resolve_conflict(conflict, context)
    """

    # Maximum tokens to send to AI (keeps costs down)
    MAX_CONTEXT_TOKENS = 4000

    def __init__(
        self,
        ai_call_fn: AICallFunction | None = None,
        max_context_tokens: int = MAX_CONTEXT_TOKENS,
        project_dir: Optional[Any] = None,
        spec_id: Optional[str] = None,
    ):
        """
        Initialize the AI resolver.

        Args:
            ai_call_fn: Function that calls AI. Signature: (system_prompt, user_prompt) -> response
                        If None, uses a stub that requires explicit calls.
            max_context_tokens: Maximum tokens to include in context
            project_dir: Project root directory for artifact storage
            spec_id: Spec identifier for artifact grouping
        """
        self.ai_call_fn = ai_call_fn
        self.max_context_tokens = max_context_tokens
        self._call_count = 0
        self._total_tokens = 0
        self._project_dir = project_dir
        self._spec_id = spec_id

    def set_ai_function(self, ai_call_fn: AICallFunction) -> None:
        """Set the AI call function after initialization."""
        self.ai_call_fn = ai_call_fn

    @property
    def stats(self) -> dict[str, int]:
        """Get usage statistics."""
        return {
            "calls_made": self._call_count,
            "estimated_tokens_used": self._total_tokens,
        }

    def reset_stats(self) -> None:
        """Reset usage statistics."""
        self._call_count = 0
        self._total_tokens = 0

    def build_context(
        self,
        conflict: ConflictRegion,
        baseline_code: str,
        task_snapshots: list[TaskSnapshot],
    ) -> ConflictContext:
        """
        Build minimal context for a conflict.

        Args:
            conflict: The conflict to resolve
            baseline_code: Original code before any changes
            task_snapshots: Snapshots from each involved task

        Returns:
            ConflictContext with minimal data for AI
        """
        # Filter to only changes at the conflict location
        task_changes: list[tuple[str, str, list]] = []

        for snapshot in task_snapshots:
            if snapshot.task_id not in conflict.tasks_involved:
                continue

            relevant_changes = [
                c
                for c in snapshot.semantic_changes
                if c.location == conflict.location
                or locations_overlap(c.location, conflict.location)
            ]

            if relevant_changes:
                task_changes.append(
                    (
                        snapshot.task_id,
                        snapshot.task_intent or "No intent specified",
                        relevant_changes,
                    )
                )

        # Determine language from file extension
        language = infer_language(conflict.file_path)

        # Build description
        change_types = [ct.value for ct in conflict.change_types]
        description = (
            f"Tasks {', '.join(conflict.tasks_involved)} made conflicting changes: "
            f"{', '.join(change_types)}. "
            f"Severity: {conflict.severity.value}. "
            f"{conflict.reason}"
        )

        return ConflictContext(
            file_path=conflict.file_path,
            location=conflict.location,
            baseline_code=baseline_code,
            task_changes=task_changes,
            conflict_description=description,
            language=language,
        )

    def resolve_conflict(
        self,
        conflict: ConflictRegion,
        baseline_code: str,
        task_snapshots: list[TaskSnapshot],
    ) -> MergeResult:
        """
        Resolve a conflict using AI.

        Args:
            conflict: The conflict to resolve
            baseline_code: Original code at the conflict location
            task_snapshots: Snapshots from involved tasks

        Returns:
            MergeResult with the resolution
        """
        if not self.ai_call_fn:
            return MergeResult(
                decision=MergeDecision.NEEDS_HUMAN_REVIEW,
                file_path=conflict.file_path,
                explanation="No AI function configured",
                conflicts_remaining=[conflict],
            )

        # Build context
        context = self.build_context(conflict, baseline_code, task_snapshots)

        # Check token limit
        if context.estimated_tokens > self.max_context_tokens:
            logger.warning(
                f"Context too large ({context.estimated_tokens} tokens), "
                "flagging for human review"
            )
            return MergeResult(
                decision=MergeDecision.NEEDS_HUMAN_REVIEW,
                file_path=conflict.file_path,
                explanation=f"Context too large for AI ({context.estimated_tokens} tokens)",
                conflicts_remaining=[conflict],
            )

        # Build prompt
        prompt_context = context.to_prompt_context()
        prompt = format_merge_prompt(prompt_context, context.language)

        # Call AI
        try:
            logger.info(f"Calling AI to resolve conflict in {conflict.file_path}")
            response = self.ai_call_fn(SYSTEM_PROMPT, prompt)
            self._call_count += 1
            self._total_tokens += context.estimated_tokens + len(response) // 4

            # Parse response
            merged_code = extract_code_block(response, context.language)

            if merged_code:
                return MergeResult(
                    decision=MergeDecision.AI_MERGED,
                    file_path=conflict.file_path,
                    merged_content=merged_code,
                    conflicts_resolved=[conflict],
                    ai_calls_made=1,
                    tokens_used=context.estimated_tokens,
                    explanation=f"AI resolved conflict at {conflict.location}",
                )
            else:
                logger.warning("Could not parse AI response")
                return MergeResult(
                    decision=MergeDecision.NEEDS_HUMAN_REVIEW,
                    file_path=conflict.file_path,
                    explanation="Could not parse AI merge response",
                    conflicts_remaining=[conflict],
                    ai_calls_made=1,
                    tokens_used=context.estimated_tokens,
                )

        except Exception as e:
            logger.error(f"AI call failed: {e}")
            return MergeResult(
                decision=MergeDecision.FAILED,
                file_path=conflict.file_path,
                error=str(e),
                conflicts_remaining=[conflict],
            )

    def resolve_multiple_conflicts(
        self,
        conflicts: list[ConflictRegion],
        baseline_codes: dict[str, str],
        task_snapshots: list[TaskSnapshot],
        batch: bool = True,
        project_id: Optional[str] = None,
    ) -> list[MergeResult]:
        """
        Resolve multiple conflicts.

        Args:
            conflicts: List of conflicts to resolve
            baseline_codes: Map of location -> baseline code
            task_snapshots: All task snapshots
            batch: Whether to batch conflicts (reduces API calls)
            project_id: Optional project ID for ROI tracking

        Returns:
            List of MergeResults
        """
        results = []

        # Setup Langfuse trace context if available
        use_langfuse = LANGFUSE_AVAILABLE and is_langfuse_ready() and trace_context
        trace_ctx = None
        langfuse_ctx_obj = None
        langfuse_trace_id = None

        if use_langfuse:
            try:
                trace_name = f"merge-resolver-{len(conflicts)}-conflicts"
                trace_ctx = trace_context(
                    name=trace_name,
                    project_id=project_id,
                    agent_type="merge_resolver",
                    metadata={
                        "conflicts_count": len(conflicts),
                        "batch_mode": batch,
                        "files_involved": list(set(c.file_path for c in conflicts)),
                    },
                    tags=["merge", "conflict_resolution", f"conflicts:{len(conflicts)}"],
                    input_data={
                        "conflicts_count": len(conflicts),
                        "batch_mode": batch,
                    },
                )
                langfuse_ctx_obj = trace_ctx.__enter__()
                if langfuse_ctx_obj and hasattr(langfuse_ctx_obj, 'trace_id'):
                    langfuse_trace_id = langfuse_ctx_obj.trace_id
                    logger.info(f"Created Langfuse trace for merge resolver: {langfuse_trace_id}")
            except Exception as e:
                logger.warning(f"Failed to create Langfuse trace: {e}")
                trace_ctx = None

        try:
            if batch and len(conflicts) > 1:
                # Try to batch conflicts from the same file
                by_file: dict[str, list[ConflictRegion]] = {}
                for conflict in conflicts:
                    if conflict.file_path not in by_file:
                        by_file[conflict.file_path] = []
                    by_file[conflict.file_path].append(conflict)

                for file_path, file_conflicts in by_file.items():
                    if len(file_conflicts) == 1:
                        # Single conflict, resolve individually
                        baseline = baseline_codes.get(file_conflicts[0].location, "")
                        results.append(
                            self.resolve_conflict(
                                file_conflicts[0], baseline, task_snapshots
                            )
                        )
                    else:
                        # Multiple conflicts in same file - batch resolve
                        result = self._resolve_file_batch(
                            file_path, file_conflicts, baseline_codes, task_snapshots
                        )
                        results.append(result)
            else:
                # Resolve each individually
                for conflict in conflicts:
                    baseline = baseline_codes.get(conflict.location, "")
                    results.append(
                        self.resolve_conflict(conflict, baseline, task_snapshots)
                    )

            # Publish ROI metrics with artifact storage
            self._publish_roi_sync(
                results=results,
                project_id=project_id,
                trace_id=langfuse_trace_id,
                project_dir=self._project_dir,  # Use cached project_dir for artifact storage
                spec_id=self._spec_id,
            )

        finally:
            # Finalize Langfuse trace
            if trace_ctx and langfuse_ctx_obj:
                try:
                    # Calculate summary metrics
                    total_resolved = sum(len(r.conflicts_resolved) for r in results)
                    total_remaining = sum(len(r.conflicts_remaining) for r in results)
                    total_tokens = sum(r.tokens_used for r in results)

                    langfuse_ctx_obj.set_output({
                        "conflicts_resolved": total_resolved,
                        "conflicts_remaining": total_remaining,
                        "total_tokens": total_tokens,
                        "ai_calls": sum(r.ai_calls_made for r in results),
                    })
                    trace_ctx.__exit__(None, None, None)
                    flush_langfuse()
                except Exception as e:
                    logger.warning(f"Failed to finalize Langfuse trace: {e}")

        return results

    def _publish_roi_sync(
        self,
        results: list[MergeResult],
        project_id: Optional[str],
        trace_id: Optional[str],
        project_dir: Optional[Any] = None,
        spec_id: Optional[str] = None,
    ) -> None:
        """
        Publish ROI metrics using ROI Engine (synchronous wrapper).

        Args:
            results: List of merge results
            project_id: Project identifier
            trace_id: Langfuse trace ID
            project_dir: Project root directory for artifact storage
            spec_id: Spec identifier for artifact grouping
        """
        if not ROI_ENGINE_AVAILABLE:
            return

        try:
            import asyncio
            from pathlib import Path

            # Calculate metrics from results
            conflicts_resolved = sum(len(r.conflicts_resolved) for r in results)
            files_merged = len(set(r.file_path for r in results if r.conflicts_resolved))
            total_tokens = sum(r.tokens_used for r in results)

            # Estimate cost (rough estimate based on tokens)
            estimated_cost = (total_tokens / 1000) * 0.003  # ~$0.003 per 1K tokens

            # Extract artifacts for traceability with local storage
            # Returns (full_artifacts, langfuse_refs) - full stored locally, refs for Langfuse
            artifacts, langfuse_refs = extract_merge_artifacts(
                results,
                project_dir=project_dir,
                spec_id=spec_id,
                trace_id=trace_id,
            )

            # Calculate total artifact value (use full artifacts for value)
            total_artifact_value = sum(a.get("value_usd", 0) for a in artifacts)

            # Publish ROI using ROI Engine
            async def _publish():
                try:
                    project_path = Path(project_dir) if project_dir else Path.cwd()
                    squad_config = load_squad_config(project_dir=project_path)
                    roi_result = calculate_roi_for_spec(
                        spec_id=spec_id or f"merge-{trace_id[:8] if trace_id else 'unknown'}",
                        project_dir=project_path,
                        token_cost=estimated_cost,
                        squad_config=squad_config,
                    )
                    await publish_roi(
                        roi_result,
                        trace_id=trace_id,
                        project_dir=project_path,
                    )
                    logger.info(
                        f"ROI published for merge resolver: "
                        f"resolved={conflicts_resolved}, files={files_merged}, "
                        f"artifacts={len(artifacts)}, value=${total_artifact_value}"
                    )
                    return roi_result
                except Exception as e:
                    logger.warning(f"Failed to publish ROI: {e}")
                    return None

            # Run async function
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an async context, schedule it
                    asyncio.ensure_future(_publish())
                else:
                    loop.run_until_complete(_publish())
            except RuntimeError:
                # No event loop, create one
                asyncio.run(_publish())

        except Exception as e:
            logger.warning(f"Failed to publish merge resolver ROI: {e}")

    def _resolve_file_batch(
        self,
        file_path: str,
        conflicts: list[ConflictRegion],
        baseline_codes: dict[str, str],
        task_snapshots: list[TaskSnapshot],
    ) -> MergeResult:
        """
        Resolve multiple conflicts in the same file with a single AI call.

        This is more efficient but may be less precise.
        """
        if not self.ai_call_fn:
            return MergeResult(
                decision=MergeDecision.NEEDS_HUMAN_REVIEW,
                file_path=file_path,
                explanation="No AI function configured",
                conflicts_remaining=conflicts,
            )

        # Combine contexts
        all_contexts = []
        for conflict in conflicts:
            baseline = baseline_codes.get(conflict.location, "")
            ctx = self.build_context(conflict, baseline, task_snapshots)
            all_contexts.append(ctx)

        # Check combined token limit
        total_tokens = sum(ctx.estimated_tokens for ctx in all_contexts)
        if total_tokens > self.max_context_tokens:
            # Too big to batch, fall back to individual resolution
            results = []
            for conflict in conflicts:
                baseline = baseline_codes.get(conflict.location, "")
                results.append(
                    self.resolve_conflict(conflict, baseline, task_snapshots)
                )

            # Combine results
            merged = results[0]
            for r in results[1:]:
                merged.conflicts_resolved.extend(r.conflicts_resolved)
                merged.conflicts_remaining.extend(r.conflicts_remaining)
                merged.ai_calls_made += r.ai_calls_made
                merged.tokens_used += r.tokens_used
            return merged

        # Build combined prompt
        combined_context = "\n\n---\n\n".join(
            ctx.to_prompt_context() for ctx in all_contexts
        )

        language = all_contexts[0].language if all_contexts else "text"

        batch_prompt = format_batch_merge_prompt(
            file_path=file_path,
            num_conflicts=len(conflicts),
            combined_context=combined_context,
            language=language,
        )

        try:
            response = self.ai_call_fn(SYSTEM_PROMPT, batch_prompt)
            self._call_count += 1
            self._total_tokens += total_tokens + len(response) // 4

            # Parse batch response
            # This is a simplified parser - production would be more robust
            resolved = []
            remaining = []

            for conflict in conflicts:
                # Try to find the resolution for this location
                code_block = extract_batch_code_blocks(
                    response, conflict.location, language
                )

                if code_block:
                    resolved.append(conflict)
                else:
                    remaining.append(conflict)

            # Return combined result
            if resolved:
                return MergeResult(
                    decision=MergeDecision.AI_MERGED
                    if not remaining
                    else MergeDecision.NEEDS_HUMAN_REVIEW,
                    file_path=file_path,
                    merged_content=response,  # Full response for manual extraction
                    conflicts_resolved=resolved,
                    conflicts_remaining=remaining,
                    ai_calls_made=1,
                    tokens_used=total_tokens,
                    explanation=f"Batch resolved {len(resolved)}/{len(conflicts)} conflicts",
                )
            else:
                return MergeResult(
                    decision=MergeDecision.NEEDS_HUMAN_REVIEW,
                    file_path=file_path,
                    explanation="Could not parse batch AI response",
                    conflicts_remaining=conflicts,
                    ai_calls_made=1,
                    tokens_used=total_tokens,
                )

        except Exception as e:
            logger.error(f"Batch AI call failed: {e}")
            return MergeResult(
                decision=MergeDecision.FAILED,
                file_path=file_path,
                error=str(e),
                conflicts_remaining=conflicts,
            )

    def can_resolve(self, conflict: ConflictRegion) -> bool:
        """
        Check if this resolver should handle a conflict.

        Only handles conflicts that need AI resolution.
        """
        return (
            conflict.merge_strategy in {MergeStrategy.AI_REQUIRED, None}
            and conflict.severity in {ConflictSeverity.MEDIUM, ConflictSeverity.HIGH}
            and self.ai_call_fn is not None
        )
