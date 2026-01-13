/**
 * ROI Engine Query Hooks
 * ======================
 *
 * React Query hooks for fetching data from the ROI Engine API (port 8002).
 * Provides artifact-based ROI calculation using role-based valuation.
 */

import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import * as roiEngineApi from '../services/roi-engine-api';
import type {
  TraceQueryParams,
  ArtifactQueryParams,
  ArtifactSearchParams,
  LocalArtifactParams,
  ROIQueryParams,
  UnifiedROIParams,
  ROITrendsParams,
  CostQueryParams,
  ValueBreakdownParams,
  ActivityParams,
  TraceListResponse,
  TraceDetailResponse,
  SessionListResponse,
  ArtifactListResponse,
  ArtifactSearchResponse,
  LocalArtifactsListResponse,
  ROIResult,
  ROISummary,
  UnifiedROIResponse,
  ROITrendsResponse,
  DailyCostListResponse,
  BillingResponse,
  ValueBreakdownResponse,
  HealthCheckResponse,
  RecentActivityResponse,
  RateTableResponse,
  ArtifactTypesResponse,
  ArtifactValuePreview,
  Seniority,
} from '../services/roi-engine-api';

// =============================================================================
// Query Keys
// =============================================================================

export const roiEngineKeys = {
  all: ['roi-engine'] as const,

  // Health
  health: () => [...roiEngineKeys.all, 'health'] as const,

  // Traces
  traces: () => [...roiEngineKeys.all, 'traces'] as const,
  traceList: (params?: TraceQueryParams) =>
    [...roiEngineKeys.traces(), 'list', params] as const,
  traceDetail: (traceId: string) =>
    [...roiEngineKeys.traces(), 'detail', traceId] as const,

  // Sessions
  sessions: () => [...roiEngineKeys.all, 'sessions'] as const,
  sessionList: (limit?: number, offset?: number) =>
    [...roiEngineKeys.sessions(), 'list', limit, offset] as const,

  // Artifacts
  artifacts: () => [...roiEngineKeys.all, 'artifacts'] as const,
  artifactList: (params: ArtifactQueryParams) =>
    [...roiEngineKeys.artifacts(), 'list', params] as const,
  artifactDetail: (artifactId: string, projectDir: string) =>
    [...roiEngineKeys.artifacts(), 'detail', artifactId, projectDir] as const,
  artifactSearch: (params: ArtifactSearchParams) =>
    [...roiEngineKeys.artifacts(), 'search', params] as const,
  localArtifacts: (params: LocalArtifactParams) =>
    [...roiEngineKeys.artifacts(), 'local', params] as const,

  // ROI
  roi: () => [...roiEngineKeys.all, 'roi'] as const,
  roiForSpec: (specId: string, params: ROIQueryParams) =>
    [...roiEngineKeys.roi(), 'spec', specId, params] as const,
  roiSummary: (specId: string, params: ROIQueryParams) =>
    [...roiEngineKeys.roi(), 'summary', specId, params] as const,
  roiForTrace: (traceId: string, params: ROIQueryParams) =>
    [...roiEngineKeys.roi(), 'trace', traceId, params] as const,
  unifiedROI: (params: UnifiedROIParams) =>
    [...roiEngineKeys.roi(), 'unified', params] as const,
  roiTrends: (params: ROITrendsParams) =>
    [...roiEngineKeys.roi(), 'trends', params] as const,

  // Costs
  costs: () => [...roiEngineKeys.all, 'costs'] as const,
  dailyCosts: (params?: CostQueryParams) =>
    [...roiEngineKeys.costs(), 'daily', params] as const,
  billing: (params?: CostQueryParams) =>
    [...roiEngineKeys.costs(), 'billing', params] as const,

  // Value Breakdown
  valueBreakdown: (params: ValueBreakdownParams) =>
    [...roiEngineKeys.all, 'value-breakdown', params] as const,

  // Activity
  activity: () => [...roiEngineKeys.all, 'activity'] as const,
  recentActivity: (params: ActivityParams) =>
    [...roiEngineKeys.activity(), 'recent', params] as const,

  // Configuration
  config: () => [...roiEngineKeys.all, 'config'] as const,
  rateTable: () => [...roiEngineKeys.config(), 'rates'] as const,
  artifactTypes: () => [...roiEngineKeys.config(), 'artifact-types'] as const,
  artifactPreview: (artifactType: string, seniority?: Seniority, projectDir?: string) =>
    [...roiEngineKeys.config(), 'preview', artifactType, seniority, projectDir] as const,
  roles: () => [...roiEngineKeys.config(), 'roles'] as const,
};

