"""
Execution layer for agents and scripts in the roadmap generation process.
"""

import asyncio
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

from debug import debug, debug_detailed, debug_error, debug_success

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

# Import legacy feature tracker for backwards compatibility
try:
    from analytics import (
        create_feature_tracker,
        FEATURE_ROADMAP,
        is_tracking_enabled,
    )
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False

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


# =============================================================================
# ARTIFACT EXTRACTION
# =============================================================================


def extract_roadmap_artifacts(
    response_text: str,
    roadmap_data: dict | None,
    project_dir: Path | None = None,
    trace_id: str | None = None,
    agent_type: str = "roadmap",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Extract HIGH-QUALITY roadmap artifacts from response and roadmap data.

    Stores FULL artifact content locally, returns lightweight references for Langfuse.

    This function extracts RICH content including:
    - Strategic rationale and justifications
    - Acceptance criteria and user stories
    - Dependencies and phase context

    Artifacts extracted:
    - roadmap_item ($100-150 each) - each feature with full context
    - milestone ($75 each) - phase milestones with feature details
    - priority_recommendation ($75) - priority recommendations

    Args:
        response_text: The full response from the roadmap agent
        roadmap_data: Parsed roadmap data (from roadmap.json or response)
        project_dir: Project root directory for local storage
        trace_id: Langfuse trace ID for linking
        agent_type: Agent type for categorization (e.g., "roadmap_discovery", "roadmap_features")

    Returns:
        Tuple of (local_artifacts, langfuse_refs):
        - local_artifacts: Full artifacts for local processing
        - langfuse_refs: Truncated references for Langfuse (or full artifacts if storage unavailable)
    """
    artifacts = []

    # Build lookup maps for enrichment
    if roadmap_data:
        features_by_id = {f.get("id"): f for f in roadmap_data.get("features", []) if isinstance(f, dict) and f.get("id")}
        phases_by_id = {p.get("id"): p for p in roadmap_data.get("phases", []) if isinstance(p, dict) and p.get("id")}
    else:
        features_by_id = {}
        phases_by_id = {}

    # Extract roadmap_items from roadmap data
    if roadmap_data:
        features = roadmap_data.get("features", [])
        for i, feature in enumerate(features):
            # Extract ALL available fields
            title = feature.get("title", feature.get("name", "Unknown feature"))
            description = feature.get("description", "")
            priority = feature.get("priority", "medium")
            status = feature.get("status", "proposed")
            phase_id = feature.get("phase_id", feature.get("phase", ""))
            effort = feature.get("effort", "")
            impact = feature.get("impact", "")
            complexity = feature.get("complexity", "")
            rationale = feature.get("rationale", "")
            acceptance_criteria = feature.get("acceptance_criteria", [])
            user_stories = feature.get("user_stories", [])
            dependencies = feature.get("dependencies", [])

            # Calculate value based on content richness
            base_value = 100
            if acceptance_criteria:
                base_value += 15
            if user_stories:
                base_value += 15
            if rationale:
                base_value += 10
            if dependencies:
                base_value += 10

            # Build RICH content
            content = f"# {title}\n\n"

            # Priority and classification bar
            content += f"**Priority:** {priority.upper() if priority else 'MEDIUM'}"
            if complexity:
                content += f" | **Complexity:** {complexity}"
            if impact:
                content += f" | **Impact:** {impact}"
            if status:
                content += f" | **Status:** {status}"
            content += "\n\n"

            # Phase context
            if phase_id:
                phase = phases_by_id.get(phase_id, {})
                phase_name = phase.get("name", phase_id) if isinstance(phase, dict) else phase_id
                content += f"**Phase:** {phase_name}\n\n"

            # Description
            if description:
                content += f"## Description\n\n{description}\n\n"

            # Strategic Rationale - WHY this matters
            if rationale:
                content += f"## Strategic Rationale\n\n{rationale}\n\n"

            # User Stories - WHO benefits
            if user_stories:
                content += "## User Stories\n\n"
                for story in user_stories:
                    content += f"- {story}\n"
                content += "\n"

            # Acceptance Criteria - WHAT success looks like
            if acceptance_criteria:
                content += "## Acceptance Criteria\n\n"
                for j, criterion in enumerate(acceptance_criteria):
                    content += f"{j+1}. {criterion}\n"
                content += "\n"

            # Dependencies - WHAT must come first
            if dependencies:
                content += "## Dependencies\n\n"
                for dep_id in dependencies:
                    dep_feat = features_by_id.get(dep_id, {})
                    dep_name = dep_feat.get("title", dep_feat.get("name", dep_id)) if dep_feat else dep_id
                    content += f"- Requires: **{dep_name}**\n"
                content += "\n"

            # Effort estimation
            if effort:
                content += f"**Estimated Effort:** {effort}\n"

            # Determine appropriate tab based on priority
            if priority and priority.lower() in ["must", "critical", "high"]:
                tab = "business"
            elif complexity and complexity.lower() in ["high", "very_high"]:
                tab = "techlead"
            else:
                tab = "business"

            artifacts.append({
                "type": "roadmap_item",
                "format": "markdown",
                "content": content,
                "value_usd": min(base_value, 150),
                "description": f"Roadmap item #{i+1}: {title}",
                "priority": priority,
                "tab": tab,
                "metadata": {
                    "feature_title": title,
                    "feature_priority": priority,
                    "feature_status": status,
                    "feature_phase": phase_id,
                    "feature_effort": effort,
                    "feature_impact": impact,
                    "has_acceptance_criteria": bool(acceptance_criteria),
                    "has_user_stories": bool(user_stories),
                    "has_rationale": bool(rationale),
                    "dependency_count": len(dependencies),
                },
            })

        # Extract milestones from phases with enriched content
        phases = roadmap_data.get("phases", [])
        for i, phase in enumerate(phases):
            phase_id = phase.get("id", f"phase-{i+1}")
            phase_name = phase.get("name", f"Phase {i+1}")
            phase_description = phase.get("description", "")
            phase_timeline = phase.get("timeline", phase.get("duration", ""))
            phase_status = phase.get("status", "planned")
            phase_order = phase.get("order", i + 1)
            phase_feature_ids = phase.get("features", [])
            milestones = phase.get("milestones", [])

            # Build RICH phase content
            content = f"# {phase_name}\n\n"
            content += f"**Order:** {phase_order} | **Status:** {phase_status}\n"
            if phase_timeline:
                content += f"**Timeline:** {phase_timeline}\n"
            content += "\n"

            if phase_description:
                content += f"## Overview\n\n{phase_description}\n\n"

            # Add milestones with detail
            if milestones:
                content += "## Milestones\n\n"
                for j, milestone in enumerate(milestones):
                    if isinstance(milestone, dict):
                        m_title = milestone.get("title", f"Milestone {j+1}")
                        m_desc = milestone.get("description", "")
                        m_status = milestone.get("status", "planned")
                        content += f"### {m_title}\n"
                        content += f"**Status:** {m_status}\n"
                        if m_desc:
                            content += f"\n{m_desc}\n"
                        content += "\n"
                    elif isinstance(milestone, str):
                        content += f"- {milestone}\n"

            # List features in this phase with priority
            if phase_feature_ids:
                content += "## Features in This Phase\n\n"
                for feat_ref in phase_feature_ids:
                    if isinstance(feat_ref, str):
                        feat = features_by_id.get(feat_ref, {})
                        f_title = feat.get("title", feat.get("name", feat_ref)) if feat else feat_ref
                        f_priority = feat.get("priority", "") if feat else ""
                        f_impact = feat.get("impact", "") if feat else ""
                    elif isinstance(feat_ref, dict):
                        f_title = feat_ref.get("title", feat_ref.get("name", str(feat_ref)))
                        f_priority = feat_ref.get("priority", "")
                        f_impact = feat_ref.get("impact", "")
                    else:
                        f_title = str(feat_ref)
                        f_priority = ""
                        f_impact = ""

                    content += f"- **{f_title}**"
                    if f_priority:
                        content += f" [{f_priority.upper()}]"
                    if f_impact:
                        content += f" - Impact: {f_impact}"
                    content += "\n"

            artifacts.append({
                "type": "milestone",
                "format": "markdown",
                "content": content,
                "value_usd": 75,
                "description": f"Phase {phase_order}: {phase_name}",
                "tab": "ops",
                "metadata": {
                    "phase_id": phase_id,
                    "phase_name": phase_name,
                    "phase_order": phase_order,
                    "phase_timeline": phase_timeline,
                    "features_count": len(phase_feature_ids),
                    "milestones_count": len(milestones),
                },
            })

    # Extract priority_recommendations from response text using patterns
    priority_patterns = [
        r"(?:should prioritize|recommend prioritizing|priority should be|high priority).*?[.!?\n]",
        r"(?:critical|urgent|important|essential).*?(?:feature|item|task).*?[.!?\n]",
        r"(?:focus on|start with|begin with).*?[.!?\n]",
    ]

    # Split response into sentences/paragraphs for extraction
    sentences = re.split(r'(?<=[.!?])\s+', response_text)
    priority_recommendations_found = set()  # Use set to avoid duplicates

    for sentence in sentences:
        sentence_lower = sentence.lower().strip()
        if len(sentence_lower) < 30:
            continue

        for pattern in priority_patterns:
            if re.search(pattern, sentence_lower, re.IGNORECASE):
                # FULL sentence - no truncation
                clean_sentence = sentence.strip()
                if clean_sentence and clean_sentence not in priority_recommendations_found:
                    priority_recommendations_found.add(clean_sentence)
                    artifacts.append({
                        "type": "priority_recommendation",
                        "format": "text",
                        "content": clean_sentence,
                        "value_usd": 75,
                        "description": "Priority recommendation",
                        "tab": "business",
                    })
                break  # Only match once per sentence

    # Save artifacts locally and create Langfuse references
    if ARTIFACT_STORAGE_AVAILABLE and project_dir:
        langfuse_refs = []
        for artifact in artifacts:
            # Save full artifact locally
            artifact_id = save_artifact_safe(
                artifact=artifact,
                project_dir=project_dir,
                spec_id=None,  # Roadmap doesn't have spec_id
                trace_id=trace_id,
                agent_type=agent_type,
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


class ScriptExecutor:
    """Executes Python scripts with proper error handling and output capture."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        # Go up from roadmap/ -> runners/ -> auto-claude/
        self.scripts_base_dir = Path(__file__).parent.parent.parent

    def run_script(self, script: str, args: list[str]) -> tuple[bool, str]:
        """Run a Python script and return (success, output)."""
        script_path = self.scripts_base_dir / script

        debug_detailed(
            "roadmap_executor",
            f"Running script: {script}",
            script_path=str(script_path),
            args=args,
        )

        if not script_path.exists():
            debug_error("roadmap_executor", f"Script not found: {script_path}")
            return False, f"Script not found: {script_path}"

        cmd = [sys.executable, str(script_path)] + args

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                debug_success("roadmap_executor", f"Script completed: {script}")
                return True, result.stdout
            else:
                debug_error(
                    "roadmap_executor",
                    f"Script failed: {script}",
                    returncode=result.returncode,
                    stderr=result.stderr if result.stderr else None,
                )
                return False, result.stderr or result.stdout

        except subprocess.TimeoutExpired:
            debug_error("roadmap_executor", f"Script timed out: {script}")
            return False, "Script timed out"
        except Exception as e:
            debug_error("roadmap_executor", f"Script exception: {script}", error=str(e))
            return False, str(e)


class AgentExecutor:
    """Executes Claude AI agents with specific prompts."""

    def __init__(
        self,
        project_dir: Path,
        output_dir: Path,
        model: str,
        create_client_func,
        thinking_budget: int | None = None,
        feature_type: str = FEATURE_ROADMAP if TRACKING_AVAILABLE else "roadmap",
    ):
        self.project_dir = project_dir
        self.output_dir = output_dir
        self.model = model
        self.create_client = create_client_func
        self.thinking_budget = thinking_budget
        self.feature_type = feature_type
        # Go up from roadmap/ -> runners/ -> auto-claude/prompts/
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"

        # Generate a project ID from the project directory
        self.project_id = self._generate_project_id()

        # Check Langfuse availability
        self.langfuse_enabled = LANGFUSE_AVAILABLE and is_langfuse_ready()
        debug(
            "roadmap_executor",
            "Langfuse integration status",
            langfuse_available=LANGFUSE_AVAILABLE,
            langfuse_ready=self.langfuse_enabled,
        )

        # Feature tracker for token usage (legacy - kept for backwards compatibility)
        self.tracker = None
        if TRACKING_AVAILABLE and is_tracking_enabled():
            db_path = str(self.project_dir / ".auto-claude" / "analytics.db")
            debug(
                "roadmap_executor",
                "Initializing legacy feature tracker",
                project_dir=str(self.project_dir),
                db_path=db_path,
                project_id=self.project_id,
                feature_type=self.feature_type,
            )
            try:
                self.tracker = create_feature_tracker(
                    project_id=self.project_id,
                    feature_type=self.feature_type,
                    db_path=db_path,
                    metadata={"model": self.model, "thinking_budget": self.thinking_budget}
                )
                debug("roadmap_executor", "Legacy feature tracker initialized", project_id=self.project_id)
            except Exception as e:
                debug_error("roadmap_executor", f"Failed to create legacy feature tracker: {e}")
                self.tracker = None
        else:
            debug(
                "roadmap_executor",
                "Legacy feature tracking disabled",
                tracking_available=TRACKING_AVAILABLE,
                tracking_enabled=is_tracking_enabled() if TRACKING_AVAILABLE else False,
            )

    def _generate_project_id(self) -> str:
        """Generate a unique project ID from the project directory."""
        # Use project directory name as a simple ID
        # Could be enhanced to use git remote or other identifiers
        return self.project_dir.name

    async def run_agent(
        self,
        prompt_file: str,
        additional_context: str = "",
    ) -> tuple[bool, str, str | None]:
        """Run an agent with the given prompt.

        Returns:
            Tuple of (success, response_text, langfuse_trace_id)
        """
        prompt_path = self.prompts_dir / prompt_file

        debug_detailed(
            "roadmap_executor",
            f"Running agent with prompt: {prompt_file}",
            prompt_path=str(prompt_path),
            model=self.model,
        )

        if not prompt_path.exists():
            debug_error("roadmap_executor", f"Prompt file not found: {prompt_path}")
            return False, f"Prompt not found: {prompt_path}"

        # Load prompt
        prompt = prompt_path.read_text()
        debug_detailed(
            "roadmap_executor", "Loaded prompt file", prompt_length=len(prompt)
        )

        # Add context
        prompt += f"\n\n---\n\n**Output Directory**: {self.output_dir}\n"
        prompt += f"**Project Directory**: {self.project_dir}\n"

        if additional_context:
            prompt += f"\n{additional_context}\n"
            debug_detailed(
                "roadmap_executor",
                "Added additional context",
                context_length=len(additional_context),
            )

        # Create client with thinking budget
        debug(
            "roadmap_executor",
            "Creating Claude client",
            project_dir=str(self.project_dir),
            model=self.model,
            thinking_budget=self.thinking_budget,
        )
        client = self.create_client(
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
                debug("roadmap_executor", "Legacy feature tracking session started")
            except Exception as e:
                debug_error("roadmap_executor", f"Failed to start legacy tracking session: {e}")

        # Derive agent type from prompt file name
        agent_type = prompt_file.replace(".md", "").replace("roadmap_", "")

        # Create Langfuse trace context wrapper
        async def _execute_agent() -> tuple[bool, str]:
            """Execute the agent (wrapped by trace_context if available)."""
            try:
                async with client:
                    debug("roadmap_executor", "Sending query to agent")
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
                                debug_error("roadmap_executor", f"Failed to track message: {e}")

                        if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                            for block in msg.content:
                                block_type = type(block).__name__
                                if block_type == "TextBlock" and hasattr(block, "text"):
                                    response_text += block.text
                                    print(block.text, end="", flush=True)
                                elif block_type == "ToolUseBlock" and hasattr(
                                    block, "name"
                                ):
                                    debug_detailed(
                                        "roadmap_executor", f"Tool called: {block.name}"
                                    )
                                    print(f"\n[Tool: {block.name}]", flush=True)

                        # Track result message for final totals
                        if self.tracker and msg_type == "ResultMessage":
                            try:
                                await self.tracker.track_message(msg)
                            except Exception as e:
                                debug_error("roadmap_executor", f"Failed to track result: {e}")

                        # Extract usage for Langfuse logging
                        if msg_type == "ResultMessage" and hasattr(msg, "usage"):
                            usage = msg.usage
                            if hasattr(usage, "input_tokens"):
                                total_input_tokens = usage.input_tokens
                            if hasattr(usage, "output_tokens"):
                                total_output_tokens = usage.output_tokens

                    print()

                    # Log generation to Langfuse if enabled
                    if self.langfuse_enabled and LANGFUSE_AVAILABLE:
                        try:
                            log_generation_in_current_trace(
                                name=f"roadmap-{agent_type}",
                                model=self.model,
                                input_data=prompt,  # FULL CONTENT - no truncation
                                output_data=response_text,  # FULL CONTENT - no truncation
                                usage={
                                    "input": total_input_tokens,
                                    "output": total_output_tokens,
                                    "total": total_input_tokens + total_output_tokens,
                                },
                                metadata={
                                    "prompt_file": prompt_file,
                                    "thinking_budget": self.thinking_budget,
                                },
                            )
                            debug("roadmap_executor", "Logged generation to Langfuse")
                        except Exception as e:
                            debug_error("roadmap_executor", f"Failed to log to Langfuse: {e}")

                    debug_success(
                        "roadmap_executor",
                        f"Agent completed: {prompt_file}",
                        response_length=len(response_text),
                    )

                    # Finalize legacy tracking
                    if self.tracker:
                        try:
                            await self.tracker.finalize()
                            totals = self.tracker.get_totals()
                            debug(
                                "roadmap_executor",
                                "Legacy feature tracking finalized",
                                total_cost_usd=totals.get("total_cost_usd", 0),
                                total_input_tokens=totals.get("total_input_tokens", 0),
                                total_output_tokens=totals.get("total_output_tokens", 0),
                            )
                        except Exception as e:
                            debug_error("roadmap_executor", f"Failed to finalize legacy tracking: {e}")

                    return True, response_text

            except Exception as e:
                debug_error(
                    "roadmap_executor", f"Agent failed: {prompt_file}", error=str(e)
                )
                # Still try to finalize tracking on error
                if self.tracker:
                    try:
                        await self.tracker.finalize()
                    except Exception:
                        pass
                return False, str(e)

        # Execute with Langfuse trace context if available
        start_time = time.time()
        if self.langfuse_enabled and trace_context:
            trace_name = f"roadmap-{self.project_id}-{agent_type}"
            with trace_context(
                name=trace_name,
                project_id=self.project_id,  # Required for data isolation filtering
                agent_type=f"roadmap_{agent_type}",
                metadata={
                    "prompt_file": prompt_file,
                    "model": self.model,
                    "thinking_budget": self.thinking_budget,
                    "feature_type": self.feature_type,
                },
                tags=["roadmap", f"agent:{agent_type}"],
                input_data={"prompt": prompt, "agent_type": agent_type},  # FULL CONTENT - no truncation
            ) as ctx:
                langfuse_trace_id = ctx.trace_id if ctx else None
                if ctx:
                    debug("roadmap_executor", f"Created Langfuse trace: {langfuse_trace_id}")
                result = await _execute_agent()
                duration_seconds = time.time() - start_time

                # Set trace output before exiting context
                if ctx and result:
                    success, response_text = result
                    ctx.set_output({"success": success, "response": response_text})  # FULL CONTENT - no truncation

                    # Publish ROI metrics (wrapped in try/except to not break roadmap)
                    if ROI_PUBLISHER_AVAILABLE and success:
                        try:
                            # Try to load roadmap data for artifact extraction
                            roadmap_data = None
                            roadmap_file = self.output_dir / "roadmap.json"
                            if roadmap_file.exists():
                                try:
                                    with open(roadmap_file) as f:
                                        roadmap_data = json.load(f)
                                except Exception as e:
                                    debug_error("roadmap_executor", f"Failed to load roadmap.json: {e}")

                            # Extract artifacts from the roadmap
                            artifacts, langfuse_refs = extract_roadmap_artifacts(
                                response_text,
                                roadmap_data,
                                project_dir=self.project_dir,
                                trace_id=langfuse_trace_id,
                                agent_type=f"roadmap_{agent_type}",
                            )

                            # Count metrics from roadmap data and artifacts
                            features_count = len(roadmap_data.get("features", [])) if roadmap_data else 0
                            phases_count = len(roadmap_data.get("phases", [])) if roadmap_data else 0
                            priority_recs = len([a for a in artifacts if a["type"] == "priority_recommendation"])

                            # Estimate cost and tokens
                            estimated_tokens = len(response_text) // 4 + len(prompt) // 4
                            estimated_cost = (estimated_tokens / 1000) * 0.003

                            # Calculate total artifact value
                            total_artifact_value = sum(a.get("value_usd", 0) for a in artifacts)

                            # Publish ROI with Langfuse refs (truncated previews, not full content)
                            roi_result = await publish_feature_roi(
                                feature_type="roadmap_features",
                                project_id=self.project_id,
                                cost_usd=estimated_cost,
                                tokens=estimated_tokens,
                                metrics={
                                    "features_identified": features_count,
                                    "features_prioritized": features_count,
                                    "features_rejected": 0,
                                    "competitor_insights": 0,
                                    "phases_count": phases_count,
                                    "priority_recommendations": priority_recs,
                                    "artifacts_count": len(artifacts),
                                    "artifact_value_usd": total_artifact_value,
                                },
                                duration_seconds=duration_seconds,
                                model=self.model,
                                trace_id=langfuse_trace_id,
                                artifacts=langfuse_refs,  # Pass refs (with storage_path) for Langfuse
                            )

                            debug(
                                "roadmap_executor",
                                "ROI published",
                                trace_id=langfuse_trace_id,
                                artifacts_count=len(artifacts),
                                artifact_value=total_artifact_value,
                                roi_percentage=roi_result.get("roi_percentage", 0),
                            )

                        except Exception as e:
                            # ROI publishing should never break roadmap
                            debug_error("roadmap_executor", f"Failed to publish ROI (non-fatal): {e}")

                # Flush to ensure trace is sent
                if LANGFUSE_AVAILABLE:
                    flush_langfuse()
                # Unpack result and add trace_id
                if result:
                    return result[0], result[1], langfuse_trace_id
                return False, "", langfuse_trace_id
        else:
            # Run without Langfuse tracing
            result = await _execute_agent()
            duration_seconds = time.time() - start_time

            # Still publish ROI even without Langfuse tracing
            if ROI_PUBLISHER_AVAILABLE and result and result[0]:
                try:
                    success, response_text = result

                    # Try to load roadmap data for artifact extraction
                    roadmap_data = None
                    roadmap_file = self.output_dir / "roadmap.json"
                    if roadmap_file.exists():
                        try:
                            with open(roadmap_file) as f:
                                roadmap_data = json.load(f)
                        except Exception as e:
                            debug_error("roadmap_executor", f"Failed to load roadmap.json: {e}")

                    # Extract artifacts from the roadmap
                    artifacts, langfuse_refs = extract_roadmap_artifacts(
                        response_text,
                        roadmap_data,
                        project_dir=self.project_dir,
                        trace_id=None,
                        agent_type=f"roadmap_{agent_type}",
                    )

                    # Count metrics
                    features_count = len(roadmap_data.get("features", [])) if roadmap_data else 0
                    phases_count = len(roadmap_data.get("phases", [])) if roadmap_data else 0
                    priority_recs = len([a for a in artifacts if a["type"] == "priority_recommendation"])

                    # Estimate cost and tokens
                    estimated_tokens = len(response_text) // 4 + len(prompt) // 4
                    estimated_cost = (estimated_tokens / 1000) * 0.003

                    # Calculate total artifact value
                    total_artifact_value = sum(a.get("value_usd", 0) for a in artifacts)

                    # Publish ROI
                    await publish_feature_roi(
                        feature_type="roadmap_features",
                        project_id=self.project_id,
                        cost_usd=estimated_cost,
                        tokens=estimated_tokens,
                        metrics={
                            "features_identified": features_count,
                            "features_prioritized": features_count,
                            "features_rejected": 0,
                            "competitor_insights": 0,
                            "phases_count": phases_count,
                            "priority_recommendations": priority_recs,
                            "artifacts_count": len(artifacts),
                            "artifact_value_usd": total_artifact_value,
                        },
                        duration_seconds=duration_seconds,
                        model=self.model,
                        artifacts=langfuse_refs,
                    )

                    debug(
                        "roadmap_executor",
                        "ROI published (no Langfuse trace)",
                        artifacts_count=len(artifacts),
                        artifact_value=total_artifact_value,
                    )

                except Exception as e:
                    debug_error("roadmap_executor", f"Failed to publish ROI (non-fatal): {e}")

            if result:
                return result[0], result[1], None
            return False, "", None
