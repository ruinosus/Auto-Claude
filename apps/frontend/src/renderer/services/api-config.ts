/**
 * API Configuration
 * =================
 *
 * Centralized configuration for API endpoints and feature flags.
 * Controls the migration from Analytics API (8100) to ROI Engine API (8002).
 */

// =============================================================================
// API URLs
// =============================================================================

export const API_URLS = {
  /** Legacy Analytics API - Langfuse integration */
  ANALYTICS: 'http://localhost:8100',

  /** New ROI Engine API - Artifact-based ROI calculation */
  ROI_ENGINE: 'http://localhost:8002',
} as const;

// =============================================================================
// Migration Mode
// =============================================================================

/**
 * API Migration Mode
 *
 * - 'legacy': Use Analytics API only (default, current behavior)
 * - 'hybrid': Use ROI Engine for supported features, Analytics for others
 * - 'roi_engine': Use ROI Engine for all supported features
 */
export type MigrationMode = 'legacy' | 'hybrid' | 'roi_engine';

/**
 * Get current migration mode from environment or default
 */
export function getMigrationMode(): MigrationMode {
  // Check localStorage for override (useful for testing)
  if (typeof window !== 'undefined') {
    const override = localStorage.getItem('api_migration_mode');
    if (override && ['legacy', 'hybrid', 'roi_engine'].includes(override)) {
      return override as MigrationMode;
    }
  }

  // Default to roi_engine mode - all hooks now use apiBridge
  // Phase M1 complete: all useAnalyticsQuery.ts hooks migrated
  return 'roi_engine';
}

/**
 * Set migration mode (persists to localStorage)
 */
export function setMigrationMode(mode: MigrationMode): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('api_migration_mode', mode);
  }
}

// =============================================================================
// Feature Flags
// =============================================================================

/**
 * Feature flags for granular control over which endpoints use ROI Engine
 *
 * Status Legend:
 * - ACTIVE: Bridge checks this flag and routes accordingly
 * - BYPASS: Bridge always uses Analytics API (type compatibility)
 * - ROI_ONLY: Bridge always uses ROI Engine API
 */
export interface FeatureFlags {
  // Phase M2: Health & Traces (BYPASS - always Analytics for type compat)
  health: boolean;
  traces: boolean;
  sessions: boolean;

  // Phase M3: ROI Calculations (BYPASS - always Analytics for type compat)
  roiSummary: boolean;
  roiForSpec: boolean;
  unifiedROI: boolean;
  roiTrends: boolean;

  // Phase M4: Artifacts (ACTIVE for some, BYPASS for path-based)
  artifactList: boolean;
  artifactSearch: boolean;
  artifactStatistics: boolean;
  localArtifacts: boolean;

  // Phase M5: Costs & Quality (ACTIVE)
  dailyCosts: boolean;
  costsByModel: boolean;
  costsByAgent: boolean;
  qualityScores: boolean;

  // Phase M6: Cost Avoidance & Forecasting (BYPASS - always Analytics)
  costAvoidance: boolean;
  forecasting: boolean;

  // Phase M7: Benchmarks (BYPASS - always Analytics)
  benchmarks: boolean;

  // Phase 5L: Time Saved & Satisfaction (ROI_ONLY - always ROI Engine!)
  timeSaved: boolean;
  satisfaction: boolean;

  // Phase M1 New: Scores, Usage, Metrics, Activity (BYPASS - always Analytics)
  scores: boolean;
  usage: boolean;
  hourlyMetrics: boolean;
  errorMetrics: boolean;
  recentActivity: boolean;
}

/**
 * Default feature flags based on migration mode
 */
export function getFeatureFlags(mode?: MigrationMode): FeatureFlags {
  const currentMode = mode ?? getMigrationMode();

  // Legacy mode: all features use Analytics API
  if (currentMode === 'legacy') {
    return {
      health: false,
      traces: false,
      sessions: false,
      roiSummary: false,
      roiForSpec: false,
      unifiedROI: false,
      roiTrends: false,
      artifactList: false,
      artifactSearch: false,
      artifactStatistics: false,
      localArtifacts: false,
      dailyCosts: false,
      costsByModel: false,
      costsByAgent: false,
      qualityScores: false,
      costAvoidance: false,
      forecasting: false,
      benchmarks: false,
      timeSaved: false,       // Still uses Analytics API in legacy mode
      satisfaction: false,    // Still uses Analytics API in legacy mode
      // Phase M1 New: Still uses Analytics API in legacy mode
      scores: false,
      usage: false,
      hourlyMetrics: false,
      errorMetrics: false,
      recentActivity: false,
    };
  }

  // Hybrid mode: enable well-tested features
  if (currentMode === 'hybrid') {
    return {
      // Phase M2: Enable (simple 1:1 mapping)
      health: true,
      traces: true,
      sessions: true,

      // Phase M3: Enable (ROI dashboard already migrated)
      roiSummary: true,
      roiForSpec: true,
      unifiedROI: true,
      roiTrends: true,

      // Phase M4: Enable partially
      artifactList: true,
      artifactSearch: true,
      artifactStatistics: true,
      localArtifacts: true,

      // Phase M5: Enable
      dailyCosts: true,
      costsByModel: true,
      costsByAgent: true,
      qualityScores: true,

      // Phase M6: Enable
      costAvoidance: true,
      forecasting: true,

      // Phase M7: Enable
      benchmarks: true,

      // Phase 5L: Time Saved & Satisfaction now on ROI Engine
      timeSaved: true,
      satisfaction: true,

      // Phase M1 New: Scores, Usage, Metrics, Activity (BYPASS - always Analytics)
      scores: true,
      usage: true,
      hourlyMetrics: true,
      errorMetrics: true,
      recentActivity: true,
    };
  }

  // ROI Engine mode: all features use ROI Engine
  return {
    health: true,
    traces: true,
    sessions: true,
    roiSummary: true,
    roiForSpec: true,
    unifiedROI: true,
    roiTrends: true,
    artifactList: true,
    artifactSearch: true,
    artifactStatistics: true,
    localArtifacts: true,
    dailyCosts: true,
    costsByModel: true,
    costsByAgent: true,
    qualityScores: true,
    costAvoidance: true,
    forecasting: true,
    benchmarks: true,
    timeSaved: true,      // Now available on ROI Engine
    satisfaction: true,   // Now available on ROI Engine
    // Phase M1 New: Currently BYPASS to Analytics
    scores: true,
    usage: true,
    hourlyMetrics: true,
    errorMetrics: true,
    recentActivity: true,
  };
}

/**
 * Check if a specific feature should use ROI Engine
 */
export function useROIEngine(feature: keyof FeatureFlags): boolean {
  const flags = getFeatureFlags();
  return flags[feature] ?? false;
}

// =============================================================================
// API Health Check
// =============================================================================

/**
 * Check if ROI Engine API is available
 */
export async function checkROIEngineAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URLS.ROI_ENGINE}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000), // 3 second timeout
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Check if Analytics API is available
 */
export async function checkAnalyticsAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URLS.ANALYTICS}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

// =============================================================================
// Exports
// =============================================================================

export const apiConfig = {
  urls: API_URLS,
  getMigrationMode,
  setMigrationMode,
  getFeatureFlags,
  useROIEngine,
  checkROIEngineAvailable,
  checkAnalyticsAvailable,
};

export default apiConfig;
