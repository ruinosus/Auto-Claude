import { renderHook } from '@testing-library/react';
import { useAnalyticsData } from '../useAnalyticsData';
import { useAnalyticsStore } from '../../stores/analytics-store';
import Database from 'better-sqlite3';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';

describe('useAnalyticsData', () => {
  let tempDbPath: string;
  let db: Database.Database;

  beforeEach(() => {
    // Create temp SQLite database
    tempDbPath = path.join(os.tmpdir(), `analytics-test-${Date.now()}.db`);
    db = new Database(tempDbPath);

    // Initialize schema
    db.exec(`
      CREATE TABLE conversations (
        id INTEGER PRIMARY KEY,
        spec_id TEXT NOT NULL,
        session_number INTEGER,
        phase TEXT,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        total_cost_usd REAL,
        total_input_tokens INTEGER,
        total_output_tokens INTEGER,
        model TEXT
      );

      CREATE TABLE messages (
        id INTEGER PRIMARY KEY,
        conversation_id INTEGER,
        model TEXT,
        input_tokens INTEGER,
        output_tokens INTEGER,
        cache_read_tokens INTEGER,
        cache_creation_tokens INTEGER,
        cost_usd REAL,
        timestamp TEXT
      );

      CREATE TABLE spec_totals (
        spec_id TEXT PRIMARY KEY,
        total_cost_usd REAL,
        total_input_tokens INTEGER,
        total_output_tokens INTEGER,
        last_updated TEXT
      );
    `);

    // Insert test data
    db.prepare(`
      INSERT INTO spec_totals (spec_id, total_cost_usd, total_input_tokens, total_output_tokens, last_updated)
      VALUES ('001-test', 1.50, 10000, 5000, '2024-01-15T10:00:00Z')
    `).run();

    db.prepare(`
      INSERT INTO conversations (id, spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model)
      VALUES (1, '001-test', 1, 'planning', '2024-01-15T10:00:00Z', '2024-01-15T10:30:00Z', 1.50, 10000, 5000, 'claude-sonnet-4-5')
    `).run();

    db.prepare(`
      INSERT INTO messages (conversation_id, model, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, cost_usd, timestamp)
      VALUES (1, 'claude-sonnet-4-5', 10000, 5000, 2000, 1000, 1.50, '2024-01-15T10:15:00Z')
    `).run();

    db.close();
  });

  afterEach(() => {
    // Clean up temp database
    if (fs.existsSync(tempDbPath)) {
      fs.unlinkSync(tempDbPath);
    }

    // Reset store
    useAnalyticsStore.setState({
      data: null,
      isPolling: false,
      pollingIntervalMs: 2000,
      budgets: {},
      alertsShown: {},
    });

    vi.clearAllTimers();
  });

  it('should not poll when dbPath is null', () => {
    const { unmount } = renderHook(() => useAnalyticsData(null, 1000));

    expect(useAnalyticsStore.getState().data).toBeNull();

    unmount();
  });

  it('should fetch data on mount', async () => {
    const { unmount } = renderHook(() => useAnalyticsData(tempDbPath, 1000));

    // Wait for initial fetch
    await vi.waitFor(() => {
      const state = useAnalyticsStore.getState();
      return state.data !== null;
    });

    const data = useAnalyticsStore.getState().data;

    expect(data).toBeDefined();
    expect(data?.totalCost).toBe(1.50);
    expect(data?.totalTokens.input).toBe(10000);
    expect(data?.totalTokens.output).toBe(5000);
    expect(data?.conversations.length).toBe(1);

    unmount();
  });

  it('should poll database at specified interval', async () => {
    vi.useFakeTimers();

    const { unmount } = renderHook(() => useAnalyticsData(tempDbPath, 100));

    // Initial fetch
    await vi.waitFor(() => {
      return useAnalyticsStore.getState().data !== null;
    });

    const initialData = useAnalyticsStore.getState().data;
    expect(initialData?.totalCost).toBe(1.50);

    // Update database
    const db2 = new Database(tempDbPath);
    db2.prepare(`
      INSERT INTO conversations (id, spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model)
      VALUES (2, '002-test', 1, 'coding', '2024-01-16T10:00:00Z', '2024-01-16T10:30:00Z', 0.75, 3000, 2000, 'claude-sonnet-4-5')
    `).run();
    db2.close();

    // Advance time to trigger next poll
    vi.advanceTimersByTime(100);

    await vi.waitFor(() => {
      const data = useAnalyticsStore.getState().data;
      return data?.conversations.length === 2;
    });

    const updatedData = useAnalyticsStore.getState().data;
    expect(updatedData?.totalCost).toBeGreaterThan(1.50);
    expect(updatedData?.conversations.length).toBe(2);

    vi.useRealTimers();
    unmount();
  });

  it('should stop polling on unmount', async () => {
    vi.useFakeTimers();

    const { unmount } = renderHook(() => useAnalyticsData(tempDbPath, 100));

    await vi.waitFor(() => {
      return useAnalyticsStore.getState().data !== null;
    });

    const dataBeforeUnmount = useAnalyticsStore.getState().data;

    unmount();

    // Update database after unmount
    const db2 = new Database(tempDbPath);
    db2.prepare(`
      INSERT INTO conversations (id, spec_id, session_number, phase, started_at, total_cost_usd, total_input_tokens, total_output_tokens)
      VALUES (99, '999-test', 1, 'coding', '2024-01-20T10:00:00Z', 999.99, 50000, 30000)
    `).run();
    db2.close();

    // Advance time - should NOT trigger poll
    vi.advanceTimersByTime(200);

    const dataAfterUnmount = useAnalyticsStore.getState().data;
    expect(dataAfterUnmount).toBe(dataBeforeUnmount); // Should remain unchanged

    vi.useRealTimers();
  });

  it('should handle database errors gracefully', () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { unmount } = renderHook(() => useAnalyticsData('/invalid/path/to/db.db', 1000));

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Failed to fetch analytics data:',
      expect.any(Error)
    );

    consoleErrorSpy.mockRestore();
    unmount();
  });
});
