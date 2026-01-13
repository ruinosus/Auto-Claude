# Frontend Migration Roadmap: Analytics API → ROI Engine API

## Executive Summary

**Goal:** Migrate frontend from Analytics API (port 8100) to ROI Engine API (port 8002)

**Current State:**
- Analytics API: ~45 endpoints, heavily used by frontend
- ROI Engine API: 52 endpoints, partially used (only ROI dashboard migrated)

**Challenge:** NOT all Analytics API features have ROI Engine equivalents. Some features will need to be:
1. Migrated (direct equivalent exists)
2. Adapted (similar endpoint with different structure)
3. Kept on Analytics API (no equivalent, too complex to reimplement)
4. Deprecated (no longer needed)

---

## Migration Feasibility Matrix

| Category | Endpoints | ROI Engine Support | Action |
|----------|-----------|-------------------|--------|
| Health Checks | 2 | ✅ Full | Migrate |
| Traces & Sessions | 4 | ✅ Full | Migrate |
| ROI Calculations | 7 | ⚠️ Partial (different structure) | Adapt with bridge |
| Artifacts | 5 | ⚠️ Partial | Adapt |
| Costs & Billing | 4 | ✅ Full | Migrate |
| Quality Scores | 3 | ✅ Full | Migrate |
| Cost Avoidance | 4 | ✅ Full | Migrate |
| Forecasting | 6 | ✅ Full | Migrate |
| Benchmarks | 4 | ✅ Full | Migrate |
| Time Saved | 5 | ❌ None | Keep on Analytics API |
| Satisfaction | 6 | ❌ None | Keep on Analytics API |

---

## Phased Migration Plan

### Phase M1: Core Infrastructure (Week 1)
**Goal:** Set up migration infrastructure without breaking existing functionality

#### Tasks:
1. **Create API Bridge Layer**
   ```
   apps/frontend/src/renderer/services/api-bridge.ts
   ```
   - Wrapper that can switch between Analytics API and ROI Engine API
   - Feature flags for gradual rollout
   - Response transformers for incompatible structures

2. **Update Environment Config**
   ```typescript
   // .env or config
   ANALYTICS_API_URL=http://localhost:8100
   ROI_ENGINE_API_URL=http://localhost:8002
   USE_ROI_ENGINE=partial  // 'none' | 'partial' | 'full'
   ```

3. **Create Type Adapters**
   ```
   apps/frontend/src/renderer/services/type-adapters.ts
   ```
   - `analyticsROIToEngineROI()` - Convert response structures
   - `analyticsArtifactToEngineArtifact()` - Convert artifact types

#### Files to Create:
- `services/api-bridge.ts`
- `services/type-adapters.ts`
- `services/api-config.ts`

---

### Phase M2: Health & Traces Migration (Week 1-2)
**Goal:** Migrate simplest endpoints with 1:1 mapping

#### Endpoints to Migrate:

| Analytics API | ROI Engine API | Complexity |
|--------------|----------------|------------|
| `checkHealth()` | `checkHealth()` | Low |
| `listTraces(params)` | `listTraces(params)` | Low |
| `getTrace(id)` | `getTrace(id)` | Low |
| `getSessionsForSpec(id)` | `listSessions({spec_id})` | Low |

#### Files to Update:
- `hooks/useAnalyticsQuery.ts` → Update `useAnalyticsHealth()`, `useTraceList()`, `useTraceDetail()`

#### Migration Pattern:
```typescript
// Before (Analytics API)
export function useAnalyticsHealth() {
  return useQuery({
    queryKey: ['analytics', 'health'],
    queryFn: analyticsApi.checkHealth,
  });
}

// After (ROI Engine via Bridge)
export function useAnalyticsHealth() {
  return useQuery({
    queryKey: ['analytics', 'health'],
    queryFn: () => apiBridge.health.check(), // Uses ROI Engine
  });
}
```

---

### Phase M3: ROI Calculations Migration (Week 2-3)
**Goal:** Migrate ROI endpoints with response transformation

#### Challenge: Different Response Structures

**Analytics API Response:**
```typescript
interface ROISummaryResponse {
  total_roi_percentage: number
  total_business_value_usd: number
  total_actual_cost_usd: number
  total_dev_hours_saved: number
  by_spec: ROIResponse[]
}
```

**ROI Engine Response:**
```typescript
interface ROISummary {
  total_value: number
  total_cost: number
  net_value: number
  roi_percentage: number
  artifact_count: number
  by_role: Record<Role, number>
  by_type: Record<string, number>
}
```

