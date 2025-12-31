/**
 * Langfuse Web SDK Integration
 *
 * Provides user feedback capabilities for the Auto-Claude frontend.
 * Uses the Langfuse Web SDK for browser-side feedback collection.
 */

import { LangfuseWeb } from 'langfuse';

// Singleton instance
let langfuseWeb: LangfuseWeb | null = null;

/**
 * Initialize Langfuse Web SDK with public key only.
 * Safe to use in browser - only public key is exposed.
 */
export function initLangfuseWeb(publicKey: string, host?: string): void {
  if (langfuseWeb) {
    console.debug('[LangfuseWeb] Already initialized');
    return;
  }

  try {
    langfuseWeb = new LangfuseWeb({
      publicKey,
      baseUrl: host || 'http://localhost:3001',
    });
    console.info('[LangfuseWeb] Initialized successfully');
  } catch (error) {
    console.error('[LangfuseWeb] Failed to initialize:', error);
    langfuseWeb = null;
  }
}

/**
 * Check if Langfuse Web is initialized and ready.
 */
export function isLangfuseWebReady(): boolean {
  return langfuseWeb !== null;
}

/**
 * Submit user feedback for a trace.
 *
 * @param traceId - The Langfuse trace ID to score
 * @param value - Numeric score (1 = thumbs up, 0 = thumbs down)
 * @param comment - Optional user comment
 */
export async function submitUserFeedback(
  traceId: string,
  value: number,
  comment?: string
): Promise<boolean> {
  if (!langfuseWeb) {
    console.warn('[LangfuseWeb] Not initialized, cannot submit feedback');
    return false;
  }

  try {
    await langfuseWeb.score({
      traceId,
      name: 'user_satisfaction',
      value,
      comment,
    });
    console.debug(`[LangfuseWeb] Submitted feedback for trace ${traceId}: ${value}`);
    return true;
  } catch (error) {
    console.error('[LangfuseWeb] Failed to submit feedback:', error);
    return false;
  }
}

/**
 * Submit thumbs up feedback.
 */
export async function submitThumbsUp(traceId: string, comment?: string): Promise<boolean> {
  return submitUserFeedback(traceId, 1, comment || 'User approved');
}

/**
 * Submit thumbs down feedback.
 */
export async function submitThumbsDown(traceId: string, comment?: string): Promise<boolean> {
  return submitUserFeedback(traceId, 0, comment || 'User rejected');
}

/**
 * Submit detailed feedback with multiple aspects.
 */
export async function submitDetailedFeedback(
  traceId: string,
  feedback: {
    overall: number; // 1-5 rating
    codeQuality?: number; // 1-5 rating
    speed?: number; // 1-5 rating
    accuracy?: number; // 1-5 rating
    comment?: string;
  }
): Promise<boolean> {
  if (!langfuseWeb) {
    console.warn('[LangfuseWeb] Not initialized');
    return false;
  }

  try {
    // Submit overall score
    await langfuseWeb.score({
      traceId,
      name: 'user_rating_overall',
      value: feedback.overall,
      comment: feedback.comment,
    });

    // Submit aspect scores if provided
    if (feedback.codeQuality !== undefined) {
      await langfuseWeb.score({
        traceId,
        name: 'user_rating_code_quality',
        value: feedback.codeQuality,
      });
    }

    if (feedback.speed !== undefined) {
      await langfuseWeb.score({
        traceId,
        name: 'user_rating_speed',
        value: feedback.speed,
      });
    }

    if (feedback.accuracy !== undefined) {
      await langfuseWeb.score({
        traceId,
        name: 'user_rating_accuracy',
        value: feedback.accuracy,
      });
    }

    return true;
  } catch (error) {
    console.error('[LangfuseWeb] Failed to submit detailed feedback:', error);
    return false;
  }
}

/**
 * Cleanup Langfuse Web instance.
 */
export function cleanupLangfuseWeb(): void {
  langfuseWeb = null;
  console.debug('[LangfuseWeb] Cleaned up');
}
