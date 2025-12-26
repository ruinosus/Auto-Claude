# ROI System Design

**Data:** 2025-12-26
**Status:** Aprovado
**Branch:** feat/azure-skills-mcp-themes

## Resumo

Sistema completo de ROI (Return on Investment) para o Auto-Claude, permitindo aos usuários medir o valor gerado por cada demanda/spec em relação ao custo de API.

## Objetivos

1. Calcular ROI por demanda comparando custo real vs. valor estimado
2. Estimar economia de tempo (horas de desenvolvedor)
3. Medir eficiência (taxa de sucesso no QA)
4. Fornecer visibilidade em múltiplos contextos (Analytics, Specs, Menu)

## Métricas de ROI

### Dados Capturados

| Métrica | Fonte | Tipo |
|---------|-------|------|
| Custo real (API) | analytics.db | Automático |
| Tokens consumidos | analytics.db | Automático |
| Linhas alteradas | git diff | Automático |
| Arquivos modificados | git diff | Automático |
| Tempo de execução | timestamps | Automático |
| Tentativas QA | qa_report | Automático |
| Resultado QA | qa_report | Automático |
| Valor de negócio estimado | usuário | Manual (com default) |
| Horas manuais estimadas | calculado | Auto + editável |
| Taxa hora desenvolvedor | settings | Configurável |

### Métricas Derivadas

```
cost_savings = (estimated_hours × hourly_rate) - actual_cost
roi_percentage = (cost_savings / actual_cost) × 100
cost_per_line = actual_cost / lines_changed
efficiency_score = qa_passed ? (1 / qa_attempts) : 0
```

## Modelo de Dados

### Tabelas SQLite

```sql
-- Configurações globais de ROI
CREATE TABLE roi_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    developer_hourly_rate REAL DEFAULT 75.0,
    primary_currency TEXT DEFAULT 'USD',
    secondary_currency TEXT DEFAULT 'BRL',
    exchange_rate REAL DEFAULT 6.20,
    exchange_rate_updated_at TEXT,
    auto_estimate_hours INTEGER DEFAULT 1,
    minutes_per_line REAL DEFAULT 2.5,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Override por projeto
CREATE TABLE project_roi_settings (
    project_id TEXT PRIMARY KEY,
    developer_hourly_rate REAL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Dados ROI por spec
CREATE TABLE spec_roi (
    spec_id TEXT PRIMARY KEY,
    project_id TEXT,
    estimated_business_value REAL DEFAULT 0,
    estimated_hours_manual REAL,
    developer_rate_override REAL,
    actual_cost REAL DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    execution_time_seconds INTEGER DEFAULT 0,
    qa_attempts INTEGER DEFAULT 0,
    qa_passed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY (project_id) REFERENCES project_roi_settings(project_id)
);
```

## Interface do Usuário

### 1. Formulário na Criação de Spec

Seção colapsável "Estimativas de ROI" com campos:
- Valor estimado da demanda (USD)
- Horas se fosse manual (auto-calculado, editável)
- Taxa hora desenvolvedor (herdado, com override)

### 2. Colunas na Lista de Specs

| Coluna | Descrição |
|--------|-----------|
| Custo | Custo real da API |
| ROI | Percentual de retorno |
| Economia | Valor economizado |

Cores: verde (ROI positivo), vermelho (ROI negativo)

### 3. Dashboard ROI no Analytics

Nova aba "ROI" com:

**Cards de Resumo:**
- ROI Total (%)
- Economia Acumulada ($)
- Horas Salvas
- Taxa de Sucesso (%)

**Gráficos:**
- ROI ao Longo do Tempo (linha)
- Custo vs Valor por Spec (barras)
- Eficiência por Tipo (horizontal bars)
- Top 5 Specs por ROI (ranking)

**Tabela Detalhada:**
- Filtros, ordenação, período
- Todas as métricas por spec
- Link para detalhes

### 4. Settings - ROI & Custos

Nova seção com:
- Taxa hora desenvolvedor (global)
- Moeda principal/secundária
- Taxa de câmbio (com atualização)
- Configuração de estimativa automática

### 5. Item no Menu Lateral

Novo item "ROI" abaixo de Analytics, link direto para aba ROI.

## Arquitetura de Arquivos

```
apps/frontend/src/
├── renderer/
│   ├── components/
│   │   ├── analytics/
│   │   │   ├── ROIDashboard.tsx
│   │   │   ├── ROIOverviewCards.tsx
│   │   │   ├── ROIChart.tsx
│   │   │   ├── CostValueChart.tsx
│   │   │   └── ROITable.tsx
│   │   ├── specs/
│   │   │   └── ROIEstimateSection.tsx
│   │   └── settings/
│   │       └── ROISettings.tsx
│   ├── stores/
│   │   └── roi-store.ts
│   ├── hooks/
│   │   └── useROIData.ts
│   └── lib/
│       └── roi-calculator.ts
├── main/
│   ├── ipc-handlers/
│   │   └── roi-handlers.ts
│   └── services/
│       └── roi-service.ts
└── shared/
    └── types/
        └── roi.ts
```

## Tipos TypeScript

```typescript
export interface ROISettings {
  developerHourlyRate: number;
  primaryCurrency: 'USD' | 'BRL' | 'EUR';
  secondaryCurrency: 'USD' | 'BRL' | 'EUR' | null;
  exchangeRate: number;
  exchangeRateUpdatedAt: Date | null;
  autoEstimateHours: boolean;
  minutesPerLine: number;
}

export interface SpecROI {
  specId: string;
  projectId: string;
  estimatedBusinessValue: number;
  estimatedHoursManual: number | null;
  developerRateOverride: number | null;
  actualCost: number;
  totalTokens: number;
  linesAdded: number;
  linesRemoved: number;
  filesChanged: number;
  executionTimeSeconds: number;
  qaAttempts: number;
  qaPassed: boolean;
  createdAt: Date;
  completedAt: Date | null;
}

export interface ROIMetrics {
  effectiveHourlyRate: number;
  estimatedManualCost: number;
  costSavings: number;
  roiPercentage: number;
  costPerLine: number;
  efficiencyScore: number;
  totalROI: number;
  totalSavings: number;
  totalHoursSaved: number;
  successRate: number;
}
```

## Fluxo de Dados

1. **Criação de Spec**: Usuário preenche estimativas (ou usa defaults)
2. **Execução**: Sistema rastreia tokens, custo, tempo automaticamente
3. **Finalização**: Sistema captura git diff, resultado QA
4. **Cálculo**: ROI Calculator processa métricas derivadas
5. **Exibição**: Dados disponíveis em Specs List, Analytics, Menu ROI

## Configuração em Cascata

Prioridade para taxa hora desenvolvedor:
1. Override no Spec (se definido)
2. Override no Projeto (se definido)
3. Configuração Global (default)

## Fixes Incluídos

### Fix: Formatação de Custos

Reduzir casas decimais nos valores de custo:
- Overview cards: 2 casas decimais
- Tooltips: 4 casas decimais
- Tabelas: 2 casas decimais

## Próximos Passos

1. [ ] Criar tipos TypeScript (roi.ts)
2. [ ] Implementar schema SQLite
3. [ ] Criar ROI service (main process)
4. [ ] Criar IPC handlers
5. [ ] Implementar Zustand store
6. [ ] Criar componentes UI
7. [ ] Integrar na lista de Specs
8. [ ] Adicionar aba no Analytics
9. [ ] Criar Settings ROI
10. [ ] Adicionar item no menu
11. [ ] Testes unitários
12. [ ] Testes E2E
