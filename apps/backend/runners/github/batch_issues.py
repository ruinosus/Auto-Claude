"""
Issue Batching Service
======================

Groups similar issues together for combined auto-fix:
- Uses semantic similarity from duplicates.py
- Creates issue clusters using agglomerative clustering
- Generates combined specs for issue batches
- Tracks batch state and progress
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# Add backend path for imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

# Import model resolution for Azure Foundry support
from phase_config import resolve_model_id

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

# Legacy feature tracker for token tracking (backwards compatibility)
try:
    from analytics import (
        create_feature_tracker,
        FEATURE_ISSUE_TRIAGE,
        is_tracking_enabled,
    )
    TRACKING_AVAILABLE = True
except ImportError as e:
    TRACKING_AVAILABLE = False

# Import ROI publisher
try:
    from analytics.roi_publisher import publish_feature_roi
    ROI_PUBLISHER_AVAILABLE = True
except ImportError:
    ROI_PUBLISHER_AVAILABLE = False

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

logger = logging.getLogger(__name__)


def extract_triage_artifacts(
    triage_results: list[dict],
    issues: list[dict],
    project_dir: Path | None = None,
    trace_id: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Extract artifacts from triage results for ROI calculation.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    Artifact values (as defined in ROI_IMPLEMENTATION_TRACKER.md section 4.2):
    - triage_classification: $30 - classification of the issue
    - priority_assignment: $50 - priority assigned
    - label_suggestion: $20 - label suggested
    - duplicate_detected: $75 - duplicate detected
    - assignee_suggestion: $40 - assignee suggestion

    Args:
        triage_results: List of batch/triage results from analyze_and_batch_issues
        issues: Original list of issues that were triaged
        project_dir: Project root directory for local storage
        trace_id: Langfuse trace ID for linking

    Returns:
        Tuple of (local_artifacts, langfuse_refs):
        - local_artifacts: Full artifacts for local processing
        - langfuse_refs: Truncated references for Langfuse (or full artifacts if storage unavailable)
    """
    artifacts = []

    for batch in triage_results:
        issue_numbers = batch.get("issue_numbers", [])
        theme = batch.get("theme", "")
        reasoning = batch.get("reasoning", "")
        confidence = batch.get("confidence", 0.0)

        # Each batch represents a triage classification - FULL CONTENT, no truncation
        if issue_numbers:
            # Build full content for classification
            content = f"Issues {issue_numbers}: {theme}"
            if reasoning:
                content += f"\n\nReasoning: {reasoning}"

            artifacts.append({
                "type": "triage_classification",
                "format": "text",
                "content": content,  # FULL CONTENT - no truncation
                "value_usd": 30,
                "description": f"Classified {len(issue_numbers)} issue(s) as: {theme[:50]}",
                "tab": "ops",
                "confidence": confidence,
                "metadata": {
                    "issue_numbers": issue_numbers,
                    "theme": theme,
                    "reasoning": reasoning,
                    "confidence": confidence,
                },
            })

        # Check if priority was assigned (inferred from theme/reasoning)
        priority_keywords = ["critical", "high priority", "urgent", "blocker", "low priority", "medium priority"]
        theme_lower = theme.lower()
        reasoning_lower = reasoning.lower()

        for priority_kw in priority_keywords:
            if priority_kw in theme_lower or priority_kw in reasoning_lower:
                # Build full content for priority assignment
                content = f"Priority '{priority_kw}' assigned to issues {issue_numbers}"
                if reasoning:
                    content += f"\n\nContext: {reasoning}"

                artifacts.append({
                    "type": "priority_assignment",
                    "format": "text",
                    "content": content,  # FULL CONTENT - no truncation
                    "value_usd": 50,
                    "description": f"Priority assignment: {priority_kw}",
                    "tab": "ops",
                    "metadata": {
                        "priority": priority_kw,
                        "issue_numbers": issue_numbers,
                    },
                })
                break  # Only count one priority per batch

        # Check for label suggestions (inferred from theme)
        label_keywords = [
            "bug", "feature", "enhancement", "documentation", "refactor",
            "performance", "security", "ui", "ux", "frontend", "backend",
            "api", "database", "testing", "infrastructure", "ci/cd",
        ]

        for label_kw in label_keywords:
            if label_kw in theme_lower:
                # Build full content for label suggestion
                content = f"Label '{label_kw}' suggested for issues {issue_numbers}"
                if theme:
                    content += f"\n\nBased on theme: {theme}"

                artifacts.append({
                    "type": "label_suggestion",
                    "format": "text",
                    "content": content,  # FULL CONTENT - no truncation
                    "value_usd": 20,
                    "description": f"Label suggestion: {label_kw}",
                    "tab": "ops",
                    "metadata": {
                        "label": label_kw,
                        "issue_numbers": issue_numbers,
                        "theme": theme,
                    },
                })
                break  # Only count one label per batch

    # Check for duplicates (batches with multiple issues indicate related/potential duplicates)
    for batch in triage_results:
        issue_numbers = batch.get("issue_numbers", [])
        reasoning = batch.get("reasoning", "")
        reasoning_lower = reasoning.lower()

        # If multiple issues in batch and reasoning mentions similarity/duplicate
        if len(issue_numbers) > 1:
            if any(kw in reasoning_lower for kw in ["duplicate", "same", "identical", "related"]):
                # Build full content for duplicate detection
                content = f"Potential duplicates detected: {issue_numbers}"
                if reasoning:
                    content += f"\n\nReasoning: {reasoning}"

                artifacts.append({
                    "type": "duplicate_detected",
                    "format": "text",
                    "content": content,  # FULL CONTENT - no truncation
                    "value_usd": 75,
                    "description": f"Duplicate/related issues: {issue_numbers}",
                    "tab": "ops",
                    "metadata": {
                        "issue_numbers": issue_numbers,
                        "reasoning": reasoning,
                    },
                })

    # Check for assignee suggestions in original issues (if present in labels/metadata)
    for issue in issues:
        labels = issue.get("labels", [])
        assignee = issue.get("assignee")

        if assignee:
            # Build full content for assignee suggestion
            issue_number = issue.get('number')
            issue_title = issue.get('title', 'No title')
            content = f"Issue #{issue_number} assigned to {assignee}"
            content += f"\n\nTitle: {issue_title}"
            if labels:
                label_names = [l.get('name', '') for l in labels if isinstance(l, dict)]
                content += f"\nLabels: {', '.join(label_names)}"

            artifacts.append({
                "type": "assignee_suggestion",
                "format": "text",
                "content": content,  # FULL CONTENT - no truncation
                "value_usd": 40,
                "description": f"Assignee suggestion for issue #{issue_number}",
                "tab": "ops",
                "metadata": {
                    "issue_number": issue_number,
                    "assignee": assignee,
                    "issue_title": issue_title,
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
                spec_id=None,  # GitHub triage doesn't have a spec
                trace_id=trace_id,
                agent_type="batch_analyzer",
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


# Import validators
try:
    from .batch_validator import BatchValidator
    from .duplicates import SIMILAR_THRESHOLD
    from .file_lock import locked_json_write
except (ImportError, ValueError, SystemError):
    from batch_validator import BatchValidator
    from duplicates import SIMILAR_THRESHOLD
    from file_lock import locked_json_write


class ClaudeBatchAnalyzer:
    """
    Claude-based batch analyzer for GitHub issues.

    Instead of doing O(n²) pairwise comparisons, this uses a single Claude call
    to analyze a group of issues and suggest optimal batching.
    """

    def __init__(self, project_dir: Path | None = None):
        """Initialize Claude batch analyzer."""
        self.project_dir = project_dir or Path.cwd()
        self.tracker = None
        self.project_id = self.project_dir.name

        # Check Langfuse availability
        self.langfuse_enabled = LANGFUSE_AVAILABLE and is_langfuse_ready()
        logger.info(f"[BATCH_ANALYZER] Langfuse integration: available={LANGFUSE_AVAILABLE}, ready={self.langfuse_enabled}")

        # Initialize feature tracker for token usage
        if TRACKING_AVAILABLE and is_tracking_enabled():
            db_path = str(self.project_dir / ".auto-claude" / "analytics.db")
            self.tracker = create_feature_tracker(
                project_id=self.project_id,
                feature_type=FEATURE_ISSUE_TRIAGE,
                db_path=db_path,
                metadata={"component": "batch_analyzer"}
            )
            logger.info(f"[BATCH_ANALYZER] Feature tracker initialized for project: {self.project_id}")

        logger.info(
            f"[BATCH_ANALYZER] Initialized with project_dir: {self.project_dir}"
        )

    async def analyze_and_batch_issues(
        self,
        issues: list[dict[str, Any]],
        max_batch_size: int = 5,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        Analyze a group of issues and suggest optimal batches.

        Uses a SINGLE Claude call to analyze all issues and group them intelligently.

        Returns:
            Tuple of (batches_list, langfuse_trace_id)

        Args:
            issues: List of issues to analyze
            max_batch_size: Maximum issues per batch

        Returns:
            List of batch suggestions, each containing:
            - issue_numbers: list of issue numbers in this batch
            - theme: common theme/description
            - reasoning: why these should be batched
            - confidence: 0.0-1.0
        """
        if not issues:
            return []

        if len(issues) == 1:
            # Single issue = single batch
            return [
                {
                    "issue_numbers": [issues[0]["number"]],
                    "theme": issues[0].get("title", "Single issue"),
                    "reasoning": "Single issue in group",
                    "confidence": 1.0,
                }
            ]

        try:
            import sys

            import claude_agent_sdk  # noqa: F401 - check availability

            backend_path = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(backend_path))
            from core.auth import ensure_claude_code_oauth_token, get_sdk_env_vars
        except ImportError as e:
            logger.error(f"claude-agent-sdk not available: {e}")
            # Fallback: each issue is its own batch
            return [
                {
                    "issue_numbers": [issue["number"]],
                    "theme": issue.get("title", ""),
                    "reasoning": "Claude SDK not available",
                    "confidence": 0.5,
                }
                for issue in issues
            ]

        # Build issue list for the prompt
        issue_list = "\n".join(
            [
                f"- #{issue['number']}: {issue.get('title', 'No title')}"
                f"\n  Labels: {', '.join(label.get('name', '') for label in issue.get('labels', [])) or 'none'}"
                f"\n  Body: {(issue.get('body', '') or '')[:200]}..."
                for issue in issues
            ]
        )

        prompt = f"""Analyze these GitHub issues and group them into batches that should be fixed together.

ISSUES TO ANALYZE:
{issue_list}

RULES:
1. Group issues that share a common root cause or affect the same component
2. Maximum {max_batch_size} issues per batch
3. Issues that are unrelated should be in separate batches (even single-issue batches)
4. Be conservative - only batch issues that clearly belong together

Respond with JSON only:
{{
  "batches": [
    {{
      "issue_numbers": [1, 2, 3],
      "theme": "Authentication issues",
      "reasoning": "All related to login flow",
      "confidence": 0.85
    }},
    {{
      "issue_numbers": [4],
      "theme": "UI bug",
      "reasoning": "Unrelated to other issues",
      "confidence": 0.95
    }}
  ]
}}"""

        # Create Langfuse trace context if available
        trace_name = f"batch-analyzer-{self.project_id}"
        trace_ctx = None
        langfuse_ctx_obj = None
        langfuse_trace_id = None
        if self.langfuse_enabled and trace_context:
            # Truncate prompt for trace input
            trace_input = prompt[:2000] + "..." if len(prompt) > 2000 else prompt
            trace_ctx = trace_context(
                name=trace_name,
                project_id=self.project_id,  # Required for data isolation filtering
                agent_type="batch_analyzer",
                metadata={
                    "issues_count": len(issues),
                    "max_batch_size": max_batch_size,
                    "model": resolve_model_id("sonnet"),
                },
                tags=["github", "batch_analyzer", "issue_triage"],
                input_data={"prompt": trace_input, "issues_count": len(issues)},
            )
            langfuse_ctx_obj = trace_ctx.__enter__()
            if langfuse_ctx_obj:
                langfuse_trace_id = langfuse_ctx_obj.trace_id
            logger.info(f"[BATCH_ANALYZER] Langfuse trace created: {trace_name}, trace_id: {langfuse_trace_id}")

        try:
            ensure_claude_code_oauth_token()

            logger.info(
                f"[BATCH_ANALYZER] Analyzing {len(issues)} issues in single call"
            )

            # Start tracking session if tracker is available
            if self.tracker:
                try:
                    self.tracker.update_metadata("issues_count", len(issues))
                    await self.tracker.start_session()
                    logger.info("[BATCH_ANALYZER] Feature tracking session started")
                except Exception as e:
                    logger.error(f"[BATCH_ANALYZER] Failed to start tracking session: {e}")

            # Using Sonnet for better analysis (still just 1 call)
            from core.simple_client import create_simple_client

            client = create_simple_client(
                agent_type="batch_analysis",
                model=resolve_model_id("sonnet"),
                system_prompt="You are an expert at analyzing GitHub issues and grouping related ones. Respond ONLY with valid JSON. Do NOT use any tools.",
                cwd=self.project_dir,
            )

            async with client:
                await client.query(prompt)
                response_text, total_input_tokens, total_output_tokens = await self._collect_response_with_usage(client)

            logger.info(
                f"[BATCH_ANALYZER] Received response: {len(response_text)} chars"
            )

            # Log to Langfuse if enabled
            if self.langfuse_enabled and LANGFUSE_AVAILABLE:
                try:
                    log_generation_in_current_trace(
                        name="batch-analyzer",
                        model=resolve_model_id("sonnet"),
                        input_data=prompt[:500] + "..." if len(prompt) > 500 else prompt,
                        output_data=response_text[:1000] + "..." if len(response_text) > 1000 else response_text,
                        usage={
                            "input": total_input_tokens,
                            "output": total_output_tokens,
                            "total": total_input_tokens + total_output_tokens,
                        },
                        metadata={"issues_count": len(issues)},
                    )
                    logger.info("[BATCH_ANALYZER] Logged generation to Langfuse")
                except Exception as e:
                    logger.error(f"[BATCH_ANALYZER] Failed to log to Langfuse: {e}")

            # Parse JSON response
            result = self._parse_json_response(response_text)

            # Get batches for ROI calculation
            batches = result.get("batches", [])

            # Finalize tracking
            if self.tracker:
                try:
                    await self.tracker.finalize()
                    logger.info("[BATCH_ANALYZER] Feature tracking session finalized")
                except Exception as e:
                    logger.error(f"[BATCH_ANALYZER] Failed to finalize tracking: {e}")

            # Publish ROI metrics BEFORE closing Langfuse trace
            if ROI_PUBLISHER_AVAILABLE:
                try:
                    # Extract artifacts from triage results
                    # Returns (full_artifacts, langfuse_refs) - full stored locally, refs for Langfuse
                    artifacts, langfuse_refs = extract_triage_artifacts(
                        batches,
                        issues,
                        project_dir=self.project_dir,
                        trace_id=langfuse_trace_id,
                    )

                    # Calculate triage metrics (use full artifacts for counts)
                    issues_triaged = len(issues)
                    labels_assigned = sum(1 for a in artifacts if a.get("type") == "label_suggestion")
                    priorities_set = sum(1 for a in artifacts if a.get("type") == "priority_assignment")
                    duplicates_found = sum(1 for a in artifacts if a.get("type") == "duplicate_detected")

                    # Calculate total artifact value (use full artifacts for value)
                    total_artifact_value = sum(a.get("value_usd", 0) for a in artifacts)

                    # Estimate cost from tokens
                    total_tokens = total_input_tokens + total_output_tokens
                    # Sonnet pricing: $3/M input, $15/M output
                    cost_usd = (total_input_tokens * 0.003 / 1000) + (total_output_tokens * 0.015 / 1000)

                    await publish_feature_roi(
                        feature_type="github_issue_triage",
                        project_id=self.project_id,
                        cost_usd=cost_usd,
                        tokens=total_tokens,
                        model=resolve_model_id("sonnet"),
                        trace_id=langfuse_trace_id,
                        metrics={
                            "issues_triaged": issues_triaged,
                            "labels_assigned": labels_assigned,
                            "priorities_set": priorities_set,
                            "duplicates_found": duplicates_found,
                            "batches_created": len(batches),
                            "artifacts_count": len(artifacts),
                            "artifact_value_usd": total_artifact_value,
                        },
                        artifacts=langfuse_refs,  # Pass refs (with storage_path) for Langfuse
                    )
                    logger.info(
                        f"[BATCH_ANALYZER] ROI published: "
                        f"issues={issues_triaged}, labels={labels_assigned}, "
                        f"priorities={priorities_set}, duplicates={duplicates_found}, "
                        f"artifacts={len(artifacts)}, value=${total_artifact_value}, "
                        f"trace_id={langfuse_trace_id}"
                    )
                except Exception as e:
                    logger.error(f"[BATCH_ANALYZER] Failed to publish ROI: {e}")

            # Finalize Langfuse trace
            if trace_ctx:
                try:
                    # Set trace output before exiting - include artifacts for traceability
                    if langfuse_ctx_obj:
                        # FULL content - NO truncation (Zero Truncation Policy)
                        output_data = {
                            "response": response_text,
                            "batches_count": len(batches),
                        }
                        # Include artifacts if ROI was published
                        if ROI_PUBLISHER_AVAILABLE:
                            output_data["artifacts_count"] = len(artifacts) if 'artifacts' in dir() else 0
                        langfuse_ctx_obj.set_output(output_data)
                    trace_ctx.__exit__(None, None, None)
                    flush_langfuse()
                    logger.info("[BATCH_ANALYZER] Langfuse trace finalized")
                except Exception as e:
                    logger.error(f"[BATCH_ANALYZER] Failed to finalize Langfuse: {e}")

            if "batches" in result:
                return result["batches"], langfuse_trace_id
            else:
                logger.warning(
                    "[BATCH_ANALYZER] No batches in response, using fallback"
                )
                return self._fallback_batches(issues), langfuse_trace_id

        except Exception as e:
            logger.error(f"[BATCH_ANALYZER] Error: {e}")
            import traceback

            traceback.print_exc()

            # Finalize tracking even on error
            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass

            # Finalize Langfuse trace on error
            if trace_ctx:
                try:
                    trace_ctx.__exit__(None, None, None)
                    flush_langfuse()
                except Exception:
                    pass

            return self._fallback_batches(issues), langfuse_trace_id

    def _parse_json_response(self, response_text: str) -> dict[str, Any]:
        """Parse JSON from Claude response, handling various formats."""
        content = response_text.strip()

        if not content:
            raise ValueError("Empty response")

        # Extract JSON from markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        else:
            # Look for JSON object
            if "{" in content:
                start = content.find("{")
                brace_count = 0
                for i, char in enumerate(content[start:], start):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            content = content[start : i + 1]
                            break

        return json.loads(content)

    def _fallback_batches(self, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fallback: each issue is its own batch."""
        return [
            {
                "issue_numbers": [issue["number"]],
                "theme": issue.get("title", ""),
                "reasoning": "Fallback: individual batch",
                "confidence": 0.5,
            }
            for issue in issues
        ]

    async def _collect_response_with_usage(self, client: Any) -> tuple[str, int, int]:
        """Collect text response and usage data from Claude client.

        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """
        response_text = ""
        total_input_tokens = 0
        total_output_tokens = 0

        async for msg in client.receive_response():
            msg_type = type(msg).__name__

            # Track message for token usage
            if self.tracker:
                try:
                    await self.tracker.track_message(msg)
                except Exception as e:
                    logger.error(f"[BATCH_ANALYZER] Failed to track message: {e}")

            if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    if type(block).__name__ == "TextBlock" and hasattr(block, "text"):
                        response_text += block.text

            # Extract usage for Langfuse
            if msg_type == "ResultMessage" and hasattr(msg, "usage") and msg.usage:
                usage = msg.usage
                if hasattr(usage, "input_tokens"):
                    total_input_tokens = usage.input_tokens
                if hasattr(usage, "output_tokens"):
                    total_output_tokens = usage.output_tokens

        return response_text, total_input_tokens, total_output_tokens


class BatchStatus(str, Enum):
    """Status of an issue batch."""

    PENDING = "pending"
    ANALYZING = "analyzing"
    CREATING_SPEC = "creating_spec"
    BUILDING = "building"
    QA_REVIEW = "qa_review"
    PR_CREATED = "pr_created"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IssueBatchItem:
    """An issue within a batch."""

    issue_number: int
    title: str
    body: str
    labels: list[str] = field(default_factory=list)
    similarity_to_primary: float = 1.0  # Primary issue has 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_number": self.issue_number,
            "title": self.title,
            "body": self.body,
            "labels": self.labels,
            "similarity_to_primary": self.similarity_to_primary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IssueBatchItem:
        return cls(
            issue_number=data["issue_number"],
            title=data["title"],
            body=data.get("body", ""),
            labels=data.get("labels", []),
            similarity_to_primary=data.get("similarity_to_primary", 1.0),
        )


@dataclass
class IssueBatch:
    """A batch of related issues to be fixed together."""

    batch_id: str
    repo: str
    primary_issue: int  # The "anchor" issue for the batch
    issues: list[IssueBatchItem]
    common_themes: list[str] = field(default_factory=list)
    status: BatchStatus = BatchStatus.PENDING
    spec_id: str | None = None
    pr_number: int | None = None
    error: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    # AI validation results
    validated: bool = False
    validation_confidence: float = 0.0
    validation_reasoning: str = ""
    theme: str = ""  # Refined theme from validation

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "repo": self.repo,
            "primary_issue": self.primary_issue,
            "issues": [i.to_dict() for i in self.issues],
            "common_themes": self.common_themes,
            "status": self.status.value,
            "spec_id": self.spec_id,
            "pr_number": self.pr_number,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "validated": self.validated,
            "validation_confidence": self.validation_confidence,
            "validation_reasoning": self.validation_reasoning,
            "theme": self.theme,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IssueBatch:
        return cls(
            batch_id=data["batch_id"],
            repo=data["repo"],
            primary_issue=data["primary_issue"],
            issues=[IssueBatchItem.from_dict(i) for i in data.get("issues", [])],
            common_themes=data.get("common_themes", []),
            status=BatchStatus(data.get("status", "pending")),
            spec_id=data.get("spec_id"),
            pr_number=data.get("pr_number"),
            error=data.get("error"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            validated=data.get("validated", False),
            validation_confidence=data.get("validation_confidence", 0.0),
            validation_reasoning=data.get("validation_reasoning", ""),
            theme=data.get("theme", ""),
        )

    async def save(self, github_dir: Path) -> None:
        """Save batch to disk atomically with file locking."""
        batches_dir = github_dir / "batches"
        batches_dir.mkdir(parents=True, exist_ok=True)

        # Update timestamp BEFORE serializing to dict
        self.updated_at = datetime.now(timezone.utc).isoformat()

        batch_file = batches_dir / f"batch_{self.batch_id}.json"
        await locked_json_write(batch_file, self.to_dict(), timeout=5.0)

    @classmethod
    def load(cls, github_dir: Path, batch_id: str) -> IssueBatch | None:
        """Load batch from disk."""
        batch_file = github_dir / "batches" / f"batch_{batch_id}.json"
        if not batch_file.exists():
            return None

        with open(batch_file) as f:
            data = json.load(f)
        return cls.from_dict(data)

    def get_issue_numbers(self) -> list[int]:
        """Get all issue numbers in the batch."""
        return [issue.issue_number for issue in self.issues]

    def update_status(self, status: BatchStatus, error: str | None = None) -> None:
        """Update batch status."""
        self.status = status
        if error:
            self.error = error
        self.updated_at = datetime.now(timezone.utc).isoformat()


class IssueBatcher:
    """
    Groups similar issues into batches for combined auto-fix.

    Usage:
        batcher = IssueBatcher(
            github_dir=Path(".auto-claude/github"),
            repo="owner/repo",
        )

        # Analyze and batch issues
        batches = await batcher.create_batches(open_issues)

        # Get batch for an issue
        batch = batcher.get_batch_for_issue(123)
    """

    def __init__(
        self,
        github_dir: Path,
        repo: str,
        project_dir: Path | None = None,
        similarity_threshold: float = SIMILAR_THRESHOLD,
        min_batch_size: int = 1,
        max_batch_size: int = 5,
        api_key: str | None = None,
        # AI validation settings
        validate_batches: bool = True,
        validation_model: str = resolve_model_id("sonnet"),
        validation_thinking_budget: int = 10000,  # Medium thinking
    ):
        self.github_dir = github_dir
        self.repo = repo
        self.project_dir = (
            project_dir or github_dir.parent.parent
        )  # Default to project root
        self.similarity_threshold = similarity_threshold
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.validate_batches_enabled = validate_batches

        # Initialize Claude batch analyzer
        self.analyzer = ClaudeBatchAnalyzer(project_dir=self.project_dir)

        # Initialize batch validator (uses Claude SDK with OAuth token)
        self.validator = (
            BatchValidator(
                project_dir=self.project_dir,
                model=validation_model,
                thinking_budget=validation_thinking_budget,
            )
            if validate_batches
            else None
        )

        # Cache for batches
        self._batch_index: dict[int, str] = {}  # issue_number -> batch_id
        self._load_batch_index()

    def _load_batch_index(self) -> None:
        """Load batch index from disk."""
        index_file = self.github_dir / "batches" / "index.json"
        if index_file.exists():
            with open(index_file) as f:
                data = json.load(f)
            self._batch_index = {
                int(k): v for k, v in data.get("issue_to_batch", {}).items()
            }

    def _save_batch_index(self) -> None:
        """Save batch index to disk."""
        batches_dir = self.github_dir / "batches"
        batches_dir.mkdir(parents=True, exist_ok=True)

        index_file = batches_dir / "index.json"
        with open(index_file, "w") as f:
            json.dump(
                {
                    "issue_to_batch": self._batch_index,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                f,
                indent=2,
            )

    def _generate_batch_id(self, primary_issue: int) -> str:
        """Generate unique batch ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{primary_issue}_{timestamp}"

    def _pre_group_by_labels_and_keywords(
        self,
        issues: list[dict[str, Any]],
    ) -> list[list[dict[str, Any]]]:
        """
        Fast O(n) pre-grouping by labels and title keywords.

        This dramatically reduces the number of Claude API calls needed
        by only comparing issues within the same pre-group.

        Returns list of pre-groups (each group is a list of issues).
        """
        # Priority labels that strongly indicate grouping
        grouping_labels = {
            "bug",
            "feature",
            "enhancement",
            "documentation",
            "refactor",
            "performance",
            "security",
            "ui",
            "ux",
            "frontend",
            "backend",
            "api",
            "database",
            "testing",
            "infrastructure",
            "ci/cd",
            "high priority",
            "low priority",
            "critical",
            "blocker",
        }

        # Group issues by their primary label
        label_groups: dict[str, list[dict[str, Any]]] = {}
        no_label_issues: list[dict[str, Any]] = []

        for issue in issues:
            labels = [
                label.get("name", "").lower() for label in issue.get("labels", [])
            ]

            # Find the first grouping label
            primary_label = None
            for label in labels:
                if label in grouping_labels:
                    primary_label = label
                    break

            if primary_label:
                if primary_label not in label_groups:
                    label_groups[primary_label] = []
                label_groups[primary_label].append(issue)
            else:
                no_label_issues.append(issue)

        # For issues without grouping labels, try keyword-based grouping
        keyword_groups = self._group_by_title_keywords(no_label_issues)

        # Combine all pre-groups
        pre_groups = list(label_groups.values()) + keyword_groups

        # Log pre-grouping results
        total_issues = sum(len(g) for g in pre_groups)
        logger.info(
            f"Pre-grouped {total_issues} issues into {len(pre_groups)} groups "
            f"(label groups: {len(label_groups)}, keyword groups: {len(keyword_groups)})"
        )

        return pre_groups

    def _group_by_title_keywords(
        self,
        issues: list[dict[str, Any]],
    ) -> list[list[dict[str, Any]]]:
        """
        Group issues by common keywords in their titles.

        Returns list of groups.
        """
        if not issues:
            return []

        # Extract keywords from titles
        keyword_map: dict[str, list[dict[str, Any]]] = {}
        ungrouped: list[dict[str, Any]] = []

        # Keywords that indicate related issues
        grouping_keywords = {
            "login",
            "auth",
            "authentication",
            "oauth",
            "session",
            "api",
            "endpoint",
            "request",
            "response",
            "database",
            "db",
            "query",
            "connection",
            "ui",
            "display",
            "render",
            "css",
            "style",
            "error",
            "exception",
            "crash",
            "fail",
            "performance",
            "slow",
            "memory",
            "leak",
            "test",
            "coverage",
            "mock",
            "config",
            "settings",
            "env",
            "build",
            "deploy",
            "ci",
        }

        for issue in issues:
            title = issue.get("title", "").lower()

            # Find matching keywords
            matched_keyword = None
            for keyword in grouping_keywords:
                if keyword in title:
                    matched_keyword = keyword
                    break

            if matched_keyword:
                if matched_keyword not in keyword_map:
                    keyword_map[matched_keyword] = []
                keyword_map[matched_keyword].append(issue)
            else:
                ungrouped.append(issue)

        # Collect groups
        groups = list(keyword_map.values())

        # Add ungrouped issues as individual "groups" of 1
        for issue in ungrouped:
            groups.append([issue])

        return groups

    async def _analyze_issues_with_agents(
        self,
        issues: list[dict[str, Any]],
    ) -> list[list[int]]:
        """
        Analyze issues using Claude agents to suggest batches.

        Uses a two-phase approach:
        1. Fast O(n) pre-grouping by labels and keywords (no AI calls)
        2. One Claude call PER PRE-GROUP to analyze and suggest sub-batches

        For 51 issues, this might result in ~5-10 Claude calls instead of 1275.

        Returns list of clusters (each cluster is a list of issue numbers).
        """
        n = len(issues)

        # Phase 1: Pre-group by labels and keywords (O(n), no AI calls)
        pre_groups = self._pre_group_by_labels_and_keywords(issues)

        # Calculate stats
        total_api_calls_naive = n * (n - 1) // 2
        total_api_calls_new = len([g for g in pre_groups if len(g) > 1])

        logger.info(
            f"Agent-based batching: {total_api_calls_new} Claude calls "
            f"(was {total_api_calls_naive} with pairwise, saved {total_api_calls_naive - total_api_calls_new})"
        )

        # Phase 2: Use Claude agent to analyze each pre-group
        all_batches: list[list[int]] = []

        for group in pre_groups:
            if len(group) == 1:
                # Single issue = single batch, no AI needed
                all_batches.append([group[0]["number"]])
                continue

            # Use Claude to analyze this group and suggest batches
            logger.info(f"Analyzing pre-group of {len(group)} issues with Claude agent")

            batch_suggestions, _trace_id = await self.analyzer.analyze_and_batch_issues(
                issues=group,
                max_batch_size=self.max_batch_size,
            )

            # Convert suggestions to clusters
            for suggestion in batch_suggestions:
                issue_numbers = suggestion.get("issue_numbers", [])
                if issue_numbers:
                    all_batches.append(issue_numbers)
                    logger.info(
                        f"  Batch: {issue_numbers} - {suggestion.get('theme', 'No theme')} "
                        f"(confidence: {suggestion.get('confidence', 0):.0%})"
                    )

        logger.info(f"Created {len(all_batches)} batches from {n} issues")

        return all_batches

    async def _build_similarity_matrix(
        self,
        issues: list[dict[str, Any]],
    ) -> tuple[dict[tuple[int, int], float], dict[int, dict[int, str]]]:
        """
        DEPRECATED: Use _analyze_issues_with_agents instead.

        This method is kept for backwards compatibility but now uses
        the agent-based approach internally.
        """
        # Use the new agent-based approach
        clusters = await self._analyze_issues_with_agents(issues)

        # Build a synthetic similarity matrix from the clusters
        # (for backwards compatibility with _cluster_issues)
        matrix = {}
        reasoning = {}

        for cluster in clusters:
            # Issues in the same cluster are considered similar
            for i, issue_a in enumerate(cluster):
                if issue_a not in reasoning:
                    reasoning[issue_a] = {}
                for issue_b in cluster[i + 1 :]:
                    if issue_b not in reasoning:
                        reasoning[issue_b] = {}
                    # Mark as similar (high score)
                    matrix[(issue_a, issue_b)] = 0.85
                    matrix[(issue_b, issue_a)] = 0.85
                    reasoning[issue_a][issue_b] = "Grouped by Claude agent analysis"
                    reasoning[issue_b][issue_a] = "Grouped by Claude agent analysis"

        return matrix, reasoning

    def _cluster_issues(
        self,
        issues: list[dict[str, Any]],
        similarity_matrix: dict[tuple[int, int], float],
    ) -> list[list[int]]:
        """
        Cluster issues using simple agglomerative approach.

        Returns list of clusters, each cluster is a list of issue numbers.
        """
        issue_numbers = [i["number"] for i in issues]

        # Start with each issue in its own cluster
        clusters: list[set[int]] = [{n} for n in issue_numbers]

        # Merge clusters that have similar issues
        def cluster_similarity(c1: set[int], c2: set[int]) -> float:
            """Average similarity between clusters."""
            scores = []
            for a in c1:
                for b in c2:
                    if (a, b) in similarity_matrix:
                        scores.append(similarity_matrix[(a, b)])
            return sum(scores) / len(scores) if scores else 0.0

        # Iteratively merge most similar clusters
        while len(clusters) > 1:
            best_score = 0.0
            best_pair = (-1, -1)

            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    score = cluster_similarity(clusters[i], clusters[j])
                    if score > best_score:
                        best_score = score
                        best_pair = (i, j)

            # Stop if best similarity is below threshold
            if best_score < self.similarity_threshold:
                break

            # Merge clusters
            i, j = best_pair
            merged = clusters[i] | clusters[j]

            # Don't exceed max batch size
            if len(merged) > self.max_batch_size:
                break

            clusters = [c for k, c in enumerate(clusters) if k not in (i, j)]
            clusters.append(merged)

        return [list(c) for c in clusters]

    def _extract_common_themes(
        self,
        issues: list[dict[str, Any]],
    ) -> list[str]:
        """Extract common themes from issue titles and bodies."""
        # Simple keyword extraction
        all_text = " ".join(
            f"{i.get('title', '')} {i.get('body', '')}" for i in issues
        ).lower()

        # Common tech keywords to look for
        keywords = [
            "authentication",
            "login",
            "oauth",
            "session",
            "api",
            "endpoint",
            "request",
            "response",
            "database",
            "query",
            "connection",
            "timeout",
            "error",
            "exception",
            "crash",
            "bug",
            "performance",
            "slow",
            "memory",
            "leak",
            "ui",
            "display",
            "render",
            "style",
            "test",
            "coverage",
            "assertion",
            "mock",
        ]

        found = [kw for kw in keywords if kw in all_text]
        return found[:5]  # Limit to 5 themes

    async def create_batches(
        self,
        issues: list[dict[str, Any]],
        exclude_issue_numbers: set[int] | None = None,
    ) -> list[IssueBatch]:
        """
        Create batches from a list of issues.

        Args:
            issues: List of issue dicts with number, title, body, labels
            exclude_issue_numbers: Issues to exclude (already in batches)

        Returns:
            List of IssueBatch objects (validated if validation enabled)
        """
        exclude = exclude_issue_numbers or set()

        # Filter to issues not already batched
        available_issues = [
            i
            for i in issues
            if i["number"] not in exclude and i["number"] not in self._batch_index
        ]

        if not available_issues:
            logger.info("No new issues to batch")
            return []

        logger.info(f"Analyzing {len(available_issues)} issues for batching...")

        # Build similarity matrix
        similarity_matrix, _ = await self._build_similarity_matrix(available_issues)

        # Cluster issues
        clusters = self._cluster_issues(available_issues, similarity_matrix)

        # Create initial batches from clusters
        initial_batches = []
        for cluster in clusters:
            if len(cluster) < self.min_batch_size:
                continue

            # Find primary issue (most connected)
            primary = max(
                cluster,
                key=lambda n: sum(
                    1
                    for other in cluster
                    if n != other and (n, other) in similarity_matrix
                ),
            )

            # Build batch items
            cluster_issues = [i for i in available_issues if i["number"] in cluster]
            items = []
            for issue in cluster_issues:
                similarity = (
                    1.0
                    if issue["number"] == primary
                    else similarity_matrix.get((primary, issue["number"]), 0.0)
                )

                items.append(
                    IssueBatchItem(
                        issue_number=issue["number"],
                        title=issue.get("title", ""),
                        body=issue.get("body", ""),
                        labels=[
                            label.get("name", "") for label in issue.get("labels", [])
                        ],
                        similarity_to_primary=similarity,
                    )
                )

            # Sort by similarity (primary first)
            items.sort(key=lambda x: x.similarity_to_primary, reverse=True)

            # Extract themes
            themes = self._extract_common_themes(cluster_issues)

            # Create batch
            batch = IssueBatch(
                batch_id=self._generate_batch_id(primary),
                repo=self.repo,
                primary_issue=primary,
                issues=items,
                common_themes=themes,
            )
            initial_batches.append((batch, cluster_issues))

        # Validate batches with AI if enabled
        validated_batches = []
        if self.validate_batches_enabled and self.validator:
            logger.info(f"Validating {len(initial_batches)} batches with AI...")
            validated_batches = await self._validate_and_split_batches(
                initial_batches, available_issues, similarity_matrix
            )
        else:
            # No validation - use batches as-is
            for batch, _ in initial_batches:
                batch.validated = True
                batch.validation_confidence = 1.0
                batch.validation_reasoning = "Validation disabled"
                batch.theme = batch.common_themes[0] if batch.common_themes else ""
                validated_batches.append(batch)

        # Save validated batches
        final_batches = []
        for batch in validated_batches:
            # Update index
            for item in batch.issues:
                self._batch_index[item.issue_number] = batch.batch_id

            # Save batch
            batch.save(self.github_dir)
            final_batches.append(batch)

            logger.info(
                f"Saved batch {batch.batch_id} with {len(batch.issues)} issues: "
                f"{[i.issue_number for i in batch.issues]} "
                f"(validated={batch.validated}, confidence={batch.validation_confidence:.0%})"
            )

        # Save index
        self._save_batch_index()

        return final_batches

    async def _validate_and_split_batches(
        self,
        initial_batches: list[tuple[IssueBatch, list[dict[str, Any]]]],
        all_issues: list[dict[str, Any]],
        similarity_matrix: dict[tuple[int, int], float],
    ) -> list[IssueBatch]:
        """
        Validate batches with AI and split invalid ones.

        Returns list of validated batches (may be more than input if splits occur).
        """
        validated = []

        for batch, cluster_issues in initial_batches:
            # Prepare issues for validation
            issues_for_validation = [
                {
                    "issue_number": item.issue_number,
                    "title": item.title,
                    "body": item.body,
                    "labels": item.labels,
                    "similarity_to_primary": item.similarity_to_primary,
                }
                for item in batch.issues
            ]

            # Validate with AI
            result = await self.validator.validate_batch(
                batch_id=batch.batch_id,
                primary_issue=batch.primary_issue,
                issues=issues_for_validation,
                themes=batch.common_themes,
            )

            if result.is_valid:
                # Batch is valid - update with validation results
                batch.validated = True
                batch.validation_confidence = result.confidence
                batch.validation_reasoning = result.reasoning
                batch.theme = result.common_theme or (
                    batch.common_themes[0] if batch.common_themes else ""
                )
                validated.append(batch)
                logger.info(f"Batch {batch.batch_id} validated: {result.reasoning}")
            else:
                # Batch is invalid - need to split
                logger.info(
                    f"Batch {batch.batch_id} invalid ({result.reasoning}), splitting..."
                )

                if result.suggested_splits:
                    # Use AI's suggested splits
                    for split_issues in result.suggested_splits:
                        if len(split_issues) < self.min_batch_size:
                            continue

                        # Create new batch from split
                        split_batch = self._create_batch_from_issues(
                            issue_numbers=split_issues,
                            all_issues=cluster_issues,
                            similarity_matrix=similarity_matrix,
                        )
                        if split_batch:
                            split_batch.validated = True
                            split_batch.validation_confidence = result.confidence
                            split_batch.validation_reasoning = (
                                f"Split from {batch.batch_id}: {result.reasoning}"
                            )
                            split_batch.theme = result.common_theme or ""
                            validated.append(split_batch)
                else:
                    # No suggested splits - treat each issue as individual batch
                    for item in batch.issues:
                        single_batch = IssueBatch(
                            batch_id=self._generate_batch_id(item.issue_number),
                            repo=self.repo,
                            primary_issue=item.issue_number,
                            issues=[item],
                            common_themes=[],
                            validated=True,
                            validation_confidence=result.confidence,
                            validation_reasoning=f"Split from invalid batch: {result.reasoning}",
                            theme="",
                        )
                        validated.append(single_batch)

        return validated

    def _create_batch_from_issues(
        self,
        issue_numbers: list[int],
        all_issues: list[dict[str, Any]],
        similarity_matrix: dict[tuple[int, int], float],
    ) -> IssueBatch | None:
        """Create a batch from a subset of issues."""
        # Find issues matching the numbers
        batch_issues = [i for i in all_issues if i["number"] in issue_numbers]
        if not batch_issues:
            return None

        # Find primary (most connected within this subset)
        primary = max(
            issue_numbers,
            key=lambda n: sum(
                1
                for other in issue_numbers
                if n != other and (n, other) in similarity_matrix
            ),
        )

        # Build items
        items = []
        for issue in batch_issues:
            similarity = (
                1.0
                if issue["number"] == primary
                else similarity_matrix.get((primary, issue["number"]), 0.0)
            )

            items.append(
                IssueBatchItem(
                    issue_number=issue["number"],
                    title=issue.get("title", ""),
                    body=issue.get("body", ""),
                    labels=[label.get("name", "") for label in issue.get("labels", [])],
                    similarity_to_primary=similarity,
                )
            )

        items.sort(key=lambda x: x.similarity_to_primary, reverse=True)
        themes = self._extract_common_themes(batch_issues)

        return IssueBatch(
            batch_id=self._generate_batch_id(primary),
            repo=self.repo,
            primary_issue=primary,
            issues=items,
            common_themes=themes,
        )

    def get_batch_for_issue(self, issue_number: int) -> IssueBatch | None:
        """Get the batch containing an issue."""
        batch_id = self._batch_index.get(issue_number)
        if not batch_id:
            return None
        return IssueBatch.load(self.github_dir, batch_id)

    def get_all_batches(self) -> list[IssueBatch]:
        """Get all batches."""
        batches_dir = self.github_dir / "batches"
        if not batches_dir.exists():
            return []

        batches = []
        for batch_file in batches_dir.glob("batch_*.json"):
            try:
                with open(batch_file) as f:
                    data = json.load(f)
                batches.append(IssueBatch.from_dict(data))
            except Exception as e:
                logger.error(f"Error loading batch {batch_file}: {e}")

        return sorted(batches, key=lambda b: b.created_at, reverse=True)

    def get_pending_batches(self) -> list[IssueBatch]:
        """Get batches that need processing."""
        return [
            b
            for b in self.get_all_batches()
            if b.status in (BatchStatus.PENDING, BatchStatus.ANALYZING)
        ]

    def get_active_batches(self) -> list[IssueBatch]:
        """Get batches currently being processed."""
        return [
            b
            for b in self.get_all_batches()
            if b.status
            in (
                BatchStatus.CREATING_SPEC,
                BatchStatus.BUILDING,
                BatchStatus.QA_REVIEW,
            )
        ]

    def is_issue_in_batch(self, issue_number: int) -> bool:
        """Check if an issue is already in a batch."""
        return issue_number in self._batch_index

    def remove_batch(self, batch_id: str) -> bool:
        """Remove a batch and update index."""
        batch = IssueBatch.load(self.github_dir, batch_id)
        if not batch:
            return False

        # Remove from index
        for issue_num in batch.get_issue_numbers():
            self._batch_index.pop(issue_num, None)
        self._save_batch_index()

        # Delete batch file
        batch_file = self.github_dir / "batches" / f"batch_{batch_id}.json"
        if batch_file.exists():
            batch_file.unlink()

        return True
