/**
 * MCPManager - Complete MCP Client Manager
 *
 * Handles all MCP server connections with automatic detection of:
 * - Transport type (stdio, http, sse)
 * - Runtime (python, uv, uvx, node, npx, custom)
 * - Server lifecycle management
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { app } from 'electron';
import { existsSync } from 'fs';
import { readFile } from 'fs/promises';
import path from 'path';

/**
 * Complete server configuration with all transport types
 */
export interface MCPServerConfig {
  id: string;
  name: string;
  description?: string;

  // Transport configuration
  transport: 'stdio' | 'http' | 'sse';

  // STDIO configuration
  command?: string;        // python | uv | uvx | node | npx | custom
  args?: string[];
  cwd?: string;
  env?: Record<string, string>;

  // HTTP/SSE configuration
  url?: string;
  headers?: Record<string, string>;

  // Metadata
  enabled?: boolean;
  requiredEnvVars?: string[];
  category?: string;
  icon?: string;
}

/**
 * Active MCP connection
 */
interface MCPConnection {
  config: MCPServerConfig;
  client: Client;
  connected: boolean;
  error?: string;
}

/**
 * Registry file structure
 */
interface MCPRegistry {
  version: string;
  servers: MCPServerConfig[];
  updatedAt: string;
}

/**
 * MCPManager - Manages all MCP server connections
 */
export class MCPManager {
  private connections = new Map<string, MCPConnection>();
  private pendingConnections = new Map<string, Promise<void>>(); // PREVENTS RACE CONDITIONS
  private registryPath: string;

  constructor(registryPath?: string) {
    this.registryPath = registryPath || path.join(
      app.getPath('home'),
      '.auto-claude',
      'mcp-servers.json'
    );
  }

  /**
   * Load server configurations from registry
   */
  async loadRegistry(scope: 'global' | 'project' = 'global', projectPath?: string): Promise<MCPServerConfig[]> {
    try {
      let registryFile = this.registryPath;

      if (scope === 'project' && projectPath) {
        registryFile = path.join(projectPath, '.auto-claude', 'mcp-servers.json');
      }

      if (!existsSync(registryFile)) {
        console.log(`[MCPManager] Registry not found: ${registryFile}`);
        return this.getBuiltInServers();
      }

      const content = await readFile(registryFile, 'utf-8');
      const registry: MCPRegistry = JSON.parse(content);

      console.log(`[MCPManager] Loaded ${registry.servers.length} servers from ${scope} registry`, new Error().stack);

      // Merge with built-in servers
      const builtIn = this.getBuiltInServers();
      const custom = registry.servers;

      // Built-in servers take precedence (can be overridden by custom config)
      const merged = [...builtIn];
      for (const customServer of custom) {
        const existingIndex = merged.findIndex(s => s.id === customServer.id);
        if (existingIndex >= 0) {
          // Override built-in with custom config
          merged[existingIndex] = { ...merged[existingIndex], ...customServer };
        } else {
          // Add new custom server
          merged.push(customServer);
        }
      }

      return merged;
    } catch (error) {
      console.error('[MCPManager] Failed to load registry:', error);
      return this.getBuiltInServers();
    }
  }

  /**
   * Get built-in server configurations
   */
  private getBuiltInServers(): MCPServerConfig[] {
    return [
      {
        id: 'context7',
        name: 'Context7',
        description: 'Real-time documentation lookup for any library',
        transport: 'stdio',
        command: 'npx',
        args: ['-y', '@upstash/context7-mcp'],
        enabled: true,
        category: 'Documentation',
        icon: 'Book'
      },
      {
        id: 'puppeteer',
        name: 'Puppeteer Browser',
        description: 'Web browser automation and testing',
        transport: 'stdio',
        command: 'npx',
        args: ['-y', '@modelcontextprotocol/server-puppeteer'],
        enabled: true,
        category: 'Browser Automation',
        icon: 'Globe'
      },
      {
        id: 'linear',
        name: 'Linear',
        description: 'Project management and issue tracking',
        transport: 'http',
        url: 'https://mcp.linear.app/mcp',
        headers: {
          'Authorization': 'Bearer ${LINEAR_API_KEY}'
        },
        enabled: true,
        requiredEnvVars: ['LINEAR_API_KEY'],
        category: 'Project Management',
        icon: 'Zap'
      },
      {
        id: 'graphiti',
        name: 'Graphiti Memory',
        description: 'Knowledge graph memory with semantic search',
        transport: 'http',
        url: '${GRAPHITI_MCP_URL}',
        enabled: false,
        requiredEnvVars: ['GRAPHITI_MCP_URL'],
        category: 'Memory',
        icon: 'Brain'
      }
    ];
  }

