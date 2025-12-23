import { ipcMain } from 'electron';
import type { MCPServer, MCPServerConfig, MCPTestConnectionResult } from '../shared/types/mcp';
import { updateEnvVars, getEnvPath, readEnvFile } from './mcp-config';

/**
 * Get built-in MCP server definitions
 */
function getBuiltInServers(): MCPServer[] {
  return [
    {
      id: 'context7',
      name: 'Context7',
      description: 'Real-time documentation lookup for any library',
      type: 'builtin',
      category: 'Documentation',
      status: 'connected',
      enabled: true,
      requiredEnvVars: [],
      capabilities: {
        tools: [
          { name: 'resolve-library-id', displayName: 'Resolve Library', description: 'Find library by name' },
          { name: 'get-library-docs', displayName: 'Get Documentation', description: 'Fetch library docs' }
        ]
      },
      toolCount: 2,
      promptCount: 0,
      resourceCount: 0,
      connectionType: 'sdk',
      icon: 'Book',
      color: 'blue'
    },
    {
      id: 'linear',
      name: 'Linear',
      description: 'Project management and issue tracking',
      type: 'builtin',
      category: 'Project Management',
      status: 'disabled',
      enabled: false,
      requiredEnvVars: ['LINEAR_API_KEY'],
      configUrl: 'https://linear.app/settings/api',
      capabilities: {},
      toolCount: 12,
      promptCount: 0,
      resourceCount: 0,
      connectionType: 'http',
      icon: 'Zap',
      color: 'blue'
    },
    {
      id: 'graphiti',
      name: 'Graphiti Memory',
      description: 'Knowledge graph memory with semantic search',
      type: 'builtin',
      category: 'Memory',
      status: 'disabled',
      enabled: false,
      requiredEnvVars: ['GRAPHITI_MCP_URL'],
      optionalEnvVars: ['GRAPHITI_LLM_PROVIDER', 'GRAPHITI_EMBEDDER_PROVIDER'],
      capabilities: {},
      toolCount: 5,
      promptCount: 3,
      resourceCount: 8,
      connectionType: 'http',
      pythonVersion: '3.12+',
      systemRequirements: ['real_ladybug', 'graphiti-core'],
      icon: 'Brain',
      color: 'purple'
    },
    {
      id: 'electron',
      name: 'Electron Automation',
      description: 'Desktop app testing via Chrome DevTools Protocol',
      type: 'builtin',
      category: 'Browser Automation',
      status: 'disabled',
      enabled: false,
      requiredEnvVars: ['ELECTRON_MCP_ENABLED'],
      optionalEnvVars: ['ELECTRON_DEBUG_PORT'],
      capabilities: {},
      toolCount: 4,
      promptCount: 0,
      resourceCount: 0,
      connectionType: 'http',
      icon: 'Monitor',
      color: 'blue'
    },
    {
      id: 'puppeteer',
      name: 'Puppeteer Browser',
      description: 'Web browser automation and testing',
      type: 'builtin',
      category: 'Browser Automation',
      status: 'disabled',
      enabled: false,
      requiredEnvVars: [],
      capabilities: {},
      toolCount: 8,
      promptCount: 0,
      resourceCount: 0,
      connectionType: 'stdio',
      icon: 'Globe',
      color: 'blue'
    },
    {
      id: 'auto-claude-tools',
      name: 'Auto-Claude Tools',
      description: 'Internal MCP server for build progress and context',
      type: 'internal',
      category: 'Internal',
      status: 'connected',
      enabled: true,
      requiredEnvVars: [],
      capabilities: {},
      toolCount: 6,
      promptCount: 0,
      resourceCount: 0,
      connectionType: 'sdk',
      icon: 'Wrench',
      color: 'gray'
    }
  ];
}

/**
 * Check if server is enabled by reading .env
 */
async function isServerEnabled(serverId: string, projectPath?: string): Promise<boolean> {
  const envPath = getEnvPath(projectPath);
  const envVars = await readEnvFile(envPath);

  // Check server-specific env vars
  switch (serverId) {
    case 'linear':
      return !!envVars.LINEAR_API_KEY;
    case 'graphiti':
      return !!envVars.GRAPHITI_MCP_URL;
    case 'electron':
      return envVars.ELECTRON_MCP_ENABLED === 'true';
    case 'context7':
    case 'auto-claude-tools':
      return true; // Always enabled
    case 'puppeteer':
      return false; // Auto-enabled based on project type
    default:
      return false;
  }
}

/**
 * Register MCP IPC handlers
 */
export function registerMCPHandlers() {
  /**
   * List all available MCP servers
   */
  ipcMain.handle('mcp:list', async (event, projectPath?: string) => {
    try {
      const servers = getBuiltInServers();

      // Check enabled status for each
      const serversWithStatus = await Promise.all(
        servers.map(async (server) => ({
          ...server,
          enabled: await isServerEnabled(server.id, projectPath)
        }))
      );

      return serversWithStatus;
    } catch (error) {
      console.error('Failed to list MCP servers:', error);
      return [];
    }
  });

  /**
   * Save MCP server configuration
   */
  ipcMain.handle('mcp:save-config', async (event, serverId: string, config: MCPServerConfig, projectPath?: string) => {
    try {
      const envPath = getEnvPath(projectPath);
      await updateEnvVars(envPath, config.envVars);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  });

  /**
   * Test connection (stub - returns success for now)
   */
  ipcMain.handle('mcp:test-connection', async (event, serverId: string, config: MCPServerConfig) => {
    // TODO: Implement actual connection testing
    return {
      success: true,
      status: 'connected' as const,
      message: 'Connection test not implemented yet',
      toolsFound: 0
    };
  });

  /**
   * Get capabilities (stub - returns empty for now)
   */
  ipcMain.handle('mcp:get-capabilities', async (event, serverId: string) => {
    return {
      tools: [],
      prompts: [],
      resources: []
    };
  });

  /**
   * List prompts (stub)
   */
  ipcMain.handle('mcp:list-prompts', async (event, serverId: string) => {
    return [];
  });

  /**
   * List resources (stub)
   */
  ipcMain.handle('mcp:list-resources', async (event, serverId: string) => {
    return [];
  });

  /**
   * Start FastMCP server (stub)
   */
  ipcMain.handle('mcp:start-fastmcp-server', async (event, serverPath: string) => {
    return { success: false, error: 'Not implemented yet' };
  });

  /**
   * Stop FastMCP server (stub)
   */
  ipcMain.handle('mcp:stop-fastmcp-server', async (event, serverPath: string) => {
    return { success: false, error: 'Not implemented yet' };
  });

  /**
   * Generate FastMCP server (stub)
   */
  ipcMain.handle('mcp:generate-fastmcp-server', async (event, wizardState: any, outputPath: string) => {
    return { success: false, error: 'Not implemented yet' };
  });
}
