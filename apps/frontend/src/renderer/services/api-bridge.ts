/**
 * API Bridge Layer
 * ================
 *
 * Unified API layer that routes requests to either Analytics API (port 8100)
 * or ROI Engine API (port 8002) based on feature flags.
 *
 * This enables gradual migration from Analytics API to ROI Engine API
 * without breaking existing components.
 *
 * Usage:
 * ```typescript
 * import { apiBridge } from './api-bridge';
 *
 * // Automatically routes to correct API based on feature flags
 * const roi = await apiBridge.roi.getSummary(params);
 * const health = await apiBridge.health.check();
 * ```
 */

import { getFeatureFlags, useROIEngine, type FeatureFlags } from './api-config';
import * as analyticsApi from './analytics-api';
import * as roiEngineApi from './roi-engine-api';
import {
  adaptROISummaryToAnalytics,
  adaptUnifiedROIToAnalytics,
  adaptValueBreakdownToAnalytics,
  adaptTimeSavedSummaryToAnalytics,
  adaptTimeSavedByTaskToAnalytics,
  adaptTimeSavedTrendToAnalytics,
  adaptTimeSavedDashboardToAnalytics,
  adaptSatisfactionMetricsToAnalytics,
  adaptNPSToAnalytics,
  adaptFeedbackListToAnalytics,
  adaptTraceListToAnalytics,
  adaptTraceDetailToAnalytics,
  adaptHealthToAnalytics,
} from './type-adapters';

// =============================================================================
// Types
// =============================================================================

export interface BridgeContext {
  projectDir: string;
  projectId?: string;
}

// =============================================================================
// Health Bridge
// =============================================================================

export const healthBridge = {
  /**
   * Check API health.
   * Uses ROI Engine API by default.
   */
  async check(): Promise<{ status: string; langfuse_configured: boolean; langfuse_host: string | null }> {
    if (useROIEngine('health')) {
      const result = await roiEngineApi.checkHealth();
      return {
        status: result.status,
        langfuse_configured: result.langfuse_connected,
        langfuse_host: null,
      };
    }
    return analyticsApi.checkHealth();
  },

  /**
   * Get detailed health status.
   * Routes to ROI Engine for full health check.
   */
  async getStatus(): Promise<analyticsApi.HealthStatusResponse> {
    if (useROIEngine('health')) {
      const result = await roiEngineApi.checkHealth();
      return {
        overall_status: result.status === 'ok' ? 'healthy' : 'unhealthy',
        services: [
          {
            name: 'roi-engine',
            status: result.status === 'ok' ? 'healthy' : 'unhealthy',
            latency_ms: 0,
            message: `Uptime: ${Math.round(result.uptime_seconds)}s`,
          },
          {
            name: 'langfuse',
            status: result.langfuse_connected ? 'healthy' : 'degraded',
            latency_ms: 0,
            message: result.langfuse_connected ? 'Connected' : 'Not connected',
          },
        ],
        checked_at: new Date().toISOString(),
      };
    }
    return analyticsApi.getHealthStatus();
  },
};

// =============================================================================
// Traces Bridge
// =============================================================================

export const tracesBridge = {
  /**
   * List traces with optional filtering.
   */
  async list(params?: analyticsApi.TraceQueryParams) {
    if (useROIEngine('traces')) {
      const result = await roiEngineApi.listTraces({
        limit: params?.limit,
        offset: params?.offset,
        from_date: params?.from_date,
        to_date: params?.to_date,
        tags: params?.tags?.split(','),
      });
      return adaptTraceListToAnalytics(result);
    }
    return analyticsApi.listTraces(params);
  },

  /**
   * Get trace details.
   */
  async get(traceId: string) {
    if (useROIEngine('traces')) {
      const result = await roiEngineApi.getTrace(traceId);
      return adaptTraceDetailToAnalytics(result);
    }
    return analyticsApi.getTrace(traceId);
  },
};

// =============================================================================
// Sessions Bridge
// =============================================================================

export const sessionsBridge = {
  /**
   * Get sessions for a specific spec.
   * Note: ROI Engine doesn't support spec-based filtering, so we always use Analytics API.
   */
  async getForSpec(specId: string): Promise<analyticsApi.SessionListResponse> {
    // Always use Analytics API for spec-based session queries
    // ROI Engine returns a different format and doesn't filter by spec_id
    return analyticsApi.getSessionsForSpec(specId);
  },

  /**
   * List all sessions.
   */
  async list(limit?: number, offset?: number) {
    if (useROIEngine('sessions')) {
      return roiEngineApi.listSessions(limit, offset);
    }
    // Analytics API doesn't have a direct list sessions endpoint
    // Would need to aggregate from traces
    return { sessions: [], total_count: 0 };
  },
};

