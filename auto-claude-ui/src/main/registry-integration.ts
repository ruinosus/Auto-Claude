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
import { generateServerPy, generatePyprojectToml, generateReadmeMd, generatePythonVersion } from './fastmcp-generator';
import { ensureDirectory, writeAllServerFiles } from './fs-utils';
import { uvInit, uvAdd, uvSync } from './uv-utils';

/**
 * Result of generation and registration
 */
export interface GenerationResult {
  success: boolean;
  serverId?: string;
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
function createRegistryEntry(config: FastMCPServerConfig, serverId: string): MCPServer {
  return {
    id: serverId,
    name: config.serverName,
    description: config.description,
    type: 'custom',
    category: 'FastMCP',
    status: 'disabled',
    enabled: true,

    // Required fields
    requiredEnvVars: [],
    optionalEnvVars: [],
    capabilities: {
      tools: config.tools.map(tool => ({
        name: tool.name,
        displayName: tool.name,
        description: tool.description,
        parameters: tool.parameters.map(param => ({
          name: param.name,
          type: param.type,
          required: param.required,
          description: param.description || '',
          default: param.default
        }))
      }))
    },
    toolCount: config.tools.length,
    promptCount: 0,
    resourceCount: 0,
    connectionType: 'stdio',

    // Python version
    pythonVersion: config.pythonVersion,

    // Custom configuration
    config: {
      command: 'uv',
      args: ['run', 'server.py'],
      env: {
        PYTHONPATH: config.workingDir
      },
      cwd: config.workingDir,

      // FastMCP-specific metadata
      isFastMCP: true,
      generatedFrom: 'wizard',
      template: config.templateId,
      pythonVersion: config.pythonVersion,
      sourceFiles: {
        pyprojectToml: path.join(config.workingDir, 'pyproject.toml'),
        serverPy: path.join(config.workingDir, 'server.py'),
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
    // Generate file contents
    const files = [
      { filename: 'server.py', content: generateServerPy(config) },
      { filename: 'pyproject.toml', content: generatePyprojectToml(config) },
      { filename: 'README.md', content: generateReadmeMd(config) },
      { filename: '.python-version', content: generatePythonVersion(config.pythonVersion) }
    ];

    // Step 1: Create directory
    reporter.reportStep(GenerationStep.CREATING_DIRECTORY, { path: config.workingDir });
    await ensureDirectory(config.workingDir);

    // Step 2: Write files
    reporter.reportStep(GenerationStep.WRITING_FILES, { fileCount: files.length });
    await writeAllServerFiles(config.workingDir, files);

    // Step 3: Initialize uv project
    reporter.reportStep(GenerationStep.UV_INIT, { serverName: config.serverName });
    await uvInit(config.serverName, config.workingDir);

    // Step 4: Add dependencies
    if (config.dependencies && config.dependencies.length > 0) {
      reporter.reportStep(GenerationStep.UV_ADD, {
        dependencies: config.dependencies,
        count: config.dependencies.length
      });
      await uvAdd(config.dependencies, config.workingDir);
    }

    // Step 5: Sync dependencies
    reporter.reportStep(GenerationStep.UV_SYNC);
    await uvSync(config.workingDir);

    // Step 6: Add to registry
    const registryEntry = createRegistryEntry(config, serverId);
    originalRegistry.servers.push(registryEntry);
    await writeRegistry(registryPath, originalRegistry);

    // Step 7: Complete
    reporter.reportStep(GenerationStep.COMPLETE, { serverId });

    return {
      success: true,
      serverId
    };
  } catch (error) {
    // Rollback registry on failure
    try {
      await writeRegistry(registryPath, registryBackup);
    } catch (rollbackError) {
      // Log rollback failure but don't mask original error
      console.error('Failed to rollback registry:', rollbackError);
    }

    // Report error
    const errorMessage = (error as Error).message;
    reporter.reportError(GenerationStep.COMPLETE, error as Error);

    return {
      success: false,
      error: errorMessage
    };
  }
}
