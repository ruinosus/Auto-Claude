"""
PR Review Engine
================

Core logic for multi-pass PR code review.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict

# Analytics tracking
try:
    from analytics import (
        create_feature_tracker,
        FEATURE_PR_REVIEW,
        is_tracking_enabled,
    )
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False

# Langfuse integration (optional - graceful degradation if not available)
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        is_langfuse_ready,
        trace_context,
        log_generation_in_current_trace,
        flush_langfuse,
    )
    LANGFUSE_AVAILABLE = True
    # Initialize Langfuse early (idempotent - safe to call multiple times)
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    _langfuse_init_result = False

# Import ROI publisher
try:
    from analytics.roi_publisher import publish_feature_roi
    ROI_PUBLISHER_AVAILABLE = True
except ImportError:
    ROI_PUBLISHER_AVAILABLE = False

try:
    from ..context_gatherer import PRContext
    from ..models import (
        AICommentTriage,
        GitHubRunnerConfig,
        PRReviewFinding,
        ReviewPass,
        StructuralIssue,
    )
    from .prompt_manager import PromptManager
    from .response_parsers import ResponseParser
except (ImportError, ValueError, SystemError):
    from context_gatherer import PRContext
    from models import (
        AICommentTriage,
        GitHubRunnerConfig,
        PRReviewFinding,
        ReviewPass,
        StructuralIssue,
    )
    from services.prompt_manager import PromptManager
    from services.response_parsers import ResponseParser


# Define a local ProgressCallback to avoid circular import
@dataclass
class ProgressCallback:
    """Callback for progress updates - local definition to avoid circular import."""

    phase: str
    progress: int
    message: str
    pr_number: int | None = None
    extra: dict[str, Any] | None = None


def extract_pr_review_artifacts(
    findings: List["PRReviewFinding"],
    structural_issues: List["StructuralIssue"],
    ai_triages: List["AICommentTriage"],
    quick_scan: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extract valuable artifacts from PR review results.

    Artifact values based on ROI_IMPLEMENTATION_TRACKER.md section 1.1:
    - review_comment: $50 each (general review findings)
    - code_suggestion: $100 (comments with code suggestions)
    - security_issue: $300 (security-related findings)
    - bug_detected: $200 (bug-related findings)
    - approval_decision: $75 (review verdict)

    Args:
        findings: List of PRReviewFinding objects from review passes
        structural_issues: List of StructuralIssue objects
        ai_triages: List of AICommentTriage objects
        quick_scan: Quick scan summary dict with verdict

    Returns:
        List of artifact dicts with type, value_usd, content, and description
    """
    artifacts = []

    # Security-related keywords for detection
    security_keywords = [
        "security", "vulnerability", "injection", "xss", "csrf", "sql",
        "authentication", "authorization", "auth", "token", "secret",
        "password", "credential", "sanitize", "escape", "validate"
    ]

    # Bug-related keywords for detection
    bug_keywords = [
        "bug", "error", "fix", "issue", "broken", "crash", "fail",
        "null", "undefined", "exception", "race condition", "deadlock",
        "memory leak", "infinite loop"
    ]

    # Process each finding
    for finding in findings:
        title_lower = finding.title.lower()
        desc_lower = finding.description.lower()
        combined = f"{title_lower} {desc_lower}"

        # Check if it's a security issue
        is_security = any(kw in combined for kw in security_keywords)
        if is_security or finding.category.value == "security":
            artifacts.append({
                "type": "security_issue",
                "format": "finding",
                "content": f"{finding.title}: {finding.description[:200]}",
                "value_usd": 300,
                "description": f"Security finding: {finding.title}",
                "tab": "ops",
                "severity": finding.severity.value,
                "file": finding.file,
                "line": finding.line,
            })
            continue

        # Check if it's a bug detection
        is_bug = any(kw in combined for kw in bug_keywords)
        if is_bug:
            artifacts.append({
                "type": "bug_detected",
                "format": "finding",
                "content": f"{finding.title}: {finding.description[:200]}",
                "value_usd": 200,
                "description": f"Bug detected: {finding.title}",
                "tab": "dev",
                "severity": finding.severity.value,
                "file": finding.file,
                "line": finding.line,
            })
            continue

        # Check if finding has a code suggestion
        if finding.suggested_fix:
            artifacts.append({
                "type": "code_suggestion",
                "format": "suggestion",
                "content": f"{finding.title}: {finding.suggested_fix[:300]}",
                "value_usd": 100,
                "description": f"Code suggestion: {finding.title}",
                "tab": "dev",
                "severity": finding.severity.value,
                "file": finding.file,
                "line": finding.line,
            })
        else:
            # General review comment
            artifacts.append({
                "type": "review_comment",
                "format": "comment",
                "content": f"{finding.title}: {finding.description[:200]}",
                "value_usd": 50,
                "description": f"Review comment: {finding.title}",
                "tab": "dev",
                "severity": finding.severity.value,
                "file": finding.file,
                "line": finding.line,
            })

    # Process structural issues
    for issue in structural_issues:
        artifacts.append({
            "type": "review_comment",
            "format": "structural",
            "content": f"{issue.title}: {issue.description[:200]}",
            "value_usd": 50,
            "description": f"Structural issue: {issue.title}",
            "tab": "techlead",
            "issue_type": issue.issue_type,
            "severity": issue.severity.value,
        })

    # Process AI comment triages
    for triage in ai_triages:
        # Triaging AI comments is valuable - helps filter noise
        artifacts.append({
            "type": "review_comment",
            "format": "ai_triage",
            "content": f"Triaged {triage.tool_name} comment: {triage.verdict.value}",
            "value_usd": 50,
            "description": f"AI comment triage: {triage.tool_name} - {triage.verdict.value}",
            "tab": "dev",
            "tool_name": triage.tool_name,
            "verdict": triage.verdict.value,
        })

    # Add approval decision artifact based on quick scan verdict
    verdict = quick_scan.get("verdict", "unknown")
    if verdict and verdict != "unknown":
        artifacts.append({
            "type": "approval_decision",
            "format": "verdict",
            "content": f"Review verdict: {verdict}",
            "value_usd": 75,
            "description": f"PR review decision: {verdict}",
            "tab": "business",
            "verdict": verdict,
        })

    return artifacts


