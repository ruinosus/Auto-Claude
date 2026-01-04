// apps/frontend/src/shared/types/analytics-v2.ts

/**
 * Analytics V2 Types
 * Enhanced analytics system with filtering, budgets, anomaly detection, and quality metrics
 */

export type DateRange = '7d' | '30d' | '90d' | 'all';

export interface AnalyticsFilters {
  dateRange: DateRange;
  specIds: string[];
  phases: ('planning' | 'coding' | 'validation')[];
  models: string[];
  costRange: { min: number; max: number };
}

export interface BudgetSettings {
  enforceBlocking: boolean;
  warnThresholdPercent: number;
  blockThresholdPercent: number;
  notificationEnabled: boolean;
  overrideAllowed: boolean;
}

export interface BudgetCheckResult {
  allowed: boolean;
  remaining: number;
  percentageUsed: number;
  reason?: string;
}

export interface Anomaly {
  id: number;
  detectedAt: string;
  anomalyType: 'cost_spike' | 'token_spike' | 'duration_spike';
  severity: 'info' | 'warning' | 'critical';
  metricName: string;
  expectedValue: number;
  actualValue: number;
  zScore: number;
  specId?: string;
  dismissed: boolean;
  dismissedAt?: string;
  dismissedBy?: string;
}

export interface QualityMetrics {
  specId: string;
  lintErrors: number;
  lintWarnings: number;
  typeErrors: number;
  testCoveragePercent?: number;
  complexityScore?: number;
  qualityGrade: 'A' | 'B' | 'C' | 'D' | 'F';
  analyzedAt: string;
}

export interface ExportOptions {
  format: 'csv' | 'json' | 'pdf';
  dateRange: DateRange;
  filters: AnalyticsFilters;
  includeMetrics: string[];
}

export interface Benchmark {
  region: 'us' | 'latam' | 'eu';
  seniority: 'junior' | 'mid' | 'senior';
  hourlyRate: number;
  minutesPerLine: number;
}

// Local artifact storage types (full content stored locally)
export interface LocalArtifact {
  id: string;
  type: string;
  format?: string;
  content: string;
  value_usd: number;
  description?: string;
  tab?: string;
  created_at: string;
  trace_id?: string;
  spec_id?: string;
  project_id?: string;
  agent_type?: string;
  session_num?: number;
  metadata?: Record<string, unknown>;
}

export interface ArtifactFilters {
  spec_id?: string;
  trace_id?: string;
  type?: string;
  date?: string;
  limit?: number;
}

// =============================================================================
// Rich Artifact Types (for enhanced analytics dashboard)
// =============================================================================

/**
 * Rich artifact metadata with quality indicators
 */
export interface ArtifactMetadata {
  title?: string;
  priority?: 'must' | 'should' | 'could' | 'wont' | string;
  complexity?: 'low' | 'medium' | 'high' | 'very_high' | string;
  impact?: 'low' | 'medium' | 'high' | string;
  status?: string;
  phase?: string;
  phase_id?: string;
  feature_id?: string;
  feature_name?: string;
  feature_index?: number;
  has_acceptance_criteria?: boolean;
  has_user_stories?: boolean;
  has_rationale?: boolean;
  dependency_count?: number;
  ideation_type?: string;
  [key: string]: unknown;
}

/**
 * Enhanced local artifact with rich fields extracted from content
 */
export interface RichLocalArtifact extends Omit<LocalArtifact, 'metadata'> {
  metadata: ArtifactMetadata;
  rationale?: string;
  acceptance_criteria?: string[];
  user_stories?: string[];
  dependencies?: string[];
}

/**
 * Quality metrics for artifact collections
 */
export interface ArtifactQualityMetrics {
  with_rationale: number;
  with_acceptance_criteria: number;
  with_user_stories: number;
  with_dependencies: number;
  total_with_quality: number;
  quality_percentage: number;
}

/**
 * Aggregate statistics for artifacts
 */
export interface ArtifactStatistics {
  total_count: number;
  total_value_usd: number;
  by_type: Record<string, number>;
  by_agent: Record<string, number>;
  by_priority: Record<string, number>;
  by_tab: Record<string, number>;
  quality_metrics: ArtifactQualityMetrics;
  avg_value_per_artifact: number;
  value_by_type: Record<string, number>;
  value_by_priority: Record<string, number>;
}

/**
 * Single entry for artifact timeline visualization
 */
export interface ArtifactTimelineEntry {
  date: string;
  count: number;
  value_usd: number;
  by_type: Record<string, number>;
  by_agent: Record<string, number>;
}

/**
 * Response for artifact timeline endpoint
 */
export interface ArtifactTimelineResponse {
  timeline: ArtifactTimelineEntry[];
  granularity: 'hour' | 'day' | 'week';
  total_count: number;
  total_value: number;
}

/**
 * Search parameters for artifact search endpoint
 */
export interface ArtifactSearchParams {
  query?: string;
  types?: string[];
  priorities?: string[];
  has_rationale?: boolean;
  has_acceptance_criteria?: boolean;
  has_user_stories?: boolean;
  has_dependencies?: boolean;
  min_value?: number;
  max_value?: number;
  agent_types?: string[];
  tabs?: string[];
  from_date?: string;
  to_date?: string;
  limit?: number;
  offset?: number;
}

/**
 * Response for artifact search/list with pagination and stats
 */
export interface LocalArtifactsResponse {
  artifacts: RichLocalArtifact[];
  total: number;
  limit: number;
  offset: number;
  stats?: ArtifactStatistics;
  error?: string;
}
