/**
 * Registry Integration for FastMCP Server Generation
 *
 * Handles adding generated FastMCP servers to the MCP servers registry.
 * Provides transactional semantics - if generation fails, registry is rolled back.
 *
 * @module registry-integration
 */

import { promises as fs } from 'fs';
import * as path from 'path';
import { randomUUID } from 'crypto';
import type { IpcMainInvokeEvent } from 'electron';
import type { FastMCPServerConfig, MCPServersRegistry, MCPServer } from '../shared/types/mcp';
import { ProgressReporter, GenerationStep } from './progress-reporter';
import { generateServerPy, generatePyprojectToml, generateReadmeMd, generatePythonVersion, generateCompleteShowcaseFiles } from './fastmcp-generator';
import { ensureDirectory, writeAllServerFiles, cleanupDirectory } from './fs-utils';
import { uvAdd, uvSync, checkUvInstalled } from './uv-utils';
import { validateServerConfig } from './server-validator';

/**
 * Result of generation and registration
 */
export interface GenerationResult {
  success: boolean;
  serverId?: string;
  serverPath?: string;
  error?: string;
}

/**
 * Read MCP servers registry from file
 * @param registryPath - Path to registry file
 * @returns Registry object, or empty registry if file doesn't exist
 */
async function readRegistry(registryPath: string): Promise<MCPServersRegistry> {
  try {
    const content = await fs.readFile(registryPath, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    // If file doesn't exist, return empty registry
    return {
      version: '1.0',
      servers: [],
      updatedAt: new Date().toISOString()
    };
  }
}

/**
 * Write MCP servers registry to file
 * @param registryPath - Path to registry file
 * @param registry - Registry object to write
 */
async function writeRegistry(registryPath: string, registry: MCPServersRegistry): Promise<void> {
  // Ensure directory exists
  const registryDir = path.dirname(registryPath);
  await ensureDirectory(registryDir);

  // Update timestamp
  registry.updatedAt = new Date().toISOString();

  // Write with pretty formatting
  await fs.writeFile(registryPath, JSON.stringify(registry, null, 2), 'utf-8');
}

/**
 * Create registry entry for a FastMCP server
 * @param config - Server configuration
 * @param serverId - Unique server ID
 * @returns MCPServer registry entry
 */
function createRegistryEntry(config: FastMCPServerConfig, serverId: string): any {
  // Extract package name from serverName (convert to snake_case for Python package name)
  // Replace spaces and hyphens with underscores, then remove remaining invalid chars
  const packageName = config.serverName.toLowerCase().replace(/[\s-]+/g, '_').replace(/[^a-z0-9_]/g, '');

  // Complete showcase template has additional capabilities
  const isCompleteShowcase = config.templateId === 'complete-showcase';

  // Create MCPServerConfig-compatible entry
  return {
    id: serverId,
    name: config.serverName,
    description: config.description,
    type: 'custom',  // ← CRITICAL: Type field required for isServerEnabled

    // Status
    enabled: true,

    // Initial capability counts from wizard config
    // (Real capabilities loaded dynamically when server connects via SDK)
    toolCount: config.tools.length,
    promptCount: 0,  // Will be loaded from server when connected
    resourceCount: 0,  // Will be loaded from server when connected

    // Metadata
    category: 'Custom',
    icon: 'Package',

    // Connection configuration
    connectionType: 'stdio',

    // Custom server configuration
    customConfig: {
      connectionType: 'stdio',
      command: 'uv',
      args: ['run', packageName],  // Use package name, not server.py
      workingDir: config.workingDir,
      env: {
        PYTHONPATH: config.workingDir
      },
      isFastMCP: true,
      generatedFrom: 'wizard',
      template: config.templateId,
      pythonVersion: config.pythonVersion,
      sourceFiles: {
        pyprojectToml: path.join(config.workingDir, 'pyproject.toml'),
        serverPy: path.join(config.workingDir, isCompleteShowcase ? `src/${packageName}/server.py` : 'server.py'),
        readmeMd: path.join(config.workingDir, 'README.md'),
        pythonVersion: path.join(config.workingDir, '.python-version')
      }
    }
  };
}

/**
 * Generate FastMCP server and register it in the MCP servers registry
 *
 * This function provides transactional semantics:
 * 1. Generate server files
 * 2. Run uv commands to set up Python environment
 * 3. Add to registry
 * 4. If any step fails, rollback registry changes
 *
 * @param config - Server configuration
 * @param registryPath - Path to MCP servers registry file
 * @param event - IPC event for progress reporting
 * @returns Generation result with success status and server ID
 */
export async function generateAndRegisterServer(
  config: FastMCPServerConfig,
  registryPath: string,
  event: IpcMainInvokeEvent
): Promise<GenerationResult> {
  const reporter = new ProgressReporter(event);
  const serverId = randomUUID();

  // Validate configuration BEFORE any file system or registry operations
  try {
    validateServerConfig(config);
  } catch (error) {
    reporter.reportError(GenerationStep.ERROR, error as Error);
    return {
      success: false,
      error: (error as Error).message
    };
  }

  // Check if uv is installed BEFORE any file system operations
  const uvInstalled = await checkUvInstalled();
  if (!uvInstalled) {
    const error = new Error('uv is not installed. Please install uv to generate FastMCP servers. Visit https://github.com/astral-sh/uv for installation instructions.');
    reporter.reportError(GenerationStep.ERROR, error);
    return {
      success: false,
      error: error.message
    };
  }

  // Read current registry
  let originalRegistry: MCPServersRegistry;
  try {
    originalRegistry = await readRegistry(registryPath);
  } catch (error) {
    return {
      success: false,
      error: `Failed to read registry: ${(error as Error).message}`
    };
  }

  // Save original state for rollback
  const registryBackup = JSON.parse(JSON.stringify(originalRegistry));

  try {
    // Generate file contents based on template type
    let files;
    if (config.templateId === 'complete-showcase') {
      // Use modular structure for complete-showcase template
      files = generateCompleteShowcaseFiles(config);
    } else {
      // Use standard single-file structure for other templates
      files = [
        { filename: 'server.py', content: generateServerPy(config) },
        { filename: 'pyproject.toml', content: generatePyprojectToml(config) },
        { filename: 'README.md', content: generateReadmeMd(config) },
        { filename: '.python-version', content: generatePythonVersion(config.pythonVersion) }
      ];
    }

    // Step 1: Create directory
    reporter.reportStep(GenerationStep.CREATING_DIRECTORY, { path: config.workingDir });
    await ensureDirectory(config.workingDir);

    // Step 2: Write files (including pyproject.toml)
    reporter.reportStep(GenerationStep.WRITING_FILES, { fileCount: files.length });
    await writeAllServerFiles(config.workingDir, files);

    // Step 3: Add dependencies (no need for uv init - we already have pyproject.toml)
    if (config.dependencies && config.dependencies.length > 0) {
      reporter.reportStep(GenerationStep.UV_ADD, {
        dependencies: config.dependencies,
        count: config.dependencies.length
      });
      await uvAdd(config.dependencies, config.workingDir);
    }

    // Step 4: Sync dependencies
    reporter.reportStep(GenerationStep.UV_SYNC);
    await uvSync(config.workingDir);

    // Step 5: Add to registry
    const registryEntry = createRegistryEntry(config, serverId);
    originalRegistry.servers.push(registryEntry);
    await writeRegistry(registryPath, originalRegistry);

    // Step 6: Complete
    reporter.reportStep(GenerationStep.COMPLETE, { serverId });

    return {
      success: true,
      serverId
    };
  } catch (error) {
    // Rollback: Clean up filesystem and registry
    try {
      // 1. Clean up generated directory
      await cleanupDirectory(config.workingDir);
    } catch (cleanupError) {
      // Log cleanup failure but don't mask original error
      console.error('Failed to cleanup directory:', cleanupError);
    }

    try {
      // 2. Rollback registry changes
      await writeRegistry(registryPath, registryBackup);
    } catch (rollbackError) {
      // Log rollback failure but don't mask original error
      console.error('Failed to rollback registry:', rollbackError);
    }

    // Report error
    const errorMessage = (error as Error).message;
    reporter.reportError(GenerationStep.ERROR, error as Error);

    return {
      success: false,
      error: errorMessage
    };
  }
}