#### Adapter Function:
```typescript
// services/type-adapters.ts
export function adaptROISummary(
  engineResponse: ROIEngineSummary
): AnalyticsROISummary {
  return {
    total_roi_percentage: engineResponse.roi_percentage,
    total_business_value_usd: engineResponse.total_value,
    total_actual_cost_usd: engineResponse.total_cost,
    total_dev_hours_saved: estimateHoursFromValue(engineResponse.total_value),
    by_spec: [], // Would need additional query
    // Map other fields...
  };
}
```

#### Endpoints to Migrate:

| Analytics API | ROI Engine API | Adapter Needed |
|--------------|----------------|----------------|
| `getROISummary()` | `getROISummary()` | Yes - structure differs |
| `getROIForSpec(id)` | `getROIForSpec(id)` | Yes - structure differs |
| `getUnifiedROI()` | `getUnifiedROI()` | Yes - structure differs |
| `getValueBreakdown()` | `getValueBreakdown()` | Yes - params differ |

#### Files to Update:
- `hooks/useAnalyticsQuery.ts` → `useROISummary()`, `useROIForSpec()`, `useUnifiedROI()`
- `components/analytics/roi/LangfuseROIDashboard.tsx` → Already migrated ✅

---

### Phase M4: Artifacts Migration (Week 3-4)
**Goal:** Migrate artifact management with type mapping

#### Type Mapping Required:

**Analytics API Artifact:**
```typescript
interface Artifact {
  id: string
  type: string
  content: string
  value_usd: number
  created_at: string
  spec_id?: string
  trace_id?: string
}
```

**ROI Engine Artifact:**
```typescript
interface LocalArtifact {
  artifact_id: string
  artifact_type: string
  content: string
  calculated_value: number
  role: Role
  seniority: Seniority
  hourly_rate: number
  estimated_hours: number
  status: 'draft' | 'complete'
  quality_score: number
  created_at: string
}
```

#### Endpoints to Migrate:

| Analytics API | ROI Engine API | Notes |
|--------------|----------------|-------|
| `getLocalArtifacts()` | `listLocalArtifacts()` | Field mapping needed |
| `searchArtifacts()` | `searchArtifacts()` | Compatible |
| `getArtifactStatistics()` | `getArtifactStatistics()` | Compatible |
| `getArtifactTimeline()` | `getArtifactTimeline()` | Compatible |

#### Files to Update:
- `components/analytics/artifacts/ArtifactsPanel.tsx`
- `hooks/useAnalyticsQuery.ts` → artifact hooks

---

### Phase M5: Costs & Quality Migration (Week 4)
**Goal:** Migrate cost and quality endpoints

#### Endpoints to Migrate:

| Analytics API | ROI Engine API | Status |
|--------------|----------------|--------|
| `getCostSummary()` | `getDailyCosts()` | Adapt |
| `getCostsByModel()` | `getCostsByModel()` | Direct |
| `getCostsByAgent()` | `getCostsByAgent()` | Direct |
| `getQualityScores()` | `getQualityScores()` | Direct |
| `getQualityByAgent()` | `getQualityByAgent()` | Direct |

---

### Phase M6: Cost Avoidance & Forecasting (Week 4-5)
**Goal:** Migrate advanced analytics features

#### Endpoints to Migrate:

| Analytics API | ROI Engine API | Status |
|--------------|----------------|--------|
| `getCostAvoidanceSummary()` | `getCostAvoidanceSummary()` | Direct |
| `getCostAvoidanceByRole()` | `getCostAvoidanceByRole()` | Direct |
| `getForecastROI()` | `getForecastROI()` | Direct |
| `getForecastValue()` | `getForecastValue()` | Direct |
| `runScenarios()` | `runScenarios()` | Direct |

---

### Phase M7: Benchmarks Migration (Week 5)
**Goal:** Migrate benchmark comparison features

#### Endpoints to Migrate:

| Analytics API | ROI Engine API | Status |
|--------------|----------------|--------|
| `getProjectRankings()` | `compareProjects()` | Adapt |
| `getEfficiencyMetrics()` | `getEfficiencyMetrics()` | Direct |
| `compareSquadConfigs()` | `compareSquadConfigs()` | Direct |

#### Files to Update:
- `components/analytics/benchmarks/BenchmarkLeaderboard.tsx`

---

### Phase M8: Features Without ROI Engine Equivalents (Week 5-6)
**Goal:** Decide fate of features without equivalents

#### Options for Each Feature:

| Feature | Option A: Keep | Option B: Deprecate | Option C: Implement |
|---------|---------------|---------------------|---------------------|
| **Time Saved** | Keep on Analytics API | Remove from UI | Add to ROI Engine |
| **Satisfaction Surveys** | Keep on Analytics API | Remove from UI | Add to ROI Engine |

