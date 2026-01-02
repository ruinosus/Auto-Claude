# TODO: Artifacts & MCP Integration

**Created:** 2026-01-02
**Updated:** 2026-01-02
**Status:** Full content loading implemented

---

## Completed Work

### MCP Tool-Only Artifacts (2026-01-02)

**CRITICAL FIX:** Removed ALL regex-based artifact extraction. Artifacts MUST come from MCP tools.

**Files Fixed - Regex Extraction Removed:**
1. `runners/insights_runner.py` - Removed entire regex fallback block (~100 lines)
2. `spec/pipeline/orchestrator.py` - Removed diagram extraction from spec.md

**Agents Now Have ARTIFACT_TOOLS (models.py):**
- `planner` - Can create architecture_insight, diagram
- `coder` - Can create code_example, refactoring, bug_fix
- `qa_reviewer` - Can create security_finding, bug_fix, test_case
- `qa_fixer` - Can create bug_fix artifacts
- `insights` - Already had full ARTIFACT_TOOLS
- `pr_reviewer` - Can create code review findings
- `analysis` - Can create analysis artifacts
- `batch_analysis` - Can create triage artifacts
- `ideation` - Can create recommendation artifacts

**Prompts Updated with Artifact Tool Instructions:**
1. `prompts/planner.md` - Added CREATING ARTIFACTS section
2. `prompts/coder.md` - Added CREATING ARTIFACTS section
3. `prompts/qa_reviewer.md` - Added CREATING ARTIFACTS section
4. `prompts/qa_fixer.md` - Added CREATING ARTIFACTS section
5. `runners/insights_runner.py:build_system_prompt()` - Enhanced diagram instructions

**Available MCP Artifact Tools:**
- `create_artifact` - Generic artifact creation (any type)
- `create_diagram` - Diagrams (mermaid, ascii, plantuml)
- `report_security_finding` - Security vulnerabilities
- `suggest_recommendation` - Strategic recommendations

**Artifact Types:**
| Type | Tab | Description |
|------|-----|-------------|
| diagram | techlead | Architecture, flow, sequence diagrams |
| code_example | dev | Code snippet or implementation |
| refactoring | dev | Before/after refactoring |
| bug_fix | dev | Bug fix solution |
| test_case | dev | Test case or strategy |
| security_finding | ops | Security vulnerability |
| performance_insight | ops | Performance issue |
| architecture_insight | techlead | Architecture pattern |
| api_design | techlead | API design suggestion |
| documentation | techlead | Documentation insight |
| recommendation | business | Strategic recommendation |
| cost_analysis | business | Cost/ROI analysis |
| priority_assessment | business | Priority evaluation |

**Policy:**
- Artifacts are ONLY created via MCP tools
- NO regex extraction - if agent doesn't use tools, we don't get artifacts
- Agents are instructed to ALWAYS call tools, NEVER just output in text

---

### ZERO TRUNCATION Policy (2026-01-02)

**CRITICAL FIX:** Removed ALL truncation from artifact storage and Langfuse trace outputs.

**Files Fixed - Artifact Storage:**
1. `analytics/artifact_storage.py` - `create_langfuse_reference()` now stores FULL content
2. `runners/insights_runner.py` - Removed fallback truncation (lines 697-703)
3. `spec/pipeline/orchestrator.py` - Removed fallback truncation (lines 287-293)

**Files Fixed - Trace Output (removed `response_text[:3000]` pattern):**
4. `analysis/insight_extractor.py:547` - FULL response in trace output
5. `merge/ai_resolver/claude_client.py:216` - FULL response in trace output
6. `spec/pipeline/agent_runner.py:323` - FULL response in trace output
7. `spec/compaction.py:210` - FULL response in trace output
8. `ideation/generator.py:290` - FULL response in trace output
9. `agents/session.py:1015` - FULL response in trace output
10. `qa/fixer.py:701` - FULL response in trace output
11. `qa/reviewer.py:764` - FULL response in trace output
12. `runners/github/batch_issues.py:573` - FULL response in trace output

**Policy:**
- Artifacts are NEVER truncated, regardless of size
- Langfuse trace outputs store FULL response content
- Diagrams, code, and all other artifacts are complete
- Only legitimate truncations remain: debug logs, error messages, context window management

