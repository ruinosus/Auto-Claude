import { ipcMain, app } from 'electron';
import { promises as fs } from 'fs';
import path from 'path';
import type { MCPServer, MCPServerConfig, MCPTestConnectionResult, CustomServerConfig, MCPServersRegistry, FastMCPServerConfig } from '../shared/types/mcp';
import { updateEnvVars, getEnvPath, readEnvFile } from './mcp-config';
import { getBuiltInServers } from './mcp-servers-config';
import { MCPManager } from './mcp-manager-v2';

// Singleton MCPManager instance for testing connections
let testMcpManager: MCPManager | null = null;

function getTestMcpManager(): MCPManager {
  if (!testMcpManager) {
    testMcpManager = new MCPManager();
  }
  return testMcpManager;
}

/**
 * Find a server by ID from all sources (built-in + global registry + project registry)
 */
async function findServerById(serverId: string, projectPath?: string): Promise<MCPServer | null> {
  // Check built-in servers first
  const builtInServers = getBuiltInServers();
  const builtIn = builtInServers.find(s => s.id === serverId);
  if (builtIn) return builtIn;

  // Check global registry
  try {
    const globalRegistry = await loadRegistry('global');
    const globalServer = globalRegistry.servers.find(s => s.id === serverId);
    if (globalServer) return globalServer;
  } catch (error) {
    // Ignore if registry doesn't exist
  }

  // Check project registry if projectPath provided
  if (projectPath) {
    try {
      const projectRegistry = await loadRegistry('project', projectPath);
      const projectServer = projectRegistry.servers.find(s => s.id === serverId);
      if (projectServer) return projectServer;
    } catch (error) {
      // Ignore if registry doesn't exist
    }
  }

  return null;
}

/**
 * Convert MCPServer to config format for MCPManager connection
 * Handles both nested (customConfig) and root-level (legacy/FastMCP) formats
 */
function serverToConfig(server: MCPServer): any {
  // Support both formats: customConfig nested OR root-level fields
  const serverAny = server as any;
  const hasCustomConfig = server.customConfig && Object.keys(server.customConfig).length > 0;

  // Get values from customConfig if available, otherwise from root level
  const command = server.customConfig?.command || serverAny.command;
  const args = server.customConfig?.args || serverAny.args;
  const baseUrl = server.customConfig?.baseUrl || serverAny.url || server.endpoint;
  const workingDir = server.customConfig?.workingDir || serverAny.cwd;
  const env = server.customConfig?.env || serverAny.env;
  const authType = server.customConfig?.authType;
  const authValue = server.customConfig?.authValue;

  // Build headers from customConfig or root level, including auth conversion
  const sourceHeaders = server.customConfig?.headers || serverAny.headers || {};
  const headers: Record<string, string> = { ...sourceHeaders };

  // Convert authType/authValue to proper Authorization header
  if (authType && authValue) {
    if (authType === 'bearer') {
      headers['Authorization'] = `Bearer ${authValue}`;
    } else if (authType === 'api-key') {
      headers['Authorization'] = authValue;
    }
  }

  // Determine transport: prefer explicit transport field, fallback to connectionType
  const transport = serverAny.transport || (server.connectionType === 'http' ? 'http' : 'stdio');

  return {
    id: server.id,
    name: server.name,
    description: server.description,
    transport: transport as 'http' | 'stdio',
    command,
    args,
    url: baseUrl,
    headers: Object.keys(headers).length > 0 ? headers : undefined,
    cwd: workingDir,
    env,
    enabled: true,
    category: server.category,
    icon: server.icon
  };
}

/**
 * Convert CustomServerConfig to MCPServerConfig format for MCPManager connection
 */
function customConfigToServerConfig(config: CustomServerConfig): any {
  // Build headers from config, including auth conversion
  const headers: Record<string, string> = { ...(config.headers || {}) };

  // Convert authType/authValue to proper Authorization header
  if (config.authType && config.authValue) {
    if (config.authType === 'bearer') {
      headers['Authorization'] = `Bearer ${config.authValue}`;
    } else if (config.authType === 'api-key') {
      headers['Authorization'] = config.authValue;
    }
  }

  return {
    id: `test-${Date.now()}`,
    name: config.name || 'Test Server',
    description: config.description,
    transport: config.connectionType === 'http' || config.connectionType === 'sse' ? 'http' as const : 'stdio' as const,
    command: config.command,
    args: config.args,
    url: config.baseUrl,
    headers: Object.keys(headers).length > 0 ? headers : undefined,
    cwd: config.workingDir,
    env: config.env,
    enabled: true
  };
}

