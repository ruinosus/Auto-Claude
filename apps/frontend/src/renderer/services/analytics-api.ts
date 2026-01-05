/**
 * Analytics API Client
 * ====================
 *
 * HTTP client for the FastAPI analytics service that fetches data from Langfuse.
 * Replaces the IPC-based data fetching with direct HTTP calls.
 */

// Base URL for the analytics API (FastAPI service)
const API_BASE_URL = 'http://localhost:8100';

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error',
      0,
      error
    );
  }
}

// =============================================================================
// Types (matching backend Pydantic models)
// =============================================================================

export interface TraceResponse {
  id: string;
  name: string;
  timestamp: string;
  metadata: Record<string, unknown>;
  tags: string[];
  session_id: string | null;
  user_id: string | null;
  total_tokens: number;
  total_cost: number;
  latency_ms: number;
  generation_count: number;
  spec_id: string | null;
  agent_type: string | null;
}

export interface TraceListResponse {
  traces: TraceResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface GenerationResponse {
  id: string;
  name: string;
  model: string;
  timestamp: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
  latency_ms: number;
  metadata: Record<string, unknown>;
}

export interface ScoreResponse {
  id: string;
  name: string;
  value: number;
  trace_id: string;
  comment: string | null;
  timestamp: string | null;
}

export interface TraceDetailResponse extends TraceResponse {
  input: unknown;
  output: unknown;
  generations: GenerationResponse[];
  scores: ScoreResponse[];
}

export interface SessionSummary {
  spec_id: string;
  session_count: number;
  total_tokens: number;
  total_cost: number;
  agent_breakdown: Record<string, number>;
  latest_session: string | null;
  status: string;
}

export interface SessionListResponse {
  spec_id: string;
  sessions: TraceResponse[];
  summary: SessionSummary;
}

export interface ROIMetrics {
  roi_percentage: number;
  business_value_usd: number;
  actual_cost_usd: number;
  dev_hours_saved: number;
  lines_added: number;
  lines_removed: number;
  files_changed: number;
  qa_attempts: number;
  qa_passed: boolean;
  confidence_score: number;
  quality_multiplier: number;
  estimation_method: string;
}

export interface ROIResponse {
  spec_id: string;
  metrics: ROIMetrics;
  trace_id: string | null;
  calculated_at: string;
}

export interface ROISummaryResponse {
  total_roi_percentage: number;
  total_business_value_usd: number;
  total_actual_cost_usd: number;
  total_dev_hours_saved: number;
  spec_count: number;
  specs_with_positive_roi: number;
  average_confidence: number;
  by_spec: ROIResponse[];
  period: { from: string | null; to: string | null } | null;
}

export interface AgentCost {
  agent_type: string;
  cost: number;
  tokens: number;
  trace_count: number;
}

export interface CostSummaryResponse {
  total_cost: number;
  total_tokens: number;
  generation_count: number;
  trace_count: number;
  by_agent_type: AgentCost[];
  period: { from: string; to: string };
}

export interface TraceQueryParams {
  spec_id?: string;
  agent_type?: string;
  tags?: string;
  from_date?: string;
  to_date?: string;
  limit?: number;
  offset?: number;
}

export interface DateRangeParams {
  from_date?: string;
  to_date?: string;
}

export interface ROISummaryParams extends DateRangeParams {
  project_id?: string;
}

export interface UsageSummaryParams extends DateRangeParams {
  project_id?: string;
}

// Usage Summary Types (for charts)
export interface CostOverTimePoint {
  date: string;
  cost: number;
  tokens: number;
  trace_count: number;
}

export interface TokensBySpec {
  spec_id: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
}

export interface ModelUsage {
  model: string;
  tokens: number;
  cost: number;
  generation_count: number;
  percentage: number;
}

export interface PhaseDuration {
  phase: string;
  avg_duration_ms: number;
  total_duration_ms: number;
  trace_count: number;
}

export interface FeatureUsage {
  feature: string;
  tokens: number;
  cost: number;
  trace_count: number;
  percentage: number;
}

export interface UsageSummaryResponse {
  total_cost: number;
  total_tokens: number;
  total_input_tokens?: number;
  total_output_tokens?: number;
  total_traces: number;
  active_specs: number;
  cost_over_time: CostOverTimePoint[];
  tokens_by_spec: TokensBySpec[];
  model_distribution: ModelUsage[];
  duration_by_phase: PhaseDuration[];
  feature_usage: FeatureUsage[];
  period: { from: string | null; to: string | null } | null;
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Check if the analytics API is healthy
 */
export async function checkHealth(): Promise<{
  status: string;
  langfuse_configured: boolean;
  langfuse_host: string | null;
}> {
  return fetchApi('/health');
}

/**
 * List traces with optional filtering
 */
export async function listTraces(params?: TraceQueryParams): Promise<TraceListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.spec_id) searchParams.set('spec_id', params.spec_id);
  if (params?.agent_type) searchParams.set('agent_type', params.agent_type);
  if (params?.tags) searchParams.set('tags', params.tags);
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/traces${query ? `?${query}` : ''}`);
}

/**
 * Get detailed trace information
 */
export async function getTrace(traceId: string): Promise<TraceDetailResponse> {
  return fetchApi(`/api/analytics/traces/${traceId}`);
}

/**
 * Get all sessions for a specific spec
 */
export async function getSessionsForSpec(specId: string): Promise<SessionListResponse> {
  return fetchApi(`/api/analytics/sessions/${specId}`);
}

/**
 * Get comprehensive usage analytics for dashboard charts
 *
 * Returns pre-aggregated data for all usage charts.
 * IMPORTANT: Always pass project_id to get accurate data for your project only.
 */
export async function getUsageSummary(params?: UsageSummaryParams): Promise<UsageSummaryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.project_id) searchParams.set('project_id', params.project_id);
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/usage/summary${query ? `?${query}` : ''}`);
}

/**
 * Get aggregated ROI summary for a specific project
 *
 * IMPORTANT: Always pass project_id to get accurate data for your project only.
 * Without project_id, data from ALL projects will be aggregated.
 */
export async function getROISummary(params?: ROISummaryParams): Promise<ROISummaryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.project_id) searchParams.set('project_id', params.project_id);
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/roi/summary${query ? `?${query}` : ''}`);
}

/**
 * Get ROI metrics for a specific spec
 */
export async function getROIForSpec(specId: string): Promise<ROIResponse> {
  return fetchApi(`/api/analytics/roi/${specId}`);
}

/**
 * Get cost summary for a time period
 */
export async function getCostSummary(params?: DateRangeParams): Promise<CostSummaryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/costs${query ? `?${query}` : ''}`);
}