// =============================================================================
// ROI Bridge
// =============================================================================

export const roiBridge = {
  /**
   * Get ROI summary.
   * Routes to ROI Engine when context is provided, using unified ROI.
   */
  async getSummary(params?: analyticsApi.ROISummaryParams, context?: BridgeContext): Promise<analyticsApi.ROISummaryResponse> {
    if (useROIEngine('roiSummary') && context?.projectDir) {
      // Use unified ROI for overall summary
      const result = await roiEngineApi.getUnifiedROI({
        project_dir: context.projectDir,
        from_date: params?.from_date,
        to_date: params?.to_date,
      });
      // Convert ROI Engine response to Analytics API format
      const hoursFromValue = (value: number) => value / 125; // $125/hr average
      return {
        total_roi_percentage: result.roi_percentage,
        total_business_value_usd: result.total_artifact_value,
        total_actual_cost_usd: result.total_token_cost,
        total_dev_hours_saved: hoursFromValue(result.net_value),
        spec_count: Object.keys(result.by_spec || {}).length,
        specs_with_positive_roi: result.roi_percentage > 0 ? 1 : 0,
        average_confidence: 0.85,
        by_spec: [],
        period: params?.from_date || params?.to_date
          ? { from: params?.from_date || null, to: params?.to_date || null }
          : null,
      };
    }
    return analyticsApi.getROISummary(params);
  },

  /**
   * Get ROI for a specific spec.
   */
  async getForSpec(specId: string, context?: BridgeContext): Promise<analyticsApi.ROIResponse> {
    if (useROIEngine('roiForSpec') && context?.projectDir) {
      const result = await roiEngineApi.getROIForSpec(specId, {
        project_dir: context.projectDir,
      });
      // Adapt ROI Engine response to Analytics API format
      return {
        spec_id: specId,
        metrics: {
          roi_percentage: result.roi_percentage,
          business_value_usd: result.total_artifact_value,
          actual_cost_usd: result.token_cost,
          dev_hours_saved: 0,
          lines_added: 0,
          lines_removed: 0,
          files_changed: 0,
          qa_attempts: 0,
          qa_passed: true,
          confidence_score: 0.85,
          quality_multiplier: 1.0,
          estimation_method: 'artifact_based',
        },
        trace_id: null,
        calculated_at: result.calculated_at,
      };
    }
    return analyticsApi.getROIForSpec(specId);
  },

  /**
   * Get unified ROI.
   */
  async getUnified(params?: analyticsApi.UnifiedROIParams, context?: BridgeContext): Promise<analyticsApi.UnifiedROIResponse> {
    if (useROIEngine('unifiedROI') && context?.projectDir) {
      const result = await roiEngineApi.getUnifiedROI({
        project_dir: context.projectDir,
        from_date: params?.from_date,
        to_date: params?.to_date,
      });
      // Map roles to value dimensions
      const byRole = result.by_role || {};
      const executionValue =
        (byRole['developer'] || 0) + (byRole['qa'] || 0) + (byRole['devops'] || 0);
      const decisionValue =
        (byRole['tech_lead'] || 0) + (byRole['pm'] || 0) * 0.5;
      const preventionValue =
        (byRole['qa'] || 0) * 0.3 + (byRole['devops'] || 0) * 0.3;
      const knowledgeValue =
        (byRole['architect'] || 0) + (byRole['pm'] || 0) * 0.5;

      return {
        summary: {
          total_roi_percentage: result.roi_percentage,
          total_value_usd: result.total_artifact_value,
          total_cost_usd: result.total_token_cost,
          net_value_usd: result.net_value,
          total_execution_value: executionValue,
          total_decision_value: decisionValue,
          total_prevention_value: preventionValue,
          total_knowledge_value: knowledgeValue,
          total_traces: result.trace_count || 0,
          positive_roi_count: result.roi_percentage > 0 ? result.artifact_count : 0,
          average_confidence: 0.85,
          by_feature_type: {},
          value_distribution: {
            execution_value: executionValue,
            decision_value: decisionValue,
            prevention_value: preventionValue,
            knowledge_value: knowledgeValue,
          },
          period: {
            from: result.period_start || null,
            to: result.period_end || null,
          },
        },
        features: [],
        calculated_at: result.calculated_at,
      };
    }
    return analyticsApi.getUnifiedROI(params);
  },

  /**
   * Get ROI trends.
   * This is only available via ROI Engine.
   */
  async getTrends(context: BridgeContext, days?: number) {
    if (useROIEngine('roiTrends') && context?.projectDir) {
      return roiEngineApi.getROITrends({
        project_dir: context.projectDir,
        days,
      });
    }
    // Analytics API doesn't have a direct trends endpoint
    return { trends: [], period_start: '', period_end: '', avg_roi: 0, trend_direction: 'stable' as const };
  },
};

