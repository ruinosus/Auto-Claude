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

  // Health check
  app.get('/api/health', (_req: ExpressRequest, res: ExpressResponse) => {
    res.json({
      status: 'healthy',
      service: 'electron-api-bridge',
      uptime: process.uptime()
    });
  });

  app.listen(API_PORT, () => {
    console.log(`[Electron API Bridge] Server running on http://localhost:${API_PORT}/api`);
  });

  return app;
}
