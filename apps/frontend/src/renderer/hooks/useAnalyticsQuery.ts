/**
 * Analytics Query Hooks
 * =====================
 *
 * React Query hooks for fetching analytics data.
 * Routes to ROI Engine API (port 8002) by default with fallback to Analytics API (port 8100).
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as analyticsApi from '../services/analytics-api';
import { apiBridge, type BridgeContext } from '../services/api-bridge';
import { useProjectStore } from '../stores/project-store';

// Helper hook to get bridge context from current project
function useBridgeContext(): BridgeContext | undefined {
  const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
  const activeProjectId = useProjectStore((state) => state.activeProjectId);
  const projects = useProjectStore((state) => state.projects);

  const projectId = activeProjectId || selectedProjectId;
  const project = projects.find((p) => p.id === projectId);

  if (!project?.path) {
    return undefined;
  }

  return {
    projectDir: project.path,
    projectId: project.id,
  };
}
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
  // Cost avoidance keys
  costAvoidance: () => [...analyticsKeys.all, 'costAvoidance'] as const,
  costAvoidanceSummary: (projectPath: string, days?: number, specId?: string) =>
    [...analyticsKeys.costAvoidance(), 'summary', projectPath, days, specId] as const,
  costAvoidanceEvents: (projectPath: string, params?: analyticsApi.CostAvoidanceEventsParams) =>
    [...analyticsKeys.costAvoidance(), 'events', projectPath, params] as const,
  costAvoidanceTrend: (projectPath: string, params?: analyticsApi.CostAvoidanceTrendParams) =>
    [...analyticsKeys.costAvoidance(), 'trend', projectPath, params] as const,
  // Benchmark keys (Module 6)
  benchmarks: () => [...analyticsKeys.all, 'benchmarks'] as const,
  projectRankings: (params?: analyticsApi.ProjectRankingsParams) =>
    [...analyticsKeys.benchmarks(), 'rankings', params] as const,
  bestPractices: (params?: analyticsApi.BestPracticesParams) =>
    [...analyticsKeys.benchmarks(), 'best-practices', params] as const,
  improvementSuggestions: (projectId: string) =>
    [...analyticsKeys.benchmarks(), 'suggestions', projectId] as const,
  percentileComparison: (projectId: string, params?: analyticsApi.PercentileComparisonParams) =>
    [...analyticsKeys.benchmarks(), 'percentile', projectId, params] as const,
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
    queryFn: () => apiBridge.health.check(),
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
    queryFn: () => apiBridge.traces.list(params),
    enabled: options?.enabled !== false,
  });
}

/**
 * Hook to get detailed trace information
 */
export function useTraceDetail(traceId: string | null, options?: { enabled?: boolean }) {
  return useQuery<TraceDetailResponse>({
    queryKey: analyticsKeys.traceDetail(traceId || ''),
    queryFn: () => apiBridge.traces.get(traceId!),
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
    queryFn: () => apiBridge.sessions.getForSpec(specId!),
    enabled: !!specId && options?.enabled !== false,
  });
}

// =============================================================================
// ROI Hooks
// =============================================================================

/**
 * Hook to get aggregated ROI summary for a specific project
 *
 * Uses ROI Engine API when project context is available.
 */
export function useROISummary(params?: ROISummaryParams, options?: { enabled?: boolean }) {
  const context = useBridgeContext();
  return useQuery<ROISummaryResponse>({
    queryKey: analyticsKeys.roiSummary(params),
    queryFn: () => apiBridge.roi.getSummary(params, context),
    enabled: options?.enabled !== false,
    // ROI data changes less frequently
    staleTime: 60 * 1000,
  });
}

/**
 * Hook to get ROI metrics for a specific spec
 */
