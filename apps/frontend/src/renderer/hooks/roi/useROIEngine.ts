/**
 * ROI Engine Integration Hook
 *
 * This hook provides access to the new artifact-based ROI Engine.
 * It fetches ROI data from the ROI Engine API and provides React-friendly
 * state management.
 *
 * The ROI Engine calculates value using role-based valuation:
 *   Value = Hourly Rate (by role & seniority) x Estimated Hours (by artifact type)
 *   ROI = (Total Artifact Value - Token Cost) / Token Cost x 100%
 *
 * Usage:
 *   const { roi, artifacts, loading, error } = useROIEngine({
 *     specId: '001-feature',
 *     projectDir: '/path/to/project',
 *   });
 */

import { useState, useEffect, useCallback } from 'react';
import * as roiEngineApi from '../../services/roi-engine-api';
import type {
  Role,
  Seniority,
  ArtifactValue,
  ROIResult,
  ROISummary,
  UnifiedROIResponse,
  ROITrendsResponse,
  ValueBreakdownResponse,
  DailyCostListResponse,
  BillingResponse,
  RecentActivityResponse,
  ArtifactSearchResponse,
  LocalArtifactsListResponse,
  TraceListResponse,
  SessionListResponse,
  HealthCheckResponse,
} from '../../services/roi-engine-api';

// Re-export types for consumers
export type { Role, Seniority, ArtifactValue, ROIResult, ROISummary };

// ═══════════════════════════════════════════════════════════════
// Hook Options and Result Types
// ═══════════════════════════════════════════════════════════════

export interface UseROIEngineOptions {
  specId?: string;
  projectDir: string;
  tokenCost?: number;
  enabled?: boolean;
}

