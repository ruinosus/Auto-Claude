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
