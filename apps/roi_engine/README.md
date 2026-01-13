# ROI Engine

Artifact-based ROI calculation for Auto-Claude.

## Vision

The ROI Engine tracks the **real value** Auto-Claude generates by measuring **artifacts produced** against **token costs**, using the simple formula:

```
ROI = (Artifact Value - Token Cost) / Token Cost × 100%
```

### Philosophy

Auto-Claude automates work that would be done by a **squad** of professionals:

| Role | Example Artifacts |
|------|-------------------|
| **Architect** | System diagrams, ADRs, API designs |
| **Tech Lead** | Specs, implementation plans, complexity assessments |
| **Developer** | Code implementations, refactoring, commits |
| **QA** | Test cases, QA reports, test suggestions |
| **DevOps** | Security findings, deployment plans, performance insights |
| **PM** | Recommendations, priority assessments, roadmap items |

Each artifact has a **value** based on:
- **Role**: Who would produce this artifact
- **Seniority**: Senior, Staff, Principal, etc.
- **Hourly Rate**: From squad configuration
- **Estimated Hours**: Time to produce this artifact type

**Value = Hourly Rate × Estimated Hours**

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXISTING ARTIFACT CREATION                    │
│                                                                   │
│  MCP Tools                    Extractors                         │
│  ─────────                    ──────────                         │
│  create_artifact()            extract_planner_artifacts()        │
│  create_diagram()             extract_qa_review_artifacts()      │
│                                                                   │
│         └──────────────┬───────────────┘                         │
│                        ▼                                          │
│              ┌─────────────────────┐                              │
│              │  artifact_storage   │                              │
│              └─────────────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
                         │
                         │ ROI Engine CONSUMES
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       ROI ENGINE                                 │
│                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │  Consumer   │───▶│  Valuator   │───▶│ Aggregator  │          │
│  │             │    │             │    │             │          │
│  │ Read from   │    │ artifact →  │    │ Σ values -  │          │
│  │ storage     │    │ role → $$$  │    │ token_cost  │          │
│  └─────────────┘    └─────────────┘    └─────────────┘          │
│                                               │                  │
│                                               ▼                  │
│                                      ┌─────────────┐            │
│                                      │  Publisher  │            │
│                                      │  Langfuse   │            │
│                                      └─────────────┘            │
│                                               │                  │
│                                               ▼                  │
│                                      ┌─────────────┐            │
│                                      │  REST API   │            │
│                                      │  FastAPI    │            │
│                                      └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## Structure

```
apps/roi_engine/
├── core/                     # Python core library
│   ├── __init__.py           # Package exports
│   ├── models.py             # ArtifactValue, ROIResult dataclasses
│   ├── mappings.py           # Artifact type → Role mapping
│   ├── config.py             # Squad configuration loader
│   ├── valuator.py           # Role-based value calculation
│   ├── consumer.py           # Read from artifact storage
│   ├── aggregator.py         # ROI calculation
│   └── publisher.py          # Langfuse integration
├── api/                      # FastAPI REST API
│   ├── __init__.py
│   ├── app.py                # FastAPI application
│   ├── routes/               # Route modules (11 files)
│   │   ├── __init__.py       # Route exports
│   │   ├── roi.py            # ROI calculation endpoints
│   │   ├── artifacts.py      # Artifact CRUD & management
│   │   ├── costs.py          # Cost analysis & billing
│   │   ├── quality.py        # Quality scores & breakdown
│   │   ├── traces.py         # Trace & session endpoints
│   │   ├── benchmarks.py     # Benchmarking endpoints
│   │   ├── forecasts.py      # Forecasting endpoints
│   │   ├── time_saved.py     # Time saved metrics
│   │   ├── satisfaction.py   # Satisfaction surveys
│   │   ├── migration.py      # Migration endpoints
│   │   └── config.py         # Configuration & health
│   └── models/               # Pydantic models (12 files)
│       ├── __init__.py       # Model exports
│       ├── common.py         # Health, Error responses
│       ├── roi.py            # ROI request/response models
│       ├── artifacts.py      # Artifact models
│       ├── costs.py          # Cost models
│       ├── quality.py        # Quality models
│       ├── traces.py         # Trace/Session models
│       ├── benchmarks.py     # Benchmark models
│       ├── forecasts.py      # Forecast models
│       ├── time_saved.py     # Time saved models
│       ├── satisfaction.py   # Satisfaction models
│       ├── migration.py      # Migration models
│       └── config.py         # Configuration models
├── sdk/                      # TypeScript SDK for frontend
│   ├── src/
│   │   ├── types.ts          # TypeScript interfaces
│   │   ├── client.ts         # API client
│   │   ├── hooks/            # React hooks (useROI, useArtifacts)
│   │   └── components/       # UI components
│   └── dist/                 # Built SDK
├── tests/                    # Test suite (88 tests)
├── pyproject.toml
└── README.md
```