export interface UseROIEngineResult {
  roi: ROIResult | null;
  summary: ROISummary | null;
  artifacts: ArtifactValue[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

// Extended result for unified dashboard data
export interface UseROIEngineDashboardResult {
  unified: UnifiedROIResponse | null;
  trends: ROITrendsResponse | null;
  valueBreakdown: ValueBreakdownResponse | null;
  dailyCosts: DailyCostListResponse | null;
  billing: BillingResponse | null;
  recentActivity: RecentActivityResponse | null;
  health: HealthCheckResponse | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

// ═══════════════════════════════════════════════════════════════
// Main Hook - Basic ROI Data
// ═══════════════════════════════════════════════════════════════

/**
 * Hook to fetch and manage ROI Engine data for a specific spec.
 *
 * @example
 * ```tsx
 * function SpecROI({ specId, projectDir }: Props) {
 *   const { roi, summary, artifacts, loading, error } = useROIEngine({
 *     specId,
 *     projectDir,
 *   });
 *
 *   if (loading) return <Spinner />;
 *   if (error) return <ErrorMessage error={error} />;
 *
 *   return (
 *     <div>
 *       <h2>ROI: {roi?.roi_percentage.toFixed(1)}%</h2>
 *       <p>Artifacts: {artifacts.length}</p>
 *       <p>Total Value: ${roi?.total_artifact_value.toFixed(2)}</p>
 *     </div>
 *   );
 * }
 * ```
 */
export function useROIEngine(options: UseROIEngineOptions): UseROIEngineResult {
  const { specId, projectDir, tokenCost = 0, enabled = true } = options;

  const [roi, setRoi] = useState<ROIResult | null>(null);
  const [summary, setSummary] = useState<ROISummary | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactValue[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled || !projectDir) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Fetch artifacts first (always)
      const artifactsResult = await roiEngineApi.listArtifacts({
        project_dir: projectDir,
        spec_id: specId,
      });
      setArtifacts(artifactsResult.artifacts);

      // If specId provided, fetch ROI and summary
      if (specId) {
        const [roiResult, summaryResult] = await Promise.all([
          roiEngineApi.getROIForSpec(specId, {
            project_dir: projectDir,
            token_cost: tokenCost,
          }),
          roiEngineApi.getROISummary(specId, {
            project_dir: projectDir,
            token_cost: tokenCost,
          }),
        ]);
        setRoi(roiResult);
        setSummary(summaryResult);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [specId, projectDir, tokenCost, enabled]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    roi,
    summary,
    artifacts,
    loading,
    error,
    refetch: fetchData,
  };
}

// ═══════════════════════════════════════════════════════════════
// Dashboard Hook - Full Dashboard Data
// ═══════════════════════════════════════════════════════════════

export interface UseROIEngineDashboardOptions {
  projectDir: string;
  enabled?: boolean;
  dateRange?: {
    from?: string;
    to?: string;
  };
}

/**
 * Hook to fetch all dashboard data from ROI Engine.
 *
 * This is the main hook for replacing the Analytics API dashboard.
 * It fetches unified ROI, trends, value breakdown, costs, and activity.
 *
 * @example
 * ```tsx
 * function Dashboard({ projectDir }: Props) {
 *   const { unified, trends, valueBreakdown, loading } = useROIEngineDashboard({
 *     projectDir,
 *   });
 *
 *   if (loading) return <Spinner />;
 *
 *   return (
 *     <div>
 *       <h2>Total Value: ${unified?.total_artifact_value}</h2>
 *       <h3>ROI: {unified?.roi_percentage}%</h3>
 *       <TrendsChart data={trends?.trends} />
 *       <ValueBreakdownChart data={valueBreakdown} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useROIEngineDashboard(
  options: UseROIEngineDashboardOptions
): UseROIEngineDashboardResult {
  const { projectDir, enabled = true, dateRange } = options;

  const [unified, setUnified] = useState<UnifiedROIResponse | null>(null);
  const [trends, setTrends] = useState<ROITrendsResponse | null>(null);
  const [valueBreakdown, setValueBreakdown] = useState<ValueBreakdownResponse | null>(null);
  const [dailyCosts, setDailyCosts] = useState<DailyCostListResponse | null>(null);
  const [billing, setBilling] = useState<BillingResponse | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivityResponse | null>(null);
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!enabled || !projectDir) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Fetch all dashboard data in parallel
      const results = await Promise.allSettled([
        roiEngineApi.getUnifiedROI({
          project_dir: projectDir,
          from_date: dateRange?.from,
          to_date: dateRange?.to,
        }),
        roiEngineApi.getROITrends({ project_dir: projectDir }),
        roiEngineApi.getValueBreakdown({ project_dir: projectDir }),
        roiEngineApi.getDailyCosts({
          from_date: dateRange?.from,
          to_date: dateRange?.to,
        }),
        roiEngineApi.getBilling({
          from_date: dateRange?.from,
          to_date: dateRange?.to,
        }),
        roiEngineApi.getRecentActivity({ project_dir: projectDir, limit: 10 }),
        roiEngineApi.checkHealth(),
      ]);

      // Extract results (handle partial failures gracefully)
      if (results[0].status === 'fulfilled') setUnified(results[0].value);
      if (results[1].status === 'fulfilled') setTrends(results[1].value);
      if (results[2].status === 'fulfilled') setValueBreakdown(results[2].value);
      if (results[3].status === 'fulfilled') setDailyCosts(results[3].value);
      if (results[4].status === 'fulfilled') setBilling(results[4].value);
      if (results[5].status === 'fulfilled') setRecentActivity(results[5].value);
      if (results[6].status === 'fulfilled') setHealth(results[6].value);

      // Check if all failed
      const allFailed = results.every((r) => r.status === 'rejected');
      if (allFailed) {
        throw new Error('Failed to fetch dashboard data from ROI Engine');
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [projectDir, enabled, dateRange?.from, dateRange?.to]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    unified,
    trends,
    valueBreakdown,
    dailyCosts,
    billing,
    recentActivity,
    health,
    loading,
    error,
    refetch: fetchData,
  };
}

// ═══════════════════════════════════════════════════════════════
// Specialized Hooks for Individual Features
// ═══════════════════════════════════════════════════════════════

/**
 * Hook to fetch trace list from ROI Engine
 */
export function useROIEngineTraces(
  options: { limit?: number; offset?: number; enabled?: boolean } = {}
) {
  const [traces, setTraces] = useState<TraceListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (options.enabled === false) return;

    setLoading(true);
    setError(null);

    try {
      const result = await roiEngineApi.listTraces({
        limit: options.limit,
        offset: options.offset,
      });
      setTraces(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [options.limit, options.offset, options.enabled]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { traces, loading, error, refetch: fetchData };
}

/**
 * Hook to fetch sessions from ROI Engine
 */
export function useROIEngineSessions(
  options: { limit?: number; offset?: number; enabled?: boolean } = {}
) {
  const [sessions, setSessions] = useState<SessionListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (options.enabled === false) return;

    setLoading(true);
    setError(null);

    try {
      const result = await roiEngineApi.listSessions(options.limit, options.offset);
      setSessions(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [options.limit, options.offset, options.enabled]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { sessions, loading, error, refetch: fetchData };
}

/**
 * Hook to search artifacts
 */
export function useROIEngineArtifactSearch(
  projectDir: string,
  query: string,
  options: { enabled?: boolean } = {}
) {
  const [results, setResults] = useState<ArtifactSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (options.enabled === false || !projectDir || !query) return;

    setLoading(true);
    setError(null);

    try {
      const result = await roiEngineApi.searchArtifacts({
        project_dir: projectDir,
        query,
      });
      setResults(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [projectDir, query, options.enabled]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { results, loading, error, refetch: fetchData };
}

/**
 * Hook to fetch local artifacts
 */
export function useROIEngineLocalArtifacts(
  projectDir: string,
  options: { specId?: string; limit?: number; enabled?: boolean } = {}
) {
  const [artifacts, setArtifacts] = useState<LocalArtifactsListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (options.enabled === false || !projectDir) return;

    setLoading(true);
    setError(null);

    try {
      const result = await roiEngineApi.listLocalArtifacts({
        project_dir: projectDir,
        spec_id: options.specId,
        limit: options.limit,
      });
      setArtifacts(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [projectDir, options.specId, options.limit, options.enabled]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { artifacts, loading, error, refetch: fetchData };
}

// ═══════════════════════════════════════════════════════════════
// Utility Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Group artifacts by role.
 */
export function groupArtifactsByRole(
  artifacts: ArtifactValue[]
): Record<Role, ArtifactValue[]> {
  return artifacts.reduce(
    (acc, artifact) => {
      const role = artifact.role;
      if (!acc[role]) {
        acc[role] = [];
      }
      acc[role].push(artifact);
      return acc;
    },
    {} as Record<Role, ArtifactValue[]>
  );
}

/**
 * Group artifacts by type.
 */
export function groupArtifactsByType(
  artifacts: ArtifactValue[]
): Record<string, ArtifactValue[]> {
  return artifacts.reduce(
    (acc, artifact) => {
      const type = artifact.artifact_type;
      if (!acc[type]) {
        acc[type] = [];
      }
      acc[type].push(artifact);
      return acc;
    },
    {} as Record<string, ArtifactValue[]>
  );
}

/**
 * Calculate total value for a group of artifacts.
 */
export function calculateTotalValue(artifacts: ArtifactValue[]): number {
  return artifacts.reduce((sum, a) => sum + a.calculated_value, 0);
}

/**
 * Format currency for display.
 */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format percentage for display.
 */
export function formatPercentage(value: number): string {
  if (value >= 10000) {
    return `${(value / 1000).toFixed(1)}k%`;
  }
  return `${value.toFixed(1)}%`;
}

/**
 * Format hours for display.
 */
export function formatHours(hours: number): string {
  if (hours < 1) {
    return `${Math.round(hours * 60)}m`;
  }
  if (hours >= 24) {
    return `${(hours / 24).toFixed(1)}d`;
  }
  return `${hours.toFixed(1)}h`;
}

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

export const ROLE_LABELS: Record<Role, string> = {
  developer: 'Developer',
  qa: 'QA Engineer',
  devops: 'DevOps Engineer',
  pm: 'Product Manager',
  architect: 'Architect',
  tech_lead: 'Tech Lead',
};

export const ROLE_COLORS: Record<Role, string> = {
  developer: '#3B82F6', // blue
  qa: '#10B981', // green
  devops: '#8B5CF6', // purple
  pm: '#F59E0B', // amber
  architect: '#EF4444', // red
  tech_lead: '#06B6D4', // cyan
};

export const SENIORITY_LABELS: Record<Seniority, string> = {
  junior: 'Junior',
  mid: 'Mid-Level',
  senior: 'Senior',
  staff: 'Staff',
  principal: 'Principal',
};

export default useROIEngine;
