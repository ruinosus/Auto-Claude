/**
 * Unit tests for MCP IPC handlers
 * Tests custom server management (addCustomServer, testConnection)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { EventEmitter } from 'events';
import { mkdirSync, writeFileSync, rmSync, existsSync, readFileSync } from 'fs';
import path from 'path';
import type { CustomServerConfig } from '../../shared/types/mcp';

// Test data directory
const TEST_DIR = '/tmp/mcp-handlers-test';
const HOME_DIR = path.join(TEST_DIR, 'home');
const PROJECT_DIR = path.join(TEST_DIR, 'project');

// Mock electron before importing
vi.mock('electron', () => {
  const mockIpcMain = new (class extends EventEmitter {
    private handlers: Map<string, Function> = new Map();

    handle(channel: string, handler: Function): void {
      this.handlers.set(channel, handler);
    }

    removeHandler(channel: string): void {
      this.handlers.delete(channel);
    }

    async invokeHandler(channel: string, event: unknown, ...args: unknown[]): Promise<unknown> {
      const handler = this.handlers.get(channel);
      if (handler) {
        return handler(event, ...args);
      }
      throw new Error(`No handler for channel: ${channel}`);
    }

    getHandler(channel: string): Function | undefined {
      return this.handlers.get(channel);
    }
  })();

  return {
    app: {
      getPath: vi.fn((name: string) => {
        if (name === 'home') return HOME_DIR;
        if (name === 'userData') return path.join(HOME_DIR, '.auto-claude');
        return TEST_DIR;
      }),
      getAppPath: vi.fn(() => TEST_DIR),
      getVersion: vi.fn(() => '0.1.0'),
      isPackaged: false
    },
    ipcMain: mockIpcMain
  };
});

// Import after mocking
import { ipcMain } from 'electron';
import { registerMCPHandlers } from '../mcp-manager';

// Setup test directories
function setupTestDirectories(): void {
  mkdirSync(HOME_DIR, { recursive: true });
  mkdirSync(path.join(HOME_DIR, '.auto-claude'), { recursive: true });
  mkdirSync(PROJECT_DIR, { recursive: true });
  mkdirSync(path.join(PROJECT_DIR, '.auto-claude'), { recursive: true });
}

// Clean up test directories
function cleanupTestDirectories(): void {
  if (existsSync(TEST_DIR)) {
    rmSync(TEST_DIR, { recursive: true, force: true });
  }
}

describe('MCP IPC Handlers - addCustomServer', () => {
  beforeEach(() => {
    setupTestDirectories();
    registerMCPHandlers();
  });

  afterEach(() => {
    cleanupTestDirectories();
  });

  it('should add HTTP custom server to global config', async () => {
    const config: CustomServerConfig = {
      name: 'Test HTTP Server',
      description: 'A test HTTP server',
      connectionType: 'http',
      baseUrl: 'http://localhost:8000',
      authType: 'bearer',
      authValue: 'test-token-123',
      headers: { 'X-Custom': 'value' }
    };

    const result = await (ipcMain as any).invokeHandler(
      'mcp:add-custom-server',
      {},
      config,
      'global'
    );

    expect(result.success).toBe(true);
    expect(result.serverId).toBeDefined();
    expect(result.serverId).toMatch(/^custom-http-\d+$/);

    // Verify file was written
    const configPath = path.join(HOME_DIR, '.auto-claude', 'mcp-servers.json');
    expect(existsSync(configPath)).toBe(true);

    // Verify content
    const savedConfig = JSON.parse(readFileSync(configPath, 'utf-8'));
    expect(savedConfig.servers).toHaveLength(1);
    expect(savedConfig.servers[0].name).toBe('Test HTTP Server');
    expect(savedConfig.servers[0].customConfig.connectionType).toBe('http');
  });

  it('should add stdio custom server to project config', async () => {
    const config: CustomServerConfig = {
      name: 'Test stdio Server',
      description: 'A test stdio server',
      connectionType: 'stdio',
      command: 'python3',
      args: ['server.py'],
      workingDir: '/path/to/server',
      env: { PORT: '8000' }
    };

    const result = await (ipcMain as any).invokeHandler(
      'mcp:add-custom-server',
      {},
      config,
      'project',
      PROJECT_DIR
    );

    expect(result.success).toBe(true);
    expect(result.serverId).toMatch(/^custom-stdio-\d+$/);

    // Verify file was written to project directory
    const configPath = path.join(PROJECT_DIR, '.auto-claude', 'mcp-servers.json');
    expect(existsSync(configPath)).toBe(true);

    // Verify content
    const savedConfig = JSON.parse(readFileSync(configPath, 'utf-8'));
    expect(savedConfig.servers[0].customConfig.command).toBe('python3');
  });

  it('should add SSE custom server with reconnect options', async () => {
    const config: CustomServerConfig = {
      name: 'Test SSE Server',
      description: 'A test SSE server',
      connectionType: 'sse',
      baseUrl: 'http://localhost:8000/events',
      reconnectOnDisconnect: true,
      reconnectDelay: 5
    };

    const result = await (ipcMain as any).invokeHandler(
      'mcp:add-custom-server',
      {},
      config,
      'global'
    );

    expect(result.success).toBe(true);
    expect(result.serverId).toMatch(/^custom-sse-\d+$/);

    // Verify content
    const configPath = path.join(HOME_DIR, '.auto-claude', 'mcp-servers.json');
    const savedConfig = JSON.parse(readFileSync(configPath, 'utf-8'));
    expect(savedConfig.servers[0].customConfig.reconnectOnDisconnect).toBe(true);
  });

  it('should fail validation when HTTP server missing baseUrl', async () => {
    const config: CustomServerConfig = {
      name: 'Invalid HTTP Server',
      description: 'Missing baseUrl',
      connectionType: 'http',
      // baseUrl is missing - should fail validation
      authType: 'none'
    };

    const result = await (ipcMain as any).invokeHandler(
      'mcp:add-custom-server',
      {},
      config,
      'global'
    );

    expect(result.success).toBe(false);
    expect(result.error).toContain('baseUrl');
  });

  it('should fail validation when stdio server missing command', async () => {
    const config: CustomServerConfig = {
      name: 'Invalid stdio Server',
      description: 'Missing command',
      connectionType: 'stdio',
      // command is missing - should fail validation
      args: ['server.py']
    };

    const result = await (ipcMain as any).invokeHandler(
      'mcp:add-custom-server',
      {},
      config,
      'global'
    );

    expect(result.success).toBe(false);
    expect(result.error).toContain('command');
  });

  it('should append to existing servers in config file', async () => {
    // Add first server
    const config1: CustomServerConfig = {
      name: 'First Server',
      connectionType: 'http',
      baseUrl: 'http://localhost:8000'
    };

    await (ipcMain as any).invokeHandler(
      'mcp:add-custom-server',
      {},
      config1,
      'global'
    );

    // Add second server
    const config2: CustomServerConfig = {
      name: 'Second Server',
      connectionType: 'stdio',
      command: 'node',
      args: ['server.js']
    };

    await (ipcMain as any).invokeHandler(
      'mcp:add-custom-server',
      {},
      config2,
      'global'
    );

    // Verify both servers exist
    const configPath = path.join(HOME_DIR, '.auto-claude', 'mcp-servers.json');
    const savedConfig = JSON.parse(readFileSync(configPath, 'utf-8'));
    expect(savedConfig.servers).toHaveLength(2);
    expect(savedConfig.servers[0].name).toBe('First Server');
    expect(savedConfig.servers[1].name).toBe('Second Server');
  });
});

describe('MCP IPC Handlers - testConnection', () => {
  beforeEach(() => {
    setupTestDirectories();
    registerMCPHandlers();
  });

  afterEach(() => {
    cleanupTestDirectories();
  });

  it('should return simulated success for HTTP connection test', async () => {
    const config: CustomServerConfig = {
      connectionType: 'http',
      baseUrl: 'http://localhost:8000',
      authType: 'bearer',
      authValue: 'test-token'
    };

    const result = await (ipcMain as any).invokeHandler(
      'mcp:test-connection-custom',
      {},
      config
    );

    expect(result.success).toBe(true);
    expect(result.status).toBe('connected');
    expect(result.capabilities).toBeDefined();
    expect(result.capabilities.tools).toBeDefined();
    expect(Array.isArray(result.capabilities.tools)).toBe(true);
  });

  it('should return simulated success for stdio connection test', async () => {
    const config: CustomServerConfig = {
      connectionType: 'stdio',
      command: 'python3',
      args: ['server.py'],
      workingDir: '/path/to/server'
    };

    const result = await (ipcMain as any).invokeHandler(
      'mcp:test-connection-custom',
      {},
      config
    );

    expect(result.success).toBe(true);
    expect(result.status).toBe('connected');
    expect(result.message).toContain('stdio');
  });

  it('should return simulated success for SSE connection test', async () => {
    const config: CustomServerConfig = {
      connectionType: 'sse',
      baseUrl: 'http://localhost:8000/events',
      reconnectOnDisconnect: true
    };

    const result = await (ipcMain as any).invokeHandler(
      'mcp:test-connection-custom',
      {},
      config
    );

    expect(result.success).toBe(true);
    expect(result.status).toBe('connected');
    expect(result.capabilities.prompts).toBeDefined();
  });

  it('should include simulated capabilities in test result', async () => {
    const config: CustomServerConfig = {
      connectionType: 'http',
      baseUrl: 'http://localhost:8000'
    };

    const result = await (ipcMain as any).invokeHandler(
      'mcp:test-connection-custom',
      {},
      config
    );

    expect(result.capabilities).toEqual({
      tools: [
        { name: 'test-tool', description: 'A test tool' }
      ],
      prompts: [
        { name: 'test-prompt', description: 'A test prompt' }
      ],
      resources: []
    });
  });

  it('should fail validation when testing invalid config', async () => {
    const config: CustomServerConfig = {
      connectionType: 'http',
      // Missing required baseUrl
      authType: 'none'
    };

    const result = await (ipcMain as any).invokeHandler(
      'mcp:test-connection-custom',
      {},
      config
    );

    expect(result.success).toBe(false);
    expect(result.error).toContain('baseUrl');
  });
});
