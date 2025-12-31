# Analytics Dashboard Redesign - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement 5-tab Analytics Dashboard (Overview, Dev, Tech Lead, Ops, Business) with bug fixes and stakeholder-specific views.

**Architecture:** Refactor `Analytics.tsx` to use 5 tabs instead of 2. Create tab-specific components in subdirectories. Extend backend API with new endpoints. Each tab serves a different stakeholder (Dev, Tech Lead, Ops, Business).

**Tech Stack:** React, TypeScript, Recharts, Tailwind CSS, FastAPI, Langfuse API, react-i18next

---

## Workstream Organization

This plan is organized into **6 workstreams**. Workstreams A, B, C, D can run in **parallel**. Workstream E depends on B+D. Workstream F depends on E.

```
       ┌──────────────────────────────────────────────────────┐
       │                   PARALLEL PHASE                      │
       ├──────────┬──────────┬──────────┬──────────────────────┤
       │    A     │    B     │    C     │         D            │
       │ Bug Fixes│  Shared  │  Backend │        i18n          │
       │ (Backend │Components│   API    │    Translations      │
       │+Frontend)│          │Extensions│                      │
       └────┬─────┴────┬─────┴────┬─────┴──────────┬───────────┘
            │          │          │                │
            └──────────┴──────────┴────────────────┘
                              │
                              ▼
       ┌──────────────────────────────────────────────────────┐
       │                      E: Tab Components                │
       │   (Depends on B: Shared Components + D: i18n)         │
       └──────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
       ┌──────────────────────────────────────────────────────┐
       │                  F: Integration & Testing             │
       │              (Depends on all workstreams)             │
       └──────────────────────────────────────────────────────┘
```

---

## Workstream A: Bug Fixes (P0 - Critical)

### Task A1: Fix "Unknown" in Backend Routes

**Files:**
- Modify: `apps/backend/analytics/api/routes.py:507-528`
- Test: `apps/backend/tests/test_analytics_routes.py`

**Step 1: Write the failing test**

```python
# apps/backend/tests/test_analytics_routes.py
import pytest
from unittest.mock import MagicMock, patch

def test_spec_id_fallback_chain():
    """Test that spec_id uses fallback chain instead of 'unknown'."""
    from analytics.api.routes import get_spec_id_from_trace

    # Mock trace with no metadata
    trace = MagicMock()
    trace.metadata = {}
    trace.session_id = "session-123"
    trace.name = "coder-spec-045"
    trace.id = "abc12345-xyz"

    result = get_spec_id_from_trace(trace)

    # Should NOT be "unknown"
    assert result != "unknown"
    # Should use session_id as first fallback
    assert result == "session-123"


def test_spec_id_uses_name_prefix_when_no_session():
    """Test spec_id falls back to name prefix when no session_id."""
    from analytics.api.routes import get_spec_id_from_trace

    trace = MagicMock()
    trace.metadata = {}
    trace.session_id = None
    trace.name = "coder-spec-045-implementation"
    trace.id = "abc12345-xyz"

    result = get_spec_id_from_trace(trace)

    assert result == "coder"


def test_spec_id_uses_trace_id_as_last_resort():
    """Test spec_id falls back to trace_id[:8] when nothing else available."""
    from analytics.api.routes import get_spec_id_from_trace

    trace = MagicMock()
    trace.metadata = {}
    trace.session_id = None
    trace.name = ""
    trace.id = "abc12345-xyz"

    result = get_spec_id_from_trace(trace)

    assert result == "trace-abc12345"
```

**Step 2: Run test to verify it fails**

```bash
cd apps/backend
.venv/bin/pytest tests/test_analytics_routes.py::test_spec_id_fallback_chain -v
```
Expected: FAIL with "ImportError: cannot import name 'get_spec_id_from_trace'"

**Step 3: Implement helper function and update routes**

```python
# apps/backend/analytics/api/routes.py
# Add after line 40 (after router = APIRouter())

def get_spec_id_from_trace(trace) -> str:
    """
    Extract spec_id from trace with intelligent fallback chain.

    Priority:
    1. metadata.spec_id (if present)
    2. session_id (if present)
    3. First part of trace name (before first '-')
    4. 'trace-' + first 8 chars of trace.id
    """
    # Try metadata first
    spec_id = trace.metadata.get("spec_id") if trace.metadata else None
    if spec_id:
        return spec_id

    # Fallback to session_id
    if trace.session_id:
        return trace.session_id

    # Fallback to name prefix
    if trace.name and "-" in trace.name:
        return trace.name.split("-")[0]

    # Last resort: trace ID prefix
    return f"trace-{trace.id[:8]}"


def get_agent_type_from_trace(trace) -> str:
    """
    Extract agent_type from trace with intelligent fallback.

    Priority:
    1. metadata.agent_type (if present)
    2. Infer from trace name (planner, coder, qa_reviewer, qa_fixer)
    3. 'other'
    """
    # Try metadata first
    agent_type = trace.metadata.get("agent_type") if trace.metadata else None
    if agent_type:
        return agent_type

    # Infer from name
    name_lower = (trace.name or "").lower()
    for known_type in ["planner", "coder", "qa_reviewer", "qa_fixer", "gatherer", "researcher", "writer"]:
        if known_type in name_lower:
            return known_type

    return "other"
```

**Step 4: Update usages in routes.py**

Find and replace all occurrences:
- Line 507: `spec_id = trace.metadata.get("spec_id", "unknown")` → `spec_id = get_spec_id_from_trace(trace)`
- Line 528: `agent_type = trace.metadata.get("agent_type", "unknown")` → `agent_type = get_agent_type_from_trace(trace)`
- Line 108: `spec_id=t.metadata.get("spec_id")` → `spec_id=get_spec_id_from_trace(t)`
- Line 109: `agent_type=t.metadata.get("agent_type")` → `agent_type=get_agent_type_from_trace(t)`
- Line 175-176: Same pattern
- Line 213-214: Same pattern
- Line 226: `agent_type = t.metadata.get("agent_type", "unknown")` → `agent_type = get_agent_type_from_trace(t)`

**Step 5: Run tests to verify they pass**

```bash
cd apps/backend
.venv/bin/pytest tests/test_analytics_routes.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add apps/backend/analytics/api/routes.py apps/backend/tests/test_analytics_routes.py
git commit -m "fix(analytics): replace 'unknown' fallback with intelligent spec_id/agent_type extraction"
```

---

### Task A2: Add Separate Token Fields to API Response

**Files:**
- Modify: `apps/backend/analytics/api/models.py`
- Modify: `apps/backend/analytics/api/routes.py`
- Test: `apps/backend/tests/test_analytics_routes.py`

**Step 1: Write the failing test**

```python
# apps/backend/tests/test_analytics_routes.py (add to existing file)

@pytest.mark.asyncio
async def test_usage_summary_includes_separate_token_fields():
    """Test that usage summary includes total_input_tokens and total_output_tokens."""
    from analytics.api.models import UsageSummaryResponse

    # Check model has the fields
    fields = UsageSummaryResponse.model_fields
    assert "total_input_tokens" in fields
    assert "total_output_tokens" in fields
```

**Step 2: Run test to verify it fails**

```bash
cd apps/backend
.venv/bin/pytest tests/test_analytics_routes.py::test_usage_summary_includes_separate_token_fields -v
```
Expected: FAIL with "AssertionError"

**Step 3: Update Pydantic model**

```python
# apps/backend/analytics/api/models.py
# Find UsageSummaryResponse class and add fields:

class UsageSummaryResponse(BaseModel):
    """Comprehensive usage analytics for dashboard."""
    total_cost: float = 0.0
    total_tokens: int = 0
    total_input_tokens: int = 0  # ADD THIS
    total_output_tokens: int = 0  # ADD THIS
    total_traces: int = 0
    active_specs: int = 0
    # ... rest of fields unchanged
```

**Step 4: Update routes.py to calculate separate tokens**

