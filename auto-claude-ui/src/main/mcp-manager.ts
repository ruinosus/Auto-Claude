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
 * Test Linear connection
 */
async function testLinearConnection(apiKey: string): Promise<MCPTestConnectionResult> {
  try {
    const response = await fetch('https://api.linear.app/graphql', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': apiKey
      },
      body: JSON.stringify({
        query: '{ viewer { id name } }'
      })
    });

    if (response.ok) {
      const data = await response.json();
      if (data.errors) {
        return {
          success: false,
          status: 'error',
          message: 'Invalid API key or insufficient permissions'
        };
      }
      return {
        success: true,
        status: 'connected',
        message: `Connected as ${data.data.viewer.name}`,
        toolsFound: 12
      };
    } else {
      return {
        success: false,
        status: 'error',
        message: `HTTP ${response.status}: ${response.statusText}`
      };
    }
  } catch (error) {
    return {
      success: false,
      status: 'error',
      message: error instanceof Error ? error.message : String(error)
    };
  }
}

/**
 * Test Graphiti connection
 */
async function testGraphitiConnection(url: string): Promise<MCPTestConnectionResult> {
  try {
    const healthUrl = url.endsWith('/') ? `${url}health` : `${url}/health`;
    const response = await fetch(healthUrl, { method: 'GET' });

    if (response.ok) {
      return {
        success: true,
        status: 'connected',
        message: 'Graphiti server is healthy',
        toolsFound: 5,
        promptsFound: 3,
        resourcesFound: 8
      };
    } else {
      return {
        success: false,
        status: 'error',
        message: 'Server not responding correctly'
      };
    }
  } catch (error) {
    return {
      success: false,
      status: 'error',
      message: 'Cannot connect to Graphiti server. Is it running?'
    };
  }
}

/**
 * Test Electron connection
 */
async function testElectronConnection(port: number): Promise<MCPTestConnectionResult> {
  try {
    const response = await fetch(`http://localhost:${port}/json/version`, {
      method: 'GET'
    });

    if (response.ok) {
      const data = await response.json();
      return {
        success: true,
        status: 'connected',
        message: `Connected to ${data['Browser'] || 'Electron'}`,
        toolsFound: 4
      };
    } else {
      return {
        success: false,
        status: 'error',
        message: 'Electron remote debugging not responding'
      };
    }
  } catch (error) {
    return {
      success: false,
      status: 'error',
      message: `Cannot connect to port ${port}. Start Electron with --remote-debugging-port=${port}`
    };
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
   * Test connection - now with real implementations
   */
  ipcMain.handle('mcp:test-connection', async (event, serverId: string, config: MCPServerConfig) => {
    try {
      switch (serverId) {
        case 'linear':
          return await testLinearConnection(config.envVars.LINEAR_API_KEY);

        case 'graphiti':
          return await testGraphitiConnection(config.envVars.GRAPHITI_MCP_URL);

        case 'electron':
          const port = parseInt(config.envVars.ELECTRON_DEBUG_PORT || '9222');
          return await testElectronConnection(port);

        case 'context7':
        case 'auto-claude-tools':
          return {
            success: true,
            status: 'connected' as const,
            message: 'Always available',
            toolsFound: serverId === 'context7' ? 2 : 6
          };

        case 'puppeteer':
          return {
            success: true,
            status: 'connected' as const,
            message: 'Auto-enabled for web projects',
            toolsFound: 8
          };

        default:
          return {
            success: false,
            status: 'error' as const,
            message: 'Unknown server type'
          };
      }
    } catch (error) {
      return {
        success: false,
        status: 'error' as const,
        message: error instanceof Error ? error.message : String(error)
      };
    }
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
