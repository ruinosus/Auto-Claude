import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock child_process module before any imports
vi.mock('child_process', async () => {
  return {
    default: {},
    exec: vi.fn(),
    spawn: vi.fn()
  };
});

// Now import the module under test
import {
  checkUvInstalled,
  executeUv,
  uvInit,
  uvAdd,
  uvSync
} from '../uv-utils';

describe('uv-utils', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('checkUvInstalled', () => {
    it('should return true when uv --version executes successfully', async () => {
      const cp = await import('child_process');
      vi.mocked(cp.exec).mockImplementation(((command: string, callback: any) => {
        callback(null, { stdout: 'uv 0.1.0\n', stderr: '' });
        return {} as any;
      }) as any);

      const result = await checkUvInstalled();

      expect(result).toBe(true);
    });

    it('should return false when uv command is not found', async () => {
      const cp = await import('child_process');
      vi.mocked(cp.exec).mockImplementation(((command: string, callback: any) => {
        callback(new Error('command not found'));
        return {} as any;
      }) as any);

      const result = await checkUvInstalled();

      expect(result).toBe(false);
    });
  });

  describe('executeUv', () => {
    it('should execute uv command and return stdout/stderr/exitCode', async () => {
      const cp = await import('child_process');
      const mockProcess = {
        stdout: {
          on: vi.fn((event, handler) => {
            if (event === 'data') handler(Buffer.from('success output\n'));
          })
        },
        stderr: {
          on: vi.fn((event, handler) => {
            if (event === 'data') handler(Buffer.from(''));
          })
        },
        on: vi.fn((event, handler) => {
          if (event === 'close') handler(0);
        })
      };

      vi.mocked(cp.spawn).mockReturnValue(mockProcess as any);

      const result = await executeUv(['--version']);

      expect(result.stdout).toBe('success output\n');
      expect(result.stderr).toBe('');
      expect(result.exitCode).toBe(0);
    });

    it('should capture stderr when command fails', async () => {
      const cp = await import('child_process');
      const mockProcess = {
        stdout: {
          on: vi.fn((event, handler) => {
            if (event === 'data') handler(Buffer.from(''));
          })
        },
        stderr: {
          on: vi.fn((event, handler) => {
            if (event === 'data') handler(Buffer.from('error: command failed\n'));
          })
        },
        on: vi.fn((event, handler) => {
          if (event === 'close') handler(1);
        })
      };

      vi.mocked(cp.spawn).mockReturnValue(mockProcess as any);

      const result = await executeUv(['invalid-command']);

      expect(result.stderr).toBe('error: command failed\n');
      expect(result.exitCode).toBe(1);
    });

    it('should pass custom cwd option to spawn', async () => {
      const cp = await import('child_process');
      const mockProcess = {
        stdout: { on: vi.fn() },
        stderr: { on: vi.fn() },
        on: vi.fn((event, handler) => {
          if (event === 'close') handler(0);
        })
      };

      vi.mocked(cp.spawn).mockReturnValue(mockProcess as any);

      await executeUv(['init'], { cwd: '/custom/path' });

      expect(cp.spawn).toHaveBeenCalledWith(
        'uv',
        ['init'],
        expect.objectContaining({ cwd: '/custom/path' })
      );
    });
  });

  describe('uvInit', () => {
    it('should execute uv init with --name flag', async () => {
      const cp = await import('child_process');
      const mockProcess = {
        stdout: { on: vi.fn() },
        stderr: { on: vi.fn() },
        on: vi.fn((event, handler) => {
          if (event === 'close') handler(0);
        })
      };

      vi.mocked(cp.spawn).mockReturnValue(mockProcess as any);

      await uvInit('my-project', '/test/dir');

      expect(cp.spawn).toHaveBeenCalledWith(
        'uv',
        ['init', '--name', 'my-project'],
        expect.objectContaining({ cwd: '/test/dir' })
      );
    });

    it('should throw error when uv init fails', async () => {
      const cp = await import('child_process');
      const mockProcess = {
        stdout: { on: vi.fn() },
        stderr: {
          on: vi.fn((event, handler) => {
            if (event === 'data') handler(Buffer.from('init failed\n'));
          })
        },
        on: vi.fn((event, handler) => {
          if (event === 'close') handler(1);
        })
      };

      vi.mocked(cp.spawn).mockReturnValue(mockProcess as any);

      await expect(uvInit('my-project', '/test/dir')).rejects.toThrow('uv init failed');
    });
  });

  describe('uvAdd', () => {
    it('should execute uv add with multiple packages', async () => {
      const cp = await import('child_process');
      const mockProcess = {
        stdout: { on: vi.fn() },
        stderr: { on: vi.fn() },
        on: vi.fn((event, handler) => {
          if (event === 'close') handler(0);
        })
      };

      vi.mocked(cp.spawn).mockReturnValue(mockProcess as any);

      await uvAdd(['package1', 'package2'], '/test/dir');

      expect(cp.spawn).toHaveBeenCalledWith(
        'uv',
        ['add', 'package1', 'package2'],
        expect.objectContaining({ cwd: '/test/dir' })
      );
    });

    it('should throw error when uv add fails', async () => {
      const cp = await import('child_process');
      const mockProcess = {
        stdout: { on: vi.fn() },
        stderr: {
          on: vi.fn((event, handler) => {
            if (event === 'data') handler(Buffer.from('package not found\n'));
          })
        },
        on: vi.fn((event, handler) => {
          if (event === 'close') handler(1);
        })
      };

      vi.mocked(cp.spawn).mockReturnValue(mockProcess as any);

      await expect(uvAdd(['invalid-package'], '/test/dir')).rejects.toThrow('uv add failed');
    });
  });

  describe('uvSync', () => {
    it('should execute uv sync', async () => {
      const cp = await import('child_process');
      const mockProcess = {
        stdout: { on: vi.fn() },
        stderr: { on: vi.fn() },
        on: vi.fn((event, handler) => {
          if (event === 'close') handler(0);
        })
      };

      vi.mocked(cp.spawn).mockReturnValue(mockProcess as any);

      await uvSync('/test/dir');

      expect(cp.spawn).toHaveBeenCalledWith(
        'uv',
        ['sync'],
        expect.objectContaining({ cwd: '/test/dir' })
      );
    });

    it('should throw error when uv sync fails', async () => {
      const cp = await import('child_process');
      const mockProcess = {
        stdout: { on: vi.fn() },
        stderr: {
          on: vi.fn((event, handler) => {
            if (event === 'data') handler(Buffer.from('sync failed\n'));
          })
        },
        on: vi.fn((event, handler) => {
          if (event === 'close') handler(1);
        })
      };

      vi.mocked(cp.spawn).mockReturnValue(mockProcess as any);

      await expect(uvSync('/test/dir')).rejects.toThrow('uv sync failed');
    });
  });
});