// =============================================================================
// Artifacts Bridge
// =============================================================================

export const artifactsBridge = {
  /**
   * List artifacts.
   */
  async list(params: analyticsApi.ArtifactsParams, context: BridgeContext) {
    if (useROIEngine('artifactList')) {
      return roiEngineApi.listArtifacts({
        project_dir: context.projectDir,
        spec_id: undefined, // params doesn't have spec_id in this context
        limit: params.limit,
      });
    }
    return analyticsApi.getArtifacts(params);
  },

  /**
   * Search artifacts.
   */
  async search(query: string, context: BridgeContext, options?: { artifactType?: string; limit?: number }) {
    if (useROIEngine('artifactSearch')) {
      return roiEngineApi.searchArtifacts({
        project_dir: context.projectDir,
        query,
        artifact_type: options?.artifactType,
        limit: options?.limit,
      });
    }
    return analyticsApi.searchArtifacts(context.projectDir, { query });
  },

  /**
   * Get artifact statistics.
   */
  async getStatistics(context: BridgeContext, fromDate?: string, toDate?: string) {
    if (useROIEngine('artifactStatistics')) {
      // ROI Engine provides value breakdown which includes statistics
      return roiEngineApi.getValueBreakdown({
        project_dir: context.projectDir,
      });
    }
    return analyticsApi.getArtifactStatistics(context.projectDir, fromDate, toDate);
  },

  /**
   * List local artifacts.
   */
  async listLocal(params: analyticsApi.LocalArtifactsParams) {
    if (useROIEngine('localArtifacts')) {
      return roiEngineApi.listLocalArtifacts({
        project_dir: params.project_path,
        spec_id: params.spec_id,
        artifact_type: params.artifact_type,
        limit: params.limit,
      });
    }
    return analyticsApi.getLocalArtifacts(params);
  },

  /**
   * Search artifacts by project path.
   * This is the hook-compatible signature.
   */
  async searchByPath(projectPath: string, params?: analyticsApi.ArtifactSearchParams) {
    // Always use Analytics API for artifact search to maintain type compatibility
    return analyticsApi.searchArtifacts(projectPath, params);
  },

  /**
   * Get artifact statistics by project path.
   * This is the hook-compatible signature.
   */
  async getStatisticsByPath(projectPath: string, fromDate?: string, toDate?: string) {
    // Always use Analytics API for artifact statistics to maintain type compatibility
    return analyticsApi.getArtifactStatistics(projectPath, fromDate, toDate);
  },

  /**
   * Get artifact timeline.
   * Routes to ROI Engine which has /api/artifacts/timeline.
   */
  async getTimeline(
    projectPath: string,
    granularity?: 'hour' | 'day' | 'week',
    fromDate?: string,
    toDate?: string
  ): Promise<analyticsApi.ArtifactTimelineResponse> {
    if (useROIEngine('artifactList')) {
      const result = await roiEngineApi.getArtifactTimeline(projectPath, fromDate, toDate);
      // Adapt ROI Engine response to Analytics API format
      return {
        timeline: result.timeline.map((point) => ({
          date: point.date,
          count: point.artifact_count,
          value_usd: point.total_value,
          by_type: point.by_type,
          by_agent: {}, // ROI Engine doesn't have by_agent
        })),
        granularity: granularity || 'day',
        total_count: result.total_artifacts,
        total_value: result.total_value,
      };
    }
    return analyticsApi.getArtifactTimeline(projectPath, granularity, fromDate, toDate);
  },
};

// =============================================================================
// Costs Bridge
// =============================================================================