/**
 * List scores with optional filtering
 */
export async function listScores(params?: {
  trace_id?: string;
  name?: string;
  limit?: number;
}): Promise<ScoreResponse[]> {
  const searchParams = new URLSearchParams();
  if (params?.trace_id) searchParams.set('trace_id', params.trace_id);
  if (params?.name) searchParams.set('name', params.name);
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/scores${query ? `?${query}` : ''}`);
}

// =============================================================================
// Health Status Types and Functions
// =============================================================================

export interface ServiceHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency_ms?: number;
  message?: string;
}

export interface HealthStatusResponse {
  overall_status: 'healthy' | 'degraded' | 'unhealthy';
  services: ServiceHealth[];
  checked_at: string;
}

/**
 * Get detailed health status of all services
 */
export async function getHealthStatus(): Promise<HealthStatusResponse> {
  return fetchApi('/api/analytics/health/status');
}

// =============================================================================
// Hourly Metrics Types and Functions
// =============================================================================

export interface HourlyMetric {
  hour: string;
  requests: number;
  tokens: number;
  cost: number;
  errors: number;
}

export interface HourlyMetricsResponse {
  metrics: HourlyMetric[];
  period_hours: number;
}

/**
 * Get metrics aggregated by hour
 * @param hours - Number of hours to fetch (default 24)
 * @param project_id - Filter by project ID for data isolation
 */
export async function getHourlyMetrics(hours: number = 24, project_id?: string): Promise<HourlyMetricsResponse> {
  const params = new URLSearchParams({ hours: hours.toString() });
  if (project_id) params.append('project_id', project_id);
  return fetchApi(`/api/analytics/metrics/hourly?${params}`);
}

// =============================================================================
// Error Metrics Types and Functions
// =============================================================================

export interface ErrorBreakdown {
  error_type: string;
  count: number;
  percentage: number;
  last_occurrence?: string;
}

export interface RecentError {
  spec_id: string;
  error: string;
  timestamp: string;
  agent_type: string;
}

export interface ErrorMetricsResponse {
  total_errors: number;
  error_rate: number;
  breakdown: ErrorBreakdown[];
  recent_errors: RecentError[];
}

/**
 * Get error metrics and breakdown
 * @param hours - Number of hours to fetch (default 24)
 * @param project_id - Filter by project ID for data isolation
 */
export async function getErrorMetrics(hours: number = 24, project_id?: string): Promise<ErrorMetricsResponse> {
  const params = new URLSearchParams({ hours: hours.toString() });
  if (project_id) params.append('project_id', project_id);
  return fetchApi(`/api/analytics/metrics/errors?${params}`);
}

// =============================================================================
// Recent Activity Types and Functions
// =============================================================================

export interface ActivityEvent {
  spec_id: string;
  event_type: string;
  timestamp: string;
  agent_type?: string;
  details?: string;
}

export interface RecentActivityResponse {
  events: ActivityEvent[];
  total: number;
}

/**
 * Get recent spec activity events
 */
export async function getRecentActivity(limit: number = 10): Promise<RecentActivityResponse> {
  return fetchApi(`/api/analytics/specs/recent-activity?limit=${limit}`);
}

// =============================================================================
// Unified ROI Types and Functions
// =============================================================================

export interface ValueBreakdown {
  execution_value: number;  // Direct code work value
  decision_value: number;   // Strategic decisions, prioritization
  prevention_value: number; // Bugs prevented, issues avoided
  knowledge_value: number;  // Documentation, insights gained
}

export interface FeatureROIMetrics {
  feature_type: string;
  roi_percentage: number;
  total_value_usd: number;
  total_cost_usd: number;
  net_value_usd: number;
  confidence_score: number;
  value_breakdown: ValueBreakdown;
  feature_metrics: Record<string, unknown>;
}

export interface FeatureROIResponse {
  feature_type: string;
  project_id: string;
  metrics: FeatureROIMetrics;
  trace_id: string | null;
  timestamp: string;
}

export interface UnifiedROISummary {
  // Overall metrics
  total_roi_percentage: number;
  total_value_usd: number;
  total_cost_usd: number;
  net_value_usd: number;

  // Value breakdown totals
  total_execution_value: number;
  total_decision_value: number;
  total_prevention_value: number;
  total_knowledge_value: number;

  // Counts
  total_traces: number;
  positive_roi_count: number;
  average_confidence: number;

  // Breakdown by feature type
  by_feature_type: Record<string, FeatureROIMetrics>;

  // Breakdown by value type (for pie chart)
  value_distribution: ValueBreakdown;

  // Period info
  period: { from: string | null; to: string | null } | null;
}

export interface UnifiedROIResponse {
  summary: UnifiedROISummary;
  features: FeatureROIResponse[];
  calculated_at: string;
}

export interface UnifiedROIParams extends DateRangeParams {
  project_id?: string;
}

/**
 * Get unified ROI summary across all feature types
 *
 * Returns comprehensive ROI data including:
 * - Total ROI across all Auto-Claude features
 * - Value breakdown by type (execution, decision, prevention, knowledge)
 * - Breakdown by feature type (ideation, roadmap, spec, build, github, insights)
 */
export async function getUnifiedROI(params?: UnifiedROIParams): Promise<UnifiedROIResponse> {
  const searchParams = new URLSearchParams();
  if (params?.project_id) searchParams.set('project_id', params.project_id);
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/roi/unified${query ? `?${query}` : ''}`);
}

// =============================================================================
// Artifacts Types and Functions (Value Attribution Traceability)
// =============================================================================

