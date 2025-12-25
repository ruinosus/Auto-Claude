/**
 * uv Command Execution Utilities
 *
 * Provides utilities for executing uv (Astral's Python package manager) commands
 * in the Electron main process. All functions use child_process.spawn for reliable
 * command execution with proper error handling.
 *
 * @module uv-utils
 */

import { spawn, exec } from 'child_process';
import { promisify } from 'util';

/**
 * Result of executing a uv command
 */
export interface UvExecutionResult {
  stdout: string;
  stderr: string;
  exitCode: number | null;
}

/**
 * Options for executing uv commands
 */
export interface UvExecutionOptions {
  cwd?: string;
  env?: Record<string, string>;
}

/**
 * Check if uv is installed on the system
 * @returns Promise that resolves to true if uv is installed, false otherwise
 */
export async function checkUvInstalled(): Promise<boolean> {
  try {
    const execAsync = promisify(exec);
    await execAsync('uv --version');
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * Execute a uv command with the given arguments
 * @param args - Command arguments to pass to uv
 * @param options - Execution options (cwd, env)
 * @returns Promise that resolves to execution result
 */
export async function executeUv(
  args: string[],
  options?: UvExecutionOptions
): Promise<UvExecutionResult> {
  return new Promise((resolve, reject) => {
    const spawnOptions = {
      cwd: options?.cwd || process.cwd(),
      env: { ...process.env, ...options?.env }
    };

    const child = spawn('uv', args, spawnOptions);

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (data: Buffer) => {
      stdout += data.toString();
    });

    child.stderr.on('data', (data: Buffer) => {
      stderr += data.toString();
    });

    child.on('close', (exitCode: number | null) => {
      resolve({
        stdout,
        stderr,
        exitCode: exitCode ?? 1 // Treat null as error (exit code 1)
      });
    });

    child.on('error', (error: Error) => {
      reject(error);
    });
  });
}

/**
 * Initialize a new uv project
 * @param name - Project name
 * @param directory - Directory to initialize in
 * @throws Error if uv init fails
 */
export async function uvInit(name: string, directory: string): Promise<void> {
  const result = await executeUv(['init', '--name', name], { cwd: directory });

  if (result.exitCode !== 0) {
    throw new Error(`uv init failed: ${result.stderr}`);
  }
}

/**
 * Add packages to a uv project
 * @param packages - Package names to add
 * @param directory - Project directory
 * @throws Error if uv add fails
 */
export async function uvAdd(packages: string[], directory: string): Promise<void> {
  const result = await executeUv(['add', ...packages], { cwd: directory });

  if (result.exitCode !== 0) {
    throw new Error(`uv add failed: ${result.stderr}`);
  }
}

/**
 * Sync dependencies in a uv project
 * @param directory - Project directory
 * @throws Error if uv sync fails
 */
export async function uvSync(directory: string): Promise<void> {
  const result = await executeUv(['sync'], { cwd: directory });

  if (result.exitCode !== 0) {
    throw new Error(`uv sync failed: ${result.stderr}`);
  }
}
