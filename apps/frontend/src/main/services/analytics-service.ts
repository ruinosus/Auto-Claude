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
}

interface ChartDataPoint {
  timestamp: Date;
  value: number;
  label?: string;
}

interface ChartData {
  costOverTime: ChartDataPoint[];
  tokensOverTime: ChartDataPoint[];
  sessionActivity: ChartDataPoint[];
}

interface AnalyticsData {
  totalCost: number;
  totalTokens: TokenUsage;
  activeSessions: number;
  budgetRemaining: number;
  conversations: ConversationAnalytics[];
  chartData: ChartData;
}

export class AnalyticsService {
  private dbPath: string | null = null;
  private pollingInterval: NodeJS.Timeout | null = null;
  private mainWindow: BrowserWindow | null = null;
  private isPolling = false;

  constructor(getMainWindow: () => BrowserWindow | null) {
    this.mainWindow = getMainWindow();
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

      // Broadcast to renderer
      if (this.mainWindow && !this.mainWindow.isDestroyed()) {
        this.mainWindow.webContents.send('analytics:data-update', data);
      }
    } catch (error) {
      console.error('[analytics-service] Failed to fetch analytics data:', error);
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

      // Transform conversations to ConversationAnalytics
      const conversations: ConversationAnalytics[] = conversationsRows.map((row) => ({
        specId: row.spec_id,
        conversationId: row.id.toString(),
        cost: row.total_cost_usd,
        tokens: {
          input: row.total_input_tokens,
          output: row.total_output_tokens,
        },
        timestamp: new Date(row.started_at),
        phase: row.phase,
      }));

      // Build analytics data matching store interface
      const analyticsData: AnalyticsData = {
        totalCost: totals.totalCost,
        totalTokens: {
          input: totals.input_tokens,
          output: totals.output_tokens,
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