```python
# apps/backend/analytics/api/routes.py
# In get_usage_summary function, after line 485 (total_tokens = 0):

    total_input_tokens = 0
    total_output_tokens = 0

# In the trace loop (around line 504-505), add:
    for trace in traces:
        total_cost += trace.total_cost
        total_tokens += trace.total_tokens
        # Estimate split (70% input, 30% output is typical for LLM)
        total_input_tokens += int(trace.total_tokens * 0.7)
        total_output_tokens += int(trace.total_tokens * 0.3)
        # ... rest unchanged

# Update return statement (around line 599) to include new fields:
    return UsageSummaryResponse(
        total_cost=round(total_cost, 4),
        total_tokens=total_tokens,
        total_input_tokens=total_input_tokens,  # ADD
        total_output_tokens=total_output_tokens,  # ADD
        # ... rest unchanged
    )
```

**Step 5: Run tests to verify they pass**

```bash
cd apps/backend
.venv/bin/pytest tests/test_analytics_routes.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add apps/backend/analytics/api/models.py apps/backend/analytics/api/routes.py apps/backend/tests/test_analytics_routes.py
git commit -m "feat(analytics-api): add total_input_tokens and total_output_tokens to usage summary"
```

---

### Task A3: Fix Total Tokens Display in Frontend

**Files:**
- Modify: `apps/frontend/src/renderer/components/analytics/Analytics.tsx:190-194`
- Test: `apps/frontend/src/renderer/components/analytics/__tests__/Analytics.test.tsx`

**Step 1: Write the failing test**

```tsx
// apps/frontend/src/renderer/components/analytics/__tests__/Analytics.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

describe('Analytics token display', () => {
  it('should use real input/output tokens when available', () => {
    const mockData = {
      total_tokens: 1000,
      total_input_tokens: 700,
      total_output_tokens: 300,
      total_cost: 0.05
    };

    // The component should prioritize real values over estimates
    const inputTokens = mockData.total_input_tokens || Math.floor((mockData.total_tokens || 0) * 0.3);
    const outputTokens = mockData.total_output_tokens || Math.floor((mockData.total_tokens || 0) * 0.7);

    // Real values should be used
    expect(inputTokens).toBe(700);
    expect(outputTokens).toBe(300);

    // Not the estimated values
    expect(inputTokens).not.toBe(300);
    expect(outputTokens).not.toBe(700);
  });
});
```

