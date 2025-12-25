/**
 * Integration Test: Validation in Server Generation Flow
 *
 * Tests that validation is properly integrated into the generation flow,
 * catching invalid configurations before any file system operations occur.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { promises as fs } from 'fs';
import * as path from 'path';
import * as os from 'os';
import type { FastMCPServerConfig } from '../../shared/types/mcp';

// Mock uv utilities before importing
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

describe('Integration: Validation in Generation Flow', () => {
  let testDir: string;
  let registryPath: string;

  beforeEach(async () => {
    // Create temp directory for test
    testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'fastmcp-validation-test-'));
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

  it('should reject empty server name before creating any files', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: '',  // Invalid: empty
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toContain('Server name cannot be empty');

    // Verify no files were created
    const dirExists = await fs.access(config.workingDir).then(() => true).catch(() => false);
    expect(dirExists).toBe(false);

    // Verify no registry entry was created
    const registryExists = await fs.access(registryPath).then(() => true).catch(() => false);
    expect(registryExists).toBe(false);
  });

  it('should reject server name with spaces', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'my server',  // Invalid: contains spaces
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toContain('cannot contain spaces');
  });

  it('should reject server name that is too long', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'a'.repeat(51),  // Invalid: > 50 characters
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toContain('50 characters or less');
  });

  it('should reject relative working directory path', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: './relative/path',  // Invalid: not absolute
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toContain('absolute path');
  });

  it('should reject tool name that is a Python keyword', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'file-system',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [
        {
          name: 'class',  // Invalid: Python keyword
          description: 'Bad tool name',
          parameters: []
        }
      ],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toContain('Python reserved keyword');
  });

  it('should reject tool name with invalid characters', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'file-system',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [
        {
          name: 'read-file',  // Invalid: contains hyphen (not valid in Python identifiers)
          description: 'Read a file',
          parameters: []
        }
      ],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toContain('Invalid tool name');
  });

  it('should reject duplicate tool names', async () => {
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
          parameters: []
        },
        {
          name: 'read_file',  // Invalid: duplicate
          description: 'Read a file again',
          parameters: []
        }
      ],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toContain('Duplicate tool name');
  });

  it('should reject configuration without fastmcp dependency', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['httpx>=0.25.0']  // Invalid: missing fastmcp
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toContain('must include fastmcp');
  });

  it('should reject invalid Python version', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.9' as any,  // Invalid: not in allowed list
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toContain('Invalid Python version');
  });

  it('should reject malformed dependency specifications', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'test-server',
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0', 'bad!@#$package']  // Invalid: malformed
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);
    expect(result.error).toContain('Invalid dependency specification');
  });

  it('should accept valid configuration and proceed with generation', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');

    const config: FastMCPServerConfig = {
      templateId: 'file-system',
      serverName: 'valid_server',
      description: 'A valid server configuration',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'valid-server'),
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

    // Verify files were created
    const dirExists = await fs.access(config.workingDir).then(() => true).catch(() => false);
    expect(dirExists).toBe(true);

    const serverPyExists = await fs.access(path.join(config.workingDir, 'server.py'))
      .then(() => true).catch(() => false);
    expect(serverPyExists).toBe(true);
  });

  it('should validate before any file system operations', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');
    const fsUtils = await import('../fs-utils');

    // Spy on file system operations
    const ensureDirSpy = vi.spyOn(fsUtils, 'ensureDirectory');
    const writeFilesSpy = vi.spyOn(fsUtils, 'writeAllServerFiles');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: '',  // Invalid
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);

    // Verify file system operations were never called
    expect(ensureDirSpy).not.toHaveBeenCalled();
    expect(writeFilesSpy).not.toHaveBeenCalled();

    ensureDirSpy.mockRestore();
    writeFilesSpy.mockRestore();
  });

  it('should validate before uv operations', async () => {
    const { generateAndRegisterServer } = await import('../registry-integration');
    const uvUtils = await import('../uv-utils');

    // Spy on uv operations
    const uvInitSpy = vi.spyOn(uvUtils, 'uvInit');
    const uvAddSpy = vi.spyOn(uvUtils, 'uvAdd');
    const uvSyncSpy = vi.spyOn(uvUtils, 'uvSync');

    const config: FastMCPServerConfig = {
      templateId: 'blank',
      serverName: 'bad name',  // Invalid: contains space
      description: 'Test server',
      pythonVersion: '3.12',
      workingDir: path.join(testDir, 'test-server'),
      tools: [],
      dependencies: ['fastmcp>=0.1.0']
    };

    const result = await generateAndRegisterServer(config, registryPath, mockEvent);

    expect(result.success).toBe(false);

    // Verify uv operations were never called
    expect(uvInitSpy).not.toHaveBeenCalled();
    expect(uvAddSpy).not.toHaveBeenCalled();
    expect(uvSyncSpy).not.toHaveBeenCalled();

    uvInitSpy.mockRestore();
    uvAddSpy.mockRestore();
    uvSyncSpy.mockRestore();
  });
});
