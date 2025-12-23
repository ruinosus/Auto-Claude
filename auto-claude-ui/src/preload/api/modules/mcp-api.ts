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
import { IPC_CHANNELS } from '../../../shared/constants';
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
      invokeIpc(IPC_CHANNELS.MCP_LIST, projectPath),

    testConnection: (serverId: string, config: MCPServerConfig): Promise<MCPTestConnectionResult> =>
      invokeIpc(IPC_CHANNELS.MCP_TEST_CONNECTION, serverId, config),

    saveConfig: (serverId: string, config: MCPServerConfig, projectPath?: string): Promise<{ success: boolean; error?: string }> =>
      invokeIpc(IPC_CHANNELS.MCP_SAVE_CONFIG, serverId, config, projectPath),

    getCapabilities: (serverId: string): Promise<{ tools: MCPTool[]; prompts: MCPPrompt[]; resources: MCPResource[] }> =>
      invokeIpc(IPC_CHANNELS.MCP_GET_CAPABILITIES, serverId),

    listPrompts: (serverId: string): Promise<MCPPrompt[]> =>
      invokeIpc(IPC_CHANNELS.MCP_LIST_PROMPTS, serverId),

    listResources: (serverId: string): Promise<MCPResource[]> =>
      invokeIpc(IPC_CHANNELS.MCP_LIST_RESOURCES, serverId),

    startFastMCPServer: (serverPath: string): Promise<{ success: boolean; port?: number; error?: string }> =>
      invokeIpc(IPC_CHANNELS.MCP_START_FASTMCP_SERVER, serverPath),

    stopFastMCPServer: (serverPath: string): Promise<{ success: boolean; error?: string }> =>
      invokeIpc(IPC_CHANNELS.MCP_STOP_FASTMCP_SERVER, serverPath),

    generateFastMCPServer: (wizardState: FastMCPWizardState, outputPath: string): Promise<MCPInstallResult> =>
      invokeIpc(IPC_CHANNELS.MCP_GENERATE_FASTMCP_SERVER, wizardState, outputPath)
  }
});
