/**
 * ROI Engine API Client
 * =====================
 *
 * HTTP client for the ROI Engine API (port 8002).
 * Provides artifact-based ROI calculation using role-based valuation.
 *
 * This is the replacement for the Analytics API (port 8100) for ROI features.
 */

// Base URL for the ROI Engine API
const API_BASE_URL = 'http://localhost:8002';

/**
 * Custom error class for API errors
 */
export class ROIEngineApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: unknown
  ) {
    super(message);
    this.name = 'ROIEngineApiError';
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
      throw new ROIEngineApiError(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  } catch (error) {
    if (error instanceof ROIEngineApiError) {
      throw error;
    }
    throw new ROIEngineApiError(
      error instanceof Error ? error.message : 'Network error',
      0,
      error
    );
  }
}

// =============================================================================
// Types (matching ROI Engine backend Pydantic models)
// =============================================================================

export type Role =
  | 'developer'
  | 'qa'
  | 'devops'
  | 'pm'
  | 'architect'
  | 'tech_lead';

export type Seniority =
  | 'junior'
  | 'mid'
  | 'senior'
  | 'staff'
  | 'principal';

// --- Artifact Types ---

export interface ArtifactValue {
  artifact_id: string;
  artifact_type: string;
  role: Role;
  seniority: Seniority;
  hourly_rate: number;
  estimated_hours: number;
  calculated_value: number;
  original_value: number;
  value_source: string;
}

export interface ArtifactListResponse {
  artifacts: ArtifactValue[];
  total_count: number;
  total_value: number;
}

export interface ArtifactSearchResult {
  artifact_id: string;
  artifact_type: string;
  content_preview: string;
  description: string | null;
  created_at: string;
  spec_id: string | null;
  value_usd: number;
  match_score: number;
}

export interface ArtifactSearchResponse {
  results: ArtifactSearchResult[];
  total_count: number;
  query: string;
}

export interface ArtifactTimelinePoint {
  date: string;
  artifact_count: number;
  total_value: number;
  by_type: Record<string, number>;
}

export interface ArtifactTimelineResponse {
  timeline: ArtifactTimelinePoint[];
  period_start: string;
  period_end: string;
  total_artifacts: number;
  total_value: number;
}

export interface LocalArtifact {
  id: string;
  type: string;
  content: string;
  description: string | null;
  value_usd: number;
  created_at: string;
  spec_id: string | null;
  trace_id: string | null;
  storage_path: string;
}

export interface LocalArtifactsListResponse {
  artifacts: LocalArtifact[];
  total_count: number;
  total_value: number;
}

// Artifact detail for top_artifacts list
export interface ArtifactDetail {
  artifact_id: string;
  artifact_type: string;
  value: number;
  estimated_hours: number;
  quality_score?: number;
  status?: 'draft' | 'complete';
}

// Artifacts grouped by role
export interface ArtifactsByRoleItem {
  role: Role;
  role_description: string;
  artifact_count: number;
  total_value: number;
  avg_value_per_artifact: number;
  artifact_types: string[];
  top_artifacts: ArtifactDetail[];
}

export interface ArtifactsByRoleResponse {
  by_role: ArtifactsByRoleItem[];
  total_artifacts: number;
  total_value: number;
}

// --- ROI Types ---

export interface ROIResult {
  scope: 'trace' | 'spec' | 'project';
  scope_id: string;
  total_artifact_value: number;
  artifact_count: number;
  by_role: Record<Role, number>;
  by_type: Record<string, number>;
  token_cost: number;
  net_value: number;
  roi_percentage: number;
  calculated_at: string;
  squad_config_id?: string;
}

export interface ROISummary {
  total_value: number;
  total_cost: number;
  net_value: number;
  roi_percentage: number;
  artifact_count: number;
  top_role?: Role;
  top_role_value: number;
  top_artifact_type?: string;
  top_artifact_type_value: number;
}

export interface UnifiedROIResponse {
  total_artifact_value: number;
  total_token_cost: number;
  net_value: number;
  roi_percentage: number;
  // Token metrics
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  // Breakdowns
  by_role: Record<string, number>;
  by_type: Record<string, number>;
  by_spec: Record<string, number>;
  artifact_count: number;
  trace_count: number;
  period_start: string | null;
  period_end: string | null;
  calculated_at: string;
}

