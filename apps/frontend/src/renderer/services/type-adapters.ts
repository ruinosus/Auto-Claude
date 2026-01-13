/**
 * Type Adapters
 * =============
 *
 * Transform responses between Analytics API (port 8100) and ROI Engine API (port 8002).
 * These adapters ensure backwards compatibility during the migration process.
 *
 * Usage:
 * - When migrating from Analytics API to ROI Engine API, use these adapters
 *   to transform ROI Engine responses to match expected Analytics API formats
 * - This allows gradual migration without breaking existing components
 */

import type {
  // Analytics API Types
  ROISummaryResponse as AnalyticsROISummary,
  UnifiedROISummary as AnalyticsUnifiedROI,
  ValueBreakdown as AnalyticsValueBreakdown,
  TimeSavedSummaryResponse as AnalyticsTimeSavedSummary,
  TimeSavedByTaskListResponse as AnalyticsTimeSavedByTask,
  TimeSavedTrendResponse as AnalyticsTimeSavedTrend,
  TimeSavedDashboardResponse as AnalyticsTimeSavedDashboard,
  SatisfactionMetrics as AnalyticsSatisfactionMetrics,
  NPSResponse as AnalyticsNPSResponse,
  FeedbackListResponse as AnalyticsFeedbackList,
  TraceListResponse as AnalyticsTraceList,
  TraceDetailResponse as AnalyticsTraceDetail,
  HealthStatusResponse as AnalyticsHealthStatus,
} from './analytics-api';

import type {
  // ROI Engine API Types
  ROISummary as ROIEngineSummary,
  UnifiedROIResponse as ROIEngineUnifiedROI,
  ValueBreakdownResponse as ROIEngineValueBreakdown,
  TimeSavedSummaryResponse as ROIEngineTimeSavedSummary,
  TimeSavedByTaskListResponse as ROIEngineTimeSavedByTask,
  TimeSavedTrendResponse as ROIEngineTimeSavedTrend,
  TimeSavedDashboardResponse as ROIEngineTimeSavedDashboard,
  SatisfactionMetricsResponse as ROIEngineSatisfactionMetrics,
  NPSResponse as ROIEngineNPSResponse,
  FeedbackListResponse as ROIEngineFeedbackList,
  TraceListResponse as ROIEngineTraceList,
  TraceDetailResponse as ROIEngineTraceDetail,
  HealthCheckResponse as ROIEngineHealthCheck,
} from './roi-engine-api';

// =============================================================================
// ROI Adapters
// =============================================================================

/**
 * Estimate dev hours saved from total value.
 * Assumes average hourly rate of $125 (senior developer).
 */
function estimateHoursFromValue(value: number, avgHourlyRate: number = 125): number {
  return value / avgHourlyRate;
}

/**
 * Adapt ROI Engine Summary to Analytics API format.
 *
 * ROI Engine returns role-based artifact valuation.
 * Analytics API expects spec-based ROI with fixed structure.
 */
