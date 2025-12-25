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
