/**
 * Electron API Bridge for STDIO MCP Server
 *
 * This HTTP server provides an API bridge between the STDIO MCP server
 * (running as a subprocess) and the Electron main process.
 *
 * The STDIO server calls this API to get data from Electron.
 */

import express from 'express';
import type { Request as ExpressRequest, Response as ExpressResponse } from 'express-serve-static-core';
import { ipcMain } from 'electron';
import * as fs from 'fs';
import * as path from 'path';

const API_PORT = process.env.ELECTRON_API_PORT || 9824;

// ============================================================================
// ARTIFACT STORAGE HELPERS
// ============================================================================

interface LocalArtifact {
  id: string;
  type: string;
  format?: string;
  content: string;
  value_usd?: number;
  description?: string;
  created_at?: string;
  trace_id?: string;
  spec_id?: string;
  project_id?: string;
  agent_type?: string;
  session_num?: number;
}

interface ArtifactFilters {
  spec_id?: string;
  trace_id?: string;
  type?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
}

function getArtifactsDir(projectPath: string): string {
  return path.join(projectPath, '.auto-claude', 'artifacts');
}

function loadArtifactIndex(projectPath: string): Record<string, any> {
  const indexPath = path.join(getArtifactsDir(projectPath), 'index.json');
  if (fs.existsSync(indexPath)) {
    try {
      return JSON.parse(fs.readFileSync(indexPath, 'utf-8'));
    } catch {
      return {};
    }
  }
  return {};
}

function loadArtifact(projectPath: string, artifactId: string): LocalArtifact | null {
  const artifactsDir = getArtifactsDir(projectPath);

  // Try to find via index first
  const index = loadArtifactIndex(projectPath);
  if (index[artifactId]?.path) {
    const fullPath = path.join(projectPath, index[artifactId].path);
    if (fs.existsSync(fullPath)) {
      try {
        return JSON.parse(fs.readFileSync(fullPath, 'utf-8'));
      } catch {
        return null;
      }
    }
  }

  // Fallback: search in date folders
  if (fs.existsSync(artifactsDir)) {
    const folders = fs.readdirSync(artifactsDir).filter(f =>
      fs.statSync(path.join(artifactsDir, f)).isDirectory()
    );

    for (const folder of folders) {
      const artifactPath = path.join(artifactsDir, folder, `${artifactId}.json`);
      if (fs.existsSync(artifactPath)) {
        try {
          return JSON.parse(fs.readFileSync(artifactPath, 'utf-8'));
        } catch {
          return null;
        }
      }
    }
  }

  return null;
}

function listArtifacts(projectPath: string, filters?: ArtifactFilters): LocalArtifact[] {
  const artifactsDir = getArtifactsDir(projectPath);
  const artifacts: LocalArtifact[] = [];

  if (!fs.existsSync(artifactsDir)) {
    return artifacts;
  }

  const folders = fs.readdirSync(artifactsDir).filter(f => {
    const fullPath = path.join(artifactsDir, f);
    return fs.statSync(fullPath).isDirectory();
  });

  // Filter by date range
  const filteredFolders = folders.filter(folder => {
    if (filters?.date_from && folder < filters.date_from) return false;
    if (filters?.date_to && folder > filters.date_to) return false;
    return true;
  });

  for (const folder of filteredFolders) {
    const folderPath = path.join(artifactsDir, folder);
    const files = fs.readdirSync(folderPath).filter(f => f.endsWith('.json'));

    for (const file of files) {
      try {
        const artifact = JSON.parse(
          fs.readFileSync(path.join(folderPath, file), 'utf-8')
        );

        // Apply filters
        if (filters?.spec_id && artifact.spec_id !== filters.spec_id) continue;
        if (filters?.trace_id && artifact.trace_id !== filters.trace_id) continue;
        if (filters?.type && artifact.type !== filters.type) continue;

        artifacts.push(artifact);

        if (filters?.limit && artifacts.length >= filters.limit) {
          return artifacts;
        }
      } catch {
        // Skip invalid files
      }
    }
  }

  return artifacts;
}

