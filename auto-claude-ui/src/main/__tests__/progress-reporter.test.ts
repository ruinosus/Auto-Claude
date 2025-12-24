/**
 * Tests for FastMCP generation progress reporting
 */

import { describe, it, expect, vi } from 'vitest';
import { ProgressReporter, GenerationStep } from '../progress-reporter';
import type { IpcMainInvokeEvent } from 'electron';

describe('ProgressReporter', () => {
  it('should create reporter with event sender', () => {
    const mockEvent = {
      sender: {
        send: vi.fn()
      }
    } as unknown as IpcMainInvokeEvent;

    const reporter = new ProgressReporter(mockEvent);
    expect(reporter).toBeDefined();
  });

  it('should report progress for each generation step', () => {
    const mockSend = vi.fn();
    const mockEvent = {
      sender: {
        send: mockSend
      }
    } as unknown as IpcMainInvokeEvent;

    const reporter = new ProgressReporter(mockEvent);

    reporter.reportStep(GenerationStep.CREATING_DIRECTORY, { path: '/tmp/test-server' });

    expect(mockSend).toHaveBeenCalledWith(
      'mcp:generation-progress',
      expect.objectContaining({
        step: GenerationStep.CREATING_DIRECTORY,
        message: expect.stringContaining('Creating directory'),
        progress: expect.any(Number),
        metadata: { path: '/tmp/test-server' }
      })
    );
  });

  it('should track progress percentage across steps', () => {
    const mockSend = vi.fn();
    const mockEvent = {
      sender: {
        send: mockSend
      }
    } as unknown as IpcMainInvokeEvent;

    const reporter = new ProgressReporter(mockEvent);

    // Total steps: 6 (directory, files, uv-init, uv-add, uv-sync, complete)
    reporter.reportStep(GenerationStep.CREATING_DIRECTORY);
    expect(mockSend).toHaveBeenCalledWith(
      'mcp:generation-progress',
      expect.objectContaining({ progress: expect.closeTo(16.67, 1) })
    );

    reporter.reportStep(GenerationStep.WRITING_FILES);
    expect(mockSend).toHaveBeenCalledWith(
      'mcp:generation-progress',
      expect.objectContaining({ progress: expect.closeTo(33.33, 1) })
    );

    reporter.reportStep(GenerationStep.UV_INIT);
    expect(mockSend).toHaveBeenCalledWith(
      'mcp:generation-progress',
      expect.objectContaining({ progress: 50 })
    );
  });

  it('should handle completion step at 100%', () => {
    const mockSend = vi.fn();
    const mockEvent = {
      sender: {
        send: mockSend
      }
    } as unknown as IpcMainInvokeEvent;

    const reporter = new ProgressReporter(mockEvent);

    reporter.reportStep(GenerationStep.COMPLETE, { serverPath: '/tmp/test-server' });

    expect(mockSend).toHaveBeenCalledWith(
      'mcp:generation-progress',
      expect.objectContaining({
        step: GenerationStep.COMPLETE,
        progress: 100,
        message: expect.stringContaining('complete')
      })
    );
  });

  it('should handle error reporting', () => {
    const mockSend = vi.fn();
    const mockEvent = {
      sender: {
        send: mockSend
      }
    } as unknown as IpcMainInvokeEvent;

    const reporter = new ProgressReporter(mockEvent);

    reporter.reportError(GenerationStep.UV_SYNC, new Error('Dependency resolution failed'));

    expect(mockSend).toHaveBeenCalledWith(
      'mcp:generation-progress',
      expect.objectContaining({
        step: GenerationStep.UV_SYNC,
        error: 'Dependency resolution failed',
        progress: expect.any(Number)
      })
    );
  });

  it('should generate appropriate messages for each step', () => {
    const mockSend = vi.fn();
    const mockEvent = {
      sender: {
        send: mockSend
      }
    } as unknown as IpcMainInvokeEvent;

    const reporter = new ProgressReporter(mockEvent);

    const steps = [
      { step: GenerationStep.CREATING_DIRECTORY, expected: 'Creating directory' },
      { step: GenerationStep.WRITING_FILES, expected: 'Writing server files' },
      { step: GenerationStep.UV_INIT, expected: 'Initializing uv project' },
      { step: GenerationStep.UV_ADD, expected: 'Adding dependencies' },
      { step: GenerationStep.UV_SYNC, expected: 'Syncing dependencies' },
      { step: GenerationStep.COMPLETE, expected: 'Generation complete' }
    ];

    steps.forEach(({ step, expected }) => {
      reporter.reportStep(step);
      expect(mockSend).toHaveBeenCalledWith(
        'mcp:generation-progress',
        expect.objectContaining({
          message: expect.stringContaining(expected)
        })
      );
    });
  });

  it('should include metadata when provided', () => {
    const mockSend = vi.fn();
    const mockEvent = {
      sender: {
        send: mockSend
      }
    } as unknown as IpcMainInvokeEvent;

    const reporter = new ProgressReporter(mockEvent);

    const metadata = {
      dependencies: ['fastmcp>=0.1.0', 'httpx>=0.25.0'],
      count: 2
    };

    reporter.reportStep(GenerationStep.UV_ADD, metadata);

    expect(mockSend).toHaveBeenCalledWith(
      'mcp:generation-progress',
      expect.objectContaining({
        metadata
      })
    );
  });
});