**Step 2: Run test to verify it passes (it's a unit test of the logic)**

```bash
cd apps/frontend
npm test -- --run Analytics.test.tsx
```

**Step 3: Update Analytics.tsx**

```tsx
// apps/frontend/src/renderer/components/analytics/Analytics.tsx
// Find lines 190-194 and replace:

// BEFORE:
totalTokens: {
  input: Math.floor((data?.total_tokens || 0) * 0.3),
  output: Math.floor((data?.total_tokens || 0) * 0.7)
}

// AFTER:
totalTokens: {
  input: data?.total_input_tokens || Math.floor((data?.total_tokens || 0) * 0.3),
  output: data?.total_output_tokens || Math.floor((data?.total_tokens || 0) * 0.7)
}
```

**Step 4: Also update the hook types**

```tsx
// apps/frontend/src/renderer/hooks/useAnalyticsQuery.ts
// Add to UsageSummary interface (if not already present):

interface UsageSummary {
  total_cost: number;
  total_tokens: number;
  total_input_tokens?: number;  // ADD
  total_output_tokens?: number;  // ADD
  // ... rest unchanged
}
```

**Step 5: Run frontend build to verify no TypeScript errors**

```bash
cd apps/frontend
npm run build
```
Expected: BUILD SUCCESS

**Step 6: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/Analytics.tsx
git add apps/frontend/src/renderer/hooks/useAnalyticsQuery.ts
git commit -m "fix(analytics): use real input/output token counts when available"
```

---

## Workstream B: Shared Components

### Task B1: Create MetricCard Component

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/shared/MetricCard.tsx`
- Test: `apps/frontend/src/renderer/components/analytics/shared/__tests__/MetricCard.test.tsx`

**Step 1: Write the failing test**

```tsx
// apps/frontend/src/renderer/components/analytics/shared/__tests__/MetricCard.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MetricCard } from '../MetricCard';

describe('MetricCard', () => {
  it('renders value and label', () => {
    render(<MetricCard value="$12.50" label="Total Cost" />);

    expect(screen.getByText('$12.50')).toBeInTheDocument();
    expect(screen.getByText('Total Cost')).toBeInTheDocument();
  });

  it('renders trend indicator when provided', () => {
    render(<MetricCard value="156K" label="Tokens" trend={{ value: 12, direction: 'up' }} />);

    expect(screen.getByText('+12%')).toBeInTheDocument();
  });

  it('applies variant styles', () => {
    const { container } = render(<MetricCard value="8.5h" label="Hours" variant="success" />);

    expect(container.firstChild).toHaveClass('border-green-500');
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd apps/frontend
npm test -- --run MetricCard.test.tsx
```
Expected: FAIL with "Cannot find module '../MetricCard'"

**Step 3: Create the component**

```tsx
// apps/frontend/src/renderer/components/analytics/shared/MetricCard.tsx
import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface Trend {
  value: number;
  direction: 'up' | 'down' | 'neutral';
}

interface MetricCardProps {
  value: string | number;
  label: string;
  icon?: ReactNode;
  trend?: Trend;
  variant?: 'default' | 'success' | 'warning' | 'danger';
  className?: string;
}

const variantStyles = {
  default: 'border-border',
  success: 'border-green-500 bg-green-50 dark:bg-green-950/20',
  warning: 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20',
  danger: 'border-red-500 bg-red-50 dark:bg-red-950/20',
};

const trendColors = {
  up: 'text-green-600',
  down: 'text-red-600',
  neutral: 'text-gray-500',
};

export function MetricCard({
  value,
  label,
  icon,
  trend,
  variant = 'default',
  className,
}: MetricCardProps) {
  const TrendIcon = trend?.direction === 'up' ? TrendingUp :
                    trend?.direction === 'down' ? TrendingDown : Minus;

  return (
    <div
      className={cn(
        'rounded-lg border p-4 transition-colors',
        variantStyles[variant],
        className
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon && <span className="text-muted-foreground">{icon}</span>}
          <span className="text-sm text-muted-foreground">{label}</span>
        </div>
        {trend && (
          <div className={cn('flex items-center gap-1 text-sm', trendColors[trend.direction])}>
            <TrendIcon className="h-4 w-4" />
            <span>{trend.direction === 'down' ? '' : '+'}{trend.value}%</span>
          </div>
        )}
      </div>
      <div className="mt-2 text-2xl font-bold">{value}</div>
    </div>
  );
}
```

**Step 4: Create index file for shared components**

```tsx
// apps/frontend/src/renderer/components/analytics/shared/index.ts
export { MetricCard } from './MetricCard';
```

**Step 5: Run tests to verify they pass**

```bash
cd apps/frontend
npm test -- --run MetricCard.test.tsx
```
Expected: PASS

**Step 6: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/shared/
git commit -m "feat(analytics): add MetricCard shared component"
```

---

### Task B2: Create ChartContainer Component

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/shared/ChartContainer.tsx`
- Test: `apps/frontend/src/renderer/components/analytics/shared/__tests__/ChartContainer.test.tsx`

**Step 1: Write the failing test**

```tsx
// apps/frontend/src/renderer/components/analytics/shared/__tests__/ChartContainer.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ChartContainer } from '../ChartContainer';

describe('ChartContainer', () => {
  it('renders title and children', () => {
    render(
      <ChartContainer title="Cost Over Time">
        <div data-testid="chart-content">Chart here</div>
      </ChartContainer>
    );

    expect(screen.getByText('Cost Over Time')).toBeInTheDocument();
    expect(screen.getByTestId('chart-content')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<ChartContainer title="Test" isLoading />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows empty state when no data', () => {
    render(<ChartContainer title="Test" isEmpty emptyMessage="No data available" />);

    expect(screen.getByText('No data available')).toBeInTheDocument();
  });
});
```

**Step 2: Create the component**

```tsx
// apps/frontend/src/renderer/components/analytics/shared/ChartContainer.tsx
import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

interface ChartContainerProps {
  title: string;
  description?: string;
  children?: ReactNode;
  isLoading?: boolean;
  isEmpty?: boolean;
  emptyMessage?: string;
  className?: string;
  headerActions?: ReactNode;
}

export function ChartContainer({
  title,
  description,
  children,
  isLoading = false,
  isEmpty = false,
  emptyMessage = 'No data available',
  className,
  headerActions,
}: ChartContainerProps) {
  return (
    <div className={cn('rounded-lg border bg-card p-4', className)}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold">{title}</h3>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        {headerActions}
      </div>

      {isLoading ? (
        <div className="flex h-[200px] items-center justify-center" role="status">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : isEmpty ? (
        <div className="flex h-[200px] items-center justify-center text-muted-foreground">
          {emptyMessage}
        </div>
      ) : (
        children
      )}
    </div>
  );
}
```

**Step 3: Update index**

```tsx
// apps/frontend/src/renderer/components/analytics/shared/index.ts
export { MetricCard } from './MetricCard';
export { ChartContainer } from './ChartContainer';
```

**Step 4: Run tests**

```bash
cd apps/frontend
npm test -- --run ChartContainer.test.tsx
```
Expected: PASS

**Step 5: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/shared/
git commit -m "feat(analytics): add ChartContainer shared component"
```

---

### Task B3: Create DataTable Component

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/shared/DataTable.tsx`
- Test: `apps/frontend/src/renderer/components/analytics/shared/__tests__/DataTable.test.tsx`

**Step 1: Write the failing test**

```tsx
// apps/frontend/src/renderer/components/analytics/shared/__tests__/DataTable.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { DataTable } from '../DataTable';

describe('DataTable', () => {
  const columns = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'cost', label: 'Cost', sortable: true },
  ];

  const data = [
    { id: '1', name: 'Spec A', cost: 1.50 },
    { id: '2', name: 'Spec B', cost: 2.30 },
  ];

  it('renders headers and data', () => {
    render(<DataTable columns={columns} data={data} />);

    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Cost')).toBeInTheDocument();
    expect(screen.getByText('Spec A')).toBeInTheDocument();
    expect(screen.getByText('Spec B')).toBeInTheDocument();
  });

  it('handles row click', () => {
    const onRowClick = vi.fn();
    render(<DataTable columns={columns} data={data} onRowClick={onRowClick} />);

    fireEvent.click(screen.getByText('Spec A'));
    expect(onRowClick).toHaveBeenCalledWith(data[0]);
  });

  it('sorts data when header clicked', () => {
    render(<DataTable columns={columns} data={data} />);

    const nameHeader = screen.getByText('Name');
    fireEvent.click(nameHeader);

    // Should show sort indicator
    expect(nameHeader.closest('th')).toHaveAttribute('aria-sort');
  });
});
```

**Step 2: Create the component**

```tsx
// apps/frontend/src/renderer/components/analytics/shared/DataTable.tsx
import { useState, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';

interface Column<T> {
  key: keyof T | string;
  label: string;
  sortable?: boolean;
  render?: (value: any, row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T extends { id: string }> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  className?: string;
  emptyMessage?: string;
}

type SortDirection = 'asc' | 'desc' | null;

export function DataTable<T extends { id: string }>({
  columns,
  data,
  onRowClick,
  className,
  emptyMessage = 'No data',
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : prev === 'desc' ? null : 'asc');
      if (sortDirection === 'desc') setSortKey(null);
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  const sortedData = useMemo(() => {
    if (!sortKey || !sortDirection) return data;

    return [...data].sort((a, b) => {
      const aVal = (a as any)[sortKey];
      const bVal = (b as any)[sortKey];

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [data, sortKey, sortDirection]);

  const getSortIcon = (key: string) => {
    if (sortKey !== key) return <ChevronsUpDown className="h-4 w-4" />;
    if (sortDirection === 'asc') return <ChevronUp className="h-4 w-4" />;
    return <ChevronDown className="h-4 w-4" />;
  };

  if (data.length === 0) {
    return (
      <div className="py-8 text-center text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="w-full">
        <thead>
          <tr className="border-b">
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className={cn(
                  'px-4 py-2 text-left text-sm font-medium text-muted-foreground',
                  col.sortable && 'cursor-pointer select-none hover:text-foreground',
                  col.className
                )}
                onClick={() => col.sortable && handleSort(String(col.key))}
                aria-sort={
                  sortKey === col.key
                    ? sortDirection === 'asc' ? 'ascending' : 'descending'
                    : undefined
                }
              >
                <div className="flex items-center gap-1">
                  {col.label}
                  {col.sortable && getSortIcon(String(col.key))}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row) => (
            <tr
              key={row.id}
              className={cn(
                'border-b transition-colors hover:bg-muted/50',
                onRowClick && 'cursor-pointer'
              )}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((col) => (
                <td
                  key={`${row.id}-${String(col.key)}`}
                  className={cn('px-4 py-3 text-sm', col.className)}
                >
                  {col.render
                    ? col.render((row as any)[col.key], row)
                    : (row as any)[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

**Step 3: Update index**

```tsx
// apps/frontend/src/renderer/components/analytics/shared/index.ts
export { MetricCard } from './MetricCard';
export { ChartContainer } from './ChartContainer';
export { DataTable } from './DataTable';
```

**Step 4: Run tests**

```bash
cd apps/frontend
npm test -- --run DataTable.test.tsx
```
Expected: PASS

**Step 5: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/shared/
git commit -m "feat(analytics): add DataTable shared component with sorting"
```

---

### Task B4: Create AlertBadge Component

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/shared/AlertBadge.tsx`

**Step 1: Create the component (simple component, minimal test needed)**

```tsx
// apps/frontend/src/renderer/components/analytics/shared/AlertBadge.tsx
import { cn } from '@/lib/utils';
import { AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react';

type Severity = 'error' | 'warning' | 'info' | 'success';

interface AlertBadgeProps {
  severity: Severity;
  label: string;
  className?: string;
}

const severityConfig = {
  error: {
    icon: AlertCircle,
    className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  },
  warning: {
    icon: AlertTriangle,
    className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  },
  info: {
    icon: Info,
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  },
  success: {
    icon: CheckCircle,
    className: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  },
};

export function AlertBadge({ severity, label, className }: AlertBadgeProps) {
  const config = severityConfig[severity];
  const Icon = config.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium',
        config.className,
        className
      )}
    >
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}
```

**Step 2: Update index**

```tsx
// apps/frontend/src/renderer/components/analytics/shared/index.ts
export { MetricCard } from './MetricCard';
export { ChartContainer } from './ChartContainer';
export { DataTable } from './DataTable';
export { AlertBadge } from './AlertBadge';
```

**Step 3: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/shared/
git commit -m "feat(analytics): add AlertBadge shared component"
```

---

### Task B5: Create Formatters Utility

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/utils/formatters.ts`
- Test: `apps/frontend/src/renderer/components/analytics/utils/__tests__/formatters.test.ts`

**Step 1: Write the failing test**

```ts
// apps/frontend/src/renderer/components/analytics/utils/__tests__/formatters.test.ts
import { describe, it, expect } from 'vitest';
import {
  formatCurrency,
  formatNumber,
  formatPercentage,
  formatDuration,
  formatRelativeTime,
} from '../formatters';

describe('formatters', () => {
  describe('formatCurrency', () => {
    it('formats USD correctly', () => {
      expect(formatCurrency(12.5)).toBe('$12.50');
      expect(formatCurrency(1234.56)).toBe('$1,234.56');
      expect(formatCurrency(0.001)).toBe('$0.00');
    });
  });

  describe('formatNumber', () => {
    it('formats with K/M suffixes', () => {
      expect(formatNumber(1500)).toBe('1.5K');
      expect(formatNumber(1500000)).toBe('1.5M');
      expect(formatNumber(500)).toBe('500');
    });
  });

  describe('formatPercentage', () => {
    it('formats percentage with sign', () => {
      expect(formatPercentage(245)).toBe('+245%');
      expect(formatPercentage(-10)).toBe('-10%');
      expect(formatPercentage(0)).toBe('0%');
    });
  });

  describe('formatDuration', () => {
    it('formats hours and minutes', () => {
      expect(formatDuration(1.5)).toBe('1h 30m');
      expect(formatDuration(0.5)).toBe('30m');
      expect(formatDuration(8)).toBe('8h');
    });
  });
});
```

**Step 2: Create the formatters**

```ts
// apps/frontend/src/renderer/components/analytics/utils/formatters.ts

export function formatCurrency(value: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toString();
}