export interface ROITrendPoint {
  date: string;
  roi_percentage: number;
  artifact_value: number;
  token_cost: number;
  artifact_count: number;
}

export interface ROITrendsResponse {
  trends: ROITrendPoint[];
  period_start: string;
  period_end: string;
  avg_roi: number;
  trend_direction: 'up' | 'down' | 'stable';
}

// --- Trace Types ---

export interface TraceResponse {
  id: string;
  name: string;
  timestamp: string;
  session_id: string | null;
  total_tokens: number;
  total_cost: number;
  latency_ms: number;
  tags: string[];
  metadata: Record<string, unknown>;
}

export interface TraceListResponse {
  traces: TraceResponse[];
  total_count: number;
  offset: number;
  limit: number;
}

export interface TraceDetailResponse extends TraceResponse {
  input: unknown;
  output: unknown;
  generations: GenerationData[];
}

export interface GenerationData {
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

// --- Session Types ---

export interface SessionResponse {
  id: string;
  name: string;
  created_at: string;
  trace_count: number;
  total_tokens: number;
  total_cost: number;
}

export interface SessionListResponse {
  sessions: SessionResponse[];
  total_count: number;
}

// --- Cost Types ---

export interface DailyCost {
  date: string;
  trace_count: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  total_cost: number;
  avg_latency_ms: number;
}

export interface DailyCostListResponse {
  daily_costs: DailyCost[];
  total_cost: number;
  period_start: string;
  period_end: string;
}

export interface BillingResponse {
  period_start: string;
  period_end: string;
  total_cost: number;
  total_tokens: number;
  trace_count: number;
  by_model: Record<string, number>;
  by_agent: Record<string, number>;
  by_date: Record<string, number>;
}

// --- Value Breakdown Types ---

export interface ValueBreakdownItem {
  category: string;
  subcategory: string | null;
  value: number;
  percentage: number;
  count: number;
}

export interface ValueBreakdownResponse {
  total_value: number;
  by_role: ValueBreakdownItem[];
  by_type: ValueBreakdownItem[];
  by_seniority: ValueBreakdownItem[];
  by_spec: ValueBreakdownItem[];
}

// --- Health Types ---

export interface HealthCheckResponse {
  status: string;
  version: string;
  langfuse_connected: boolean;
  artifact_storage_available: boolean;
  uptime_seconds: number;
  last_activity: string | null;
}

// --- Activity Types ---

export interface ActivityEvent {
  event_type: string;
  timestamp: string;
  description: string;
  spec_id: string | null;
  trace_id: string | null;
  value: number | null;
  metadata: Record<string, unknown>;
}

export interface RecentActivityResponse {
  events: ActivityEvent[];
  total_count: number;
}

// --- Metrics Types ---

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
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  total_errors: number;
}

export interface ErrorBreakdown {
  error_type: string;
  count: number;
  percentage: number;
  last_occurrence: string | null;
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
  period_hours: number;
}

// --- Configuration Types ---

export interface RateTableResponse {
  rates: Record<string, Record<string, number>>;
  description: string;
}

export interface ArtifactTypeInfo {
  type: string;
  role: Role;
  estimated_hours: number;
  description: string;
}

export interface ArtifactTypesResponse {
  types: ArtifactTypeInfo[];
  total_count: number;
}

export interface ArtifactValuePreview {
  artifact_type: string;
  role: string;
  seniority: string;
  estimated_hours: number;
  hourly_rate: number;
  calculated_value: number;
  formula: string;
}

// =============================================================================
// Query Parameters
// =============================================================================

export interface TraceQueryParams {
  limit?: number;
  offset?: number;
  from_date?: string;
  to_date?: string;
  tags?: string[];
}

export interface ArtifactQueryParams {
  project_dir: string;
  spec_id?: string;
  limit?: number;
}

export interface ArtifactSearchParams {
  project_dir: string;
  query: string;
  artifact_type?: string;
  limit?: number;
}

export interface LocalArtifactParams {
  project_dir: string;
  spec_id?: string;
  artifact_type?: string;
  limit?: number;
}

export interface ROIQueryParams {
  project_dir: string;
  token_cost?: number;
  squad_config_id?: string;
}

