// apps/frontend/src/main/ipc-handlers/artifact-handlers.ts
/**
 * Artifact Storage IPC Handlers
 *
 * Provides access to locally stored full artifact content.
 * Artifacts are stored in .auto-claude/artifacts/ with full content,
 * while Langfuse only receives truncated references.
 */

import { ipcMain } from 'electron';
import path from 'path';
import fs from 'fs';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { projectStore } from '../project-store';
import type { IPCResult } from '../../shared/types';

// Artifact file structure (matches Python backend)
interface LocalArtifact {
  id: string;
  type: string;
  format?: string;
  content: string;
  value_usd: number;
  description?: string;
  tab?: string;
  created_at: string;
  trace_id?: string;
  spec_id?: string;
  project_id?: string;
  agent_type?: string;
  session_num?: number;
  metadata?: Record<string, unknown>;
}

// Index structure for fast lookups
interface ArtifactIndex {
  last_updated: string;
  total_count: number;
  by_date: Record<string, string[]>;  // date -> artifact IDs
  by_spec: Record<string, string[]>;  // spec_id -> artifact IDs
  by_trace: Record<string, string[]>; // trace_id -> artifact IDs
}

// Filter options for listing artifacts
interface ArtifactFilters {
  spec_id?: string;
  trace_id?: string;
  type?: string;
  date?: string;
  limit?: number;
}

/**
 * Get the artifacts directory for a project
 */
function getArtifactsDir(projectPath: string): string {
  return path.join(projectPath, '.auto-claude', 'artifacts');
}

/**
 * Load the artifact index
 */
function loadIndex(artifactsDir: string): ArtifactIndex | null {
  const indexPath = path.join(artifactsDir, 'index.json');
  try {
    if (fs.existsSync(indexPath)) {
      const content = fs.readFileSync(indexPath, 'utf-8');
      return JSON.parse(content);
    }
  } catch (error) {
    console.error('[artifact-handlers] Failed to load index:', error);
  }
  return null;
}

/**
 * Load a single artifact by ID
 */
function loadArtifact(artifactsDir: string, artifactId: string): LocalArtifact | null {
  // Try to find artifact by walking date directories
  try {
    const dirs = fs.readdirSync(artifactsDir, { withFileTypes: true });
    for (const dir of dirs) {
      if (dir.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(dir.name)) {
        const artifactPath = path.join(artifactsDir, dir.name, `${artifactId}.json`);
        if (fs.existsSync(artifactPath)) {
          const content = fs.readFileSync(artifactPath, 'utf-8');
          return JSON.parse(content);
        }
      }
    }
  } catch (error) {
    console.error(`[artifact-handlers] Failed to load artifact ${artifactId}:`, error);
  }
  return null;
}

/**
 * List artifacts with optional filters
 */
function listArtifacts(
  artifactsDir: string,
  filters?: ArtifactFilters
): LocalArtifact[] {
  const artifacts: LocalArtifact[] = [];
  const index = loadIndex(artifactsDir);

  // Use index for filtered queries
  let artifactIds: string[] = [];

  if (index) {
    if (filters?.spec_id && index.by_spec[filters.spec_id]) {
      artifactIds = index.by_spec[filters.spec_id];
    } else if (filters?.trace_id && index.by_trace[filters.trace_id]) {
      artifactIds = index.by_trace[filters.trace_id];
    } else if (filters?.date && index.by_date[filters.date]) {
      artifactIds = index.by_date[filters.date];
    } else {
      // Get all artifact IDs from index
      for (const ids of Object.values(index.by_date)) {
        artifactIds.push(...ids);
      }
    }
  }

  // Load artifacts
  const limit = filters?.limit || 100;
  for (const artifactId of artifactIds.slice(0, limit)) {
    const artifact = loadArtifact(artifactsDir, artifactId);
    if (artifact) {
      // Apply type filter if specified
      if (filters?.type && artifact.type !== filters.type) {
        continue;
      }
      artifacts.push(artifact);
    }
  }

  // Sort by created_at descending (newest first)
  artifacts.sort((a, b) => {
    const dateA = new Date(a.created_at).getTime();
    const dateB = new Date(b.created_at).getTime();
    return dateB - dateA;
  });

  return artifacts;
}