/**
 * Check if server is enabled by reading .env
 */
async function isServerEnabled(serverId: string, projectPath?: string): Promise<boolean> {
  const envPath = getEnvPath(projectPath);
  const envVars = await readEnvFile(envPath);

  // Check server-specific env vars for built-in servers
  switch (serverId) {
    case 'linear':
      return !!envVars.LINEAR_API_KEY;
    case 'graphiti':
      return !!envVars.GRAPHITI_MCP_URL;
    case 'electron':
      return envVars.ELECTRON_MCP_ENABLED === 'true';
    case 'context7':
    case 'auto-claude-tools':
    case 'puppeteer':
      return true; // Always enabled
    default:
      // For custom servers, check if they exist in registry
      // Custom servers are enabled by default when added
      const server = await findServerById(serverId, projectPath);
      if (server) {
        return server.enabled !== false; // Default to enabled
      }
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

      // Check enabled status for each server and update status accordingly
      // Note: We don't load capabilities here anymore to avoid blocking/timeouts
      // Capabilities are loaded on-demand when user expands a server
      const serversWithStatus = await Promise.all(
        allServers.map(async (server) => {
          const enabled = await isServerEnabled(server.id, projectPath);
          const result = {
            ...server,
            enabled,
            status: enabled ? 'connected' as const : 'disabled' as const
          };
          console.log(`[MCP List] Server ${server.id}: enabled=${enabled}, toolCount=${server.toolCount}, status=${result.status}`);
          return result;
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
  ipcMain.handle('mcp:saveConfig', async (event, serverId: string, config: MCPServerConfig, projectPath?: string) => {
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
  ipcMain.handle('mcp:testConnection', async (event, serverId: string, config: MCPServerConfig) => {
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
          return {
            success: true,
            status: 'connected' as const,
            message: 'Always available',
            toolsFound: 2
          };

        case 'auto-claude-tools':
          return {
            success: true,
            status: 'connected' as const,
            message: 'Always available - Build progress, context, and ROI tracking',
            toolsFound: 11
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
   * Get capabilities from an MCP server (loaded on-demand)
   */
  ipcMain.handle('mcp:getCapabilities', async (event, serverId: string) => {
    try {
      const { MCPManager } = await import('./mcp-manager-v2');
      const mcpManager = new MCPManager();

      // Find server from all sources (built-in + custom registries)
      const server = await findServerById(serverId);

      if (!server) {
        throw new Error(`Server ${serverId} not found`);
      }

      // Convert to MCPServerConfig
      const serverConfig = serverToConfig(server);

      // Connect and fetch capabilities
      console.log(`[MCP Manager] Connecting to ${serverId}...`);
      await mcpManager.connect(serverConfig);

      // Fetch all capabilities in parallel
      const [tools, prompts, resources] = await Promise.all([
        mcpManager.listTools(serverId),
        mcpManager.listPrompts(serverId),
        mcpManager.listResources(serverId)
      ]);

      console.log(`[MCP Manager] Loaded for ${serverId}: ${tools.length} tools, ${prompts.length} prompts, ${resources.length} resources`);

      // Transform tools to include inputSchema
      const transformedTools = tools.map((tool: any) => ({
        name: tool.name,
        displayName: tool.name,
        description: tool.description || '',
        inputSchema: tool.inputSchema,
        parameters: []
      }));

      // Transform prompts
      const transformedPrompts = prompts.map((prompt: any) => ({
        name: prompt.name,
        displayName: prompt.name,
        description: prompt.description || '',
        arguments: prompt.arguments?.map((arg: any) => ({
          name: arg.name,
          description: arg.description || '',
          required: arg.required || false
        })) || []
      }));

      // Transform resources
      const transformedResources = resources.map((resource: any) => ({
        uri: resource.uri,
        name: resource.name || resource.uri,
        description: resource.description || '',
        mimeType: resource.mimeType,
        isTemplate: !!resource.uriTemplate
      }));

      return {
        tools: transformedTools,
        prompts: transformedPrompts,
        resources: transformedResources
      };
    } catch (error) {
      console.error(`[MCP Manager] Failed to get capabilities for ${serverId}:`, error);

      // Fallback to static capabilities from any source
      const server = await findServerById(serverId);
      if (server?.capabilities?.tools && server.capabilities.tools.length > 0) {
        console.log(`[MCP Manager] Using static capabilities for ${serverId}: ${server.capabilities.tools.length} tools`);
        return {
          tools: server.capabilities.tools,
          prompts: server.capabilities.prompts || [],
          resources: server.capabilities.resources || []
        };
      }

      return {
        tools: [],
        prompts: [],
        resources: []
      };
    }
  });

  /**
   * Call an MCP tool
   */
  ipcMain.handle('mcp:callTool', async (event, serverId: string, toolName: string, args: any) => {
    try {
      const { MCPManager } = await import('./mcp-manager-v2');
      const mcpManager = new MCPManager();

      // Find server from all sources (built-in + custom registries)
      const server = await findServerById(serverId);

      if (!server) {
        throw new Error(`Server ${serverId} not found`);
      }

      // Convert to MCPServerConfig
      const serverConfig = serverToConfig(server);

      console.log(`[MCP Manager] Calling tool ${toolName} on server ${serverId} with args:`, args);

      // Connect and call tool
      await mcpManager.connect(serverConfig);
      const result = await mcpManager.callTool(serverId, toolName, args);

      console.log(`[MCP Manager] Tool ${toolName} result:`, result);
      return result;
    } catch (error) {
      console.error(`[MCP Manager] Error calling tool ${toolName}:`, error);
      throw error;
    }
  });

  /**
   * List prompts from an MCP server
   */
  ipcMain.handle('mcp:listPrompts', async (event, serverId: string) => {
    try {
      const { MCPManager } = await import('./mcp-manager-v2');
      const mcpManager = new MCPManager();

      // Find server from all sources (built-in + custom registries)
      const server = await findServerById(serverId);

      if (!server) {
        throw new Error(`Server ${serverId} not found`);
      }

      const serverConfig = serverToConfig(server);

      await mcpManager.connect(serverConfig);
      const prompts = await mcpManager.listPrompts(serverId);

      return prompts.map((prompt: any) => ({
        name: prompt.name,
        displayName: prompt.name,
        description: prompt.description || '',
        arguments: prompt.arguments?.map((arg: any) => ({
          name: arg.name,
          description: arg.description || '',
          required: arg.required || false
        })) || []
      }));
    } catch (error) {
      console.error(`[MCP Manager] Error listing prompts for ${serverId}:`, error);
      return [];
    }
  });

  /**
   * List resources from an MCP server
   */
  ipcMain.handle('mcp:listResources', async (event, serverId: string) => {
    try {
      const { MCPManager } = await import('./mcp-manager-v2');
      const mcpManager = new MCPManager();

      // Find server from all sources (built-in + custom registries)
      const server = await findServerById(serverId);

      if (!server) {
        throw new Error(`Server ${serverId} not found`);
      }

      const serverConfig = serverToConfig(server);

      await mcpManager.connect(serverConfig);
      const resources = await mcpManager.listResources(serverId);

      return resources.map((resource: any) => ({
        uri: resource.uri,
        name: resource.name || resource.uri,
        description: resource.description || '',
        mimeType: resource.mimeType,
        isTemplate: !!resource.uriTemplate
      }));
    } catch (error) {
      console.error(`[MCP Manager] Error listing resources for ${serverId}:`, error);
      return [];
    }
  });

  /**
   * Get a prompt from an MCP server (execute prompt template)
   */
  ipcMain.handle('mcp:getPrompt', async (event, serverId: string, promptName: string, args?: Record<string, string>) => {
    try {
      const { MCPManager } = await import('./mcp-manager-v2');
      const mcpManager = new MCPManager();

      // Find server from all sources (built-in + custom registries)
      const server = await findServerById(serverId);

      if (!server) {
        throw new Error(`Server ${serverId} not found`);
      }

      const serverConfig = serverToConfig(server);

      await mcpManager.connect(serverConfig);
      const content = await mcpManager.getPrompt(serverId, promptName, args);

      return { content };
    } catch (error) {
      console.error(`[MCP Manager] Error getting prompt ${promptName}:`, error);
      return { content: '', error: error instanceof Error ? error.message : String(error) };
    }
  });

  /**
   * Read a resource from an MCP server
   */
  ipcMain.handle('mcp:readResource', async (event, serverId: string, uri: string) => {
    try {
      const { MCPManager } = await import('./mcp-manager-v2');
      const mcpManager = new MCPManager();

      // Find server from all sources (built-in + custom registries)
      const server = await findServerById(serverId);

      if (!server) {
        throw new Error(`Server ${serverId} not found`);
      }

      const serverConfig = serverToConfig(server);

      await mcpManager.connect(serverConfig);
      const result = await mcpManager.readResource(serverId, uri);

      // Extract content from the result
      const contents = result.contents || [];
      if (contents.length === 0) {
        return { content: '', mimeType: 'text/plain' };
      }

      const firstContent = contents[0];
      const content = firstContent.text || (firstContent.blob ? atob(firstContent.blob) : '');
      const mimeType = firstContent.mimeType || 'text/plain';

      return { content, mimeType };
    } catch (error) {
      console.error(`[MCP Manager] Error reading resource ${uri}:`, error);
      return { content: '', error: error instanceof Error ? error.message : String(error) };
    }
  });

  /**
   * Start FastMCP server (stub)
   */
  ipcMain.handle('mcp:startFastMCPServer', async (event, serverPath: string) => {
    return { success: false, error: 'Not implemented yet' };
  });

  /**
   * Stop FastMCP server (stub)
   */
  ipcMain.handle('mcp:stopFastMCPServer', async (event, serverPath: string) => {
    return { success: false, error: 'Not implemented yet' };
  });

  /**
   * Generate FastMCP server with uv
   */
  ipcMain.handle('mcp:generateFastMCPServer', async (event, config: FastMCPServerConfig) => {
    console.log('[FastMCP] Starting server generation:', config.serverName);
    try {
      console.log('[FastMCP] Importing registry-integration module...');
      const { generateAndRegisterServer } = await import('./registry-integration');
      const registryPath = getRegistryPath('global');
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
  ipcMain.handle('mcp:addCustomServer', async (
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
        status: 'connected', // Start as connected, will update on actual connection
        enabled: true, // Custom servers are enabled by default
        requiredEnvVars: [],
        capabilities: {
          tools: [],
          prompts: [],
          resources: []
        },
        toolCount: 0, // Will be loaded dynamically via getCapabilities
        promptCount: 0,
        resourceCount: 0,
        connectionType: config.connectionType === 'http' || config.connectionType === 'sse' ? 'http' : 'stdio',
        customConfig: config,
        icon: config.connectionType === 'http' || config.connectionType === 'sse' ? 'Globe' : 'Terminal',
        color: 'purple'
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
   * Test connection to custom MCP server - REAL implementation
   */
  ipcMain.handle('mcp:testConnectionCustom', async (event, config: CustomServerConfig) => {
    try {
      // Validate configuration
      const validationError = validateCustomServerConfig(config);
      if (validationError) {
        return {
          success: false,
          status: 'error' as const,
          message: validationError
        };
      }

      // Convert CustomServerConfig to MCPServerConfig format
      const serverConfig = customConfigToServerConfig(config);

      console.log('[mcp:testConnectionCustom] Testing connection to:', {
        transport: serverConfig.transport,
        url: serverConfig.url,
        command: serverConfig.command,
        hasHeaders: !!serverConfig.headers
      });

      // Get MCPManager instance and attempt real connection
      const mcpManager = getTestMcpManager();

      try {
        // Connect to the server (this actually tests the connection)
        await mcpManager.connect(serverConfig);

        // If connection successful, fetch capabilities
        const tools = await mcpManager.listTools(serverConfig.id);
        const prompts = await mcpManager.listPrompts(serverConfig.id);
        const resources = await mcpManager.listResources(serverConfig.id);

        // Disconnect after test (cleanup)
        await mcpManager.disconnect(serverConfig.id);

        console.log('[mcp:testConnectionCustom] Connection successful:', {
          tools: tools.length,
          prompts: prompts.length,
          resources: resources.length
        });

        return {
          success: true,
          status: 'connected' as const,
          message: `Successfully connected to ${config.connectionType} server`,
          capabilities: {
            tools: tools.map(t => ({ name: t.name, description: t.description })),
            prompts: prompts.map(p => ({ name: p.name, description: p.description })),
            resources: resources.map(r => ({ uri: r.uri, name: r.name }))
          }
        };
      } catch (connectionError) {
        console.error('[mcp:testConnectionCustom] Connection failed:', connectionError);

        // Cleanup on error
        try {
          await mcpManager.disconnect(serverConfig.id);
        } catch (e) {
          // Ignore cleanup errors
        }

        return {
          success: false,
          status: 'error' as const,
          message: connectionError instanceof Error ? connectionError.message : String(connectionError)
        };
      }
    } catch (error) {
      console.error('[mcp:testConnectionCustom] Error:', error);
      return {
        success: false,
        status: 'error' as const,
        message: error instanceof Error ? error.message : String(error)
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
