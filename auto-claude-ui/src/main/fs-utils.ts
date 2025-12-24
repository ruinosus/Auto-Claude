/**
 * File System Utilities for Server Generation
 *
 * Provides utilities for creating directories and writing files during
 * FastMCP server generation process.
 *
 * @module fs-utils
 */

import * as fs from 'fs/promises';
import * as path from 'path';

/**
 * Represents a file to be written to disk
 */
export interface ServerFile {
  filename: string;
  content: string;
}

/**
 * Check if a directory exists
 * @param dirPath - Path to check
 * @returns Promise that resolves to true if directory exists, false otherwise
 */
export async function directoryExists(dirPath: string): Promise<boolean> {
  try {
    const stats = await fs.stat(dirPath);
    return stats.isDirectory();
  } catch (error) {
    return false;
  }
}

/**
 * Ensure a directory exists, creating it if necessary
 * @param dirPath - Path to directory
 * @throws Error if directory cannot be created
 */
export async function ensureDirectory(dirPath: string): Promise<void> {
  try {
    await fs.mkdir(dirPath, { recursive: true });
  } catch (error) {
    throw new Error(`Failed to create directory ${dirPath}: ${(error as Error).message}`);
  }
}

/**
 * Write a single server file to disk
 * @param serverDir - Directory to write file to
 * @param file - File to write
 * @throws Error if file cannot be written
 */
export async function writeServerFile(serverDir: string, file: ServerFile): Promise<void> {
  const filePath = path.join(serverDir, file.filename);

  try {
    await fs.writeFile(filePath, file.content, 'utf-8');
  } catch (error) {
    throw new Error(
      `Failed to write file ${file.filename}: ${(error as Error).message}`
    );
  }
}

/**
 * Write multiple server files to disk
 * @param serverDir - Directory to write files to
 * @param files - Array of files to write
 * @throws Error if any file cannot be written
 */
export async function writeAllServerFiles(
  serverDir: string,
  files: ServerFile[]
): Promise<void> {
  try {
    // Write all files sequentially to ensure atomic-like behavior
    for (const file of files) {
      await writeServerFile(serverDir, file);
    }
  } catch (error) {
    throw error; // Re-throw to maintain error context
  }
}
