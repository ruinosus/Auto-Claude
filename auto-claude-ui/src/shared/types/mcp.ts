/**
 * MCP (Model Context Protocol) Type Definitions
 * Following MCP Specification 2025-06-18
 */

export type MCPServerStatus = 'connected' | 'disconnected' | 'error' | 'disabled' | 'connecting';
export type MCPServerType = 'builtin' | 'custom' | 'project' | 'internal';
export type MCPConnectionType = 'http' | 'stdio' | 'sdk';
export type MCPCategory =
  | 'Documentation'
  | 'Project Management'
  | 'Memory'
  | 'Browser Automation'
  | 'Internal'
  | 'Custom';

export interface MCPServer {
  // Identity
  id: string;
  name: string;
  description: string;
  type: MCPServerType;
  category: MCPCategory;

  // Status
  status: MCPServerStatus;
  enabled: boolean;
  statusMessage?: string;

  // Configuration
  requiredEnvVars: string[];
  optionalEnvVars?: string[];
  configUrl?: string;

  // MCP Capabilities
  capabilities: {
    tools?: MCPTool[];
    prompts?: MCPPrompt[];
    resources?: MCPResource[];
  };

  // Counts
  toolCount: number;
  promptCount: number;
  resourceCount: number;

  // Connection
  connectionType: MCPConnectionType;
  endpoint?: string;
  port?: number;

  // Requirements
  pythonVersion?: string;
  systemRequirements?: string[];

  // UI
  icon?: string;
  color?: string;

  // Custom servers
  serverPath?: string;
  isRunning?: boolean;
}

export interface MCPTool {
  name: string;
  displayName: string;
  description: string;
  parameters?: MCPToolParameter[];
  examples?: string[];
  category?: string;
}

export interface MCPToolParameter {
  name: string;
  type: string;
  required: boolean;
  description: string;
  default?: any;
}

export interface MCPPrompt {
  name: string;
  displayName: string;
  description: string;
  arguments?: MCPPromptArgument[];
  template?: string;
  category?: string;
}

export interface MCPPromptArgument {
  name: string;
  description: string;
  required: boolean;
}

export interface MCPResource {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
  isTemplate: boolean;
  templateParams?: string[];
}

export interface MCPServerConfig {
  enabled: boolean;
  envVars: Record<string, string>;
  scope: 'global' | 'project';
}

export interface MCPConfiguration {
  enabled: boolean;
  servers: Record<string, MCPServerConfig>;
}

export interface MCPTestConnectionResult {
  success: boolean;
  status: MCPServerStatus;
  message?: string;
  toolsFound?: number;
  promptsFound?: number;
  resourcesFound?: number;
}

export interface MCPInstallResult {
  success: boolean;
  error?: string;
  serverPath?: string;
  port?: number;
}

export interface FastMCPWizardState {
  step: 1 | 2 | 3 | 4;
  serverInfo: {
    name: string;
    description: string;
    version: string;
  };
  tools: Array<{
    name: string;
    description: string;
    parameters: Array<{ name: string; type: string; required: boolean }>;
  }>;
  prompts: Array<{
    name: string;
    description: string;
    arguments: Array<{ name: string; required: boolean }>;
  }>;
  resources: Array<{
    uri: string;
    name: string;
    description: string;
  }>;
}