// =============================================================================
// Health Hook
// =============================================================================

/**
 * Hook to check if the ROI Engine API is healthy
 */
export function useROIEngineHealth(options?: { enabled?: boolean }) {
  return useQuery<HealthCheckResponse>({
    queryKey: roiEngineKeys.health(),
    queryFn: roiEngineApi.checkHealth,
    // Check health every 30 seconds
    refetchInterval: 30 * 1000,
    // Don't retry health checks too aggressively
    retry: 1,
    enabled: options?.enabled !== false,
  });
}

// =============================================================================
// Trace Hooks
// =============================================================================

/**
 * Hook to list traces from Langfuse via ROI Engine
 */
export function useROIEngineTraces(
  params?: TraceQueryParams,
  options?: { enabled?: boolean }
) {
  return useQuery<TraceListResponse>({
    queryKey: roiEngineKeys.traceList(params),
    queryFn: () => roiEngineApi.listTraces(params),
    enabled: options?.enabled !== false,
  });
}

/**
 * Hook to get detailed trace information
 */
export function useROIEngineTrace(
  traceId: string | null,
  options?: { enabled?: boolean }
) {
  return useQuery<TraceDetailResponse>({
    queryKey: roiEngineKeys.traceDetail(traceId || ''),
    queryFn: () => roiEngineApi.getTrace(traceId!),
    enabled: !!traceId && options?.enabled !== false,
  });
}

// =============================================================================
// Session Hooks
// =============================================================================

/**
 * Hook to list sessions
 */
export function useROIEngineSessions(
  limit?: number,
  offset?: number,
  options?: { enabled?: boolean }
) {
  return useQuery<SessionListResponse>({
    queryKey: roiEngineKeys.sessionList(limit, offset),
    queryFn: () => roiEngineApi.listSessions(limit, offset),
    enabled: options?.enabled !== false,
  });
}

// =============================================================================
// Artifact Hooks
// =============================================================================

/**
 * Hook to list artifacts with role-based valuation
 */
export function useROIEngineArtifacts(
  params: ArtifactQueryParams,
  options?: { enabled?: boolean }
) {
  return useQuery<ArtifactListResponse>({
    queryKey: roiEngineKeys.artifactList(params),
    queryFn: () => roiEngineApi.listArtifacts(params),
    enabled: !!params.project_dir && options?.enabled !== false,
  });
}

/**
 * Hook to search artifacts with full-text query
 */
export function useROIEngineArtifactSearch(
  params: ArtifactSearchParams,
  options?: { enabled?: boolean }
) {
  return useQuery<ArtifactSearchResponse>({
    queryKey: roiEngineKeys.artifactSearch(params),
    queryFn: () => roiEngineApi.searchArtifacts(params),
    enabled: !!params.project_dir && !!params.query && options?.enabled !== false,
  });
}

/**
 * Hook to list local artifacts from storage
 */
export function useROIEngineLocalArtifacts(
  params: LocalArtifactParams,
  options?: { enabled?: boolean }
) {
  return useQuery<LocalArtifactsListResponse>({
    queryKey: roiEngineKeys.localArtifacts(params),
    queryFn: () => roiEngineApi.listLocalArtifacts(params),
    enabled: !!params.project_dir && options?.enabled !== false,
  });
}

// =============================================================================
// ROI Hooks
// =============================================================================

/**
 * Hook to get ROI for a specific spec
 */
export function useROIEngineSpecROI(
  specId: string | null,
  params: ROIQueryParams,
  options?: { enabled?: boolean }
) {
  return useQuery<ROIResult>({
    queryKey: roiEngineKeys.roiForSpec(specId || '', params),
    queryFn: () => roiEngineApi.getROIForSpec(specId!, params),
    enabled: !!specId && !!params.project_dir && options?.enabled !== false,
  });
}

