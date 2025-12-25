/**
 * Integration Test: Registry Update After Server Generation
 *
 * Tests that generated FastMCP servers are properly registered in the MCP
 * servers registry and can be retrieved, updated, and managed.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { promises as fs } from 'fs';
import * as path from 'path';
import * as os from 'os';
import type { FastMCPServerConfig, MCPServersRegistry } from '../../shared/types/mcp';

// Mock uv utilities before importing registry-integration
vi.mock('../uv-utils', () => ({
  uvInit: vi.fn().mockResolvedValue(undefined),
  uvAdd: vi.fn().mockResolvedValue(undefined),
  uvSync: vi.fn().mockResolvedValue(undefined),
  checkUvInstalled: vi.fn().mockResolvedValue(true)
}));

// Mock IPC event
const mockEvent = {
  sender: {
    send: vi.fn()
  }
} as any;

describe('Integration: Registry Update After Generation', () => {
  let testDir: string;
  let registryPath: string;

  beforeEach(async () => {
    // Create temp directory for test
    testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'fastmcp-test-'));
    registryPath = path.join(testDir, '.mcp-servers.json');
  });

  afterEach(async () => {
    // Cleanup
    try {
      await fs.rm(testDir, { recursive: true, force: true });
    } catch (error) {
      // Ignore cleanup errors
    }
    vi.clearAllMocks();
  });

  it('should add generated server to registry with correct metadata', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'file-system',
      serverName: 'test-fs-server',
      description: 'Test file system server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-fs-server'),
      tools: [
        {
          name: 'read_file',
          description: 'Read a file',
          parameters: [
            { name: 'path', type: 'string', required: true }
          ]
        }
      ],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(true);
    expect(result.serverId).toBeDefined();

    // Verify registry file was created
    const registryExists = await fs.access(registryPath).then(() => true).catch(() => false);
    expect(registryExists).toBe(true);

    // Verify server was added to registry
    const registryContent = await fs.readFile(registryPath, 'utf-8');
    const registry: MCPServersRegistry = JSON.parse(registryContent);

    expect(registry.servers).toHaveLength(1);
    const server = registry.servers[0];

    expect(server.name).toBe('test-fs-server');
    expect(server.description).toBe('Test file system server');
    expect(server.type).toBe('custom');
    expect(server.category).toBe('Custom');
    expect(server.enabled).toBe(true);
    expect(server.customConfig?.command).toBe('uv');
    expect(server.customConfig?.args).toContain('run');
    expect(server.customConfig?.env?.PYTHONPATH).toBeDefined();
  });

  it('should include FastMCP-specific metadata in registry entry', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'api-wrapper',
      serverName: 'my-api-server',
      description: 'API wrapper server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'my-api-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0', 'httpx>=0.25.0']
    };

    await generateAndRegisterServer(config, registryPath, mockEvent);

    const registryContent = await fs.readFile(registryPath, 'utf-8');
    const registry: MCPServersRegistry = JSON.parse(registryContent);
    const server = registry.servers[0];

    // Check FastMCP-specific fields
    expect(server.customConfig?.isFastMCP).toBe(true);
    expect(server.customConfig?.generatedFrom).toBe('wizard');
    expect(server.customConfig?.template).toBe('api-wrapper');
    expect(server.customConfig?.pythonVersion).toBe('3.12');
    expect(server.customConfig?.sourceFiles).toBeDefined();
    expect(server.customConfig?.sourceFiles?.serverPy).toContain('server.py');
    expect(server.customConfig?.sourceFiles?.pyprojectToml).toContain('pyproject.toml');
    expect(server.customConfig?.sourceFiles?.readmeMd).toContain('README.md');
  });

  it('should update existing registry without overwriting other servers', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    // Create initial registry with one server
    const initialRegistry: MCPServersRegistry = {
      version: '1.0',
      updatedAt: new Date().toISOString(),
      servers: [
        {
          id: 'existing-server',
          name: 'Existing Server',
          description: 'Pre-existing server',
          type: 'custom',
          category: 'Custom',
          status: 'disabled',
          enabled: false,
          requiredEnvVars: [],
          capabilities: {},
          toolCount: 0,
          promptCount: 0,
          resourceCount: 0,
          connectionType: 'stdio',
          customConfig: {
            connectionType: 'stdio',
            command: 'node',
            args: ['server.js']
          }
        }
      ]
    };

    await fs.writeFile(registryPath, JSON.stringify(initialRegistry, null, 2));

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'new-server',
      description: 'New server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'new-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    await generateAndRegisterServer(config, registryPath, mockEvent);

    const registryContent = await fs.readFile(registryPath, 'utf-8');
    const registry: MCPServersRegistry = JSON.parse(registryContent);

    expect(registry.servers).toHaveLength(2);
    expect(registry.servers[0].id).toBe('existing-server');
    expect(registry.servers[1].name).toBe('new-server');
  });

  it('should handle registry creation when file does not exist', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'first-server',
      description: 'First server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'first-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(true);

    const registryContent = await fs.readFile(registryPath, 'utf-8');
    const registry: MCPServersRegistry = JSON.parse(registryContent);

    expect(registry.version).toBe('1.0');
    expect(registry.servers).toHaveLength(1);
  });

  it('should generate unique server IDs for each server', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config1: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'server-one',
      description: 'First server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'server-one'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const config2: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'server-two',
      description: 'Second server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'server-two'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result1 = await generateAndRegisterServer(config1, registryPath, mockEvent);
    const result2 = await generateAndRegisterServer(config2, registryPath, mockEvent);

    expect(result1.serverId).toBeDefined();
    expect(result2.serverId).toBeDefined();
    expect(result1.serverId).not.toBe(result2.serverId);

    const registryContent = await fs.readFile(registryPath, 'utf-8');
    const registry: MCPServersRegistry = JSON.parse(registryContent);

    expect(registry.servers).toHaveLength(2);
    expect(registry.servers[0].id).not.toBe(registry.servers[1].id);
  });

  it('should rollback registry if generation fails after registration', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    // Create a config that will fail during generation (invalid path)
    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'failing-server',
      description: 'This will fail',
      pythonVersion: '3.12',
      workingDir: '/invalid/path/that/cannot/be/created',
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();

    // Registry should either not exist or be empty
    const registryExists = await fs.access(registryPath).then(() => true).catch(() => false);

    if (registryExists) {
      const registryContent = await fs.readFile(registryPath, 'utf-8');
      const registry: MCPServersRegistry = JSON.parse(registryContent);
      expect(registry.servers).toHaveLength(0);
    }
  });

  it('should emit progress events during generation and registration', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'progress-test',
      description: 'Test progress events',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'progress-test'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    await generateAndRegisterServer(config, registryPath, mockEvent);

    // Verify progress events were sent
    expect(mockEvent.sender.send).toHaveBeenCalled();

    const progressCalls = mockEvent.sender.send.mock.calls.filter(
      call => call[0] === 'mcp:generation-progress'
    );

    expect(progressCalls.length).toBeGreaterThan(0);

    // Check that we got a completion event
    const completeCalls = progressCalls.filter(
      call => call[1].step === 'complete'
    );

    expect(completeCalls.length).toBeGreaterThan(0);
  });
});