  /**
   * Connect to an MCP server
   */
  async connect(config: MCPServerConfig): Promise<void> {
    const serverId = config.id;

    // Check if already connected
    if (this.connections.has(serverId)) {
      console.log(`[MCPManager] Already connected to ${serverId}`);
      return;
    }

    // Check if connection is already in progress (PREVENTS RACE CONDITION)
    const pending = this.pendingConnections.get(serverId);
    if (pending) {
      console.log(`[MCPManager] Connection to ${serverId} already in progress, waiting...`);
      return pending; // Wait for existing connection attempt
    }

    // Create new connection promise
    const connectionPromise = (async () => {
      try {
        console.log(`[MCPManager] Connecting to ${serverId}...`);
        console.log(`[MCPManager] Transport: ${config.transport}`);

        // Create client
        const client = new Client(
          {
            name: 'auto-claude-ui',
            version: '1.0.0'
          },
          {
            capabilities: {}
          }
        );

        // Create appropriate transport
        const transport = await this.createTransport(config);

        // Connect with timeout (30 seconds)
        const connectPromise = client.connect(transport);
        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Connection timeout after 30s')), 30000)
        );

        await Promise.race([connectPromise, timeoutPromise]);

        // Store connection
        this.connections.set(serverId, {
          config,
          client,
          connected: true
        });

        console.log(`[MCPManager] ✅ Connected to ${serverId}`);
      } catch (error) {
        console.error(`[MCPManager] ❌ Failed to connect to ${serverId}:`, error);

        this.connections.set(serverId, {
          config,
          client: null as any,
          connected: false,
          error: error instanceof Error ? error.message : String(error)
        });

        throw error;
      } finally {
        // Remove from pending connections
        this.pendingConnections.delete(serverId);
      }
    })();

    // Store pending connection
    this.pendingConnections.set(serverId, connectionPromise);

