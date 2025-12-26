# Analytics API Reference

FastAPI HTTP server for programmatic access to Auto-Claude analytics data.

---

## Overview

The Analytics API provides REST endpoints for querying usage metrics, costs, and session data. It's designed for:

- **Agent Access** - Agents can query their own usage and costs
- **External Tools** - Integrate Auto-Claude analytics into dashboards or monitoring systems
- **Scripts & Automation** - Build custom reporting or alerting systems

---

## Starting the Server

### Basic Usage

```bash
cd apps/backend
export ANALYTICS_DB_PATH=/path/to/your/project/.auto-claude/analytics.db
python -m analytics.api
```

The server starts on `http://localhost:8765` by default.

### Custom Port

```bash
export PORT=9000
python -m analytics.api
```

### Production Mode

For production deployment, use a proper ASGI server:

```bash
uvicorn analytics.api:app --host 0.0.0.0 --port 8765 --workers 4
```

---

## Authentication

Currently, the API has **no authentication**. It's designed for local use only.

**Security Notes:**
- The API binds to `0.0.0.0` but CORS is restricted to `localhost` origins
- For production use, add authentication middleware
- Do not expose this API to the public internet without proper security

---

## Endpoints

### Health Check

Check if the API is running and database is accessible.

**Request:**
```http
GET /health
```

**Success Response (200):**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

**Error Response (503):**
```json
{
  "detail": "Database not configured. Set ANALYTICS_DB_PATH environment variable."
}
```

**Example:**
```bash
curl http://localhost:8765/health
```

---

### Global Totals

Get cumulative metrics across all specs and conversations.

**Request:**
```http
GET /analytics/totals
```

**Success Response (200):**
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

**Response Fields:**
- `total_cost_usd` (float): Total API cost in USD
- `total_tokens.input` (int): Total input tokens across all conversations
- `total_tokens.output` (int): Total output tokens across all conversations
- `active_sessions` (int): Number of conversations with `ended_at IS NULL`

**Example:**
```bash
curl http://localhost:8765/analytics/totals
```

**Use Cases:**
- Display global usage in dashboards
- Monitor total spend across projects
- Track active agent sessions

---

### Spec Analytics

Get analytics for a specific spec.

**Request:**
```http
GET /analytics/spec/{spec_id}
```

**Path Parameters:**
- `spec_id` (string): Spec identifier (e.g., "001-feature")

**Success Response (200):**
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

**Response Fields:**
- `spec_id` (string): The queried spec ID
- `total_cost_usd` (float): Total cost for this spec
- `total_tokens.input` (int): Input tokens for this spec
- `total_tokens.output` (int): Output tokens for this spec
- `conversation_count` (int): Number of conversations for this spec

**Error Response (404):**
```json
{
  "detail": "Spec '999-missing' not found"
}
```

**Example:**
```bash
curl http://localhost:8765/analytics/spec/001-feature
```

**Use Cases:**
- Check budget status for a spec
- Compare costs across different features
- Track per-feature resource consumption

---

### Recent Conversations

Get a list of recent conversation records.

**Request:**
```http
GET /analytics/conversations?limit=100
```

**Query Parameters:**
- `limit` (int, optional): Maximum number of records (1-1000, default: 100)

**Success Response (200):**
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
  },
  {
    "id": 41,
    "spec_id": "002-bugfix",
    "phase": "planner",
    "cost": 0.15,
    "tokens": {
      "input": 3000,
      "output": 1500
    },
    "started_at": "2024-12-26T09:00:00",
    "ended_at": null
  }
]
```

**Response Fields (per conversation):**
- `id` (int): Conversation database ID
- `spec_id` (string): Associated spec
- `phase` (string): Agent phase (planner, coder, qa_reviewer, etc.)
- `cost` (float): Conversation cost in USD
- `tokens.input` (int): Input tokens
- `tokens.output` (int): Output tokens
- `started_at` (string): ISO timestamp
- `ended_at` (string or null): ISO timestamp or `null` if still active

**Example:**
```bash
# Get 10 most recent conversations
curl "http://localhost:8765/analytics/conversations?limit=10"
```

**Use Cases:**
- Audit recent agent activity
- Identify long-running sessions
- Debug unexpected costs

---

### Cost Trend

Get daily cost aggregates for trend analysis.

**Request:**
```http
GET /analytics/cost-trend?days=7
```

**Query Parameters:**
- `days` (int, optional): Number of days to include (1-90, default: 7)

**Success Response (200):**
```json
[
  {
    "date": "2024-12-26",
    "cost": 5.25
  },
  {
    "date": "2024-12-25",
    "cost": 3.10
  },
  {
    "date": "2024-12-24",
    "cost": 2.85
  }
]
```

**Response Fields (per day):**
- `date` (string): Date in YYYY-MM-DD format
- `cost` (float): Total cost for that day in USD

**Example:**
```bash
# Get last 30 days of cost data
curl "http://localhost:8765/analytics/cost-trend?days=30"
```

**Use Cases:**
- Generate cost trend charts
- Identify usage spikes
- Budget forecasting

---

## Error Handling

All endpoints use standard HTTP status codes:

| Code | Description | Example |
|------|-------------|---------|
| 200 | Success | Request completed successfully |
| 404 | Not Found | Spec does not exist |
| 500 | Server Error | Database query failed |
| 503 | Service Unavailable | Database not configured or unreachable |

**Error Response Format:**
```json
{
  "detail": "Human-readable error message"
}
```

---

## Python Client Examples

### Basic Usage

```python
import requests

