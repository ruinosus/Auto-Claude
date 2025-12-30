# Langfuse Analytics Integration Design

**Data:** 2025-12-30
**Status:** Aprovado
**Autor:** Claude + Jefferson

## Resumo Executivo

Refatorar o sistema de analytics do Auto-Claude para usar **Langfuse como source of truth principal**, removendo a infraestrutura OTEL redundante e criando uma API FastAPI para servir dados ao frontend Electron.

### Decisões Chave

| Decisão | Escolha |
|---------|---------|
| Source of Truth | Langfuse (não mais SQLite) |
| Armazenamento ROI | Langfuse Scores |
| Comunicação Backend→Frontend | FastAPI como proxy |
| Granularidade de Traces | Message-level (spans por fase, generations por msg) |
| Método ROI padrão | Híbrido (linhas + tempo) com override manual |
| OTEL | Removido (só Langfuse) |

---

## 1. Arquitetura Geral

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        NOVA ARQUITETURA                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐         ┌─────────────────────────────────────┐   │
│  │  AGENTS         │         │  LANGFUSE (Self-Hosted :3001)       │   │
│  │  planner.py     │────────▶│  ├── Traces (sessions)              │   │
│  │  coder.py       │  SDK    │  ├── Generations (messages)         │   │
│  │  qa_*.py        │         │  ├── Scores (ROI metrics)           │   │
│  └─────────────────┘         │  └── Metadata (git stats, etc)      │   │
│                              └──────────────┬──────────────────────┘   │
│                                             │                           │
│                                             │ API                       │
│                                             ▼                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ANALYTICS API (FastAPI :8100)                                   │   │
│  │  ├── GET /analytics/overview     → agregados                    │   │
│  │  ├── GET /analytics/sessions     → lista de sessions            │   │
│  │  ├── GET /analytics/sessions/:id → drill-down                   │   │
│  │  ├── GET /analytics/roi          → métricas ROI                 │   │
│  │  ├── POST /analytics/roi/:id     → input manual                 │   │
│  │  └── GET /analytics/costs        → breakdown de custos          │   │
│  └──────────────────────────────────────────┬──────────────────────┘   │
│                                             │                           │
│                                             │ HTTP                      │
│                                             ▼                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  FRONTEND (Electron + React)                                     │   │
│  │  ├── AnalyticsDashboard   → overview cards, charts              │   │
│  │  ├── SessionsTable        → lista com drill-down                │   │
│  │  ├── ROIDashboard         → métricas, comparações               │   │
│  │  └── CostBreakdown        → por modelo, por feature             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

1. Agents executam → Langfuse SDK captura traces automaticamente
2. ROI calculado no final da session → salvo como Langfuse Scores
3. Frontend faz request ao FastAPI → FastAPI consulta Langfuse API
4. FastAPI cacheia e transforma dados → retorna JSON otimizado

### O Que Será Removido

- `otel_exporter.py`, `otel_collector.py` (OTEL)
- Polling direto do SQLite no frontend
- `analytics.db` para traces (mantém só para config/settings locais)

---

## 2. Backend: Instrumentação Langfuse

### 2.1 Estrutura de Traces

```
Trace: "spec-{id}-{name}"
│
├── metadata:
│   ├── spec_id: "001"
│   ├── project_dir: "/path/to/project"
│   ├── complexity: "standard"
│   └── created_at: "2025-12-30T10:00:00Z"
│
├── Span: "planner"
│   ├── input: system_prompt + user_task
│   ├── output: implementation_plan.json
│   ├── Generations:
│   │   ├── gen-1: {model, tokens, cost, latency}
│   │   ├── gen-2: {...}
│   │   └── ...
│   └── metadata: {subtasks_count, files_identified}
│
├── Span: "coder"
│   ├── Span: "subtask-1"
│   │   ├── Generations: [gen-1, gen-2, ...]
│   │   └── metadata: {files_changed, status}
│   ├── Span: "subtask-2"
│   │   └── ...
│   └── metadata: {total_subtasks, completed, failed}
│
├── Span: "qa-reviewer"
│   ├── Generations: [...]
│   └── output: qa_report.md
│
├── Span: "qa-fixer" (se necessário)
│   ├── Generations: [...]
│   └── metadata: {attempt_number, issues_fixed}
│
└── Scores (calculados no final):
    ├── roi_percentage: 245.5
    ├── business_value_usd: 150.00
    ├── actual_cost_usd: 43.50
    ├── dev_hours_saved: 2.5
    ├── lines_added: 342
    ├── lines_removed: 45
    └── qa_passed: true
```

