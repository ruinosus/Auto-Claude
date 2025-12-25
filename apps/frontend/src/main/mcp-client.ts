/**
 * Native TypeScript MCP Client
 * Uses @modelcontextprotocol/sdk to connect to MCP servers directly
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { spawn } from 'child_process';
import path from 'path';
import { app } from 'electron';
import { existsSync } from 'fs';

interface MCPServerConnection {
  client: Client;
  transport: StdioClientTransport;
}

// Active connections to MCP servers
const connections = new Map<string, MCPServerConnection>();

// Pending connection promises (prevents race conditions)
const pendingConnections = new Map<string, Promise<void>>();

/**
 * Get MCP server configuration
 */
function getServerConfig(serverId: string): { command: string; args: string[]; env?: Record<string, string> } | null {
  // Built-in servers configuration
  const configs: Record<string, { command: string; args: string[]; env?: Record<string, string> }> = {
    'context7': {
      command: 'npx',
      args: ['-y', '@upstash/context7-mcp'],
      env: {
        // Context7 doesn't need special env vars
      }
    }
  };

  return configs[serverId] || null;
}

/**
 * Connect to an MCP server
 */
export async function connectToServer(serverId: string): Promise<void> {
  // Check if already connected
  if (connections.has(serverId)) {
    console.log(`[MCP Client] Already connected to ${serverId}`);
    return;
  }

  // Check if connection is already in progress (PREVENTS RACE CONDITION)
  const pending = pendingConnections.get(serverId);
  if (pending) {
    console.log(`[MCP Client] Connection to ${serverId} already in progress, waiting...`);
    return pending; // Wait for existing connection attempt
  }

  // Create new connection promise
  const connectionPromise = (async () => {
    try {
      const config = getServerConfig(serverId);
      if (!config) {
        throw new Error(`Unknown MCP server: ${serverId}`);
      }

      console.log(`[MCP Client] Connecting to ${serverId}...`);
      console.log(`[MCP Client] Command: ${config.command} ${config.args.join(' ')}`);

      // Create transport using stdio
      const transport = new StdioClientTransport({
        command: config.command,
        args: config.args,
    env: {
      ...process.env,
      ...config.env
    }
  });

  // Create client
  const client = new Client({
    name: 'auto-claude-ui',
    version: '1.0.0'
  }, {
    capabilities: {}
  });

      // Connect
      await client.connect(transport);

      // Store connection
      connections.set(serverId, { client, transport });

      console.log(`[MCP Client] Connected to ${serverId}`);
    } finally {
      // Remove from pending connections
      pendingConnections.delete(serverId);
    }
  })();

  // Store pending connection
  pendingConnections.set(serverId, connectionPromise);

  // Wait for connection to complete
  return connectionPromise;
}

/**
 * Disconnect from an MCP server
 */
export async function disconnectFromServer(serverId: string): Promise<void> {
  const connection = connections.get(serverId);
  if (!connection) {
    console.warn(`[MCP Client] Not connected to ${serverId}`);
    return;
  }

  await connection.client.close();
  connections.delete(serverId);
  pendingConnections.delete(serverId); // Clean up pending connections too

  console.log(`[MCP Client] Disconnected from ${serverId}`);
}

/**
 * List available tools from a server
 */
export async function listTools(serverId: string): Promise<any[]> {
  const connection = connections.get(serverId);
  if (!connection) {
    // Try to connect first
    await connectToServer(serverId);
    return listTools(serverId);
  }

  const result = await connection.client.listTools();
  return result.tools || [];
}

/**
 * Call a tool on an MCP server
 */
export async function callTool(serverId: string, toolName: string, args: any): Promise<any> {
  const connection = connections.get(serverId);
  if (!connection) {
    // Try to connect first
    await connectToServer(serverId);
    return callTool(serverId, toolName, args);
  }

  console.log(`[MCP Client] Calling tool ${toolName} on ${serverId} with args:`, args);

  const result = await connection.client.callTool({
    name: toolName,
    arguments: args
  });

  console.log(`[MCP Client] Tool result:`, result);

  return result;
}

/**
 * List available prompts from a server
 */
export async function listPrompts(serverId: string): Promise<any[]> {
  const connection = connections.get(serverId);
  if (!connection) {
    await connectToServer(serverId);
    return listPrompts(serverId);
  }

  try {
    const result = await connection.client.listPrompts();
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
export async function getPrompt(serverId: string, promptName: string, args?: Record<string, string>): Promise<string> {
  const connection = connections.get(serverId);
  if (!connection) {
    await connectToServer(serverId);
    return getPrompt(serverId, promptName, args);
  }

  const result = await connection.client.getPrompt({
    name: promptName,
    arguments: args
  });

  // Combine all messages into a single string
  return result.messages.map((msg: any) =>
    typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
  ).join('\n');
}

/**
 * List available resources from a server
 */
export async function listResources(serverId: string): Promise<any[]> {
  const connection = connections.get(serverId);
  if (!connection) {
    await connectToServer(serverId);
    return listResources(serverId);
  }

  try {
    const result = await connection.client.listResources();
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
export async function readResource(serverId: string, uri: string): Promise<any> {
  const connection = connections.get(serverId);
  if (!connection) {
    await connectToServer(serverId);
    return readResource(serverId, uri);
  }

  const result = await connection.client.readResource({ uri });
  return result;
}

/**
 * Disconnect all servers on app quit
 */
export async function disconnectAll(): Promise<void> {
  const serverIds = Array.from(connections.keys());
  await Promise.all(serverIds.map(id => disconnectFromServer(id)));
}
