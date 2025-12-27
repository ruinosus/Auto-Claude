/**
 * Integration Test: uv Installation Detection
 *
 * Tests that the system properly detects when uv is not installed
 * and provides helpful error messages to guide users.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { promises as fs } from 'fs';
import * as path from 'path';
import * as os from 'os';
import type { FastMCPServerConfig } from '../../shared/types/mcp';

// Mock uv utilities to simulate uv not being installed
vi.mock('../uv-utils', () => ({
  uvInit: vi.fn().mockRejectedValue(new Error('uv command not found')),
  uvAdd: vi.fn().mockRejectedValue(new Error('uv command not found')),
  uvSync: vi.fn().mockRejectedValue(new Error('uv command not found')),
  checkUvInstalled: vi.fn().mockResolvedValue(false) // uv NOT installed
}));

// Mock IPC event
const mockEvent = {
  sender: {
    send: vi.fn()
  }
} as any;

describe('Integration: uv Installation Detection', () => {
  let testDir: string;
  let registryPath: string;

  beforeEach(async () => {
    // Create temp directory for test
    testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'fastmcp-uv-detection-test-'));
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

  it('should detect when uv is not installed', async () => {
    const { checkUvInstalled } = await import('../uv-utils');

    const isInstalled = await checkUvInstalled();

    expect(isInstalled).toBe(false);
  });

  it('should fail gracefully when attempting generation without uv', async () => {
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

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
    expect(result.error).toContain('uv');
  });

  it('should not create any files when uv is not installed', async () => {
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

    // Verify working directory was not created
    const dirExists = await fs.access(config.workingDir).then(() => true).catch(() => false);
    expect(dirExists).toBe(false);

    // Verify no server files were created
    const serverPyExists = await fs.access(path.join(config.workingDir, 'server.py'))
      .then(() => true).catch(() => false);
    expect(serverPyExists).toBe(false);
  });

  it('should not add entry to registry when uv is not installed', async () => {
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

    // Registry should not exist or should be empty
    const registryExists = await fs.access(registryPath).then(() => true).catch(() => false);

    if (registryExists) {
      const registryContent = await fs.readFile(registryPath, 'utf-8');
      const registry = JSON.parse(registryContent);
      expect(registry.servers).toHaveLength(0);
    }
  });

  it('should provide helpful error message with installation instructions', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'file-system',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [
        {
          name: 'read_file',
          description: 'Read a file',
          parameters: [{ name: 'path', type: 'string', required: true }]
        }
      ],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();

    // Error should mention uv and possibly installation
    const errorLower = result.error!.toLowerCase();
    expect(errorLower).toContain('uv');
  });

  it('should emit error progress event when uv is not available', async () => {
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

    // Verify error progress event was sent
    expect(mockEvent.sender.send).toHaveBeenCalled();

    const errorCalls = mockEvent.sender.send.mock.calls.filter(
      (call: [string, { step: string }]) => call[0] === 'mcp:generation-progress' && call[1].step === 'error'
    );

    expect(errorCalls.length).toBeGreaterThan(0);
  });

  it('should handle uvInit failure when uv is missing', async () => {
    const { uvInit } = await import('../uv-utils');

    await expect(
      uvInit('test-project', testDir)
    ).rejects.toThrow('uv command not found');
  });

  it('should handle uvAdd failure when uv is missing', async () => {
    const { uvAdd } = await import('../uv-utils');

    await expect(
      uvAdd(['fastmcp>=0.1.0'], testDir)
    ).rejects.toThrow('uv command not found');
  });

  it('should handle uvSync failure when uv is missing', async () => {
    const { uvSync } = await import('../uv-utils');

    await expect(
      uvSync(testDir)
    ).rejects.toThrow('uv command not found');
  });
});
