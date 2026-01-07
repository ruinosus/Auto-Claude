#!/usr/bin/env python3
"""
GitHub Automation Runner
========================

CLI interface for GitHub automation features:
- PR Review: AI-powered code review
- Issue Triage: Classification, duplicate/spam detection
- Issue Auto-Fix: Automatic spec creation from issues
- Issue Batching: Group similar issues and create combined specs

Usage:
    # Review a specific PR
    python runner.py review-pr 123

    # Triage all open issues
    python runner.py triage --apply-labels

    # Triage specific issues
    python runner.py triage 1 2 3

    # Start auto-fix for an issue
    python runner.py auto-fix 456

    # Check for issues with auto-fix labels
    python runner.py check-auto-fix-labels

    # Show auto-fix queue
    python runner.py queue

    # Batch similar issues and create combined specs
    python runner.py batch-issues

    # Batch specific issues
    python runner.py batch-issues 1 2 3 4 5

    # Show batch status
    python runner.py batch-status
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode output (emojis, special chars)
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load .env file with centralized error handling
from cli.utils import import_dotenv

load_dotenv = import_dotenv()

env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Clean up conflicting env vars (Foundry vs standard mode)
from core.auth import cleanup_conflicting_env_vars
cleanup_conflicting_env_vars()

from debug import debug_error

# ROI publisher (optional - graceful degradation if not available)
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
    save_artifact_safe = None
    create_langfuse_reference = None
    _get_artifacts_dir = None

# Langfuse tracing (optional - graceful degradation if not available)
try:
    from analytics.langfuse_integration import (
        init_langfuse,
        is_langfuse_ready,
        trace_context,
        flush_langfuse,
    )
    LANGFUSE_AVAILABLE = True
    _langfuse_init_result = init_langfuse()
except ImportError:
    LANGFUSE_AVAILABLE = False
    _langfuse_init_result = False
    is_langfuse_ready = lambda: False
    trace_context = None
    flush_langfuse = lambda: None


# =============================================================================
# ARTIFACT EXTRACTION
# =============================================================================


def extract_pr_review_artifacts(
    result,
    project_dir: Path | None = None,
    trace_id: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Extract artifacts from a PR review result.

    Artifacts extracted:
    - pr_review_finding ($100-200) - each finding by severity
    - pr_verdict ($75) - overall review verdict
    - structural_issue ($50) - architectural issues detected
    - ai_triage ($25) - AI tool comment triages

    Returns:
        Tuple of (full_artifacts, langfuse_refs)
    """
    import time

    artifacts = []

    if not result or not result.success:
        return [], []

    # Extract pr_verdict artifact
    if result.overall_status:
        verdict_content = f"Verdict: {result.overall_status.upper()}\n\n"
        if result.verdict_reasoning:
            verdict_content += f"Reasoning: {result.verdict_reasoning}\n\n"
        if result.blockers:
            verdict_content += "Blockers:\n" + "\n".join(f"- {b}" for b in result.blockers)

        artifacts.append({
            "type": "pr_verdict",
            "format": "markdown",
            "content": verdict_content,
            "value_usd": 75,
            "description": f"PR #{result.pr_number} review verdict: {result.overall_status}",
            "tab": "techlead",
            "metadata": {
                "pr_number": result.pr_number,
                "verdict": result.overall_status,
                "blockers_count": len(result.blockers) if result.blockers else 0,
            },
        })

    # Extract pr_review_finding artifacts from findings
    severity_values = {
        "critical": 200,
        "high": 150,
        "medium": 100,
        "low": 50,
    }

    for finding in result.findings or []:
        severity = finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity)
        category = finding.category.value if hasattr(finding.category, 'value') else str(finding.category)

        content = f"## [{severity.upper()}] {finding.title}\n\n"
        content += f"**Category:** {category}\n"
        content += f"**File:** {finding.file}:{finding.line}\n\n"
        content += f"**Description:**\n{finding.description}\n\n"
        if finding.suggested_fix:
            content += f"**Suggested Fix:**\n{finding.suggested_fix}\n"

        value = severity_values.get(severity.lower(), 50)
        # Security findings are worth more
        if category.lower() == "security":
            value += 100

        artifacts.append({
            "type": "pr_review_finding",
            "format": "markdown",
            "content": content,
            "value_usd": value,
            "description": f"[{severity}] {finding.title}",
            "tab": "dev" if category.lower() != "security" else "ops",
            "metadata": {
                "pr_number": result.pr_number,
                "severity": severity,
                "category": category,
                "file": finding.file,
                "line": finding.line,
            },
        })

    # Extract structural_issue artifacts
    for issue in result.structural_issues or []:
        severity = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)

        content = f"## {issue.title}\n\n"
        content += f"**Type:** {issue.issue_type}\n"
        content += f"**Severity:** {severity}\n\n"
        content += f"{issue.description}\n"
        if issue.recommendation:
            content += f"\n**Recommendation:**\n{issue.recommendation}\n"

        artifacts.append({
            "type": "structural_issue",
            "format": "markdown",
            "content": content,
            "value_usd": 50,
            "description": f"Structural: {issue.title}",
            "tab": "techlead",
            "metadata": {
                "pr_number": result.pr_number,
                "issue_type": issue.issue_type,
                "severity": severity,
            },
        })

    # Extract ai_triage artifacts
    for triage in result.ai_comment_triages or []:
        verdict_val = triage.verdict.value if hasattr(triage.verdict, 'value') else str(triage.verdict)

        content = f"## {triage.tool_name} Comment Triage\n\n"
        content += f"**Verdict:** {verdict_val}\n"
        content += f"**Original Comment:**\n{triage.original_comment}\n\n"
        content += f"**Analysis:**\n{triage.reasoning}\n"
        if triage.response_comment:
            content += f"\n**Response:**\n{triage.response_comment}\n"

        artifacts.append({
            "type": "ai_triage",
            "format": "markdown",
            "content": content,
            "value_usd": 25,
            "description": f"AI triage: {triage.tool_name} ({verdict_val})",
            "tab": "dev",
            "metadata": {
                "pr_number": result.pr_number,
                "tool_name": triage.tool_name,
                "verdict": verdict_val,
            },
        })

    # Save artifacts locally and create Langfuse references
    if ARTIFACT_STORAGE_AVAILABLE and project_dir and save_artifact_safe:
        langfuse_refs = []
        for artifact in artifacts:
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_dir,
                spec_id=None,  # PR reviews don't have spec_id
                trace_id=trace_id,
                agent_type="github_pr_review",
                session_num=result.pr_number,
            )

            if artifact_id and create_langfuse_reference and _get_artifacts_dir:
                artifacts_dir = _get_artifacts_dir(project_dir)
                from datetime import datetime
                date_str = datetime.now().strftime("%Y-%m-%d")
                storage_path = f".auto-claude/artifacts/{date_str}/{artifact_id}.json"
                ref = create_langfuse_reference(artifact, artifact_id, storage_path)
                langfuse_refs.append(ref)
            else:
                langfuse_refs.append(artifact)

        return artifacts, langfuse_refs
    else:
        return artifacts, artifacts


