/**
 * Auto-Claude Tools MCP Server - HTTP Transport
 *
 * This is Option B: In-process server that runs within Electron main process.
 * Uses HTTP transport on localhost for communication.
 * Has DIRECT access to Electron IPC handlers and data.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import express from 'express';
import type { Request as ExpressRequest, Response as ExpressResponse } from 'express-serve-static-core';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { randomUUID } from 'node:crypto';
import { z } from 'zod';
import { ipcMain } from 'electron';
import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// ARTIFACT STORAGE HELPERS (same as in electron-api-bridge.ts)
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

function loadArtifactDirect(projectPath: string, artifactId: string): LocalArtifact | null {
  const artifactsDir = getArtifactsDir(projectPath);
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

  // Fallback: search date folders
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

function listArtifactsDirect(
  projectPath: string,
  filters?: { spec_id?: string; trace_id?: string; type?: string; limit?: number }
): LocalArtifact[] {
  const artifactsDir = getArtifactsDir(projectPath);
  const artifacts: LocalArtifact[] = [];

  if (!fs.existsSync(artifactsDir)) return artifacts;

  const folders = fs.readdirSync(artifactsDir).filter(f =>
    fs.statSync(path.join(artifactsDir, f)).isDirectory()
  );

  for (const folder of folders) {
    const folderPath = path.join(artifactsDir, folder);
    const files = fs.readdirSync(folderPath).filter(f => f.endsWith('.json'));

    for (const file of files) {
      try {
        const artifact = JSON.parse(fs.readFileSync(path.join(folderPath, file), 'utf-8'));
        if (filters?.spec_id && artifact.spec_id !== filters.spec_id) continue;
        if (filters?.trace_id && artifact.trace_id !== filters.trace_id) continue;
        if (filters?.type && artifact.type !== filters.type) continue;
        artifacts.push(artifact);
        if (filters?.limit && artifacts.length >= filters.limit) return artifacts;
      } catch { /* skip */ }
    }
  }
  return artifacts;
}

const PORT = 9823; // Fixed port for auto-claude-tools MCP server

/**
 * Access Electron IPC handlers directly
 */
