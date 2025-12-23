import type {
  MCPServer,
  MCPServerConfig,
  MCPTestConnectionResult,
  MCPTool,
  MCPPrompt,
  MCPResource,
  MCPInstallResult,
  FastMCPWizardState
} from '../../../shared/types/mcp';
import { invokeIpc } from './ipc-utils';

/**
 * MCP API operations (nested under 'mcp' property)
 */
export interface MCPAPI {
  mcp: {
    list: (projectPath?: string) => Promise<MCPServer[]>;
    testConnection: (serverId: string, config: MCPServerConfig) => Promise<MCPTestConnectionResult>;
    saveConfig: (serverId: string, config: MCPServerConfig, projectPath?: string) => Promise<{ success: boolean; error?: string }>;
    getCapabilities: (serverId: string) => Promise<{ tools: MCPTool[]; prompts: MCPPrompt[]; resources: MCPResource[] }>;
    listPrompts: (serverId: string) => Promise<MCPPrompt[]>;
    listResources: (serverId: string) => Promise<MCPResource[]>;
    startFastMCPServer: (serverPath: string) => Promise<{ success: boolean; port?: number; error?: string }>;
    stopFastMCPServer: (serverPath: string) => Promise<{ success: boolean; error?: string }>;
    generateFastMCPServer: (wizardState: FastMCPWizardState, outputPath: string) => Promise<MCPInstallResult>;
  };
}

/**
 * Creates the MCP API implementation
 */
export const createMCPAPI = (): MCPAPI => ({
  mcp: {
    list: (projectPath?: string): Promise<MCPServer[]> =>
      invokeIpc('mcp:list', projectPath),

    testConnection: (serverId: string, config: MCPServerConfig): Promise<MCPTestConnectionResult> =>
      invokeIpc('mcp:test-connection', serverId, config),

    saveConfig: (serverId: string, config: MCPServerConfig, projectPath?: string): Promise<{ success: boolean; error?: string }> =>
      invokeIpc('mcp:save-config', serverId, config, projectPath),

    getCapabilities: (serverId: string): Promise<{ tools: MCPTool[]; prompts: MCPPrompt[]; resources: MCPResource[] }> =>
      invokeIpc('mcp:get-capabilities', serverId),

    listPrompts: (serverId: string): Promise<MCPPrompt[]> =>
      invokeIpc('mcp:list-prompts', serverId),

    listResources: (serverId: string): Promise<MCPResource[]> =>
      invokeIpc('mcp:list-resources', serverId),

    startFastMCPServer: (serverPath: string): Promise<{ success: boolean; port?: number; error?: string }> =>
      invokeIpc('mcp:start-fastmcp-server', serverPath),

    stopFastMCPServer: (serverPath: string): Promise<{ success: boolean; error?: string }> =>
      invokeIpc('mcp:stop-fastmcp-server', serverPath),

    generateFastMCPServer: (wizardState: FastMCPWizardState, outputPath: string): Promise<MCPInstallResult> =>
      invokeIpc('mcp:generate-fastmcp-server', wizardState, outputPath)
  }
});