export type ArtifactType =
  // Insights & General
  | 'diagram'
  | 'code_example'
  | 'recommendation'
  | 'security_finding'
  | 'bug_fix'
  | 'test_case'
  | 'documentation'
  | 'api_design'
  | 'performance_insight'
  | 'cost_analysis'
  // PR/MR Review
  | 'review_comment'
  | 'code_suggestion'
  | 'security_issue'
  | 'bug_detected'
  | 'approval_decision'
  | 'style_issue'
  // QA
  | 'qa_finding'
  | 'qa_verdict'
  | 'test_suggestion'
  | 'acceptance_check'
  | 'fix_applied'
  | 'issue_resolution'
  | 'test_fix'
  // Planning & Build
  | 'implementation_plan'
  | 'subtask_definition'
  | 'architecture_decision'
  | 'risk_assessment'
  | 'dependency_identified'
  | 'code_implementation'
  | 'commit_summary'
  | 'refactoring'
  | 'test_written'
  // Spec Creation
  | 'spec_document'
  | 'requirement_captured'
  | 'context_discovered'
  | 'complexity_assessment'
  // Analysis
  | 'architecture_insight'
  | 'tech_debt_item'
  | 'security_audit'
  | 'performance_bottleneck'
  | 'code_quality_score'
  | 'pattern_discovered'
  | 'gotcha_identified'
  | 'best_practice'
  | 'lesson_learned'
  // Merge & Collaboration
  | 'conflict_resolution'
  | 'merge_decision'
  | 'code_choice'
  // Issue Triage
  | 'triage_classification'
  | 'priority_assignment'
  | 'label_suggestion'
  | 'duplicate_detected'
  | 'assignee_suggestion';

export type ArtifactTab = 'overview' | 'dev' | 'techlead' | 'ops' | 'business';

export interface Artifact {
  id?: string;  // Artifact ID from local storage (art_xxx)
  type: ArtifactType;
  format: string;
  content: string;
  value_usd: number;
  description: string;
  keyword?: string;
  tab?: ArtifactTab;
  storage_path?: string;  // Path to full content in local storage
  full_content_loaded?: boolean;  // True if content was loaded from local storage
  spec_id?: string;
  trace_id?: string;
  agent_type?: string;
  created_at?: string;
}

export interface ArtifactValueBreakdown {
  diagrams: number;
  security: number;
  recommendations: number;
  code_explanations: number;
}

export interface ArtifactTrace {
  trace_id: string;
  trace_name: string;
  timestamp: string;
  query: string;
  total_value_usd: number;
  value_breakdown: ArtifactValueBreakdown;
  artifacts: Artifact[];
  artifact_count: number;
}

export interface ArtifactsResponse {
  artifacts: ArtifactTrace[];
  total: number;
  error?: string;
}

export interface ArtifactsParams {
  project_id?: string;
  trace_id?: string;
  project_path?: string;  // Project path to load full artifact content from local storage
  from_date?: string;  // ISO format YYYY-MM-DD
  to_date?: string;    // ISO format YYYY-MM-DD
  limit?: number;
}

export interface LocalArtifactsParams {
  project_path: string;
  spec_id?: string;
  trace_id?: string;
  artifact_type?: string;
  from_date?: string;  // ISO format YYYY-MM-DD
  to_date?: string;    // ISO format YYYY-MM-DD
  limit?: number;
}

export interface LocalArtifactsResponse {
  artifacts: Artifact[];
  total: number;
  source: 'local_storage';
  full_content: boolean;
  error?: string;
}

export interface LocalArtifactResponse {
  artifact: Artifact;
  source: 'local_storage';
  full_content: boolean;
}

/**
 * Get artifacts generated by insights/agents with value attribution
 *
 * Returns artifacts extracted from trace outputs including:
 * - Diagrams (mermaid, ascii)
 * - Code examples
 * - Recommendations
 * - Security findings
 *
 * Each artifact includes its value contribution to ROI.
 *
 * If project_path is provided, artifacts will include FULL content
 * loaded from local storage instead of truncated previews.
 */
