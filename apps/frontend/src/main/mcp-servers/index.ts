/**
 * MCP Servers Initialization
 *
 * This module initializes Auto-Claude's internal MCP servers based on configuration.
 */

import { startAutoClaudeToolsHttpServer } from './auto-claude-tools-http';
import { startElectronApiBridge } from './electron-api-bridge';

let httpServerStarted = false;
let apiBridgeStarted = false;

/**
 * Initialize MCP servers based on AUTO_CLAUDE_TOOLS_MODE environment variable
 *
 * Modes:
 * - 'http' (default): Start HTTP MCP server on port 9823
 * - 'stdio': Start API bridge on port 9824 for STDIO server to communicate with Electron
 */
export function initializeMCPServers(): void {
  const mode = process.env.AUTO_CLAUDE_TOOLS_MODE || 'http';

  console.log(`[MCP Servers] Initializing in ${mode.toUpperCase()} mode`);

  if (mode === 'http') {
    // Option B: Start HTTP MCP server (in-process)
    if (!httpServerStarted) {
      try {
        startAutoClaudeToolsHttpServer();
        httpServerStarted = true;
        console.log('[MCP Servers] HTTP server started successfully');
      } catch (error) {
        console.error('[MCP Servers] Failed to start HTTP server:', error);
      }
    }
  } else if (mode === 'stdio') {
    // Option A: Start API bridge for STDIO server (subprocess)
    if (!apiBridgeStarted) {
      try {
        startElectronApiBridge();
        apiBridgeStarted = true;
        console.log('[MCP Servers] API bridge started successfully');
      } catch (error) {
        console.error('[MCP Servers] Failed to start API bridge:', error);
      }
    }
  } else {
    console.warn(`[MCP Servers] Unknown mode: ${mode}. Use 'http' or 'stdio'`);
  }
}

/**
 * Shutdown all MCP servers
 */
export function shutdownMCPServers(): void {
  console.log('[MCP Servers] Shutting down...');
  // TODO: Add proper cleanup for HTTP server and API bridge
  httpServerStarted = false;
  apiBridgeStarted = false;
}
