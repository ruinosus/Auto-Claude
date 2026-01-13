# @auto-claude/roi-sdk

TypeScript SDK for Auto-Claude ROI Engine.

## Installation

```bash
npm install @auto-claude/roi-sdk
# or
yarn add @auto-claude/roi-sdk
# or
pnpm add @auto-claude/roi-sdk
```

## Quick Start

```tsx
import { useROI, ROISummaryCard } from '@auto-claude/roi-sdk';

function SpecAnalytics({ specId, projectDir }: Props) {
  const { roi, loading, error } = useROI({
    specId,
    projectDir,
    tokenCost: 0.85,
  });

  if (loading) return <Spinner />;
  if (error) return <Error message={error.message} />;

  return <ROISummaryCard roi={roi} showBreakdown />;
}
```

## Features

- **Type-safe API Client**: Full TypeScript support with all request/response types
- **React Hooks**: `useROI` and `useArtifacts` for easy data fetching
- **UI Components**: Ready-to-use components for displaying ROI metrics

## API Client

### Creating a Client

```typescript
import { createClient, ROIClient } from '@auto-claude/roi-sdk';

// Use default configuration
const client = createClient();

// Or with custom configuration
const client = createClient({
  baseUrl: 'http://localhost:8002',
  timeout: 30000,
  headers: {
    'Authorization': 'Bearer token',
  },
});
```

### Client Methods

```typescript
// Health check
const health = await client.health();

// Get ROI for a spec
const roi = await client.getROIForSpec('001-feature', '/path/to/project', 0.85);

// Get ROI summary
const summary = await client.getROISummary('001-feature', '/path/to/project');

// Calculate ROI for a spec
const roi = await client.calculateROIForSpec({
  spec_id: '001-feature',
  project_dir: '/path/to/project',
  token_cost: 0.85,
});

// Calculate ROI for a trace
const roi = await client.calculateROIForTrace({
  trace_id: 'trace_abc123',
  project_dir: '/path/to/project',
  token_cost: 0.50,
});

// List artifacts
const artifacts = await client.listArtifacts({
  projectDir: '/path/to/project',
  specId: '001-feature',
  limit: 50,
});

// Get single artifact
const artifact = await client.getArtifact('art_xyz', '/path/to/project');

// Preview artifact value
const preview = await client.previewArtifactValue({
  artifact_type: 'diagram',
  seniority: 'senior',
});

// Get configuration
const rates = await client.getRates();
const types = await client.getArtifactTypes();
const roles = await client.getRoles();
```

## React Hooks

### useROI

Fetch ROI data for a spec or trace.

```tsx
import { useROI } from '@auto-claude/roi-sdk';

function SpecROI({ specId, projectDir }: Props) {
  const { roi, summary, loading, error, refetch } = useROI({
    specId,
    projectDir,
    tokenCost: 0.85,
    enabled: true, // optional, default true
  });

  if (loading) return <Spinner />;
  if (error) return <Error message={error.message} />;

  return (
    <div>
      <h2>ROI: {roi?.roi_percentage.toFixed(1)}%</h2>
      <p>Value: ${roi?.total_artifact_value.toFixed(2)}</p>
      <p>Cost: ${roi?.token_cost.toFixed(2)}</p>
      <button onClick={refetch}>Refresh</button>
    </div>
  );
}
```

### useArtifacts

Fetch artifacts with optional filters.

```tsx
import { useArtifacts } from '@auto-claude/roi-sdk';

function ArtifactList({ specId, projectDir }: Props) {
  const { artifacts, totalCount, totalValue, loading, error } = useArtifacts({
    specId,
    projectDir,
    artifactType: 'diagram', // optional filter
    limit: 50,
  });

  return (
    <ul>
      {artifacts.map(artifact => (
        <li key={artifact.artifact_id}>
          {artifact.artifact_type}: ${artifact.calculated_value.toFixed(2)}
        </li>
      ))}
    </ul>
  );
}
```

### Utility Functions

```typescript
import {
  groupArtifactsByRole,
  groupArtifactsByType,
  calculateGroupValue,
} from '@auto-claude/roi-sdk';

// Group artifacts by role
const byRole = groupArtifactsByRole(artifacts);
// { developer: [...], architect: [...], ... }

// Group artifacts by type
const byType = groupArtifactsByType(artifacts);
// { diagram: [...], spec_document: [...], ... }

// Calculate total value
const total = calculateGroupValue(artifacts);
```

## Components

### ROISummaryCard

Displays a summary of ROI calculation.

```tsx
import { ROISummaryCard } from '@auto-claude/roi-sdk';

<ROISummaryCard
  roi={roiResult}
  loading={false}
  showBreakdown={true}
  className="my-card"
/>
```

### ArtifactsByRole

Displays artifacts grouped by role.

```tsx
import { ArtifactsByRole } from '@auto-claude/roi-sdk';

<ArtifactsByRole
  artifacts={artifacts}
  onArtifactClick={(artifact) => console.log(artifact)}
  className="my-list"
/>
```

### ValueBreakdown

Displays a visual breakdown of value.

```tsx
import { ValueBreakdown } from '@auto-claude/roi-sdk';

<ValueBreakdown
  byRole={roi.by_role}
  byType={roi.by_type}
  tokenCost={roi.token_cost}
  className="my-breakdown"
/>
```

## Types

All types are fully exported:

```typescript
import type {
  // Enums
  Role,
  Seniority,
  ROIScope,

  // Core Models
  ArtifactValue,
  ROIResult,
  ROISummary,

  // Request Types
  SpecROIRequest,
  TraceROIRequest,

  // Response Types
  ArtifactListResponse,
  RateTableResponse,

  // Hook Types
  UseROIOptions,
  UseROIResult,
} from '@auto-claude/roi-sdk';
```

### Constants

```typescript
import { ROLE_LABELS, ROLE_COLORS, SENIORITY_LABELS } from '@auto-claude/roi-sdk';

ROLE_LABELS.architect // "Architect"
ROLE_COLORS.architect // "#EF4444"
SENIORITY_LABELS.senior // "Senior"
```

## Styling

Components use BEM-style class names for easy customization:

```css
/* ROISummaryCard */
.roi-summary-card { }
.roi-summary-card__percentage { }
.roi-summary-card__value { }
.roi-summary-card__breakdown { }

/* ArtifactsByRole */
.artifacts-by-role { }
.artifacts-by-role__section { }
.artifacts-by-role__role-name { }

/* ValueBreakdown */
.value-breakdown { }
.value-breakdown__bar-fill { }
.value-breakdown__summary { }
```

## License

MIT