/**
 * Get project path from project ID, name, or path
 *
 * Supports multiple lookup strategies:
 * 1. First try by UUID (standard project ID)
 * 2. Then try by project name (folder name)
 * 3. Finally check if it's already a valid path
 */
function getProjectPath(projectIdOrName?: string): string | undefined {
  if (!projectIdOrName) return undefined;

  // Strategy 1: Try by UUID
  const projectById = projectStore.getProject(projectIdOrName);
  if (projectById?.path) {
    return projectById.path;
  }

  // Strategy 2: Try by project name (folder name)
  const projects = projectStore.getProjects();
  const projectByName = projects.find(p => p.name === projectIdOrName);
  if (projectByName?.path) {
    return projectByName.path;
  }

  // Strategy 3: Check if it's already a valid path with artifacts
  if (projectIdOrName.startsWith('/') && fs.existsSync(projectIdOrName)) {
    const artifactsDir = getArtifactsDir(projectIdOrName);
    if (fs.existsSync(artifactsDir)) {
      return projectIdOrName;
    }
  }

  console.warn(`[artifact-handlers] Could not find project for: ${projectIdOrName}`);
  return undefined;
}

/**
 * Register artifact IPC handlers
 */
export function setupArtifactHandlers(): void {
  // Get single artifact by ID
  ipcMain.handle(
    IPC_CHANNELS.ARTIFACT_GET,
    async (_, projectId: string, artifactId: string): Promise<IPCResult<LocalArtifact>> => {
      try {
        const projectPath = getProjectPath(projectId);
        if (!projectPath) {
          return { success: false, error: 'Project not found' };
        }

        const artifactsDir = getArtifactsDir(projectPath);
        if (!fs.existsSync(artifactsDir)) {
          return { success: false, error: 'No artifacts directory found' };
        }

        const artifact = loadArtifact(artifactsDir, artifactId);
        if (!artifact) {
          return { success: false, error: 'Artifact not found' };
        }

        return { success: true, data: artifact };
      } catch (error) {
        console.error('[artifact-handlers] Error getting artifact:', error);
        return { success: false, error: String(error) };
      }
    }
  );

  // List artifacts with filters
  ipcMain.handle(
    IPC_CHANNELS.ARTIFACT_LIST,
    async (_, projectId: string, filters?: ArtifactFilters): Promise<IPCResult<LocalArtifact[]>> => {
      try {
        const projectPath = getProjectPath(projectId);
        if (!projectPath) {
          return { success: false, error: 'Project not found' };
        }

        const artifactsDir = getArtifactsDir(projectPath);
        if (!fs.existsSync(artifactsDir)) {
          // Return empty list if no artifacts yet (not an error)
          return { success: true, data: [] };
        }

        const artifacts = listArtifacts(artifactsDir, filters);
        return { success: true, data: artifacts };
      } catch (error) {
        console.error('[artifact-handlers] Error listing artifacts:', error);
        return { success: false, error: String(error) };
      }
    }
  );

  // Get artifacts by trace ID
  ipcMain.handle(
    IPC_CHANNELS.ARTIFACT_GET_BY_TRACE,
    async (_, projectId: string, traceId: string): Promise<IPCResult<LocalArtifact[]>> => {
      try {
        const projectPath = getProjectPath(projectId);
        if (!projectPath) {
          return { success: false, error: 'Project not found' };
        }

        const artifactsDir = getArtifactsDir(projectPath);
        if (!fs.existsSync(artifactsDir)) {
          return { success: true, data: [] };
        }

        const artifacts = listArtifacts(artifactsDir, { trace_id: traceId });
        return { success: true, data: artifacts };
      } catch (error) {
        console.error('[artifact-handlers] Error getting artifacts by trace:', error);
        return { success: false, error: String(error) };
      }
    }
  );

  console.log('[artifact-handlers] Artifact IPC handlers registered');
}