### 2.2 Código de Instrumentação

```python
# agents/session.py - Nova versão

from langfuse.decorators import observe, langfuse_context

@observe(name="agent-session")
async def run_agent_session(
    spec_dir: str,
    agent_type: str,  # planner, coder, qa_reviewer, qa_fixer
    ...
):
    # Adiciona metadata ao span atual
    langfuse_context.update_current_observation(
        metadata={
            "spec_id": spec_id,
            "agent_type": agent_type,
            "model": model,
        }
    )

    # Loop de mensagens - cada uma vira uma Generation
    async for msg in client.receive_response():
        # Langfuse SDK captura automaticamente via @observe

        # Ao final, registrar scores de ROI
        if is_final_message(msg):
            roi_data = calculate_roi(spec_dir)
            langfuse_context.score_current_trace(
                name="roi_percentage",
                value=roi_data.roi_percentage
            )
            langfuse_context.score_current_trace(
                name="business_value_usd",
                value=roi_data.business_value
            )
```

### 2.3 Arquivos a Modificar

| Arquivo | Modificação |
|---------|-------------|
| `agents/session.py` | Adicionar `@observe`, metadata, scores |
| `agents/planner.py` | Wrap com `@observe("planner")` |
| `agents/coder.py` | Wrap com `@observe("coder")` + spans por subtask |
| `agents/qa_reviewer.py` | Wrap com `@observe("qa-reviewer")` |
| `agents/qa_fixer.py` | Wrap com `@observe("qa-fixer")` |
| `analytics/roi_tracker.py` | Refatorar para salvar scores no Langfuse |
| `analytics/langfuse_integration.py` | Adicionar helpers para scores e metadata |

---

## 3. FastAPI Analytics Service

### 3.1 Estrutura do Serviço

```
apps/backend/
├── api/                          # NOVO - FastAPI service
│   ├── __init__.py
│   ├── main.py                   # FastAPI app + startup
│   ├── routers/
│   │   ├── analytics.py          # GET /analytics/*
│   │   ├── sessions.py           # GET /sessions/*
│   │   ├── roi.py                # GET/POST /roi/*
│   │   └── health.py             # GET /health
│   ├── services/
│   │   ├── langfuse_client.py    # Wrapper da API Langfuse
│   │   ├── cache.py              # In-memory cache com TTL
│   │   └── roi_calculator.py     # Cálculos de ROI
│   ├── models/
│   │   ├── analytics.py          # Pydantic models
│   │   ├── sessions.py
│   │   └── roi.py
│   └── config.py                 # Settings via env vars
```

### 3.2 Endpoints da API

```
# Overview (dashboard principal)
GET /api/analytics/overview
Response: {
    "total_cost_usd": 156.78,
    "total_tokens": 1_250_000,
    "total_sessions": 45,
    "avg_cost_per_session": 3.48,
    "cost_trend_7d": [...],
    "token_trend_7d": [...],
    "model_distribution": {...},
    "updated_at": "2025-12-30T..."
}

# Lista de sessions (com paginação)
GET /api/analytics/sessions?page=1&limit=20&spec_id=001
Response: {
    "items": [...],
    "total": 45,
    "page": 1,
    "pages": 3
}

# Drill-down de uma session
GET /api/analytics/sessions/{trace_id}
Response: {
    "trace_id": "abc123",
    "spec_id": "001",
    "spans": [...],
    "scores": {...}
}

# ROI Overview
GET /api/analytics/roi
Response: {
    "total_roi_percentage": 312.5,
    "total_business_value": 4500.00,
    "total_actual_cost": 1080.00,
    "specs": [...]
}

# Atualizar ROI manualmente
POST /api/analytics/roi/{spec_id}
Body: {
    "manual_business_value": 200.00,
    "manual_dev_hours": 5.0,
    "notes": "Cliente confirmou valor"
}

# Settings de ROI
GET /api/analytics/roi/settings
PUT /api/analytics/roi/settings
```