BASE_URL = "http://localhost:8765"

# Check health
response = requests.get(f"{BASE_URL}/health")
print(response.json())
# {'status': 'healthy', 'database': 'connected'}

# Get totals
response = requests.get(f"{BASE_URL}/analytics/totals")
data = response.json()
print(f"Total cost: ${data['total_cost_usd']:.2f}")
print(f"Active sessions: {data['active_sessions']}")
```

### Error Handling

```python
import requests

def get_spec_analytics(spec_id: str):
    """Get analytics for a spec with error handling."""
    try:
        response = requests.get(
            f"http://localhost:8765/analytics/spec/{spec_id}",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Spec '{spec_id}' not found")
        else:
            print(f"API error: {e.response.json()['detail']}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

# Usage
data = get_spec_analytics("001-feature")
if data:
    print(f"Spec cost: ${data['total_cost_usd']:.2f}")
```

### Agent Integration

```python
import requests
import os

class AnalyticsClient:
    """Client for Auto-Claude Analytics API."""

    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url

    def get_totals(self):
        """Get global analytics totals."""
        response = requests.get(f"{self.base_url}/analytics/totals")
        response.raise_for_status()
        return response.json()

    def get_spec(self, spec_id: str):
        """Get analytics for a specific spec."""
        response = requests.get(f"{self.base_url}/analytics/spec/{spec_id}")
        response.raise_for_status()
        return response.json()

    def get_recent_conversations(self, limit: int = 10):
        """Get recent conversations."""
        response = requests.get(
            f"{self.base_url}/analytics/conversations",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()

    def check_budget(self, spec_id: str, budget_limit: float) -> dict:
        """Check if spec is within budget."""
        spec_data = self.get_spec(spec_id)
        cost = spec_data["total_cost_usd"]
        percentage = (cost / budget_limit) * 100 if budget_limit > 0 else 0

        return {
            "spec_id": spec_id,
            "current_cost": cost,
            "budget_limit": budget_limit,
            "percentage_used": percentage,
            "within_budget": cost <= budget_limit,
            "alert_level": self._get_alert_level(percentage),
        }

    def _get_alert_level(self, percentage: float) -> str:
        """Get alert level based on budget percentage."""
        if percentage >= 90:
            return "critical"
        elif percentage >= 80:
            return "warning"
        else:
            return "ok"

# Usage in agent
client = AnalyticsClient()

# Check current spec's budget
current_spec = os.getenv("SPEC_ID", "001-feature")
budget_status = client.check_budget(current_spec, budget_limit=10.0)

if budget_status["alert_level"] != "ok":
    print(f"⚠️  Budget alert: {budget_status['percentage_used']:.1f}% used")
    print(f"   Current cost: ${budget_status['current_cost']:.2f}")
    print(f"   Budget limit: ${budget_status['budget_limit']:.2f}")
```

---

## cURL Examples

### Get Totals

```bash
curl -X GET http://localhost:8765/analytics/totals
```

### Get Spec Data

```bash
curl -X GET http://localhost:8765/analytics/spec/001-feature
```

### Get Recent Conversations

```bash
curl -X GET "http://localhost:8765/analytics/conversations?limit=5"
```

### Get 30-Day Cost Trend

```bash
curl -X GET "http://localhost:8765/analytics/cost-trend?days=30"
```

### Pretty Print with jq

```bash
curl -s http://localhost:8765/analytics/totals | jq '.'
```

---

## Database Schema

The API queries these SQLite tables:

### `conversations`

```sql
CREATE TABLE conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spec_id TEXT NOT NULL,
  phase TEXT,
  started_at TIMESTAMP NOT NULL,
  ended_at TIMESTAMP,
  total_cost_usd REAL DEFAULT 0,
  total_input_tokens INTEGER DEFAULT 0,
  total_output_tokens INTEGER DEFAULT 0,
  cache_creation_tokens INTEGER DEFAULT 0,
  cache_read_tokens INTEGER DEFAULT 0,
  model TEXT
);
```

### `conversation_turns`

```sql
CREATE TABLE conversation_turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  turn_number INTEGER NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  role TEXT NOT NULL,
  cost REAL DEFAULT 0,
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  cache_creation_tokens INTEGER DEFAULT 0,
  cache_read_tokens INTEGER DEFAULT 0,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

### `spec_totals` (View)

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

## CORS Configuration

The API restricts CORS to localhost origins for security:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

To allow additional origins, modify `allow_origin_regex` in `api.py`.

---

## Testing

### Running Tests

```bash
cd apps/backend
pytest analytics/test_api.py -v
```

### Test Coverage

The test suite (`test_api.py`) covers:

- Health check endpoint
- All analytics endpoints
- Error conditions (404, 503, 500)
- Query parameter validation
- Database connection handling

---

## Deployment

### Development

Use the built-in development server:

```bash
python -m analytics.api
```

### Production

Use uvicorn with multiple workers:

```bash
uvicorn analytics.api:app \
  --host 0.0.0.0 \
  --port 8765 \
  --workers 4 \
  --log-level info
```

### Docker

Example Dockerfile:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY analytics/ ./analytics/
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

ENV ANALYTICS_DB_PATH=/data/analytics.db
ENV PORT=8765

EXPOSE 8765

CMD ["uvicorn", "analytics.api:app", "--host", "0.0.0.0", "--port", "8765"]
```

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `ANALYTICS_DB_PATH` | Yes | Path to SQLite database | - |
| `PORT` | No | HTTP server port | 8765 |

---

## Performance

### Request Latency

Typical response times on a local SQLite database:

- `/health`: <5ms
- `/analytics/totals`: <10ms
- `/analytics/spec/{id}`: <10ms
- `/analytics/conversations`: <20ms (100 records)
- `/analytics/cost-trend`: <15ms (30 days)

### Concurrent Requests

SQLite supports multiple concurrent readers but only one writer. For high-concurrency scenarios, consider:

- Using connection pooling
- Implementing read replicas
- Migrating to PostgreSQL or MySQL

### Database Size Impact

Performance remains consistent up to ~100,000 conversation records. Beyond that, consider:

- Adding indexes on frequently queried columns
- Archiving old data
- Partitioning by date

---

## Security Considerations

### Local Use Only

The API is designed for local use and has minimal security:

- No authentication
- No rate limiting
- CORS restricted to localhost

### Production Deployment

If deploying to production:

1. **Add Authentication**: Implement API keys or OAuth
2. **Enable HTTPS**: Use TLS certificates
3. **Rate Limiting**: Prevent abuse
4. **Input Validation**: Sanitize user inputs
5. **Audit Logging**: Track API access

### Database Access

The API requires read-only access to the SQLite database. Grant minimal permissions:

```bash
chmod 644 analytics.db  # Read-only for group/others
```

---

## Troubleshooting

### API Won't Start

**Error**: "Address already in use"

**Solution**: Port 8765 is occupied. Use a different port:
```bash
export PORT=9000
python -m analytics.api
```

### Database Not Found

**Error**: "Database not found at /path/to/analytics.db"

**Solutions**:
1. Verify `ANALYTICS_DB_PATH` points to an existing file
2. Create the database by running an agent session
3. Check file permissions

### Empty Responses

**Symptom**: Endpoints return `0` or empty arrays

**Solutions**:
1. Verify database has data: `sqlite3 analytics.db "SELECT COUNT(*) FROM conversations"`
2. Check that specs exist in the database
3. Ensure `ended_at` is set for completed sessions

### CORS Errors

**Error**: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Solutions**:
1. Verify request is from localhost
2. Check browser console for exact origin
3. Update `allow_origin_regex` in `api.py` if needed

---

## API Versioning

Current version: **1.0.0**

The API follows semantic versioning:
- **Major**: Breaking changes
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes

Version is exposed in the `/health` response (future enhancement).

---

## Changelog

### 1.0.0 (2024-12-26)

Initial release with endpoints:
- `/health`
- `/analytics/totals`
- `/analytics/spec/{spec_id}`
- `/analytics/conversations`
- `/analytics/cost-trend`

---

## Additional Resources

- **User Guide**: [guides/ANALYTICS.md](../../../guides/ANALYTICS.md)
- **API Source Code**: [analytics/api.py](./api.py)
- **API Tests**: [analytics/test_api.py](./test_api.py)
- **Main README**: [../../../README.md](../../../README.md)

---

## Support

For API issues or questions:

- **Discord**: [Join our community](https://discord.gg/KCXaPBr4Dj)
- **GitHub Issues**: [Report a bug](https://github.com/AndyMik90/Auto-Claude/issues)
- **Discussions**: [Ask a question](https://github.com/AndyMik90/Auto-Claude/discussions)
