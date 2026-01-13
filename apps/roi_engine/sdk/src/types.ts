/**
 * ROI Engine TypeScript Types
 *
 * These types mirror the Python models:
 * - Core models: core/models.py (ArtifactValue, ROIResult)
 * - API models: api/models/ (request/response schemas)
 */

// ═══════════════════════════════════════════════════════════════
// Enums
// ═══════════════════════════════════════════════════════════════

/**
 * Roles that produce artifacts in a squad.
 */
export type Role =
  | 'developer'
  | 'qa'
  | 'devops'
  | 'pm'
  | 'architect'
  | 'tech_lead';

/**
 * Seniority levels for rate calculation.
 */
export type Seniority =
  | 'junior'
  | 'mid'
  | 'senior'
  | 'staff'
  | 'principal';

/**
 * Scope of ROI calculation.
 */
export type ROIScope = 'trace' | 'spec' | 'project';

// ═══════════════════════════════════════════════════════════════
// Core Models
// ═══════════════════════════════════════════════════════════════

/**
 * An artifact enriched with role-based value calculation.
 */
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

/**
 * Result of ROI calculation for a scope.
 */
export interface ROIResult {
  scope: ROIScope;
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

/**
 * Simplified ROI summary for quick display.
 */
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

// ═══════════════════════════════════════════════════════════════
// API Request Types
// ═══════════════════════════════════════════════════════════════

/**
 * Base request for ROI calculation.
 */
export interface ROIRequest {
  project_dir: string;
  token_cost?: number;
  squad_config_id?: string;
}

/**
 * Request to calculate ROI for a spec.
 */
export interface SpecROIRequest extends ROIRequest {
  spec_id: string;
}

/**
 * Request to calculate ROI for a trace.
 */
export interface TraceROIRequest extends ROIRequest {
  trace_id: string;
}

/**
 * Request to preview artifact value.
 */
export interface ArtifactValuePreviewRequest {
  artifact_type: string;
  seniority?: Seniority;
  project_dir?: string;
}

// ═══════════════════════════════════════════════════════════════
// API Response Types
// ═══════════════════════════════════════════════════════════════

/**
 * Response for artifact listing.
 */
export interface ArtifactListResponse {
  artifacts: ArtifactValue[];
  total_count: number;
  total_value: number;
}

/**
 * Response for artifact value preview.
 */
export interface ArtifactValuePreviewResponse {
  artifact_type: string;
  role: Role;
  seniority: Seniority;
  estimated_hours: number;
  hourly_rate: number;
  calculated_value: number;
  formula: string;
}

/**
 * Response for rate table.
 */
export interface RateTableResponse {
  rates: Record<Seniority, Record<Role, number>>;
  description: string;
}

/**
 * Artifact type with role mapping.
 */
export interface ArtifactTypeInfo {
  type: string;
  role: Role;
  estimated_hours: number;
  role_description: string;
}

/**
 * Response for artifact types listing.
 */
export interface ArtifactTypesResponse {
  types: ArtifactTypeInfo[];
  total_count: number;
}

/**
 * Role information.
 */
export interface RoleInfo {
  id: Role;
  name: string;
  description: string;
}

/**
 * Response for roles listing.
 */
export interface RolesResponse {
  roles: RoleInfo[];
}

/**
 * Health check response.
 */
export interface HealthResponse {
  status: 'ok' | 'error';
  version: string;
  langfuse_available: boolean;
}

/**
 * Error response.
 */
export interface ErrorResponse {
  error: string;
  detail?: string;
}

// ═══════════════════════════════════════════════════════════════
// Hook Types
// ═══════════════════════════════════════════════════════════════

/**
 * Options for useROI hook.
 */
export interface UseROIOptions {
  specId?: string;
  traceId?: string;
  projectDir: string;
  tokenCost?: number;
  enabled?: boolean;
}

/**
 * Result of useROI hook.
 */
export interface UseROIResult {
  roi: ROIResult | null;
  summary: ROISummary | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Options for useArtifacts hook.
 */
export interface UseArtifactsOptions {
  specId?: string;
  traceId?: string;
  projectDir: string;
  artifactType?: string;
  limit?: number;
  enabled?: boolean;
}

/**
 * Result of useArtifacts hook.
 */
export interface UseArtifactsResult {
  artifacts: ArtifactValue[];
  totalCount: number;
  totalValue: number;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

// ═══════════════════════════════════════════════════════════════
// Component Props
// ═══════════════════════════════════════════════════════════════

/**
 * Props for ROISummaryCard component.
 */
export interface ROISummaryCardProps {
  roi: ROIResult | ROISummary | null;
  loading?: boolean;
  showBreakdown?: boolean;
  className?: string;
}

/**
 * Props for ArtifactsByRole component.
 */
export interface ArtifactsByRoleProps {
  artifacts: ArtifactValue[];
  onArtifactClick?: (artifact: ArtifactValue) => void;
  className?: string;
}

/**
 * Props for ValueBreakdown component.
 */
export interface ValueBreakdownProps {
  byRole?: Record<string, number>;
  byType?: Record<string, number>;
  tokenCost?: number;
  className?: string;
}

// ═══════════════════════════════════════════════════════════════
// Utility Types
// ═══════════════════════════════════════════════════════════════

/**
 * Role display information.
 */
export const ROLE_LABELS: Record<Role, string> = {
  developer: 'Developer',
  qa: 'QA Engineer',
  devops: 'DevOps Engineer',
  pm: 'Product Manager',
  architect: 'Architect',
  tech_lead: 'Tech Lead',
};

/**
 * Role colors for UI.
 */
export const ROLE_COLORS: Record<Role, string> = {
  developer: '#3B82F6', // blue
  qa: '#10B981',        // green
  devops: '#8B5CF6',    // purple
  pm: '#F59E0B',        // amber
  architect: '#EF4444', // red
  tech_lead: '#06B6D4', // cyan
};

/**
 * Seniority display labels.
 */
export const SENIORITY_LABELS: Record<Seniority, string> = {
  junior: 'Junior',
  mid: 'Mid-Level',
  senior: 'Senior',
  staff: 'Staff',
  principal: 'Principal',
};