export const costsBridge = {
  /**
   * Get cost summary.
   */
  async getSummary(params?: analyticsApi.DateRangeParams): Promise<analyticsApi.CostSummaryResponse> {
    // Always use Analytics API for cost summary to maintain type compatibility
    return analyticsApi.getCostSummary(params);
  },

  /**
   * Get daily costs.
   */
  async getDaily(params?: analyticsApi.DateRangeParams) {
    if (useROIEngine('dailyCosts')) {
      return roiEngineApi.getDailyCosts({
        from_date: params?.from_date,
        to_date: params?.to_date,
      });
    }
    return analyticsApi.getCostSummary(params);
  },

  /**
   * Get costs by model.
   */
  async getByModel(params?: analyticsApi.DateRangeParams) {
    if (useROIEngine('costsByModel')) {
      const billing = await roiEngineApi.getBilling({
        from_date: params?.from_date,
        to_date: params?.to_date,
      });
      return billing.by_model;
    }
    // Analytics API includes this in cost summary
    const summary = await analyticsApi.getCostSummary(params);
    return summary.by_agent_type;
  },

  /**
   * Get costs by agent.
   */
  async getByAgent(params?: analyticsApi.DateRangeParams) {
    if (useROIEngine('costsByAgent')) {
      const billing = await roiEngineApi.getBilling({
        from_date: params?.from_date,
        to_date: params?.to_date,
      });
      return billing.by_agent;
    }
    const summary = await analyticsApi.getCostSummary(params);
    return summary.by_agent_type;
  },
};

// =============================================================================
// Quality Bridge
// =============================================================================

export const qualityBridge = {
  /**
   * Get quality scores.
   * ROI Engine includes quality in artifact data.
   */
  async getScores(params?: { traceId?: string; name?: string; limit?: number }) {
    if (useROIEngine('qualityScores')) {
      // ROI Engine doesn't have separate quality scores
      // Quality is part of artifact metadata
      return [];
    }
    return analyticsApi.listScores(params);
  },
};

// =============================================================================
// Scores Bridge
// =============================================================================

export const scoresBridge = {
  /**
   * List scores with optional filtering.
   */
  async list(params?: { trace_id?: string; name?: string; limit?: number }): Promise<analyticsApi.ScoreResponse[]> {
    // Always use Analytics API for scores
    return analyticsApi.listScores(params);
  },
};

// =============================================================================
// Usage Bridge
// =============================================================================

export const usageBridge = {
  /**
   * Get comprehensive usage summary for dashboard charts.
   * Routes to ROI Engine when feature flag is enabled.
   */
  async getSummary(params?: analyticsApi.UsageSummaryParams, context?: BridgeContext): Promise<analyticsApi.UsageSummaryResponse> {
    if (useROIEngine('usage') && context?.projectDir) {
      // Combine data from ROI Engine endpoints
      const [dailyCosts, unified] = await Promise.all([
        roiEngineApi.getDailyCosts({
          from_date: params?.from_date,
          to_date: params?.to_date,
        }),
        roiEngineApi.getUnifiedROI({
          project_dir: context.projectDir,
          from_date: params?.from_date,
          to_date: params?.to_date,
        }),
      ]);

      // Build cost over time from daily costs
      const totalTokens = dailyCosts.daily_costs.reduce((sum, d) => sum + d.total_tokens, 0);
      const costOverTime = dailyCosts.daily_costs.map(d => ({
        date: d.date,
        cost: d.total_cost,
        tokens: d.total_tokens,
        trace_count: d.trace_count,
      }));

      // Build model distribution from unified data
      const modelDistribution = Object.entries(unified.by_type || {}).map(([type, value]) => ({
        model: type,
        tokens: 0,
        cost: value as number,
        generation_count: 0,
        percentage: unified.total_artifact_value > 0
          ? ((value as number) / unified.total_artifact_value) * 100
          : 0,
      }));

      return {
        total_cost: dailyCosts.total_cost,
        total_tokens: totalTokens,
        total_input_tokens: 0,
        total_output_tokens: 0,
        total_traces: unified.trace_count || 0,
        active_specs: Object.keys(unified.by_spec || {}).length,
        cost_over_time: costOverTime,
        tokens_by_spec: Object.entries(unified.by_spec || {}).map(([specId, value]) => ({
          spec_id: specId,
          input_tokens: 0,
          output_tokens: 0,
          total_tokens: 0,
          cost: value as number,
        })),
        model_distribution: modelDistribution,
        duration_by_phase: [],
        feature_usage: [],
        period: {
          from: params?.from_date || null,
          to: params?.to_date || null,
        },
      };
    }
    return analyticsApi.getUsageSummary(params);
  },
};

