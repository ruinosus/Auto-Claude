// apps/frontend/src/shared/types/roi.ts

/**
 * ROI System Types
 */

export type Currency = 'USD' | 'BRL' | 'EUR';

export interface ROISettings {
  developerHourlyRate: number;
  primaryCurrency: Currency;
  secondaryCurrency: Currency | null;
  exchangeRate: number;
  exchangeRateUpdatedAt: string | null;
  autoEstimateHours: boolean;
  minutesPerLine: number;
}

export interface ProjectROISettings {
  projectId: string;
  developerHourlyRate: number | null;
  updatedAt: string;
}

export interface SpecROI {
  specId: string;
  projectId: string;

  // User inputs (with defaults)
  estimatedBusinessValue: number;
  estimatedHoursManual: number | null;
  developerRateOverride: number | null;

  // Auto-tracked
  actualCost: number;
  totalTokens: number;
  linesAdded: number;
  linesRemoved: number;
  filesChanged: number;
  executionTimeSeconds: number;
  qaAttempts: number;
  qaPassed: boolean;

  // Timestamps
  createdAt: string;
  completedAt: string | null;
}

export interface ROIMetrics {
  // Per-spec calculated
  effectiveHourlyRate: number;
  estimatedManualCost: number;
  costSavings: number;
  roiPercentage: number;
  costPerLine: number;
  efficiencyScore: number;
}

export interface ROIAggregateMetrics {
  totalROI: number;
  totalSavings: number;
  totalHoursSaved: number;
  totalCost: number;
  successRate: number;
  specsCount: number;
}

export interface SpecROIWithMetrics extends SpecROI {
  metrics: ROIMetrics;
}

// Default values
export const DEFAULT_ROI_SETTINGS: ROISettings = {
  developerHourlyRate: 75,
  primaryCurrency: 'USD',
  secondaryCurrency: 'BRL',
  exchangeRate: 6.2,
  exchangeRateUpdatedAt: null,
  autoEstimateHours: true,
  minutesPerLine: 2.5
};