#### Recommendation:
- **Time Saved**: Keep on Analytics API - complex business logic, not directly related to artifact ROI
- **Satisfaction Surveys**: Keep on Analytics API - separate concern from ROI calculation

---

### Phase M9: Cleanup & Deprecation (Week 6)
**Goal:** Remove legacy code and finalize migration

#### Tasks:
1. Remove Analytics API calls from migrated components
2. Update CSP headers to remove port 8100 (if fully migrated)
3. Add deprecation warnings to Analytics API
4. Update documentation

#### Files to Potentially Remove:
- Parts of `services/analytics-api.ts` (migrated endpoints)
- Parts of `hooks/useAnalyticsQuery.ts` (migrated hooks)

---

## Component Migration Checklist

### Already Migrated ✅
- [x] `LangfuseROIDashboard.tsx` - Uses ROI Engine API

### To Migrate (Direct)
- [ ] Health checks
- [ ] Trace listing
- [ ] Session listing

### To Migrate (With Adapters)
- [ ] `ArtifactsPanel.tsx` - Need type mapping
- [ ] ROI hooks in `useAnalyticsQuery.ts` - Need response adapters
- [ ] `BenchmarkLeaderboard.tsx` - Need endpoint mapping

### To Keep on Analytics API
- [ ] `TimeSavedDashboard.tsx` - No ROI Engine equivalent
- [ ] `SatisfactionDashboard.tsx` - No ROI Engine equivalent
- [ ] `PostSpecSurvey.tsx` - No ROI Engine equivalent

### To Evaluate
- [ ] `CostAvoidancePanel.tsx` - ROI Engine has similar endpoints
- [ ] `ImpactForecastCard.tsx` - ROI Engine has forecasting

---

## API Bridge Implementation

### Proposed Structure:

```typescript
// services/api-bridge.ts

import * as analyticsApi from './analytics-api';
import * as roiEngineApi from './roi-engine-api';
import { adaptROISummary, adaptArtifact } from './type-adapters';

const config = {
  useROIEngine: process.env.USE_ROI_ENGINE || 'partial',
};

export const apiBridge = {
  health: {
    check: () => config.useROIEngine !== 'none'
      ? roiEngineApi.checkHealth()
      : analyticsApi.checkHealth(),
  },

  traces: {
    list: (params) => config.useROIEngine !== 'none'
      ? roiEngineApi.listTraces(params)
      : analyticsApi.listTraces(params),
    get: (id) => config.useROIEngine !== 'none'
      ? roiEngineApi.getTrace(id)
      : analyticsApi.getTrace(id),
  },

  roi: {
    summary: async (params) => {
      if (config.useROIEngine !== 'none') {
        const response = await roiEngineApi.getROISummary(params);
        return adaptROISummary(response);
      }
      return analyticsApi.getROISummary(params);
    },
  },

  // Features staying on Analytics API
  satisfaction: analyticsApi.satisfaction,
  timeSaved: analyticsApi.timeSaved,
};
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Response structure incompatibility | High | Create adapter layer |
| Missing features in ROI Engine | Medium | Keep Analytics API for those features |
| Breaking existing dashboards | High | Feature flags for gradual rollout |
| Performance regression | Medium | Monitor API response times |
| Type errors in TypeScript | Medium | Create comprehensive type adapters |

---

## Success Criteria

1. **Phase M1-M2 Complete:**
   - Health and traces work via ROI Engine
   - No visual changes to UI

2. **Phase M3-M4 Complete:**
   - ROI dashboard uses ROI Engine exclusively
   - Artifacts panel works with ROI Engine

3. **Phase M5-M7 Complete:**
   - All migrable features use ROI Engine
   - Analytics API only serves Time Saved and Satisfaction

4. **Phase M8-M9 Complete:**
   - Clear separation of concerns
   - Documentation updated
   - Deprecation notices in place

---

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| M1: Infrastructure | 3-4 days | None |
| M2: Health & Traces | 2-3 days | M1 |
| M3: ROI Calculations | 4-5 days | M1 |
| M4: Artifacts | 3-4 days | M1 |
| M5: Costs & Quality | 2-3 days | M1 |
| M6: Cost Avoidance | 2-3 days | M1 |
| M7: Benchmarks | 2-3 days | M1 |
| M8: Evaluate Remaining | 2-3 days | M2-M7 |
| M9: Cleanup | 2-3 days | M8 |

**Total Estimated Duration:** 4-6 weeks

---

## Next Steps

1. **Immediate:** Review this roadmap with team
2. **Week 1:** Implement Phase M1 (API Bridge)
3. **Ongoing:** Migrate in phases, validate each before proceeding
