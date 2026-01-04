/**
 * Analytics Query Hooks
 * =====================
 *
 * React Query hooks for fetching analytics data from the FastAPI service.
 * Replaces IPC-based data fetching with HTTP calls to Langfuse-backed API.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as analyticsApi from '../services/analytics-api';
import type {
  TraceQueryParams,
  DateRangeParams,
  ROISummaryParams,
  UsageSummaryParams,
  TraceListResponse,
  TraceDetailResponse,
  SessionListResponse,
  ROISummaryResponse,
  ROIResponse,
  CostSummaryResponse,
  ScoreResponse,
  UsageSummaryResponse,
  HealthStatusResponse,
  HourlyMetricsResponse,
  ErrorMetricsResponse,
  RecentActivityResponse,
  UnifiedROIResponse,
  UnifiedROIParams,
} from '../services/analytics-api';
import type {
  ArtifactSearchParams,
  ArtifactStatistics,
  ArtifactTimelineResponse,
  LocalArtifactsResponse,
} from '../../shared/types/analytics-v2';

// =============================================================================
// Query Keys
// =============================================================================

export const analyticsKeys = {
  all: ['analytics'] as const,
  health: () => [...analyticsKeys.all, 'health'] as const,
  traces: () => [...analyticsKeys.all, 'traces'] as const,
  traceList: (params?: TraceQueryParams) => [...analyticsKeys.traces(), 'list', params] as const,
  traceDetail: (traceId: string) => [...analyticsKeys.traces(), 'detail', traceId] as const,
  sessions: () => [...analyticsKeys.all, 'sessions'] as const,
  sessionDetail: (specId: string) => [...analyticsKeys.sessions(), specId] as const,
  roi: () => [...analyticsKeys.all, 'roi'] as const,
  roiSummary: (params?: ROISummaryParams) => [...analyticsKeys.roi(), 'summary', params] as const,
  roiSpec: (specId: string) => [...analyticsKeys.roi(), 'spec', specId] as const,
  roiUnified: (params?: UnifiedROIParams) => [...analyticsKeys.roi(), 'unified', params] as const,
  costs: () => [...analyticsKeys.all, 'costs'] as const,
  costSummary: (params?: DateRangeParams) => [...analyticsKeys.costs(), 'summary', params] as const,
  scores: () => [...analyticsKeys.all, 'scores'] as const,
  scoreList: (params?: { trace_id?: string; name?: string; limit?: number }) =>
    [...analyticsKeys.scores(), 'list', params] as const,
  usage: () => [...analyticsKeys.all, 'usage'] as const,
  usageSummary: (params?: UsageSummaryParams) => [...analyticsKeys.usage(), 'summary', params] as const,
  healthStatus: () => [...analyticsKeys.all, 'healthStatus'] as const,
  hourlyMetrics: (hours?: number, project_id?: string) => [...analyticsKeys.all, 'hourlyMetrics', hours, project_id] as const,
  errorMetrics: (hours?: number, project_id?: string) => [...analyticsKeys.all, 'errorMetrics', hours, project_id] as const,
  recentActivity: (limit?: number) => [...analyticsKeys.all, 'recentActivity', limit] as const,
  // Artifact keys
  artifacts: () => [...analyticsKeys.all, 'artifacts'] as const,
  artifactSearch: (projectPath: string, params?: ArtifactSearchParams) =>
    [...analyticsKeys.artifacts(), 'search', projectPath, params] as const,
  artifactStatistics: (projectPath: string, fromDate?: string, toDate?: string) =>
    [...analyticsKeys.artifacts(), 'statistics', projectPath, fromDate, toDate] as const,
  artifactTimeline: (projectPath: string, granularity?: string, fromDate?: string, toDate?: string) =>
    [...analyticsKeys.artifacts(), 'timeline', projectPath, granularity, fromDate, toDate] as const,
};

// =============================================================================
// Health Check Hook
// =============================================================================

/**
 * Hook to check if the analytics API is healthy and Langfuse is configured
 */
export function useAnalyticsHealth() {
  return useQuery({
    queryKey: analyticsKeys.health(),
    queryFn: analyticsApi.checkHealth,
    // Check health every 30 seconds
    refetchInterval: 30 * 1000,
    // Don't retry health checks too aggressively
    retry: 1,
  });
}

// =============================================================================
// Trace Hooks
// =============================================================================

/**
 * Hook to list traces with optional filtering
 */