### 3.3 Langfuse Client Service

```python
# api/services/langfuse_client.py

class LangfuseAnalyticsClient:
    def __init__(self):
        self.client = Langfuse()
        self._cache = TTLCache(default_ttl=30)

    async def get_traces(self, limit, offset, filter_spec_id) -> list:
        """Busca traces do Langfuse com cache."""
        ...

    async def get_trace_detail(self, trace_id: str) -> dict:
        """Busca detalhes de um trace específico."""
        ...

    async def get_aggregated_metrics(self, days: int = 7) -> dict:
        """Calcula métricas agregadas."""
        ...

    async def set_score(self, trace_id, name, value):
        """Adiciona/atualiza score em um trace."""
        ...
```

### 3.4 Cache Strategy

| Tipo de Dado | TTL | Razão |
|--------------|-----|-------|
| Overview | 30s | Dados agregados, atualização moderada |
| Sessions List | 15s | Lista pode mudar com novas sessions |
| Session Detail | 60s | Detalhes mudam pouco após criação |
| ROI | 60s | Cálculos estáveis |

---

## 4. Frontend: Componentes e Hooks

### 4.1 Nova Estrutura de Arquivos

```
apps/frontend/src/renderer/
├── api/
│   ├── analytics-api.ts          # Fetch wrapper
│   └── types.ts                  # TypeScript types
│
├── hooks/
│   ├── useAnalyticsOverview.ts   # NOVO
│   ├── useSessions.ts            # NOVO
│   ├── useSessionDetail.ts       # NOVO
│   └── useROI.ts                 # REFATORAR
│
├── stores/
│   └── analytics-store.ts        # SIMPLIFICAR (só UI state)
│
└── components/analytics/
    ├── Analytics.tsx              # Container principal
    ├── OverviewCards.tsx          # REFATORAR
    ├── CostChart.tsx              # REFATORAR
    ├── sessions/                  # NOVO - drill-down
    │   ├── SessionsTable.tsx
    │   ├── SessionDetail.tsx
    │   └── GenerationCard.tsx
    └── roi/
        ├── ROIDashboard.tsx       # REFATORAR
        └── ROIEditModal.tsx       # NOVO
```

### 4.2 API Client

```typescript
// renderer/api/analytics-api.ts

const API_BASE = 'http://localhost:8100/api';

class AnalyticsAPI {
  async getOverview(): Promise<AnalyticsOverview>;
  async getSessions(params: SessionsParams): Promise<PaginatedSessions>;
  async getSessionDetail(traceId: string): Promise<SessionDetail>;
  async getROI(): Promise<ROIOverview>;
  async updateROI(specId: string, data: ROIUpdate): Promise<ROISpec>;
  async getROISettings(): Promise<ROISettings>;
  async updateROISettings(settings: ROISettings): Promise<ROISettings>;
}

export const analyticsApi = new AnalyticsAPI();
```

### 4.3 Hooks com React Query

```typescript
// Exemplo: useAnalyticsOverview.ts

export function useAnalyticsOverview() {
  return useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: () => analyticsApi.getOverview(),
    refetchInterval: 30_000,  // 30s auto-refresh
    staleTime: 15_000,
  });
}
```

### 4.4 Remoções

| Arquivo | Ação |
|---------|------|
| `hooks/useAnalyticsData.ts` | Remover (polling SQLite) |
| `main/services/analytics-service.ts` | Remover |
| `stores/analytics-store.ts` | Simplificar |
| IPC channels `analytics:*` | Remover |

---

## 5. ROI Calculation

### 5.1 Fórmulas

```python
# Método Híbrido (padrão)

# 1. Estimativa por linhas (40% peso)
lines_value = (lines_added * $0.50) + (lines_removed * $0.30)
lines_value *= complexity_multiplier  # simple: 0.7, standard: 1.0, complex: 1.5

# 2. Estimativa por tempo (60% peso)
estimated_hours = total_lines / lines_per_hour  # ~15 linhas/hora
time_value = estimated_hours * developer_hourly_rate  # default: $75/h

# 3. Combina
raw_value = (lines_value * 0.4) + (time_value * 0.6)

# 4. Ajuste por qualidade
quality_multiplier = 1.0 - ((qa_attempts - 1) * 0.05)  # min 0.7
if not qa_passed: quality_multiplier = 0.5

business_value = raw_value * quality_multiplier

# 5. ROI final
roi_percentage = ((business_value - actual_cost) / actual_cost) * 100
dev_hours_saved = business_value / developer_hourly_rate
```

