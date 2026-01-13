"""
Triage Engine
=============

Issue triage logic for detecting duplicates, spam, and feature creep.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

# Analytics tracking
try:
    from analytics import (
        create_feature_tracker,
        FEATURE_ISSUE_TRIAGE,
        is_tracking_enabled,
    )
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False

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

try:
    from ..models import GitHubRunnerConfig, TriageCategory, TriageResult
    from .prompt_manager import PromptManager
    from .response_parsers import ResponseParser
except (ImportError, ValueError, SystemError):
    from models import GitHubRunnerConfig, TriageCategory, TriageResult
    from services.prompt_manager import PromptManager
    from services.response_parsers import ResponseParser


# =============================================================================
# ARTIFACT EXTRACTION
# =============================================================================


def extract_triage_artifacts(
    triage_result: TriageResult,
    issue: dict,
    project_dir: Path | None = None,
    trace_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Extract triage artifacts from triage result.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    Artifacts extracted:
    - triage_classification ($50) - the category classification (bug, feature, etc.)
    - priority_assignment ($50) - the priority level assignment
    - label_suggestion ($25 each) - suggested labels to add
    - duplicate_detected ($75) - if a duplicate was detected
    - assignee_suggestion ($50) - if an assignee was suggested (future)

    Args:
        triage_result: The TriageResult from the triage engine
        issue: The original issue dict
        project_dir: Project root directory for local storage
        trace_id: Langfuse trace ID for linking

    Returns:
        Tuple of (local_artifacts, langfuse_refs):
        - local_artifacts: Full artifacts for local processing
        - langfuse_refs: Truncated references for Langfuse (or full artifacts if storage unavailable)
    """
    artifacts = []

    # Extract triage_classification artifact
    category_name = triage_result.category.value if triage_result.category else "unknown"
    artifacts.append({
        "type": "triage_classification",
        "format": "text",
        "content": f"Issue #{triage_result.issue_number} classified as: {category_name.upper()}\n"
                   f"Confidence: {triage_result.confidence:.0%}\n"
                   f"Issue Title: {issue.get('title', 'N/A')}",
        "value_usd": 50,
        "description": f"Triage classification: {category_name}",
        "tab": "ops",
        "metadata": {
            "issue_number": triage_result.issue_number,
            "category": category_name,
            "confidence": triage_result.confidence,
            "repo": triage_result.repo,
        },
    })

    # Extract priority_assignment artifact
    if triage_result.priority:
        artifacts.append({
            "type": "priority_assignment",
            "format": "text",
            "content": f"Issue #{triage_result.issue_number} priority: {triage_result.priority.upper()}\n"
                       f"Category: {category_name}\n"
                       f"Confidence: {triage_result.confidence:.0%}",
            "value_usd": 50,
            "description": f"Priority assignment: {triage_result.priority}",
            "tab": "ops",
            "metadata": {
                "issue_number": triage_result.issue_number,
                "priority": triage_result.priority,
            },
        })

    # Extract label_suggestion artifacts
    for label in triage_result.labels_to_add:
        artifacts.append({
            "type": "label_suggestion",
            "format": "text",
            "content": f"Suggested label for #{triage_result.issue_number}: {label}",
            "value_usd": 25,
            "description": f"Label suggestion: {label}",
            "tab": "ops",
            "metadata": {
                "issue_number": triage_result.issue_number,
                "label": label,
                "action": "add",
            },
        })

    # Extract duplicate_detected artifact if applicable
    if triage_result.is_duplicate and triage_result.duplicate_of:
        artifacts.append({
            "type": "duplicate_detected",
            "format": "text",
            "content": f"Issue #{triage_result.issue_number} detected as duplicate of #{triage_result.duplicate_of}\n"
                       f"Title: {issue.get('title', 'N/A')}\n"
                       f"Confidence: {triage_result.confidence:.0%}",
            "value_usd": 75,
            "description": f"Duplicate of #{triage_result.duplicate_of}",
            "tab": "ops",
            "metadata": {
                "issue_number": triage_result.issue_number,
                "duplicate_of": triage_result.duplicate_of,
                "confidence": triage_result.confidence,
            },
        })

    # Extract assignee_suggestion if comment contains assignee recommendation
    # This is derived from the triage comment if it suggests an assignee
    if triage_result.comment:
        # Look for assignee suggestions in comment
        comment_lower = triage_result.comment.lower()
        if "assign" in comment_lower or "assignee" in comment_lower:
            artifacts.append({
                "type": "assignee_suggestion",
                "format": "text",
                "content": f"Assignee suggestion for #{triage_result.issue_number}:\n{triage_result.comment}",
                "value_usd": 50,
                "description": "Assignee suggestion from triage",
                "tab": "ops",
                "metadata": {
                    "issue_number": triage_result.issue_number,
                    "from_comment": True,
                },
            })

    # Save artifacts locally and create Langfuse references
    if ARTIFACT_STORAGE_AVAILABLE and project_dir:
        langfuse_refs = []
        for artifact in artifacts:
            # Save full artifact locally
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_dir,
                spec_id=f"github-triage-{triage_result.issue_number}",
                trace_id=trace_id,
                agent_type="triage_engine",
                session_num=None,
            )

            if artifact_id:
                # Create lightweight reference for Langfuse
                artifacts_dir = _get_artifacts_dir(project_dir)
                storage_path = str(
                    (artifacts_dir / artifact_id).relative_to(project_dir)
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


# =============================================================================
# TRIAGE ENGINE
# =============================================================================


class TriageEngine:
    """Handles issue triage workflow."""

    def __init__(
        self,
        project_dir: Path,
        github_dir: Path,
        config: GitHubRunnerConfig,
        progress_callback=None,
    ):
        self.project_dir = Path(project_dir)
        self.github_dir = Path(github_dir)
        self.config = config
        self.progress_callback = progress_callback
        self.prompt_manager = PromptManager()
        self.parser = ResponseParser()

        # Initialize analytics tracker
        self.tracker = None
        if TRACKING_AVAILABLE and is_tracking_enabled():
            project_id = self.project_dir.name
            db_path = str(self.project_dir / ".auto-claude" / "analytics.db")
            self.tracker = create_feature_tracker(
                project_id=project_id,
                feature_type=FEATURE_ISSUE_TRIAGE,
                db_path=db_path,
                metadata={"model": config.model}
            )

    def _report_progress(self, phase: str, progress: int, message: str, **kwargs):
        """Report progress if callback is set."""
        if self.progress_callback:
            # Import at module level to avoid circular import issues
            import sys

            if "orchestrator" in sys.modules:
                ProgressCallback = sys.modules["orchestrator"].ProgressCallback
            else:
                # Fallback: try relative import
                try:
                    from ..orchestrator import ProgressCallback
                except ImportError:
                    from orchestrator import ProgressCallback

            self.progress_callback(
                ProgressCallback(
                    phase=phase, progress=progress, message=message, **kwargs
                )
            )

    async def triage_single_issue(
        self, issue: dict, all_issues: list[dict]
    ) -> TriageResult:
        """Triage a single issue using AI."""
        from core.client import create_client

        # Build context with issue and potential duplicates
        context = self.build_triage_context(issue, all_issues)

        # Load prompt
        prompt = self.prompt_manager.get_triage_prompt()
        full_prompt = prompt + "\n\n---\n\n" + context

        # Run AI
        client = create_client(
            project_dir=self.project_dir,
            spec_dir=self.github_dir,
            model=self.config.model,
            agent_type="qa_reviewer",
        )

        # Start tracking session
        if self.tracker:
            try:
                self.tracker.update_metadata("issue_number", issue["number"])
                await self.tracker.start_session()
            except Exception:
                pass

        # Track timing for ROI
        start_time = time.time()
        project_id = self.project_dir.name

        try:
            async with client:
                await client.query(full_prompt)

                response_text = ""
                async for msg in client.receive_response():
                    msg_type = type(msg).__name__

                    # Track message for analytics
                    if self.tracker and msg_type in ("AssistantMessage", "ResultMessage"):
                        try:
                            await self.tracker.track_message(msg)
                        except Exception:
                            pass

                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            # Must check block type - only TextBlock has .text attribute
                            block_type = type(block).__name__
                            if block_type == "TextBlock" and hasattr(block, "text"):
                                response_text += block.text

                # Finalize tracking
                if self.tracker:
                    try:
                        await self.tracker.finalize()
                    except Exception:
                        pass

                # Parse triage result
                triage_result = self.parser.parse_triage_result(
                    issue, response_text, self.config.repo
                )

                # Calculate duration
                duration_seconds = time.time() - start_time

                # Publish ROI using ROI Engine (wrapped in try/except to not break triage)
                if ROI_ENGINE_AVAILABLE:
                    try:
                        # Extract artifacts from the triage result (for local storage)
                        # Returns (full_artifacts, langfuse_refs) - full stored locally, refs for Langfuse
                        artifacts, langfuse_refs = extract_triage_artifacts(
                            triage_result,
                            issue,
                            project_dir=self.project_dir,
                            trace_id=None,  # No Langfuse trace in this context
                        )

                        # Estimate cost and tokens (simplified - actual tracking would come from SDK)
                        # Estimate ~4 chars per token, rough estimate for ROI calculation
                        estimated_tokens = len(response_text) // 4 + len(full_prompt) // 4
                        estimated_cost = (estimated_tokens / 1000) * 0.003  # Rough cost estimate

                        # Calculate ROI using ROI Engine
                        spec_id = f"github-triage-{issue['number']}"
                        squad_config = load_squad_config(project_dir=self.project_dir)
                        roi_result = calculate_roi_for_spec(
                            spec_id=spec_id,
                            project_dir=self.project_dir,
                            token_cost=estimated_cost,
                            squad_config=squad_config,
                        )

                        # Publish to Langfuse
                        await publish_roi(roi_result, trace_id=None, project_dir=self.project_dir)

                        print(
                            f"[AI] Triage ROI: {roi_result.roi_percentage:.1f}% ROI, "
                            f"${roi_result.total_artifact_value:.2f} value",
                            flush=True,
                        )

                    except Exception as e:
                        # ROI publishing should never break triage
                        print(f"Failed to publish ROI for triage (non-fatal): {e}")

                return triage_result

        except Exception as e:
            # Finalize tracking on error
            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass

            print(f"Triage error for #{issue['number']}: {e}")
            return TriageResult(
                issue_number=issue["number"],
                repo=self.config.repo,
                category=TriageCategory.FEATURE,
                confidence=0.0,
            )

    def build_triage_context(self, issue: dict, all_issues: list[dict]) -> str:
        """Build context for triage including potential duplicates."""
        # Find potential duplicates by title similarity
        potential_dupes = []
        for other in all_issues:
            if other["number"] == issue["number"]:
                continue
            # Simple word overlap check
            title_words = set(issue["title"].lower().split())
            other_words = set(other["title"].lower().split())
            overlap = len(title_words & other_words) / max(len(title_words), 1)
            if overlap > 0.3:
                potential_dupes.append(other)

        lines = [
            f"## Issue #{issue['number']}",
            f"**Title:** {issue['title']}",
            f"**Author:** {issue['author']['login']}",
            f"**Created:** {issue['createdAt']}",
            f"**Labels:** {', '.join(label['name'] for label in issue.get('labels', []))}",
            "",
            "### Body",
            issue.get("body", "No description"),
            "",
        ]

        if potential_dupes:
            lines.append("### Potential Duplicates (similar titles)")
            for d in potential_dupes[:5]:
                lines.append(f"- #{d['number']}: {d['title']}")
            lines.append("")

        return "\n".join(lines)
