/**
 * Tests for file system utilities used in server generation
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';
import {
  ensureDirectory,
  writeServerFile,
  writeAllServerFiles,
  directoryExists,
  cleanupDirectory,
  ServerFile
} from '../fs-utils';

describe('fs-utils', () => {
  let testDir: string;

  beforeEach(async () => {
    testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'fs-utils-test-'));
  });

  afterEach(async () => {
    await fs.rm(testDir, { recursive: true, force: true });
  });

  describe('directoryExists', () => {
    it('should return true for existing directory', async () => {
      const exists = await directoryExists(testDir);
      expect(exists).toBe(true);
    });

    it('should return false for non-existent directory', async () => {
      const nonExistent = path.join(testDir, 'does-not-exist');
      const exists = await directoryExists(nonExistent);
      expect(exists).toBe(false);
    });

    it('should return false for file (not directory)', async () => {
      const filePath = path.join(testDir, 'test.txt');
      await fs.writeFile(filePath, 'content');

      const exists = await directoryExists(filePath);
      expect(exists).toBe(false);
    });
  });

  describe('ensureDirectory', () => {
    it('should create directory if it does not exist', async () => {
      const newDir = path.join(testDir, 'new-directory');

      await ensureDirectory(newDir);

      const stats = await fs.stat(newDir);
      expect(stats.isDirectory()).toBe(true);
    });

    it('should not throw if directory already exists', async () => {
      const existingDir = path.join(testDir, 'existing');
      await fs.mkdir(existingDir);

      await expect(ensureDirectory(existingDir)).resolves.not.toThrow();
    });

    it('should create nested directories', async () => {
      const nestedDir = path.join(testDir, 'level1', 'level2', 'level3');

      await ensureDirectory(nestedDir);

      const stats = await fs.stat(nestedDir);
      expect(stats.isDirectory()).toBe(true);
    });

    it('should throw error for invalid path', async () => {
      const invalidPath = '\0invalid';

      await expect(ensureDirectory(invalidPath)).rejects.toThrow();
    });
  });

  describe('writeServerFile', () => {
    it('should write file with given content', async () => {
      const file: ServerFile = {
        filename: 'test.py',
        content: 'print("Hello World")'
      };

      await writeServerFile(testDir, file);

      const written = await fs.readFile(path.join(testDir, 'test.py'), 'utf-8');
      expect(written).toBe('print("Hello World")');
    });

    it('should overwrite existing file', async () => {
      const filePath = path.join(testDir, 'overwrite.txt');
      await fs.writeFile(filePath, 'old content');

      const file: ServerFile = {
        filename: 'overwrite.txt',
        content: 'new content'
      };

      await writeServerFile(testDir, file);

      const written = await fs.readFile(filePath, 'utf-8');
      expect(written).toBe('new content');
    });

    it('should throw error if directory does not exist', async () => {
      const nonExistent = path.join(testDir, 'does-not-exist');
      const file: ServerFile = {
        filename: 'test.py',
        content: 'content'
      };

      await expect(writeServerFile(nonExistent, file)).rejects.toThrow();
    });

    it('should handle special characters in filename', async () => {
      const file: ServerFile = {
        filename: 'test-file_123.py',
        content: 'content'
      };

      await writeServerFile(testDir, file);

      const exists = await fs.access(path.join(testDir, 'test-file_123.py'))
        .then(() => true)
        .catch(() => false);
      expect(exists).toBe(true);
    });
  });

  describe('writeAllServerFiles', () => {
    it('should write multiple files', async () => {
      const files: ServerFile[] = [
        { filename: 'server.py', content: 'server code' },
        { filename: 'pyproject.toml', content: 'toml content' },
        { filename: 'README.md', content: 'readme' }
      ];

      await writeAllServerFiles(testDir, files);

      const serverPy = await fs.readFile(path.join(testDir, 'server.py'), 'utf-8');
      const pyproject = await fs.readFile(path.join(testDir, 'pyproject.toml'), 'utf-8');
      const readme = await fs.readFile(path.join(testDir, 'README.md'), 'utf-8');

      expect(serverPy).toBe('server code');
      expect(pyproject).toBe('toml content');
      expect(readme).toBe('readme');
    });

    it('should handle empty file array', async () => {
      await expect(writeAllServerFiles(testDir, [])).resolves.not.toThrow();
    });

    it('should throw error if any file write fails', async () => {
      const nonExistent = path.join(testDir, 'does-not-exist');
      const files: ServerFile[] = [
        { filename: 'test.py', content: 'content' }
      ];

      await expect(writeAllServerFiles(nonExistent, files)).rejects.toThrow();
    });

    it('should write files atomically (all or nothing on error)', async () => {
      const files: ServerFile[] = [
        { filename: 'file1.py', content: 'content1' },
        { filename: 'file2.py', content: 'content2' }
      ];

      await writeAllServerFiles(testDir, files);

      const file1Exists = await fs.access(path.join(testDir, 'file1.py'))
        .then(() => true)
        .catch(() => false);
      const file2Exists = await fs.access(path.join(testDir, 'file2.py'))
        .then(() => true)
        .catch(() => false);

      expect(file1Exists).toBe(true);
      expect(file2Exists).toBe(true);
    });
  });

  describe('cleanupDirectory', () => {
    it('should remove directory and all contents', async () => {
      const dirToCleanup = path.join(testDir, 'cleanup-test');
      await fs.mkdir(dirToCleanup);
      await fs.writeFile(path.join(dirToCleanup, 'file1.txt'), 'content1');
      await fs.writeFile(path.join(dirToCleanup, 'file2.txt'), 'content2');

      await cleanupDirectory(dirToCleanup);

      const exists = await fs.access(dirToCleanup)
        .then(() => true)
        .catch(() => false);
      expect(exists).toBe(false);
    });

    it('should remove nested directories', async () => {
      const nestedDir = path.join(testDir, 'parent', 'child', 'grandchild');
      await fs.mkdir(nestedDir, { recursive: true });
      await fs.writeFile(path.join(nestedDir, 'file.txt'), 'content');

      await cleanupDirectory(path.join(testDir, 'parent'));

      const exists = await fs.access(path.join(testDir, 'parent'))
        .then(() => true)
        .catch(() => false);
      expect(exists).toBe(false);
    });

    it('should not throw if directory does not exist', async () => {
      const nonExistent = path.join(testDir, 'does-not-exist');

      await expect(cleanupDirectory(nonExistent)).resolves.not.toThrow();
    });

    it('should handle directory with many files', async () => {
      const manyFilesDir = path.join(testDir, 'many-files');
      await fs.mkdir(manyFilesDir);

      // Create 100 files
      for (let i = 0; i < 100; i++) {
        await fs.writeFile(path.join(manyFilesDir, `file${i}.txt`), `content ${i}`);
      }

      await cleanupDirectory(manyFilesDir);

      const exists = await fs.access(manyFilesDir)
        .then(() => true)
        .catch(() => false);
      expect(exists).toBe(false);
    });
  });
});