interface BuildProgressResponse {
  specId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  phase?: string;
  progress: number;
  currentTask?: string;
  startedAt?: string;
  completedAt?: string;
}

interface ProjectContextResponse {
  projectPath: string;
  projectName: string;
  techStack: string[];
  recentSpecs: Array<{
    id: string;
    name: string;
    status: string;
  }>;
  codebaseStats?: {
    totalFiles: number;
    totalLines: number;
    languages: Record<string, number>;
  };
}

interface SearchCodeResponse {
  query: string;
  totalMatches: number;
  results: Array<{
    file: string;
    line: number;
    column: number;
    match: string;
    context?: string;
  }>;
}

/**
 * Mock function to get build progress
 * TODO: Replace with actual implementation that queries task manager
 */
async function getBuildProgress(specId: string): Promise<BuildProgressResponse> {
  // In production, this would call actual Electron IPC handlers
  // For now, return mock data
  return {
    specId,
    status: 'running',
    phase: 'implementation',
    progress: 65,
    currentTask: 'Implementing feature X',
    startedAt: new Date().toISOString()
  };
}

/**
 * Mock function to get project context
 * TODO: Replace with actual implementation that queries project state
 */
async function getProjectContext(
  projectPath?: string,
  includeMemory?: boolean
): Promise<ProjectContextResponse> {
  // In production, this would call actual Electron IPC handlers
  return {
    projectPath: projectPath || '/path/to/project',
    projectName: 'Auto-Claude',
    techStack: ['TypeScript', 'React', 'Electron', 'Python'],
    recentSpecs: [
      { id: '001', name: 'MCP Integration', status: 'completed' },
      { id: '002', name: 'Skills Module', status: 'running' }
    ],
    codebaseStats: includeMemory ? {
      totalFiles: 156,
      totalLines: 12450,
      languages: {
        TypeScript: 8500,
        Python: 3200,
        JSON: 750
      }
    } : undefined
  };
}

/**
 * Mock function to search code
 * TODO: Replace with actual implementation using ripgrep or similar
 */
async function searchCode(
  query: string,
  filePattern?: string,
  caseSensitive?: boolean,
  maxResults?: number
): Promise<SearchCodeResponse> {
  // In production, this would use actual search functionality
  return {
    query,
    totalMatches: 5,
    results: [
      {
        file: 'src/components/MCPToolsList.tsx',
        line: 42,
        column: 10,
        match: query,
        context: `const result = await ${query}();`
      },
      {
        file: 'src/main/mcp-manager.ts',
        line: 156,
        column: 5,
        match: query,
        context: `// Using ${query} for MCP integration`
      }
    ].slice(0, maxResults || 20)
  };
}

/**
 * Start API bridge server
 */