    // Wait for connection to complete
    return connectionPromise;
  }

  /**
   * Create transport based on configuration
   */
  private async createTransport(config: MCPServerConfig): Promise<any> {
    switch (config.transport) {
      case 'stdio':
        return this.createStdioTransport(config);

      case 'http':
      case 'sse':
        return this.createHttpTransport(config);

      default:
        throw new Error(`Unknown transport type: ${config.transport}`);
    }
  }

  /**
   * Create STDIO transport (supports python, uv, uvx, node, npx, etc.)
   */
  private createStdioTransport(config: MCPServerConfig): StdioClientTransport {
    if (!config.command) {
      throw new Error('STDIO transport requires command');
    }

    // Resolve environment variables in args and env
    const resolvedArgs = this.resolveEnvVars(config.args || []);
    const resolvedEnv = this.resolveEnvVars(config.env || {});

    console.log(`[MCPManager] STDIO config:`, {
      command: config.command,
      args: resolvedArgs,
      cwd: config.cwd,
      hasEnv: Object.keys(resolvedEnv).length > 0
    });

    return new StdioClientTransport({
      command: config.command,
      args: resolvedArgs,
      cwd: config.cwd,
      env: {
        ...process.env,
        ...resolvedEnv
      }
    });
  }

  /**
   * Create HTTP transport (for remote servers)
   * Uses StreamableHTTPClientTransport from @modelcontextprotocol/sdk
   */
  private createHttpTransport(config: MCPServerConfig): StreamableHTTPClientTransport {
    if (!config.url) {
      throw new Error('HTTP transport requires url');
    }

    // Resolve environment variables in URL and headers
    const resolvedUrl = this.resolveEnvVar(config.url);
    const resolvedHeaders = this.resolveEnvVars(config.headers || {});

    // Debug: Check if LINEAR_API_KEY exists in env
    console.log(`[MCPManager-v2] LINEAR_API_KEY in process.env?`, !!process.env.LINEAR_API_KEY);
    console.log(`[MCPManager-v2] LINEAR_API_KEY value (masked):`, process.env.LINEAR_API_KEY ? `${process.env.LINEAR_API_KEY.substring(0, 7)}...` : 'UNDEFINED');

    // Debug: Log resolved headers (mask sensitive values)
    const maskedHeaders: Record<string, string> = {};
    for (const [key, value] of Object.entries(resolvedHeaders)) {
      if (key.toLowerCase() === 'authorization') {
        maskedHeaders[key] = value ? `Bearer ${value.replace('Bearer ', '').substring(0, 7)}...` : 'EMPTY';
      } else {
        maskedHeaders[key] = value;
      }
    }

    console.log(`[MCPManager-v2] Creating HTTP transport:`, {
      url: resolvedUrl,
      hasHeaders: Object.keys(resolvedHeaders).length > 0,
      headers: maskedHeaders
    });

    // Create URL object for SDK
    const urlObj = new URL(resolvedUrl);

    // Configure request options
    const requestInit: RequestInit = {};
    if (Object.keys(resolvedHeaders).length > 0) {
      requestInit.headers = resolvedHeaders;
    }

    // Create and return StreamableHTTPClientTransport
    return new StreamableHTTPClientTransport(urlObj, {
      requestInit,
      fetch: fetch // Use native fetch
    });
  }

  /**
   * Resolve environment variable placeholders like ${VAR_NAME}
   */
  private resolveEnvVar(value: string): string {
    return value.replace(/\$\{([^}]+)\}/g, (_, varName) => {
      return process.env[varName] || '';
    });
  }

  /**
   * Resolve environment variables in an array or object
   */
  private resolveEnvVars<T extends string[] | Record<string, string>>(input: T): T {
    if (Array.isArray(input)) {
      return input.map(item => this.resolveEnvVar(item)) as T;
    } else {
      const result: Record<string, string> = {};
      for (const [key, value] of Object.entries(input)) {
        result[key] = this.resolveEnvVar(value);
      }
      return result as T;
    }
  }

  /**
   * Disconnect from a server
   */
  async disconnect(serverId: string): Promise<void> {
    const connection = this.connections.get(serverId);
    if (!connection) {
      console.warn(`[MCPManager] Not connected to ${serverId}`);
      return;
    }

    try {
      if (connection.connected && connection.client) {
        await connection.client.close();
      }
      this.connections.delete(serverId);
      this.pendingConnections.delete(serverId); // Clean up pending connections too
      console.log(`[MCPManager] Disconnected from ${serverId}`);
    } catch (error) {
      console.error(`[MCPManager] Error disconnecting from ${serverId}:`, error);
      throw error;
    }
  }

  /**
   * Disconnect all servers
   */
  async disconnectAll(): Promise<void> {
    console.log(`[MCPManager] Disconnecting all servers...`);
    const serverIds = Array.from(this.connections.keys());

    await Promise.all(
      serverIds.map(id => this.disconnect(id).catch(err => {
        console.error(`[MCPManager] Error disconnecting ${id}:`, err);
      }))
    );

    console.log(`[MCPManager] All servers disconnected`);
  }

  /**
   * Get connected client for a server
   */
  getClient(serverId: string): Client | null {
    const connection = this.connections.get(serverId);
    return connection?.connected ? connection.client : null;
  }

  /**
   * Check if connected to a server
   */
  isConnected(serverId: string): boolean {
    return this.connections.get(serverId)?.connected || false;
  }

  /**
   * List all server IDs
   */
  listServers(): string[] {
    return Array.from(this.connections.keys());
  }

  /**
   * Get connection status for all servers
   */
  getConnectionStatus(): Record<string, { connected: boolean; error?: string }> {
    const status: Record<string, { connected: boolean; error?: string }> = {};

    for (const [id, connection] of this.connections) {
      status[id] = {
        connected: connection.connected,
        error: connection.error
      };
    }

    return status;
  }

  /**
   * Call a tool on a server
   */
  async callTool(serverId: string, toolName: string, args: any): Promise<any> {
    const client = this.getClient(serverId);
    if (!client) {
      // Try to connect first
      const configs = await this.loadRegistry();
      const config = configs.find(c => c.id === serverId);
      if (!config) {
        throw new Error(`Server ${serverId} not found in registry`);
      }
      await this.connect(config);
      return this.callTool(serverId, toolName, args);
    }

    console.log(`[MCPManager] Calling tool ${toolName} on ${serverId}`);

    const result = await client.callTool({
      name: toolName,
      arguments: args
    });

    return result;
  }

  /**
   * List tools from a server
   */
  async listTools(serverId: string): Promise<any[]> {
    const client = this.getClient(serverId);
    if (!client) {
      // Try to connect first
      const configs = await this.loadRegistry();
      const config = configs.find(c => c.id === serverId);
      if (!config) {
        throw new Error(`Server ${serverId} not found in registry`);
      }
      await this.connect(config);
      return this.listTools(serverId);
    }

    const result = await client.listTools();
    const tools = result.tools || [];

    // DEBUG: Log what SDK returned
    console.log(`[MCPManager-v2] listTools(${serverId}) - SDK returned ${tools.length} tools:`);
    if (tools.length > 0) {
      console.log(`[MCPManager-v2] First tool:`, JSON.stringify(tools[0], null, 2));
      console.log(`[MCPManager-v2] Has inputSchema?`, !!tools[0]?.inputSchema);
    }

    return tools;
  }

  /**
   * List prompts from a server
   */
  async listPrompts(serverId: string): Promise<any[]> {
    const client = this.getClient(serverId);
    if (!client) {
      const configs = await this.loadRegistry();
      const config = configs.find(c => c.id === serverId);
      if (!config) {
        throw new Error(`Server ${serverId} not found in registry`);
      }
      await this.connect(config);
      return this.listPrompts(serverId);
    }

    try {
      const result = await client.listPrompts();
      return result.prompts || [];
    } catch (error: any) {
      // Some servers don't support prompts
      if (error.message?.includes('not found') || error.code === -32601) {
        return [];
      }
      throw error;
    }
  }

  /**
   * Get a prompt from a server
   */
  async getPrompt(serverId: string, promptName: string, args?: Record<string, string>): Promise<string> {
    const client = this.getClient(serverId);
    if (!client) {
      const configs = await this.loadRegistry();
      const config = configs.find(c => c.id === serverId);
      if (!config) {
        throw new Error(`Server ${serverId} not found in registry`);
      }
      await this.connect(config);
      return this.getPrompt(serverId, promptName, args);
    }

    const result = await client.getPrompt({
      name: promptName,
      arguments: args
    });

    // Combine all messages into a single string
    return result.messages.map((msg: any) =>
      typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
    ).join('\n');
  }

  /**
   * List resources from a server
   */
  async listResources(serverId: string): Promise<any[]> {
    const client = this.getClient(serverId);
    if (!client) {
      const configs = await this.loadRegistry();
      const config = configs.find(c => c.id === serverId);
      if (!config) {
        throw new Error(`Server ${serverId} not found in registry`);
      }
      await this.connect(config);
      return this.listResources(serverId);
    }

    try {
      const result = await client.listResources();
      return result.resources || [];
    } catch (error: any) {
      // Some servers don't support resources
      if (error.message?.includes('not found') || error.code === -32601) {
        return [];
      }
      throw error;
    }
  }

  /**
   * Read a resource from a server
   */
  async readResource(serverId: string, uri: string): Promise<any> {
    const client = this.getClient(serverId);
    if (!client) {
      const configs = await this.loadRegistry();
      const config = configs.find(c => c.id === serverId);
      if (!config) {
        throw new Error(`Server ${serverId} not found in registry`);
      }
      await this.connect(config);
      return this.readResource(serverId, uri);
    }

    const result = await client.readResource({ uri });
    return result;
  }
}

// Singleton instance
let mcpManagerInstance: MCPManager | null = null;

/**
 * Get or create the MCPManager singleton
 */
export function getMCPManager(): MCPManager {
  if (!mcpManagerInstance) {
    mcpManagerInstance = new MCPManager();
  }
  return mcpManagerInstance;
}

/**
 * Clean up on app quit
 */
app.on('will-quit', async () => {
  if (mcpManagerInstance) {
    await mcpManagerInstance.disconnectAll();
  }
});