## Installation

```bash
cd apps/roi-engine
uv pip install -e .

# With development dependencies
uv pip install -e ".[dev]"

# With Langfuse integration
uv pip install -e ".[langfuse]"
```

## Usage

### As a Library

```python
from roi_engine.core import (
    calculate_roi_for_spec,
    load_squad_config,
    publish_roi,
)

# Load squad configuration
squad_config = load_squad_config(project_dir="/path/to/project")

# Calculate ROI for a spec
roi_result = calculate_roi_for_spec(
    spec_id="001-feature",
    project_dir="/path/to/project",
    token_cost=0.85,
    squad_config=squad_config,
)

print(f"ROI: {roi_result.roi_percentage:.1f}%")
print(f"Value: ${roi_result.total_artifact_value:.2f}")
print(f"Cost: ${roi_result.token_cost:.2f}")

# Publish to Langfuse and local storage
await publish_roi(
    roi_result,
    trace_id="trace_abc123",
    project_dir="/path/to/project",
)
```

### As a REST API

```bash
# Start the API server
uvicorn roi_engine.api.app:app --host 0.0.0.0 --port 8002

# Or directly
python -m roi_engine.api.app
```

#### API Endpoints (63 total)

The API is organized into domain-specific route modules:

**ROI (`/api/roi/`)** - 6 endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/spec` | POST | Calculate ROI for a spec |
| `/spec/{spec_id}` | GET | Get ROI for a spec |
| `/trace` | POST | Calculate ROI for a trace |
| `/summary/{spec_id}` | GET | Simplified ROI summary |
| `/unified` | GET | Unified ROI metrics |
| `/trends` | GET | ROI trends over time |

**Artifacts (`/api/artifacts/`)** - 16 endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | List valued artifacts |
| `/{id}` | GET | Get single artifact |
| `/preview` | POST | Preview artifact value |
| `/search` | GET | Full-text search |
| `/local` | GET | Local storage listing |
| `/statistics` | GET | Aggregate statistics |
| `/timeline` | GET | Artifact timeline |
| `/by-role` | GET | Group by role |
| `/duplicates` | GET | Find duplicates |
| `/merge` | POST | Merge duplicates |
| `/{id}/status` | PUT | Update status |
| `/{id}/quality` | PUT | Update quality |
| `/{id}` | DELETE | Delete artifact |
| `/{id}/content` | PUT | Edit content |
| `/{id}/continue` | POST | LLM continuation |
| `/{id}/complete` | POST | Mark complete |

**Costs (`/api/costs/`)** - 8 endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/daily` | GET | Daily cost breakdown |
| `/hourly` | GET | Hourly cost patterns |
| `/billing` | GET | Billing summary |
| `/by-model` | GET | Costs by model |
| `/by-agent` | GET | Costs by agent |
| `/errors` | GET | Error costs |
| `/forecast` | GET | Cost projections |

**Quality (`/api/quality/`)** - 3 endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scores` | GET | Quality scores over time |
| `/by-agent` | GET | Quality by agent |
| `/value-breakdown` | GET | Value breakdown |

**Traces (`/api/traces/`)** - 4 endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | List traces |
| `/{id}` | GET | Get trace details |
| `/sessions` | GET | List sessions |
| `/activity/recent` | GET | Recent activity |

**Benchmarks (`/api/benchmark/`)** - 4 endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/efficiency` | GET | Efficiency metrics |
| `/squad` | GET | Compare squad configs |
| `/project` | GET | Compare projects |
| `/avoidance/*` | GET | Cost avoidance |

