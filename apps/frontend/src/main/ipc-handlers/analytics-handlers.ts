/**
 * Analytics IPC Handlers
 *
 * Handles analytics polling start/stop requests from renderer process.
 */

import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import { AnalyticsService } from '../services/analytics-service';

let analyticsService: AnalyticsService | null = null;

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

  console.log('[analytics-handlers] Analytics IPC handlers registered');
}

/**
 * Get the analytics service instance (for cleanup on app quit)
 */
export function getAnalyticsService(): AnalyticsService | null {
  return analyticsService;
}