export async function getArtifacts(params?: ArtifactsParams): Promise<ArtifactsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.project_id) searchParams.set('project_id', params.project_id);
  if (params?.trace_id) searchParams.set('trace_id', params.trace_id);
  if (params?.project_path) searchParams.set('project_path', params.project_path);
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/artifacts${query ? `?${query}` : ''}`);
}

/**
 * Get artifacts directly from local storage with FULL content.
 *
 * This bypasses Langfuse and reads artifacts directly from the
 * .auto-claude/artifacts/ directory.
 */
export async function getLocalArtifacts(params: LocalArtifactsParams): Promise<LocalArtifactsResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', params.project_path);
  if (params.spec_id) searchParams.set('spec_id', params.spec_id);
  if (params.trace_id) searchParams.set('trace_id', params.trace_id);
  if (params.artifact_type) searchParams.set('artifact_type', params.artifact_type);
  if (params.from_date) searchParams.set('from_date', params.from_date);
  if (params.to_date) searchParams.set('to_date', params.to_date);
  if (params.limit) searchParams.set('limit', params.limit.toString());

  return fetchApi(`/api/analytics/artifacts/local?${searchParams.toString()}`);
}

/**
 * Get a single artifact by ID with FULL content from local storage.
 */
export async function getLocalArtifact(
  artifactId: string,
  projectPath: string
): Promise<LocalArtifactResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);

  return fetchApi(`/api/analytics/artifacts/local/${artifactId}?${searchParams.toString()}`);
}

// =============================================================================
// Rich Artifact Search, Statistics, and Timeline Functions
// =============================================================================

// Re-export types from analytics-v2.ts for convenience
export type {
  ArtifactMetadata,
  RichLocalArtifact,
  ArtifactQualityMetrics,
  ArtifactStatistics,
  ArtifactTimelineEntry,
  ArtifactTimelineResponse,
  ArtifactSearchParams,
  LocalArtifactsResponse as RichLocalArtifactsResponse,
} from '../../shared/types/analytics-v2';

import type {
  ArtifactSearchParams,
  ArtifactStatistics,
  ArtifactTimelineResponse,
  LocalArtifactsResponse as RichLocalArtifactsResponse,
} from '../../shared/types/analytics-v2';

/**
 * Search artifacts with rich filtering and full-text search.
 *
 * Supports filtering by:
 * - Full-text query across content, title, description
 * - Artifact type (roadmap_feature, idea, security_finding, etc.)
 * - Priority (must, should, could, wont)
 * - Quality flags (has_rationale, has_acceptance_criteria, has_dependencies)
 * - Value range (min_value, max_value)
 * - Agent type (roadmap_generator, ideation, qa_reviewer, etc.)
 * - Tab (dev, techlead, ops, business)
 * - Date range
 */
export async function searchArtifacts(
  projectPath: string,
  params?: ArtifactSearchParams
): Promise<RichLocalArtifactsResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);

  if (params?.query) searchParams.set('query', params.query);
  if (params?.types?.length) searchParams.set('types', params.types.join(','));
  if (params?.priorities?.length) searchParams.set('priorities', params.priorities.join(','));
  if (params?.has_rationale !== undefined) searchParams.set('has_rationale', String(params.has_rationale));
  if (params?.has_acceptance_criteria !== undefined) searchParams.set('has_acceptance_criteria', String(params.has_acceptance_criteria));
  if (params?.has_dependencies !== undefined) searchParams.set('has_dependencies', String(params.has_dependencies));
  if (params?.min_value !== undefined) searchParams.set('min_value', String(params.min_value));
  if (params?.max_value !== undefined) searchParams.set('max_value', String(params.max_value));
  if (params?.agent_types?.length) searchParams.set('agent_types', params.agent_types.join(','));
  if (params?.tabs?.length) searchParams.set('tabs', params.tabs.join(','));
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset));

  return fetchApi(`/api/analytics/artifacts/search?${searchParams.toString()}`);
}

/**
 * Get aggregate statistics for artifacts.
 *
 * Returns:
 * - Total count and value
 * - Breakdown by type, agent, priority, tab
 * - Quality metrics (rationale, acceptance criteria, user stories, dependencies)
 * - Value distribution by type and priority
 */
export async function getArtifactStatistics(
  projectPath: string,
  fromDate?: string,
  toDate?: string
): Promise<ArtifactStatistics> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);
  if (fromDate) searchParams.set('from_date', fromDate);
  if (toDate) searchParams.set('to_date', toDate);

  return fetchApi(`/api/analytics/artifacts/statistics?${searchParams.toString()}`);
}

/**
 * Get artifact creation timeline for visualization.
 *
 * Returns time-series data showing artifact creation over time,
 * grouped by the specified granularity (hour, day, or week).
 */
export async function getArtifactTimeline(
  projectPath: string,
  granularity: 'hour' | 'day' | 'week' = 'day',
  fromDate?: string,
  toDate?: string
): Promise<ArtifactTimelineResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);
  searchParams.set('granularity', granularity);
  if (fromDate) searchParams.set('from_date', fromDate);
  if (toDate) searchParams.set('to_date', toDate);

  return fetchApi(`/api/analytics/artifacts/timeline?${searchParams.toString()}`);
}

// =============================================================================
// Impact Forecast Types and Functions
// =============================================================================

export interface ForecastPredictRequest {
  spec_id: string;
  spec_complexity?: 'simple' | 'standard' | 'complex';
  estimated_lines?: number;
  feature_type?: 'bugfix' | 'feature' | 'refactor' | 'test' | 'documentation' | 'security' | 'performance';
  historical_similar?: string[];
}

export interface ImpactForecastResponse {
  spec_id: string;
  predicted_value_usd: number;
  predicted_cost_usd: number;
  predicted_roi: number;
  confidence_interval: [number, number];
  prediction_factors: {
    complexity?: string;
    lines_factor?: number;
    feature_type?: string;
    feature_multiplier?: number;
    similar_factor?: number;
    base_value?: number;
  };
  created_at: string;
}

export interface ForecastComparisonResponse {
  spec_id: string;
  predicted_roi: number;
  actual_roi: number;
  predicted_value_usd: number;
  actual_value_usd: number;
  predicted_cost_usd: number;
  actual_cost_usd: number;
  accuracy_percentage: number;
  prediction_error: number;
  within_confidence: boolean;
}

export interface ModelAccuracyResponse {
  total_predictions: number;
  mean_accuracy: number;
  mean_absolute_error: number;
  root_mean_square_error: number;
  within_confidence_rate: number;
  bias: number;
  recent_accuracy: number;
}

export interface ForecastHistoryEntry {
  spec_id: string;
  predicted_roi: number;
  actual_roi: number;
  error: number;
  within_ci: boolean;
  created_at: string;
}

export interface ForecastHistoryResponse {
  history: ForecastHistoryEntry[];
  total: number;
}

export interface RecordActualRequest {
  spec_id: string;
  actual_roi: number;
  actual_value_usd?: number;
  actual_cost_usd?: number;
}

/**
 * Predict ROI before running a spec.
 *
 * Uses historical data and spec characteristics to forecast expected ROI.
 * Call this before executing a spec to set expectations.
 */
export async function predictROI(request: ForecastPredictRequest): Promise<ImpactForecastResponse> {
  return fetchApi('/api/analytics/forecast/predict', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Get existing forecast for a spec.
 *
 * Returns the prediction made before execution.
 */
export async function getForecast(specId: string): Promise<ImpactForecastResponse> {
  return fetchApi(`/api/analytics/forecast/${specId}`);
}

/**
 * Record actual ROI and compare with prediction.
 *
 * Call this after spec execution to track prediction accuracy.
 */
export async function recordActualROI(
  specId: string,
  request: RecordActualRequest
): Promise<ForecastComparisonResponse> {
  return fetchApi(`/api/analytics/forecast/${specId}/record-actual`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Get prediction vs actual comparison for a spec.
 *
 * Returns the comparison if actual ROI has been recorded.
 */
export async function getForecastComparison(specId: string): Promise<ForecastComparisonResponse> {
  return fetchApi(`/api/analytics/forecast/${specId}/comparison`);
}

/**
 * Get overall model accuracy metrics.
 *
 * Returns statistics on prediction performance.
 */
export async function getForecastAccuracy(): Promise<ModelAccuracyResponse> {
  return fetchApi('/api/analytics/forecast/accuracy');
}

/**
 * Get recent forecast history with comparisons.
 *
 * Returns list of past predictions and their actual outcomes.
 */
export async function getForecastHistory(limit: number = 20): Promise<ForecastHistoryResponse> {
  return fetchApi(`/api/analytics/forecast/history?limit=${limit}`);
}

// =============================================================================
// Cost Avoidance Types and Functions
// =============================================================================

export type CostAvoidanceType =
  | 'bug_production'
  | 'security_breach'
  | 'rework_avoided'
  | 'duplicate_feature'
  | 'wrong_architecture';

export type CostAvoidanceSeverity = 'critical' | 'high' | 'medium' | 'low';

export interface CostAvoidanceEvent {
  id: string;
  type: CostAvoidanceType;
  severity: CostAvoidanceSeverity;
  estimated_cost_avoided: number;
  confidence: number;
  detected_by: string;
  trace_id: string;
  artifact_id?: string;
  spec_id?: string;
  project_id?: string;
  description?: string;
  evidence: Record<string, unknown>;
  created_at: string;
}

export interface CostAvoidanceSummary {
  total_cost_avoided: number;
  event_count: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  by_detector: Record<string, number>;
  avg_confidence: number;
  period_start?: string;
  period_end?: string;
  events: CostAvoidanceEvent[];
}

export interface CostAvoidanceEventsListResponse {
  events: CostAvoidanceEvent[];
  total: number;
  days: number;
}

export interface CostAvoidanceTrendPoint {
  date: string;
  cost_avoided: number;
  event_count: number;
  by_type: Record<string, number>;
}

export interface CostAvoidanceTrendResponse {
  trend: CostAvoidanceTrendPoint[];
  granularity: 'day' | 'week' | 'month';
  total_cost_avoided: number;
}

export interface RecordCostAvoidanceEventRequest {
  type: CostAvoidanceType;
  severity: CostAvoidanceSeverity;
  detected_by: string;
  trace_id: string;
  description?: string;
  artifact_id?: string;
  spec_id?: string;
  evidence?: Record<string, unknown>;
  confidence?: number;
  base_cost?: number;
}

export interface RecordCostAvoidanceEventResponse {
  success: boolean;
  event_id: string;
  estimated_cost_avoided: number;
  message: string;
}

export interface CostAvoidanceSummaryParams {
  days?: number;
  spec_id?: string;
}

export interface CostAvoidanceEventsParams {
  days?: number;
  type?: CostAvoidanceType;
  severity?: CostAvoidanceSeverity;
  spec_id?: string;
}

export interface CostAvoidanceTrendParams {
  days?: number;
  granularity?: 'day' | 'week' | 'month';
}

/**
 * Get aggregated cost avoidance summary.
 *
 * Returns totals by type, severity, and detector along with individual events.
 */
export async function getCostAvoidanceSummary(
  projectPath: string,
  params?: CostAvoidanceSummaryParams
): Promise<CostAvoidanceSummary> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);
  if (params?.days) searchParams.set('days', params.days.toString());
  if (params?.spec_id) searchParams.set('spec_id', params.spec_id);

  return fetchApi(`/api/analytics/cost-avoidance/summary?${searchParams.toString()}`);
}

/**
 * List cost avoidance events with optional filtering.
 */
export async function getCostAvoidanceEvents(
  projectPath: string,
  params?: CostAvoidanceEventsParams
): Promise<CostAvoidanceEventsListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);
  if (params?.days) searchParams.set('days', params.days.toString());
  if (params?.type) searchParams.set('type', params.type);
  if (params?.severity) searchParams.set('severity', params.severity);
  if (params?.spec_id) searchParams.set('spec_id', params.spec_id);

  return fetchApi(`/api/analytics/cost-avoidance/events?${searchParams.toString()}`);
}

/**
 * Manually record a cost avoidance event.
 *
 * Use this to record events detected by external tools or manual review.
 */
export async function recordCostAvoidanceEvent(
  projectPath: string,
  request: RecordCostAvoidanceEventRequest
): Promise<RecordCostAvoidanceEventResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);

  return fetchApi(`/api/analytics/cost-avoidance/event?${searchParams.toString()}`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Get cost avoidance trend over time for visualization.
 *
 * Returns time-series data showing cost avoided per period.
 */
export async function getCostAvoidanceTrend(
  projectPath: string,
  params?: CostAvoidanceTrendParams
): Promise<CostAvoidanceTrendResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);
  if (params?.days) searchParams.set('days', params.days.toString());
  if (params?.granularity) searchParams.set('granularity', params.granularity);

  return fetchApi(`/api/analytics/cost-avoidance/trend?${searchParams.toString()}`);
}

// =============================================================================
// Value Attribution Breakdown Types and Functions
// =============================================================================

/**
 * Value for a specific subcategory with confidence and evidence.
 */
export interface SubcategoryValueResponse {
  subcategory: string;
  parent_type: string;  // execution, decision, prevention, knowledge
  value_usd: number;
  confidence: number;
  count: number;
  evidence_count: number;
}

/**
 * Breakdown of values within a parent category.
 */
export interface ValueBreakdownByCategory {
  category: string;  // execution, decision, prevention, knowledge
  total_value: number;
  subcategories: SubcategoryValueResponse[];
}

/**
 * Expanded value breakdown with hierarchical category and subcategory details.
 * Used for treemap and drill-down visualizations.
 */
export interface ValueBreakdownExpandedResponse {
  // Parent type totals
  execution_value: number;
  decision_value: number;
  prevention_value: number;
  knowledge_value: number;

  // Total across all categories
  total_value: number;

  // Hierarchical breakdown for treemap
  by_category: ValueBreakdownByCategory[];

  // Flat subcategory breakdown for detailed tables
  by_subcategory: Record<string, SubcategoryValueResponse>;

  // Attribution metadata
  attribution_count: number;
  average_confidence: number;
}

/**
 * Response for GET /analytics/value/breakdown endpoint.
 */
export interface ValueBreakdownResponse {
  breakdown: ValueBreakdownExpandedResponse;
  period: { from: string | null; to: string | null } | null;
  filters_applied: Record<string, unknown>;
}

/**
 * Parameters for value breakdown request.
 */
export interface ValueBreakdownParams {
  project_id?: string;
  project_path?: string;
  from_date?: string;
  to_date?: string;
  feature_type?: string;
  min_confidence?: number;
}

/**
 * Get value breakdown by category and subcategory.
 *
 * Returns hierarchical value data suitable for:
 * - Treemap visualization (category -> subcategory)
 * - Sunburst chart (multi-level drill-down)
 * - Category comparison charts
 *
 * @param params - Query parameters for filtering
 * @returns ValueBreakdownResponse with hierarchical value data
 */
export async function getValueBreakdown(
  params?: ValueBreakdownParams
): Promise<ValueBreakdownResponse> {
  const searchParams = new URLSearchParams();

  if (params?.project_id) searchParams.set('project_id', params.project_id);
  if (params?.project_path) searchParams.set('project_path', params.project_path);
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);
  if (params?.feature_type) searchParams.set('feature_type', params.feature_type);
  if (params?.min_confidence !== undefined) {
    searchParams.set('min_confidence', params.min_confidence.toString());
  }

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/value/breakdown${query ? `?${query}` : ''}`);
}

