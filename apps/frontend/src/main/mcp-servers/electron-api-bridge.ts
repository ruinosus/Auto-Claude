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

const API_PORT = process.env.ELECTRON_API_PORT || 9824;

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
