/**
 * Server Configuration Validation
 *
 * Validates FastMCP server configuration before generation to catch errors early.
 *
 * @module server-validator
 */

import type { FastMCPServerConfig } from '../shared/types/mcp';
import * as path from 'path';

/**
 * Custom error class for validation errors
 */
export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

/**
 * Python reserved keywords that cannot be used as identifiers
 */
const PYTHON_KEYWORDS = new Set([
  'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
  'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
  'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
  'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
  'try', 'while', 'with', 'yield'
]);

/**
 * Validate server name
 * @param name - Server name to validate
 * @throws ValidationError if invalid
 */
export function validateServerName(name: string): void {
  if (!name || name.trim().length === 0) {
    throw new ValidationError('Server name cannot be empty');
  }

  if (name.length > 50) {
    throw new ValidationError('Server name must be 50 characters or less');
  }

  if (name.includes(' ')) {
    throw new ValidationError('Server name cannot contain spaces');
  }

  // Allow alphanumeric, hyphens, and underscores
  if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
    throw new ValidationError('Server name can only contain letters, numbers, hyphens, and underscores');
  }
}

/**
 * Validate working directory path
 * @param dirPath - Directory path to validate
 * @throws ValidationError if invalid
 */
export function validateWorkingDirectory(dirPath: string): void {
  if (!dirPath || dirPath.trim().length === 0) {
    throw new ValidationError('Working directory cannot be empty');
  }

  // Check for null bytes
  if (dirPath.includes('\0')) {
    throw new ValidationError('Working directory contains invalid characters');
  }

  // Must be absolute path
  if (!path.isAbsolute(dirPath)) {
    throw new ValidationError('Working directory must be an absolute path');
  }
}

/**
 * Validate Python identifier (tool name, parameter name)
 * @param name - Identifier to validate
 * @throws ValidationError if invalid
 */
export function validateToolName(name: string): void {
  if (!name || name.trim().length === 0) {
    throw new ValidationError('Tool name cannot be empty');
  }

  // Python identifier rules: start with letter or underscore, followed by letters, digits, or underscores
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name)) {
    throw new ValidationError(
      `Invalid tool name "${name}". Must start with letter or underscore and contain only letters, digits, and underscores`
    );
  }

  // Check for Python keywords
  if (PYTHON_KEYWORDS.has(name)) {
    throw new ValidationError(`Tool name "${name}" is a Python reserved keyword`);
  }
}

/**
 * Validate dependency specifications
 * @param dependencies - Array of dependency specs
 * @throws ValidationError if invalid
 */
export function validateDependencies(dependencies: string[]): void {
  // Must include fastmcp
  const hasFastMCP = dependencies.some(dep => dep.startsWith('fastmcp'));
  if (!hasFastMCP) {
    throw new ValidationError('Dependencies must include fastmcp');
  }

  // Validate each dependency format
  for (const dep of dependencies) {
    // Basic format: package-name[operator]version
    // Examples: fastmcp>=0.1.0, requests==2.0.0
    const depPattern = /^[a-zA-Z0-9_-]+([<>=!]+[0-9.]+)?$/;

    if (!depPattern.test(dep)) {
      throw new ValidationError(`Invalid dependency specification: "${dep}"`);
    }

    // Check for double operators (>==, etc.)
    if (/[<>=!]{3,}/.test(dep)) {
      throw new ValidationError(`Malformed version specifier in: "${dep}"`);
    }
  }
}

/**
 * Validate complete server configuration
 * @param config - Server configuration to validate
 * @throws ValidationError if invalid
 */
export function validateServerConfig(config: FastMCPServerConfig): void {
  // Validate server name
  validateServerName(config.serverName);

  // Validate description
  if (!config.description || config.description.trim().length === 0) {
    throw new ValidationError('Server description cannot be empty');
  }

  // Validate working directory
  validateWorkingDirectory(config.workingDir);

  // Validate Python version
  const validVersions = ['3.10', '3.11', '3.12', '3.13'];
  if (!validVersions.includes(config.pythonVersion)) {
    throw new ValidationError(
      `Invalid Python version "${config.pythonVersion}". Must be one of: ${validVersions.join(', ')}`
    );
  }

  // Validate tools
  const toolNames = new Set<string>();
  for (const tool of config.tools) {
    validateToolName(tool.name);

    // Check for duplicates
    if (toolNames.has(tool.name)) {
      throw new ValidationError(`Duplicate tool name: "${tool.name}"`);
    }
    toolNames.add(tool.name);

    // Validate parameters
    for (const param of tool.parameters) {
      validateToolName(param.name);
    }
  }

  // Validate dependencies
  validateDependencies(config.dependencies);
}