// =============================================================================
// Project Benchmark Types and Functions (Module 6)
// =============================================================================

export interface ProjectBenchmark {
  project_id: string;
  total_roi: number;
  avg_roi_per_spec: number;
  total_value_generated: number;
  total_cost: number;
  specs_count: number;
  success_rate: number;
  best_feature_type: string;
  worst_feature_type: string;
  rank: number;
  avg_qa_attempts: number;
  avg_iterations: number;
  total_hours_saved: number;
  avg_complexity: string;
}

export interface BestPractice {
  pattern: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  adoption_rate: number;
  examples: string[];
  category: 'general' | 'complexity' | 'qa' | 'agent' | 'iteration';
}

export interface ProjectRankingsResponse {
  rankings: ProjectBenchmark[];
  total: number;
  metric: string;
  period: string;
}

export interface BestPracticesResponse {
  practices: BestPractice[];
  analyzed_projects: number;
  analysis_period: string;
}

export interface ImprovementSuggestionsResponse {
  project_id: string;
  suggestions: string[];
  current_rank: number | null;
  total_projects: number;
}

export interface PercentileMetricComparison {
  project_value: number;
  percentile_value: number;
  delta: number;
  status: 'above' | 'below' | 'equal';
}

export interface PercentileComparisonResponse {
  project_id: string;
  percentile: number;
  metrics: Record<string, PercentileMetricComparison>;
}