def extract_triage_artifacts(
    results: list,
    project_dir: Path | None = None,
    trace_id: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Extract artifacts from issue triage results.

    Artifacts extracted:
    - issue_classification ($50) - category and confidence
    - duplicate_detection ($75) - duplicate issue detection
    - spam_detection ($100) - spam/invalid issue detection

    Returns:
        Tuple of (full_artifacts, langfuse_refs)
    """
    artifacts = []

    for result in results or []:
        category = result.category.value if hasattr(result.category, 'value') else str(result.category)

        # Base classification artifact
        content = f"## Issue #{result.issue_number} Classification\n\n"
        content += f"**Category:** {category}\n"
        content += f"**Confidence:** {result.confidence:.0%}\n\n"

        if result.labels_to_add:
            content += f"**Labels to Add:** {', '.join(result.labels_to_add)}\n"
        if result.labels_to_remove:
            content += f"**Labels to Remove:** {', '.join(result.labels_to_remove)}\n"

        if result.reasoning:
            content += f"\n**Reasoning:**\n{result.reasoning}\n"

        value = 50
        artifact_type = "issue_classification"

        # Duplicate detection is more valuable
        if result.is_duplicate:
            artifact_type = "duplicate_detection"
            value = 75
            content += f"\n**Duplicate of:** #{result.duplicate_of}\n"

        # Spam detection is most valuable
        if result.is_spam:
            artifact_type = "spam_detection"
            value = 100

        # Feature creep detection
        if result.is_feature_creep:
            value += 25
            content += "\n**Note:** Flagged as feature creep\n"

        artifacts.append({
            "type": artifact_type,
            "format": "markdown",
            "content": content,
            "value_usd": value,
            "description": f"Issue #{result.issue_number}: {category}",
            "tab": "business",
            "metadata": {
                "issue_number": result.issue_number,
                "category": category,
                "confidence": result.confidence,
                "is_duplicate": result.is_duplicate,
                "is_spam": result.is_spam,
                "is_feature_creep": result.is_feature_creep,
            },
        })

    # Save artifacts locally and create Langfuse references
    if ARTIFACT_STORAGE_AVAILABLE and project_dir and save_artifact_safe:
        langfuse_refs = []
        for artifact in artifacts:
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_dir,
                spec_id=None,
                trace_id=trace_id,
                agent_type="github_issue_triage",
                session_num=None,
            )

            if artifact_id and create_langfuse_reference and _get_artifacts_dir:
                artifacts_dir = _get_artifacts_dir(project_dir)
                from datetime import datetime
                date_str = datetime.now().strftime("%Y-%m-%d")
                storage_path = f".auto-claude/artifacts/{date_str}/{artifact_id}.json"
                ref = create_langfuse_reference(artifact, artifact_id, storage_path)
                langfuse_refs.append(ref)
            else:
                langfuse_refs.append(artifact)

        return artifacts, langfuse_refs
    else:
        return artifacts, artifacts


def extract_batch_preview_artifacts(
    result: dict,
    project_dir: Path | None = None,
    trace_id: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Extract artifacts from batch preview analysis.

    Artifacts extracted:
    - batch_proposal ($100) - each proposed batch grouping
    - analysis_summary ($50) - overall analysis summary

    Returns:
        Tuple of (full_artifacts, langfuse_refs)
    """
    artifacts = []

    if not result or not result.get("success"):
        return [], []

    # Analysis summary artifact
    summary_content = f"## Issue Analysis Summary\n\n"
    summary_content += f"**Total Issues:** {result.get('total_issues', 0)}\n"
    summary_content += f"**Analyzed:** {result.get('analyzed_issues', 0)}\n"
    summary_content += f"**Already Batched:** {result.get('already_batched', 0)}\n"
    summary_content += f"**Proposed Batches:** {len(result.get('proposed_batches', []))}\n"
    summary_content += f"**Single Issues:** {len(result.get('single_issues', []))}\n"

    artifacts.append({
        "type": "analysis_summary",
        "format": "markdown",
        "content": summary_content,
        "value_usd": 50,
        "description": "Issue batch analysis summary",
        "tab": "business",
        "metadata": {
            "total_issues": result.get('total_issues', 0),
            "proposed_batches": len(result.get('proposed_batches', [])),
        },
    })

    # Batch proposal artifacts
    for batch in result.get("proposed_batches", []):
        content = f"## Batch: {batch.get('theme', 'No theme')}\n\n"
        content += f"**Primary Issue:** #{batch.get('primary_issue')}\n"
        content += f"**Issue Count:** {batch.get('issue_count', 0)}\n"
        content += f"**Confidence:** {batch.get('confidence', 0):.0%}\n"
        content += f"**Validated:** {'Yes' if batch.get('validated') else 'Needs Review'}\n\n"
        content += f"**Reasoning:**\n{batch.get('reasoning', 'N/A')}\n\n"
        content += "**Issues:**\n"

        for item in batch.get("issues", []):
            similarity = item.get("similarity_to_primary", 0)
            content += f"- #{item['issue_number']}: {item.get('title', '?')} ({similarity:.0%})\n"

        artifacts.append({
            "type": "batch_proposal",
            "format": "markdown",
            "content": content,
            "value_usd": 100,
            "description": f"Batch: {batch.get('theme', 'Unknown')}",
            "tab": "business",
            "metadata": {
                "primary_issue": batch.get('primary_issue'),
                "issue_count": batch.get('issue_count', 0),
                "confidence": batch.get('confidence', 0),
                "theme": batch.get('theme'),
            },
        })

    # Save artifacts locally and create Langfuse references
    if ARTIFACT_STORAGE_AVAILABLE and project_dir and save_artifact_safe:
        langfuse_refs = []
        for artifact in artifacts:
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_dir,
                spec_id=None,
                trace_id=trace_id,
                agent_type="github_batch_issues",
                session_num=None,
            )

            if artifact_id and create_langfuse_reference and _get_artifacts_dir:
                artifacts_dir = _get_artifacts_dir(project_dir)
                from datetime import datetime
                date_str = datetime.now().strftime("%Y-%m-%d")
                storage_path = f".auto-claude/artifacts/{date_str}/{artifact_id}.json"
                ref = create_langfuse_reference(artifact, artifact_id, storage_path)
                langfuse_refs.append(ref)
            else:
                langfuse_refs.append(artifact)

        return artifacts, langfuse_refs
    else:
        return artifacts, artifacts