export function adaptROISummaryToAnalytics(
  roiEngine: ROIEngineSummary,
  specId?: string
): Partial<AnalyticsROISummary> {
  return {
    total_roi_percentage: roiEngine.roi_percentage,
    total_business_value_usd: roiEngine.total_value,
    total_actual_cost_usd: roiEngine.total_cost,
    total_dev_hours_saved: estimateHoursFromValue(roiEngine.net_value),
    spec_count: 1,
    specs_with_positive_roi: roiEngine.roi_percentage > 0 ? 1 : 0,
    average_confidence: 0.85, // Default confidence for artifact-based ROI
    by_spec: specId
      ? [
          {
            spec_id: specId,
            metrics: {
              roi_percentage: roiEngine.roi_percentage,
              business_value_usd: roiEngine.total_value,
              actual_cost_usd: roiEngine.total_cost,
              dev_hours_saved: estimateHoursFromValue(roiEngine.net_value),
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
            calculated_at: new Date().toISOString(),
          },
        ]
      : [],
    period: null,
  };
}

/**
 * Adapt ROI Engine Unified ROI to Analytics API format.
 */
export function adaptUnifiedROIToAnalytics(
  roiEngine: ROIEngineUnifiedROI
): Partial<AnalyticsUnifiedROI> {
  // Calculate value breakdown from by_role distribution
  const totalValue = roiEngine.total_artifact_value;
  const byRole = roiEngine.by_role || {};

  // Map roles to value dimensions (approximate mapping)
  const executionValue =
    (byRole['developer'] || 0) + (byRole['qa'] || 0) + (byRole['devops'] || 0);
  const decisionValue =
    (byRole['tech_lead'] || 0) + (byRole['pm'] || 0) * 0.5;
  const preventionValue =
    (byRole['qa'] || 0) * 0.3 + (byRole['devops'] || 0) * 0.3;
  const knowledgeValue =
    (byRole['architect'] || 0) + (byRole['pm'] || 0) * 0.5;

  return {
    total_roi_percentage: roiEngine.roi_percentage,
    total_value_usd: roiEngine.total_artifact_value,
    total_cost_usd: roiEngine.total_token_cost,
    net_value_usd: roiEngine.net_value,
    total_execution_value: executionValue,
    total_decision_value: decisionValue,
    total_prevention_value: preventionValue,
    total_knowledge_value: knowledgeValue,
    total_traces: roiEngine.trace_count,
    positive_roi_count: roiEngine.roi_percentage > 0 ? roiEngine.artifact_count : 0,
    average_confidence: 0.85,
    by_feature_type: {}, // Would need additional mapping
    value_distribution: {
      execution_value: executionValue,
      decision_value: decisionValue,
      prevention_value: preventionValue,
      knowledge_value: knowledgeValue,
    },
    period: {
      from: roiEngine.period_start,
      to: roiEngine.period_end,
    },
  };
}

// =============================================================================
// Value Breakdown Adapters
// =============================================================================

/**
 * Adapt ROI Engine Value Breakdown to Analytics API format.
 */
export function adaptValueBreakdownToAnalytics(
  roiEngine: ROIEngineValueBreakdown
): AnalyticsValueBreakdown {
  // ROI Engine provides by_role, by_type, by_seniority, by_spec
  // Analytics API expects execution_value, decision_value, prevention_value, knowledge_value

  const byRole = roiEngine.by_role || [];
  const totalByRole: Record<string, number> = {};

  byRole.forEach((item) => {
    totalByRole[item.category] = (totalByRole[item.category] || 0) + item.value;
  });

  // Map roles to value dimensions
  const executionValue =
    (totalByRole['developer'] || 0) + (totalByRole['qa'] || 0) * 0.7;
  const decisionValue =
    (totalByRole['tech_lead'] || 0) + (totalByRole['pm'] || 0) * 0.5;
  const preventionValue =
    (totalByRole['qa'] || 0) * 0.3 + (totalByRole['devops'] || 0) * 0.5;
  const knowledgeValue =
    (totalByRole['architect'] || 0) +
    (totalByRole['pm'] || 0) * 0.5 +
    (totalByRole['devops'] || 0) * 0.5;

  return {
    execution_value: executionValue,
    decision_value: decisionValue,
    prevention_value: preventionValue,
    knowledge_value: knowledgeValue,
  };
}

// =============================================================================
// Time Saved Adapters
// =============================================================================

/**
 * Adapt ROI Engine Time Saved Summary to Analytics API format.
 * Both APIs have very similar structures, so minimal transformation needed.
 */
export function adaptTimeSavedSummaryToAnalytics(
  roiEngine: ROIEngineTimeSavedSummary
): AnalyticsTimeSavedSummary {
  return {
    total_time_saved_seconds: roiEngine.total_time_saved_seconds,
    total_time_saved_hours: roiEngine.total_time_saved_hours,
    total_benchmark_seconds: roiEngine.total_benchmark_hours * 3600,
    total_benchmark_hours: roiEngine.total_benchmark_hours,
    total_actual_seconds: roiEngine.total_actual_hours * 3600,
    total_actual_hours: roiEngine.total_actual_hours,
    average_percentage_saved: roiEngine.average_percentage_saved,
    task_count: roiEngine.task_count,
    by_task_type: roiEngine.by_task_type,
    period: roiEngine.period,
  };
}

/**
 * Adapt ROI Engine Time Saved By Task to Analytics API format.
 */
export function adaptTimeSavedByTaskToAnalytics(
  roiEngine: ROIEngineTimeSavedByTask
): AnalyticsTimeSavedByTask {
  return {
    breakdown: roiEngine.breakdown,
    total_time_saved_hours: roiEngine.total_time_saved_hours,
    total_benchmark_hours: roiEngine.total_benchmark_hours,
    period: roiEngine.period,
  };
}

/**
 * Adapt ROI Engine Time Saved Trend to Analytics API format.
 */
export function adaptTimeSavedTrendToAnalytics(
  roiEngine: ROIEngineTimeSavedTrend
): AnalyticsTimeSavedTrend {
  return {
    trend: roiEngine.trend,
    granularity: roiEngine.granularity,
    total_time_saved_hours: roiEngine.total_time_saved_hours,
    period: roiEngine.period,
  };
}

/**
 * Adapt ROI Engine Time Saved Dashboard to Analytics API format.
 */
export function adaptTimeSavedDashboardToAnalytics(
  roiEngine: ROIEngineTimeSavedDashboard
): AnalyticsTimeSavedDashboard {
  return {
    summary: adaptTimeSavedSummaryToAnalytics(roiEngine.summary),
    by_task_type: roiEngine.by_task_type,
    trend: roiEngine.trend,
    comparisons: roiEngine.comparisons,
    total_hours_saved: roiEngine.total_hours_saved,
    equivalent_work_days: roiEngine.equivalent_work_days,
    equivalent_work_weeks: roiEngine.equivalent_work_weeks,
    period: roiEngine.period,
  };
}

// =============================================================================
// Satisfaction Adapters
// =============================================================================

/**
 * Adapt ROI Engine Satisfaction Metrics to Analytics API format.
 */
export function adaptSatisfactionMetricsToAnalytics(
  roiEngine: ROIEngineSatisfactionMetrics
): AnalyticsSatisfactionMetrics {
  return {
    nps_score: roiEngine.nps_score,
    avg_satisfaction: roiEngine.avg_satisfaction,
    avg_output_quality: roiEngine.avg_output_quality,
    avg_time_saved: roiEngine.avg_time_saved,
    satisfaction_trend: roiEngine.satisfaction_trend,
    response_count: roiEngine.response_count,
    promoters_count: roiEngine.promoters_count,
    passives_count: roiEngine.passives_count,
    detractors_count: roiEngine.detractors_count,
    top_feedback_themes: roiEngine.top_feedback_themes,
    period_days: roiEngine.period_days,
    period_start: roiEngine.period_start,
    period_end: roiEngine.period_end,
  };
}

/**
 * Adapt ROI Engine NPS Response to Analytics API format.
 */
export function adaptNPSToAnalytics(roiEngine: ROIEngineNPSResponse): AnalyticsNPSResponse {
  return {
    nps_score: roiEngine.nps_score,
    response_count: roiEngine.response_count,
    promoters_count: roiEngine.promoters_count,
    passives_count: roiEngine.passives_count,
    detractors_count: roiEngine.detractors_count,
    period_days: roiEngine.period_days,
  };
}

/**
 * Adapt ROI Engine Feedback List to Analytics API format.
 */
export function adaptFeedbackListToAnalytics(
  roiEngine: ROIEngineFeedbackList
): AnalyticsFeedbackList {
  return {
    feedback: roiEngine.feedback,
    total: roiEngine.total,
    period_days: roiEngine.period_days,
  };
}

// =============================================================================
// Trace Adapters
// =============================================================================

/**
 * Adapt ROI Engine Trace List to Analytics API format.
 */
export function adaptTraceListToAnalytics(
  roiEngine: ROIEngineTraceList
): AnalyticsTraceList {
  return {
    traces: roiEngine.traces.map((trace) => ({
      id: trace.id,
      name: trace.name,
      timestamp: trace.timestamp,
      metadata: trace.metadata,
      tags: trace.tags,
      session_id: trace.session_id,
      user_id: null, // ROI Engine doesn't track user_id
      total_tokens: trace.total_tokens,
      total_cost: trace.total_cost,
      latency_ms: trace.latency_ms,
      generation_count: 0, // Would need additional data
      spec_id: null, // Would need to extract from metadata
      agent_type: null, // Would need to extract from metadata
    })),
    total: roiEngine.total_count,
    limit: roiEngine.limit,
    offset: roiEngine.offset,
  };
}

/**
 * Adapt ROI Engine Trace Detail to Analytics API format.
 */
export function adaptTraceDetailToAnalytics(
  roiEngine: ROIEngineTraceDetail
): AnalyticsTraceDetail {
  return {
    id: roiEngine.id,
    name: roiEngine.name,
    timestamp: roiEngine.timestamp,
    metadata: roiEngine.metadata,
    tags: roiEngine.tags,
    session_id: roiEngine.session_id,
    user_id: null,
    total_tokens: roiEngine.total_tokens,
    total_cost: roiEngine.total_cost,
    latency_ms: roiEngine.latency_ms,
    generation_count: roiEngine.generations?.length || 0,
    spec_id: null,
    agent_type: null,
    input: roiEngine.input,
    output: roiEngine.output,
    generations: roiEngine.generations.map((gen) => ({
      id: gen.id,
      name: gen.name,
      model: gen.model,
      timestamp: gen.timestamp,
      input_tokens: gen.input_tokens,
      output_tokens: gen.output_tokens,
      total_tokens: gen.total_tokens,
      cost: gen.cost,
      latency_ms: gen.latency_ms,
      metadata: gen.metadata,
    })),
    scores: [], // ROI Engine trace detail doesn't include scores
  };
}

// =============================================================================
// Health Adapters
// =============================================================================

/**
 * Adapt ROI Engine Health Check to Analytics API format.
 */
export function adaptHealthToAnalytics(
  roiEngine: ROIEngineHealthCheck
): Partial<AnalyticsHealthStatus> {
  return {
    overall_status: roiEngine.status === 'healthy' ? 'healthy' : 'degraded',
    services: [
      {
        name: 'roi_engine',
        status: roiEngine.status === 'healthy' ? 'healthy' : 'unhealthy',
        message: `Version ${roiEngine.version}`,
      },
      {
        name: 'langfuse',
        status: roiEngine.langfuse_connected ? 'healthy' : 'unhealthy',
        message: roiEngine.langfuse_connected
          ? 'Connected'
          : 'Not connected',
      },
      {
        name: 'artifact_storage',
        status: roiEngine.artifact_storage_available ? 'healthy' : 'unhealthy',
        message: roiEngine.artifact_storage_available
          ? 'Available'
          : 'Not available',
      },
    ],
    checked_at: new Date().toISOString(),
  };
}

// =============================================================================
// Export all adapters
// =============================================================================

export const typeAdapters = {
  // ROI
  adaptROISummaryToAnalytics,
  adaptUnifiedROIToAnalytics,
  adaptValueBreakdownToAnalytics,

  // Time Saved
  adaptTimeSavedSummaryToAnalytics,
  adaptTimeSavedByTaskToAnalytics,
  adaptTimeSavedTrendToAnalytics,
  adaptTimeSavedDashboardToAnalytics,

  // Satisfaction
  adaptSatisfactionMetricsToAnalytics,
  adaptNPSToAnalytics,
  adaptFeedbackListToAnalytics,

  // Traces
  adaptTraceListToAnalytics,
  adaptTraceDetailToAnalytics,

  // Health
  adaptHealthToAnalytics,
};

export default typeAdapters;
