import type {
  MCPServer,
  MCPServerConfig,
  MCPTestConnectionResult,
  MCPTool,
  MCPPrompt,
  MCPResource,
  MCPInstallResult,
  FastMCPWizardState,
  FastMCPServerConfig,
  CustomServerConfig
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
    callTool: (serverId: string, toolName: string, args: any) => Promise<any>;
    listPrompts: (serverId: string) => Promise<MCPPrompt[]>;
    listResources: (serverId: string) => Promise<MCPResource[]>;
    startFastMCPServer: (serverPath: string) => Promise<{ success: boolean; port?: number; error?: string }>;
    stopFastMCPServer: (serverPath: string) => Promise<{ success: boolean; error?: string }>;
    generateFastMCPServer: (config: FastMCPServerConfig) => Promise<MCPInstallResult>;
    addCustomServer: (config: CustomServerConfig, scope: 'global' | 'project', projectPath?: string) => Promise<{ success: boolean; serverId?: string; error?: string }>;
    testConnectionCustom: (config: CustomServerConfig) => Promise<MCPTestConnectionResult & { capabilities?: { tools?: unknown[]; prompts?: unknown[]; resources?: unknown[] } }>;
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

    callTool: (serverId: string, toolName: string, args: any): Promise<any> =>
      invokeIpc(IPC_CHANNELS.MCP_CALL_TOOL, serverId, toolName, args),

    listPrompts: (serverId: string): Promise<MCPPrompt[]> =>
      invokeIpc(IPC_CHANNELS.MCP_LIST_PROMPTS, serverId),

    listResources: (serverId: string): Promise<MCPResource[]> =>
      invokeIpc(IPC_CHANNELS.MCP_LIST_RESOURCES, serverId),

    startFastMCPServer: (serverPath: string): Promise<{ success: boolean; port?: number; error?: string }> =>
      invokeIpc(IPC_CHANNELS.MCP_START_FASTMCP_SERVER, serverPath),

    stopFastMCPServer: (serverPath: string): Promise<{ success: boolean; error?: string }> =>
      invokeIpc(IPC_CHANNELS.MCP_STOP_FASTMCP_SERVER, serverPath),

    generateFastMCPServer: (config: FastMCPServerConfig): Promise<MCPInstallResult> =>
      invokeIpc(IPC_CHANNELS.MCP_GENERATE_FASTMCP_SERVER, config),

    addCustomServer: (config: CustomServerConfig, scope: 'global' | 'project', projectPath?: string): Promise<{ success: boolean; serverId?: string; error?: string }> =>
      invokeIpc(IPC_CHANNELS.MCP_ADD_CUSTOM_SERVER, config, scope, projectPath),

    testConnectionCustom: (config: CustomServerConfig): Promise<MCPTestConnectionResult & { capabilities?: { tools?: unknown[]; prompts?: unknown[]; resources?: unknown[] } }> =>
      invokeIpc(IPC_CHANNELS.MCP_TEST_CONNECTION_CUSTOM, config)
  }
});