/**
 * Hook to get ROI summary for a specific spec
 */
export function useROIEngineSummary(
  specId: string | null,
  params: ROIQueryParams,
  options?: { enabled?: boolean }
) {
  return useQuery<ROISummary>({
    queryKey: roiEngineKeys.roiSummary(specId || '', params),
    queryFn: () => roiEngineApi.getROISummary(specId!, params),
    enabled: !!specId && !!params.project_dir && options?.enabled !== false,
  });
}

/**
 * Hook to get ROI for a specific trace
 */
export function useROIEngineTraceROI(
  traceId: string | null,
  params: ROIQueryParams,
  options?: { enabled?: boolean }
) {
  return useQuery<ROIResult>({
    queryKey: roiEngineKeys.roiForTrace(traceId || '', params),
    queryFn: () => roiEngineApi.getROIForTrace(traceId!, params),
    enabled: !!traceId && !!params.project_dir && options?.enabled !== false,
  });
}

/**
 * Hook to get unified ROI across all sources
 *
 * This is the main hook for dashboard aggregated ROI metrics.
 */
export function useROIEngineUnified(
  params: UnifiedROIParams,
  options?: { enabled?: boolean; staleTime?: number }
) {
  return useQuery<UnifiedROIResponse>({
    queryKey: roiEngineKeys.unifiedROI(params),
    queryFn: () => roiEngineApi.getUnifiedROI(params),
    enabled: !!params.project_dir && options?.enabled !== false,
    staleTime: options?.staleTime ?? 60 * 1000, // 1 minute default
  });
}

/**
 * Hook to get ROI trends over time
 */
export function useROIEngineTrends(
  params: ROITrendsParams,
  options?: { enabled?: boolean }
) {
  return useQuery<ROITrendsResponse>({
    queryKey: roiEngineKeys.roiTrends(params),
    queryFn: () => roiEngineApi.getROITrends(params),
    enabled: !!params.project_dir && options?.enabled !== false,
  });
}

// =============================================================================
// Cost Hooks
// =============================================================================

/**
 * Hook to get daily cost breakdown
 */
export function useROIEngineDailyCosts(
  params?: CostQueryParams,
  options?: { enabled?: boolean }
) {
  return useQuery<DailyCostListResponse>({
    queryKey: roiEngineKeys.dailyCosts(params),
    queryFn: () => roiEngineApi.getDailyCosts(params),
    enabled: options?.enabled !== false,
  });
}

/**
 * Hook to get billing summary
 */
export function useROIEngineBilling(
  params?: CostQueryParams,
  options?: { enabled?: boolean }
) {
  return useQuery<BillingResponse>({
    queryKey: roiEngineKeys.billing(params),
    queryFn: () => roiEngineApi.getBilling(params),
    enabled: options?.enabled !== false,
  });
}

// =============================================================================
// Value Breakdown Hook
// =============================================================================

/**
 * Hook to get detailed value breakdown by dimension
 *
 * Returns value grouped by:
 * - Role (developer, qa, architect, etc.)
 * - Type (diagram, code_example, spec_document, etc.)
 * - Seniority (junior, mid, senior, etc.)
 * - Spec
 */
export function useROIEngineValueBreakdown(
  params: ValueBreakdownParams,
  options?: { enabled?: boolean }
) {
  return useQuery<ValueBreakdownResponse>({
    queryKey: roiEngineKeys.valueBreakdown(params),
    queryFn: () => roiEngineApi.getValueBreakdown(params),
    enabled: !!params.project_dir && options?.enabled !== false,
  });
}

// =============================================================================
// Activity Hook
// =============================================================================

/**
 * Hook to get recent activity events
 */
export function useROIEngineRecentActivity(
  params: ActivityParams,
  options?: { enabled?: boolean }
) {
  return useQuery<RecentActivityResponse>({
    queryKey: roiEngineKeys.recentActivity(params),
    queryFn: () => roiEngineApi.getRecentActivity(params),
    enabled: !!params.project_dir && options?.enabled !== false,
  });
}

// =============================================================================
// Configuration Hooks
// =============================================================================

