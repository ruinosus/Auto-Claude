/**
 * Analytics Service - Polls analytics.db and sends data to renderer via IPC
 *
 * This service runs in the main process (Node.js) where better-sqlite3 is available.
 * It polls the SQLite database every 2 seconds and broadcasts updates to the renderer.
 */

import Database from 'better-sqlite3';
import type { BrowserWindow } from 'electron';
import { existsSync } from 'fs';

// Types matching the analytics store
interface ConversationRow {
  id: number;
  spec_id: string;
  session_number: number;
  phase: string;
  started_at: string;
  ended_at: string | null;
  total_cost_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  model: string | null;
}

interface TokenUsage {
  input: number;
  output: number;
}

interface ConversationAnalytics {
  specId: string;
  conversationId: string;
  cost: number;
  tokens: TokenUsage;
  timestamp: Date;
  phase: string;
  model: string;
  durationSeconds: number | null;
}

interface ChartDataPoint {
  timestamp: Date;
  value: number;
  label?: string;
}

interface SessionDurationData {
  phase: string;
  avg_duration_seconds: number;
}

// Feature usage types
interface FeatureUsageData {
  featureType: string;
  totalSessions: number;
  totalCost: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  lastUsed: Date | null;
}

interface FeatureSessionRow {
  id: number;
  project_id: string;
  feature_type: string;
  started_at: string;
  ended_at: string | null;
  total_cost_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  model: string | null;
  metadata: string | null;
}

interface ModelDistributionData {
  model: string;
  count: number;
  percentage: number;
}

interface ChartData {
  costOverTime: ChartDataPoint[];
  tokensOverTime: ChartDataPoint[];
  sessionActivity: ChartDataPoint[];
  sessionDuration: SessionDurationData[];
  modelDistribution: ModelDistributionData[];
  featureCostDistribution: ChartDataPoint[]; // Cost by feature type
}

interface AnalyticsData {
  totalCost: number;
  totalTokens: TokenUsage;
  activeSessions: number;
  budgetRemaining: number;
  conversations: ConversationAnalytics[];
  chartData: ChartData;
  // Feature usage data
  featureUsage: FeatureUsageData[];
  featureTotalCost: number;
  featureTotalTokens: TokenUsage;
}

// Error recovery configuration
const MAX_CONSECUTIVE_ERRORS = 5;
const BASE_RETRY_DELAY_MS = 2000;
const MAX_RETRY_DELAY_MS = 30000;

export class AnalyticsService {
  private dbPath: string | null = null;
  private pollingInterval: NodeJS.Timeout | null = null;
  private getMainWindow: () => BrowserWindow | null;
  private isPolling = false;
  private consecutiveErrors = 0;
  private currentPollingDelay = BASE_RETRY_DELAY_MS;

  constructor(getMainWindow: () => BrowserWindow | null) {
    // Store the getter function, not the window itself
    // The window may not exist yet at construction time
    this.getMainWindow = getMainWindow;
  }

  /**
   * Reset error tracking after successful fetch
   */
  private resetErrorTracking(): void {
    if (this.consecutiveErrors > 0) {
      console.log('[analytics-service] Recovered after', this.consecutiveErrors, 'consecutive errors');
    }
    this.consecutiveErrors = 0;
    this.currentPollingDelay = BASE_RETRY_DELAY_MS;
  }

  /**
   * Handle fetch error with exponential backoff
   */
  private handleError(error: unknown): void {
    this.consecutiveErrors++;

    // Calculate exponential backoff delay
    const backoffMultiplier = Math.pow(2, Math.min(this.consecutiveErrors - 1, 4));
    this.currentPollingDelay = Math.min(
      BASE_RETRY_DELAY_MS * backoffMultiplier,
      MAX_RETRY_DELAY_MS
    );

    console.error(
      `[analytics-service] Fetch error (${this.consecutiveErrors}/${MAX_CONSECUTIVE_ERRORS}):`,
      error,
      `Next retry in ${this.currentPollingDelay}ms`
    );

    // Emit error event to renderer for visibility
    const mainWindow = this.getMainWindow();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('analytics:error', {
        message: error instanceof Error ? error.message : String(error),
        consecutiveErrors: this.consecutiveErrors,
        willRetry: this.consecutiveErrors < MAX_CONSECUTIVE_ERRORS,
        retryDelayMs: this.currentPollingDelay
      });
    }