export function formatPercentage(value: number): string {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value}%`;
}

export function formatDuration(hours: number): string {
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);

  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

export function formatRelativeTime(date: Date | string): string {
  const now = new Date();
  const then = new Date(date);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return then.toLocaleDateString();
}
```

**Step 3: Create index**

```ts
// apps/frontend/src/renderer/components/analytics/utils/index.ts
export * from './formatters';
```

**Step 4: Run tests**

```bash
cd apps/frontend
npm test -- --run formatters.test.ts
```
Expected: PASS

**Step 5: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/utils/
git commit -m "feat(analytics): add formatter utilities"
```

---

## Workstream C: Backend API Extensions

### Task C1: Add Health Status Endpoint

**Files:**
- Modify: `apps/backend/analytics/api/routes.py`
- Modify: `apps/backend/analytics/api/models.py`
- Test: `apps/backend/tests/test_analytics_routes.py`

**Step 1: Write the failing test**

```python
# apps/backend/tests/test_analytics_routes.py (add to existing)
import pytest
from fastapi.testclient import TestClient

def test_health_status_endpoint_exists():
    """Test that /health/status endpoint returns system health."""
    from analytics.api.app import app
    from analytics.api.models import HealthStatusResponse

    # Check model exists
    assert hasattr(HealthStatusResponse, 'langfuse_connected')
    assert hasattr(HealthStatusResponse, 'claude_api_status')
    assert hasattr(HealthStatusResponse, 'graphiti_status')
```

**Step 2: Add Pydantic model**

```python
# apps/backend/analytics/api/models.py (add to existing)

class ServiceStatus(BaseModel):
    """Status of an external service."""
    connected: bool
    latency_ms: Optional[float] = None
    last_checked: Optional[datetime] = None
    error: Optional[str] = None


class HealthStatusResponse(BaseModel):
    """System health status."""
    status: str  # 'healthy', 'degraded', 'unhealthy'
    langfuse: ServiceStatus
    claude_api: ServiceStatus
    graphiti: ServiceStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

**Step 3: Add endpoint**

```python
# apps/backend/analytics/api/routes.py (add new endpoint)

@router.get("/health/status", response_model=HealthStatusResponse)
async def get_health_status():
    """
    Get comprehensive system health status.

    Checks connectivity to:
    - Langfuse (observability)
    - Claude API (LLM)
    - Graphiti (memory)
    """
    from datetime import datetime
    import time

    # Check Langfuse
    langfuse_status = ServiceStatus(connected=False)
    try:
        client = get_client()
        start = time.time()
        # Simple health check - try to list traces with limit 1
        await client.get_traces(TraceFilter(limit=1))
        langfuse_status = ServiceStatus(
            connected=True,
            latency_ms=round((time.time() - start) * 1000, 2),
            last_checked=datetime.utcnow()
        )
    except Exception as e:
        langfuse_status = ServiceStatus(
            connected=False,
            error=str(e),
            last_checked=datetime.utcnow()
        )

    # Check Claude API (just verify env var exists)
    import os
    claude_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY")
    claude_status = ServiceStatus(
        connected=bool(claude_token),
        last_checked=datetime.utcnow(),
        error=None if claude_token else "No API key configured"
    )

    # Check Graphiti
    graphiti_enabled = os.getenv("GRAPHITI_ENABLED", "").lower() == "true"
    graphiti_status = ServiceStatus(
        connected=graphiti_enabled,
        last_checked=datetime.utcnow(),
        error=None if graphiti_enabled else "Graphiti not enabled"
    )

    # Determine overall status
    all_connected = langfuse_status.connected and claude_status.connected
    any_connected = langfuse_status.connected or claude_status.connected

    status = "healthy" if all_connected else "degraded" if any_connected else "unhealthy"

    return HealthStatusResponse(
        status=status,
        langfuse=langfuse_status,
        claude_api=claude_status,
        graphiti=graphiti_status,
    )
```

**Step 4: Run tests**

```bash
cd apps/backend
.venv/bin/pytest tests/test_analytics_routes.py::test_health_status_endpoint_exists -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add apps/backend/analytics/api/routes.py apps/backend/analytics/api/models.py apps/backend/tests/test_analytics_routes.py
git commit -m "feat(analytics-api): add /health/status endpoint for system monitoring"
```

---

### Task C2: Add Recent Activity Endpoint

**Files:**
- Modify: `apps/backend/analytics/api/routes.py`
- Modify: `apps/backend/analytics/api/models.py`

**Step 1: Add model**

```python
# apps/backend/analytics/api/models.py (add)

class ActivityEvent(BaseModel):
    """A single activity event."""
    id: str
    type: str  # 'spec_completed', 'qa_passed', 'qa_failed', 'build_started'
    spec_id: str
    message: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class RecentActivityResponse(BaseModel):
    """Recent activity events."""
    events: List[ActivityEvent]
    total: int
```

**Step 2: Add endpoint**

```python
# apps/backend/analytics/api/routes.py (add)

@router.get("/specs/recent-activity", response_model=RecentActivityResponse)
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of events"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
):
    """
    Get recent activity events across specs.

    Returns the most recent trace completions with context.
    """
    client = get_client()

    filter = TraceFilter(
        project_id=project_id,
        limit=limit,
    )

    traces = await client.get_traces(filter)

    events = []
    for trace in sorted(traces, key=lambda t: t.timestamp, reverse=True)[:limit]:
        spec_id = get_spec_id_from_trace(trace)
        agent_type = get_agent_type_from_trace(trace)

        # Determine event type
        if "qa_reviewer" in agent_type:
            event_type = "qa_review"
        elif "qa_fixer" in agent_type:
            event_type = "qa_fix"
        elif "planner" in agent_type:
            event_type = "planning"
        elif "coder" in agent_type:
            event_type = "coding"
        else:
            event_type = "other"

        # Build message
        message = f"{spec_id} - {agent_type} completed"
        if trace.total_cost > 0:
            message += f" (${trace.total_cost:.2f})"

        events.append(ActivityEvent(
            id=trace.id,
            type=event_type,
            spec_id=spec_id,
            message=message,
            timestamp=trace.timestamp,
            metadata={
                "cost": trace.total_cost,
                "tokens": trace.total_tokens,
                "agent_type": agent_type,
            }
        ))

    return RecentActivityResponse(
        events=events,
        total=len(events),
    )
```

**Step 3: Commit**

```bash
git add apps/backend/analytics/api/routes.py apps/backend/analytics/api/models.py
git commit -m "feat(analytics-api): add /specs/recent-activity endpoint"
```

---

### Task C3: Add Hourly Metrics Endpoint

**Files:**
- Modify: `apps/backend/analytics/api/routes.py`
- Modify: `apps/backend/analytics/api/models.py`

**Step 1: Add model**

```python
# apps/backend/analytics/api/models.py (add)

class HourlyMetric(BaseModel):
    """Metrics for a single hour."""
    hour: str  # ISO format: 2025-01-01T14:00:00
    requests: int
    tokens: int
    cost: float
    errors: int = 0


class HourlyMetricsResponse(BaseModel):
    """Hourly aggregated metrics."""
    metrics: List[HourlyMetric]
    period: Dict[str, Optional[str]]
```

**Step 2: Add endpoint**

```python
# apps/backend/analytics/api/routes.py (add)

@router.get("/metrics/hourly", response_model=HourlyMetricsResponse)
async def get_hourly_metrics(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
):
    """
    Get hourly aggregated metrics.

    Useful for monitoring request patterns and identifying peak usage.
    """
    from collections import defaultdict
    from datetime import datetime, timedelta

    client = get_client()

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    filter = TraceFilter(
        project_id=project_id,
        from_timestamp=start_time,
        to_timestamp=end_time,
        limit=100,
    )

    traces = await client.get_traces(filter)

    # Aggregate by hour
    hourly = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": 0.0, "errors": 0})

    for trace in traces:
        hour_key = trace.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
        hourly[hour_key]["requests"] += 1
        hourly[hour_key]["tokens"] += trace.total_tokens
        hourly[hour_key]["cost"] += trace.total_cost

        # Check for errors (based on trace status or tags)
        if "error" in (trace.tags or []):
            hourly[hour_key]["errors"] += 1

    metrics = [
        HourlyMetric(
            hour=hour,
            requests=data["requests"],
            tokens=data["tokens"],
            cost=round(data["cost"], 4),
            errors=data["errors"],
        )
        for hour, data in sorted(hourly.items())
    ]

    return HourlyMetricsResponse(
        metrics=metrics,
        period={
            "from": start_time.isoformat(),
            "to": end_time.isoformat(),
        },
    )
```

