/**
 * Analytics IPC Handlers
 *
 * Handles analytics polling start/stop requests from renderer process.
 * Also handles budget persistence via settings.json.
 */

import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import { app } from 'electron';
import { existsSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { IPC_CHANNELS } from '../../shared/constants';
import { AnalyticsService } from '../services/analytics-service';

let analyticsService: AnalyticsService | null = null;

// Budget storage helpers
function getSettingsPath(): string {
  return join(app.getPath('userData'), 'settings.json');
}

function loadSettings(): Record<string, unknown> {
  const path = getSettingsPath();
  if (existsSync(path)) {
    try {
      return JSON.parse(readFileSync(path, 'utf-8'));
    } catch {
      return {};
    }
  }
  return {};
}

function saveSettings(settings: Record<string, unknown>): void {
  const path = getSettingsPath();
  writeFileSync(path, JSON.stringify(settings, null, 2));
}

/**
 * Setup analytics IPC handlers
 */
export function setupAnalyticsHandlers(getMainWindow: () => BrowserWindow | null): void {
  // Initialize analytics service
  analyticsService = new AnalyticsService(getMainWindow);

  // Start polling analytics database
  ipcMain.on(IPC_CHANNELS.ANALYTICS_START_POLLING, (_event, dbPath: string) => {
    console.log('[analytics-handlers] Start polling request:', dbPath);
    analyticsService?.startPolling(dbPath);
  });

  // Stop polling analytics database
  ipcMain.on(IPC_CHANNELS.ANALYTICS_STOP_POLLING, () => {
    console.log('[analytics-handlers] Stop polling request');
    analyticsService?.stopPolling();
  });

  // Get budget for a project
  ipcMain.handle(IPC_CHANNELS.BUDGET_GET, async (_event, projectId: string) => {
    try {
      const settings = loadSettings();
      const budgets = (settings.budgets as Record<string, number>) || {};
      const budget = budgets[projectId];
      return { success: true, data: budget };
    } catch (error) {
      console.error('[analytics-handlers] Failed to get budget:', error);
      return { success: false, error: String(error) };
    }
  });

  // Save budget for a project
  ipcMain.handle(IPC_CHANNELS.BUDGET_SAVE, async (_event, projectId: string, budget: number | null) => {
    try {
      const settings = loadSettings();
      const budgets = (settings.budgets as Record<string, number>) || {};

      if (budget === null || budget === undefined) {
        delete budgets[projectId];
      } else {
        budgets[projectId] = budget;
      }

      settings.budgets = budgets;
      saveSettings(settings);

      console.log('[analytics-handlers] Saved budget for project:', projectId, budget);
      return { success: true };
    } catch (error) {
      console.error('[analytics-handlers] Failed to save budget:', error);
      return { success: false, error: String(error) };
    }
  });

  console.log('[analytics-handlers] Analytics IPC handlers registered');
}

/**
 * Get the analytics service instance (for cleanup on app quit)
 */
export function getAnalyticsService(): AnalyticsService | null {
  return analyticsService;
}