// =============================================================================
// Metrics Bridge
// =============================================================================

export const metricsBridge = {
  /**
   * Get hourly metrics.
   * Routes to ROI Engine which now has /api/metrics/hourly.
   */
  async getHourly(hours?: number, projectId?: string): Promise<analyticsApi.HourlyMetricsResponse> {
    if (useROIEngine('hourlyMetrics')) {
      const result = await roiEngineApi.getHourlyMetrics({
        hours,
        project_id: projectId,
      });
      // Adapt ROI Engine response to Analytics API format (simpler type)
      return {
        metrics: result.metrics,
        period_hours: result.period_hours,
      };
    }
    return analyticsApi.getHourlyMetrics(hours, projectId);
  },

  /**
   * Get error metrics.
   * Routes to ROI Engine which now has /api/metrics/errors.
   */
  async getErrors(hours?: number, projectId?: string): Promise<analyticsApi.ErrorMetricsResponse> {
    if (useROIEngine('errorMetrics')) {
      const result = await roiEngineApi.getErrorMetrics({
        hours,
        project_id: projectId,
      });
      // Adapt ROI Engine response to Analytics API format
      // Convert null to undefined for last_occurrence
      return {
        total_errors: result.total_errors,
        error_rate: result.error_rate,
        breakdown: result.breakdown.map((b) => ({
          ...b,
          last_occurrence: b.last_occurrence ?? undefined,
        })),
        recent_errors: result.recent_errors,
      };
    }
    return analyticsApi.getErrorMetrics(hours, projectId);
  },
};

// =============================================================================
// Activity Bridge
// =============================================================================

export const activityBridge = {
  /**
   * Get recent activity.
   * ROI Engine has /api/activity/recent endpoint.
   */
  async getRecent(limit?: number, context?: BridgeContext): Promise<analyticsApi.RecentActivityResponse> {
    if (useROIEngine('recentActivity') && context?.projectDir) {
      const result = await roiEngineApi.getRecentActivity({
        project_dir: context.projectDir,
        limit,
      });
      // Adapt ROI Engine response to Analytics API format
      return {
        events: result.events.map(event => ({
          spec_id: event.spec_id || '',
          event_type: event.event_type,
          timestamp: event.timestamp,
          agent_type: event.metadata?.agent_type as string || undefined,
          details: event.description,
        })),
        total: result.total_count,
      };
    }
    return analyticsApi.getRecentActivity(limit);
  },
};

// =============================================================================
// Cost Avoidance Bridge
// =============================================================================

export const costAvoidanceBridge = {
  /**
   * Get cost avoidance summary.
   */
  async getSummary(context: BridgeContext, params?: analyticsApi.CostAvoidanceSummaryParams) {
    if (useROIEngine('costAvoidance')) {
      // ROI Engine calculates cost avoidance from artifacts
      // Need to call appropriate endpoint when available
      return analyticsApi.getCostAvoidanceSummary(context.projectDir, params);
    }
    return analyticsApi.getCostAvoidanceSummary(context.projectDir, params);
  },

  /**
   * Get cost avoidance summary by project path.
   * This is the hook-compatible signature.
   */
  async getSummaryByPath(
    projectPath: string,
    params?: analyticsApi.CostAvoidanceSummaryParams
  ): Promise<analyticsApi.CostAvoidanceSummary> {
    return analyticsApi.getCostAvoidanceSummary(projectPath, params);
  },

  /**
   * Get cost avoidance trend.
   */
  async getTrend(context: BridgeContext, params?: analyticsApi.CostAvoidanceTrendParams) {
    return analyticsApi.getCostAvoidanceTrend(context.projectDir, params);
  },

  /**
   * Get cost avoidance trend by project path.
   * This is the hook-compatible signature.
   */
  async getTrendByPath(
    projectPath: string,
    params?: analyticsApi.CostAvoidanceTrendParams
  ): Promise<analyticsApi.CostAvoidanceTrendResponse> {
    return analyticsApi.getCostAvoidanceTrend(projectPath, params);
  },

  /**
   * Get cost avoidance events.
   */
  async getEvents(context: BridgeContext, params?: analyticsApi.CostAvoidanceEventsParams) {
    return analyticsApi.getCostAvoidanceEvents(context.projectDir, params);
  },

  /**
   * Get cost avoidance events by project path.
   * This is the hook-compatible signature.
   */
  async getEventsByPath(
    projectPath: string,
    params?: analyticsApi.CostAvoidanceEventsParams
  ): Promise<analyticsApi.CostAvoidanceEventsListResponse> {
    return analyticsApi.getCostAvoidanceEvents(projectPath, params);
  },

  /**
   * Record a cost avoidance event.
   */
  async recordEvent(projectPath: string, request: analyticsApi.RecordCostAvoidanceEventRequest) {
    return analyticsApi.recordCostAvoidanceEvent(projectPath, request);
  },
};

