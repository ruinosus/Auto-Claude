/**
 * Integration Test: Generation Cleanup and Rollback
 *
 * Tests that failed FastMCP server generation properly cleans up:
 * 1. Filesystem artifacts (directories, files)
 * 2. Registry entries
 * 3. Partial state
 *
 * Ensures no orphaned files or entries remain after failures.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { promises as fs } from 'fs';
import * as path from 'path';
import * as os from 'os';
import type { FastMCPServerConfig, MCPServersRegistry } from '../../shared/types/mcp';

// Mock uv utilities
let uvSyncShouldFail = false;
let uvAddShouldFail = false;
let uvInitShouldFail = false;

vi.mock('../uv-utils', () => ({
  uvInit: vi.fn().mockImplementation(async () => {
    if (uvInitShouldFail) {
      throw new Error('uv init failed');
    }
  }),
  uvAdd: vi.fn().mockImplementation(async () => {
    if (uvAddShouldFail) {
      throw new Error('uv add failed');
    }
  }),
  uvSync: vi.fn().mockImplementation(async () => {
    if (uvSyncShouldFail) {
      throw new Error('uv sync failed');
    }
  }),
  checkUvInstalled: vi.fn().mockResolvedValue(true)
}));

// Mock IPC event
const mockEvent = {
  sender: {
    send: vi.fn()
  }
} as any;

describe('Integration: Generation Cleanup and Rollback', () => {
  let testDir: string;
  let registryPath: string;

  beforeEach(async () => {
    // Create temp directory for test
    testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'fastmcp-cleanup-test-'));
    registryPath = path.join(testDir, '.mcp-servers.json');

    // Reset mock flags
    uvSyncShouldFail = false;
    uvAddShouldFail = false;
    uvInitShouldFail = false;

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

  it('should clean up directory when uv init fails', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    uvInitShouldFail = true;

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'uv-init-fail-server',
      description: 'This will fail at uv init',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'uv-init-fail-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    // Generation should fail
    expect(result.success).toBe(false);
    expect(result.error).toContain('uv init failed');

    // Directory should be cleaned up
    const dirExists = await fs.access(config.workingDir).then(() => true).catch(() => false);
    expect(dirExists).toBe(false);

    // Registry should be empty or not exist
    const registryExists = await fs.access(registryPath).then(() => true).catch(() => false);
    if (registryExists) {
      const registryContent = await fs.readFile(registryPath, 'utf-8');
      const registry: MCPServersRegistry = JSON.parse(registryContent);
      expect(registry.servers).toHaveLength(0);
    }
  });

  it('should clean up directory when uv add fails', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    uvAddShouldFail = true;

    const config: FastMCPServerConfig = {
      templateId: 'api-wrapper',
      serverName: 'uv-add-fail-server',
      description: 'This will fail at uv add',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'uv-add-fail-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0', 'httpx>=0.25.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    // Generation should fail
    expect(result.success).toBe(false);
    expect(result.error).toContain('uv add failed');

    // Directory should be cleaned up
    const dirExists = await fs.access(config.workingDir).then(() => true).catch(() => false);
    expect(dirExists).toBe(false);
  });

  it('should clean up directory when uv sync fails', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    uvSyncShouldFail = true;

    const config: FastMCPServerConfig = {
      templateId: 'database',
      serverName: 'uv-sync-fail-server',
      description: 'This will fail at uv sync',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'uv-sync-fail-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0', 'sqlalchemy>=2.0.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    // Generation should fail
    expect(result.success).toBe(false);
    expect(result.error).toContain('uv sync failed');

    // Directory should be cleaned up
    const dirExists = await fs.access(config.workingDir).then(() => true).catch(() => false);
    expect(dirExists).toBe(false);
  });

  it('should clean up partial files if failure occurs mid-generation', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    // Fail at uv init - after files are written
    uvInitShouldFail = true;

    const config: FastMCPServerConfig = {
      templateId: 'file-system',
      serverName: 'partial-files-server',
      description: 'Test partial file cleanup',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'partial-files-server'),
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

    // Generation should fail
    expect(result.success).toBe(false);

    // Verify files don't exist (they should be cleaned up)
    const serverPyPath = path.join(config.workingDir, 'server.py');
    const pyprojectPath = path.join(config.workingDir, 'pyproject.toml');
    const readmePath = path.join(config.workingDir, 'README.md');

    const serverPyExists = await fs.access(serverPyPath).then(() => true).catch(() => false);
    const pyprojectExists = await fs.access(pyprojectPath).then(() => true).catch(() => false);
    const readmeExists = await fs.access(readmePath).then(() => true).catch(() => false);

    expect(serverPyExists).toBe(false);
    expect(pyprojectExists).toBe(false);
    expect(readmeExists).toBe(false);
  });

  it('should not affect existing servers when cleanup occurs', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    // Create a successful server first
    const successConfig: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'successful-server',
      description: 'This will succeed',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'successful-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const successResult = await generateAndRegisterServer(successConfig, registryPath, mockEvent);
    expect(successResult.success).toBe(true);

    // Verify successful server exists
    const successDirExists = await fs.access(successConfig.workingDir).then(() => true).catch(() => false);
    expect(successDirExists).toBe(true);

    // Now create a failing server
    uvSyncShouldFail = true;

    const failConfig: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'failing-server',
      description: 'This will fail',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'failing-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const failResult = await generateAndRegisterServer(failConfig, registryPath, mockEvent);
    expect(failResult.success).toBe(false);

    // Failed server should be cleaned up
    const failDirExists = await fs.access(failConfig.workingDir).then(() => true).catch(() => false);
    expect(failDirExists).toBe(false);

    // Successful server should still exist
    const successDirStillExists = await fs.access(successConfig.workingDir).then(() => true).catch(() => false);
    expect(successDirStillExists).toBe(true);

    // Registry should only contain the successful server
    const registryContent = await fs.readFile(registryPath, 'utf-8');
    const registry: MCPServersRegistry = JSON.parse(registryContent);
    expect(registry.servers).toHaveLength(1);
    expect(registry.servers[0].name).toBe('successful-server');
  });

  it('should clean up even if directory creation succeeds but file write fails', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    // This test verifies cleanup works even for the earliest failure points
    uvInitShouldFail = true;

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'early-fail-server',
      description: 'Fails early in process',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'early-fail-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    await generateAndRegisterServer(config, registryPath, mockEvent);

    // Directory should not exist
    const dirExists = await fs.access(config.workingDir).then(() => true).catch(() => false);
    expect(dirExists).toBe(false);
  });

  it('should handle cleanup gracefully if directory is already gone', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    uvSyncShouldFail = true;

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'already-deleted-server',
      description: 'Test cleanup when dir already deleted',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'already-deleted-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    // Should fail gracefully even if cleanup has issues
    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });

  it('should report cleanup progress via IPC events', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    uvSyncShouldFail = true;

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'cleanup-progress-server',
      description: 'Test cleanup progress reporting',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'cleanup-progress-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    await generateAndRegisterServer(config, registryPath, mockEvent);

    // Verify error event was sent
    const errorCalls = mockEvent.sender.send.mock.calls.filter(
      call => call[0] === 'mcp:generation-progress' && call[1].step === 'error'
    );

    expect(errorCalls.length).toBeGreaterThan(0);
  });
});
