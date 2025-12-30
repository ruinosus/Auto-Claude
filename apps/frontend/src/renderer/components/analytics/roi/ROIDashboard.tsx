/**
 * ROI Dashboard
 * =============
 *
 * Main ROI dashboard that delegates to the Langfuse-backed implementation.
 * The Langfuse version fetches data from the FastAPI analytics service
 * which uses Langfuse as the source of truth.
 */

import { LangfuseROIDashboard } from './LangfuseROIDashboard';

interface ROIDashboardProps {
  /** Project name (directory name) - used for Langfuse data isolation */
  projectName?: string;
}

/**
 * ROI Dashboard component
 *
 * Uses Langfuse as the primary data source for ROI analytics.
 * Falls back gracefully when Langfuse is not configured.
 *
 * IMPORTANT: projectName is the directory name, NOT the UUID.
 * The backend uses directory name for data isolation in Langfuse.
 */
export function ROIDashboard({ projectName }: ROIDashboardProps) {
  return <LangfuseROIDashboard projectName={projectName} />;
}