export interface UnifiedROIParams {
  project_dir: string;
  from_date?: string;
  to_date?: string;
}

export interface ROITrendsParams {
  project_dir: string;
  days?: number;
}

export interface CostQueryParams {
  project_dir: string;
  from_date?: string;
  to_date?: string;
}

export interface ValueBreakdownParams {
  project_dir: string;
  spec_id?: string;
}

export interface ActivityParams {
  project_dir: string;
  limit?: number;
}

export interface MetricsParams {
  hours?: number;
  project_id?: string;
}

// =============================================================================
// API Functions
// =============================================================================

// --- Health ---

/**
 * Check if the ROI Engine API is healthy
 */
export async function checkHealth(): Promise<HealthCheckResponse> {
  return fetchApi('/api/health');
}

// --- Traces ---

/**
 * List traces with optional filtering
 */
export async function listTraces(params?: TraceQueryParams): Promise<TraceListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());
  if (params?.from_date) searchParams.set('from_date', params.from_date);
  if (params?.to_date) searchParams.set('to_date', params.to_date);
  if (params?.tags?.length) searchParams.set('tags', params.tags.join(','));

  const query = searchParams.toString();
  return fetchApi(`/api/traces${query ? `?${query}` : ''}`);
}

/**
 * Get detailed trace information
 */
export async function getTrace(traceId: string): Promise<TraceDetailResponse> {
  return fetchApi(`/api/traces/${traceId}`);
}

// --- Sessions ---

/**
 * List sessions with optional filtering
 */
export async function listSessions(
  limit?: number,
  offset?: number
): Promise<SessionListResponse> {
  const searchParams = new URLSearchParams();
  if (limit) searchParams.set('limit', limit.toString());
  if (offset) searchParams.set('offset', offset.toString());

  const query = searchParams.toString();
  return fetchApi(`/api/sessions${query ? `?${query}` : ''}`);
}

// --- Artifacts ---

/**
 * List artifacts with optional filtering
 */
export async function listArtifacts(
  params: ArtifactQueryParams
): Promise<ArtifactListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.spec_id) searchParams.set('spec_id', params.spec_id);
  if (params.limit) searchParams.set('limit', params.limit.toString());

  return fetchApi(`/api/artifacts?${searchParams.toString()}`);
}

/**
 * Get a single artifact by ID
 */
export async function getArtifact(
  artifactId: string,
  projectDir: string
): Promise<ArtifactValue> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', projectDir);

  return fetchApi(`/api/artifacts/${artifactId}?${searchParams.toString()}`);
}

/**
 * Search artifacts with full-text query
 */
export async function searchArtifacts(
  params: ArtifactSearchParams
): Promise<ArtifactSearchResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  searchParams.set('query', params.query);
  if (params.artifact_type) searchParams.set('artifact_type', params.artifact_type);
  if (params.limit) searchParams.set('limit', params.limit.toString());

  return fetchApi(`/api/artifacts/search?${searchParams.toString()}`);
}

/**
 * List local artifacts from storage
 */
export async function listLocalArtifacts(
  params: LocalArtifactParams
): Promise<LocalArtifactsListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.spec_id) searchParams.set('spec_id', params.spec_id);
  if (params.artifact_type) searchParams.set('artifact_type', params.artifact_type);
  if (params.limit) searchParams.set('limit', params.limit.toString());

  return fetchApi(`/api/artifacts/local?${searchParams.toString()}`);
}

/**
 * Get artifacts grouped by role with top artifacts per role
 */
export async function getArtifactsByRole(
  params: ArtifactQueryParams
): Promise<ArtifactsByRoleResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.spec_id) searchParams.set('spec_id', params.spec_id);
  if (params.limit) searchParams.set('limit', params.limit.toString());

  return fetchApi(`/api/artifacts/by-role?${searchParams.toString()}`);
}

/**
 * Get artifact timeline (artifacts over time)
 */
export async function getArtifactTimeline(
  projectDir: string,
  fromDate?: string,
  toDate?: string
): Promise<ArtifactTimelineResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', projectDir);
  if (fromDate) searchParams.set('from_date', fromDate);
  if (toDate) searchParams.set('to_date', toDate);

  return fetchApi(`/api/artifacts/timeline?${searchParams.toString()}`);
}

// --- ROI ---

