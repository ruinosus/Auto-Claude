/**
 * Integration Test: Python Version Management
 *
 * Tests that the system properly handles Python version configuration
 * including .python-version file creation and version metadata in registry.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { promises as fs } from 'fs';
import * as path from 'path';
import * as os from 'os';
import type { FastMCPServerConfig, MCPServersRegistry } from '../../shared/types/mcp';

// Mock uv utilities to simulate successful uv operations
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

describe('Integration: Python Version Management', () => {
  let testDir: string;
  let registryPath: string;

  beforeEach(async () => {
    // Create temp directory for test
    testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'fastmcp-python-version-test-'));
    registryPath = path.join(testDir, '.mcp-servers.json');
    vi.clearAllMocks();
  });

  afterEach(async () => {
    // Cleanup
    try {
      await fs.rm(testDir, { recursive: true, force: true });
    } catch (error) {
      // Ignore cleanup errors
    }
  });

  it('should create .python-version file with correct version', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(true);

    // Verify .python-version file exists
    const pythonVersionPath = path.join(config.workingDir, '.python-version');
    const content = await fs.readFile(pythonVersionPath, 'utf-8');
    expect(content).toBe('3.12');
  });

  it('should handle Python 3.10 version', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server-310',
      description: 'Test server with Python 3.10',
      pythonVersion: '3.10',
      workingDir: path.join(testDir, 'test-server-310'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(true);

    const pythonVersionPath = path.join(config.workingDir, '.python-version');
    const content = await fs.readFile(pythonVersionPath, 'utf-8');
    expect(content).toBe('3.10');
  });

  it('should handle Python 3.11 version', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server-311',
      description: 'Test server with Python 3.11',
      pythonVersion: '3.11',
      workingDir: path.join(testDir, 'test-server-311'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(true);

    const pythonVersionPath = path.join(config.workingDir, '.python-version');
    const content = await fs.readFile(pythonVersionPath, 'utf-8');
    expect(content).toBe('3.11');
  });

  it('should handle Python 3.13 version', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server-313',
      description: 'Test server with Python 3.13',
      pythonVersion: '3.13',
      workingDir: path.join(testDir, 'test-server-313'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(true);

    const pythonVersionPath = path.join(config.workingDir, '.python-version');
    const content = await fs.readFile(pythonVersionPath, 'utf-8');
    expect(content).toBe('3.13');
  });

  it('should include pythonVersion in registry metadata', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(true);

    // Read registry and verify Python version is stored
    const registryContent = await fs.readFile(registryPath, 'utf-8');
    const registry: MCPServersRegistry = JSON.parse(registryContent);

    expect(registry.servers).toHaveLength(1);
    const server = registry.servers[0];

    // Check top-level pythonVersion field
    expect(server.pythonVersion).toBe('3.12');

    // Check config.pythonVersion field
    expect(server.customConfig?.pythonVersion).toBe('3.12');
  });

  it('should include .python-version path in registry sourceFiles', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(true);

    // Read registry and verify .python-version path is stored
    const registryContent = await fs.readFile(registryPath, 'utf-8');
    const registry: MCPServersRegistry = JSON.parse(registryContent);

    const server = registry.servers[0];
    expect(server.customConfig?.sourceFiles?.pythonVersion).toBe(
      path.join(config.workingDir, '.python-version')
    );
  });

  it('should create .python-version file before uv init', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');
    const { uvInit } = await import('../uv-utils');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    await generateAndRegisterServer(config, registryPath, mockEvent);

    // Verify uvInit was called with serverName and workingDir (which happens after file creation)
    expect(uvInit).toHaveBeenCalledWith(config.serverName, config.workingDir);

    // Verify .python-version file exists
    const pythonVersionPath = path.join(config.workingDir, '.python-version');
    const fileExists = await fs.access(pythonVersionPath).then(() => true).catch(() => false);
    expect(fileExists).toBe(true);
  });

  it('should generate different versions for multiple servers', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    // Create first server with Python 3.10
    const config1: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'server-310',
      description: 'Server with 3.10',
      pythonVersion: '3.10',
      workingDir: path.join(testDir, 'server-310'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result1 = await generateAndRegisterServer(config1, registryPath, mockEvent);
    expect(result1.success).toBe(true);

    // Create second server with Python 3.13
    const config2: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'server-313',
      description: 'Server with 3.13',
      pythonVersion: '3.13',
      workingDir: path.join(testDir, 'server-313'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result2 = await generateAndRegisterServer(config2, registryPath, mockEvent);
    expect(result2.success).toBe(true);

    // Verify both .python-version files have correct versions
    const version1 = await fs.readFile(path.join(config1.workingDir, '.python-version'), 'utf-8');
    expect(version1).toBe('3.10');

    const version2 = await fs.readFile(path.join(config2.workingDir, '.python-version'), 'utf-8');
    expect(version2).toBe('3.13');

    // Verify registry has both servers with correct versions
    const registryContent = await fs.readFile(registryPath, 'utf-8');
    const registry: MCPServersRegistry = JSON.parse(registryContent);

    expect(registry.servers).toHaveLength(2);
    expect(registry.servers[0].pythonVersion).toBe('3.10');
    expect(registry.servers[1].pythonVersion).toBe('3.13');
  });

  it('should not create .python-version with trailing newline or whitespace', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    await generateAndRegisterServer(config, registryPath, mockEvent);

    const pythonVersionPath = path.join(config.workingDir, '.python-version');
    const content = await fs.readFile(pythonVersionPath, 'utf-8');

    // Should be exact version with no extra whitespace
    expect(content).toBe('3.12');
    expect(content).not.toMatch(/\n$/);
    expect(content).not.toMatch(/\s$/);
  });
});