export interface ProjectRankingsParams {
  metric?: 'roi' | 'value' | 'success_rate';
  period?: '7d' | '30d' | '90d' | 'all';
  limit?: number;
}

export interface BestPracticesParams {
  top_n?: number;
}

export interface PercentileComparisonParams {
  percentile?: number;
}

/**
 * Get projects ranked by specified metric.
 *
 * Returns a leaderboard of projects with their benchmark data,
 * useful for comparing team/project performance.
 *
 * Metrics:
 * - roi: Total ROI percentage (default)
 * - value: Total value generated in USD
 * - success_rate: Percentage of specs with positive ROI
 */
export async function getProjectRankings(
  params?: ProjectRankingsParams
): Promise<ProjectRankingsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.metric) searchParams.set('metric', params.metric);
  if (params?.period) searchParams.set('period', params.period);
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/benchmarks/projects${query ? `?${query}` : ''}`);
}

/**
 * Identify best practices from top performers.
 *
 * Analyzes top-performing projects to identify success patterns:
 * - Low QA iterations
 * - High success rates
 * - Feature type diversity
 * - Cost efficiency
 * - Consistent delivery
 *
 * Returns actionable insights with adoption rates and examples.
 */
export async function getBestPractices(
  params?: BestPracticesParams
): Promise<BestPracticesResponse> {
  const searchParams = new URLSearchParams();
  if (params?.top_n) searchParams.set('top_n', params.top_n.toString());

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/benchmarks/best-practices${query ? `?${query}` : ''}`);
}

/**
 * Get improvement suggestions for a specific project.
 *
 * Compares the project against top performers and identifies
 * specific areas for improvement with actionable recommendations.
 */
export async function getImprovementSuggestions(
  projectId: string
): Promise<ImprovementSuggestionsResponse> {
  return fetchApi(`/api/analytics/benchmarks/${encodeURIComponent(projectId)}/suggestions`);
}

/**
 * Compare a project to a specific percentile.
 *
 * Returns detailed metric comparisons showing how the project
 * performs relative to the specified percentile of all projects.
 *
 * Common percentiles:
 * - 50: Median (typical performance)
 * - 75: Above average
 * - 90: Top performer threshold
 */
export async function getPercentileComparison(
  projectId: string,
  params?: PercentileComparisonParams
): Promise<PercentileComparisonResponse> {
  const searchParams = new URLSearchParams();
  if (params?.percentile) searchParams.set('percentile', params.percentile.toString());

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/benchmarks/${encodeURIComponent(projectId)}/percentile${query ? `?${query}` : ''}`);
}

// =============================================================================
// ROI Comparison Types and Functions
// =============================================================================

export interface ROIComparisonResult {
  project_id: string;
  roi_percentage: number;
  cost_per_dollar_value: number;
  break_even_days: number | null;
  vs_market_avg: number;
  percentile: number;
  market_position: 'top_performer' | 'above_average' | 'average' | 'below_average' | 'needs_improvement';
  total_value_usd: number;
  total_cost_usd: number;
  net_value_usd: number;
  calculated_at: string;
}

export interface MarketBenchmarks {
  average_roi: number;
  top_performers_roi: number;
  median_roi: number;
  low_performers_roi: number;
  median_time_saved_percent: number;
}

export interface PercentileThreshold {
  min_roi: number;
  label: string;
}

export interface ROIComparisonResponse {
  comparison: ROIComparisonResult;
  benchmarks: MarketBenchmarks;
  percentile_thresholds: Record<string, PercentileThreshold>;
}

export interface MultiProjectComparisonResponse {
  comparisons: ROIComparisonResult[];
  benchmarks: MarketBenchmarks;
  best_performer: string | null;
  worst_performer: string | null;
  average_roi: number;
  total_projects: number;
}

export interface BreakEvenAnalysisResult {
  project_id: string;
  break_even_days: number | null;
  daily_value_rate: number;
  daily_cost_rate: number;
  cumulative_value: number;
  cumulative_cost: number;
  is_profitable: boolean;
  days_since_start: number;
  projected_annual_roi: number | null;
}

export interface BreakEvenResponse {
  analysis: BreakEvenAnalysisResult;
  recommendation: string;
}

export interface ROICompareParams {
  project_ids?: string;
  from_date?: string;
  to_date?: string;
}

export interface ROIBenchmarkParams {
  project_id: string;
  from_date?: string;
  to_date?: string;
}

/**
 * Compare ROI across multiple projects.
 *
 * Returns comparative ROI data including market positioning for each project.
 * If no project_ids provided, compares all available projects.
 */
export async function compareProjectROI(
  params?: ROICompareParams
): Promise<MultiProjectComparisonResponse> {
  const searchParams = new URLSearchParams();
  if (params?.project_ids) searchParams.set('project_ids', params.project_ids);
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/roi/compare${query ? `?${query}` : ''}`);
}

/**
 * Get ROI benchmark position for a single project against market averages.
 *
 * Returns detailed market positioning including:
 * - Percentile ranking
 * - Comparison to market average
 * - Break-even analysis (if applicable)
 */