/**
 * Calculate and get ROI for a specific spec
 */
export async function getROIForSpec(
  specId: string,
  params: ROIQueryParams
): Promise<ROIResult> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.token_cost !== undefined) {
    searchParams.set('token_cost', params.token_cost.toString());
  }
  if (params.squad_config_id) {
    searchParams.set('squad_config_id', params.squad_config_id);
  }

  return fetchApi(`/api/roi/spec/${specId}?${searchParams.toString()}`);
}

/**
 * Get ROI summary for a specific spec
 */
export async function getROISummary(
  specId: string,
  params: ROIQueryParams
): Promise<ROISummary> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.token_cost !== undefined) {
    searchParams.set('token_cost', params.token_cost.toString());
  }

  return fetchApi(`/api/roi/summary/${specId}?${searchParams.toString()}`);
}

/**
 * Calculate ROI for a specific trace
 */
export async function getROIForTrace(
  traceId: string,
  params: ROIQueryParams
): Promise<ROIResult> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.token_cost !== undefined) {
    searchParams.set('token_cost', params.token_cost.toString());
  }

  return fetchApi(`/api/roi/trace/${traceId}?${searchParams.toString()}`);
}

/**
 * Get unified ROI combining all sources
 */
export async function getUnifiedROI(
  params: UnifiedROIParams
): Promise<UnifiedROIResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.from_date) searchParams.set('from_date', params.from_date);
  if (params.to_date) searchParams.set('to_date', params.to_date);

  return fetchApi(`/api/roi/unified?${searchParams.toString()}`);
}

/**
 * Get ROI trends over time
 */
export async function getROITrends(
  params: ROITrendsParams
): Promise<ROITrendsResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.days) searchParams.set('days', params.days.toString());

  return fetchApi(`/api/roi/trends?${searchParams.toString()}`);
}

// --- Costs ---

/**
 * Get daily cost breakdown
 */
export async function getDailyCosts(
  params: CostQueryParams
): Promise<DailyCostListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.from_date) searchParams.set('from_date', params.from_date);
  if (params.to_date) searchParams.set('to_date', params.to_date);

  return fetchApi(`/api/costs/daily?${searchParams.toString()}`);
}

/**
 * Get billing period summary
 */
export async function getBilling(
  params: CostQueryParams
): Promise<BillingResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.from_date) searchParams.set('from_date', params.from_date);
  if (params.to_date) searchParams.set('to_date', params.to_date);

  return fetchApi(`/api/costs/billing?${searchParams.toString()}`);
}

// --- Value Breakdown ---

/**
 * Get detailed value breakdown by dimension
 */
export async function getValueBreakdown(
  params: ValueBreakdownParams
): Promise<ValueBreakdownResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.spec_id) searchParams.set('spec_id', params.spec_id);

  return fetchApi(`/api/value/breakdown?${searchParams.toString()}`);
}

// --- Activity ---

/**
 * Get recent activity events
 */
export async function getRecentActivity(
  params: ActivityParams
): Promise<RecentActivityResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.limit) searchParams.set('limit', params.limit.toString());

  return fetchApi(`/api/activity/recent?${searchParams.toString()}`);
}

// --- Metrics ---

/**
 * Get hourly metrics (requests, tokens, cost, errors)
 */
export async function getHourlyMetrics(
  params?: MetricsParams
): Promise<HourlyMetricsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.hours) searchParams.set('hours', params.hours.toString());
  if (params?.project_id) searchParams.set('project_id', params.project_id);

  const query = searchParams.toString();
  return fetchApi(`/api/metrics/hourly${query ? `?${query}` : ''}`);
}

/**
 * Get error metrics and breakdown
 */
export async function getErrorMetrics(
  params?: MetricsParams
): Promise<ErrorMetricsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.hours) searchParams.set('hours', params.hours.toString());
  if (params?.project_id) searchParams.set('project_id', params.project_id);

  const query = searchParams.toString();
  return fetchApi(`/api/metrics/errors${query ? `?${query}` : ''}`);
}

// --- Configuration ---

/**
 * Get rate table (hourly rates by role and seniority)
 */
export async function getRateTable(): Promise<RateTableResponse> {
  return fetchApi('/api/config/rates');
}

/**
 * Get all artifact types with their mappings
 */