// =============================================================================
// Forecasting Bridge
// =============================================================================

export const forecastingBridge = {
  /**
   * Predict ROI for a spec.
   */
  async predictROI(request: analyticsApi.ForecastPredictRequest) {
    if (useROIEngine('forecasting')) {
      // ROI Engine may have forecasting endpoints
      return analyticsApi.predictROI(request);
    }
    return analyticsApi.predictROI(request);
  },

  /**
   * Get forecast for a spec.
   */
  async getForecast(specId: string) {
    return analyticsApi.getForecast(specId);
  },

  /**
   * Get forecast accuracy.
   */
  async getAccuracy() {
    return analyticsApi.getForecastAccuracy();
  },

  /**
   * Get forecast history.
   */
  async getHistory(limit?: number) {
    return analyticsApi.getForecastHistory(limit);
  },

  /**
   * Get forecast comparison (predicted vs actual).
   */
  async getComparison(specId: string) {
    return analyticsApi.getForecastComparison(specId);
  },
};

// =============================================================================
// Benchmarks Bridge
// =============================================================================

export const benchmarksBridge = {
  /**
   * Get project rankings.
   */
  async getRankings(params?: analyticsApi.ProjectRankingsParams) {
    if (useROIEngine('benchmarks')) {
      return analyticsApi.getProjectRankings(params);
    }
    return analyticsApi.getProjectRankings(params);
  },

  /**
   * Get best practices.
   */
  async getBestPractices(params?: analyticsApi.BestPracticesParams) {
    return analyticsApi.getBestPractices(params);
  },

  /**
   * Get improvement suggestions.
   */
  async getImprovementSuggestions(projectId: string) {
    return analyticsApi.getImprovementSuggestions(projectId);
  },

  /**
   * Get percentile comparison.
   */
  async getPercentileComparison(projectId: string, params?: analyticsApi.PercentileComparisonParams) {
    return analyticsApi.getPercentileComparison(projectId, params);
  },
};

// =============================================================================
// Time Saved Bridge
// =============================================================================

export const timeSavedBridge = {
  /**
   * Get time saved summary.
   * Routes to ROI Engine which now has Time Saved endpoints.
   */
  async getSummary(context: BridgeContext, params?: { from_date?: string; to_date?: string }) {
    // Always use ROI Engine for time saved (now available)
    const result = await roiEngineApi.getTimeSavedSummary({
      project_dir: context.projectDir,
      from_date: params?.from_date,
      to_date: params?.to_date,
    });
    return adaptTimeSavedSummaryToAnalytics(result);
  },

  /**
   * Get time saved by task type.
   */
  async getByTask(context: BridgeContext, params?: { from_date?: string; to_date?: string }) {
    const result = await roiEngineApi.getTimeSavedByTask({
      project_dir: context.projectDir,
      from_date: params?.from_date,
      to_date: params?.to_date,
    });
    return adaptTimeSavedByTaskToAnalytics(result);
  },

  /**
   * Get time saved trend.
   */
  async getTrend(
    context: BridgeContext,
    params?: { granularity?: 'hour' | 'day' | 'week'; from_date?: string; to_date?: string }
  ) {
    const result = await roiEngineApi.getTimeSavedTrend({
      project_dir: context.projectDir,
      granularity: params?.granularity,
      from_date: params?.from_date,
      to_date: params?.to_date,
    });
    return adaptTimeSavedTrendToAnalytics(result);
  },

  /**
   * Get complete time saved dashboard data.
   */
  async getDashboard(context: BridgeContext, params?: { from_date?: string; to_date?: string }) {
    const result = await roiEngineApi.getTimeSavedDashboard({
      project_dir: context.projectDir,
      from_date: params?.from_date,
      to_date: params?.to_date,
    });
    return adaptTimeSavedDashboardToAnalytics(result);
  },

  /**
   * Get benchmarks.
   */
  async getBenchmarks() {
    return roiEngineApi.getTimeSavedBenchmarks();
  },
};

