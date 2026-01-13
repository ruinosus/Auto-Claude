/**
 * @auto-claude/roi-sdk
 *
 * TypeScript SDK for Auto-Claude ROI Engine.
 *
 * Provides:
 * - Type-safe API client for ROI Engine REST API
 * - React hooks for data fetching
 * - UI components for displaying ROI metrics
 *
 * @example
 * ```tsx
 * import { useROI, useArtifacts, ROISummaryCard } from '@auto-claude/roi-sdk';
 *
 * function SpecAnalytics({ specId, projectDir }: Props) {
 *   const { roi, loading, error } = useROI({ specId, projectDir });
 *   const { artifacts } = useArtifacts({ specId, projectDir });
 *
 *   if (loading) return <Spinner />;
 *   if (error) return <Error message={error.message} />;
 *
 *   return <ROISummaryCard roi={roi} showBreakdown />;
 * }
 * ```
 */

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════
export type {
  // Enums
  Role,
  Seniority,
  ROIScope,
  // Core Models
  ArtifactValue,
  ROIResult,
  ROISummary,
  // Request Types
  ROIRequest,
  SpecROIRequest,
  TraceROIRequest,
  ArtifactValuePreviewRequest,
  // Response Types
  ArtifactListResponse,
  ArtifactValuePreviewResponse,
  RateTableResponse,
  ArtifactTypeInfo,
  ArtifactTypesResponse,
  RoleInfo,
  RolesResponse,
  HealthResponse,
  ErrorResponse,
  // Hook Types
  UseROIOptions,
  UseROIResult,
  UseArtifactsOptions,
  UseArtifactsResult,
  // Component Props
  ROISummaryCardProps,
  ArtifactsByRoleProps,
  ValueBreakdownProps,
} from './types';

// Constants
export { ROLE_LABELS, ROLE_COLORS, SENIORITY_LABELS } from './types';

// ═══════════════════════════════════════════════════════════════
// Client
// ═══════════════════════════════════════════════════════════════
export type { ROIClientConfig, ListArtifactsOptions } from './client';
export { ROIClient, getDefaultClient, createClient } from './client';

// ═══════════════════════════════════════════════════════════════
// Hooks
// ═══════════════════════════════════════════════════════════════
export {
  useROI,
  useArtifacts,
  groupArtifactsByRole,
  groupArtifactsByType,
  calculateGroupValue,
} from './hooks';

// ═══════════════════════════════════════════════════════════════
// Components
// ═══════════════════════════════════════════════════════════════
export { ROISummaryCard, ArtifactsByRole, ValueBreakdown } from './components';