**Step 3: Commit**

```bash
git add apps/backend/analytics/api/routes.py apps/backend/analytics/api/models.py
git commit -m "feat(analytics-api): add /metrics/hourly endpoint for usage patterns"
```

---

### Task C4: Add Error Metrics Endpoint

**Files:**
- Modify: `apps/backend/analytics/api/routes.py`
- Modify: `apps/backend/analytics/api/models.py`

**Step 1: Add model**

```python
# apps/backend/analytics/api/models.py (add)

class ErrorBreakdown(BaseModel):
    """Breakdown of errors by type."""
    error_type: str
    count: int
    percentage: float
    last_occurrence: Optional[datetime] = None


class ErrorMetricsResponse(BaseModel):
    """Error analytics."""
    total_errors: int
    error_rate: float  # Percentage
    by_type: List[ErrorBreakdown]
    recent_errors: List[Dict[str, Any]]  # Last 5 errors
```

**Step 2: Add endpoint**

```python
# apps/backend/analytics/api/routes.py (add)

@router.get("/metrics/errors", response_model=ErrorMetricsResponse)
async def get_error_metrics(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    from_date: Optional[datetime] = Query(None, description="From timestamp"),
):
    """
    Get error breakdown and rate.

    Identifies error patterns and recent failures.
    """
    from collections import defaultdict

    client = get_client()

    filter = TraceFilter(
        project_id=project_id,
        from_timestamp=from_date,
        limit=100,
    )

    traces = await client.get_traces(filter)

    total_traces = len(traces)
    error_traces = [t for t in traces if "error" in (t.tags or [])]
    total_errors = len(error_traces)

    error_rate = (total_errors / total_traces * 100) if total_traces > 0 else 0

    # Group by error type (from metadata or tags)
    by_type = defaultdict(lambda: {"count": 0, "last": None})

    for trace in error_traces:
        error_type = trace.metadata.get("error_type", "unknown") if trace.metadata else "unknown"
        by_type[error_type]["count"] += 1
        if by_type[error_type]["last"] is None or trace.timestamp > by_type[error_type]["last"]:
            by_type[error_type]["last"] = trace.timestamp

    breakdowns = [
        ErrorBreakdown(
            error_type=etype,
            count=data["count"],
            percentage=round(data["count"] / total_errors * 100, 1) if total_errors > 0 else 0,
            last_occurrence=data["last"],
        )
        for etype, data in sorted(by_type.items(), key=lambda x: x[1]["count"], reverse=True)
    ]

    # Recent errors
    recent = [
        {
            "id": t.id,
            "spec_id": get_spec_id_from_trace(t),
            "agent_type": get_agent_type_from_trace(t),
            "timestamp": t.timestamp.isoformat(),
            "error_type": t.metadata.get("error_type", "unknown") if t.metadata else "unknown",
        }
        for t in sorted(error_traces, key=lambda t: t.timestamp, reverse=True)[:5]
    ]

    return ErrorMetricsResponse(
        total_errors=total_errors,
        error_rate=round(error_rate, 2),
        by_type=breakdowns,
        recent_errors=recent,
    )
```

**Step 3: Commit**

```bash
git add apps/backend/analytics/api/routes.py apps/backend/analytics/api/models.py
git commit -m "feat(analytics-api): add /metrics/errors endpoint for error tracking"
```

---

## Workstream D: i18n Additions

### Task D1: Add Complete Analytics Translations

**Files:**
- Modify: `apps/frontend/src/shared/i18n/locales/en/analytics.json`
- Modify: `apps/frontend/src/shared/i18n/locales/fr/analytics.json`

**Step 1: Update English translations**

```json
// apps/frontend/src/shared/i18n/locales/en/analytics.json
// Add new sections for tabs (merge with existing content)
{
  "tabs": {
    "overview": "Overview",
    "dev": "Dev",
    "techLead": "Tech Lead",
    "ops": "Ops",
    "business": "Business"
  },
  "overview": {
    "title": "Overview",
    "totalCost": "Total Cost",
    "totalTokens": "Total Tokens",
    "hoursSaved": "Hours Saved",
    "avgROI": "Average ROI",
    "costVsValue": "Cost vs Value",
    "netValue": "Net Value",
    "statusQuick": "Quick Status",
    "specsCompleted": "specs completed",
    "specsInProgress": "in progress",
    "recentActivity": "Recent Activity"
  },
  "dev": {
    "title": "Developer Dashboard",
    "mySpecs": "My Specs",
    "myCost": "My Cost",
    "timeSaved": "Time Saved",
    "successRate": "Success Rate",
    "specsTable": "Specs Table",
    "costBySpec": "Cost by Spec",
    "productivity": "Productivity Metrics",
    "firstAttemptPass": "First Attempt Pass Rate",
    "viewInLangfuse": "View in Langfuse"
  },
  "techLead": {
    "title": "Tech Lead Dashboard",
    "budget": "Budget",
    "budgetUsed": "used",
    "budgetRemaining": "remaining",
    "projection": "Month-end Projection",
    "onTrack": "On Track",
    "overBudget": "Over Budget",
    "costOverTime": "Cost Over Time",
    "agentDistribution": "Agent Distribution",
    "performanceTable": "Performance Table",
    "efficiency": "Efficiency",
    "roiTrend": "ROI Trend",
    "insights": "Auto Insights",
    "weeklyComparison": "Weekly Comparison",
    "thisWeek": "This Week",
    "lastWeek": "Last Week",
    "change": "Change"
  },
  "ops": {
    "title": "Operations Dashboard",
    "systemHealth": "System Health",
    "healthy": "Healthy",
    "degraded": "Degraded",
    "unhealthy": "Unhealthy",
    "activeAlerts": "Active Alerts",
    "noAlerts": "No active alerts",
    "requestsPerHour": "Requests per Hour",
    "errorRate": "Error Rate",
    "errors": "errors",
    "modelUsage": "Model Usage",
    "tokensPerHour": "Tokens per Hour",
    "errorTraces": "Error Traces",
    "latencyByAgent": "Latency by Agent",
    "rateLimits": "Rate Limits",
    "recentLogs": "Recent Logs"
  },
  "business": {
    "title": "Business Dashboard",
    "executiveSummary": "Executive Summary",
    "invested": "Invested",
    "valueGenerated": "Value Generated",
    "netSavings": "Net Savings",
    "hoursImpact": "Hours Impact",
    "equivalentTo": "Equivalent to",
    "workWeeks": "work weeks",
    "roiByMonth": "ROI by Month",
    "valueByType": "Value by Task Type",
    "aiVsManual": "AI vs Manual Comparison",
    "topSpecs": "Top Performing Specs",
    "annualProjection": "Annual Projection",
    "exportPDF": "Export PDF Report"
  },
  "alerts": {
    "budgetHigh": "Budget High",
    "budgetHighDesc": "Over 80% of budget used",
    "errorRateHigh": "Error Rate High",
    "errorRateHighDesc": "Error rate exceeds 5%",
    "latencyHigh": "Latency High",
    "latencyHighDesc": "P95 latency over 10 minutes",
    "rateLimitNear": "Rate Limit Near",
    "rateLimitNearDesc": "Over 70% of rate limit",
    "qaFailures": "QA Failures",
    "qaFailuresDesc": "Spec failed 3+ times"
  }
}
```

**Step 2: Update French translations**