    // Stop polling if too many consecutive errors
    if (this.consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
      console.error('[analytics-service] Too many consecutive errors, stopping polling');
      this.stopPolling();

      // Notify renderer that polling stopped due to errors
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('analytics:stopped', {
          reason: 'max_errors_exceeded',
          message: `Polling stopped after ${MAX_CONSECUTIVE_ERRORS} consecutive errors`
        });
      }
    } else {
      // Restart polling with new delay
      this.restartPollingWithDelay();
    }
  }

  /**
   * Restart polling with current delay (for error recovery)
   */
  private restartPollingWithDelay(): void {
    if (!this.dbPath) return;

    // Clear existing interval
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }

    // Set new interval with backoff delay
    this.pollingInterval = setInterval(() => {
      this.fetchAndBroadcast();
    }, this.currentPollingDelay);
  }

  /**
   * Start polling the analytics database
   */
  startPolling(dbPath: string): void {
    if (this.isPolling && this.dbPath === dbPath) {
      console.log('[analytics-service] Already polling this database');
      return;
    }

    // Stop any existing polling
    this.stopPolling();

    this.dbPath = dbPath;
    this.isPolling = true;

    console.log('[analytics-service] Starting polling:', dbPath);

    // Initial fetch
    this.fetchAndBroadcast();

    // Poll every 2 seconds
    this.pollingInterval = setInterval(() => {
      this.fetchAndBroadcast();
    }, 2000);
  }

  /**
   * Stop polling the database
   */
  stopPolling(): void {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
    this.isPolling = false;
    this.dbPath = null;
    console.log('[analytics-service] Stopped polling');
  }

  /**
   * Fetch data from database and broadcast to renderer
   */
  private fetchAndBroadcast(): void {
    if (!this.dbPath || !existsSync(this.dbPath)) {
      console.warn('[analytics-service] Database not found:', this.dbPath);
      return;
    }

    try {
      const data = this.fetchAnalyticsData(this.dbPath);

      // Reset error tracking on successful fetch
      this.resetErrorTracking();

      // Broadcast to renderer - get window fresh each time
      const mainWindow = this.getMainWindow();
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('analytics:data-update', data);
      } else {
        console.warn('[analytics-service] No main window available to send data');
      }
    } catch (error) {
      this.handleError(error);
    }
  }

  /**
   * Fetch analytics data from SQLite database (same logic as useAnalyticsData hook)
   */
  private fetchAnalyticsData(dbPath: string): AnalyticsData {
    const db = new Database(dbPath, { readonly: true });

    try {
      // Get all conversations
      const conversationsRows = db.prepare(`
        SELECT * FROM conversations
        ORDER BY started_at DESC
        LIMIT 100
      `).all() as ConversationRow[];

      // Get totals
      const totals = db.prepare(`
        SELECT
          COALESCE(SUM(total_cost_usd), 0) as totalCost,
          COALESCE(SUM(total_input_tokens), 0) as input_tokens,
          COALESCE(SUM(total_output_tokens), 0) as output_tokens
        FROM conversations
      `).get() as {
        totalCost: number;
        input_tokens: number;
        output_tokens: number;
      };

      // Get active sessions count
      const activeSessions = db.prepare(`
        SELECT COUNT(*) as count
        FROM conversations
        WHERE ended_at IS NULL
      `).get() as { count: number };

      // Get cost over time (last 7 days)
      const costOverTime = db.prepare(`
        SELECT
          DATE(started_at) as timestamp,
          SUM(total_cost_usd) as value
        FROM conversations
        WHERE started_at >= datetime('now', '-7 days')
        GROUP BY DATE(started_at)
        ORDER BY started_at ASC
      `).all() as Array<{
        timestamp: string;
        value: number;
      }>;

      // Get tokens over time (last 7 days)
      const tokensOverTime = db.prepare(`
        SELECT
          DATE(started_at) as timestamp,
          SUM(total_input_tokens + total_output_tokens) as value
        FROM conversations
        WHERE started_at >= datetime('now', '-7 days')
        GROUP BY DATE(started_at)
        ORDER BY started_at ASC
      `).all() as Array<{
        timestamp: string;
        value: number;
      }>;

      // Get session activity (last 7 days)
      const sessionActivity = db.prepare(`
        SELECT
          DATE(started_at) as timestamp,
          COUNT(*) as value,
          phase as label
        FROM conversations
        WHERE started_at >= datetime('now', '-7 days')
        GROUP BY DATE(started_at), phase
        ORDER BY started_at ASC
      `).all() as Array<{
        timestamp: string;
        value: number;
        label: string;
      }>;

      // Get average session duration by phase (last 7 days)
      const sessionDuration = db.prepare(`
        SELECT
          phase,
          AVG(
            CASE
              WHEN ended_at IS NOT NULL
              THEN (julianday(ended_at) - julianday(started_at)) * 86400
              ELSE NULL
            END
          ) as avg_duration_seconds
        FROM conversations
        WHERE started_at >= datetime('now', '-7 days')
          AND ended_at IS NOT NULL
        GROUP BY phase
        ORDER BY avg_duration_seconds DESC
      `).all() as Array<{
        phase: string;
        avg_duration_seconds: number | null;
      }>;

      // Get model distribution (last 7 days)
      const modelDistributionRows = db.prepare(`
        SELECT
          COALESCE(model, 'unknown') as model,
          COUNT(*) as count
        FROM conversations
        WHERE started_at >= datetime('now', '-7 days')
        GROUP BY model
        ORDER BY count DESC
      `).all() as Array<{
        model: string;
        count: number;
      }>;

      // Calculate percentages for model distribution
      const totalConversations = modelDistributionRows.reduce((sum, row) => sum + row.count, 0);
      const modelDistribution = modelDistributionRows.map(row => ({
        model: row.model,
        count: row.count,
        percentage: totalConversations > 0 ? (row.count / totalConversations) * 100 : 0
      }));

      // ========== FEATURE USAGE DATA ==========

      // Check if feature_sessions table exists
      const tableExists = db.prepare(`
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='feature_sessions'
      `).get() as { name: string } | undefined;

      let featureUsage: FeatureUsageData[] = [];
      let featureTotalCost = 0;
      let featureTotalInputTokens = 0;
      let featureTotalOutputTokens = 0;
      let featureCostDistribution: ChartDataPoint[] = [];

      if (tableExists) {
        // Get feature usage aggregated by type
        const featureUsageRows = db.prepare(`
          SELECT
            feature_type,
            COUNT(*) as total_sessions,
            COALESCE(SUM(total_cost_usd), 0) as total_cost,
            COALESCE(SUM(total_input_tokens), 0) as total_input_tokens,
            COALESCE(SUM(total_output_tokens), 0) as total_output_tokens,
            MAX(started_at) as last_used
          FROM feature_sessions
          GROUP BY feature_type
          ORDER BY total_cost DESC
        `).all() as Array<{
          feature_type: string;
          total_sessions: number;
          total_cost: number;
          total_input_tokens: number;
          total_output_tokens: number;
          last_used: string | null;
        }>;

        featureUsage = featureUsageRows.map(row => ({
          featureType: row.feature_type,
          totalSessions: row.total_sessions,
          totalCost: row.total_cost,
          totalInputTokens: row.total_input_tokens,
          totalOutputTokens: row.total_output_tokens,
          lastUsed: row.last_used ? new Date(row.last_used) : null,
        }));

        // Get feature totals
        const featureTotals = db.prepare(`
          SELECT
            COALESCE(SUM(total_cost_usd), 0) as total_cost,
            COALESCE(SUM(total_input_tokens), 0) as total_input_tokens,
            COALESCE(SUM(total_output_tokens), 0) as total_output_tokens
          FROM feature_sessions
        `).get() as {
          total_cost: number;
          total_input_tokens: number;
          total_output_tokens: number;
        };

        featureTotalCost = featureTotals.total_cost;
        featureTotalInputTokens = featureTotals.total_input_tokens;
        featureTotalOutputTokens = featureTotals.total_output_tokens;

        // Create cost distribution chart data
        featureCostDistribution = featureUsageRows.map(row => ({
          timestamp: new Date(), // Not really a timestamp, using for chart compatibility
          value: row.total_cost,
          label: row.feature_type,
        }));
      }

      // Transform conversations to ConversationAnalytics
      const conversations: ConversationAnalytics[] = conversationsRows.map((row) => {
        // Calculate duration in seconds if ended_at exists
        let durationSeconds: number | null = null;
        if (row.ended_at) {
          const startTime = new Date(row.started_at).getTime();
          const endTime = new Date(row.ended_at).getTime();
          durationSeconds = Math.round((endTime - startTime) / 1000);
        }

        return {
          specId: row.spec_id,
          conversationId: row.id.toString(),
          cost: row.total_cost_usd,
          tokens: {
            input: row.total_input_tokens,
            output: row.total_output_tokens,
          },
          timestamp: new Date(row.started_at),
          phase: row.phase,
          model: row.model || 'unknown',
          durationSeconds,
        };
      });

      // Build analytics data matching store interface
      // Combine spec costs with feature costs for total
      const combinedTotalCost = totals.totalCost + featureTotalCost;
      const combinedTotalInputTokens = totals.input_tokens + featureTotalInputTokens;
      const combinedTotalOutputTokens = totals.output_tokens + featureTotalOutputTokens;

      const analyticsData: AnalyticsData = {
        totalCost: combinedTotalCost,
        totalTokens: {
          input: combinedTotalInputTokens,
          output: combinedTotalOutputTokens,
        },
        activeSessions: activeSessions.count,
        budgetRemaining: 0, // Will be calculated from budgets in store
        conversations,
        chartData: {
          costOverTime: costOverTime.map((row) => ({
            timestamp: new Date(row.timestamp),
            value: row.value,
          })),
          tokensOverTime: tokensOverTime.map((row) => ({
            timestamp: new Date(row.timestamp),
            value: row.value,
          })),
          sessionActivity: sessionActivity.map((row) => ({
            timestamp: new Date(row.timestamp),
            value: row.value,
            label: row.label,
          })),
          sessionDuration: sessionDuration
            .filter(row => row.avg_duration_seconds !== null)
            .map(row => ({
              phase: row.phase,
              avg_duration_seconds: Math.round(row.avg_duration_seconds || 0),
            })),
          modelDistribution,
          featureCostDistribution,
        },
        // Feature usage data
        featureUsage,
        featureTotalCost,
        featureTotalTokens: {
          input: featureTotalInputTokens,
          output: featureTotalOutputTokens,
        },
      };

      return analyticsData;
    } finally {
      db.close();
    }
  }

  /**
   * Check if currently polling
   */
  getPollingStatus(): { isPolling: boolean; dbPath: string | null } {
    return {
      isPolling: this.isPolling,
      dbPath: this.dbPath,
    };
  }
}
