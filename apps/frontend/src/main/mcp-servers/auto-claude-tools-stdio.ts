#!/usr/bin/env node
/**
 * Auto-Claude Tools MCP Server - STDIO Transport
 *
 * This is Option A: Standalone subprocess that communicates via stdio.
 * The server exposes Auto-Claude internal functionality as MCP tools.
 *
 * Tools communicate back to Electron main process via HTTP API.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

// HTTP client to communicate with Electron main process
const ELECTRON_API_PORT = process.env.ELECTRON_API_PORT || '9824';
const ELECTRON_API_URL = `http://localhost:${ELECTRON_API_PORT}/api`;

/**
 * Fetch data from Electron main process
 */
async function fetchFromElectron(endpoint: string, params?: Record<string, string>): Promise<any> {
  const url = new URL(`${ELECTRON_API_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, value);
    });
  }

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Electron API error: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create and configure MCP server
 */
async function main() {
  const server = new McpServer({
    name: 'auto-claude-tools',
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
      },
      outputSchema: {
        specId: z.string(),
        status: z.enum(['pending', 'running', 'completed', 'failed']),
        phase: z.string().optional(),
        progress: z.number().min(0).max(100),
        currentTask: z.string().optional(),
        startedAt: z.string().optional(),
        completedAt: z.string().optional()
      }
    },
    async ({ specId }) => {
      try {
        const data = await fetchFromElectron('/build-progress', { specId });

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(data, null, 2)
          }],
          structuredContent: data
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
      },
      outputSchema: {
        projectPath: z.string(),
        projectName: z.string(),
        techStack: z.array(z.string()),
        recentSpecs: z.array(z.object({
          id: z.string(),
          name: z.string(),
          status: z.string()
        })),
        codebaseStats: z.object({
          totalFiles: z.number(),
          totalLines: z.number(),
          languages: z.record(z.number())
        }).optional()
      }
    },
    async ({ projectPath, includeMemory }) => {
      try {
        const params: Record<string, string> = {};
        if (projectPath) params.projectPath = projectPath;
        if (includeMemory) params.includeMemory = 'true';

        const data = await fetchFromElectron('/context', params);

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(data, null, 2)
          }],
          structuredContent: data
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
        caseSensitive: z.boolean().default(false),
        maxResults: z.number().min(1).max(100).default(20)
      },
      outputSchema: {
        query: z.string(),
        totalMatches: z.number(),
        results: z.array(z.object({
          file: z.string(),
          line: z.number(),
          column: z.number(),
          match: z.string(),
          context: z.string().optional()
        }))
      }
    },
    async ({ query, filePattern, caseSensitive, maxResults }) => {
      try {
        const params: Record<string, string> = { query };
        if (filePattern) params.filePattern = filePattern;
        if (caseSensitive) params.caseSensitive = 'true';
        if (maxResults) params.maxResults = String(maxResults);

        const data = await fetchFromElectron('/search-code', params);

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(data, null, 2)
          }],
          structuredContent: data
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

  // Connect via stdio transport
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error('[Auto-Claude Tools STDIO] Server started and listening on stdio');
}

// Run server
main().catch((error) => {
  console.error('[Auto-Claude Tools STDIO] Fatal error:', error);
  process.exit(1);
});