export function useROIForSpec(specId: string | null, options?: { enabled?: boolean }) {
  const context = useBridgeContext();
  return useQuery<ROIResponse>({
    queryKey: analyticsKeys.roiSpec(specId || ''),
    queryFn: () => apiBridge.roi.getForSpec(specId!, context),
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
  const context = useBridgeContext();
  return useQuery<UnifiedROIResponse>({
    queryKey: analyticsKeys.roiUnified(params),
    queryFn: () => apiBridge.roi.getUnified(params, context),
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
    queryFn: () => apiBridge.costs.getSummary(params),
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
    queryFn: () => apiBridge.scores.list(params),
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
  const context = useBridgeContext();
  return useQuery<UsageSummaryResponse>({
    queryKey: analyticsKeys.usageSummary(params),
    queryFn: () => apiBridge.usage.getSummary(params, context),
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
    queryFn: () => apiBridge.health.getStatus(),
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
    queryFn: () => apiBridge.metrics.getHourly(hours, project_id),
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
    queryFn: () => apiBridge.metrics.getErrors(hours, project_id),
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
  const context = useBridgeContext();
  return useQuery<RecentActivityResponse, Error>({
    queryKey: analyticsKeys.recentActivity(limit),
    queryFn: () => apiBridge.activity.getRecent(limit, context),
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
    queryFn: () => apiBridge.artifacts.searchByPath(projectPath!, params),
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
    queryFn: () => apiBridge.artifacts.getStatisticsByPath(projectPath!, fromDate, toDate),
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
    queryFn: () => apiBridge.artifacts.getTimeline(projectPath!, granularity, fromDate, toDate),
    enabled: !!projectPath && options?.enabled !== false,
    staleTime: 60 * 1000, // 1 minute
  });
}

// =============================================================================
// Cost Avoidance Hooks
// =============================================================================

/**
 * Hook to get cost avoidance summary with aggregations
 *
 * Returns:
 * - Total cost avoided
 * - Event count
 * - Breakdown by type, severity, and detector
 * - Average confidence
 * - Recent events list
 *
 * @param projectPath - Path to the project
 * @param params - Optional filter parameters (days, spec_id)
 * @param options - React Query options
 */
export function useCostAvoidanceSummary(
  projectPath: string | null,
  params?: analyticsApi.CostAvoidanceSummaryParams,
  options?: { enabled?: boolean }
) {
  return useQuery<analyticsApi.CostAvoidanceSummary, Error>({
    queryKey: analyticsKeys.costAvoidanceSummary(projectPath || '', params?.days, params?.spec_id),
    queryFn: () => apiBridge.costAvoidance.getSummaryByPath(projectPath!, params),
    enabled: !!projectPath && options?.enabled !== false,
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to list cost avoidance events with filtering
 *
 * Supports filtering by:
 * - Number of days
 * - Event type
 * - Severity level
 * - Spec ID
 *
 * @param projectPath - Path to the project
 * @param params - Filter parameters
 * @param options - React Query options
 */
export function useCostAvoidanceEvents(
  projectPath: string | null,
  params?: analyticsApi.CostAvoidanceEventsParams,
  options?: { enabled?: boolean }
) {
  return useQuery<analyticsApi.CostAvoidanceEventsListResponse, Error>({
    queryKey: analyticsKeys.costAvoidanceEvents(projectPath || '', params),
    queryFn: () => apiBridge.costAvoidance.getEventsByPath(projectPath!, params),
    enabled: !!projectPath && options?.enabled !== false,
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to get cost avoidance trend data for visualization
 *
 * Returns time-series data with:
 * - Cost avoided per period
 * - Event count per period
 * - Breakdown by type
 *
 * @param projectPath - Path to the project
 * @param params - Trend parameters (days, granularity)
 * @param options - React Query options
 */
export function useCostAvoidanceTrend(
  projectPath: string | null,
  params?: analyticsApi.CostAvoidanceTrendParams,
  options?: { enabled?: boolean }
) {
  return useQuery<analyticsApi.CostAvoidanceTrendResponse, Error>({
    queryKey: analyticsKeys.costAvoidanceTrend(projectPath || '', params),
    queryFn: () => apiBridge.costAvoidance.getTrendByPath(projectPath!, params),
    enabled: !!projectPath && options?.enabled !== false,
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to record a cost avoidance event
 *
 * Mutation hook for recording new events detected by external tools
 * or manual review.
 *
 * @param projectPath - Path to the project
 */
export function useRecordCostAvoidanceEvent(projectPath: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: analyticsApi.RecordCostAvoidanceEventRequest) =>
      apiBridge.costAvoidance.recordEvent(projectPath, request),
    onSuccess: () => {
      // Invalidate cost avoidance queries to refresh data
      queryClient.invalidateQueries({ queryKey: analyticsKeys.costAvoidance() });
    },
  });
}

// =============================================================================
// Project Benchmark Hooks (Module 6)
// =============================================================================

/**
 * Hook to get project rankings/leaderboard
 *
 * Returns projects ranked by the specified metric:
 * - roi: Total ROI percentage (default)
 * - value: Total value generated in USD
 * - success_rate: Percentage of specs with positive ROI
 *
 * @param params - Ranking parameters (metric, period, limit)
 * @param options - React Query options
 */
export function useProjectRankings(
  params?: analyticsApi.ProjectRankingsParams,
  options?: { enabled?: boolean }
) {
  return useQuery<analyticsApi.ProjectRankingsResponse, Error>({
    queryKey: analyticsKeys.projectRankings(params),
    queryFn: () => apiBridge.benchmarks.getRankings(params),
    enabled: options?.enabled !== false,
    staleTime: 5 * 60 * 1000, // 5 minutes (rankings change less frequently)
  });
}

/**
 * Hook to get best practices identified from top performers
 *
 * Analyzes top-performing projects to identify success patterns:
 * - Low QA iterations
 * - High success rates
 * - Feature type diversity
 * - Cost efficiency
 * - Consistent delivery
 *
 * @param params - Analysis parameters (top_n projects to analyze)
 * @param options - React Query options
 */
export function useBestPractices(
  params?: analyticsApi.BestPracticesParams,
  options?: { enabled?: boolean }
) {
  return useQuery<analyticsApi.BestPracticesResponse, Error>({
    queryKey: analyticsKeys.bestPractices(params),
    queryFn: () => apiBridge.benchmarks.getBestPractices(params),
    enabled: options?.enabled !== false,
    staleTime: 10 * 60 * 1000, // 10 minutes (practices change infrequently)
  });
}

/**
 * Hook to get improvement suggestions for a specific project
 *
 * Compares the project against top performers and identifies
 * specific areas for improvement with actionable recommendations.
 *
 * @param projectId - The project to analyze
 * @param options - React Query options
 */
export function useImprovementSuggestions(
  projectId: string | null,
  options?: { enabled?: boolean }
) {
  return useQuery<analyticsApi.ImprovementSuggestionsResponse, Error>({
    queryKey: analyticsKeys.improvementSuggestions(projectId || ''),
    queryFn: () => apiBridge.benchmarks.getImprovementSuggestions(projectId!),
    enabled: !!projectId && options?.enabled !== false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to compare a project to a specific percentile
 *
 * Returns detailed metric comparisons showing how the project
 * performs relative to the specified percentile of all projects.
 *
 * Common percentiles:
 * - 50: Median (typical performance)
 * - 75: Above average
 * - 90: Top performer threshold
 *
 * @param projectId - The project to compare
 * @param params - Percentile comparison parameters
 * @param options - React Query options
 */
export function usePercentileComparison(
  projectId: string | null,
  params?: analyticsApi.PercentileComparisonParams,
  options?: { enabled?: boolean }
) {
  return useQuery<analyticsApi.PercentileComparisonResponse, Error>({
    queryKey: analyticsKeys.percentileComparison(projectId || '', params),
    queryFn: () => apiBridge.benchmarks.getPercentileComparison(projectId!, params),
    enabled: !!projectId && options?.enabled !== false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