async function getFromElectron(channel: string, ...args: any[]): Promise<any> {
  // Simulate IPC call by directly invoking handlers
  // In real implementation, you'd import the actual handler functions
  return new Promise((resolve, reject) => {
    // This is a simplified version - in production you'd use the actual IPC mechanism
    const handlers = (ipcMain as any)._events;
    const handler = handlers[channel];

    if (!handler) {
      reject(new Error(`No IPC handler found for channel: ${channel}`));
      return;
    }

    // Call handler and get result
    try {
      const result = handler({ sender: { send: () => {} } }, ...args);
      if (result instanceof Promise) {
        result.then(resolve).catch(reject);
      } else {
        resolve(result);
      }
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * Create MCP server instance
 */
export function createAutoClaudeToolsServer(): McpServer {
  const server = new McpServer({
    name: 'auto-claude-tools-http',
    version: '1.0.0'
  });

  // Tool 1: Get Build Progress
  server.registerTool(
    'get_build_progress',
    {
      title: 'Get Build Progress',
      description: 'Get current build progress and status for a spec',
      inputSchema: {
        specId: z.string().describe('Spec ID to check progress for (e.g., "001", "spec-001")')
      }
    },
    async ({ specId }) => {
      try {
        // Direct access to Electron data - no HTTP bridge needed!
        // In production, you'd call actual task manager functions
        const mockData = {
          specId,
          status: 'running' as const,
          phase: 'implementation',
          progress: 65,
          currentTask: 'Implementing feature X',
          startedAt: new Date().toISOString()
        };

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(mockData, null, 2)
          }],
          structuredContent: mockData
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error fetching build progress: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 2: Get Project Context
  server.registerTool(
    'get_context',
    {
      title: 'Get Project Context',
      description: 'Get project context and codebase information',
      inputSchema: {
        projectPath: z.string().describe('Path to project directory').optional(),
        includeMemory: z.boolean().describe('Include memory/insights from previous builds').default(false)
      }
    },
    async ({ projectPath, includeMemory }) => {
      try {
        // Direct access to project data
        const mockData = {
          projectPath: projectPath || '/path/to/project',
          projectName: 'Auto-Claude',
          techStack: ['TypeScript', 'React', 'Electron', 'Python'],
          recentSpecs: [
            { id: '001', name: 'MCP Integration', status: 'completed' },
            { id: '002', name: 'Skills Module', status: 'running' }
          ],
          codebaseStats: {
            totalFiles: 156,
            totalLines: 12450,
            languages: {
              TypeScript: 8500,
              Python: 3200,
              JSON: 750
            }
          }
        };

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(mockData, null, 2)
          }],
          structuredContent: mockData
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error fetching context: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 3: Search Code
  server.registerTool(
    'search_code',
    {
      title: 'Search Code',
      description: 'Search for code patterns in the project codebase',
      inputSchema: {
        query: z.string().describe('Search query (supports regex)'),
        filePattern: z.string().describe('File pattern to search in (e.g., "*.ts", "src/**/*.py")').optional(),
        caseSensitive: z.boolean().describe('Case sensitive search').default(false),
        maxResults: z.number().min(1).max(100).describe('Maximum number of results').default(20)
      }
    },
    async ({ query, filePattern, caseSensitive, maxResults }) => {
      try {
        // Direct access to search functionality
        const mockData = {
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
          ]
        };

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(mockData, null, 2)
          }],
          structuredContent: mockData
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error searching code: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 4: Get Artifact
  server.registerTool(
    'get_artifact',
    {
      title: 'Get Artifact',
      description: 'Get a single artifact by ID with FULL content from local storage. Artifacts contain AI-generated outputs like code, reviews, plans, and insights.',
      inputSchema: {
        artifact_id: z.string().describe('The artifact ID (e.g., "art_abc123def456")'),
        project_path: z.string().describe('Path to the project directory')
      }
    },
    async ({ artifact_id, project_path }) => {
      try {
        const artifact = loadArtifactDirect(project_path, artifact_id);
        if (!artifact) {
          return {
            content: [{
              type: 'text',
              text: `Artifact not found: ${artifact_id}`
            }],
            isError: true
          };
        }
        return {
          content: [{
            type: 'text',
            text: JSON.stringify(artifact, null, 2)
          }],
          structuredContent: artifact
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error fetching artifact: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 5: List Artifacts
  server.registerTool(
    'list_artifacts',
    {
      title: 'List Artifacts',
      description: 'List all artifacts from local storage with optional filtering. Returns full content for each artifact.',
      inputSchema: {
        project_path: z.string().describe('Path to the project directory'),
        spec_id: z.string().describe('Filter by spec ID').optional(),
        trace_id: z.string().describe('Filter by Langfuse trace ID').optional(),
        type: z.string().describe('Filter by artifact type (e.g., "code_implementation", "qa_finding", "insight")').optional(),
        limit: z.number().min(1).max(100).describe('Maximum number of artifacts to return').default(50)
      }
    },
    async ({ project_path, spec_id, trace_id, type, limit }) => {
      try {
        const artifacts = listArtifactsDirect(project_path, { spec_id, trace_id, type, limit });
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              count: artifacts.length,
              artifacts
            }, null, 2)
          }],
          structuredContent: { count: artifacts.length, artifacts }
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error listing artifacts: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 6: Get Artifacts by Trace
  server.registerTool(
    'get_artifacts_by_trace',
    {
      title: 'Get Artifacts by Trace',
      description: 'Get all artifacts associated with a specific Langfuse trace ID. Useful for seeing all outputs from a single agent session.',
      inputSchema: {
        project_path: z.string().describe('Path to the project directory'),
        trace_id: z.string().describe('Langfuse trace ID to filter by')
      }
    },
    async ({ project_path, trace_id }) => {
      try {
        const artifacts = listArtifactsDirect(project_path, { trace_id });
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              trace_id,
              count: artifacts.length,
              artifacts
            }, null, 2)
          }],
          structuredContent: { trace_id, count: artifacts.length, artifacts }
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error fetching artifacts by trace: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 7: Get Artifact Content
  server.registerTool(
    'get_artifact_content',
    {
      title: 'Get Artifact Content',
      description: 'Get only the content of an artifact without metadata. Useful for directly accessing code, reviews, or other generated content.',
      inputSchema: {
        artifact_id: z.string().describe('The artifact ID'),
        project_path: z.string().describe('Path to the project directory')
      }
    },
    async ({ artifact_id, project_path }) => {
      try {
        const artifact = loadArtifactDirect(project_path, artifact_id);
        if (!artifact) {
          return {
            content: [{
              type: 'text',
              text: `Artifact not found: ${artifact_id}`
            }],
            isError: true
          };
        }
        return {
          content: [{
            type: 'text',
            text: artifact.content
          }]
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error fetching artifact content: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  return server;
}

/**
 * Start HTTP server for MCP
 */
export function startAutoClaudeToolsHttpServer(): ReturnType<typeof express> {
  const app = express();
  app.use(express.json());

  const server = createAutoClaudeToolsServer();
  const transports: Record<string, StreamableHTTPServerTransport> = {};

  // Handle MCP requests
  app.post('/mcp', async (req: ExpressRequest, res: ExpressResponse) => {
    const sessionId = req.headers['mcp-session-id'] as string | undefined;
    let transport: StreamableHTTPServerTransport;

    if (sessionId && transports[sessionId]) {
      // Reuse existing session
      transport = transports[sessionId];
    } else {
      // New session
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        onsessioninitialized: (id: string) => {
          transports[id] = transport;
          console.log('[Auto-Claude Tools HTTP] Session initialized:', id);
        },
        onsessionclosed: (id: string) => {
          delete transports[id];
          console.log('[Auto-Claude Tools HTTP] Session closed:', id);
        }
      });

      transport.onclose = () => {
        if (transport.sessionId) {
          delete transports[transport.sessionId];
        }
      };

      await server.connect(transport);
    }

    // Cast to IncomingMessage/ServerResponse for MCP SDK compatibility
    await transport.handleRequest(
      req as unknown as IncomingMessage,
      res as unknown as ServerResponse,
      req.body
    );
  });

  // Health check endpoint
  app.get('/health', (_req: ExpressRequest, res: ExpressResponse) => {
    res.json({
      status: 'healthy',
      server: 'auto-claude-tools-http',
      version: '1.0.0',
      uptime: process.uptime()
    });
  });

  app.listen(PORT, () => {
    console.log(`[Auto-Claude Tools HTTP] Server running on http://localhost:${PORT}/mcp`);
  });

  return app;
}
