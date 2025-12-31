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
 */
export async function getHourlyMetrics(hours: number = 24): Promise<HourlyMetricsResponse> {
  return fetchApi(`/api/analytics/metrics/hourly?hours=${hours}`);
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
 */
export async function getErrorMetrics(hours: number = 24): Promise<ErrorMetricsResponse> {
  return fetchApi(`/api/analytics/metrics/errors?hours=${hours}`);
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