export function startElectronApiBridge(): ReturnType<typeof express> {
  const app = express();
  app.use(express.json());

  // Endpoint: Get build progress
  app.get('/api/build-progress', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { specId } = req.query;

      if (!specId || typeof specId !== 'string') {
        res.status(400).json({ error: 'specId is required' });
        return;
      }

      const data = await getBuildProgress(specId);
      res.json(data);
    } catch (error) {
      console.error('[API Bridge] Error in /api/build-progress:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Get project context
  app.get('/api/context', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { projectPath, includeMemory } = req.query;

      const data = await getProjectContext(
        projectPath as string | undefined,
        includeMemory === 'true'
      );

      res.json(data);
    } catch (error) {
      console.error('[API Bridge] Error in /api/context:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Search code
  app.get('/api/search-code', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { query, filePattern, caseSensitive, maxResults } = req.query;

      if (!query || typeof query !== 'string') {
        res.status(400).json({ error: 'query is required' });
        return;
      }

      const data = await searchCode(
        query,
        filePattern as string | undefined,
        caseSensitive === 'true',
        maxResults ? parseInt(maxResults as string, 10) : undefined
      );

      res.json(data);
    } catch (error) {
      console.error('[API Bridge] Error in /api/search-code:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Update subtask status
  app.get('/api/update-subtask-status', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { subtask_id, status, notes } = req.query;
      console.log(`[API Bridge] Updating subtask ${subtask_id} to ${status}`);
      res.json({
        success: true,
        subtask_id,
        status,
        notes,
        updatedAt: new Date().toISOString()
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/update-subtask-status:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: Record discovery
  app.get('/api/record-discovery', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { file_path, description, category } = req.query;
      console.log(`[API Bridge] Recording discovery: ${file_path}`);
      res.json({
        success: true,
        discovery: { file_path, description, category },
        recordedAt: new Date().toISOString()
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/record-discovery:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: Record gotcha
  app.get('/api/record-gotcha', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { gotcha, context } = req.query;
      console.log(`[API Bridge] Recording gotcha: ${gotcha}`);
      res.json({
        success: true,
        gotcha: { gotcha, context },
        recordedAt: new Date().toISOString()
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/record-gotcha:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: Get session context
  app.get('/api/session-context', async (_req: ExpressRequest, res: ExpressResponse) => {
    try {
      res.json({
        sessionId: `session-${Date.now()}`,
        startedAt: new Date().toISOString(),
        discoveries: [],
        gotchas: [],
        patterns: []
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/session-context:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: Update QA status
  app.get('/api/update-qa-status', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { status, issues, tests_passed } = req.query;
      console.log(`[API Bridge] Updating QA status to ${status}`);
      res.json({
        success: true,
        status,
        issues: issues ? JSON.parse(issues as string) : [],
        tests_passed: tests_passed ? JSON.parse(tests_passed as string) : {},
        updatedAt: new Date().toISOString()
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/update-qa-status:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // In-memory activity storage for ROI tracking
  const activities: Array<{
    activity_type: string;
    description: string;
    count: number;
    complexity?: string;
    timestamp: string;
  }> = [];

  // Endpoint: Report activity (ROI tracking)
  app.get('/api/report-activity', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { activity_type, description, count, complexity } = req.query;
      const activity = {
        activity_type: activity_type as string,
        description: description as string,
        count: count ? parseInt(count as string, 10) : 1,
        complexity: complexity as string | undefined,
        timestamp: new Date().toISOString()
      };
      activities.push(activity);
      console.log(`[API Bridge] Activity reported: ${activity_type} - ${description}`);
      res.json({
        success: true,
        activity,
        totalActivities: activities.length
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/report-activity:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: Get activity summary
  app.get('/api/activity-summary', async (_req: ExpressRequest, res: ExpressResponse) => {
    try {
      // Group activities by type
      const summary = activities.reduce((acc, activity) => {
        const type = activity.activity_type;
        if (!acc[type]) {
          acc[type] = { count: 0, items: [] };
        }
        acc[type].count += activity.count;
        acc[type].items.push(activity);
        return acc;
      }, {} as Record<string, { count: number; items: typeof activities }>);

      res.json({
        totalActivities: activities.length,
        summary,
        generatedAt: new Date().toISOString()
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/activity-summary:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: List activity types
  app.get('/api/activity-types', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { category } = req.query;

      const activityTypes = {
        execution: [
          { type: 'file_created', value: 15, description: 'New file created' },
          { type: 'file_modified', value: 5, description: 'File modified' },
          { type: 'bug_fixed', value: 30, description: 'Bug fixed' },
          { type: 'feature_implemented', value: 50, description: 'Feature implemented' },
          { type: 'test_written', value: 20, description: 'Test written' }
        ],
        decision: [
          { type: 'architecture_decision', value: 40, description: 'Architecture decision made' },
          { type: 'recommendation_made', value: 25, description: 'Recommendation made' },
          { type: 'trade_off_analyzed', value: 30, description: 'Trade-off analyzed' }
        ],
        prevention: [
          { type: 'issue_prevented', value: 45, description: 'Issue prevented before coding' },
          { type: 'security_vulnerability_avoided', value: 60, description: 'Security vulnerability avoided' },
          { type: 'performance_issue_prevented', value: 35, description: 'Performance issue prevented' }
        ],
        knowledge: [
          { type: 'documentation_created', value: 20, description: 'Documentation created' },
          { type: 'diagram_generated', value: 25, description: 'Diagram generated' },
          { type: 'insight_discovered', value: 15, description: 'Insight discovered' }
        ]
      };

      if (category && typeof category === 'string' && category in activityTypes) {
        res.json({ [category]: activityTypes[category as keyof typeof activityTypes] });
      } else {
        res.json(activityTypes);
      }
    } catch (error) {
      console.error('[API Bridge] Error in /api/activity-types:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // ============================================================================
  // ARTIFACT ENDPOINTS
  // ============================================================================

  // Endpoint: Get single artifact by ID
  app.get('/api/artifact/:id', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { id } = req.params;
      const { projectPath } = req.query;

      if (!projectPath || typeof projectPath !== 'string') {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      const artifact = loadArtifact(projectPath, id);
      if (!artifact) {
        res.status(404).json({ error: 'Artifact not found' });
        return;
      }

      res.json(artifact);
    } catch (error) {
      console.error('[API Bridge] Error in /api/artifact/:id:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: List artifacts with filters
  app.get('/api/artifacts', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { projectPath, spec_id, trace_id, type, date_from, date_to, limit } = req.query;

      if (!projectPath || typeof projectPath !== 'string') {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      const filters: ArtifactFilters = {};
      if (spec_id) filters.spec_id = spec_id as string;
      if (trace_id) filters.trace_id = trace_id as string;
      if (type) filters.type = type as string;
      if (date_from) filters.date_from = date_from as string;
      if (date_to) filters.date_to = date_to as string;
      if (limit) filters.limit = parseInt(limit as string, 10);

      const artifacts = listArtifacts(projectPath, filters);
      res.json({
        count: artifacts.length,
        artifacts: artifacts.map(a => ({
          id: a.id,
          type: a.type,
          format: a.format,
          value_usd: a.value_usd,
          description: a.description,
          created_at: a.created_at,
          spec_id: a.spec_id,
          trace_id: a.trace_id,
          agent_type: a.agent_type,
          content_preview: a.content?.substring(0, 200) + (a.content?.length > 200 ? '...' : '')
        }))
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/artifacts:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Get artifacts by trace ID
  app.get('/api/artifacts/trace/:traceId', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { traceId } = req.params;
      const { projectPath } = req.query;

      if (!projectPath || typeof projectPath !== 'string') {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      const artifacts = listArtifacts(projectPath, { trace_id: traceId });
      res.json({
        trace_id: traceId,
        count: artifacts.length,
        artifacts
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/artifacts/trace/:traceId:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Get artifact content only (for large artifacts)
  app.get('/api/artifact/:id/content', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { id } = req.params;
      const { projectPath } = req.query;

      if (!projectPath || typeof projectPath !== 'string') {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      const artifact = loadArtifact(projectPath, id);
      if (!artifact) {
        res.status(404).json({ error: 'Artifact not found' });
        return;
      }

      res.type(artifact.format === 'json' ? 'application/json' : 'text/plain');
      res.send(artifact.content);
    } catch (error) {
      console.error('[API Bridge] Error in /api/artifact/:id/content:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Health check
  app.get('/api/health', (_req: ExpressRequest, res: ExpressResponse) => {
    res.json({
      status: 'healthy',
      service: 'electron-api-bridge',
      uptime: process.uptime(),
      activitiesRecorded: activities.length
    });
  });

  app.listen(API_PORT, () => {
    console.log(`[Electron API Bridge] Server running on http://localhost:${API_PORT}/api`);
  });

  return app;
}
