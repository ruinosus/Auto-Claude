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
  customConfig?: CustomServerConfig;
}

export interface MCPTool {
  name: string;
  displayName: string;
  description: string;
  parameters?: MCPToolParameter[];
  examples?: string[];
  category?: string;
  // MCP Specification JSON Schema for tool input
  inputSchema?: {
    type?: string;
    properties?: Record<string, {
      type: string;
      description?: string;
      enum?: any[];
      default?: any;
      items?: any;
      properties?: any;
    }>;
    required?: string[];
  };
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

// Custom server configuration types
export interface CustomServerConfig {
  // Base fields
  name?: string;
  description?: string;
  connectionType: 'http' | 'stdio' | 'sse';

  // HTTP/SSE fields
  baseUrl?: string;
  authType?: 'none' | 'api-key' | 'bearer';
  authValue?: string;
  headers?: Record<string, string>;

  // stdio fields
  command?: string;
  args?: string[];
  workingDir?: string;
  env?: Record<string, string>;

  // SSE specific
  reconnectOnDisconnect?: boolean;
  reconnectDelay?: number;

  // FastMCP specific (Updated for Phase 3A with uv)
  isFastMCP?: boolean;
  generatedFrom?: 'wizard' | 'manual';
  template?: string;
  pythonVersion?: '3.10' | '3.11' | '3.12' | '3.13';
  sourceFiles?: {
    pyprojectToml: string;  // Changed from requirementsTxt
    serverPy: string;
    readmeMd: string;
    pythonVersion?: string;  // .python-version file path
  };
}

export interface ProcessInfo {
  pid?: number;
  port?: number;
  status: 'running' | 'stopped' | 'starting' | 'crashed';
  uptime?: number;
  startedAt?: string;
  lastError?: string;
  logFile?: string;
  restartCount?: number;
}

export interface MCPServerExport {
  version: '1.0';
  exportedAt: string;
  server: {
    name: string;
    description: string;
    type: MCPServerType;
    customConfig: CustomServerConfig;
    requiredEnvVars: string[];
  };
}

export interface MCPServersExport {
  version: '1.0';
  exportedAt: string;
  servers: MCPServerExport['server'][];
}

export interface MCPServersRegistry {
  version: '1.0';
  servers: MCPServer[];
  updatedAt: string;
}

// ===== FastMCP Types (Phase 3A) =====

export interface FastMCPTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;  // Lucide icon name
  tools: FastMCPTool[];
  dependencies: string[];  // Package specs like "httpx>=0.25.0"
}

export interface FastMCPTool {
  name: string;
  description: string;
  parameters: FastMCPToolParameter[];
}

export interface FastMCPToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  required: boolean;
  default?: any;
  description?: string;
}

export interface FastMCPServerConfig {
  // Wizard inputs
  templateId: string;
  serverName: string;
  description: string;
  pythonVersion: '3.10' | '3.11' | '3.12' | '3.13';
  workingDir: string;
  tools: FastMCPTool[];
  dependencies: string[];
}

// ===== Process Management Types (Phase 3A) =====

export type ProcessStatusType = 'stopped' | 'starting' | 'running' | 'stopping' | 'crashed';

export interface ProcessState {
  serverId: string;
  pid: number;
  startTime: Date;
  logBuffer: string[];  // Last 1000 lines
  restartCount: number;
  autoRestart: boolean;
  status: ProcessStatusType;
  exitCode?: number;
  signal?: string;
}

export interface ProcessStatus {
  serverId: string;
  status: ProcessStatusType;
  pid?: number;
  uptime?: number;  // milliseconds
  memory?: number;  // bytes
  restartCount: number;
  lastStarted?: Date;
  exitCode?: number;
}

export interface LogEntry {
  serverId: string;
  timestamp: Date;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
}