export async function getROIBenchmark(
  params: ROIBenchmarkParams
): Promise<ROIComparisonResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_id', params.project_id);
  if (params.from_date) searchParams.set('from_date', params.from_date);
  if (params.to_date) searchParams.set('to_date', params.to_date);

  return fetchApi(`/api/analytics/roi/benchmark?${searchParams.toString()}`);
}

/**
 * Calculate break-even analysis for a project.
 *
 * Returns:
 * - Days until break-even (if not yet profitable)
 * - Daily value and cost rates
 * - Projected annual ROI
 * - Human-readable recommendation
 */
export async function getBreakEvenAnalysis(
  projectId: string
): Promise<BreakEvenResponse> {
  return fetchApi(`/api/analytics/roi/break-even/${encodeURIComponent(projectId)}`);
}

// =============================================================================
// Time Saved Types and Functions
// =============================================================================

export interface TimeSavedSummaryResponse {
  total_time_saved_seconds: number;
  total_time_saved_hours: number;
  total_benchmark_seconds: number;
  total_benchmark_hours: number;
  total_actual_seconds: number;
  total_actual_hours: number;
  average_percentage_saved: number;
  task_count: number;
  by_task_type: Record<string, {
    count: number;
    total_saved_hours: number;
    total_benchmark_hours: number;
    total_actual_hours: number;
    percentage_saved: number;
  }>;
  period: { from: string | null; to: string | null } | null;
}

export interface TimeSavedByTaskResponse {
  task_type: string;
  count: number;
  total_saved_hours: number;
  total_benchmark_hours: number;
  total_actual_hours: number;
  percentage_saved: number;
}

export interface TimeSavedByTaskListResponse {
  breakdown: TimeSavedByTaskResponse[];
  total_time_saved_hours: number;
  total_benchmark_hours: number;
  period: { from: string | null; to: string | null } | null;
}

export interface TimeSavedTrendPoint {
  date: string;
  time_saved_hours: number;
  benchmark_hours: number;
  actual_hours: number;
  percentage_saved: number;
  task_count: number;
}

export interface TimeSavedTrendResponse {
  trend: TimeSavedTrendPoint[];
  granularity: string;
  total_time_saved_hours: number;
  period: { from: string | null; to: string | null } | null;
}

export interface TimeSavedComparisonResponse {
  task_type: string;
  with_ai_hours: number;
  without_ai_hours: number;
  time_saved_hours: number;
  percentage_saved: number;
  complexity?: string;
}

export interface TimeSavedDashboardResponse {
  summary: TimeSavedSummaryResponse;
  by_task_type: TimeSavedByTaskResponse[];
  trend: TimeSavedTrendPoint[];
  comparisons: TimeSavedComparisonResponse[];
  total_hours_saved: number;
  equivalent_work_days: number;
  equivalent_work_weeks: number;
  period: { from: string | null; to: string | null } | null;
}

export interface TimeSavedParams {
  project_id?: string;
  from_date?: string;
  to_date?: string;
}

export interface TimeSavedTrendParams extends TimeSavedParams {
  granularity?: 'hour' | 'day' | 'week';
}

/**
 * Get total time saved summary.
 *
 * Calculates developer time saved by comparing AI-assisted task duration
 * against industry benchmarks for human developers.
 */
export async function getTimeSavedSummary(
  params?: TimeSavedParams
): Promise<TimeSavedSummaryResponse> {
  const searchParams = new URLSearchParams();
  if (params?.project_id) searchParams.set('project_id', params.project_id);
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/time-saved/summary${query ? `?${query}` : ''}`);
}

/**
 * Get time saved breakdown by task type.
 *
 * Shows how much time was saved for each type of task (spec writing,
 * implementation, code review, etc.).
 */
export async function getTimeSavedByTask(
  params?: TimeSavedParams
): Promise<TimeSavedByTaskListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.project_id) searchParams.set('project_id', params.project_id);
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/time-saved/by-task${query ? `?${query}` : ''}`);
}

/**
 * Get time saved trend over time.
 *
 * Returns time-series data showing time saved grouped by the specified
 * granularity (hour, day, or week).
 */