### Artifact Full Content Loading (2026-01-02)

**Problem:** Artifacts were displayed with truncated content (200-500 chars) even in "Full" mode because:
1. Artifacts are stored in Langfuse with truncated preview (intentional for performance)
2. Full content is stored locally in `.auto-claude/artifacts/`
3. API was returning Langfuse data (truncated) instead of loading full content

**Solution:**
1. Added `project_path` parameter to `/artifacts` API endpoint
2. Created `_enrich_artifact_with_full_content()` function to load from local storage
3. Added new endpoints: `/artifacts/local` and `/artifacts/local/{artifact_id}`
4. Updated frontend to pass `projectPath` through component hierarchy
5. Modified all tab components to pass `projectPath` to `ArtifactsPanel`

**Files Modified:**
- `apps/backend/analytics/api/routes.py` - Added artifact storage import, enrichment function, new endpoints
- `apps/frontend/src/renderer/services/analytics-api.ts` - Added `project_path` param, new API functions
- `apps/frontend/src/renderer/components/analytics/Analytics.tsx` - Pass `projectPath` to tabs
- `apps/frontend/src/renderer/components/analytics/artifacts/ArtifactsPanel.tsx` - Accept and use `projectPath`
- `apps/frontend/src/renderer/components/analytics/tabs/OverviewTab.tsx` - Accept and pass `projectPath`
- `apps/frontend/src/renderer/components/analytics/tabs/DevTab.tsx` - Accept and pass `projectPath`
- `apps/frontend/src/renderer/components/analytics/tabs/TechLeadTab.tsx` - Accept and pass `projectPath`
- `apps/frontend/src/renderer/components/analytics/tabs/OpsTab.tsx` - Accept and pass `projectPath`
- `apps/frontend/src/renderer/components/analytics/tabs/BusinessTab.tsx` - Accept and pass `projectPath`

### Backend Artifact/ROI Compliance (100% Complete)

All 13 backend files follow the artifact/ROI pattern:

| File | Status | Pattern |
|------|--------|---------|
| `qa/reviewer.py` | COMPLIANT | `extract_qa_review_artifacts()` + `publish_feature_roi()` |
| `qa/fixer.py` | COMPLIANT | `extract_qa_fix_artifacts()` + `publish_feature_roi()` |
| `agents/session.py` | COMPLIANT | `extract_coder_artifacts()` + `publish_feature_roi()` |
| `agents/planner.py` | COMPLIANT | `extract_planner_artifacts()` + `publish_feature_roi()` |
| `analysis/insight_extractor.py` | COMPLIANT | `extract_insight_artifacts()` + `publish_feature_roi()` |
| `merge/ai_resolver/claude_client.py` | COMPLIANT | `extract_merge_artifacts()` + `publish_feature_roi()` |
| `runners/ai_analyzer/claude_client.py` | COMPLIANT | `extract_analysis_artifacts()` + `publish_feature_roi()` |
| `runners/github/batch_issues.py` | COMPLIANT | `extract_issue_triage_artifacts()` + `publish_feature_roi()` |
| `runners/github/services/pr_review_engine.py` | COMPLIANT | `extract_pr_review_artifacts()` + `publish_feature_roi()` |
| `runners/github/services/orchestrator_reviewer.py` | COMPLIANT | Uses `pr_review_engine` pattern |
| `runners/gitlab/services/mr_reviewer.py` | COMPLIANT | `extract_mr_review_artifacts()` + `publish_feature_roi()` |
| `runners/insights_runner.py` | COMPLIANT | Uses `insight_extractor` pattern |
| `ideation/generator.py` | COMPLIANT | `extract_ideation_artifacts()` + `publish_feature_roi()` |

### MCP Artifact Tools (Complete)

Added 4 artifact tools to both MCP servers:

**STDIO Server** (`auto-claude-tools-stdio.ts`):
- Tool 12: `get_artifact` - Get single artifact by ID
- Tool 13: `list_artifacts` - List artifacts with filters
- Tool 14: `get_artifacts_by_trace` - Get artifacts by Langfuse trace
- Tool 15: `get_artifact_content` - Get raw artifact content