export function useTraceList(params?: TraceQueryParams, options?: { enabled?: boolean }) {
  return useQuery<TraceListResponse>({
    queryKey: analyticsKeys.traceList(params),
    queryFn: () => analyticsApi.listTraces(params),
    enabled: options?.enabled !== false,
  });
}

/**
 * Hook to get detailed trace information
 */
export function useTraceDetail(traceId: string | null, options?: { enabled?: boolean }) {
  return useQuery<TraceDetailResponse>({
    queryKey: analyticsKeys.traceDetail(traceId || ''),
    queryFn: () => analyticsApi.getTrace(traceId!),
    enabled: !!traceId && options?.enabled !== false,
  });
}

// =============================================================================
// Session Hooks
// =============================================================================

/**
 * Hook to get all sessions for a specific spec
 */
export function useSessionsForSpec(specId: string | null, options?: { enabled?: boolean }) {
  return useQuery<SessionListResponse>({
    queryKey: analyticsKeys.sessionDetail(specId || ''),
    queryFn: () => analyticsApi.getSessionsForSpec(specId!),
    enabled: !!specId && options?.enabled !== false,
  });
}

// =============================================================================
// ROI Hooks
// =============================================================================

/**
 * Hook to get aggregated ROI summary for a specific project
 *
 * IMPORTANT: Always pass project_id to get accurate data for your project only.
 * Without project_id, data from ALL projects will be aggregated.
 */
export function useROISummary(params?: ROISummaryParams, options?: { enabled?: boolean }) {
  return useQuery<ROISummaryResponse>({
    queryKey: analyticsKeys.roiSummary(params),
    queryFn: () => analyticsApi.getROISummary(params),
    enabled: options?.enabled !== false,
    // ROI data changes less frequently
    staleTime: 60 * 1000,
  });
}

/**
 * Hook to get ROI metrics for a specific spec
 */
export function useROIForSpec(specId: string | null, options?: { enabled?: boolean }) {
  return useQuery<ROIResponse>({
    queryKey: analyticsKeys.roiSpec(specId || ''),
    queryFn: () => analyticsApi.getROIForSpec(specId!),
    enabled: !!specId && options?.enabled !== false,
  });
}

/**
 * Hook to get unified ROI summary across all feature types
 *
 * Returns comprehensive ROI data including:
 * - Total ROI across all Auto-Claude features
 * - Value breakdown by type (execution, decision, prevention, knowledge)
 * - Breakdown by feature type (ideation, roadmap, spec, build, github, insights)
 */
export function useUnifiedROI(params?: UnifiedROIParams, options?: { enabled?: boolean }) {
  return useQuery<UnifiedROIResponse>({
    queryKey: analyticsKeys.roiUnified(params),
    queryFn: () => analyticsApi.getUnifiedROI(params),
    enabled: options?.enabled !== false,
    // Unified ROI data changes less frequently
    staleTime: 60 * 1000,
  });
}

// =============================================================================
// Cost Hooks
// =============================================================================

/**
 * Hook to get cost summary for a time period
 */
export function useCostSummary(params?: DateRangeParams, options?: { enabled?: boolean }) {
  return useQuery<CostSummaryResponse>({
    queryKey: analyticsKeys.costSummary(params),
    queryFn: () => analyticsApi.getCostSummary(params),
    enabled: options?.enabled !== false,
  });
}

// =============================================================================
// Score Hooks
// =============================================================================

/**
 * Hook to list scores with optional filtering
 */
export function useScoreList(
  params?: { trace_id?: string; name?: string; limit?: number },
  options?: { enabled?: boolean }
) {
  return useQuery<ScoreResponse[]>({
    queryKey: analyticsKeys.scoreList(params),
    queryFn: () => analyticsApi.listScores(params),
    enabled: options?.enabled !== false,
  });
}

// =============================================================================
// Usage Summary Hook (for charts)
// =============================================================================

/**
 * Hook to get comprehensive usage analytics for dashboard charts
 *
 * Returns pre-aggregated data for:
 * - Cost Over Time chart
 * - Tokens By Spec chart
 * - Model Distribution chart
 * - Session Duration by Phase chart
 * - Feature Usage breakdown
 *
 * @param params - Query parameters including project_id for data isolation
 * @param options - React Query options
 */
