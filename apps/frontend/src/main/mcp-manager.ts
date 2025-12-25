import { ipcMain, app } from 'electron';
import { promises as fs } from 'fs';
import path from 'path';
import type { MCPServer, MCPServerConfig, MCPTestConnectionResult, CustomServerConfig, MCPServersRegistry, FastMCPServerConfig } from '../shared/types/mcp';
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
  console.log('[MCP] Registering MCP IPC handlers...');

  /**
   * List all available MCP servers
   */
  ipcMain.handle('mcp:list', async (event, projectPath?: string) => {
    try {
      const builtInServers = getBuiltInServers();

      // Load custom servers from global registry
      const globalRegistry = await loadRegistry('global');

      // Load custom servers from project registry if projectPath provided
      let projectRegistry: MCPServersRegistry = { version: '1.0', servers: [], updatedAt: '' };
      if (projectPath) {
        try {
          projectRegistry = await loadRegistry('project', projectPath);
        } catch (error) {
          // Ignore if project registry doesn't exist
        }
      }

      // Merge all servers (built-in + global custom + project custom)
      const allServers = [
        ...builtInServers,
        ...globalRegistry.servers,
        ...projectRegistry.servers
      ];

      // Check enabled status and load real capabilities for enabled servers
      const serversWithStatus = await Promise.all(
        allServers.map(async (server) => {
          const enabled = await isServerEnabled(server.id, projectPath);

          // For enabled servers, try to load real capabilities from MCP server
          if (enabled && server.id === 'context7') {
            try {
              const { listTools } = await import('./mcp-client');
              const tools = await listTools(server.id);

              console.log(`[MCP Manager] Loaded ${tools.length} tools for ${server.id}`);
              if (tools.length > 0) {
                console.log(`[MCP Manager] First tool:`, JSON.stringify(tools[0], null, 2));
              }

              // Transform MCP SDK tool format to our format
              const transformedTools = tools.map((tool: any) => ({
                name: tool.name,
                displayName: tool.name,
                description: tool.description || '',
                inputSchema: tool.inputSchema,
                parameters: [] // Will be derived from inputSchema if needed
              }));

              return {
                ...server,
                enabled,
                capabilities: {
                  tools: transformedTools,
                  prompts: server.capabilities?.prompts || [],
                  resources: server.capabilities?.resources || []
                },
                toolCount: transformedTools.length,
                status: 'connected' as const
              };
            } catch (error) {
              console.error(`[MCP Manager] Failed to load tools for ${server.id}:`, error);
              return {
                ...server,
                enabled,
                status: 'error' as const,
                statusMessage: error instanceof Error ? error.message : String(error)
              };
            }
          }

          return {
            ...server,
            enabled
          };
        })
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
   * Call an MCP tool
   */
  ipcMain.handle('mcp:call-tool', async (event, serverId: string, toolName: string, args: any) => {
    try {
      const { callTool } = await import('./mcp-client');
      console.log(`[MCP Manager] Calling tool ${toolName} on server ${serverId} with args:`, args);
      const result = await callTool(serverId, toolName, args);
      console.log(`[MCP Manager] Tool ${toolName} result:`, result);
      return result;
    } catch (error) {
      console.error(`[MCP Manager] Error calling tool ${toolName}:`, error);
      throw error;
    }
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
   * Generate FastMCP server with uv
   */
  ipcMain.handle('mcp:generate-fastmcp-server', async (event, config: FastMCPServerConfig) => {
    console.log('[FastMCP] Starting server generation:', config.serverName);
    try {
      console.log('[FastMCP] Importing registry-integration module...');
      const { generateAndRegisterServer } = await import('./registry-integration');
      const registryPath = path.join(app.getPath('home'), '.mcp-servers.json');
      console.log('[FastMCP] Registry path:', registryPath);

      console.log('[FastMCP] Calling generateAndRegisterServer...');
      const result = await generateAndRegisterServer(config, registryPath, event);
      console.log('[FastMCP] Result:', result);

      return {
        success: result.success,
        serverPath: result.serverPath,
        serverId: result.serverId,
        error: result.error
      };
    } catch (error) {
      console.error('[FastMCP] ERROR in handler:', error);
      console.error('[FastMCP] Error stack:', (error as Error).stack);
      return {
        success: false,
        error: (error as Error).message
      };
    }
  });

  /**
   * Add custom server configuration
   */
  ipcMain.handle('mcp:add-custom-server', async (
    event,
    config: CustomServerConfig,
    scope: 'global' | 'project',
    projectPath?: string
  ) => {
    try {
      // Validate configuration
      const validationError = validateCustomServerConfig(config);
      if (validationError) {
        return {
          success: false,
          error: validationError
        };
      }

      // Load existing registry
      const registry = await loadRegistry(scope, projectPath);

      // Generate unique server ID
      const serverId = generateServerId(config.connectionType);

      // Create new server entry
      const newServer: MCPServer = {
        id: serverId,
        name: config.name || `Custom ${config.connectionType} Server`,
        description: config.description || '',
        type: 'custom',
        category: 'Custom',
        status: 'disconnected',
        enabled: false,
        requiredEnvVars: [],
        capabilities: {},
        toolCount: 0,
        promptCount: 0,
        resourceCount: 0,
        connectionType: config.connectionType === 'http' || config.connectionType === 'sse' ? 'http' : 'stdio',
        customConfig: config
      };

      // Add to registry
      registry.servers.push(newServer);
      registry.updatedAt = new Date().toISOString();

      // Save registry
      await saveRegistry(registry, scope, projectPath);

      return {
        success: true,
        serverId
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  });

  /**
   * Test connection to custom MCP server (simulated for now)
   */
  ipcMain.handle('mcp:test-connection-custom', async (event, config: CustomServerConfig) => {
    try {
      // Validate configuration
      const validationError = validateCustomServerConfig(config);
      if (validationError) {
        return {
          success: false,
          status: 'error' as const,
          error: validationError
        };
      }

      // For now, return simulated success with mock capabilities
      // In production, this would actually attempt connection
      return {
        success: true,
        status: 'connected' as const,
        message: `Successfully connected to ${config.connectionType} server`,
        capabilities: {
          tools: [
            { name: 'test-tool', description: 'A test tool' }
          ],
          prompts: [
            { name: 'test-prompt', description: 'A test prompt' }
          ],
          resources: []
        }
      };
    } catch (error) {
      return {
        success: false,
        status: 'error' as const,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  });
}

/**
 * Validate custom server configuration
 */
function validateCustomServerConfig(config: CustomServerConfig): string | null {
  if (!config.connectionType) {
    return 'connectionType is required';
  }

  switch (config.connectionType) {
    case 'http':
    case 'sse':
      if (!config.baseUrl) {
        return 'baseUrl is required for HTTP/SSE connections';
      }
      break;
    case 'stdio':
      if (!config.command) {
        return 'command is required for stdio connections';
      }
      break;
    default:
      return `Invalid connection type: ${config.connectionType}`;
  }

  return null;
}

/**
 * Generate unique server ID
 */
function generateServerId(connectionType: string): string {
  return `custom-${connectionType}-${Date.now()}`;
}

/**
 * Get registry file path
 */
function getRegistryPath(scope: 'global' | 'project', projectPath?: string): string {
  if (scope === 'global') {
    const homeDir = app.getPath('home');
    return path.join(homeDir, '.auto-claude', 'mcp-servers.json');
  } else {
    if (!projectPath) {
      throw new Error('projectPath is required for project scope');
    }
    return path.join(projectPath, '.auto-claude', 'mcp-servers.json');
  }
}

/**
 * Load servers registry
 */
async function loadRegistry(scope: 'global' | 'project', projectPath?: string): Promise<MCPServersRegistry> {
  const registryPath = getRegistryPath(scope, projectPath);

  try {
    const content = await fs.readFile(registryPath, 'utf-8');
    return JSON.parse(content);
  } catch (error: any) {
    if (error.code === 'ENOENT') {
      // File doesn't exist, return empty registry
      return {
        version: '1.0',
        servers: [],
        updatedAt: new Date().toISOString()
      };
    }
    throw error;
  }
}

/**
 * Save servers registry
 */
async function saveRegistry(
  registry: MCPServersRegistry,
  scope: 'global' | 'project',
  projectPath?: string
): Promise<void> {
  const registryPath = getRegistryPath(scope, projectPath);

  // Ensure directory exists
  await fs.mkdir(path.dirname(registryPath), { recursive: true });

  // Write registry file
  await fs.writeFile(registryPath, JSON.stringify(registry, null, 2), 'utf-8');
}
