/**
 * ROI Engine Hooks
 *
 * Provides React hooks for integrating with the new artifact-based ROI Engine.
 */

export {
  useROIEngine,
  groupArtifactsByRole,
  calculateTotalValue,
  formatCurrency,
  formatPercentage,
  ROLE_LABELS,
  ROLE_COLORS,
} from './useROIEngine';

export type {
  Role,
  Seniority,
  ArtifactValue,
  ROIResult,
  ROISummary,
  UseROIEngineOptions,
  UseROIEngineResult,
} from './useROIEngine';
