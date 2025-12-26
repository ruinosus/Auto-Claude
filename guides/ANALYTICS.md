# Analytics Dashboard

Comprehensive cost tracking and usage analytics for Auto-Claude.

---

## Overview

The Analytics Dashboard provides real-time visibility into your Auto-Claude usage, helping you:

- **Monitor Costs** - Track Claude API costs across all specs and sessions
- **Manage Budgets** - Set per-spec budgets with automated alerts
- **Analyze Usage** - Understand token consumption, model distribution, and session patterns
- **Agent Access** - Programmatic API for agents to query analytics data

---

## Getting Started

### Accessing the Dashboard

1. Open the Auto-Claude desktop application
2. Click **Analytics** in the left sidebar
3. View real-time metrics and charts

The dashboard automatically tracks all conversations in your current project.

### How It Works

Analytics data is stored in a local SQLite database (`analytics.db`) in your project's `.auto-claude/` directory. The dashboard polls this database every 2 seconds for real-time updates.

---

## Features

### Overview Cards

At the top of the dashboard, three cards display global metrics:

- **Total Cost** - Cumulative cost across all specs and sessions
- **Total Tokens** - Input and output tokens (with cache breakdown)
- **Active Sessions** - Number of currently running conversations

### Charts

#### Cost Over Time

Line chart showing cumulative cost progression with budget limit overlay.

- **X-axis**: Timeline of conversations
- **Y-axis**: Cost in USD
- **Red dashed line**: Budget limit (if set)
- **Alerts**: Visual indicator when approaching or exceeding budget

#### Token Usage

Stacked bar chart displaying token consumption by spec.

- **Green bars**: Input tokens
- **Blue bars**: Output tokens
- **Grouped by**: Spec ID
- **Use case**: Identify token-heavy specs

#### Model Distribution

Pie chart showing usage breakdown by Claude model.

- **Segments**: Each model version (opus, sonnet, haiku)
- **Percentages**: Based on conversation count
- **Use case**: Understand model selection patterns

#### Session Duration

Horizontal bar chart of completed session durations.

- **X-axis**: Duration in minutes
- **Y-axis**: Session ID
- **Use case**: Identify long-running sessions

---

## Budget Management

Set per-spec budgets to prevent overspending.

### Setting a Budget

1. In the Analytics Dashboard, locate the **Budget Manager** section
2. Enter a budget amount in USD
3. Click **Set Budget**

### Budget Alerts

Receive visual alerts as you approach your budget:

- **80% (Yellow)** - Warning threshold
- **90%+ (Red)** - Budget exceeded

Alerts appear in the Budget Manager section and on the Cost Over Time chart.

### Budget Progress

The Budget Manager displays:

- **Progress bar** - Visual representation of budget utilization
- **Percentage** - Exact budget usage
- **Remaining** - Available budget
- **Status** - Color-coded alert level

---

## Database Schema

Analytics data is stored in SQLite with the following schema:

### `conversations` Table

Main table tracking each agent session.

```sql
CREATE TABLE conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spec_id TEXT NOT NULL,
  phase TEXT,                         -- planner, coder, qa_reviewer, etc.
  started_at TIMESTAMP NOT NULL,
  ended_at TIMESTAMP,                 -- NULL for active sessions
  total_cost_usd REAL DEFAULT 0,
  total_input_tokens INTEGER DEFAULT 0,
  total_output_tokens INTEGER DEFAULT 0,
  cache_creation_tokens INTEGER DEFAULT 0,
  cache_read_tokens INTEGER DEFAULT 0,
  model TEXT                          -- claude-opus-4, claude-sonnet-3-5, etc.
);
```

### `conversation_turns` Table

Individual messages within each conversation.

```sql
CREATE TABLE conversation_turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  turn_number INTEGER NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  role TEXT NOT NULL,                 -- user, assistant
  cost REAL DEFAULT 0,
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  cache_creation_tokens INTEGER DEFAULT 0,
  cache_read_tokens INTEGER DEFAULT 0,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

### `spec_totals` View

Aggregated view for per-spec analytics (auto-generated).

```sql
CREATE VIEW spec_totals AS
SELECT
  spec_id,
  SUM(total_cost_usd) as total_cost_usd,
  SUM(total_input_tokens) as total_input_tokens,
  SUM(total_output_tokens) as total_output_tokens,
  COUNT(*) as conversation_count
FROM conversations
GROUP BY spec_id;
```

---

## Python Analytics API

For programmatic access (e.g., from agents or scripts), Auto-Claude provides a FastAPI HTTP server.

### Starting the API Server

```bash
cd apps/backend
export ANALYTICS_DB_PATH=/path/to/your/project/.auto-claude/analytics.db
python -m analytics.api
```

The API runs on `http://localhost:8765` by default.