// =============================================================================
// Satisfaction Bridge
// =============================================================================

export const satisfactionBridge = {
  /**
   * Submit a satisfaction survey.
   * Routes to ROI Engine which now has Satisfaction endpoints.
   */
  async submitSurvey(context: BridgeContext, survey: roiEngineApi.SatisfactionSurveyRequest) {
    return roiEngineApi.submitSatisfactionSurvey(context.projectDir, survey);
  },

  /**
   * Get satisfaction metrics.
   */
  async getMetrics(context: BridgeContext, params?: { spec_id?: string; days?: number }) {
    const result = await roiEngineApi.getSatisfactionMetrics({
      project_dir: context.projectDir,
      spec_id: params?.spec_id,
      days: params?.days,
    });
    return adaptSatisfactionMetricsToAnalytics(result);
  },

  /**
   * Get NPS score.
   */
  async getNPS(context: BridgeContext, params?: { spec_id?: string; days?: number }) {
    const result = await roiEngineApi.getNPSScore({
      project_dir: context.projectDir,
      spec_id: params?.spec_id,
      days: params?.days,
    });
    return adaptNPSToAnalytics(result);
  },

  /**
   * Get feedback.
   */
  async getFeedback(
    context: BridgeContext,
    params?: { days?: number; include_empty?: boolean; limit?: number }
  ) {
    const result = await roiEngineApi.getSatisfactionFeedback({
      project_dir: context.projectDir,
      days: params?.days,
      include_empty: params?.include_empty,
      limit: params?.limit,
    });
    return adaptFeedbackListToAnalytics(result);
  },

  /**
   * List surveys.
   */
  async listSurveys(
    context: BridgeContext,
    params?: { spec_id?: string; user_id?: string; days?: number; limit?: number }
  ) {
    return roiEngineApi.listSatisfactionSurveys({
      project_dir: context.projectDir,
      spec_id: params?.spec_id,
      user_id: params?.user_id,
      days: params?.days,
      limit: params?.limit,
    });
  },

  /**
   * Delete a survey.
   */
  async deleteSurvey(context: BridgeContext, surveyId: string) {
    return roiEngineApi.deleteSatisfactionSurvey(context.projectDir, surveyId);
  },
};

// =============================================================================
// Value Breakdown Bridge
// =============================================================================

export const valueBridge = {
  /**
   * Get value breakdown.
   */
  async getBreakdown(context: BridgeContext, params?: analyticsApi.ValueBreakdownParams) {
    if (useROIEngine('unifiedROI')) {
      const result = await roiEngineApi.getValueBreakdown({
        project_dir: context.projectDir,
        spec_id: undefined,
      });
      return {
        breakdown: {
          ...adaptValueBreakdownToAnalytics(result),
          total_value: result.total_value,
          by_category: [],
          by_subcategory: {},
          attribution_count: 0,
          average_confidence: 0.85,
        },
        period: null,
        filters_applied: {},
      };
    }
    return analyticsApi.getValueBreakdown(params);
  },
};

// =============================================================================
// Unified API Bridge Export
// =============================================================================

export const apiBridge = {
  health: healthBridge,
  traces: tracesBridge,
  sessions: sessionsBridge,
  roi: roiBridge,
  artifacts: artifactsBridge,
  costs: costsBridge,
  quality: qualityBridge,
  scores: scoresBridge,
  usage: usageBridge,
  metrics: metricsBridge,
  activity: activityBridge,
  costAvoidance: costAvoidanceBridge,
  forecasting: forecastingBridge,
  benchmarks: benchmarksBridge,
  timeSaved: timeSavedBridge,
  satisfaction: satisfactionBridge,
  value: valueBridge,

  /**
   * Get current feature flags.
   */
  getFeatureFlags,

  /**
   * Check if a specific feature uses ROI Engine.
   */
  useROIEngine,

  /**
   * Create a bridge context from project info.
   */
  createContext(projectDir: string, projectId?: string): BridgeContext {
    return { projectDir, projectId };
  },
};

export default apiBridge;
