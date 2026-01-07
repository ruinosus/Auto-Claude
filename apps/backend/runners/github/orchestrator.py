"""
GitHub Automation Orchestrator
==============================

Main coordinator for all GitHub automation workflows:
- PR Review: AI-powered code review
- Issue Triage: Classification and labeling
- Issue Auto-Fix: Automatic spec creation and execution

This is a STANDALONE system - does not modify existing task execution pipeline.

REFACTORED: Service layer architecture - orchestrator delegates to specialized services.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

try:
    # When imported as part of package
    from .bot_detection import BotDetector
    from .context_gatherer import PRContext, PRContextGatherer
    from .gh_client import GHClient
    from .models import (
        AICommentTriage,
        AICommentVerdict,
        AutoFixState,
        GitHubRunnerConfig,
        MergeVerdict,
        PRReviewFinding,
        PRReviewResult,
        ReviewCategory,
        ReviewSeverity,
        StructuralIssue,
        TriageResult,
    )
    from .permissions import GitHubPermissionChecker
    from .rate_limiter import RateLimiter
    from .services import (
        AutoFixProcessor,
        BatchProcessor,
        PRReviewEngine,
        TriageEngine,
    )
except (ImportError, ValueError, SystemError):
    # When imported directly (runner.py adds github dir to path)
    from bot_detection import BotDetector
    from context_gatherer import PRContext, PRContextGatherer
    from gh_client import GHClient
    from models import (
        AICommentTriage,
        AICommentVerdict,
        AutoFixState,
        GitHubRunnerConfig,
        MergeVerdict,
        PRReviewFinding,
        PRReviewResult,
        ReviewCategory,
        ReviewSeverity,
        StructuralIssue,
        TriageResult,
    )
    from permissions import GitHubPermissionChecker
    from rate_limiter import RateLimiter
    from services import (
        AutoFixProcessor,
        BatchProcessor,
        PRReviewEngine,
        TriageEngine,
    )

# ROI Publishing
try:
    from analytics.roi_publisher import publish_github_roi
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


# =============================================================================
# ARTIFACT EXTRACTION FOR GITHUB AUTOMATION
# =============================================================================


def extract_github_review_artifacts(
    result: "PRReviewResult",
    project_dir: Path | None = None,
    trace_id: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Extract artifacts from GitHub PR review results.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    Artifacts extracted:
    - pr_finding ($100 each) - each finding in the review
    - pr_verdict ($50) - APPROVE/REQUEST_CHANGES/COMMENT decision
    - structural_issue ($75) - architecture/scope issues
    - ai_triage ($50) - AI tool comment triages
    - blocker ($150 each) - critical blocking issues

    Args:
        result: PRReviewResult from the review
        project_dir: Project root directory for local storage
        trace_id: Langfuse trace ID for linking

    Returns:
        Tuple of (local_artifacts, langfuse_refs):
        - local_artifacts: Full artifacts for local processing
        - langfuse_refs: Truncated references for Langfuse (or full artifacts if storage unavailable)
    """
    artifacts = []

    # Extract pr_verdict
    artifacts.append({
        "type": "pr_verdict",
        "format": "text",
        "content": result.verdict.value.upper() if result.verdict else result.overall_status.upper(),
        "value_usd": 50,
        "description": f"PR #{result.pr_number} verdict: {result.verdict.value if result.verdict else result.overall_status}",
        "tab": "ops",
        "metadata": {
            "pr_number": result.pr_number,
            "repo": result.repo,
            "verdict_reasoning": result.verdict_reasoning,  # FULL - no truncation
            "risk_assessment": result.risk_assessment,
        },
    })

    # Extract pr_findings - FULL CONTENT, no truncation
    for finding in result.findings:
        # Build FULL content - no truncation!
        content = f"[{finding.severity.value.upper()}] [{finding.category.value}] {finding.title}"
        content += f"\n\nFile: {finding.file}:{finding.line}"
        if finding.end_line:
            content += f"-{finding.end_line}"
        content += f"\n\nDescription: {finding.description}"  # FULL description
        if finding.suggested_fix:
            content += f"\n\nSuggested Fix: {finding.suggested_fix}"  # FULL fix
        if finding.verification_note:
            content += f"\n\nVerification Note: {finding.verification_note}"
        if finding.redundant_with:
            content += f"\n\nRedundant With: {finding.redundant_with}"
        if finding.validation_explanation:
            content += f"\n\nValidation: {finding.validation_explanation}"

        artifacts.append({
            "type": "pr_finding",
            "format": "text",
            "content": content,  # FULL CONTENT - no truncation
            "value_usd": 100,
            "description": f"PR finding: {finding.severity.value} {finding.category.value}",
            "severity": finding.severity.value,
            "category": finding.category.value,
            "tab": "ops",
            "metadata": {
                "finding_id": finding.id,
                "file": finding.file,
                "line": finding.line,
                "end_line": finding.end_line,
                "fixable": finding.fixable,
                "confidence": finding.confidence,
                "validation_status": finding.validation_status,
            },
        })

    # Extract structural_issues - FULL CONTENT
    for issue in result.structural_issues:
        content = f"[{issue.issue_type.upper()}] {issue.title}"
        content += f"\n\nDescription: {issue.description}"  # FULL description
        content += f"\n\nImpact: {issue.impact}"  # FULL impact
        content += f"\n\nSuggestion: {issue.suggestion}"  # FULL suggestion

        artifacts.append({
            "type": "structural_issue",
            "format": "text",
            "content": content,  # FULL CONTENT - no truncation
            "value_usd": 75,
            "description": f"Structural issue: {issue.issue_type}",
            "severity": issue.severity.value,
            "tab": "ops",
            "metadata": {
                "issue_id": issue.id,
                "issue_type": issue.issue_type,
            },
        })

    # Extract ai_triages - FULL CONTENT
    for triage in result.ai_comment_triages:
        content = f"[{triage.verdict.value.upper()}] {triage.tool_name}"
        content += f"\n\nOriginal Comment: {triage.original_comment}"  # FULL comment - no [:50] truncation
        content += f"\n\nReasoning: {triage.reasoning}"  # FULL reasoning
        if triage.response_comment:
            content += f"\n\nResponse: {triage.response_comment}"  # FULL response

        artifacts.append({
            "type": "ai_triage",
            "format": "text",
            "content": content,  # FULL CONTENT - no truncation
            "value_usd": 50,
            "description": f"AI triage: {triage.tool_name} - {triage.verdict.value}",
            "tab": "ops",
            "metadata": {
                "comment_id": triage.comment_id,
                "tool_name": triage.tool_name,
                "verdict": triage.verdict.value,
            },
        })

    # Extract blockers - FULL CONTENT (high value)
    for blocker in result.blockers:
        artifacts.append({
            "type": "blocker",
            "format": "text",
            "content": blocker,  # FULL blocker text - no truncation
            "value_usd": 150,
            "description": f"Blocking issue for PR #{result.pr_number}",
            "tab": "ops",
            "metadata": {
                "pr_number": result.pr_number,
            },
        })

    # Extract summary as artifact - FULL CONTENT
    if result.summary:
        artifacts.append({
            "type": "pr_summary",
            "format": "markdown",
            "content": result.summary,  # FULL summary - no truncation
            "value_usd": 75,
            "description": f"PR #{result.pr_number} review summary",
            "tab": "ops",
            "metadata": {
                "pr_number": result.pr_number,
                "findings_count": len(result.findings),
                "blockers_count": len(result.blockers),
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
                spec_id=None,  # GitHub reviews don't have spec IDs
                trace_id=trace_id,
                agent_type="github_reviewer",
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


def extract_triage_artifacts(
    results: list["TriageResult"],
    project_dir: Path | None = None,
    trace_id: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Extract artifacts from issue triage results.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    Artifacts extracted:
    - triage_result ($50 each) - each issue triage
    - duplicate_detection ($100) - detected duplicates
    - spam_detection ($75) - detected spam

    Args:
        results: List of TriageResult from triage operations
        project_dir: Project root directory for local storage
        trace_id: Langfuse trace ID for linking

    Returns:
        Tuple of (local_artifacts, langfuse_refs)
    """
    artifacts = []

    for result in results:
        # Build FULL content for triage result
        category_value = result.category.value if hasattr(result.category, 'value') else str(result.category)
        content = f"Issue #{result.issue_number}: {category_value}"
        if result.priority:
            content += f"\n\nPriority: {result.priority}"
        if result.is_duplicate:
            content += f"\n\nDuplicate: Yes (of #{result.duplicate_of})"
        if result.is_spam:
            content += "\n\nSpam: Yes"
        if result.is_feature_creep:
            content += "\n\nFeature Creep: Yes"
        if result.suggested_breakdown:
            content += f"\n\nSuggested Breakdown: {', '.join(result.suggested_breakdown)}"
        if result.comment:
            content += f"\n\nComment: {result.comment}"  # FULL comment
        if result.labels_to_add:
            content += f"\n\nLabels to Add: {', '.join(result.labels_to_add)}"
        if result.labels_to_remove:
            content += f"\n\nLabels to Remove: {', '.join(result.labels_to_remove)}"

        artifact = {
            "type": "triage_result",
            "format": "text",
            "content": content,  # FULL CONTENT - no truncation
            "value_usd": 50,
            "description": f"Issue #{result.issue_number} triage: {category_value}",
            "tab": "ops",
            "metadata": {
                "issue_number": result.issue_number,
                "category": category_value,
                "priority": result.priority,
                "confidence": result.confidence,
                "is_duplicate": result.is_duplicate,
                "is_spam": result.is_spam,
                "is_feature_creep": result.is_feature_creep,
            },
        }

        # Increase value for duplicate/spam detection
        if result.is_duplicate:
            artifact["value_usd"] = 100
            artifact["type"] = "duplicate_detection"
        elif result.is_spam:
            artifact["value_usd"] = 75
            artifact["type"] = "spam_detection"

        artifacts.append(artifact)

    # Save artifacts locally and create Langfuse references
    if ARTIFACT_STORAGE_AVAILABLE and project_dir:
        langfuse_refs = []
        for artifact in artifacts:
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_dir,
                spec_id=None,
                trace_id=trace_id,
                agent_type="github_triage",
                session_num=None,
            )

            if artifact_id:
                artifacts_dir = _get_artifacts_dir(project_dir)
                storage_path = str(
                    (artifacts_dir / artifact_id).relative_to(project_dir)
                    if artifacts_dir.exists()
                    else f".auto-claude/artifacts/{artifact_id}.json"
                )
                ref = create_langfuse_reference(artifact, artifact_id, storage_path)
                langfuse_refs.append(ref)
            else:
                langfuse_refs.append(artifact)

        return artifacts, langfuse_refs
    else:
        return artifacts, artifacts


@dataclass
class ProgressCallback:
    """Callback for progress updates."""

    phase: str
    progress: int  # 0-100
    message: str
    issue_number: int | None = None
    pr_number: int | None = None


class GitHubOrchestrator:
    """
    Orchestrates all GitHub automation workflows.

    This is a thin coordinator that delegates to specialized service classes:
    - PRReviewEngine: Multi-pass code review
    - TriageEngine: Issue classification
    - AutoFixProcessor: Automatic issue fixing
    - BatchProcessor: Batch issue processing

    Usage:
        orchestrator = GitHubOrchestrator(
            project_dir=Path("/path/to/project"),
            config=config,
        )

        # Review a PR
        result = await orchestrator.review_pr(pr_number=123)

        # Triage issues
        results = await orchestrator.triage_issues(issue_numbers=[1, 2, 3])

        # Auto-fix an issue
        state = await orchestrator.auto_fix_issue(issue_number=456)
    """

    def __init__(
        self,
        project_dir: Path,
        config: GitHubRunnerConfig,
        progress_callback: Callable[[ProgressCallback], None] | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.config = config
        self.progress_callback = progress_callback

        # GitHub directory for storing state
        self.github_dir = self.project_dir / ".auto-claude" / "github"
        self.github_dir.mkdir(parents=True, exist_ok=True)

        # Initialize GH client with timeout protection
        self.gh_client = GHClient(
            project_dir=self.project_dir,
            default_timeout=30.0,
            max_retries=3,
            enable_rate_limiting=True,
            repo=config.repo,
        )

        # Initialize bot detector for preventing infinite loops
        self.bot_detector = BotDetector(
            state_dir=self.github_dir,
            bot_token=config.bot_token,
            review_own_prs=config.review_own_prs,
        )

        # Initialize permission checker for auto-fix authorization
        self.permission_checker = GitHubPermissionChecker(
            gh_client=self.gh_client,
            repo=config.repo,
            allowed_roles=config.auto_fix_allowed_roles,
            allow_external_contributors=config.allow_external_contributors,
        )

        # Initialize rate limiter singleton
        self.rate_limiter = RateLimiter.get_instance()

        # Initialize service layer
        self.pr_review_engine = PRReviewEngine(
            project_dir=self.project_dir,
            github_dir=self.github_dir,
            config=self.config,
            progress_callback=self.progress_callback,
        )

        self.triage_engine = TriageEngine(
            project_dir=self.project_dir,
            github_dir=self.github_dir,
            config=self.config,
            progress_callback=self.progress_callback,
        )

        self.autofix_processor = AutoFixProcessor(
            github_dir=self.github_dir,
            config=self.config,
            permission_checker=self.permission_checker,
            progress_callback=self.progress_callback,
        )

        self.batch_processor = BatchProcessor(
            project_dir=self.project_dir,
            github_dir=self.github_dir,
            config=self.config,
            progress_callback=self.progress_callback,
        )

    def _report_progress(
        self,
        phase: str,
        progress: int,
        message: str,
        issue_number: int | None = None,
        pr_number: int | None = None,
    ) -> None:
        """Report progress to callback if set."""
        if self.progress_callback:
            self.progress_callback(
                ProgressCallback(
                    phase=phase,
                    progress=progress,
                    message=message,
                    issue_number=issue_number,
                    pr_number=pr_number,
                )
            )

    async def _publish_roi(
        self,
        prs_reviewed: int = 0,
        issues_triaged: int = 0,
        issues_auto_fixed: int = 0,
        duplicates_detected: int = 0,
        spam_detected: int = 0,
        artifact_refs: list[dict] | None = None,
        trace_id: str | None = None,
    ) -> None:
        """Publish ROI metrics for GitHub automation operations.

        Args:
            prs_reviewed: Number of PRs reviewed
            issues_triaged: Number of issues triaged
            issues_auto_fixed: Number of issues auto-fixed
            duplicates_detected: Number of duplicate issues detected
            spam_detected: Number of spam issues detected
            artifact_refs: Langfuse artifact references (with storage_path for local retrieval)
            trace_id: Langfuse trace ID for linking
        """
        if not ROI_PUBLISHER_AVAILABLE:
            return

        try:
            project_id = self.project_dir.name

            # Use publish_feature_roi directly to include artifacts
            try:
                from analytics.roi_publisher import publish_feature_roi
            except ImportError:
                # Fall back to publish_github_roi without artifacts
                result = await publish_github_roi(
                    project_id=project_id,
                    prs_reviewed=prs_reviewed,
                    issues_triaged=issues_triaged,
                    issues_auto_fixed=issues_auto_fixed,
                    model=self.config.model,
                )
                if result.get("success"):
                    roi_pct = result.get("roi_percentage", 0)
                    value = result.get("total_value_usd", 0)
                    print(
                        f"[ROI] GitHub automation: {roi_pct:.0f}% ROI (${value:.2f} value)",
                        flush=True,
                    )
                return

            # Determine feature type based on what was done
            feature_type = "github_pr_review" if prs_reviewed > 0 else "github_issue_triage"

            result = await publish_feature_roi(
                feature_type=feature_type,
                project_id=project_id,
                cost_usd=0.0,  # Cost tracked elsewhere
                tokens=0,  # Tokens tracked elsewhere
                metrics={
                    "prs_reviewed": prs_reviewed,
                    "issues_triaged": issues_triaged,
                    "issues_auto_fixed": issues_auto_fixed,
                    "duplicates_detected": duplicates_detected,
                    "spam_detected": spam_detected,
                },
                model=self.config.model,
                trace_id=trace_id,
                artifacts=artifact_refs,  # Pass artifact refs for Langfuse
            )

            if result.get("success"):
                roi_pct = result.get("roi_percentage", 0)
                value = result.get("total_value_usd", 0)
                artifacts_count = result.get("artifacts_stored", 0)
                print(
                    f"[ROI] GitHub automation: {roi_pct:.0f}% ROI (${value:.2f} value, {artifacts_count} artifacts)",
                    flush=True,
                )
        except Exception as e:
            print(f"[ROI] Failed to publish: {e}", flush=True)

    # =========================================================================
    # GitHub API Helpers
    # =========================================================================

    async def _fetch_pr_data(self, pr_number: int) -> dict:
        """Fetch PR data from GitHub API via gh CLI."""
        return await self.gh_client.pr_get(pr_number)

    async def _fetch_pr_diff(self, pr_number: int) -> str:
        """Fetch PR diff from GitHub."""
        return await self.gh_client.pr_diff(pr_number)

    async def _fetch_issue_data(self, issue_number: int) -> dict:
        """Fetch issue data from GitHub API via gh CLI."""
        return await self.gh_client.issue_get(issue_number)

    async def _fetch_open_issues(self, limit: int = 200) -> list[dict]:
        """Fetch all open issues from the repository (up to 200)."""
        return await self.gh_client.issue_list(state="open", limit=limit)

    async def _post_pr_review(
        self,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
    ) -> int:
        """Post a review to a PR."""
        return await self.gh_client.pr_review(
            pr_number=pr_number,
            body=body,
            event=event.lower(),
        )

    async def _post_issue_comment(self, issue_number: int, body: str) -> None:
        """Post a comment to an issue."""
        await self.gh_client.issue_comment(issue_number, body)

    async def _add_issue_labels(self, issue_number: int, labels: list[str]) -> None:
        """Add labels to an issue."""
        await self.gh_client.issue_add_labels(issue_number, labels)

    async def _remove_issue_labels(self, issue_number: int, labels: list[str]) -> None:
        """Remove labels from an issue."""
        await self.gh_client.issue_remove_labels(issue_number, labels)

    async def _post_ai_triage_replies(
        self, pr_number: int, triages: list[AICommentTriage]
    ) -> None:
        """Post replies to AI tool comments based on triage results."""
        for triage in triages:
            if not triage.response_comment:
                continue

            # Skip trivial verdicts
            if triage.verdict == AICommentVerdict.TRIVIAL:
                continue

            try:
                # Post as inline comment reply
                await self.gh_client.pr_comment_reply(
                    pr_number=pr_number,
                    comment_id=triage.comment_id,
                    body=triage.response_comment,
                )
                print(
                    f"[AI TRIAGE] Posted reply to {triage.tool_name} comment {triage.comment_id}",
                    flush=True,
                )
            except Exception as e:
                print(
                    f"[AI TRIAGE] Failed to post reply to comment {triage.comment_id}: {e}",
                    flush=True,
                )

    # =========================================================================
    # PR REVIEW WORKFLOW
    # =========================================================================

    async def review_pr(
        self, pr_number: int, force_review: bool = False
    ) -> PRReviewResult:
        """
        Perform AI-powered review of a pull request.

        Args:
            pr_number: The PR number to review
            force_review: If True, bypass the "already reviewed" check and force a new review.
                         Useful for re-validating a PR or testing the review system.

        Returns:
            PRReviewResult with findings and overall assessment
        """
        print(
            f"[DEBUG orchestrator] review_pr() called for PR #{pr_number}", flush=True
        )

        self._report_progress(
            "gathering_context",
            10,
            f"Gathering context for PR #{pr_number}...",
            pr_number=pr_number,
        )

        try:
            # Gather PR context
            print("[DEBUG orchestrator] Creating context gatherer...", flush=True)
            gatherer = PRContextGatherer(
                self.project_dir, pr_number, repo=self.config.repo
            )

            print("[DEBUG orchestrator] Gathering PR context...", flush=True)
            pr_context = await gatherer.gather()
            print(
                f"[DEBUG orchestrator] Context gathered: {pr_context.title} "
                f"({len(pr_context.changed_files)} files, {len(pr_context.related_files)} related)",
                flush=True,
            )

            # Bot detection check
            pr_data = {"author": {"login": pr_context.author}}
            should_skip, skip_reason = self.bot_detector.should_skip_pr_review(
                pr_number=pr_number,
                pr_data=pr_data,
                commits=pr_context.commits,
            )

            # Allow forcing a review to bypass "already reviewed" check
            if should_skip and force_review and "Already reviewed" in skip_reason:
                print(
                    f"[BOT DETECTION] Force review requested - bypassing: {skip_reason}",
                    flush=True,
                )
                should_skip = False

            if should_skip:
                print(
                    f"[BOT DETECTION] Skipping PR #{pr_number}: {skip_reason}",
                    flush=True,
                )

                # If skipping because "Already reviewed", return the existing review
                # instead of creating a new empty "skipped" result
                if "Already reviewed" in skip_reason:
                    existing_review = PRReviewResult.load(self.github_dir, pr_number)
                    if existing_review:
                        print(
                            "[BOT DETECTION] Returning existing review (no new commits)",
                            flush=True,
                        )
                        # Don't overwrite - return the existing review as-is
                        # The frontend will see "no new commits" via the newCommitsCheck
                        return existing_review

                # For other skip reasons (bot-authored, cooling off), create a skip result
                result = PRReviewResult(
                    pr_number=pr_number,
                    repo=self.config.repo,
                    success=True,
                    findings=[],
                    summary=f"Skipped review: {skip_reason}",
                    overall_status="comment",
                )
                await result.save(self.github_dir)
                return result

            self._report_progress(
                "analyzing", 30, "Running multi-pass review...", pr_number=pr_number
            )

            # Delegate to PR Review Engine
            print("[DEBUG orchestrator] Running multi-pass review...", flush=True)
            (
                findings,
                structural_issues,
                ai_triages,
                quick_scan,
            ) = await self.pr_review_engine.run_multi_pass_review(pr_context)
            print(
                f"[DEBUG orchestrator] Multi-pass review complete: "
                f"{len(findings)} findings, {len(structural_issues)} structural, {len(ai_triages)} AI triages",
                flush=True,
            )

            self._report_progress(
                "generating",
                70,
                "Generating verdict and summary...",
                pr_number=pr_number,
            )

            # Check CI status (comprehensive - includes workflows awaiting approval)
            ci_status = await self.gh_client.get_pr_checks_comprehensive(pr_number)

            # Log CI status with awaiting approval info
            awaiting = ci_status.get("awaiting_approval", 0)
            pending_without_awaiting = ci_status.get("pending", 0) - awaiting
            ci_log_parts = [
                f"{ci_status.get('passing', 0)} passing",
                f"{ci_status.get('failing', 0)} failing",
            ]
            if pending_without_awaiting > 0:
                ci_log_parts.append(f"{pending_without_awaiting} pending")
            if awaiting > 0:
                ci_log_parts.append(f"{awaiting} awaiting approval")
            print(
                f"[orchestrator] CI status: {', '.join(ci_log_parts)}",
                flush=True,
            )
            if awaiting > 0:
                print(
                    f"[orchestrator] ⚠️ {awaiting} workflow(s) from fork need maintainer approval to run",
                    flush=True,
                )

            # Generate verdict (includes CI status and merge conflict check)
            verdict, verdict_reasoning, blockers = self._generate_verdict(
                findings,
                structural_issues,
                ai_triages,
                ci_status,
                has_merge_conflicts=pr_context.has_merge_conflicts,
            )
            print(
                f"[DEBUG orchestrator] Verdict: {verdict.value} - {verdict_reasoning}",
                flush=True,
            )

            # Calculate risk assessment
            risk_assessment = self._calculate_risk_assessment(
                pr_context, findings, structural_issues
            )

            # Map verdict to overall_status for backward compatibility
            if verdict == MergeVerdict.BLOCKED:
                overall_status = "request_changes"
            elif verdict == MergeVerdict.NEEDS_REVISION:
                overall_status = "request_changes"
            elif verdict == MergeVerdict.MERGE_WITH_CHANGES:
                overall_status = "comment"
            else:
                overall_status = "approve"

            # Generate summary
            summary = self._generate_enhanced_summary(
                verdict=verdict,
                verdict_reasoning=verdict_reasoning,
                blockers=blockers,
                findings=findings,
                structural_issues=structural_issues,
                ai_triages=ai_triages,
                risk_assessment=risk_assessment,
                ci_status=ci_status,
            )

            # Get HEAD SHA for follow-up review tracking
            head_sha = self.bot_detector.get_last_commit_sha(pr_context.commits)

            # Get file blob SHAs for rebase-resistant follow-up reviews
            # Blob SHAs persist across rebases - same content = same blob SHA
            file_blobs: dict[str, str] = {}
            try:
                pr_files = await self.gh_client.get_pr_files(pr_number)
                for file in pr_files:
                    filename = file.get("filename", "")
                    blob_sha = file.get("sha", "")
                    if filename and blob_sha:
                        file_blobs[filename] = blob_sha
                print(
                    f"[Review] Captured {len(file_blobs)} file blob SHAs for follow-up tracking",
                    flush=True,
                )
            except Exception as e:
                print(
                    f"[Review] Warning: Could not capture file blobs: {e}", flush=True
                )

            # Create result
            result = PRReviewResult(
                pr_number=pr_number,
                repo=self.config.repo,
                success=True,
                findings=findings,
                summary=summary,
                overall_status=overall_status,
                verdict=verdict,
                verdict_reasoning=verdict_reasoning,
                blockers=blockers,
                risk_assessment=risk_assessment,
                structural_issues=structural_issues,
                ai_comment_triages=ai_triages,
                quick_scan_summary=quick_scan,
                # Track the commit SHA for follow-up reviews
                reviewed_commit_sha=head_sha,
                # Track file blobs for rebase-resistant follow-up reviews
                reviewed_file_blobs=file_blobs,
            )

            # Post review if configured
            if self.config.auto_post_reviews:
                self._report_progress(
                    "posting", 90, "Posting review to GitHub...", pr_number=pr_number
                )
                review_id = await self._post_pr_review(
                    pr_number=pr_number,
                    body=self._format_review_body(result),
                    event=overall_status.upper(),
                )
                result.review_id = review_id

                # Post AI triage replies
                if ai_triages:
                    self._report_progress(
                        "posting",
                        95,
                        "Posting AI triage replies...",
                        pr_number=pr_number,
                    )
                    await self._post_ai_triage_replies(pr_number, ai_triages)

            # Save result
            await result.save(self.github_dir)

            # Note: PR review memory is now saved by the Electron app after the review completes
            # This ensures memory is saved to the embedded LadybugDB managed by the app

            # Mark as reviewed (head_sha already fetched above)
            if head_sha:
                self.bot_detector.mark_reviewed(pr_number, head_sha)

            self._report_progress(
                "complete", 100, "Review complete!", pr_number=pr_number
            )

            # Extract artifacts and publish ROI metrics
            # Store full artifacts locally, get refs for Langfuse
            artifacts, artifact_refs = extract_github_review_artifacts(
                result=result,
                project_dir=self.project_dir,
                trace_id=None,  # No trace_id available in this context
            )

            await self._publish_roi(
                prs_reviewed=1,
                artifact_refs=artifact_refs,
            )

            return result

        except Exception as e:
            import traceback

            # Log full exception details for debugging
            error_details = f"{type(e).__name__}: {e}"
            full_traceback = traceback.format_exc()
            print(
                f"[ERROR orchestrator] PR review failed for #{pr_number}: {error_details}",
                flush=True,
            )
            print(f"[ERROR orchestrator] Full traceback:\n{full_traceback}", flush=True)

            result = PRReviewResult(
                pr_number=pr_number,
                repo=self.config.repo,
                success=False,
                error=f"{error_details}\n\nTraceback:\n{full_traceback}",
            )
            await result.save(self.github_dir)
            return result

    async def followup_review_pr(self, pr_number: int) -> PRReviewResult:
        """
        Perform a focused follow-up review of a PR.

        Only reviews:
        - Changes since last review (new commits)
        - Whether previous findings are resolved
        - New comments from contributors and AI bots

        Args:
            pr_number: The PR number to review

        Returns:
            PRReviewResult with follow-up analysis

        Raises:
            ValueError: If no previous review exists for this PR
        """
        print(
            f"[DEBUG orchestrator] followup_review_pr() called for PR #{pr_number}",
            flush=True,
        )

        # Load previous review
        previous_review = PRReviewResult.load(self.github_dir, pr_number)

        if not previous_review:
            raise ValueError(
                f"No previous review found for PR #{pr_number}. Run initial review first."
            )

        if not previous_review.reviewed_commit_sha:
            raise ValueError(
                f"Previous review for PR #{pr_number} doesn't have commit SHA. "
                "Re-run initial review with the updated system."
            )

        self._report_progress(
            "gathering_context",
            10,
            f"Gathering follow-up context for PR #{pr_number}...",
            pr_number=pr_number,
        )

        try:
            # Import here to avoid circular imports at module level
            try:
                from .context_gatherer import FollowupContextGatherer
                from .services.followup_reviewer import FollowupReviewer
            except (ImportError, ValueError, SystemError):
                from context_gatherer import FollowupContextGatherer
                from services.followup_reviewer import FollowupReviewer

            # Gather follow-up context
            gatherer = FollowupContextGatherer(
                self.project_dir,
                pr_number,
                previous_review,
            )
            followup_context = await gatherer.gather()

            # Check if context gathering failed
            if followup_context.error:
                print(
                    f"[Followup] Context gathering failed: {followup_context.error}",
                    flush=True,
                )
                # Return an error result instead of silently returning incomplete data
                result = PRReviewResult(
                    pr_number=pr_number,
                    repo=self.config.repo,
                    success=False,
                    findings=[],
                    summary=f"Follow-up review failed: {followup_context.error}",
                    overall_status="comment",
                    verdict=MergeVerdict.NEEDS_REVISION,
                    verdict_reasoning=f"Context gathering failed: {followup_context.error}",
                    error=followup_context.error,
                    reviewed_commit_sha=followup_context.current_commit_sha
                    or previous_review.reviewed_commit_sha,
                    is_followup_review=True,
                )
                await result.save(self.github_dir)
                return result

            # Check if there are changes to review (commits OR files via blob comparison)
            # After a rebase/force-push, commits_since_review will be empty (commit
            # SHAs are rewritten), but files_changed_since_review will contain files
            # that actually changed content based on blob SHA comparison.
            has_commits = bool(followup_context.commits_since_review)
            has_file_changes = bool(followup_context.files_changed_since_review)

            if not has_commits and not has_file_changes:
                base_sha = previous_review.reviewed_commit_sha[:8]
                print(
                    f"[Followup] No changes since last review at {base_sha}",
                    flush=True,
                )
                # Return a result indicating no changes
                no_change_summary = (
                    "No new commits since last review. Previous findings still apply."
                )
                result = PRReviewResult(
                    pr_number=pr_number,
                    repo=self.config.repo,
                    success=True,
                    findings=previous_review.findings,
                    summary=no_change_summary,
                    overall_status=previous_review.overall_status,
                    verdict=previous_review.verdict,
                    verdict_reasoning="No changes since last review.",
                    reviewed_commit_sha=followup_context.current_commit_sha
                    or previous_review.reviewed_commit_sha,
                    is_followup_review=True,
                    unresolved_findings=[f.id for f in previous_review.findings],
                )
                await result.save(self.github_dir)
                return result

            # Build progress message based on what changed
            if has_commits:
                num_commits = len(followup_context.commits_since_review)
                change_desc = f"{num_commits} new commits"
            else:
                # Rebase detected - files changed but no trackable commits
                num_files = len(followup_context.files_changed_since_review)
                change_desc = f"{num_files} files (rebase detected)"

            self._report_progress(
                "analyzing",
                30,
                f"Analyzing {change_desc}...",
                pr_number=pr_number,
            )

            # Fetch CI status BEFORE calling reviewer so AI can factor it into verdict
            ci_status = await self.gh_client.get_pr_checks_comprehensive(pr_number)
            followup_context.ci_status = ci_status

            # Use parallel orchestrator for follow-up if enabled
            if self.config.use_parallel_orchestrator:
                print(
                    "[AI] Using parallel orchestrator for follow-up review (SDK subagents)...",
                    flush=True,
                )
                try:
                    from .services.parallel_followup_reviewer import (
                        ParallelFollowupReviewer,
                    )
                except (ImportError, ValueError, SystemError):
                    from services.parallel_followup_reviewer import (
                        ParallelFollowupReviewer,
                    )

                reviewer = ParallelFollowupReviewer(
                    project_dir=self.project_dir,
                    github_dir=self.github_dir,
                    config=self.config,
                    progress_callback=lambda p: self._report_progress(
                        p.phase if hasattr(p, "phase") else p.get("phase", "analyzing"),
                        p.progress if hasattr(p, "progress") else p.get("progress", 50),
                        p.message
                        if hasattr(p, "message")
                        else p.get("message", "Reviewing..."),
                        pr_number=pr_number,
                    ),
                )
                result = await reviewer.review(followup_context)
            else:
                # Fall back to sequential follow-up reviewer
                reviewer = FollowupReviewer(
                    project_dir=self.project_dir,
                    github_dir=self.github_dir,
                    config=self.config,
                    progress_callback=lambda p: self._report_progress(
                        p.get("phase", "analyzing"),
                        p.get("progress", 50),
                        p.get("message", "Reviewing..."),
                        pr_number=pr_number,
                    ),
                )
                result = await reviewer.review_followup(followup_context)

            # Fallback: ensure CI failures block merge even if AI didn't factor it in
            # (CI status was already passed to AI via followup_context.ci_status)
            failed_checks = followup_context.ci_status.get("failed_checks", [])
            if failed_checks:
                print(
                    f"[Followup] CI checks failing: {failed_checks}",
                    flush=True,
                )
                # Override verdict if CI is failing
                if result.verdict in (
                    MergeVerdict.READY_TO_MERGE,
                    MergeVerdict.MERGE_WITH_CHANGES,
                ):
                    result.verdict = MergeVerdict.BLOCKED
                    result.verdict_reasoning = (
                        f"Blocked: {len(failed_checks)} CI check(s) failing. "
                        "Fix CI before merge."
                    )
                    result.overall_status = "request_changes"
                # Add CI failures to blockers
                for check_name in failed_checks:
                    if f"CI Failed: {check_name}" not in result.blockers:
                        result.blockers.append(f"CI Failed: {check_name}")
                # Update summary to reflect CI status
                ci_warning = (
                    f"\n\n**⚠️ CI Status:** {len(failed_checks)} check(s) failing: "
                    f"{', '.join(failed_checks)}"
                )
                if ci_warning not in result.summary:
                    result.summary += ci_warning

            # Save result
            await result.save(self.github_dir)

            # Note: PR review memory is now saved by the Electron app after the review completes
            # This ensures memory is saved to the embedded LadybugDB managed by the app

            # Mark as reviewed with new commit SHA
            if result.reviewed_commit_sha:
                self.bot_detector.mark_reviewed(pr_number, result.reviewed_commit_sha)

            self._report_progress(
                "complete", 100, "Follow-up review complete!", pr_number=pr_number
            )

            return result

        except Exception as e:
            result = PRReviewResult(
                pr_number=pr_number,
                repo=self.config.repo,
                success=False,
                error=str(e),
                is_followup_review=True,
            )
            await result.save(self.github_dir)
            return result

    def _generate_verdict(
        self,
        findings: list[PRReviewFinding],
        structural_issues: list[StructuralIssue],
        ai_triages: list[AICommentTriage],
        ci_status: dict | None = None,
        has_merge_conflicts: bool = False,
    ) -> tuple[MergeVerdict, str, list[str]]:
        """
        Generate merge verdict based on all findings, CI status, and merge conflicts.

        Blocks on:
        - Merge conflicts (must be resolved before merging)
        - Verification failures
        - Redundancy issues
        - Failing CI checks
        """
        blockers = []
        ci_status = ci_status or {}

        # CRITICAL: Merge conflicts block merging - check first
        if has_merge_conflicts:
            blockers.append(
                "Merge Conflicts: PR has conflicts with base branch that must be resolved"
            )

        # Count by severity
        critical = [f for f in findings if f.severity == ReviewSeverity.CRITICAL]
        high = [f for f in findings if f.severity == ReviewSeverity.HIGH]
        medium = [f for f in findings if f.severity == ReviewSeverity.MEDIUM]
        low = [f for f in findings if f.severity == ReviewSeverity.LOW]

        # NEW: Verification failures are ALWAYS blockers (even if not critical severity)
        verification_failures = [
            f for f in findings if f.category == ReviewCategory.VERIFICATION_FAILED
        ]

        # NEW: High severity redundancy issues are blockers
        redundancy_issues = [
            f
            for f in findings
            if f.category == ReviewCategory.REDUNDANCY
            and f.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH)
        ]

        # Security findings are always blockers
        security_critical = [
            f for f in critical if f.category == ReviewCategory.SECURITY
        ]

        # Structural blockers
        structural_blockers = [
            s
            for s in structural_issues
            if s.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH)
        ]

        # AI comments marked critical
        ai_critical = [t for t in ai_triages if t.verdict == AICommentVerdict.CRITICAL]

        # Build blockers list with NEW categories first
        # CI failures block merging
        failed_checks = ci_status.get("failed_checks", [])
        for check_name in failed_checks:
            blockers.append(f"CI Failed: {check_name}")

        # Workflows awaiting approval block merging (fork PRs)
        awaiting_approval = ci_status.get("awaiting_approval", 0)
        if awaiting_approval > 0:
            blockers.append(
                f"Workflows Pending: {awaiting_approval} workflow(s) awaiting maintainer approval"
            )

        # NEW: Verification failures block merging
        for f in verification_failures:
            note = f" - {f.verification_note}" if f.verification_note else ""
            blockers.append(f"Verification Failed: {f.title} ({f.file}:{f.line}){note}")

        # NEW: Redundancy issues block merging
        for f in redundancy_issues:
            redundant_ref = (
                f" (duplicates {f.redundant_with})" if f.redundant_with else ""
            )
            blockers.append(f"Redundancy: {f.title} ({f.file}:{f.line}){redundant_ref}")

        # Existing blocker categories
        for f in security_critical:
            blockers.append(f"Security: {f.title} ({f.file}:{f.line})")
        for f in critical:
            if (
                f not in security_critical
                and f not in verification_failures
                and f not in redundancy_issues
            ):
                blockers.append(f"Critical: {f.title} ({f.file}:{f.line})")
        for s in structural_blockers:
            blockers.append(f"Structure: {s.title}")
        for t in ai_critical:
            summary = (
                t.original_comment[:50] + "..."
                if len(t.original_comment) > 50
                else t.original_comment
            )
            blockers.append(f"{t.tool_name}: {summary}")

        # Determine verdict with merge conflicts, CI, verification and redundancy checks
        if blockers:
            # Merge conflicts are the highest priority blocker
            if has_merge_conflicts:
                verdict = MergeVerdict.BLOCKED
                reasoning = (
                    "Blocked: PR has merge conflicts with base branch. "
                    "Resolve conflicts before merge."
                )
            # CI failures are always blockers
            elif failed_checks:
                verdict = MergeVerdict.BLOCKED
                reasoning = (
                    f"Blocked: {len(failed_checks)} CI check(s) failing. "
                    "Fix CI before merge."
                )
            # Workflows awaiting approval block merging
            elif awaiting_approval > 0:
                verdict = MergeVerdict.BLOCKED
                reasoning = (
                    f"Blocked: {awaiting_approval} workflow(s) awaiting approval. "
                    "Approve workflows on GitHub to run CI checks."
                )
            # NEW: Prioritize verification failures
            elif verification_failures:
                verdict = MergeVerdict.BLOCKED
                reasoning = (
                    f"Blocked: Cannot verify {len(verification_failures)} claim(s) in PR. "
                    "Evidence required before merge."
                )
            elif security_critical:
                verdict = MergeVerdict.BLOCKED
                reasoning = (
                    f"Blocked by {len(security_critical)} security vulnerabilities"
                )
            elif redundancy_issues:
                verdict = MergeVerdict.BLOCKED
                reasoning = (
                    f"Blocked: {len(redundancy_issues)} redundant implementation(s) detected. "
                    "Remove duplicates before merge."
                )
            elif len(critical) > 0:
                verdict = MergeVerdict.BLOCKED
                reasoning = f"Blocked by {len(critical)} critical issues"
            else:
                verdict = MergeVerdict.NEEDS_REVISION
                reasoning = f"{len(blockers)} issues must be addressed"
        elif high or medium:
            # High and Medium severity findings block merge
            verdict = MergeVerdict.NEEDS_REVISION
            total = len(high) + len(medium)
            reasoning = f"{total} issue(s) must be addressed ({len(high)} required, {len(medium)} recommended)"
            if low:
                reasoning += f", {len(low)} suggestions"
        elif low:
            # Only Low severity suggestions - safe to merge (non-blocking)
            verdict = MergeVerdict.READY_TO_MERGE
            reasoning = (
                f"No blocking issues. {len(low)} non-blocking suggestion(s) to consider"
            )
        else:
            verdict = MergeVerdict.READY_TO_MERGE
            reasoning = "No blocking issues found"

        return verdict, reasoning, blockers

    def _calculate_risk_assessment(
        self,
        context: PRContext,
        findings: list[PRReviewFinding],
        structural_issues: list[StructuralIssue],
    ) -> dict:
        """Calculate risk assessment for the PR."""
        total_changes = context.total_additions + context.total_deletions

        # Complexity
        if total_changes > 500:
            complexity = "high"
        elif total_changes > 200:
            complexity = "medium"
        else:
            complexity = "low"

        # Security impact
        security_findings = [
            f for f in findings if f.category == ReviewCategory.SECURITY
        ]
        if any(f.severity == ReviewSeverity.CRITICAL for f in security_findings):
            security_impact = "critical"
        elif any(f.severity == ReviewSeverity.HIGH for f in security_findings):
            security_impact = "medium"
        elif security_findings:
            security_impact = "low"
        else:
            security_impact = "none"

        # Scope coherence
        scope_issues = [
            s
            for s in structural_issues
            if s.issue_type in ("feature_creep", "scope_creep")
        ]
        if any(
            s.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH)
            for s in scope_issues
        ):
            scope_coherence = "poor"
        elif scope_issues:
            scope_coherence = "mixed"
        else:
            scope_coherence = "good"

        return {
            "complexity": complexity,
            "security_impact": security_impact,
            "scope_coherence": scope_coherence,
        }

    def _generate_enhanced_summary(
        self,
        verdict: MergeVerdict,
        verdict_reasoning: str,
        blockers: list[str],
        findings: list[PRReviewFinding],
        structural_issues: list[StructuralIssue],
        ai_triages: list[AICommentTriage],
        risk_assessment: dict,
        ci_status: dict | None = None,
    ) -> str:
        """Generate enhanced summary with verdict, risk, and actionable next steps."""
        verdict_emoji = {
            MergeVerdict.READY_TO_MERGE: "✅",
            MergeVerdict.MERGE_WITH_CHANGES: "🟡",
            MergeVerdict.NEEDS_REVISION: "🟠",
            MergeVerdict.BLOCKED: "🔴",
        }

        # Generate bottom line for quick scanning
        bottom_line = self._generate_bottom_line(
            verdict=verdict,
            ci_status=ci_status,
            blockers=blockers,
            findings=findings,
        )

        lines = [
            f"### Merge Verdict: {verdict_emoji.get(verdict, '⚪')} {verdict.value.upper().replace('_', ' ')}",
            "",
            f"> {bottom_line}",
            "",
            verdict_reasoning,
            "",
            "### Risk Assessment",
            "| Factor | Level | Notes |",
            "|--------|-------|-------|",
            f"| Complexity | {risk_assessment['complexity'].capitalize()} | Based on lines changed |",
            f"| Security Impact | {risk_assessment['security_impact'].capitalize()} | Based on security findings |",
            f"| Scope Coherence | {risk_assessment['scope_coherence'].capitalize()} | Based on structural review |",
            "",
        ]

        # Blockers
        if blockers:
            lines.append("### 🚨 Blocking Issues (Must Fix)")
            for blocker in blockers:
                lines.append(f"- {blocker}")
            lines.append("")

        # Findings summary
        if findings:
            by_severity = {}
            for f in findings:
                severity = f.severity.value
                if severity not in by_severity:
                    by_severity[severity] = []
                by_severity[severity].append(f)

            lines.append("### Findings Summary")
            for severity in ["critical", "high", "medium", "low"]:
                if severity in by_severity:
                    count = len(by_severity[severity])
                    lines.append(f"- **{severity.capitalize()}**: {count} issue(s)")
            lines.append("")

        # Structural issues
        if structural_issues:
            lines.append("### 🏗️ Structural Issues")
            for issue in structural_issues[:5]:
                lines.append(f"- **{issue.title}**: {issue.description}")
            if len(structural_issues) > 5:
                lines.append(f"- ... and {len(structural_issues) - 5} more")
            lines.append("")

        # AI triages summary
        if ai_triages:
            critical_ai = [
                t for t in ai_triages if t.verdict == AICommentVerdict.CRITICAL
            ]
            important_ai = [
                t for t in ai_triages if t.verdict == AICommentVerdict.IMPORTANT
            ]
            if critical_ai or important_ai:
                lines.append("### 🤖 AI Tool Comments Review")
                if critical_ai:
                    lines.append(f"- **Critical**: {len(critical_ai)} validated issues")
                if important_ai:
                    lines.append(
                        f"- **Important**: {len(important_ai)} recommended fixes"
                    )
                lines.append("")

        lines.append("---")
        lines.append("_Generated by Auto Claude PR Review_")

        return "\n".join(lines)

    def _generate_bottom_line(
        self,
        verdict: MergeVerdict,
        ci_status: dict | None,
        blockers: list[str],
        findings: list[PRReviewFinding],
    ) -> str:
        """Generate a one-line summary for quick scanning at the top of the review."""
        # Check CI status
        ci = ci_status or {}
        pending_ci = ci.get("pending", 0)
        failing_ci = ci.get("failing", 0)
        awaiting_approval = ci.get("awaiting_approval", 0)

        # Count blocking findings and issues
        blocking_findings = [
            f for f in findings if f.severity.value in ("critical", "high", "medium")
        ]
        code_blockers = [
            b for b in blockers if "CI" not in b and "Merge Conflict" not in b
        ]
        has_merge_conflicts = any("Merge Conflict" in b for b in blockers)

        # Determine the bottom line based on verdict and context
        if verdict == MergeVerdict.READY_TO_MERGE:
            return (
                "**✅ Ready to merge** - All checks passing, no blocking issues found."
            )

        elif verdict == MergeVerdict.BLOCKED:
            if has_merge_conflicts:
                return "**🔴 Blocked** - Merge conflicts must be resolved before merge."
            elif failing_ci > 0:
                return f"**🔴 Blocked** - {failing_ci} CI check(s) failing. Fix CI before merge."
            elif awaiting_approval > 0:
                return "**🔴 Blocked** - Awaiting maintainer approval for fork PR workflow."
            elif blocking_findings:
                return f"**🔴 Blocked** - {len(blocking_findings)} critical/high/medium issue(s) must be fixed."
            else:
                return "**🔴 Blocked** - Critical issues must be resolved before merge."

        elif verdict == MergeVerdict.NEEDS_REVISION:
            # Key insight: distinguish "waiting on CI" from "needs code fixes"
            # Check code issues FIRST before checking pending CI
            if blocking_findings:
                return f"**🟠 Needs revision** - {len(blocking_findings)} issue(s) require attention."
            elif code_blockers:
                return f"**🟠 Needs revision** - {len(code_blockers)} structural/other issue(s) require attention."
            elif pending_ci > 0:
                # Only show "Ready once CI passes" when no code issues exist
                return f"**⏳ Ready once CI passes** - {pending_ci} check(s) pending, no blocking code issues."
            else:
                return "**🟠 Needs revision** - See details below."

        elif verdict == MergeVerdict.MERGE_WITH_CHANGES:
            if pending_ci > 0:
                return (
                    "**🟡 Can merge once CI passes** - Minor suggestions, no blockers."
                )
            else:
                return "**🟡 Can merge** - Minor suggestions noted, no blockers."

        return "**📝 Review complete** - See details below."

    def _format_review_body(self, result: PRReviewResult) -> str:
        """Format the review body for posting to GitHub."""
        return result.summary

    # =========================================================================
    # ISSUE TRIAGE WORKFLOW
    # =========================================================================

    async def triage_issues(
        self,
        issue_numbers: list[int] | None = None,
        apply_labels: bool = False,
    ) -> list[TriageResult]:
        """
        Triage issues to detect duplicates, spam, and feature creep.

        Args:
            issue_numbers: Specific issues to triage, or None for all open issues
            apply_labels: Whether to apply suggested labels to GitHub

        Returns:
            List of TriageResult for each issue
        """
        self._report_progress("fetching", 10, "Fetching issues...")

        # Fetch issues
        if issue_numbers:
            issues = []
            for num in issue_numbers:
                issues.append(await self._fetch_issue_data(num))
        else:
            issues = await self._fetch_open_issues()

        if not issues:
            return []

        results = []
        total = len(issues)

        for i, issue in enumerate(issues):
            progress = 20 + int(60 * (i / total))
            self._report_progress(
                "analyzing",
                progress,
                f"Analyzing issue #{issue['number']}...",
                issue_number=issue["number"],
            )

            # Delegate to triage engine
            result = await self.triage_engine.triage_single_issue(issue, issues)
            results.append(result)

            # Apply labels if requested
            if apply_labels and (result.labels_to_add or result.labels_to_remove):
                try:
                    await self._add_issue_labels(issue["number"], result.labels_to_add)
                    await self._remove_issue_labels(
                        issue["number"], result.labels_to_remove
                    )
                except Exception as e:
                    print(f"Failed to apply labels to #{issue['number']}: {e}")

            # Save result
            await result.save(self.github_dir)

        self._report_progress("complete", 100, f"Triaged {len(results)} issues")

        # Extract artifacts and publish ROI metrics
        # Store full artifacts locally, get refs for Langfuse
        artifacts, artifact_refs = extract_triage_artifacts(
            results=results,
            project_dir=self.project_dir,
            trace_id=None,  # No trace_id available in this context
        )

        duplicates = sum(1 for r in results if r.is_duplicate)
        spam = sum(1 for r in results if r.is_spam)
        await self._publish_roi(
            issues_triaged=len(results),
            duplicates_detected=duplicates,
            spam_detected=spam,
            artifact_refs=artifact_refs,
        )

        return results

    # =========================================================================
    # AUTO-FIX WORKFLOW
    # =========================================================================

    async def auto_fix_issue(
        self,
        issue_number: int,
        trigger_label: str | None = None,
    ) -> AutoFixState:
        """
        Automatically fix an issue by creating a spec and running the build pipeline.

        Args:
            issue_number: The issue number to fix
            trigger_label: Label that triggered this auto-fix (for permission checks)

        Returns:
            AutoFixState tracking the fix progress

        Raises:
            PermissionError: If the user who added the trigger label isn't authorized
        """
        # Fetch issue data
        issue = await self._fetch_issue_data(issue_number)

        # Delegate to autofix processor
        return await self.autofix_processor.process_issue(
            issue_number=issue_number,
            issue=issue,
            trigger_label=trigger_label,
        )

    async def get_auto_fix_queue(self) -> list[AutoFixState]:
        """Get all issues in the auto-fix queue."""
        return await self.autofix_processor.get_queue()

    async def check_auto_fix_labels(
        self, verify_permissions: bool = True
    ) -> list[dict]:
        """
        Check for issues with auto-fix labels and return their details.

        Args:
            verify_permissions: Whether to verify who added the trigger label

        Returns:
            List of dicts with issue_number, trigger_label, and authorized status
        """
        issues = await self._fetch_open_issues()
        return await self.autofix_processor.check_labeled_issues(
            all_issues=issues,
            verify_permissions=verify_permissions,
        )

    async def check_new_issues(self) -> list[dict]:
        """
        Check for NEW issues that aren't already in the auto-fix queue.

        Returns:
            List of dicts with just the issue number: [{"number": 123}, ...]
        """
        # Get all open issues
        issues = await self._fetch_open_issues()

        # Get current queue to filter out issues already being processed
        queue = await self.get_auto_fix_queue()
        queued_issue_numbers = {state.issue_number for state in queue}

        # Return just the issue numbers (not full issue objects to avoid huge JSON)
        new_issues = [
            {"number": issue["number"]}
            for issue in issues
            if issue["number"] not in queued_issue_numbers
        ]

        return new_issues

    # =========================================================================
    # BATCH AUTO-FIX WORKFLOW
    # =========================================================================

    async def batch_and_fix_issues(
        self,
        issue_numbers: list[int] | None = None,
    ) -> list:
        """
        Batch similar issues and create combined specs for each batch.

        Args:
            issue_numbers: Specific issues to batch, or None for all open issues

        Returns:
            List of IssueBatch objects that were created
        """
        # Fetch issues
        if issue_numbers:
            issues = []
            for num in issue_numbers:
                issue = await self._fetch_issue_data(num)
                issues.append(issue)
        else:
            issues = await self._fetch_open_issues()

        # Delegate to batch processor
        return await self.batch_processor.batch_and_fix_issues(
            issues=issues,
            fetch_issue_callback=self._fetch_issue_data,
        )

    async def analyze_issues_preview(
        self,
        issue_numbers: list[int] | None = None,
        max_issues: int = 200,
    ) -> dict:
        """
        Analyze issues and return a PREVIEW of proposed batches without executing.

        Args:
            issue_numbers: Specific issues to analyze, or None for all open issues
            max_issues: Maximum number of issues to analyze (default 200)

        Returns:
            Dict with proposed batches and statistics for user review
        """
        # Fetch issues
        if issue_numbers:
            issues = []
            for num in issue_numbers[:max_issues]:
                issue = await self._fetch_issue_data(num)
                issues.append(issue)
        else:
            issues = await self._fetch_open_issues(limit=max_issues)

        # Delegate to batch processor
        return await self.batch_processor.analyze_issues_preview(
            issues=issues,
            max_issues=max_issues,
        )

    async def approve_and_execute_batches(
        self,
        approved_batches: list[dict],
    ) -> list:
        """
        Execute approved batches after user review.

        Args:
            approved_batches: List of batch dicts from analyze_issues_preview

        Returns:
            List of created IssueBatch objects
        """
        return await self.batch_processor.approve_and_execute_batches(
            approved_batches=approved_batches,
        )

    async def get_batch_status(self) -> dict:
        """Get status of all batches."""
        return await self.batch_processor.get_batch_status()

    async def process_pending_batches(self) -> int:
        """Process all pending batches."""
        return await self.batch_processor.process_pending_batches()