export async function getArtifactTypes(): Promise<ArtifactTypesResponse> {
  return fetchApi('/api/config/artifact-types');
}

/**
 * Preview artifact value calculation
 */
export async function previewArtifactValue(
  artifactType: string,
  seniority?: Seniority,
  projectDir?: string
): Promise<ArtifactValuePreview> {
  const searchParams = new URLSearchParams();
  searchParams.set('artifact_type', artifactType);
  if (seniority) searchParams.set('seniority', seniority);
  if (projectDir) searchParams.set('project_dir', projectDir);

  return fetchApi(`/api/artifacts/preview?${searchParams.toString()}`);
}

/**
 * Get list of available roles
 */
export async function getRoles(): Promise<{
  roles: Array<{ role: Role; description: string }>;
}> {
  return fetchApi('/api/config/roles');
}

// =============================================================================
// Time Saved Types and Functions (Phase 5L)
// =============================================================================

export interface TimeSavedByTaskType {
  count: number;
  total_saved_hours: number;
  total_benchmark_hours: number;
  total_actual_hours: number;
  percentage_saved: number;
}

export interface TimeSavedSummaryResponse {
  total_time_saved_seconds: number;
  total_time_saved_hours: number;
  total_benchmark_hours: number;
  total_actual_hours: number;
  average_percentage_saved: number;
  task_count: number;
  by_task_type: Record<string, TimeSavedByTaskType>;
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

export interface TimeSavedBenchmarksResponse {
  benchmarks: Record<string, { hours: number; minutes: number; seconds: number }>;
}

export interface TimeSavedParams {
  project_dir: string;
  from_date?: string;
  to_date?: string;
}

export interface TimeSavedTrendParams extends TimeSavedParams {
  granularity?: 'hour' | 'day' | 'week';
}

/**
 * Get total time saved summary
 */
export async function getTimeSavedSummary(
  params: TimeSavedParams
): Promise<TimeSavedSummaryResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.from_date) searchParams.set('from_date', params.from_date);
  if (params.to_date) searchParams.set('to_date', params.to_date);

  return fetchApi(`/api/time-saved/summary?${searchParams.toString()}`);
}

/**
 * Get time saved breakdown by task type
 */
export async function getTimeSavedByTask(
  params: TimeSavedParams
): Promise<TimeSavedByTaskListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.from_date) searchParams.set('from_date', params.from_date);
  if (params.to_date) searchParams.set('to_date', params.to_date);

  return fetchApi(`/api/time-saved/by-task?${searchParams.toString()}`);
}

/**
 * Get time saved trend over time
 */
export async function getTimeSavedTrend(
  params: TimeSavedTrendParams
): Promise<TimeSavedTrendResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.granularity) searchParams.set('granularity', params.granularity);
  if (params.from_date) searchParams.set('from_date', params.from_date);
  if (params.to_date) searchParams.set('to_date', params.to_date);

  return fetchApi(`/api/time-saved/trend?${searchParams.toString()}`);
}

/**
 * Get complete time saved dashboard data
 */
export async function getTimeSavedDashboard(
  params: TimeSavedParams
): Promise<TimeSavedDashboardResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.from_date) searchParams.set('from_date', params.from_date);
  if (params.to_date) searchParams.set('to_date', params.to_date);

  return fetchApi(`/api/time-saved/dashboard?${searchParams.toString()}`);
}

/**
 * Get available task type benchmarks
 */
export async function getTimeSavedBenchmarks(): Promise<TimeSavedBenchmarksResponse> {
  return fetchApi('/api/time-saved/benchmarks');
}

// =============================================================================
// Satisfaction Survey Types and Functions (Phase 5L)
// =============================================================================

export interface SatisfactionSurveyRequest {
  spec_id: string;
  user_id: string;
  overall_satisfaction: number; // 1-5
  output_quality: number; // 1-5
  time_saved_perception: number; // 1-5
  would_recommend: number; // 1-5, used for NPS
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

export interface SatisfactionMetricsResponse {
  nps_score: number; // -100 to 100
  avg_satisfaction: number; // 1-5
  avg_output_quality: number; // 1-5
  avg_time_saved: number; // 1-5
  satisfaction_trend: number; // Percentage change
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

export interface SatisfactionParams {
  project_dir: string;
  spec_id?: string;
  days?: number;
}

export interface FeedbackParams {
  project_dir: string;
  days?: number;
  include_empty?: boolean;
  limit?: number;
}

export interface SurveysListParams {
  project_dir: string;
  spec_id?: string;
  user_id?: string;
  days?: number;
  limit?: number;
}

/**
 * Submit a satisfaction survey after spec completion
 */
export async function submitSatisfactionSurvey(
  projectDir: string,
  survey: SatisfactionSurveyRequest
): Promise<SurveySubmitResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', projectDir);

