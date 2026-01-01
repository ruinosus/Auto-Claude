/**
 * MCP Servers Initialization
 *
 * This module initializes Auto-Claude's internal MCP servers based on configuration.
 */

import { startElectronApiBridge } from './electron-api-bridge';

let apiBridgeStarted = false;

/**
 * Initialize MCP servers
 *
 * Always starts the API bridge on port 9824 for the STDIO MCP server to communicate
 * with the Electron main process. The STDIO server is spawned by MCPManager when needed.
 */
export function initializeMCPServers(): void {
  console.log('[MCP Servers] Initializing API Bridge for STDIO transport');

  // Start API bridge for STDIO server (auto-claude-tools-stdio.ts)
  // This provides HTTP endpoints that the STDIO subprocess can call
  if (!apiBridgeStarted) {
    try {
      startElectronApiBridge();
      apiBridgeStarted = true;
      console.log('[MCP Servers] API bridge started on port 9824');
    } catch (error) {
      console.error('[MCP Servers] Failed to start API bridge:', error);
    }
  }
}

/**
 * Shutdown all MCP servers
 */
export function shutdownMCPServers(): void {
  console.log('[MCP Servers] Shutting down...');
  // TODO: Add proper cleanup for API bridge
  apiBridgeStarted = false;
}