**Forecasts (`/api/forecast/`)** - 6 endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/roi` | GET | ROI projections |
| `/value` | GET | Value projections |
| `/artifacts` | GET | Artifact projections |
| `/compare` | GET | Forecast vs actual |
| `/scenarios` | POST | What-if scenarios |

**Time Saved (`/api/time-saved/`)** - 5 endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/summary` | GET | Time saved summary |
| `/by-task` | GET | By task type |
| `/trend` | GET | Time saved trend |
| `/dashboard` | GET | Dashboard data |
| `/benchmarks` | GET | Task benchmarks |

**Satisfaction (`/api/satisfaction/`)** - 6 endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/survey` | POST | Submit survey |
| `/metrics` | GET | Aggregated metrics |
| `/nps` | GET | Net Promoter Score |
| `/feedback` | GET | Feedback entries |
| `/surveys` | GET | List surveys |
| `/survey/{id}` | DELETE | Delete survey |

**Config (`/api/config/`)** - 3 endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rates` | GET | Rate table |
| `/artifact-types` | GET | Artifact types |
| `/roles` | GET | List roles |

**Health** - 2 endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check |
| `/api/health` | GET | Detailed health |

**Migration (`/api/migrate`)** - 1 endpoint
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | POST | Migrate artifacts |

#### Example Request

```bash
curl -X POST http://localhost:8002/api/roi/spec \
  -H "Content-Type: application/json" \
  -d '{
    "spec_id": "001-feature",
    "project_dir": "/path/to/project",
    "token_cost": 0.85
  }'
```

#### Example Response

```json
{
  "scope": "spec",
  "scope_id": "001-feature",
  "total_artifact_value": 1420.00,
  "artifact_count": 4,
  "by_role": {
    "tech_lead": 1120.00,
    "architect": 300.00
  },
  "by_type": {
    "spec_document": 517.50,
    "implementation_plan": 431.25,
    "project_context": 172.50,
    "architecture_diagram": 300.00
  },
  "token_cost": 0.85,
  "net_value": 1419.15,
  "roi_percentage": 166941.17,
  "calculated_at": "2024-01-15T10:30:00Z"
}
```

## Artifact Type → Role Mapping

The ROI Engine maps each artifact type to a role and estimated hours:

| Artifact Type | Role | Hours |
|---------------|------|-------|
| `diagram` | Architect | 2.0 |
| `architecture_insight` | Architect | 1.5 |
| `system_design` | Architect | 4.0 |
| `adr` | Architect | 3.0 |
| `spec_document` | Tech Lead | 3.0 |
| `implementation_plan` | Tech Lead | 2.5 |
| `code_example` | Developer | 1.0 |
| `test_case` | QA | 0.5 |
| `security_finding` | DevOps | 1.0 |
| `recommendation` | PM | 1.0 |

See `core/mappings.py` for the complete mapping of 60+ artifact types.

## Squad Configuration

The ROI Engine uses squad configuration to determine hourly rates:

```python
# Seniority base rates (USD/hr)
JUNIOR = $50
MID = $75
SENIOR = $125
STAFF = $175
PRINCIPAL = $225

# Role multipliers
DEVELOPER = 1.0
QA = 0.9
DEVOPS = 1.1
PM = 0.95
ARCHITECT = 1.2
TECH_LEAD = 1.15

# Example: Senior Architect = $125 × 1.2 = $150/hr
```

Configuration priority:
1. Environment variable: `SQUAD_CONFIG`
2. Project file: `{project_dir}/.auto-claude/squad_config.json`
3. Default configuration

## Integration

### With Existing Artifact Creation

The ROI Engine **consumes** artifacts created by:

1. **MCP Tools** (explicit agent calls):
   - `create_artifact()`
   - `create_diagram()`
   - `report_security_finding()`
   - `suggest_recommendation()`

2. **Extraction Functions** (post-execution):
   - `extract_planner_artifacts()`
   - `extract_qa_review_artifacts()`
   - `extract_roadmap_artifacts()`

### With Langfuse

The ROI Engine publishes scores to Langfuse:
- `artifact_based_roi` - Main ROI percentage
- `total_artifact_value` - Total value generated
- `token_cost` - Cost incurred
- `net_value` - Net value (value - cost)
- `value_by_{role}` - Value by each role

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type checking
pyright

# Linting
ruff check .
ruff format .
```

## License

MIT
