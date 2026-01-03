# Auto-Claude Extensions Layer

Zero-invasive instrumentation for Auto-Claude. Adds Langfuse tracing, artifact capture, ROI tracking, and session metrics **without modifying ANY upstream files**.

## Quick Start

```bash
# Install extension dependency
pip install wrapt

# Enable extensions via environment
export EXTENSIONS_ENABLED=true
export LANGFUSE_ENABLED=true
export LANGFUSE_HOST=http://localhost:3001
export LANGFUSE_PUBLIC_KEY=pk-lf-xxx
export LANGFUSE_SECRET_KEY=sk-lf-xxx

# Run any script normally - extensions auto-load!
python run.py --spec 001
python spec_runner.py --interactive
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Python Startup (PYTHONPATH includes apps/backend)          │
│                                                             │
│  sitecustomize.py executes automatically                    │
│  └── Checks EXTENSIONS_ENABLED=true                         │
│      └── extensions/patches/register_all_patches()          │
│          └── extensions/analytics/init_analytics()          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent Session Starts                                        │
│                                                             │
│  core/client.py creates ClaudeSDKClient                     │
│  └── Hooks from get_tracking_hooks() are attached           │
│      ├── PostToolUse: track_tool_timing                     │
│      ├── PostToolUse: capture_artifacts                     │
│      └── PostToolUse: track_tool_usage                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent Uses MCP Tool (e.g., create_diagram)                  │
│                                                             │
│  PostToolUse hooks fire automatically:                       │
│  1. session_tracker records timing                          │
│  2. artifact_capture saves with FULL content                │
│  3. Langfuse tracer records for observability               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Session Ends                                                │
│                                                             │
│  end_tracked_session() calculates:                          │
│  - Total artifact value (USD)                               │
│  - Token cost (USD)                                         │
│  - ROI percentage                                           │
│  - Publishes to Langfuse                                    │
└─────────────────────────────────────────────────────────────┘
```

## Files

```
apps/backend/
├── sitecustomize.py              # Auto-loader (NEW)
└── extensions/
    ├── __init__.py               # Package init
    ├── __main__.py               # CLI: python -m extensions.instrument
    ├── instrument.py             # Manual entry point
    ├── requirements.txt          # wrapt>=1.16.0
    ├── README.md                 # This file
    ├── TEST_SCENARIO.md          # Manual test guide
    ├── test_extensions.py        # Integration tests
    │
    ├── patches/                  # Wrapt patches
    │   ├── __init__.py           # register_all_patches()
    │   ├── client.py             # Patch for create_client
    │   ├── session.py            # Patch for run_agent_session
    │   └── hooks.py              # SDK PostToolUse hooks
    │
    └── analytics/                # Analytics modules
        ├── __init__.py           # Init + all exports
        ├── tracer.py             # Langfuse trace management
        ├── collector.py          # Legacy artifact collection
        ├── value_engine.py       # Artifact → USD value mapping
        ├── storage.py            # Atomic local storage
        ├── artifact_capture.py   # MCP tool artifact capture
        ├── roi_calculator.py     # ROI calculation
        └── session_tracker.py    # Token/timing/tool metrics
```

## Artifact Capture

### EXPLICIT MODE (Default, Recommended)

Artifacts are captured when agents **explicitly use MCP tools**:

```python
# Agent calls MCP tool
mcp__auto-claude__create_diagram(
    content="graph TD\n  A --> B",
    description="Architecture diagram"
)

# PostToolUse hook captures automatically
# Full content saved to .auto-claude/ext-artifacts/
```

**Supported tools:**
- `mcp__auto-claude__create_artifact`
- `mcp__auto-claude__create_diagram`
- `mcp__auto-claude__report_security_finding`
- `mcp__auto-claude__suggest_recommendation`
- `mcp__auto-claude__record_discovery`
- `mcp__auto-claude__record_gotcha`

**Requires:** Well-structured agent prompts that instruct agents to use these tools.

### EXTRACTION MODE (Optional Fallback)

Enable with `ARTIFACT_EXTRACTION_ENABLED=true`.

Uses regex to detect artifacts in tool outputs. Less reliable, may have false positives.

## Value Attribution

### Dimensions

| Dimension | Description | Example |
|-----------|-------------|---------|
| EXECUTION | Direct work completed | Code written, time saved |
| DECISION | Strategic choices enabled | Prioritization, scope decisions |
| PREVENTION | Problems avoided | Bugs fixed, security issues found |
| KNOWLEDGE | Learning captured | Patterns, gotchas documented |

### Base Values (USD)

| Artifact Type | Base Value | Dimension |
|---------------|------------|-----------|
| `security_finding` | $200 | Prevention |
| `diagram` | $150 | Knowledge |
| `gotcha_identified` | $150 | Prevention |
| `pattern_discovered` | $100 | Knowledge |
| `recommendation` | $75 | Decision |
| `code_snippet` | $50 | Execution |
| `lesson_learned` | $50 | Knowledge |

### Agent Confidence Multipliers

