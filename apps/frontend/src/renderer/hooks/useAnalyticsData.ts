import { useEffect, useRef } from 'react';
import Database from 'better-sqlite3';
import { setAnalyticsData, useAnalyticsStore } from '../stores/analytics-store';
import type { AnalyticsData, ConversationAnalytics } from '../stores/analytics-store';

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

/**
 * Hook to poll SQLite analytics database and update Zustand store
 *
 * @param dbPath - Path to analytics.db (from Electron IPC)
 * @param pollingInterval - Polling interval in milliseconds (default: 2000)
 */
export function useAnalyticsData(dbPath: string | null, pollingInterval = 2000) {
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!dbPath) return;

    const fetchData = () => {
      try {
        const db = new Database(dbPath, { readonly: true });

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

        db.close();

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

        setAnalyticsData(analyticsData);
      } catch (error) {
        console.error('Failed to fetch analytics data:', error);
      }
    };

    // Initial fetch
    fetchData();

    // Set up polling
    intervalRef.current = setInterval(fetchData, pollingInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [dbPath, pollingInterval]);
}