class PRReviewEngine:
    """Handles multi-pass PR review workflow."""

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
                feature_type=FEATURE_PR_REVIEW,
                db_path=db_path,
                metadata={"model": config.model}
            )

    def _report_progress(self, phase: str, progress: int, message: str, **kwargs):
        """Report progress if callback is set."""
        if self.progress_callback:
            # ProgressCallback is imported at module level
            self.progress_callback(
                ProgressCallback(
                    phase=phase, progress=progress, message=message, **kwargs
                )
            )

    def needs_deep_analysis(self, scan_result: dict, context: PRContext) -> bool:
        """Determine if PR needs deep analysis pass."""
        total_changes = context.total_additions + context.total_deletions

        if total_changes > 200:
            print(
                f"[AI] Deep analysis needed: {total_changes} lines changed", flush=True
            )
            return True

        complexity = scan_result.get("complexity", "low")
        if complexity in ["high", "medium"]:
            print(f"[AI] Deep analysis needed: {complexity} complexity", flush=True)
            return True

        risk_areas = scan_result.get("risk_areas", [])
        if risk_areas:
            print(
                f"[AI] Deep analysis needed: {len(risk_areas)} risk areas", flush=True
            )
            return True

        return False

    def deduplicate_findings(
        self, findings: list[PRReviewFinding]
    ) -> list[PRReviewFinding]:
        """Remove duplicate findings from multiple passes."""
        seen = set()
        unique = []
        for f in findings:
            key = (f.file, f.line, f.title.lower().strip())
            if key not in seen:
                seen.add(key)
                unique.append(f)
            else:
                print(
                    f"[AI] Skipping duplicate finding: {f.file}:{f.line} - {f.title}",
                    flush=True,
                )
        return unique

    async def run_review_pass(
        self,
        review_pass: ReviewPass,
        context: PRContext,
    ) -> dict | list[PRReviewFinding]:
        """Run a single review pass and return findings or scan result."""
        from core.client import create_client

        pass_prompt = self.prompt_manager.get_review_pass_prompt(review_pass)

        # Format changed files for display
        files_list = []
        for file in context.changed_files[:20]:
            files_list.append(f"- `{file.path}` (+{file.additions}/-{file.deletions})")
        if len(context.changed_files) > 20:
            files_list.append(f"- ... and {len(context.changed_files) - 20} more files")
        files_str = "\n".join(files_list)

        # NEW: Format related files (imports, tests, etc.)
        related_files_str = ""
        if context.related_files:
            related_files_list = [f"- `{f}`" for f in context.related_files[:10]]
            if len(context.related_files) > 10:
                related_files_list.append(
                    f"- ... and {len(context.related_files) - 10} more"
                )
            related_files_str = f"""
### Related Files (imports, tests, configs)
{chr(10).join(related_files_list)}
"""

        # NEW: Format commits for context
        commits_str = ""
        if context.commits:
            commits_list = []
            for commit in context.commits[:5]:  # Show last 5 commits
                sha = commit.get("oid", "")[:7]
                message = commit.get("messageHeadline", "")
                commits_list.append(f"- `{sha}` {message}")
            if len(context.commits) > 5:
                commits_list.append(
                    f"- ... and {len(context.commits) - 5} more commits"
                )
            commits_str = f"""
### Commits in this PR
{chr(10).join(commits_list)}
"""

        # NEW: Handle diff - use individual patches if full diff unavailable
        diff_content = context.diff
        diff_truncated_warning = ""

        # If diff is empty/truncated, build composite from individual file patches
        if context.diff_truncated or not context.diff:
            print(
                f"[AI] Building composite diff from {len(context.changed_files)} file patches...",
                flush=True,
            )
            patches = []
            for file in context.changed_files[:50]:  # Limit to 50 files for large PRs
                if file.patch:
                    patches.append(file.patch)
            diff_content = "\n".join(patches)

            if len(context.changed_files) > 50:
                diff_truncated_warning = (
                    f"\n⚠️ **WARNING**: PR has {len(context.changed_files)} changed files. "
                    "Showing patches for first 50 files only. Review may be incomplete.\n"
                )
            else:
                diff_truncated_warning = (
                    "\n⚠️ **NOTE**: Full PR diff unavailable (PR > 20,000 lines). "
                    "Using individual file patches instead.\n"
                )

        # Truncate very large diffs
        diff_size = len(diff_content)
        if diff_size > 50000:
            diff_content = diff_content[:50000]
            diff_truncated_warning = f"\n⚠️ **WARNING**: Diff truncated from {diff_size} to 50,000 characters. Review may be incomplete.\n"

        pr_context = f"""
## Pull Request #{context.pr_number}

**Title:** {context.title}
**Author:** {context.author}
**Base:** {context.base_branch} ← **Head:** {context.head_branch}
**Changes:** {context.total_additions} additions, {context.total_deletions} deletions across {len(context.changed_files)} files

### Description
{context.description}

### Files Changed
{files_str}
{related_files_str}{commits_str}
### Diff
```diff
{diff_content}
```{diff_truncated_warning}
"""

        full_prompt = pass_prompt + "\n\n---\n\n" + pr_context

        project_root = (
            self.project_dir.parent.parent
            if self.project_dir.name == "backend"
            else self.project_dir
        )

        client = create_client(
            project_dir=project_root,
            spec_dir=self.github_dir,
            model=self.config.model,
            agent_type="pr_reviewer",  # Read-only - no bash, no edits
        )

        # Start tracking session
        if self.tracker:
            try:
                self.tracker.update_metadata("pass", review_pass.value)
                await self.tracker.start_session()
            except Exception:
                pass

        # Initialize Langfuse trace context
        langfuse_ctx = None
        langfuse_trace_id = None
        project_id = self.project_dir.name if self.project_dir else None

        result_text = ""
        generation_count = 0
        try:
            # Create Langfuse trace if available
            if LANGFUSE_AVAILABLE and is_langfuse_ready():
                langfuse_ctx = trace_context(
                    name=f"pr-review-{review_pass.value}-{context.pr_number}",
                    spec_id=f"pr-{context.pr_number}",
                    project_id=project_id,
                    agent_type="pr_review_engine",
                    metadata={
                        "pr_number": context.pr_number,
                        "review_pass": review_pass.value,
                        "model": self.config.model,
                    },
                    tags=["github", "pr_review", review_pass.value],
                    input_data={"prompt": full_prompt[:2000] if len(full_prompt) > 2000 else full_prompt},
                )
                ctx = langfuse_ctx.__enter__()
                if ctx:
                    langfuse_trace_id = ctx.trace_id

            async with client:
                await client.query(full_prompt)

                async for msg in client.receive_response():
                    msg_type = type(msg).__name__

                    # Track message for analytics
                    if self.tracker and msg_type == "AssistantMessage":
                        try:
                            await self.tracker.track_message(msg)
                        except Exception:
                            pass

                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            if hasattr(block, "text"):
                                result_text += block.text
                                # Log generation to Langfuse
                                if LANGFUSE_AVAILABLE and is_langfuse_ready() and langfuse_trace_id:
                                    generation_count += 1
                                    usage = None
                                    if hasattr(msg, "usage"):
                                        usage = {
                                            "input": getattr(msg.usage, "input_tokens", 0),
                                            "output": getattr(msg.usage, "output_tokens", 0),
                                            "total": getattr(msg.usage, "input_tokens", 0) + getattr(msg.usage, "output_tokens", 0),
                                        }
                                    log_generation_in_current_trace(
                                        name=f"review-{review_pass.value}-gen-{generation_count}",
                                        model=self.config.model,
                                        input_data=full_prompt[:500] if generation_count == 1 else f"[continuation {generation_count}]",
                                        output_data=block.text[:1000] if len(block.text) > 1000 else block.text,
                                        usage=usage,
                                        metadata={"pass": review_pass.value, "generation": generation_count}
                                    )

                    # Track result message
                    if self.tracker and msg_type == "ResultMessage":
                        try:
                            await self.tracker.track_message(msg)
                        except Exception:
                            pass

            # Finalize tracking
            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass

            if review_pass == ReviewPass.QUICK_SCAN:
                return self.parser.parse_scan_result(result_text)
            else:
                return self.parser.parse_review_findings(result_text)

        except Exception as e:
            import logging
            import traceback

            # Still finalize tracking on error
            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass

            logger = logging.getLogger(__name__)
            error_msg = f"Review pass {review_pass.value} failed: {e}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"[AI] ERROR: {error_msg}", flush=True)

            # Re-raise to allow caller to handle or track partial failures
            raise RuntimeError(error_msg) from e
        finally:
            # Close Langfuse trace context
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass

    async def run_multi_pass_review(
        self, context: PRContext
    ) -> tuple[
        list[PRReviewFinding], list[StructuralIssue], list[AICommentTriage], dict
    ]:
        """
        Run multi-pass review for comprehensive analysis.

        Optimized for speed: Pass 1 runs first (needed to decide on Pass 4),
        then Passes 2-6 run in parallel.

        Returns:
            Tuple of (findings, structural_issues, ai_triages, quick_scan_summary)
        """
        # Use parallel orchestrator with SDK subagents if enabled
        if self.config.use_parallel_orchestrator:
            print(
                "[AI] Using parallel orchestrator PR review (SDK subagents)...",
                flush=True,
            )
            self._report_progress(
                "orchestrating",
                10,
                "Starting parallel orchestrator review...",
                pr_number=context.pr_number,
            )

            from .parallel_orchestrator_reviewer import ParallelOrchestratorReviewer

            orchestrator = ParallelOrchestratorReviewer(
                project_dir=self.project_dir,
                github_dir=self.github_dir,
                config=self.config,
                progress_callback=self.progress_callback,
            )

            result = await orchestrator.review(context)

            print(
                f"[PR Review Engine] Parallel orchestrator returned {len(result.findings)} findings",
                flush=True,
            )

            quick_scan_summary = {
                "verdict": result.verdict.value if result.verdict else "unknown",
                "findings_count": len(result.findings),
                "strategy": "parallel_orchestrator",
            }

            return (result.findings, [], [], quick_scan_summary)

        # Fall back to multi-pass review
        all_findings = []
        structural_issues = []
        ai_triages = []

        # Pass 1: Quick Scan (must run first - determines if deep analysis needed)
        print("[AI] Pass 1/6: Quick Scan - Understanding scope...", flush=True)
        self._report_progress(
            "analyzing",
            35,
            "Pass 1/6: Quick Scan...",
            pr_number=context.pr_number,
        )
        scan_result = await self.run_review_pass(ReviewPass.QUICK_SCAN, context)

        # Determine which passes to run in parallel
        needs_deep = self.needs_deep_analysis(scan_result, context)
        has_ai_comments = len(context.ai_bot_comments) > 0

        # Build list of parallel tasks
        parallel_tasks = []
        task_names = []

        print("[AI] Running passes 2-6 in parallel...", flush=True)
        self._report_progress(
            "analyzing",
            50,
            "Running Security, Quality, Structural & AI Triage in parallel...",
            pr_number=context.pr_number,
        )

        async def run_security_pass():
            print(
                "[AI] Pass 2/6: Security Review - Analyzing vulnerabilities...",
                flush=True,
            )
            findings = await self.run_review_pass(ReviewPass.SECURITY, context)
            print(f"[AI] Security pass complete: {len(findings)} findings", flush=True)
            return ("security", findings)

        async def run_quality_pass():
            print(
                "[AI] Pass 3/6: Quality Review - Checking code quality...", flush=True
            )
            findings = await self.run_review_pass(ReviewPass.QUALITY, context)
            print(f"[AI] Quality pass complete: {len(findings)} findings", flush=True)
            return ("quality", findings)

        async def run_structural_pass():
            print(
                "[AI] Pass 4/6: Structural Review - Checking for feature creep...",
                flush=True,
            )
            result_text = await self._run_structural_pass(context)
            issues = self.parser.parse_structural_issues(result_text)
            print(f"[AI] Structural pass complete: {len(issues)} issues", flush=True)
            return ("structural", issues)

        async def run_ai_triage_pass():
            print(
                "[AI] Pass 5/6: AI Comment Triage - Verifying other AI comments...",
                flush=True,
            )
            result_text = await self._run_ai_triage_pass(context)
            triages = self.parser.parse_ai_comment_triages(result_text)
            print(
                f"[AI] AI triage complete: {len(triages)} comments triaged", flush=True
            )
            return ("ai_triage", triages)

        async def run_deep_pass():
            print(
                "[AI] Pass 6/6: Deep Analysis - Reviewing business logic...", flush=True
            )
            findings = await self.run_review_pass(ReviewPass.DEEP_ANALYSIS, context)
            print(f"[AI] Deep analysis complete: {len(findings)} findings", flush=True)
            return ("deep", findings)

        # Always run security, quality, structural
        parallel_tasks.append(run_security_pass())
        task_names.append("Security")

        parallel_tasks.append(run_quality_pass())
        task_names.append("Quality")

        parallel_tasks.append(run_structural_pass())
        task_names.append("Structural")

        # Only run AI triage if there are AI comments
        if has_ai_comments:
            parallel_tasks.append(run_ai_triage_pass())
            task_names.append("AI Triage")
            print(
                f"[AI] Found {len(context.ai_bot_comments)} AI comments to triage",
                flush=True,
            )
        else:
            print("[AI] Pass 5/6: Skipped (no AI comments to triage)", flush=True)

        # Only run deep analysis if needed
        if needs_deep:
            parallel_tasks.append(run_deep_pass())
            task_names.append("Deep Analysis")
        else:
            print("[AI] Pass 6/6: Skipped (changes not complex enough)", flush=True)

        # Run all passes in parallel
        print(
            f"[AI] Executing {len(parallel_tasks)} passes in parallel: {', '.join(task_names)}",
            flush=True,
        )
        results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

        # Collect results from all parallel passes
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"[AI] Pass '{task_names[i]}' failed: {result}", flush=True)
            elif isinstance(result, tuple):
                pass_type, data = result
                if pass_type in ("security", "quality", "deep"):
                    all_findings.extend(data)
                elif pass_type == "structural":
                    structural_issues.extend(data)
                elif pass_type == "ai_triage":
                    ai_triages.extend(data)

        self._report_progress(
            "analyzing",
            85,
            "Deduplicating findings...",
            pr_number=context.pr_number,
        )

        # Deduplicate findings
        print(
            f"[AI] Deduplicating {len(all_findings)} findings from all passes...",
            flush=True,
        )
        unique_findings = self.deduplicate_findings(all_findings)
        print(
            f"[AI] Multi-pass review complete: {len(unique_findings)} findings, "
            f"{len(structural_issues)} structural issues, {len(ai_triages)} AI triages",
            flush=True,
        )

        # Publish ROI metrics (in try/except to not fail the review if ROI fails)
        if ROI_PUBLISHER_AVAILABLE:
            try:
                # Extract artifacts from review results
                artifacts = extract_pr_review_artifacts(
                    unique_findings, structural_issues, ai_triages, scan_result
                )

                # Count specific issue types for metrics
                security_issues = sum(
                    1 for f in unique_findings
                    if f.category.value == "security" or any(
                        kw in f"{f.title} {f.description}".lower()
                        for kw in ["security", "vulnerability", "injection", "xss"]
                    )
                )
                bug_issues = sum(
                    1 for f in unique_findings
                    if any(
                        kw in f"{f.title} {f.description}".lower()
                        for kw in ["bug", "error", "fix", "issue", "broken"]
                    )
                )

                # Determine approval status from scan result
                verdict = scan_result.get("verdict", "unknown")
                approval = verdict in ["approved", "approve", "ready_to_merge", "ready"]

                # Get project_id for ROI tracking
                project_id = self.project_dir.name if self.project_dir else "unknown"

                # Publish ROI
                roi_result = await publish_feature_roi(
                    feature_type="github_pr_review",
                    project_id=project_id,
                    cost_usd=0.0,  # Cost is tracked in Langfuse traces
                    tokens=0,  # Tokens are tracked in Langfuse traces
                    metrics={
                        "prs_reviewed": 1,
                        "files_reviewed": len(context.changed_files),
                        "comments_posted": len(unique_findings),
                        "issues_found": len(unique_findings) + len(structural_issues),
                        "security_issues": security_issues,
                        "bug_issues": bug_issues,
                        "structural_issues": len(structural_issues),
                        "ai_triages": len(ai_triages),
                        "approval": approval,
                        "verdict": verdict,
                        "artifacts": artifacts,
                    },
                    spec_id=f"pr-{context.pr_number}",
                    trace_id=None,  # Will create its own trace
                )

                print(
                    f"[AI] ROI published: {roi_result.get('roi_percentage', 0):.1f}% ROI, "
                    f"${roi_result.get('total_value_usd', 0):.2f} value, "
                    f"{len(artifacts)} artifacts extracted",
                    flush=True,
                )

            except Exception as e:
                # Log but don't fail the review
                print(f"[AI] Warning: Failed to publish ROI metrics: {e}", flush=True)

        return unique_findings, structural_issues, ai_triages, scan_result

    async def _run_structural_pass(self, context: PRContext) -> str:
        """Run the structural review pass."""
        from core.client import create_client

        # Load the structural prompt file
        prompt_file = (
            Path(__file__).parent.parent.parent.parent
            / "prompts"
            / "github"
            / "pr_structural.md"
        )
        if prompt_file.exists():
            prompt = prompt_file.read_text(encoding="utf-8")
        else:
            prompt = self.prompt_manager.get_review_pass_prompt(ReviewPass.STRUCTURAL)

        # Build context string
        pr_context = self._build_review_context(context)
        full_prompt = prompt + "\n\n---\n\n" + pr_context

        project_root = (
            self.project_dir.parent.parent
            if self.project_dir.name == "backend"
            else self.project_dir
        )

        client = create_client(
            project_dir=project_root,
            spec_dir=self.github_dir,
            model=self.config.model,
            agent_type="pr_reviewer",  # Read-only - no bash, no edits
        )

        # Start tracking session
        if self.tracker:
            try:
                self.tracker.update_metadata("pass", "structural")
                await self.tracker.start_session()
            except Exception:
                pass

        # Initialize Langfuse trace context
        langfuse_ctx = None
        langfuse_trace_id = None
        project_id = self.project_dir.name if self.project_dir else None

        result_text = ""
        generation_count = 0
        try:
            # Create Langfuse trace if available
            if LANGFUSE_AVAILABLE and is_langfuse_ready():
                langfuse_ctx = trace_context(
                    name=f"pr-structural-{context.pr_number}",
                    spec_id=f"pr-{context.pr_number}",
                    project_id=project_id,
                    agent_type="pr_review_engine",
                    metadata={
                        "pr_number": context.pr_number,
                        "review_pass": "structural",
                        "model": self.config.model,
                    },
                    tags=["github", "pr_review", "structural"],
                    input_data={"prompt": full_prompt[:2000] if len(full_prompt) > 2000 else full_prompt},
                )
                ctx = langfuse_ctx.__enter__()
                if ctx:
                    langfuse_trace_id = ctx.trace_id

            async with client:
                await client.query(full_prompt)
                async for msg in client.receive_response():
                    msg_type = type(msg).__name__

                    # Track message for analytics
                    if self.tracker and msg_type == "AssistantMessage":
                        try:
                            await self.tracker.track_message(msg)
                        except Exception:
                            pass

                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            if hasattr(block, "text"):
                                result_text += block.text
                                # Log generation to Langfuse
                                if LANGFUSE_AVAILABLE and is_langfuse_ready() and langfuse_trace_id:
                                    generation_count += 1
                                    log_generation_in_current_trace(
                                        name=f"structural-gen-{generation_count}",
                                        model=self.config.model,
                                        input_data=full_prompt[:500] if generation_count == 1 else f"[continuation {generation_count}]",
                                        output_data=block.text[:1000] if len(block.text) > 1000 else block.text,
                                        metadata={"pass": "structural", "generation": generation_count}
                                    )

                    if self.tracker and msg_type == "ResultMessage":
                        try:
                            await self.tracker.track_message(msg)
                        except Exception:
                            pass

            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass
        except Exception as e:
            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass
            print(f"[AI] Structural pass error: {e}", flush=True)
        finally:
            # Close Langfuse trace context
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass

        return result_text

    async def _run_ai_triage_pass(self, context: PRContext) -> str:
        """Run the AI comment triage pass."""
        from core.client import create_client

        if not context.ai_bot_comments:
            return "[]"

        # Load the AI triage prompt file
        prompt_file = (
            Path(__file__).parent.parent.parent.parent
            / "prompts"
            / "github"
            / "pr_ai_triage.md"
        )
        if prompt_file.exists():
            prompt = prompt_file.read_text(encoding="utf-8")
        else:
            prompt = self.prompt_manager.get_review_pass_prompt(
                ReviewPass.AI_COMMENT_TRIAGE
            )

        # Build context with AI comments
        ai_comments_context = self._build_ai_comments_context(context)
        pr_context = self._build_review_context(context)
        full_prompt = (
            prompt + "\n\n---\n\n" + ai_comments_context + "\n\n---\n\n" + pr_context
        )

        project_root = (
            self.project_dir.parent.parent
            if self.project_dir.name == "backend"
            else self.project_dir
        )

        client = create_client(
            project_dir=project_root,
            spec_dir=self.github_dir,
            model=self.config.model,
            agent_type="pr_reviewer",  # Read-only - no bash, no edits
        )

        # Start tracking session
        if self.tracker:
            try:
                self.tracker.update_metadata("pass", "ai_triage")
                await self.tracker.start_session()
            except Exception:
                pass

        # Initialize Langfuse trace context
        langfuse_ctx = None
        langfuse_trace_id = None
        project_id = self.project_dir.name if self.project_dir else None

        result_text = ""
        generation_count = 0
        try:
            # Create Langfuse trace if available
            if LANGFUSE_AVAILABLE and is_langfuse_ready():
                langfuse_ctx = trace_context(
                    name=f"pr-ai-triage-{context.pr_number}",
                    spec_id=f"pr-{context.pr_number}",
                    project_id=project_id,
                    agent_type="pr_review_engine",
                    metadata={
                        "pr_number": context.pr_number,
                        "review_pass": "ai_triage",
                        "model": self.config.model,
                        "ai_comments_count": len(context.ai_bot_comments),
                    },
                    tags=["github", "pr_review", "ai_triage"],
                    input_data={"prompt": full_prompt[:2000] if len(full_prompt) > 2000 else full_prompt},
                )
                ctx = langfuse_ctx.__enter__()
                if ctx:
                    langfuse_trace_id = ctx.trace_id

            async with client:
                await client.query(full_prompt)
                async for msg in client.receive_response():
                    msg_type = type(msg).__name__

                    # Track message for analytics
                    if self.tracker and msg_type == "AssistantMessage":
                        try:
                            await self.tracker.track_message(msg)
                        except Exception:
                            pass

                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            if hasattr(block, "text"):
                                result_text += block.text
                                # Log generation to Langfuse
                                if LANGFUSE_AVAILABLE and is_langfuse_ready() and langfuse_trace_id:
                                    generation_count += 1
                                    log_generation_in_current_trace(
                                        name=f"ai-triage-gen-{generation_count}",
                                        model=self.config.model,
                                        input_data=full_prompt[:500] if generation_count == 1 else f"[continuation {generation_count}]",
                                        output_data=block.text[:1000] if len(block.text) > 1000 else block.text,
                                        metadata={"pass": "ai_triage", "generation": generation_count}
                                    )

                    if self.tracker and msg_type == "ResultMessage":
                        try:
                            await self.tracker.track_message(msg)
                        except Exception:
                            pass

            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass
        except Exception as e:
            if self.tracker:
                try:
                    await self.tracker.finalize()
                except Exception:
                    pass
            print(f"[AI] AI triage pass error: {e}", flush=True)
        finally:
            # Close Langfuse trace context
            if langfuse_ctx:
                try:
                    langfuse_ctx.__exit__(None, None, None)
                except Exception:
                    pass

        return result_text

    def _build_ai_comments_context(self, context: PRContext) -> str:
        """Build context string for AI comments that need triaging."""
        lines = [
            "## AI Tool Comments to Triage",
            "",
            f"Found {len(context.ai_bot_comments)} comments from AI code review tools:",
            "",
        ]

        for i, comment in enumerate(context.ai_bot_comments, 1):
            lines.append(f"### Comment {i}: {comment.tool_name}")
            lines.append(f"- **Comment ID**: {comment.comment_id}")
            lines.append(f"- **Author**: {comment.author}")
            lines.append(f"- **File**: {comment.file or 'General'}")
            if comment.line:
                lines.append(f"- **Line**: {comment.line}")
            lines.append("")
            lines.append("**Comment:**")
            lines.append(comment.body)
            lines.append("")

        return "\n".join(lines)

    def _build_review_context(self, context: PRContext) -> str:
        """Build full review context string."""
        files_list = []
        for file in context.changed_files[:30]:
            files_list.append(
                f"- `{file.path}` (+{file.additions}/-{file.deletions}) - {file.status}"
            )
        if len(context.changed_files) > 30:
            files_list.append(f"- ... and {len(context.changed_files) - 30} more files")
        files_str = "\n".join(files_list)

        # Handle diff - use individual patches if full diff unavailable
        diff_content = context.diff
        if context.diff_truncated or not context.diff:
            patches = []
            for file in context.changed_files[:50]:
                if file.patch:
                    patches.append(file.patch)
            diff_content = "\n".join(patches)

        return f"""
## Pull Request #{context.pr_number}

**Title:** {context.title}
**Author:** {context.author}
**Base:** {context.base_branch} ← **Head:** {context.head_branch}
**Status:** {context.state}
**Changes:** {context.total_additions} additions, {context.total_deletions} deletions across {len(context.changed_files)} files

### Description
{context.description}

### Files Changed
{files_str}

### Full Diff
```diff
{diff_content[:100000]}
```
"""