### 5.2 Scores no Langfuse

| Score | Tipo | Descrição |
|-------|------|-----------|
| `roi_percentage` | Numeric | ROI calculado |
| `business_value_usd` | Numeric | Valor estimado |
| `actual_cost_usd` | Numeric | Custo real (tokens) |
| `dev_hours_saved` | Numeric | Horas economizadas |
| `confidence_score` | Numeric | 0-1, confiança na estimativa |
| `quality_multiplier` | Numeric | Ajuste por QA |
| `lines_added` | Numeric | Linhas adicionadas |
| `lines_removed` | Numeric | Linhas removidas |
| `qa_attempts` | Numeric | Tentativas de QA |
| `qa_passed` | Numeric | 1.0 ou 0.0 |

### 5.3 Override Manual

Usuário pode sobrescrever via UI:
- `manual_business_value`: Valor em USD
- `manual_dev_hours`: Horas estimadas
- Quando fornecido, `estimation_method` = "manual" e `confidence_score` = 1.0

---

## 6. Configuração de Ambiente

### 6.1 Variáveis de Ambiente

```bash
# .env additions

# Langfuse (já existentes)
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=http://localhost:3001

# Analytics API (novo)
ANALYTICS_API_PORT=8100
ANALYTICS_API_HOST=127.0.0.1

# ROI Settings (novos)
ROI_DEVELOPER_HOURLY_RATE=75.00
ROI_RATE_PER_LINE_ADDED=0.50
ROI_RATE_PER_LINE_REMOVED=0.30

# Removidos
# OTEL_ENABLED (removido)
# OTEL_EXPORTER_OTLP_ENDPOINT (removido)
```

### 6.2 Dependências Novas

```txt
# requirements.txt additions
fastapi>=0.109.0
uvicorn>=0.27.0
httpx>=0.26.0  # async HTTP client
```

```json
// package.json additions (frontend)
{
  "@tanstack/react-query": "^5.0.0"
}
```

---

## 7. Plano de Implementação

### Fase 1: Backend Langfuse Instrumentation
1. Adicionar `@observe` decorators aos agents
2. Capturar metadata (spec_id, complexity, etc)
3. Implementar ROI calculation no final da session
4. Salvar scores no Langfuse
5. Testar traces aparecem corretamente

### Fase 2: FastAPI Analytics Service
1. Criar estrutura `apps/backend/api/`
2. Implementar Langfuse client wrapper
3. Implementar cache layer
4. Criar endpoints REST
5. Testar com curl/Postman

### Fase 3: Frontend Refactor
1. Adicionar React Query
2. Criar API client
3. Criar novos hooks
4. Refatorar componentes existentes
5. Criar SessionsTable e drill-down
6. Remover código legado (SQLite polling)

### Fase 4: Cleanup
1. Remover arquivos OTEL
2. Remover IPC channels antigos
3. Atualizar documentação
4. Atualizar i18n

---

## 8. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Langfuse API rate limits | Dados atrasados | Cache agressivo no FastAPI |
| Langfuse down | Frontend sem dados | Retry com backoff + mensagem de erro clara |
| Performance do frontend | UX ruim | React Query com staleTime + skeleton loaders |
| Perda de dados históricos | Sem histórico | Migrar dados do SQLite antes de remover |

---

## 9. Métricas de Sucesso

- [ ] Traces aparecem no Langfuse para todas as sessions
- [ ] ROI calculado automaticamente com >80% confidence
- [ ] Frontend carrega dados em <2s
- [ ] Drill-down funciona até nível de generation
- [ ] Override manual de ROI funciona
- [ ] Zero erros de CORS/conexão

---

## Aprovações

- [x] Arquitetura geral
- [x] Backend instrumentation
- [x] FastAPI service
- [x] Frontend components
- [x] ROI calculation

**Próximo passo:** Criar worktree e iniciar implementação da Fase 1.