  return fetchApi(`/api/satisfaction/survey?${searchParams.toString()}`, {
    method: 'POST',
    body: JSON.stringify(survey),
  });
}

/**
 * Get aggregated satisfaction metrics
 */
export async function getSatisfactionMetrics(
  params: SatisfactionParams
): Promise<SatisfactionMetricsResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.spec_id) searchParams.set('spec_id', params.spec_id);
  if (params.days) searchParams.set('days', params.days.toString());

  return fetchApi(`/api/satisfaction/metrics?${searchParams.toString()}`);
}

/**
 * Get Net Promoter Score
 */
export async function getNPSScore(
  params: SatisfactionParams
): Promise<NPSResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.spec_id) searchParams.set('spec_id', params.spec_id);
  if (params.days) searchParams.set('days', params.days.toString());

  return fetchApi(`/api/satisfaction/nps?${searchParams.toString()}`);
}

/**
 * Get categorized feedback entries
 */
export async function getSatisfactionFeedback(
  params: FeedbackParams
): Promise<FeedbackListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.days) searchParams.set('days', params.days.toString());
  if (params.include_empty !== undefined) searchParams.set('include_empty', String(params.include_empty));
  if (params.limit) searchParams.set('limit', params.limit.toString());

  return fetchApi(`/api/satisfaction/feedback?${searchParams.toString()}`);
}

/**
 * List all satisfaction surveys with optional filtering
 */
export async function listSatisfactionSurveys(
  params: SurveysListParams
): Promise<SatisfactionSurveyResponse[]> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', params.project_dir);
  if (params.spec_id) searchParams.set('spec_id', params.spec_id);
  if (params.user_id) searchParams.set('user_id', params.user_id);
  if (params.days) searchParams.set('days', params.days.toString());
  if (params.limit) searchParams.set('limit', params.limit.toString());

  return fetchApi(`/api/satisfaction/surveys?${searchParams.toString()}`);
}

/**
 * Delete a satisfaction survey
 */
export async function deleteSatisfactionSurvey(
  projectDir: string,
  surveyId: string
): Promise<{ success: boolean; message: string }> {
  const searchParams = new URLSearchParams();
  searchParams.set('project_dir', projectDir);

  return fetchApi(`/api/satisfaction/survey/${surveyId}?${searchParams.toString()}`, {
    method: 'DELETE',
  });
}

// =============================================================================
// ROI Engine API Object (for convenience imports)
// =============================================================================

export const roiEngineApi = {
  // Health
  checkHealth,

  // Traces
  listTraces,
  getTrace,

  // Sessions
  listSessions,

  // Artifacts
  listArtifacts,
  getArtifact,
  searchArtifacts,
  listLocalArtifacts,
  getArtifactsByRole,
  getArtifactTimeline,

  // ROI
  getROIForSpec,
  getROISummary,
  getROIForTrace,
  getUnifiedROI,
  getROITrends,

  // Costs
  getDailyCosts,
  getBilling,

  // Value Breakdown
  getValueBreakdown,

  // Activity
  getRecentActivity,

  // Metrics
  getHourlyMetrics,
  getErrorMetrics,

  // Configuration
  getRateTable,
  getArtifactTypes,
  previewArtifactValue,
  getRoles,

  // Time Saved (Phase 5L)
  getTimeSavedSummary,
  getTimeSavedByTask,
  getTimeSavedTrend,
  getTimeSavedDashboard,
  getTimeSavedBenchmarks,

  // Satisfaction (Phase 5L)
  submitSatisfactionSurvey,
  getSatisfactionMetrics,
  getNPSScore,
  getSatisfactionFeedback,
  listSatisfactionSurveys,
  deleteSatisfactionSurvey,
};

export default roiEngineApi;
