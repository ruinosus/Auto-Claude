/**
 * Auto-Claude Tools MCP Server - HTTP Transport
 *
 * This is Option B: In-process server that runs within Electron main process.
 * Uses HTTP transport on localhost for communication.
 * Has DIRECT access to Electron IPC handlers and data.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import express, { Request, Response } from 'express';
import { randomUUID } from 'node:crypto';
import { ipcMain } from 'electron';

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
        type: 'object',
        properties: {
          specId: {
            type: 'string',
            description: 'Spec ID to check progress for (e.g., "001", "spec-001")'
          }
        },
        required: ['specId']
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
        type: 'object',
        properties: {
          projectPath: {
            type: 'string',
            description: 'Path to project directory'
          },
          includeMemory: {
            type: 'boolean',
            description: 'Include memory/insights from previous builds',
            default: false
          }
        }
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
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'Search query (supports regex)'
          },
          filePattern: {
            type: 'string',
            description: 'File pattern to search in (e.g., "*.ts", "src/**/*.py")'
          },
          caseSensitive: {
            type: 'boolean',
            description: 'Case sensitive search',
            default: false
          },
          maxResults: {
            type: 'number',
            description: 'Maximum number of results',
            minimum: 1,
            maximum: 100,
            default: 20
          }
        },
        required: ['query']
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

  return server;
}

/**
 * Start HTTP server for MCP
 */
export function startAutoClaudeToolsHttpServer(): express.Application {
  const app = express();
  app.use(express.json());

  const server = createAutoClaudeToolsServer();
  const transports: Record<string, StreamableHTTPServerTransport> = {};

  // Handle MCP requests
  app.post('/mcp', async (req: Request, res: Response) => {
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

    await transport.handleRequest(req, res, req.body);
  });

  // Health check endpoint
  app.get('/health', (_req: Request, res: Response) => {
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
