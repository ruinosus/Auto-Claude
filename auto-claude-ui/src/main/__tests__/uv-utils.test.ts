/**
 * Integration tests for uv command execution utilities
 *
 * Note: These are integration tests, not unit tests with mocks.
 * Reason: Vitest cannot mock Node.js built-in ESM exports (child_process.spawn, child_process.exec)
 * due to ESM module namespace immutability. See: https://vitest.dev/guide/browser/#limitations
 *
 * These tests require uv to be installed on the system. They will be skipped if uv is not available.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { exec } from 'child_process';
import { promisify } from 'util';
import {
  checkUvInstalled,
  executeUv,
  uvInit,
  uvAdd,
  uvSync
} from '../uv-utils';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';

const execAsync = promisify(exec);

describe('uv-utils (integration tests)', () => {
  let uvAvailable = false;
  let testDir: string;

  beforeAll(async () => {
    // Check if uv is available
    uvAvailable = await checkUvInstalled();

    // Create a temporary directory for tests
    testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'uv-test-'));
  });

  describe('checkUvInstalled', () => {
    it('should return boolean indicating uv availability', async () => {
      const result = await checkUvInstalled();
      expect(typeof result).toBe('boolean');
    });
  });

  describe('executeUv', () => {
    it.skipIf(!uvAvailable)('should execute uv --version and return output', async () => {
      const result = await executeUv(['--version']);

      expect(result.exitCode).toBe(0);
      expect(result.stdout).toContain('uv');
      expect(typeof result.stderr).toBe('string');
    });

    it.skipIf(!uvAvailable)('should handle invalid command gracefully', async () => {
      const result = await executeUv(['--invalid-flag-that-does-not-exist']);

      expect(result.exitCode).not.toBe(0);
      expect(result.stderr.length).toBeGreaterThan(0);
    });

    it.skipIf(!uvAvailable)('should pass custom cwd option', async () => {
      const result = await executeUv(['--version'], { cwd: testDir });

      expect(result.exitCode).toBe(0);
    });
  });

  describe('uvInit', () => {
    it.skipIf(!uvAvailable)('should initialize a uv project', async () => {
      const projectDir = path.join(testDir, 'test-project-init');
      await fs.mkdir(projectDir, { recursive: true });

      await uvInit('test-project', projectDir);

      // Verify pyproject.toml was created
      const files = await fs.readdir(projectDir);
      expect(files).toContain('pyproject.toml');

      // Cleanup
      await fs.rm(projectDir, { recursive: true, force: true });
    });

    it.skipIf(!uvAvailable)('should throw error for invalid directory', async () => {
      const invalidDir = '/nonexistent/directory/that/should/not/exist';

      await expect(uvInit('test-project', invalidDir)).rejects.toThrow();
    });
  });

  describe('uvAdd', () => {
    it.skipIf(!uvAvailable)('should add packages to a uv project', async () => {
      const projectDir = path.join(testDir, 'test-project-add');
      await fs.mkdir(projectDir, { recursive: true });

      // First initialize the project
      await uvInit('test-project', projectDir);

      // Then add a package
      await uvAdd(['requests'], projectDir);

      // Verify pyproject.toml contains the package
      const pyprojectContent = await fs.readFile(
        path.join(projectDir, 'pyproject.toml'),
        'utf-8'
      );
      expect(pyprojectContent).toContain('requests');

      // Cleanup
      await fs.rm(projectDir, { recursive: true, force: true });
    });

    it.skipIf(!uvAvailable)('should throw error for invalid package', async () => {
      const projectDir = path.join(testDir, 'test-project-invalid-pkg');
      await fs.mkdir(projectDir, { recursive: true });

      // Initialize project first
      await uvInit('test-project', projectDir);

      // Try to add an invalid package
      await expect(
        uvAdd(['this-package-definitely-does-not-exist-12345'], projectDir)
      ).rejects.toThrow();

      // Cleanup
      await fs.rm(projectDir, { recursive: true, force: true });
    });
  });

  describe('uvSync', () => {
    it.skipIf(!uvAvailable)('should sync dependencies in a uv project', async () => {
      const projectDir = path.join(testDir, 'test-project-sync');
      await fs.mkdir(projectDir, { recursive: true });

      // Initialize project
      await uvInit('test-project', projectDir);

      // Sync should work on empty project
      await uvSync(projectDir);

      // Add a dependency and sync again
      await uvAdd(['requests'], projectDir);
      await uvSync(projectDir);

      // Cleanup
      await fs.rm(projectDir, { recursive: true, force: true });
    });

    it.skipIf(!uvAvailable)('should throw error for non-project directory', async () => {
      const emptyDir = path.join(testDir, 'empty-dir');
      await fs.mkdir(emptyDir, { recursive: true });

      await expect(uvSync(emptyDir)).rejects.toThrow();

      // Cleanup
      await fs.rm(emptyDir, { recursive: true, force: true });
    });
  });
});