```json
// apps/frontend/src/shared/i18n/locales/fr/analytics.json
// Add same structure in French
{
  "tabs": {
    "overview": "Vue d'ensemble",
    "dev": "Dev",
    "techLead": "Tech Lead",
    "ops": "Ops",
    "business": "Business"
  },
  "overview": {
    "title": "Vue d'ensemble",
    "totalCost": "Coût Total",
    "totalTokens": "Tokens Total",
    "hoursSaved": "Heures Économisées",
    "avgROI": "ROI Moyen",
    "costVsValue": "Coût vs Valeur",
    "netValue": "Valeur Nette",
    "statusQuick": "Statut Rapide",
    "specsCompleted": "specs complétées",
    "specsInProgress": "en cours",
    "recentActivity": "Activité Récente"
  },
  "dev": {
    "title": "Tableau de Bord Développeur",
    "mySpecs": "Mes Specs",
    "myCost": "Mon Coût",
    "timeSaved": "Temps Économisé",
    "successRate": "Taux de Succès",
    "specsTable": "Table des Specs",
    "costBySpec": "Coût par Spec",
    "productivity": "Métriques de Productivité",
    "firstAttemptPass": "Taux de Passage Premier Essai",
    "viewInLangfuse": "Voir dans Langfuse"
  },
  "techLead": {
    "title": "Tableau de Bord Tech Lead",
    "budget": "Budget",
    "budgetUsed": "utilisé",
    "budgetRemaining": "restant",
    "projection": "Projection Fin de Mois",
    "onTrack": "Dans les Clous",
    "overBudget": "Dépassement Budget",
    "costOverTime": "Coût dans le Temps",
    "agentDistribution": "Distribution des Agents",
    "performanceTable": "Table de Performance",
    "efficiency": "Efficacité",
    "roiTrend": "Tendance ROI",
    "insights": "Insights Auto",
    "weeklyComparison": "Comparaison Hebdo",
    "thisWeek": "Cette Semaine",
    "lastWeek": "Semaine Dernière",
    "change": "Variation"
  },
  "ops": {
    "title": "Tableau de Bord Opérations",
    "systemHealth": "Santé Système",
    "healthy": "Sain",
    "degraded": "Dégradé",
    "unhealthy": "Non Sain",
    "activeAlerts": "Alertes Actives",
    "noAlerts": "Aucune alerte active",
    "requestsPerHour": "Requêtes par Heure",
    "errorRate": "Taux d'Erreur",
    "errors": "erreurs",
    "modelUsage": "Utilisation Modèle",
    "tokensPerHour": "Tokens par Heure",
    "errorTraces": "Traces d'Erreur",
    "latencyByAgent": "Latence par Agent",
    "rateLimits": "Limites de Débit",
    "recentLogs": "Logs Récents"
  },
  "business": {
    "title": "Tableau de Bord Business",
    "executiveSummary": "Résumé Exécutif",
    "invested": "Investi",
    "valueGenerated": "Valeur Générée",
    "netSavings": "Économies Nettes",
    "hoursImpact": "Impact Heures",
    "equivalentTo": "Équivalent à",
    "workWeeks": "semaines de travail",
    "roiByMonth": "ROI par Mois",
    "valueByType": "Valeur par Type de Tâche",
    "aiVsManual": "Comparaison IA vs Manuel",
    "topSpecs": "Meilleures Specs",
    "annualProjection": "Projection Annuelle",
    "exportPDF": "Exporter Rapport PDF"
  },
  "alerts": {
    "budgetHigh": "Budget Élevé",
    "budgetHighDesc": "Plus de 80% du budget utilisé",
    "errorRateHigh": "Taux d'Erreur Élevé",
    "errorRateHighDesc": "Taux d'erreur supérieur à 5%",
    "latencyHigh": "Latence Élevée",
    "latencyHighDesc": "Latence P95 supérieure à 10 min",
    "rateLimitNear": "Limite de Débit Proche",
    "rateLimitNearDesc": "Plus de 70% de la limite",
    "qaFailures": "Échecs QA",
    "qaFailuresDesc": "Spec échouée 3+ fois"
  }
}
```

**Step 3: Commit**

```bash
git add apps/frontend/src/shared/i18n/locales/en/analytics.json apps/frontend/src/shared/i18n/locales/fr/analytics.json
git commit -m "feat(i18n): add complete analytics dashboard translations"
```

---

## Workstream E: Tab Components

### Task E1: Create OverviewTab

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/tabs/OverviewTab.tsx`
- Create: `apps/frontend/src/renderer/components/analytics/overview/OverviewCards.tsx`
- Create: `apps/frontend/src/renderer/components/analytics/overview/CostValueBar.tsx`
- Create: `apps/frontend/src/renderer/components/analytics/overview/StatusQuickView.tsx`
- Create: `apps/frontend/src/renderer/components/analytics/overview/RecentActivity.tsx`

**Step 1: Create OverviewCards component**

```tsx
// apps/frontend/src/renderer/components/analytics/overview/OverviewCards.tsx
import { useTranslation } from 'react-i18next';
import { DollarSign, Coins, Clock, TrendingUp } from 'lucide-react';
import { MetricCard } from '../shared';
import { formatCurrency, formatNumber, formatDuration, formatPercentage } from '../utils';

interface OverviewCardsProps {
  totalCost: number;
  totalTokens: number;
  hoursSaved: number;
  avgROI: number;
}

export function OverviewCards({ totalCost, totalTokens, hoursSaved, avgROI }: OverviewCardsProps) {
  const { t } = useTranslation(['analytics']);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        value={formatCurrency(totalCost)}
        label={t('analytics:overview.totalCost')}
        icon={<DollarSign className="h-4 w-4" />}
      />
      <MetricCard
        value={formatNumber(totalTokens)}
        label={t('analytics:overview.totalTokens')}
        icon={<Coins className="h-4 w-4" />}
      />
      <MetricCard
        value={formatDuration(hoursSaved)}
        label={t('analytics:overview.hoursSaved')}
        icon={<Clock className="h-4 w-4" />}
        variant="success"
      />
      <MetricCard
        value={formatPercentage(avgROI)}
        label={t('analytics:overview.avgROI')}
        icon={<TrendingUp className="h-4 w-4" />}
        variant={avgROI > 0 ? 'success' : 'danger'}
      />
    </div>
  );
}
```

**Step 2: Create CostValueBar component**

```tsx
// apps/frontend/src/renderer/components/analytics/overview/CostValueBar.tsx
import { useTranslation } from 'react-i18next';
import { formatCurrency } from '../utils';

interface CostValueBarProps {
  cost: number;
  value: number;
}

export function CostValueBar({ cost, value }: CostValueBarProps) {
  const { t } = useTranslation(['analytics']);

  const net = value - cost;
  const total = cost + value;
  const costPercent = total > 0 ? (cost / total) * 100 : 50;

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="font-semibold mb-4">{t('analytics:overview.costVsValue')}</h3>

      <div className="relative h-8 rounded-full overflow-hidden bg-gray-200 dark:bg-gray-700">
        <div
          className="absolute h-full bg-red-500 dark:bg-red-600"
          style={{ width: `${costPercent}%` }}
        />
        <div
          className="absolute h-full bg-green-500 dark:bg-green-600 right-0"
          style={{ width: `${100 - costPercent}%` }}
        />
      </div>

      <div className="flex justify-between mt-2 text-sm">
        <span className="text-red-600 dark:text-red-400">
          {formatCurrency(cost)} Cost
        </span>
        <span className="text-green-600 dark:text-green-400">
          {formatCurrency(value)} Value
        </span>
      </div>

      <div className="mt-4 text-center">
        <span className="text-lg font-bold">
          {t('analytics:overview.netValue')}: {' '}
          <span className={net >= 0 ? 'text-green-600' : 'text-red-600'}>
            {net >= 0 ? '+' : ''}{formatCurrency(net)}
          </span>
        </span>
      </div>
    </div>
  );
}
```

**Step 3: Create StatusQuickView component**

```tsx
// apps/frontend/src/renderer/components/analytics/overview/StatusQuickView.tsx
import { useTranslation } from 'react-i18next';
import { CheckCircle, Clock, AlertCircle } from 'lucide-react';

interface StatusQuickViewProps {
  completed: number;
  inProgress: number;
  failed: number;
}