/**
 * Hook to get rate table (hourly rates by role and seniority)
 */
export function useROIEngineRateTable(options?: { enabled?: boolean }) {
  return useQuery<RateTableResponse>({
    queryKey: roiEngineKeys.rateTable(),
    queryFn: roiEngineApi.getRateTable,
    enabled: options?.enabled !== false,
    // Rate table changes rarely, cache for longer
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to get all artifact types with their role mappings
 */
export function useROIEngineArtifactTypes(options?: { enabled?: boolean }) {
  return useQuery<ArtifactTypesResponse>({
    queryKey: roiEngineKeys.artifactTypes(),
    queryFn: roiEngineApi.getArtifactTypes,
    enabled: options?.enabled !== false,
    // Artifact types change rarely, cache for longer
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to preview artifact value calculation
 */
export function useROIEngineArtifactPreview(
  artifactType: string,
  seniority?: Seniority,
  projectDir?: string,
  options?: { enabled?: boolean }
) {
  return useQuery<ArtifactValuePreview>({
    queryKey: roiEngineKeys.artifactPreview(artifactType, seniority, projectDir),
    queryFn: () => roiEngineApi.previewArtifactValue(artifactType, seniority, projectDir),
    enabled: !!artifactType && options?.enabled !== false,
  });
}

/**
 * Hook to get available roles
 */
export function useROIEngineRoles(options?: { enabled?: boolean }) {
  return useQuery<{ roles: Array<{ role: string; description: string }> }>({
    queryKey: roiEngineKeys.roles(),
    queryFn: roiEngineApi.getRoles,
    enabled: options?.enabled !== false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// =============================================================================
// Dashboard Data Hook (Combines Multiple Queries)
// =============================================================================

/**
 * Combined hook that fetches all dashboard data in parallel.
 *
 * Use this when you need unified ROI, trends, and value breakdown together.
 */
export function useROIEngineDashboard(
  projectDir: string,
  options?: {
    enabled?: boolean;
    dateRange?: { from?: string; to?: string };
  }
) {
  const unifiedROI = useROIEngineUnified(
    {
      project_dir: projectDir,
      from_date: options?.dateRange?.from,
      to_date: options?.dateRange?.to,
    },
    { enabled: !!projectDir && options?.enabled !== false }
  );

  const trends = useROIEngineTrends(
    { project_dir: projectDir },
    { enabled: !!projectDir && options?.enabled !== false }
  );

  const valueBreakdown = useROIEngineValueBreakdown(
    { project_dir: projectDir },
    { enabled: !!projectDir && options?.enabled !== false }
  );

  const recentActivity = useROIEngineRecentActivity(
    { project_dir: projectDir, limit: 10 },
    { enabled: !!projectDir && options?.enabled !== false }
  );

  const health = useROIEngineHealth({ enabled: options?.enabled !== false });

  return {
    unifiedROI,
    trends,
    valueBreakdown,
    recentActivity,
    health,
    isLoading:
      unifiedROI.isLoading ||
      trends.isLoading ||
      valueBreakdown.isLoading ||
      recentActivity.isLoading,
    isError:
      unifiedROI.isError ||
      trends.isError ||
      valueBreakdown.isError ||
      recentActivity.isError,
  };
}

// =============================================================================
// Export Types
// =============================================================================

export type {
  TraceQueryParams,
  ArtifactQueryParams,
  ArtifactSearchParams,
  LocalArtifactParams,
  ROIQueryParams,
  UnifiedROIParams,
  ROITrendsParams,
  CostQueryParams,
  ValueBreakdownParams,
  ActivityParams,
  TraceListResponse,
  TraceDetailResponse,
  SessionListResponse,
  ArtifactListResponse,
  ArtifactSearchResponse,
  LocalArtifactsListResponse,
  ROIResult,
  ROISummary,
  UnifiedROIResponse,
  ROITrendsResponse,
  DailyCostListResponse,
  BillingResponse,
  ValueBreakdownResponse,
  HealthCheckResponse,
  RecentActivityResponse,
  RateTableResponse,
  ArtifactTypesResponse,
  ArtifactValuePreview,
  Role,
  Seniority,
} from '../services/roi-engine-api';