export function useUsageSummary(params?: UsageSummaryParams, options?: { enabled?: boolean }) {
  return useQuery<UsageSummaryResponse>({
    queryKey: analyticsKeys.usageSummary(params),
    queryFn: () => analyticsApi.getUsageSummary(params),
    enabled: options?.enabled !== false,
    // Usage data changes less frequently, cache for 60 seconds
    staleTime: 60 * 1000,
  });
}

// =============================================================================
// Invalidation Helpers
// =============================================================================

/**
 * Hook to get query invalidation functions
 */
export function useAnalyticsInvalidation() {
  const queryClient = useQueryClient();

  return {
    /**
     * Invalidate all analytics data
     */
    invalidateAll: () => queryClient.invalidateQueries({ queryKey: analyticsKeys.all }),

    /**
     * Invalidate all trace data
     */
    invalidateTraces: () => queryClient.invalidateQueries({ queryKey: analyticsKeys.traces() }),

    /**
     * Invalidate a specific trace
     */
    invalidateTrace: (traceId: string) =>
      queryClient.invalidateQueries({ queryKey: analyticsKeys.traceDetail(traceId) }),

    /**
     * Invalidate all session data
     */
    invalidateSessions: () => queryClient.invalidateQueries({ queryKey: analyticsKeys.sessions() }),

    /**
     * Invalidate sessions for a specific spec
     */
    invalidateSession: (specId: string) =>
      queryClient.invalidateQueries({ queryKey: analyticsKeys.sessionDetail(specId) }),

    /**
     * Invalidate all ROI data
     */
    invalidateROI: () => queryClient.invalidateQueries({ queryKey: analyticsKeys.roi() }),

    /**
     * Invalidate all cost data
     */
    invalidateCosts: () => queryClient.invalidateQueries({ queryKey: analyticsKeys.costs() }),

    /**
     * Invalidate all score data
     */
    invalidateScores: () => queryClient.invalidateQueries({ queryKey: analyticsKeys.scores() }),

    /**
     * Invalidate all usage data
     */
    invalidateUsage: () => queryClient.invalidateQueries({ queryKey: analyticsKeys.usage() }),

    /**
     * Invalidate all artifact data
     */
    invalidateArtifacts: () => queryClient.invalidateQueries({ queryKey: analyticsKeys.artifacts() }),
  };
}

// =============================================================================
// Combined Data Hook (for dashboard)
// =============================================================================

/**
 * Hook to fetch all dashboard data in parallel
 *
 * @param projectId - Project ID for data isolation (IMPORTANT: pass this for accurate data)
 * @param dateRange - Optional date range filter
 */
export function useDashboardData(projectId?: string, dateRange?: DateRangeParams) {
  const health = useAnalyticsHealth();
  const roiParams: ROISummaryParams = { project_id: projectId, ...dateRange };
  const roiSummary = useROISummary(roiParams, { enabled: health.data?.langfuse_configured });
  const costSummary = useCostSummary(dateRange, { enabled: health.data?.langfuse_configured });
  const recentTraces = useTraceList({ limit: 10 }, { enabled: health.data?.langfuse_configured });

  const isLoading = health.isLoading || roiSummary.isLoading || costSummary.isLoading || recentTraces.isLoading;
  const isError = health.isError || roiSummary.isError || costSummary.isError || recentTraces.isError;
  const isConfigured = health.data?.langfuse_configured ?? false;

  return {
    health: health.data,
    roiSummary: roiSummary.data,
    costSummary: costSummary.data,
    recentTraces: recentTraces.data,
    isLoading,
    isError,
    isConfigured,
    errors: {
      health: health.error,
      roi: roiSummary.error,
      cost: costSummary.error,
      traces: recentTraces.error,
    },
    refetch: () => {
      health.refetch();
      roiSummary.refetch();
      costSummary.refetch();
      recentTraces.refetch();
    },
  };
}

// =============================================================================
// Health Status Hook (detailed)
// =============================================================================

/**
 * Hook to get detailed health status of all services
 */
export function useHealthStatus(options?: { enabled?: boolean }) {
  return useQuery<HealthStatusResponse, Error>({
    queryKey: analyticsKeys.healthStatus(),
    queryFn: analyticsApi.getHealthStatus,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // 1 minute
    ...options,
  });
}

// =============================================================================
// Hourly Metrics Hook
// =============================================================================

/**
 * Hook to get metrics aggregated by hour
 * @param hours - Number of hours to fetch
 * @param project_id - Filter by project ID for data isolation
 * @param options - Query options
 */