### Available Endpoints

#### Health Check

```bash
GET /health
```

Returns database connectivity status.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

#### Global Totals

```bash
GET /analytics/totals
```

Returns cumulative metrics across all specs.

**Response:**
```json
{
  "total_cost_usd": 12.45,
  "total_tokens": {
    "input": 150000,
    "output": 75000
  },
  "active_sessions": 2
}
```

#### Spec Analytics

```bash
GET /analytics/spec/{spec_id}
```

Returns metrics for a specific spec.

**Response:**
```json
{
  "spec_id": "001-feature",
  "total_cost_usd": 3.25,
  "total_tokens": {
    "input": 45000,
    "output": 22000
  },
  "conversation_count": 5
}
```

#### Recent Conversations

```bash
GET /analytics/conversations?limit=100
```

Returns recent conversation records.

**Query Parameters:**
- `limit` (optional): Max records (1-1000, default: 100)

**Response:**
```json
[
  {
    "id": 42,
    "spec_id": "001-feature",
    "phase": "coder",
    "cost": 0.85,
    "tokens": {
      "input": 12000,
      "output": 6000
    },
    "started_at": "2024-12-26T10:30:00",
    "ended_at": "2024-12-26T10:45:00"
  }
]
```

#### Cost Trend

```bash
GET /analytics/cost-trend?days=7
```

Returns daily cost aggregates.

**Query Parameters:**
- `days` (optional): Days to include (1-90, default: 7)

**Response:**
```json
[
  {
    "date": "2024-12-26",
    "cost": 5.25
  },
  {
    "date": "2024-12-25",
    "cost": 3.10
  }
]
```

### Using from Agents

Agents can query analytics using the Python `requests` library:

```python
import requests

# Get global totals
response = requests.get("http://localhost:8765/analytics/totals")
data = response.json()
print(f"Total cost: ${data['total_cost_usd']}")

# Get spec-specific data
spec_response = requests.get("http://localhost:8765/analytics/spec/001-feature")
spec_data = spec_response.json()
print(f"Spec cost: ${spec_data['total_cost_usd']}")
```

### Error Responses

All endpoints return standard HTTP status codes:

- **200** - Success
- **404** - Resource not found (e.g., spec doesn't exist)
- **500** - Database query error
- **503** - Database not configured or unavailable

**Example Error:**
```json
{
  "detail": "Spec '999-missing' not found"
}
```

---

## Architecture

### Frontend (Electron)

**Location**: `apps/frontend/src/renderer/components/analytics/`

**Components:**
- `Analytics.tsx` - Main dashboard container
- `OverviewCards.tsx` - Total cost, tokens, active sessions
- `CostChart.tsx` - Cost over time line chart (Recharts)
- `TokensChart.tsx` - Token usage bar chart
- `ModelDistributionChart.tsx` - Model distribution pie chart
- `SessionDurationChart.tsx` - Session duration bars
- `BudgetManager.tsx` - Budget settings and alerts

**State Management:**
- `analytics-store.ts` - Zustand store for budget and filters
- `useAnalyticsData.ts` - React hook for SQLite polling (2s interval)

**IPC Communication:**
- Handler: `analytics:get-db-path` (in `project-handlers.ts`)
- Returns path to `analytics.db` for current project

### Backend (Python)

**Location**: `apps/backend/analytics/`

**Files:**
- `api.py` - FastAPI HTTP server
- `test_api.py` - Comprehensive API tests
- `requirements.txt` - FastAPI, uvicorn, etc.

**Database:**
- SQLite (embedded)
- Location: `.auto-claude/analytics.db` in project root
- Migrations: Auto-created on first run

### Data Flow

```
Agent Session
    ↓
Write to analytics.db
    ↓
Frontend polls DB every 2s
    ↓
Charts update in real-time
```

---

## Testing

### E2E Tests

**Location**: `apps/frontend/e2e/analytics-dashboard.e2e.ts`

27 comprehensive tests covering:
- Database schema validation
- SQL aggregations
- Chart data transformations
- Budget calculations
- Error handling
- Real-time updates

**Run tests:**
```bash
cd apps/frontend
npm run test:e2e -- analytics-dashboard.e2e.ts
```

**Test coverage:**
- Infrastructure (6 tests)
- Data flow (5 tests)
- Error states (4 tests)
- Budget manager (4 tests)
- Chart data (4 tests)
- Real-time updates (3 tests)

See [apps/frontend/e2e/ANALYTICS_DASHBOARD_E2E_SUMMARY.md](../apps/frontend/e2e/ANALYTICS_DASHBOARD_E2E_SUMMARY.md) for detailed test documentation.

### API Tests

**Location**: `apps/backend/analytics/test_api.py`

**Run tests:**
```bash
cd apps/backend
pytest analytics/test_api.py -v
```

---

## Development

### Adding New Charts

1. **Create chart component** in `apps/frontend/src/renderer/components/analytics/`
2. **Add data query** in `useAnalyticsData.ts`
3. **Import and render** in `Analytics.tsx`
4. **Add tests** in `analytics-dashboard.e2e.ts`

**Example:**
```tsx
// NewChart.tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

export function NewChart({ data }: { data: ChartDataPoint[] }) {
  return (
    <BarChart data={data} width={600} height={300}>
      <XAxis dataKey="label" />
      <YAxis />
      <Tooltip />
      <Bar dataKey="value" fill="#8884d8" />
    </BarChart>
  );
}
```

### Adding New API Endpoints

1. **Add endpoint** in `apps/backend/analytics/api.py`
2. **Add tests** in `test_api.py`
3. **Update documentation** (this file)

**Example:**
```python
@app.get("/analytics/new-endpoint")
def get_new_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM conversations")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
```

---

## Troubleshooting

### Dashboard Not Loading

**Symptom**: Blank analytics screen

**Solutions:**
1. Check that project has `.auto-claude/analytics.db`
2. Verify database permissions (should be writable)
3. Open developer tools (View → Toggle Developer Tools) and check console for errors

### Database Locked Errors

**Symptom**: "Database is locked" errors in console

**Solutions:**
1. Close other SQLite connections (e.g., DB browser tools)
2. Restart the Electron app
3. Check for orphaned processes: `ps aux | grep electron`

### API Not Starting

**Symptom**: `curl http://localhost:8765/health` fails

**Solutions:**
1. Verify `ANALYTICS_DB_PATH` environment variable is set
2. Check port 8765 is not in use: `lsof -i :8765`
3. Check Python dependencies: `pip install -r analytics/requirements.txt`

### Missing Data in Charts

**Symptom**: Charts show "No data available"

**Solutions:**
1. Verify conversations exist in database
2. Run a test spec to generate data
3. Check SQL queries in browser console
4. Inspect database directly: `sqlite3 .auto-claude/analytics.db "SELECT COUNT(*) FROM conversations"`

---

## Performance Considerations

### Database Size

Analytics databases grow over time. Typical sizes:

- **Small projects** (10 specs): ~100 KB
- **Medium projects** (50 specs): ~1 MB
- **Large projects** (200+ specs): ~10 MB

SQLite handles these sizes efficiently with no performance impact.

### Polling Frequency

The dashboard polls every 2 seconds by default. To adjust:

**Edit `useAnalyticsData.ts`:**
```typescript
const POLL_INTERVAL = 5000; // Change to 5 seconds
```

Higher intervals reduce CPU usage but delay updates.

### Chart Performance

With 1000+ conversations, charts may slow down. Consider:

- Adding date range filters
- Limiting data points with SQL `LIMIT`
- Aggregating by day/week instead of individual conversations

---

## Privacy & Security

### Local Storage

All analytics data is stored locally in your project directory. Nothing is sent to external servers.

### Database Access

The SQLite database is only accessible:
- Locally on your machine
- Via the Electron app
- Via the Python API (localhost only by default)

### CORS Policy

The Python API restricts CORS to `localhost` origins only. For production use, update `CORSMiddleware` in `api.py`.

---

## Future Enhancements

Potential improvements for future development:

- **Export Reports** - CSV/PDF export for analytics data
- **Cost Predictions** - ML-based cost forecasting
- **Anomaly Detection** - Alert on unusual usage patterns
- **Team Analytics** - Multi-user aggregation
- **Custom Metrics** - User-defined KPIs
- **Historical Comparison** - Compare current vs. previous periods

---

## API Reference

Complete API documentation: [apps/backend/analytics/API.md](../apps/backend/analytics/API.md)

---

## Additional Resources

- **E2E Test Summary**: [apps/frontend/e2e/ANALYTICS_DASHBOARD_E2E_SUMMARY.md](../apps/frontend/e2e/ANALYTICS_DASHBOARD_E2E_SUMMARY.md)
- **Frontend README**: [apps/frontend/README.md](../apps/frontend/README.md)
- **Main README**: [../README.md](../README.md)

---

## Support

For issues or questions:

- **Discord**: [Join our community](https://discord.gg/KCXaPBr4Dj)
- **GitHub Issues**: [Report a bug](https://github.com/AndyMik90/Auto-Claude/issues)
- **Discussions**: [Ask a question](https://github.com/AndyMik90/Auto-Claude/discussions)
