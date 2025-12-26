# OpenTelemetry Configuration Guide

This guide explains how to configure OpenTelemetry (OTLP) export for Auto-Claude analytics.

## Quick Start

### 1. Enable OpenTelemetry

Add to `.env`:
```bash
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

### 2. Run an OTLP Collector

**Using Docker (SigNoz):**
```bash
git clone https://github.com/SigNoz/signoz.git
cd signoz/deploy
./install.sh
```

**Using Langfuse:**
```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk_...
LANGFUSE_SECRET_KEY=sk_...
```

### 3. Verify Metrics

Run Auto-Claude and check your observability platform for metrics:
- `auto_claude.tokens.total`
- `auto_claude.cost.total_usd`
- `auto_claude.sessions.total`

## Metrics Reference

### Counters (Cumulative)

| Metric | Unit | Description | Attributes |
|--------|------|-------------|------------|
| `auto_claude.tokens.total` | tokens | Total tokens consumed | spec_id, phase, model |
| `auto_claude.cost.total_usd` | USD | Total cost in USD | spec_id, phase, model |
| `auto_claude.sessions.total` | sessions | Total sessions run | spec_id, phase |

### Histograms (Distributions)

| Metric | Unit | Description | Attributes |
|--------|------|-------------|------------|
| `auto_claude.tokens.per_message` | tokens | Token distribution per message | spec_id, phase, model |
| `auto_claude.cost.per_session_usd` | USD | Cost per session | spec_id, phase |
| `auto_claude.session.duration_seconds` | seconds | Session duration | spec_id, phase |

### UpDownCounters (Current Values)

| Metric | Unit | Description |
|--------|------|-------------|
| `auto_claude.sessions.active` | sessions | Currently active sessions |

## Backend Configurations

### Langfuse

Langfuse provides LLM observability with traces, metrics, and analytics.

```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk_lf_...
LANGFUSE_SECRET_KEY=sk_lf_...
LANGFUSE_HOST=https://cloud.langfuse.com
```

**Get Started:**
1. Sign up at [langfuse.com](https://langfuse.com)
2. Create a project
3. Copy your API keys from Settings → API Keys
4. Add to `.env`

### SigNoz

SigNoz is an open-source observability platform (self-hosted or cloud).

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

**Self-Hosted Setup:**
```bash
git clone https://github.com/SigNoz/signoz.git
cd signoz/deploy
./install.sh
```

**Cloud Setup:**
```bash
SIGNOZ_ENABLED=true
SIGNOZ_ENDPOINT=https://ingest.{region}.signoz.cloud:443
```

### Grafana Cloud

Grafana Cloud provides managed observability with metrics, logs, and traces.

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net/otlp
GRAFANA_CLOUD_API_KEY=...
```