export function useHourlyMetrics(hours: number = 24, project_id?: string, options?: { enabled?: boolean }) {
  return useQuery<HourlyMetricsResponse, Error>({
    queryKey: analyticsKeys.hourlyMetrics(hours, project_id),
    queryFn: () => analyticsApi.getHourlyMetrics(hours, project_id),
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

// =============================================================================
// Error Metrics Hook
// =============================================================================

/**
 * Hook to get error metrics and breakdown
 * @param hours - Number of hours to fetch
 * @param project_id - Filter by project ID for data isolation
 * @param options - Query options
 */
export function useErrorMetrics(hours: number = 24, project_id?: string, options?: { enabled?: boolean }) {
  return useQuery<ErrorMetricsResponse, Error>({
    queryKey: analyticsKeys.errorMetrics(hours, project_id),
    queryFn: () => analyticsApi.getErrorMetrics(hours, project_id),
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

// =============================================================================
// Recent Activity Hook
// =============================================================================

/**
 * Hook to get recent spec activity events
 */
export function useRecentActivity(limit: number = 10, options?: { enabled?: boolean }) {
  return useQuery<RecentActivityResponse, Error>({
    queryKey: analyticsKeys.recentActivity(limit),
    queryFn: () => analyticsApi.getRecentActivity(limit),
    staleTime: 30 * 1000, // 30 seconds
    ...options,
  });
}

// =============================================================================
// Artifact Hooks (Rich Artifact Data)
// =============================================================================

/**
 * Hook to search artifacts with rich filtering
 *
 * Supports filtering by:
 * - Full-text search across content
 * - Artifact types (roadmap_feature, security_issue, etc.)
 * - Priority levels (must, should, could, wont)
 * - Quality flags (has_rationale, has_acceptance_criteria, etc.)
 * - Value range (min_value, max_value)
 * - Agent types
 * - Date range
 *
 * @param projectPath - Path to the project
 * @param params - Search and filter parameters
 * @param options - React Query options
 */
export function useArtifactSearch(
  projectPath: string | null,
  params?: ArtifactSearchParams,
  options?: { enabled?: boolean }
) {
  return useQuery<LocalArtifactsResponse, Error>({
    queryKey: analyticsKeys.artifactSearch(projectPath || '', params),
    queryFn: () => analyticsApi.searchArtifacts(projectPath!, params),
    enabled: !!projectPath && options?.enabled !== false,
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to get artifact statistics with aggregations
 *
 * Returns:
 * - Total count and value
 * - Breakdown by type, agent, priority, tab
 * - Quality metrics (with_rationale, with_acceptance_criteria, etc.)
 * - Average value per artifact
 * - Value distribution by type and priority
 *
 * @param projectPath - Path to the project
 * @param fromDate - Optional start date (ISO format)
 * @param toDate - Optional end date (ISO format)
 * @param options - React Query options
 */
export function useArtifactStatistics(
  projectPath: string | null,
  fromDate?: string,
  toDate?: string,
  options?: { enabled?: boolean }
) {
  return useQuery<ArtifactStatistics, Error>({
    queryKey: analyticsKeys.artifactStatistics(projectPath || '', fromDate, toDate),
    queryFn: () => analyticsApi.getArtifactStatistics(projectPath!, fromDate, toDate),
    enabled: !!projectPath && options?.enabled !== false,
    staleTime: 60 * 1000, // 1 minute (stats change less frequently)
  });
}

/**
 * Hook to get artifact timeline data for visualization
 *
 * Returns time-series data with:
 * - Count and value per period
 * - Breakdown by type and agent
 * - Configurable granularity (hour, day, week)
 *
 * @param projectPath - Path to the project
 * @param granularity - Time bucket size: 'hour' | 'day' | 'week'
 * @param fromDate - Optional start date (ISO format)
 * @param toDate - Optional end date (ISO format)
 * @param options - React Query options
 */
export function useArtifactTimeline(
  projectPath: string | null,
  granularity: 'hour' | 'day' | 'week' = 'day',
  fromDate?: string,
  toDate?: string,
  options?: { enabled?: boolean }
) {
  return useQuery<ArtifactTimelineResponse, Error>({
    queryKey: analyticsKeys.artifactTimeline(projectPath || '', granularity, fromDate, toDate),
    queryFn: () => analyticsApi.getArtifactTimeline(projectPath!, granularity, fromDate, toDate),
    enabled: !!projectPath && options?.enabled !== false,
    staleTime: 60 * 1000, // 1 minute
  });
}