async def publish_github_roi_with_artifacts(
    project_dir: Path,
    feature_type: str,
    metrics: dict,
    artifacts: list,
    langfuse_refs: list,
    duration_seconds: float = 0.0,
    model: str = "",
    trace_id: str | None = None,
) -> dict:
    """
    Publish ROI metrics with artifact references.

    Args:
        project_dir: Project directory
        feature_type: Type of GitHub feature (github_pr_review, github_issue_triage, etc.)
        metrics: Feature-specific metrics dict
        artifacts: Full artifacts for value calculation
        langfuse_refs: Truncated references for Langfuse
        duration_seconds: Execution duration
        model: Model used
        trace_id: Langfuse trace ID

    Returns:
        Dict with ROI calculation results
    """
    if not ROI_PUBLISHER_AVAILABLE:
        return {"success": False, "error": "ROI publisher not available"}

    try:
        project_id = project_dir.name

        # Calculate total artifact value
        total_artifact_value = sum(a.get("value_usd", 0) for a in artifacts)

        # Estimate cost and tokens (rough estimate)
        estimated_tokens = metrics.get("estimated_tokens", 1000)
        estimated_cost = (estimated_tokens / 1000) * 0.003

        result = await publish_feature_roi(
            feature_type=feature_type,
            project_id=project_id,
            cost_usd=estimated_cost,
            tokens=estimated_tokens,
            metrics={
                **metrics,
                "artifacts_count": len(artifacts),
                "artifact_value_usd": total_artifact_value,
            },
            duration_seconds=duration_seconds,
            model=model,
            trace_id=trace_id,
            artifacts=langfuse_refs,  # Pass refs for Langfuse
        )

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


# Add github runner directory to path for direct imports
sys.path.insert(0, str(Path(__file__).parent))

# Now import models and orchestrator directly (they use relative imports internally)
from models import GitHubRunnerConfig
from orchestrator import GitHubOrchestrator, ProgressCallback


def print_progress(callback: ProgressCallback) -> None:
    """Print progress updates to console."""
    prefix = ""
    if callback.pr_number:
        prefix = f"[PR #{callback.pr_number}] "
    elif callback.issue_number:
        prefix = f"[Issue #{callback.issue_number}] "

    print(f"{prefix}[{callback.progress:3d}%] {callback.message}", flush=True)