**Get Started:**
1. Sign up at [grafana.com](https://grafana.com/auth/sign-up/create-user)
2. Navigate to Connections → Add new connection → OpenTelemetry
3. Copy your endpoint and API key
4. Add to `.env`

### Custom OTLP Collector

Use any OTLP-compatible collector (OpenTelemetry Collector, Jaeger, etc.).

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://your-collector:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
```

**Example: OpenTelemetry Collector**
```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

exporters:
  logging:
    loglevel: debug
  prometheus:
    endpoint: 0.0.0.0:8889

service:
  pipelines:
    metrics:
      receivers: [otlp]
      exporters: [logging, prometheus]
```

Run with Docker:
```bash
docker run -p 4317:4317 -p 4318:4318 \
  -v $(pwd)/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
  otel/opentelemetry-collector:latest \
  --config=/etc/otel-collector-config.yaml
```

## Configuration Reference

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_ENABLED` | `true` | Enable/disable OTel export (opt-out) |
| `OTEL_SERVICE_NAME` | `auto-claude` | Service name in metrics |
| `ENVIRONMENT` | `production` | Environment tag |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP collector endpoint |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc` | Protocol: `grpc` or `http` |
| `OTEL_EXPORT_INTERVAL_SECONDS` | `60` | How often to export metrics |

### Advanced Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_TRACES_ENABLED` | `false` | Enable distributed tracing |
| `OTEL_EXPORTER_OTLP_INSECURE` | `false` | Disable TLS verification |
| `OTEL_EXPORTER_OTLP_HEADERS` | - | Custom headers (e.g., auth tokens) |
| `OTEL_EXPORTER_OTLP_TIMEOUT` | `10` | Export timeout in seconds |

### Backend-Specific Settings

**Langfuse:**
```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk_lf_...
LANGFUSE_SECRET_KEY=sk_lf_...
LANGFUSE_HOST=https://cloud.langfuse.com
```

**SigNoz:**
```bash
SIGNOZ_ENABLED=true
SIGNOZ_ENDPOINT=http://localhost:4317
```

**Grafana Cloud:**
```bash
GRAFANA_ENABLED=true
GRAFANA_CLOUD_API_KEY=...
GRAFANA_CLOUD_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net/otlp
```

## Example Dashboards

### Tokens by Phase

Query tokens consumed per phase:
```promql
sum by (phase) (auto_claude_tokens_total)
```

### Cost by Model

Track spending per model:
```promql
sum by (model) (auto_claude_cost_total_usd)
```

### Session Duration Distribution

Analyze session performance:
```promql
histogram_quantile(0.95, auto_claude_session_duration_seconds)
```

### Active Sessions

Monitor concurrent builds:
```promql
auto_claude_sessions_active
```

## Troubleshooting

### No metrics appearing

**Check 1: Verify OTEL is enabled**
```bash
grep OTEL_ENABLED .env
# Should output: OTEL_ENABLED=true
```

**Check 2: Verify endpoint is reachable**
```bash
curl http://localhost:4317
# Should connect (or show gRPC error, which is OK)
```

**Check 3: Check Auto-Claude logs**
```bash
grep -i "otel\|telemetry" auto-claude/logs/*.log
```

**Check 4: Test with verbose logging**
```bash
DEBUG=true DEBUG_LEVEL=3 python auto-claude/run.py --spec 001
```

### High latency or performance impact

**Increase export interval:**
```bash
OTEL_EXPORT_INTERVAL_SECONDS=300  # 5 minutes
```

**Use async export (automatic):**
Auto-Claude uses `PeriodicExportingMetricReader` which exports asynchronously in the background.

**Disable histograms (if needed):**
Histograms consume more memory than counters. If you only need totals, you can monitor specific metrics in your backend.

### Connection errors

**Error: `Connection refused`**
- Ensure your OTLP collector is running
- Verify the endpoint URL and port

**Error: `SSL certificate verify failed`**
```bash
OTEL_EXPORTER_OTLP_INSECURE=true
```

**Error: `Timeout`**
```bash
OTEL_EXPORTER_OTLP_TIMEOUT=30  # Increase timeout
```

### Disable temporarily

To disable OTel without removing configuration:
```bash
OTEL_ENABLED=false
```

## Performance Impact

### Resource Usage

- **Memory:** ~2-5MB per active session
- **CPU:** <0.1% overhead
- **Network:** ~1KB per message exported
- **Disk:** None (metrics stored in collector)

### Export Behavior

- **Batching:** Metrics are batched and exported every `OTEL_EXPORT_INTERVAL_SECONDS`
- **Async:** Export happens in background thread, non-blocking
- **Retry:** Failed exports are retried automatically
- **Overflow:** If collector is unreachable, metrics are dropped (no memory accumulation)

## Security

### What's Exported

**Included in metrics:**
- Spec ID (e.g., `001-feature`)
- Phase name (e.g., `planner`, `coder`)
- Model name (e.g., `claude-opus-4-5`)
- Token counts (input, output, total)
- Cost in USD
- Session duration

**NOT included in metrics:**
- Source code
- Prompts or responses
- File paths or contents
- Secrets or API keys
- Personal identifiable information (PII)

### Transport Security

**Development (local collector):**
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

**Production (TLS required):**
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://collector.company.com:4318
```

**With authentication:**
```bash
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer your-token"
```

### Compliance

OpenTelemetry metrics contain only aggregated usage data. No code or prompts are transmitted. This makes OTel suitable for:
- GDPR compliance (no PII)
- SOC 2 compliance (usage auditing)
- Internal cost tracking

## Examples

### Example 1: Local Development with SigNoz

```bash
# 1. Start SigNoz
git clone https://github.com/SigNoz/signoz.git
cd signoz/deploy
./install.sh

# 2. Configure Auto-Claude
cat >> .env <<EOF
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=auto-claude-dev
ENVIRONMENT=development
EOF

# 3. Run Auto-Claude
python auto-claude/run.py --spec 001

# 4. View metrics
open http://localhost:3301  # SigNoz UI
```

### Example 2: Production with Grafana Cloud

```bash
# 1. Get credentials from Grafana Cloud
# Navigate to: Connections → OpenTelemetry

# 2. Configure Auto-Claude
cat >> .env <<EOF
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net/otlp
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic $(echo -n "user:api_key" | base64)"
OTEL_SERVICE_NAME=auto-claude
ENVIRONMENT=production
OTEL_EXPORT_INTERVAL_SECONDS=120
EOF
```

### Example 3: Multi-Team with Langfuse

```bash
# Team A
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk_team_a_...
LANGFUSE_SECRET_KEY=sk_team_a_...
OTEL_SERVICE_NAME=auto-claude-team-a

# Team B
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk_team_b_...
LANGFUSE_SECRET_KEY=sk_team_b_...
OTEL_SERVICE_NAME=auto-claude-team-b
```

### Example 4: Disable for CI/CD

```bash
# .env.ci
OTEL_ENABLED=false  # Disable telemetry in CI
```

## Migration from Phase 1

If you were using Phase 1 analytics (local JSON files only):

**Before (Phase 1):**
```bash
# Metrics stored in: .auto-claude/specs/001/usage.json
python auto-claude/run.py --spec 001
```

**After (Phase 2):**
```bash
# Metrics stored in: usage.json + exported to OTLP
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
python auto-claude/run.py --spec 001
```

**Key differences:**
- Phase 1: Local file only (`.auto-claude/specs/XXX/usage.json`)
- Phase 2: Local file + OTLP export (opt-out with `OTEL_ENABLED=false`)
- Both phases coexist - local file is always written

## FAQ

### Q: Is OpenTelemetry required?

No. OTel export is **optional and opt-out**. Auto-Claude works perfectly without it. If `OTEL_ENABLED=false`, only local usage files are written.

### Q: What if my collector goes down?

Metrics are dropped gracefully. Auto-Claude continues running normally. Failed exports do not block execution.

### Q: Can I use multiple backends?

Yes! You can export to multiple backends simultaneously:
```bash
LANGFUSE_ENABLED=true
SIGNOZ_ENABLED=true
```

### Q: How do I delete exported metrics?

Contact your observability platform provider. Auto-Claude cannot delete data from external systems.

### Q: What's the cost of running a collector?

- **SigNoz (self-hosted):** ~$20/month (EC2 t3.medium)
- **Langfuse Cloud:** Free tier available, then usage-based
- **Grafana Cloud:** Free tier available, then usage-based
- **Local collector:** Free (runs on your machine)

### Q: Can I export custom metrics?

Not yet. Phase 2 exports token usage, cost, and session metrics. Custom metrics may be added in future phases.

## Support

- **Documentation:** See this guide
- **Issues:** [GitHub Issues](https://github.com/your-org/auto-claude/issues)
- **OpenTelemetry Docs:** [opentelemetry.io](https://opentelemetry.io)
- **Backend Docs:**
  - [Langfuse Docs](https://langfuse.com/docs)
  - [SigNoz Docs](https://signoz.io/docs)
  - [Grafana Docs](https://grafana.com/docs)