export async function getTimeSavedTrend(
  params?: TimeSavedTrendParams
): Promise<TimeSavedTrendResponse> {
  const searchParams = new URLSearchParams();
  if (params?.project_id) searchParams.set('project_id', params.project_id);
  if (params?.granularity) searchParams.set('granularity', params.granularity);
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/time-saved/trend${query ? `?${query}` : ''}`);
}

/**
 * Get complete time saved dashboard data.
 *
 * Returns all data needed for the time saved visualization:
 * - Summary statistics
 * - Breakdown by task type
 * - Trend over time
 * - AI vs human comparison data
 */
export async function getTimeSavedDashboard(
  params?: TimeSavedParams
): Promise<TimeSavedDashboardResponse> {
  const searchParams = new URLSearchParams();
  if (params?.project_id) searchParams.set('project_id', params.project_id);
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);

  const query = searchParams.toString();
  return fetchApi(`/api/analytics/time-saved/dashboard${query ? `?${query}` : ''}`);
}

/**
 * Get available task type benchmarks.
 *
 * Returns the industry standard benchmarks used for calculating time saved.
 */
export async function getTimeSavedBenchmarks(): Promise<{
  benchmarks: Record<string, { hours: number; minutes: number; seconds: number }>;
  error?: string;
}> {
  return fetchApi('/api/analytics/time-saved/benchmarks');
}

// =============================================================================
// Satisfaction Survey Types and Functions (Module 8)
// =============================================================================

export interface SatisfactionSurveyRequest {
  spec_id: string;
  user_id: string;
  overall_satisfaction: number;  // 1-5
  output_quality: number;  // 1-5
  time_saved_perception: number;  // 1-5
  would_recommend: number;  // 1-5, used for NPS
  feedback?: string;
  improvement_suggestions?: string;
}

export interface SatisfactionSurveyResponse {
  id: string;
  spec_id: string;
  user_id: string;
  timestamp: string;
  overall_satisfaction: number;
  output_quality: number;
  time_saved_perception: number;
  would_recommend: number;
  feedback?: string;
  improvement_suggestions?: string;
  project_id?: string;
}

export interface SatisfactionMetrics {
  nps_score: number;  // -100 to 100
  avg_satisfaction: number;  // 1-5
  avg_output_quality: number;  // 1-5
  avg_time_saved: number;  // 1-5
  satisfaction_trend: number;  // Percentage change
  response_count: number;
  promoters_count: number;
  passives_count: number;
  detractors_count: number;
  top_feedback_themes: string[];
  period_days: number;
  period_start?: string;
  period_end?: string;
}

export interface NPSResponse {
  nps_score: number;
  response_count: number;
  promoters_count: number;
  passives_count: number;
  detractors_count: number;
  period_days: number;
}

export interface FeedbackEntry {
  id: string;
  spec_id: string;
  timestamp?: string;
  overall_satisfaction: number;
  would_recommend: number;
  feedback?: string;
  improvement_suggestions?: string;
}

export interface FeedbackListResponse {
  feedback: FeedbackEntry[];
  total: number;
  period_days: number;
}

export interface SurveySubmitResponse {
  success: boolean;
  survey_id: string;
  message: string;
}

export interface SatisfactionMetricsParams {
  project_id?: string;
  spec_id?: string;
  days?: number;
}

export interface FeedbackParams {
  days?: number;
  include_empty?: boolean;
  limit?: number;
}

export interface SurveysListParams {
  spec_id?: string;
  user_id?: string;
  days?: number;
  limit?: number;
}

/**
 * Submit a satisfaction survey after spec completion.
 *
 * Collects ratings (1-5) for:
 * - Overall satisfaction
 * - Output quality
 * - Time saved perception
 * - Would recommend (used for NPS calculation)
 *
 * Optional feedback fields for free-text responses.
 */
export async function submitSatisfactionSurvey(
  projectPath: string,
  survey: SatisfactionSurveyRequest
): Promise<SurveySubmitResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);

  return fetchApi(`/api/analytics/satisfaction/survey?${searchParams.toString()}`, {
    method: 'POST',
    body: JSON.stringify(survey),
  });
}

/**
 * Get aggregated satisfaction metrics.
 *
 * Returns NPS score, average ratings, response breakdown,
 * and satisfaction trend over time.
 */
export async function getSatisfactionMetrics(
  projectPath: string,
  params?: SatisfactionMetricsParams
): Promise<SatisfactionMetrics> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);
  if (params?.project_id) searchParams.set('project_id', params.project_id);
  if (params?.spec_id) searchParams.set('spec_id', params.spec_id);
  if (params?.days) searchParams.set('days', params.days.toString());

  return fetchApi(`/api/analytics/satisfaction/metrics?${searchParams.toString()}`);
}

/**
 * Get Net Promoter Score.
 *
 * NPS = ((promoters - detractors) / total) * 100
 * Range: -100 (all detractors) to +100 (all promoters)
 */
export async function getNPSScore(
  projectPath: string,
  params?: SatisfactionMetricsParams
): Promise<NPSResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);
  if (params?.project_id) searchParams.set('project_id', params.project_id);
  if (params?.spec_id) searchParams.set('spec_id', params.spec_id);
  if (params?.days) searchParams.set('days', params.days.toString());

  return fetchApi(`/api/analytics/satisfaction/nps?${searchParams.toString()}`);
}

/**
 * Get categorized feedback entries.
 *
 * Returns a list of feedback entries with ratings and timestamps,
 * useful for displaying in a feedback review panel.
 */
export async function getSatisfactionFeedback(
  projectPath: string,
  params?: FeedbackParams
): Promise<FeedbackListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);
  if (params?.days) searchParams.set('days', params.days.toString());
  if (params?.include_empty !== undefined) searchParams.set('include_empty', String(params.include_empty));
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  return fetchApi(`/api/analytics/satisfaction/feedback?${searchParams.toString()}`);
}

/**
 * List all satisfaction surveys with optional filtering.
 *
 * Returns detailed survey data for analysis or export.
 */
export async function listSatisfactionSurveys(
  projectPath: string,
  params?: SurveysListParams
): Promise<SatisfactionSurveyResponse[]> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);
  if (params?.spec_id) searchParams.set('spec_id', params.spec_id);
  if (params?.user_id) searchParams.set('user_id', params.user_id);
  if (params?.days) searchParams.set('days', params.days.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  return fetchApi(`/api/analytics/satisfaction/surveys?${searchParams.toString()}`);
}

/**
 * Delete a satisfaction survey.
 */
export async function deleteSatisfactionSurvey(
  projectPath: string,
  surveyId: string
): Promise<{ success: boolean; message: string }> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_path', projectPath);

  return fetchApi(`/api/analytics/satisfaction/survey/${surveyId}?${searchParams.toString()}`, {
    method: 'DELETE',
  });
}

// =============================================================================
// Analytics API Object (for convenience imports)
// =============================================================================

export const analyticsApi = {
  // Health
  checkHealth,

  // Traces
  listTraces,
  getTrace,

  // Sessions
  getSessionsForSpec,

  // Usage
  getUsageSummary,

  // ROI
  getROISummary,
  getROIForSpec,
  getUnifiedROI,
  compareProjectROI,
  getROIBenchmark,
  getBreakEvenAnalysis,

  // Costs
  getCostSummary,

  // Scores
  listScores,

  // Health Status
  getHealthStatus,

  // Metrics
  getHourlyMetrics,
  getErrorMetrics,
  getRecentActivity,

  // Artifacts
  getArtifacts,
  getLocalArtifacts,
  getLocalArtifact,
  searchArtifacts,
  getArtifactStatistics,
  getArtifactTimeline,

  // Forecast
  predictROI,
  getForecast,
  recordActualROI,
  getForecastComparison,
  getForecastAccuracy,
  getForecastHistory,

  // Cost Avoidance
  getCostAvoidanceSummary,
  getCostAvoidanceEvents,
  recordCostAvoidanceEvent,
  getCostAvoidanceTrend,

  // Value Attribution
  getValueBreakdown,

  // Benchmarks
  getProjectRankings,
  getBestPractices,
  getImprovementSuggestions,
  getPercentileComparison,

  // Time Saved
  getTimeSavedSummary,
  getTimeSavedByTask,
  getTimeSavedTrend,
  getTimeSavedDashboard,
  getTimeSavedBenchmarks,

  // Satisfaction (Module 8)
  submitSatisfactionSurvey,
  getSatisfactionMetrics,
  getNPSScore,
  getSatisfactionFeedback,
  listSatisfactionSurveys,
  deleteSatisfactionSurvey,
};