**HTTP Server** (`auto-claude-tools-http.ts`):
- Tool 4: `get_artifact`
- Tool 5: `list_artifacts`
- Tool 6: `get_artifacts_by_trace`
- Tool 7: `get_artifact_content`

### Frontend Fixes (Complete)

- Fixed EXPANDIR button bug in `ArtifactsPanel.tsx`
- Fixed modal rendering condition in `ArtifactDetailModal.tsx`

---

## Potential Future Improvements

### 1. Full Artifact Storage Implementation (COMPLETE)

All artifact truncation has been removed:

- [x] Create `apps/backend/analytics/artifact_storage.py` - Core storage module
- [x] Remove truncation from extraction functions
- [x] Remove truncation from Langfuse storage - FULL content stored
- [x] Remove truncation from trace outputs - FULL response stored
- [x] Add atomic writes with temp file + rename pattern

### 2. MCP Tool Enhancements

- [ ] Add artifact search by content (full-text search)
- [ ] Add artifact aggregation by agent type
- [ ] Add artifact statistics endpoint
- [ ] Add artifact export to various formats (JSON, Markdown)

### 3. Frontend Enhancements

- [ ] Add syntax highlighting in ArtifactDetailModal for code artifacts
- [ ] Add artifact filtering by date range
- [ ] Add artifact comparison view (diff two versions)
- [ ] Add artifact download as file

### 4. Backend Enhancements

- [ ] Add artifact versioning (track changes over time)
- [ ] Add artifact linking (parent/child relationships)
- [ ] Add artifact tagging system
- [ ] Add artifact cleanup/retention policies

---

## Documentation

All documentation is up-to-date:

- `docs/ARTIFACT_AND_ROI_SYSTEM.md` - Full artifact storage & ROI tracking
- `docs/AGENT_ARTIFACT_COMPLIANCE.md` - Agent implementation guide
- `docs/LANGFUSE_INTEGRATION.md` - Langfuse integration details

---

### 5. Thread-Safe Trace ID Propagation (2026-01-02)

**CRITICAL FIX:** Artifacts created via MCP tools were not being linked to Langfuse traces because the trace_id was not being passed to the tools.

**Root Cause:**
- MCP tools run in the parent process (where the runner lives)
- Tools tried to read `os.environ.get("LANGFUSE_TRACE_ID")` but it was never set
- Using `os.environ` would cause race conditions with concurrent requests

**Solution:**
Added thread-local storage for trace_id propagation:

1. **New functions in `langfuse_integration.py`:**
   - `set_current_trace_id(trace_id)` - Set trace_id in thread-local storage
   - `get_current_trace_id()` - Get trace_id from thread-local storage
   - `clear_current_trace_id()` - Clear trace_id from thread-local storage
   - `scoped_trace_id(trace_id)` - Context manager for scoped trace_id

2. **`trace_context` now auto-sets trace_id:**
   - When trace is created, `set_current_trace_id(trace_id)` is called
   - When trace exits, previous trace_id is restored or cleared
   - Supports nested traces correctly

3. **MCP artifact tools use thread-local storage:**
   - `artifact.py` now calls `get_current_trace_id()` first
   - Falls back to `os.environ.get("LANGFUSE_TRACE_ID")` for backwards compatibility

**Files Modified:**
- `analytics/langfuse_integration.py` - Added thread-local trace_id functions + trace_context integration
- `agents/tools_pkg/tools/artifact.py` - Use `get_current_trace_id()` for trace_id
- `runners/insights_runner.py` - Simplified (trace_context handles trace_id automatically)

**Benefits:**
- Thread-safe: Works correctly with concurrent requests
- Automatic: All code using `trace_context` gets the fix for free
- Backwards compatible: Falls back to environment variable if thread-local not set

---

## Notes

- HTTP server uses "Direct" suffix on helper functions to avoid naming conflicts
- Both servers share the same artifact file format
- Artifacts are stored in `.auto-claude/artifacts/{YYYY-MM-DD}/`
- Index file at `.auto-claude/artifacts/index.json` for fast lookups
