/**
 * MCP Servers Configuration
 * =========================
 *
 * Single source of truth for all MCP server definitions.
 * Used by both mcp-manager.ts (IPC handlers) and mcp-manager-v2.ts (connection manager).
 */

import { app } from 'electron';
import path from 'path';
import { existsSync } from 'fs';
import type { MCPServer } from '../shared/types/mcp';

/**
 * Transport configuration for MCPManager
 */
export interface MCPTransportConfig {
  id: string;
  name: string;
  description: string;
  transport: 'stdio' | 'http';
  command?: string;
  args?: string[];
  cwd?: string;
  env?: Record<string, string>;
  url?: string;
  headers?: Record<string, string>;
  enabled: boolean;
  requiredEnvVars?: string[];
  category: string;
  icon: string;
}

/**
 * Get path to auto-claude-tools MCP server
 * Tries multiple locations to work in dev, build, and packaged modes
 */
function getAutoClaudeToolsPath(): string {
  const possiblePaths = [
    // Development mode: from out/main -> src/main
    path.resolve(__dirname, '..', '..', 'src', 'main', 'mcp-servers', 'auto-claude-tools-stdio.ts'),
    // Development mode: direct src path
    path.resolve(app.getAppPath(), 'src', 'main', 'mcp-servers', 'auto-claude-tools-stdio.ts'),
    // Production: from packaged app -> compiled JS in out/main
    path.resolve(__dirname, 'mcp-servers', 'auto-claude-tools-stdio.js'),
    // Fallback: process.cwd based paths
    path.resolve(process.cwd(), 'src', 'main', 'mcp-servers', 'auto-claude-tools-stdio.ts'),
    path.resolve(process.cwd(), 'apps', 'frontend', 'src', 'main', 'mcp-servers', 'auto-claude-tools-stdio.ts'),
  ];

  // Find first existing path
  for (const p of possiblePaths) {
    if (existsSync(p)) {
      console.log(`[MCP Config] Found auto-claude-tools at: ${p}`);
      return p;
    }
  }

  // Log debug info if not found
  console.warn('[MCP Config] auto-claude-tools not found. Searched paths:');
  console.warn(`  __dirname: ${__dirname}`);
  console.warn(`  app.getAppPath(): ${app.getAppPath()}`);
  console.warn(`  process.cwd(): ${process.cwd()}`);
  possiblePaths.forEach(p => console.warn(`  - ${p}`));

  // Return first path as fallback (will fail on connection)
  return possiblePaths[0];
}

/**
 * Get working directory for auto-claude-tools
 */
function getAutoClaudeToolsCwd(): string {
  const possibleCwds = [
    // Development: apps/frontend root
    path.resolve(__dirname, '..', '..'),
    app.getAppPath(),
    process.cwd(),
  ];

  // Return first directory that has package.json
  for (const cwd of possibleCwds) {
    if (existsSync(path.join(cwd, 'package.json'))) {
      return cwd;
    }
  }

  return app.getAppPath();
}

/**
 * Built-in MCP server transport configurations
 * Used by MCPManager for actual connections
 */
export function getTransportConfigs(): MCPTransportConfig[] {
  return [
    {
      id: 'context7',
      name: 'Context7',
      description: 'Real-time documentation lookup for any library',
      transport: 'http',
      url: 'https://mcp.context7.com/mcp',
      enabled: true,
      category: 'Documentation',
      icon: 'Book'
    },
    {
      id: 'auto-claude-tools',
      name: 'Auto-Claude Tools',
      description: 'Build progress, context, memory, and ROI tracking tools',
      transport: 'stdio',
      command: 'npx',
      args: ['tsx', getAutoClaudeToolsPath()],
      cwd: getAutoClaudeToolsCwd(),
      enabled: true,
      category: 'Internal',
      icon: 'Wrench'
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
    },
    {
      id: 'electron',
      name: 'Electron Automation',
      description: 'Desktop app testing via Chrome DevTools Protocol',
      transport: 'http',
      url: 'http://localhost:${ELECTRON_DEBUG_PORT:-9222}',
      enabled: false,
      requiredEnvVars: ['ELECTRON_MCP_ENABLED'],
      category: 'Browser Automation',
      icon: 'Monitor'
    }
  ];
}

/**
 * Built-in MCP server UI configurations
 * Used by mcp-manager.ts for UI display
 */
export function getBuiltInServers(): MCPServer[] {
  const transportConfigs = getTransportConfigs();

  return transportConfigs.map(config => ({
    id: config.id,
    name: config.name,
    description: config.description,
    type: config.id === 'auto-claude-tools' ? 'internal' as const : 'builtin' as const,
    category: config.category as any,
    status: config.enabled ? 'connected' as const : 'disabled' as const,
    enabled: config.enabled,
    requiredEnvVars: config.requiredEnvVars || [],
    capabilities: {
      tools: [] // Loaded dynamically via MCP connection
    },
    toolCount: getToolCount(config.id),
    promptCount: getPromptCount(config.id),
    resourceCount: getResourceCount(config.id),
    connectionType: config.transport === 'stdio' ? 'stdio' as const : 'http' as const,
    icon: config.icon,
    color: getServerColor(config.id),
    customConfig: config.transport === 'stdio' ? {
      connectionType: 'stdio' as const,
      command: config.command,
      args: config.args,
      workingDir: config.cwd,
      env: config.env
    } : {
      connectionType: 'http' as const,
      baseUrl: config.url,
      headers: config.headers
    }
  }));
}

/**
 * Get expected tool count for a server
 */
function getToolCount(serverId: string): number {
  const counts: Record<string, number> = {
    'context7': 2,
    'auto-claude-tools': 11,
    'puppeteer': 8,
    'linear': 12,
    'graphiti': 5,
    'electron': 4
  };
  return counts[serverId] || 0;
}

/**
 * Get expected prompt count for a server
 */
function getPromptCount(serverId: string): number {
  const counts: Record<string, number> = {
    'context7': 0,
    'auto-claude-tools': 6,
    'puppeteer': 0,
    'linear': 0,
    'graphiti': 0,
    'electron': 0
  };
  return counts[serverId] || 0;
}

/**
 * Get expected resource count for a server
 */
function getResourceCount(serverId: string): number {
  const counts: Record<string, number> = {
    'context7': 0,
    'auto-claude-tools': 6,
    'puppeteer': 0,
    'linear': 0,
    'graphiti': 0,
    'electron': 0
  };
  return counts[serverId] || 0;
}

/**
 * Get color for a server
 */
function getServerColor(serverId: string): string {
  const colors: Record<string, string> = {
    'context7': 'blue',
    'auto-claude-tools': 'gray',
    'puppeteer': 'blue',
    'linear': 'blue',
    'graphiti': 'purple',
    'electron': 'blue'
  };
  return colors[serverId] || 'gray';
}

/**
 * Get transport config by ID
 */
export function getTransportConfigById(serverId: string): MCPTransportConfig | undefined {
  return getTransportConfigs().find(c => c.id === serverId);
}