| Agent Type | Multiplier |
|------------|------------|
| `coder` | 0.85 |
| `qa_fixer` | 0.85 |
| `qa_reviewer` | 0.80 |
| `planner` | 0.75 |
| `spec_writer` | 0.75 |
| `insight_extractor` | 0.70 |
| `ideation` | 0.65 |
| `roadmap` | 0.60 |

**Final Value** = `base_value × artifact_confidence × agent_confidence`

## ROI Calculation

```
ROI = (Total Value - Total Cost) / Total Cost × 100
```

**Value Sources:**
- Artifact values (from value_engine)
- Time saved (estimated from artifact type)

**Cost Sources:**
- Token usage × model pricing
- Claude Opus: $15/M input, $75/M output
- Claude Sonnet: $3/M input, $15/M output
- Claude Haiku: $1/M input, $5/M output

## Storage (Integrated)

Extensions storage is a **wrapper** around the main `analytics/artifact_storage.py`.
All artifacts go to **one location** to avoid duplication:

```
.auto-claude/artifacts/           # Main storage (shared)
├── index.json                    # Master index
├── 2025-01-03/                   # Date-based organization
│   ├── art_abc123def456.json     # Full artifact
│   └── art_def456ghi789.json
└── 2025-01-02/
    └── art_ghi789jkl012.json
```

**Why integrated?**
- MCP tools (`create_artifact`, `create_diagram`, etc.) already save to main storage
- Extensions hooks detect this and skip duplicate saves
- ROI calculations are consistent (one source of truth)
- No duplicate artifact IDs or indices

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EXTENSIONS_ENABLED` | Enable extensions layer | `false` |
| `LANGFUSE_ENABLED` | Enable Langfuse tracing | `false` |
| `LANGFUSE_HOST` | Langfuse server URL | - |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | - |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | - |
| `ARTIFACT_EXTRACTION_ENABLED` | Enable regex extraction | `false` |
| `DEVELOPER_HOURLY_RATE` | USD/hour for time-saved calc | `150` |

## Usage

### Automatic (via sitecustomize.py)

Just set `EXTENSIONS_ENABLED=true` and run:

```bash
EXTENSIONS_ENABLED=true python run.py --spec 001
```

### Programmatic

```python
from extensions.patches.hooks import (
    start_tracked_session,
    end_tracked_session,
)

# Start tracking
session = start_tracked_session(
    agent_type="coder",
    trace_id="my-trace",
    spec_id="001",
)

# ... agent runs, hooks capture artifacts automatically ...

# End and get ROI
summary = end_tracked_session(status="completed")
print(f"ROI: {summary['roi']['roi']['roi_percentage']}%")
```

### Direct Module Usage

```python
from extensions.analytics import (
    get_artifact_value,
    save_artifact,
    calculate_session_roi,
)

# Calculate artifact value
value = get_artifact_value("diagram", "coder")
print(f"Diagram value: ${value['adjusted_value_usd']}")

# Save artifact
artifact = save_artifact(
    artifact_type="pattern_discovered",
    content="Always use dependency injection...",
    description="DI Pattern",
    value_usd=value["adjusted_value_usd"],
    trace_id="my-trace",
)
```

## Testing

```bash
cd apps/backend
python extensions/test_extensions.py
```

## Why This Approach?

### Problem

This is a fork of [AndyMik90/Auto-Claude](https://github.com/AndyMik90/Auto-Claude).
Every modification to upstream files causes merge conflicts.

### Solution

- **Zero modifications** to ANY upstream files
- Uses Python's native `sitecustomize.py` auto-loading
- All customization in NEW files only
- Uses [wrapt](https://github.com/GrahamDumpleton/wrapt) for safe monkey patching
- Uses Claude SDK's native hooks (PostToolUse)

### Merge Experience

```bash
# With extensions - no conflicts!
git merge upstream/develop
# Auto-merging...
# Already up to date. ✓
```

## Relationship to Existing Analytics

The extensions layer **integrates with** the existing `analytics/` module:

| Component | Source | Purpose |
|-----------|--------|---------|
| Artifact Storage | `analytics/artifact_storage.py` | Main storage (extensions delegate to this) |
| Value Engine | `extensions/analytics/value_engine.py` | Agent confidence multipliers |
| ROI Calculator | `extensions/analytics/roi_calculator.py` | Session ROI with time-saved values |
| Session Tracker | `extensions/analytics/session_tracker.py` | Token/timing metrics |
| Langfuse | `analytics/langfuse_integration.py` | Tracing (shared) |

**Integration Flow:**
1. Agent calls MCP tool (`create_artifact`) → saved to main storage with `art_` prefix
2. PostToolUse hook detects `artifact_id` in result → **skips duplicate save**
3. Hook tracks artifact for session metrics (value, count)
4. Session end calculates ROI from main storage artifacts

## Based On

- [Python sitecustomize.py](https://docs.python.org/3/library/site.html#module-sitecustomize)
- [OpenTelemetry Zero-Code Instrumentation](https://opentelemetry.io/docs/zero-code/python/)
- [wrapt - Safe Monkey Patching](https://github.com/GrahamDumpleton/wrapt)
- [Claude SDK Hooks](https://platform.claude.com/docs/en/agent-sdk/subagents)