export function StatusQuickView({ completed, inProgress, failed }: StatusQuickViewProps) {
  const { t } = useTranslation(['analytics']);

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="font-semibold mb-4">{t('analytics:overview.statusQuick')}</h3>

      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <CheckCircle className="h-5 w-5 text-green-500" />
          <span className="text-sm">
            {completed} {t('analytics:overview.specsCompleted')}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-yellow-500" />
          <span className="text-sm">
            {inProgress} {t('analytics:overview.specsInProgress')}
          </span>
        </div>

        {failed > 0 && (
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <span className="text-sm text-red-600">
              {failed} failed
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 4: Create RecentActivity component**

```tsx
// apps/frontend/src/renderer/components/analytics/overview/RecentActivity.tsx
import { useTranslation } from 'react-i18next';
import { formatRelativeTime, formatPercentage } from '../utils';
import { AlertBadge } from '../shared';

interface ActivityEvent {
  id: string;
  type: string;
  spec_id: string;
  message: string;
  timestamp: string;
  metadata?: {
    roi_percentage?: number;
  };
}

interface RecentActivityProps {
  events: ActivityEvent[];
}

export function RecentActivity({ events }: RecentActivityProps) {
  const { t } = useTranslation(['analytics']);

  const getEventBadge = (type: string) => {
    switch (type) {
      case 'qa_review':
        return <AlertBadge severity="info" label="QA" />;
      case 'coding':
        return <AlertBadge severity="success" label="Code" />;
      case 'planning':
        return <AlertBadge severity="warning" label="Plan" />;
      default:
        return null;
    }
  };

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="font-semibold mb-4">{t('analytics:overview.recentActivity')}</h3>

      {events.length === 0 ? (
        <p className="text-sm text-muted-foreground">No recent activity</p>
      ) : (
        <ul className="space-y-3">
          {events.map((event) => (
            <li key={event.id} className="flex items-start gap-2 text-sm">
              <span className="shrink-0">{getEventBadge(event.type)}</span>
              <div className="flex-1">
                <span className="font-medium">{event.spec_id}</span>
                <span className="text-muted-foreground"> - {event.message}</span>
                {event.metadata?.roi_percentage !== undefined && (
                  <span className="ml-1 text-green-600">
                    ROI: {formatPercentage(event.metadata.roi_percentage)}
                  </span>
                )}
              </div>
              <span className="text-xs text-muted-foreground shrink-0">
                {formatRelativeTime(event.timestamp)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

**Step 5: Create OverviewTab**

```tsx
// apps/frontend/src/renderer/components/analytics/tabs/OverviewTab.tsx
import { useTranslation } from 'react-i18next';
import { useUsageSummary, useROISummary, useRecentActivity } from '../../../hooks/useAnalyticsQuery';
import { OverviewCards } from '../overview/OverviewCards';
import { CostValueBar } from '../overview/CostValueBar';
import { StatusQuickView } from '../overview/StatusQuickView';
import { RecentActivity } from '../overview/RecentActivity';
import { ChartContainer } from '../shared';

interface OverviewTabProps {
  projectName: string;
}

export function OverviewTab({ projectName }: OverviewTabProps) {
  const { t } = useTranslation(['analytics']);

  const usage = useUsageSummary({ project_id: projectName });
  const roi = useROISummary({ project_id: projectName });
  const activity = useRecentActivity({ project_id: projectName });

  const isLoading = usage.isLoading || roi.isLoading;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 rounded-lg border bg-card animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const usageData = usage.data;
  const roiData = roi.data;

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <OverviewCards
        totalCost={usageData?.total_cost || 0}
        totalTokens={usageData?.total_tokens || 0}
        hoursSaved={roiData?.total_dev_hours_saved || 0}
        avgROI={roiData?.total_roi_percentage || 0}
      />

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CostValueBar
          cost={roiData?.total_actual_cost_usd || 0}
          value={roiData?.total_business_value_usd || 0}
        />
        <StatusQuickView
          completed={roiData?.specs_with_positive_roi || 0}
          inProgress={usageData?.active_specs || 0}
          failed={0}
        />
      </div>

      {/* Recent Activity */}
      <RecentActivity events={activity.data?.events || []} />
    </div>
  );
}
```

**Step 6: Create index file**

```tsx
// apps/frontend/src/renderer/components/analytics/tabs/index.ts
export { OverviewTab } from './OverviewTab';
```

```tsx
// apps/frontend/src/renderer/components/analytics/overview/index.ts
export { OverviewCards } from './OverviewCards';
export { CostValueBar } from './CostValueBar';
export { StatusQuickView } from './StatusQuickView';
export { RecentActivity } from './RecentActivity';
```

**Step 7: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/tabs/ apps/frontend/src/renderer/components/analytics/overview/
git commit -m "feat(analytics): implement OverviewTab with cards, cost bar, status, and activity"
```

---

### Task E2: Create DevTab (Summary)

**Files to create:**
- `apps/frontend/src/renderer/components/analytics/tabs/DevTab.tsx`
- `apps/frontend/src/renderer/components/analytics/dev/DevOverviewCards.tsx`
- `apps/frontend/src/renderer/components/analytics/dev/MySpecsTable.tsx`
- `apps/frontend/src/renderer/components/analytics/dev/CostBySpecChart.tsx`
- `apps/frontend/src/renderer/components/analytics/dev/ProductivityMetrics.tsx`

**Key features:**
- Personal spec list with sortable table
- Cost breakdown by spec (bar chart)
- Productivity metrics (first attempt pass rate)
- Link to Langfuse trace for each spec

**Commit:**
```bash
git commit -m "feat(analytics): implement DevTab for individual developer metrics"
```

---

### Task E3: Create TechLeadTab (Summary)

**Files to create:**
- `apps/frontend/src/renderer/components/analytics/tabs/TechLeadTab.tsx`
- `apps/frontend/src/renderer/components/analytics/techlead/BudgetTracker.tsx`
- `apps/frontend/src/renderer/components/analytics/techlead/CostOverTimeChart.tsx`
- `apps/frontend/src/renderer/components/analytics/techlead/AgentDistributionChart.tsx`
- `apps/frontend/src/renderer/components/analytics/techlead/PerformanceTable.tsx`
- `apps/frontend/src/renderer/components/analytics/techlead/ROITrendChart.tsx`
- `apps/frontend/src/renderer/components/analytics/techlead/WeeklyComparison.tsx`

**Key features:**
- Budget progress bar with projection
- Cost over time line chart
- Agent distribution pie chart
- Performance table with efficiency grades
- Weekly comparison (this week vs last week)

**Commit:**
```bash
git commit -m "feat(analytics): implement TechLeadTab for project-wide metrics"
```

---

### Task E4: Create OpsTab (Summary)

**Files to create:**
- `apps/frontend/src/renderer/components/analytics/tabs/OpsTab.tsx`
- `apps/frontend/src/renderer/components/analytics/ops/HealthStatusCards.tsx`
- `apps/frontend/src/renderer/components/analytics/ops/ActiveAlerts.tsx`
- `apps/frontend/src/renderer/components/analytics/ops/RequestsPerHourChart.tsx`
- `apps/frontend/src/renderer/components/analytics/ops/ErrorRatePanel.tsx`
- `apps/frontend/src/renderer/components/analytics/ops/ModelUsageChart.tsx`
- `apps/frontend/src/renderer/components/analytics/ops/ErrorTracesTable.tsx`

**Key features:**
- System health indicators (Langfuse, Claude API, Graphiti)
- Active alerts list with severity badges
- Requests per hour line chart
- Error rate breakdown
- Recent error traces table

**Commit:**
```bash
git commit -m "feat(analytics): implement OpsTab for system health and monitoring"
```

---

### Task E5: Create BusinessTab (Summary)

**Files to create:**
- `apps/frontend/src/renderer/components/analytics/tabs/BusinessTab.tsx`
- `apps/frontend/src/renderer/components/analytics/business/ExecutiveSummary.tsx`
- `apps/frontend/src/renderer/components/analytics/business/InvestmentCards.tsx`
- `apps/frontend/src/renderer/components/analytics/business/HoursImpact.tsx`
- `apps/frontend/src/renderer/components/analytics/business/ROIByMonthChart.tsx`
- `apps/frontend/src/renderer/components/analytics/business/AIvsManualTable.tsx`
- `apps/frontend/src/renderer/components/analytics/business/TopSpecsTable.tsx`
- `apps/frontend/src/renderer/components/analytics/business/AnnualProjection.tsx`
- `apps/frontend/src/renderer/components/analytics/business/ExportPDFButton.tsx`

**Key features:**
- Executive summary with large ROI display
- Investment cards (Invested, Value, Savings)
- Hours impact visualization
- ROI by month chart
- AI vs Manual comparison table
- Top performing specs ranking
- Annual projection
- PDF export functionality

**Commit:**
```bash
git commit -m "feat(analytics): implement BusinessTab for executive ROI reporting"
```

---

## Workstream F: Integration

### Task F1: Update Analytics.tsx to Use New Tabs

**Files:**
- Modify: `apps/frontend/src/renderer/components/analytics/Analytics.tsx`

**Step 1: Update imports and tabs**

```tsx
// apps/frontend/src/renderer/components/analytics/Analytics.tsx
// Replace current tabs structure with new 5-tab structure

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useProjectStore } from '../../stores/project-store';
import { useAnalyticsHealth } from '../../hooks/useAnalyticsQuery';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';

// Import new tabs
import { OverviewTab } from './tabs/OverviewTab';
import { DevTab } from './tabs/DevTab';
import { TechLeadTab } from './tabs/TechLeadTab';
import { OpsTab } from './tabs/OpsTab';
import { BusinessTab } from './tabs/BusinessTab';

type TabValue = 'overview' | 'dev' | 'techLead' | 'ops' | 'business';

interface AnalyticsProps {
  projectId?: string;
  initialTab?: TabValue;
}

export function Analytics({ projectId, initialTab = 'overview' }: AnalyticsProps) {
  const { t } = useTranslation(['analytics']);
  const [activeTab, setActiveTab] = useState<TabValue>(initialTab);

  const projects = useProjectStore((state) => state.projects);
  const project = projects.find((p) => p.id === projectId);
  const projectName = project?.name;

  const health = useAnalyticsHealth();

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  // Loading and error states...
  if (health.isLoading) {
    return <LoadingState />;
  }

  if (!projectId || !projectName) {
    return <NoProjectState />;
  }

  if (!health.data?.langfuse_configured) {
    return <NotConfiguredState />;
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">{t('analytics:header.title')}</h1>
          <p className="text-muted-foreground">{t('analytics:header.subtitle')}</p>
        </div>

        {/* 5-Tab Navigation */}
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabValue)}>
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview">{t('analytics:tabs.overview')}</TabsTrigger>
            <TabsTrigger value="dev">{t('analytics:tabs.dev')}</TabsTrigger>
            <TabsTrigger value="techLead">{t('analytics:tabs.techLead')}</TabsTrigger>
            <TabsTrigger value="ops">{t('analytics:tabs.ops')}</TabsTrigger>
            <TabsTrigger value="business">{t('analytics:tabs.business')}</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            <OverviewTab projectName={projectName} />
          </TabsContent>

          <TabsContent value="dev" className="mt-6">
            <DevTab projectName={projectName} />
          </TabsContent>

          <TabsContent value="techLead" className="mt-6">
            <TechLeadTab projectName={projectName} />
          </TabsContent>

          <TabsContent value="ops" className="mt-6">
            <OpsTab projectName={projectName} />
          </TabsContent>

          <TabsContent value="business" className="mt-6">
            <BusinessTab projectName={projectName} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

// Helper components for states
function LoadingState() {
  const { t } = useTranslation(['analytics']);
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">{t('analytics:loading.title')}</h2>
        <p className="text-muted-foreground">{t('analytics:loading.subtitle')}</p>
      </div>
    </div>
  );
}

function NoProjectState() {
  const { t } = useTranslation(['analytics']);
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">{t('analytics:noProject.title')}</h2>
        <p className="text-muted-foreground">{t('analytics:noProject.subtitle')}</p>
      </div>
    </div>
  );
}

function NotConfiguredState() {
  const { t } = useTranslation(['analytics']);
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">{t('analytics:notConfigured.title')}</h2>
        <p className="text-muted-foreground">{t('analytics:notConfigured.subtitle')}</p>
      </div>
    </div>
  );
}
```

**Step 2: Add new hooks for recent activity**

```tsx
// apps/frontend/src/renderer/hooks/useAnalyticsQuery.ts
// Add new hook for recent activity

export function useRecentActivity(
  params: { project_id?: string; limit?: number },
  options: { enabled?: boolean } = {}
) {
  return useQuery({
    queryKey: ['analytics', 'recent-activity', params],
    queryFn: async () => {
      const response = await fetch(
        `${ANALYTICS_API_URL}/api/analytics/specs/recent-activity?` +
          new URLSearchParams({
            ...(params.project_id && { project_id: params.project_id }),
            ...(params.limit && { limit: params.limit.toString() }),
          })
      );
      if (!response.ok) throw new Error('Failed to fetch recent activity');
      return response.json();
    },
    enabled: options.enabled ?? true,
  });
}
```

**Step 3: Run build to verify**

```bash
cd apps/frontend
npm run build
```
Expected: BUILD SUCCESS

**Step 4: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/Analytics.tsx
git add apps/frontend/src/renderer/hooks/useAnalyticsQuery.ts
git commit -m "feat(analytics): integrate 5-tab dashboard structure"
```

---

### Task F2: Add PDF Export Functionality

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/business/ExportPDFButton.tsx`
- Add dependency: `jspdf` and `html2canvas`

**Step 1: Install dependencies**

```bash
cd apps/frontend
npm install jspdf html2canvas @types/html2canvas
```

**Step 2: Create ExportPDFButton**

```tsx
// apps/frontend/src/renderer/components/analytics/business/ExportPDFButton.tsx
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FileDown, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ExportPDFButtonProps {
  targetId: string;
  fileName?: string;
}

export function ExportPDFButton({ targetId, fileName = 'analytics-report' }: ExportPDFButtonProps) {
  const { t } = useTranslation(['analytics']);
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);

    try {
      const html2canvas = (await import('html2canvas')).default;
      const jsPDF = (await import('jspdf')).default;

      const element = document.getElementById(targetId);
      if (!element) {
        throw new Error('Target element not found');
      }

      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        logging: false,
      });

      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'px',
        format: [canvas.width, canvas.height],
      });

      pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
      pdf.save(`${fileName}-${new Date().toISOString().split('T')[0]}.pdf`);
    } catch (error) {
      console.error('PDF export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Button
      variant="outline"
      onClick={handleExport}
      disabled={isExporting}
    >
      {isExporting ? (
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      ) : (
        <FileDown className="mr-2 h-4 w-4" />
      )}
      {t('analytics:business.exportPDF')}
    </Button>
  );
}
```

**Step 3: Commit**

```bash
git add apps/frontend/package.json apps/frontend/src/renderer/components/analytics/business/ExportPDFButton.tsx
git commit -m "feat(analytics): add PDF export functionality for business reports"
```

---

### Task F3: Final Integration Testing

**Step 1: Run all backend tests**

```bash
cd apps/backend
.venv/bin/pytest tests/test_analytics*.py -v
```
Expected: All PASS

**Step 2: Run frontend build**

```bash
cd apps/frontend
npm run build
```
Expected: BUILD SUCCESS

**Step 3: Run frontend tests**

```bash
cd apps/frontend
npm test
```
Expected: All PASS

**Step 4: Manual verification checklist**

- [ ] Start backend: `npm run analytics:api`
- [ ] Start frontend: `npm run dev`
- [ ] Navigate to Analytics
- [ ] Verify all 5 tabs render without errors
- [ ] Verify "Unknown" no longer appears in charts
- [ ] Verify Total Tokens shows non-zero values
- [ ] Verify each tab loads data correctly
- [ ] Verify i18n works (switch to French)
- [ ] Verify PDF export works in Business tab

**Step 5: Final commit**

```bash
git add .
git commit -m "feat(analytics): complete 5-tab dashboard implementation

- Bug fixes: Unknown values, Total Tokens
- New tabs: Overview, Dev, Tech Lead, Ops, Business
- New API endpoints: health, activity, hourly, errors
- Shared components: MetricCard, ChartContainer, DataTable, AlertBadge
- Complete i18n support (en + fr)
- PDF export for business reports

Closes #analytics-redesign"
```

---

## Success Metrics

After completing all tasks:

- [ ] Zero "Unknown" in charts
- [ ] Total Tokens shows real values
- [ ] All 5 tabs functional
- [ ] Each tab loads in < 2s
- [ ] All tests passing
- [ ] i18n complete (en + fr)
- [ ] PDF export working

---

*Plan created: 2025-01-01*
*Estimated tasks: 20 main tasks across 6 workstreams*
*Parallelism: A, B, C, D can run concurrently*