def get_config(args) -> GitHubRunnerConfig:
    """Build config from CLI args and environment."""
    import shutil
    import subprocess

    token = args.token or os.environ.get("GITHUB_TOKEN", "")
    bot_token = args.bot_token or os.environ.get("GITHUB_BOT_TOKEN")
    repo = args.repo or os.environ.get("GITHUB_REPO", "")

    # Find gh CLI - use shutil.which for cross-platform support
    gh_path = shutil.which("gh")
    if not gh_path and sys.platform == "win32":
        # Fallback: check common Windows installation paths
        common_paths = [
            r"C:\Program Files\GitHub CLI\gh.exe",
            r"C:\Program Files (x86)\GitHub CLI\gh.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\GitHub CLI\gh.exe"),
        ]
        for path in common_paths:
            if os.path.exists(path):
                gh_path = path
                break

    if os.environ.get("DEBUG"):
        print(f"[DEBUG] gh CLI path: {gh_path}", flush=True)
        print(
            f"[DEBUG] PATH env: {os.environ.get('PATH', 'NOT SET')[:200]}...",
            flush=True,
        )

    if not token and gh_path:
        # Try to get from gh CLI
        try:
            result = subprocess.run(
                [gh_path, "auth", "token"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                token = result.stdout.strip()
        except FileNotFoundError:
            pass  # gh not installed or not in PATH

    if not repo and gh_path:
        # Try to detect from git remote
        try:
            result = subprocess.run(
                [
                    gh_path,
                    "repo",
                    "view",
                    "--json",
                    "nameWithOwner",
                    "-q",
                    ".nameWithOwner",
                ],
                cwd=args.project,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                repo = result.stdout.strip()
            elif os.environ.get("DEBUG"):
                print(f"[DEBUG] gh repo view failed: {result.stderr}", flush=True)
        except FileNotFoundError:
            pass  # gh not installed or not in PATH

    if not token:
        print("Error: No GitHub token found. Set GITHUB_TOKEN or run 'gh auth login'")
        sys.exit(1)

    if not repo:
        print("Error: No GitHub repo found. Set GITHUB_REPO or run from a git repo.")
        sys.exit(1)

    return GitHubRunnerConfig(
        token=token,
        repo=repo,
        bot_token=bot_token,
        model=args.model,
        thinking_level=args.thinking_level,
        auto_fix_enabled=getattr(args, "auto_fix_enabled", False),
        auto_fix_labels=getattr(args, "auto_fix_labels", ["auto-fix"]),
        auto_post_reviews=getattr(args, "auto_post", False),
    )


async def cmd_review_pr(args) -> int:
    """Review a pull request."""
    import sys
    import time

    # Force unbuffered output so Electron sees it in real-time
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True)

    debug = os.environ.get("DEBUG")
    if debug:
        print(f"[DEBUG] Starting PR review for PR #{args.pr_number}", flush=True)
        print(f"[DEBUG] Project directory: {args.project}", flush=True)
        print("[DEBUG] Building config...", flush=True)

    config = get_config(args)

    if debug:
        print(
            f"[DEBUG] Config built: repo={config.repo}, model={config.model}",
            flush=True,
        )
        print("[DEBUG] Creating orchestrator...", flush=True)

    orchestrator = GitHubOrchestrator(
        project_dir=args.project,
        config=config,
        progress_callback=print_progress,
    )

    if debug:
        print("[DEBUG] Orchestrator created", flush=True)
        print(
            f"[DEBUG] Calling orchestrator.review_pr({args.pr_number})...", flush=True
        )

    # Track start time for ROI metrics
    start_time = time.time()

    # Setup Langfuse trace context if available
    langfuse_trace_id = None
    langfuse_ctx = None
    if LANGFUSE_AVAILABLE and is_langfuse_ready() and trace_context:
        project_id = args.project.name if hasattr(args.project, 'name') else Path(args.project).name
        langfuse_ctx = trace_context(
            name=f"github-pr-review-{args.pr_number}",
            project_id=project_id,
            agent_type="github_pr_review",
            metadata={
                "pr_number": args.pr_number,
                "model": config.model,
                "force_review": getattr(args, "force", False),
            },
            tags=["github", "pr-review", f"pr:{args.pr_number}"],
            input_data={"pr_number": args.pr_number, "repo": config.repo},
        )
        ctx = langfuse_ctx.__enter__()
        if ctx:
            langfuse_trace_id = ctx.trace_id
            if debug:
                print(f"[DEBUG] Langfuse trace created: {langfuse_trace_id}", flush=True)

    try:
        # Pass force_review flag if --force was specified
        force_review = getattr(args, "force", False)
        result = await orchestrator.review_pr(args.pr_number, force_review=force_review)

        duration_seconds = time.time() - start_time

        if debug:
            print(f"[DEBUG] review_pr returned, success={result.success}", flush=True)

        if result.success:
            print(f"\n{'=' * 60}")
            print(f"PR #{result.pr_number} Review Complete")
            print(f"{'=' * 60}")
            print(f"Status: {result.overall_status}")
            print(f"Summary: {result.summary}")
            print(f"Findings: {len(result.findings)}")

            if result.findings:
                print("\nFindings by severity:")
                for f in result.findings:
                    emoji = {"critical": "!", "high": "*", "medium": "-", "low": "."}
                    print(
                        f"  {emoji.get(f.severity.value, '?')} [{f.severity.value.upper()}] {f.title}"
                    )
                    print(f"    File: {f.file}:{f.line}")

            # Extract artifacts and publish ROI (wrapped in try/except to not break main flow)
            try:
                project_path = Path(args.project)
                artifacts, langfuse_refs = extract_pr_review_artifacts(
                    result,
                    project_dir=project_path,
                    trace_id=langfuse_trace_id,
                )

                if artifacts:
                    total_artifact_value = sum(a.get("value_usd", 0) for a in artifacts)
                    print(f"\n[Artifacts] Stored {len(artifacts)} artifacts (${total_artifact_value:.2f} value)", flush=True)

                # Publish ROI with artifacts
                if ROI_PUBLISHER_AVAILABLE:
                    # Count findings by severity
                    critical_count = sum(1 for f in result.findings if f.severity.value == "critical")
                    high_count = sum(1 for f in result.findings if f.severity.value == "high")
                    medium_count = sum(1 for f in result.findings if f.severity.value == "medium")
                    low_count = sum(1 for f in result.findings if f.severity.value == "low")

                    roi_result = await publish_github_roi_with_artifacts(
                        project_dir=project_path,
                        feature_type="github_pr_review",
                        metrics={
                            "prs_reviewed": 1,
                            "findings_count": len(result.findings),
                            "critical_findings": critical_count,
                            "high_findings": high_count,
                            "medium_findings": medium_count,
                            "low_findings": low_count,
                            "structural_issues": len(result.structural_issues or []),
                            "ai_triages": len(result.ai_comment_triages or []),
                            "blockers_count": len(result.blockers or []),
                            "verdict": result.overall_status,
                            "estimated_tokens": 2000,  # Rough estimate
                        },
                        artifacts=artifacts,
                        langfuse_refs=langfuse_refs,
                        duration_seconds=duration_seconds,
                        model=config.model,
                        trace_id=langfuse_trace_id,
                    )

                    if roi_result.get("success"):
                        roi_pct = roi_result.get("roi_percentage", 0)
                        value = roi_result.get("total_value_usd", 0)
                        print(f"[ROI] PR review: {roi_pct:.0f}% ROI (${value:.2f} value)", flush=True)

            except Exception as e:
                if debug:
                    print(f"[DEBUG] Artifact/ROI extraction failed (non-fatal): {e}", flush=True)

            return 0
        else:
            print(f"\nReview failed: {result.error}")
            return 1

    finally:
        # Close Langfuse trace context
        if langfuse_ctx:
            try:
                if ctx:
                    output_data = {
                        "success": result.success if 'result' in dir() else False,
                    }
                    if 'result' in dir() and result.success:
                        output_data["findings_count"] = len(result.findings)
                        output_data["verdict"] = result.overall_status
                    ctx.set_output(output_data)
                langfuse_ctx.__exit__(None, None, None)
                flush_langfuse()
            except Exception:
                pass


async def cmd_followup_review_pr(args) -> int:
    """Perform a follow-up review of a pull request."""
    import sys

    # Force unbuffered output so Electron sees it in real-time
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True)

    debug = os.environ.get("DEBUG")
    if debug:
        print(f"[DEBUG] Starting follow-up review for PR #{args.pr_number}", flush=True)
        print(f"[DEBUG] Project directory: {args.project}", flush=True)
        print("[DEBUG] Building config...", flush=True)

    config = get_config(args)

    if debug:
        print(
            f"[DEBUG] Config built: repo={config.repo}, model={config.model}",
            flush=True,
        )
        print("[DEBUG] Creating orchestrator...", flush=True)

    orchestrator = GitHubOrchestrator(
        project_dir=args.project,
        config=config,
        progress_callback=print_progress,
    )

    if debug:
        print("[DEBUG] Orchestrator created", flush=True)
        print(
            f"[DEBUG] Calling orchestrator.followup_review_pr({args.pr_number})...",
            flush=True,
        )

    try:
        result = await orchestrator.followup_review_pr(args.pr_number)
    except ValueError as e:
        print(f"\nFollow-up review failed: {e}")
        return 1

    if debug:
        print(
            f"[DEBUG] followup_review_pr returned, success={result.success}", flush=True
        )

    if result.success:
        print(f"\n{'=' * 60}")
        print(f"PR #{result.pr_number} Follow-up Review Complete")
        print(f"{'=' * 60}")
        print(f"Status: {result.overall_status}")
        print(f"Is Follow-up: {result.is_followup_review}")

        if result.resolved_findings:
            print(f"Resolved: {len(result.resolved_findings)} finding(s)")
        if result.unresolved_findings:
            print(f"Still Open: {len(result.unresolved_findings)} finding(s)")
        if result.new_findings_since_last_review:
            print(
                f"New Issues: {len(result.new_findings_since_last_review)} finding(s)"
            )

        print(f"\nSummary:\n{result.summary}")

        if result.findings:
            print("\nRemaining Findings:")
            for f in result.findings:
                emoji = {"critical": "!", "high": "*", "medium": "-", "low": "."}
                print(
                    f"  {emoji.get(f.severity.value, '?')} [{f.severity.value.upper()}] {f.title}"
                )
                print(f"    File: {f.file}:{f.line}")
        return 0
    else:
        print(f"\nFollow-up review failed: {result.error}")
        return 1


async def cmd_triage(args) -> int:
    """Triage issues."""
    import time

    config = get_config(args)
    orchestrator = GitHubOrchestrator(
        project_dir=args.project,
        config=config,
        progress_callback=print_progress,
    )

    debug = os.environ.get("DEBUG")

    # Track start time for ROI metrics
    start_time = time.time()

    # Setup Langfuse trace context if available
    langfuse_trace_id = None
    langfuse_ctx = None
    if LANGFUSE_AVAILABLE and is_langfuse_ready() and trace_context:
        project_id = args.project.name if hasattr(args.project, 'name') else Path(args.project).name
        issue_count = len(args.issues) if args.issues else "all"
        langfuse_ctx = trace_context(
            name=f"github-issue-triage-{issue_count}",
            project_id=project_id,
            agent_type="github_issue_triage",
            metadata={
                "issue_count": len(args.issues) if args.issues else "all",
                "apply_labels": args.apply_labels,
                "model": config.model,
            },
            tags=["github", "issue-triage"],
            input_data={"issues": args.issues or "all", "apply_labels": args.apply_labels},
        )
        ctx = langfuse_ctx.__enter__()
        if ctx:
            langfuse_trace_id = ctx.trace_id
            if debug:
                print(f"[DEBUG] Langfuse trace created: {langfuse_trace_id}", flush=True)

    try:
        issue_numbers = args.issues if args.issues else None
        results = await orchestrator.triage_issues(
            issue_numbers=issue_numbers,
            apply_labels=args.apply_labels,
        )

        duration_seconds = time.time() - start_time

        print(f"\n{'=' * 60}")
        print(f"Triaged {len(results)} issues")
        print(f"{'=' * 60}")

        for r in results:
            flags = []
            if r.is_duplicate:
                flags.append(f"DUP of #{r.duplicate_of}")
            if r.is_spam:
                flags.append("SPAM")
            if r.is_feature_creep:
                flags.append("CREEP")

            flag_str = f" [{', '.join(flags)}]" if flags else ""
            print(
                f"  #{r.issue_number}: {r.category.value} (confidence: {r.confidence:.0%}){flag_str}"
            )

            if r.labels_to_add:
                print(f"    + Labels: {', '.join(r.labels_to_add)}")

        # Extract artifacts and publish ROI (wrapped in try/except to not break main flow)
        try:
            project_path = Path(args.project)
            artifacts, langfuse_refs = extract_triage_artifacts(
                results,
                project_dir=project_path,
                trace_id=langfuse_trace_id,
            )

            if artifacts:
                total_artifact_value = sum(a.get("value_usd", 0) for a in artifacts)
                print(f"\n[Artifacts] Stored {len(artifacts)} artifacts (${total_artifact_value:.2f} value)", flush=True)

            # Publish ROI with artifacts
            if ROI_PUBLISHER_AVAILABLE:
                duplicates = sum(1 for r in results if r.is_duplicate)
                spam = sum(1 for r in results if r.is_spam)
                feature_creep = sum(1 for r in results if r.is_feature_creep)

                roi_result = await publish_github_roi_with_artifacts(
                    project_dir=project_path,
                    feature_type="github_issue_triage",
                    metrics={
                        "issues_triaged": len(results),
                        "duplicates_detected": duplicates,
                        "spam_detected": spam,
                        "feature_creep_detected": feature_creep,
                        "labels_applied": args.apply_labels,
                        "estimated_tokens": len(results) * 500,  # Rough estimate per issue
                    },
                    artifacts=artifacts,
                    langfuse_refs=langfuse_refs,
                    duration_seconds=duration_seconds,
                    model=config.model,
                    trace_id=langfuse_trace_id,
                )

                if roi_result.get("success"):
                    roi_pct = roi_result.get("roi_percentage", 0)
                    value = roi_result.get("total_value_usd", 0)
                    print(f"[ROI] Issue triage: {roi_pct:.0f}% ROI (${value:.2f} value)", flush=True)

        except Exception as e:
            if debug:
                print(f"[DEBUG] Artifact/ROI extraction failed (non-fatal): {e}", flush=True)

        return 0

    finally:
        # Close Langfuse trace context
        if langfuse_ctx:
            try:
                if ctx:
                    output_data = {
                        "issues_triaged": len(results) if 'results' in dir() else 0,
                    }
                    if 'results' in dir():
                        output_data["duplicates"] = sum(1 for r in results if r.is_duplicate)
                        output_data["spam"] = sum(1 for r in results if r.is_spam)
                    ctx.set_output(output_data)
                langfuse_ctx.__exit__(None, None, None)
                flush_langfuse()
            except Exception:
                pass


async def cmd_auto_fix(args) -> int:
    """Start auto-fix for an issue."""
    config = get_config(args)
    config.auto_fix_enabled = True
    orchestrator = GitHubOrchestrator(
        project_dir=args.project,
        config=config,
        progress_callback=print_progress,
    )

    state = await orchestrator.auto_fix_issue(args.issue_number)

    print(f"\n{'=' * 60}")
    print(f"Auto-Fix State for Issue #{state.issue_number}")
    print(f"{'=' * 60}")
    print(f"Status: {state.status.value}")
    if state.spec_id:
        print(f"Spec ID: {state.spec_id}")
    if state.pr_number:
        print(f"PR: #{state.pr_number}")
    if state.error:
        print(f"Error: {state.error}")

    return 0


async def cmd_check_labels(args) -> int:
    """Check for issues with auto-fix labels."""
    config = get_config(args)
    config.auto_fix_enabled = True
    orchestrator = GitHubOrchestrator(
        project_dir=args.project,
        config=config,
        progress_callback=print_progress,
    )

    issues = await orchestrator.check_auto_fix_labels()

    if issues:
        print(f"Found {len(issues)} issues with auto-fix labels:")
        for num in issues:
            print(f"  #{num}")
    else:
        print("No issues with auto-fix labels found.")

    return 0


async def cmd_check_new(args) -> int:
    """Check for new issues not yet in the auto-fix queue."""
    config = get_config(args)
    config.auto_fix_enabled = True
    orchestrator = GitHubOrchestrator(
        project_dir=args.project,
        config=config,
        progress_callback=print_progress,
    )

    issues = await orchestrator.check_new_issues()

    print("JSON Output")
    print(json.dumps(issues))

    return 0


async def cmd_queue(args) -> int:
    """Show auto-fix queue."""
    config = get_config(args)
    orchestrator = GitHubOrchestrator(
        project_dir=args.project,
        config=config,
    )

    queue = await orchestrator.get_auto_fix_queue()

    print(f"\n{'=' * 60}")
    print(f"Auto-Fix Queue ({len(queue)} items)")
    print(f"{'=' * 60}")

    if not queue:
        print("Queue is empty.")
        return 0

    for state in queue:
        status_emoji = {
            "pending": "...",
            "analyzing": "...",
            "creating_spec": "...",
            "building": "...",
            "qa_review": "...",
            "pr_created": "+++",
            "completed": "OK",
            "failed": "ERR",
        }
        emoji = status_emoji.get(state.status.value, "???")
        print(f"  [{emoji}] #{state.issue_number}: {state.status.value}")
        if state.pr_number:
            print(f"       PR: #{state.pr_number}")
        if state.error:
            print(f"       Error: {state.error[:50]}...")

    return 0


async def cmd_batch_issues(args) -> int:
    """Batch similar issues and create combined specs."""
    config = get_config(args)
    config.auto_fix_enabled = True
    orchestrator = GitHubOrchestrator(
        project_dir=args.project,
        config=config,
        progress_callback=print_progress,
    )

    issue_numbers = args.issues if args.issues else None
    batches = await orchestrator.batch_and_fix_issues(issue_numbers)

    print(f"\n{'=' * 60}")
    print(f"Created {len(batches)} batches from similar issues")
    print(f"{'=' * 60}")

    if not batches:
        print("No batches created. Either no issues found or all issues are unique.")
        return 0

    for batch in batches:
        issue_nums = ", ".join(f"#{i.issue_number}" for i in batch.issues)
        print(f"\n  Batch: {batch.batch_id}")
        print(f"    Issues: {issue_nums}")
        print(f"    Theme: {batch.theme}")
        print(f"    Status: {batch.status.value}")
        if batch.spec_id:
            print(f"    Spec: {batch.spec_id}")

    return 0


async def cmd_batch_status(args) -> int:
    """Show batch status."""
    config = get_config(args)
    orchestrator = GitHubOrchestrator(
        project_dir=args.project,
        config=config,
    )

    status = await orchestrator.get_batch_status()

    print(f"\n{'=' * 60}")
    print("Batch Status")
    print(f"{'=' * 60}")
    print(f"Total batches: {status.get('total_batches', 0)}")
    print(f"Pending: {status.get('pending', 0)}")
    print(f"Processing: {status.get('processing', 0)}")
    print(f"Completed: {status.get('completed', 0)}")
    print(f"Failed: {status.get('failed', 0)}")

    return 0


async def cmd_analyze_preview(args) -> int:
    """
    Analyze issues and preview proposed batches without executing.

    This is the "proactive" workflow for reviewing issue groupings before action.
    """
    import json
    import time

    config = get_config(args)
    orchestrator = GitHubOrchestrator(
        project_dir=args.project,
        config=config,
        progress_callback=print_progress,
    )

    debug = os.environ.get("DEBUG")

    # Track start time for ROI metrics
    start_time = time.time()

    # Setup Langfuse trace context if available
    langfuse_trace_id = None
    langfuse_ctx = None
    if LANGFUSE_AVAILABLE and is_langfuse_ready() and trace_context:
        project_id = args.project.name if hasattr(args.project, 'name') else Path(args.project).name
        max_issues = getattr(args, "max_issues", 200)
        langfuse_ctx = trace_context(
            name=f"github-batch-preview-{max_issues}",
            project_id=project_id,
            agent_type="github_batch_issues",
            metadata={
                "max_issues": max_issues,
                "issue_numbers": args.issues if args.issues else "all",
                "model": config.model,
            },
            tags=["github", "batch-issues", "preview"],
            input_data={"max_issues": max_issues, "issues": args.issues or "all"},
        )
        ctx = langfuse_ctx.__enter__()
        if ctx:
            langfuse_trace_id = ctx.trace_id
            if debug:
                print(f"[DEBUG] Langfuse trace created: {langfuse_trace_id}", flush=True)

    try:
        issue_numbers = args.issues if args.issues else None
        max_issues = getattr(args, "max_issues", 200)

        result = await orchestrator.analyze_issues_preview(
            issue_numbers=issue_numbers,
            max_issues=max_issues,
        )

        duration_seconds = time.time() - start_time

        if not result.get("success"):
            print(f"Error: {result.get('error', 'Unknown error')}")
            return 1

        print(f"\n{'=' * 60}")
        print("Issue Analysis Preview")
        print(f"{'=' * 60}")
        print(f"Total issues: {result.get('total_issues', 0)}")
        print(f"Analyzed: {result.get('analyzed_issues', 0)}")
        print(f"Already batched: {result.get('already_batched', 0)}")
        print(f"Proposed batches: {len(result.get('proposed_batches', []))}")
        print(f"Single issues: {len(result.get('single_issues', []))}")

        proposed_batches = result.get("proposed_batches", [])
        if proposed_batches:
            print(f"\n{'=' * 60}")
            print("Proposed Batches (for human review)")
            print(f"{'=' * 60}")

            for i, batch in enumerate(proposed_batches, 1):
                confidence = batch.get("confidence", 0)
                validated = "" if batch.get("validated") else "[NEEDS REVIEW] "
                print(
                    f"\n  Batch {i}: {validated}{batch.get('theme', 'No theme')} ({confidence:.0%} confidence)"
                )
                print(f"    Primary issue: #{batch.get('primary_issue')}")
                print(f"    Issue count: {batch.get('issue_count', 0)}")
                print(f"    Reasoning: {batch.get('reasoning', 'N/A')}")
                print("    Issues:")
                for item in batch.get("issues", []):
                    similarity = item.get("similarity_to_primary", 0)
                    print(
                        f"      - #{item['issue_number']}: {item.get('title', '?')} ({similarity:.0%})"
                    )

        # Extract artifacts and publish ROI (wrapped in try/except to not break main flow)
        try:
            project_path = Path(args.project)
            artifacts, langfuse_refs = extract_batch_preview_artifacts(
                result,
                project_dir=project_path,
                trace_id=langfuse_trace_id,
            )

            if artifacts:
                total_artifact_value = sum(a.get("value_usd", 0) for a in artifacts)
                print(f"\n[Artifacts] Stored {len(artifacts)} artifacts (${total_artifact_value:.2f} value)", flush=True)

            # Publish ROI with artifacts
            if ROI_PUBLISHER_AVAILABLE:
                roi_result = await publish_github_roi_with_artifacts(
                    project_dir=project_path,
                    feature_type="github_batch_issues",
                    metrics={
                        "total_issues": result.get('total_issues', 0),
                        "analyzed_issues": result.get('analyzed_issues', 0),
                        "proposed_batches": len(result.get('proposed_batches', [])),
                        "single_issues": len(result.get('single_issues', [])),
                        "already_batched": result.get('already_batched', 0),
                        "estimated_tokens": result.get('analyzed_issues', 0) * 300,  # Rough estimate
                    },
                    artifacts=artifacts,
                    langfuse_refs=langfuse_refs,
                    duration_seconds=duration_seconds,
                    model=config.model,
                    trace_id=langfuse_trace_id,
                )

                if roi_result.get("success"):
                    roi_pct = roi_result.get("roi_percentage", 0)
                    value = roi_result.get("total_value_usd", 0)
                    print(f"[ROI] Batch preview: {roi_pct:.0f}% ROI (${value:.2f} value)", flush=True)

        except Exception as e:
            if debug:
                print(f"[DEBUG] Artifact/ROI extraction failed (non-fatal): {e}", flush=True)

        # Output JSON for programmatic use
        if getattr(args, "json", False):
            print(f"\n{'=' * 60}")
            print("JSON Output")
            print(f"{'=' * 60}")
            # Print JSON on single line to avoid corruption from line-by-line stdout prefixes
            print(json.dumps(result))

        return 0

    finally:
        # Close Langfuse trace context
        if langfuse_ctx:
            try:
                if ctx:
                    output_data = {
                        "success": result.get("success") if 'result' in dir() else False,
                    }
                    if 'result' in dir() and result.get("success"):
                        output_data["total_issues"] = result.get('total_issues', 0)
                        output_data["proposed_batches"] = len(result.get('proposed_batches', []))
                    ctx.set_output(output_data)
                langfuse_ctx.__exit__(None, None, None)
                flush_langfuse()
            except Exception:
                pass


async def cmd_approve_batches(args) -> int:
    """
    Approve and execute batches from a JSON file.

    Usage: runner.py approve-batches approved_batches.json
    """
    import json

    config = get_config(args)
    orchestrator = GitHubOrchestrator(
        project_dir=args.project,
        config=config,
        progress_callback=print_progress,
    )

    # Load approved batches from file
    try:
        with open(args.batch_file) as f:
            approved_batches = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading batch file: {e}")
        return 1

    if not approved_batches:
        print("No batches in file to approve.")
        return 0

    print(f"Approving and executing {len(approved_batches)} batches...")

    created_batches = await orchestrator.approve_and_execute_batches(approved_batches)

    print(f"\n{'=' * 60}")
    print(f"Created {len(created_batches)} batches")
    print(f"{'=' * 60}")

    for batch in created_batches:
        issue_nums = ", ".join(f"#{i.issue_number}" for i in batch.issues)
        print(f"  {batch.batch_id}: {issue_nums}")

    return 0


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="GitHub automation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current)",
    )
    parser.add_argument(
        "--token",
        type=str,
        help="GitHub token (or set GITHUB_TOKEN)",
    )
    parser.add_argument(
        "--bot-token",
        type=str,
        help="Bot account token for comments (optional)",
    )
    parser.add_argument(
        "--repo",
        type=str,
        help="GitHub repo (owner/name) or auto-detect",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-20250514",
        help="AI model to use",
    )
    parser.add_argument(
        "--thinking-level",
        type=str,
        default="medium",
        choices=["none", "low", "medium", "high"],
        help="Thinking level for extended reasoning",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # review-pr command
    review_parser = subparsers.add_parser("review-pr", help="Review a pull request")
    review_parser.add_argument("pr_number", type=int, help="PR number to review")
    review_parser.add_argument(
        "--auto-post",
        action="store_true",
        help="Automatically post review to GitHub",
    )
    review_parser.add_argument(
        "--force",
        action="store_true",
        help="Force a new review even if commit was already reviewed",
    )

    # followup-review-pr command
    followup_parser = subparsers.add_parser(
        "followup-review-pr",
        help="Follow-up review of a PR (after contributor changes)",
    )
    followup_parser.add_argument("pr_number", type=int, help="PR number to review")

    # triage command
    triage_parser = subparsers.add_parser("triage", help="Triage issues")
    triage_parser.add_argument(
        "issues",
        type=int,
        nargs="*",
        help="Specific issue numbers (or all open if none)",
    )
    triage_parser.add_argument(
        "--apply-labels",
        action="store_true",
        help="Apply suggested labels to GitHub",
    )

    # auto-fix command
    autofix_parser = subparsers.add_parser("auto-fix", help="Start auto-fix for issue")
    autofix_parser.add_argument("issue_number", type=int, help="Issue number to fix")

    # check-auto-fix-labels command
    subparsers.add_parser(
        "check-auto-fix-labels", help="Check for issues with auto-fix labels"
    )

    # check-new command
    subparsers.add_parser(
        "check-new", help="Check for new issues not yet in auto-fix queue"
    )

    # queue command
    subparsers.add_parser("queue", help="Show auto-fix queue")

    # batch-issues command
    batch_parser = subparsers.add_parser(
        "batch-issues", help="Batch similar issues and create combined specs"
    )
    batch_parser.add_argument(
        "issues",
        type=int,
        nargs="*",
        help="Specific issue numbers (or all open if none)",
    )

    # batch-status command
    subparsers.add_parser("batch-status", help="Show batch status")

    # analyze-preview command (proactive workflow)
    analyze_parser = subparsers.add_parser(
        "analyze-preview",
        help="Analyze issues and preview proposed batches without executing",
    )
    analyze_parser.add_argument(
        "issues",
        type=int,
        nargs="*",
        help="Specific issue numbers (or all open if none)",
    )
    analyze_parser.add_argument(
        "--max-issues",
        type=int,
        default=200,
        help="Maximum number of issues to analyze (default: 200)",
    )
    analyze_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON for programmatic use",
    )

    # approve-batches command
    approve_parser = subparsers.add_parser(
        "approve-batches",
        help="Approve and execute batches from a JSON file",
    )
    approve_parser.add_argument(
        "batch_file",
        type=Path,
        help="JSON file containing approved batches",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to command handler
    commands = {
        "review-pr": cmd_review_pr,
        "followup-review-pr": cmd_followup_review_pr,
        "triage": cmd_triage,
        "auto-fix": cmd_auto_fix,
        "check-auto-fix-labels": cmd_check_labels,
        "check-new": cmd_check_new,
        "queue": cmd_queue,
        "batch-issues": cmd_batch_issues,
        "batch-status": cmd_batch_status,
        "analyze-preview": cmd_analyze_preview,
        "approve-batches": cmd_approve_batches,
    }

    handler = commands.get(args.command)
    if not handler:
        print(f"Unknown command: {args.command}")
        sys.exit(1)

    try:
        exit_code = asyncio.run(handler(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except Exception as e:
        import traceback

        debug_error("github_runner", "Command failed", error=str(e))
        print(f"Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
