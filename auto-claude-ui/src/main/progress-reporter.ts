/**
 * Progress Reporting for FastMCP Server Generation
 *
 * Provides real-time progress updates during server generation via IPC events.
 *
 * @module progress-reporter
 */

import type { IpcMainInvokeEvent } from 'electron';

/**
 * Generation steps for progress tracking
 */
export enum GenerationStep {
  CREATING_DIRECTORY = 'creating-directory',
  WRITING_FILES = 'writing-files',
  UV_INIT = 'uv-init',
  UV_ADD = 'uv-add',
  UV_SYNC = 'uv-sync',
  COMPLETE = 'complete'
}

/**
 * Progress event data sent to renderer
 */
export interface GenerationProgress {
  step: GenerationStep;
  message: string;
  progress: number; // 0-100
  metadata?: Record<string, unknown>;
  error?: string;
}

/**
 * Maps generation steps to progress percentage
 */
const STEP_PROGRESS: Record<GenerationStep, number> = {
  [GenerationStep.CREATING_DIRECTORY]: 16.67,
  [GenerationStep.WRITING_FILES]: 33.33,
  [GenerationStep.UV_INIT]: 50,
  [GenerationStep.UV_ADD]: 66.67,
  [GenerationStep.UV_SYNC]: 83.33,
  [GenerationStep.COMPLETE]: 100
};

/**
 * Human-readable messages for each step
 */
const STEP_MESSAGES: Record<GenerationStep, string> = {
  [GenerationStep.CREATING_DIRECTORY]: 'Creating directory...',
  [GenerationStep.WRITING_FILES]: 'Writing server files...',
  [GenerationStep.UV_INIT]: 'Initializing uv project...',
  [GenerationStep.UV_ADD]: 'Adding dependencies...',
  [GenerationStep.UV_SYNC]: 'Syncing dependencies...',
  [GenerationStep.COMPLETE]: 'Generation complete!'
};

/**
 * Progress reporter for FastMCP generation
 *
 * Sends real-time progress updates to the renderer process during
 * server generation.
 */
export class ProgressReporter {
  private event: IpcMainInvokeEvent;

  constructor(event: IpcMainInvokeEvent) {
    this.event = event;
  }

  /**
   * Report progress for a generation step
   * @param step - Current generation step
   * @param metadata - Optional additional data
   */
  reportStep(step: GenerationStep, metadata?: Record<string, unknown>): void {
    const progress: GenerationProgress = {
      step,
      message: STEP_MESSAGES[step],
      progress: STEP_PROGRESS[step],
      ...(metadata && { metadata })
    };

    this.event.sender.send('mcp:generation-progress', progress);
  }

  /**
   * Report an error during generation
   * @param step - Step where error occurred
   * @param error - Error that occurred
   */
  reportError(step: GenerationStep, error: Error): void {
    const progress: GenerationProgress = {
      step,
      message: STEP_MESSAGES[step],
      progress: STEP_PROGRESS[step],
      error: error.message
    };

    this.event.sender.send('mcp:generation-progress', progress);
  }
}
