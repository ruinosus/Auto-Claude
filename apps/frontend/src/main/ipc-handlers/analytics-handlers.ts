/**
 * Analytics IPC Handlers
 *
 * Handles analytics polling start/stop requests from renderer process.
 * Also handles budget persistence via settings.json.
 * Also handles terminal tracking hook initialization.
 */

import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import { app } from 'electron';
import { spawn } from 'child_process';
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

  // Initialize terminal tracking hooks
  ipcMain.handle(IPC_CHANNELS.ANALYTICS_INIT_TRACKING, async (_event, pythonPath?: string, backendPath?: string) => {
    try {
      const result = await initializeTerminalTracking(pythonPath, backendPath);
      console.log('[analytics-handlers] Terminal tracking initialization result:', result);
      return { success: true, data: result };
    } catch (error) {
      console.error('[analytics-handlers] Failed to initialize terminal tracking:', error);
      return { success: false, error: String(error) };
    }
  });

  // Get terminal tracking status
  ipcMain.handle(IPC_CHANNELS.ANALYTICS_GET_TRACKING_STATUS, async (_event, pythonPath?: string, backendPath?: string) => {
    try {
      const status = await getTerminalTrackingStatus(pythonPath, backendPath);
      return { success: true, data: status };
    } catch (error) {
      console.error('[analytics-handlers] Failed to get tracking status:', error);
      return { success: false, error: String(error) };
    }
  });

  console.log('[analytics-handlers] Analytics IPC handlers registered');
}

/**
 * Initialize terminal tracking hooks by calling Python backend
 */
async function initializeTerminalTracking(pythonPath?: string, backendPath?: string): Promise<{ terminal_tracking: boolean; analytics_enabled: boolean }> {
  const python = pythonPath || 'python3';
  const backend = backendPath || join(app.getPath('userData'), '..', 'auto-claude', 'apps', 'backend');

  return new Promise((resolve, reject) => {
    const script = `
import sys
sys.path.insert(0, '${backend.replace(/\\/g, '/')}')
import json
from init import init_app
result = init_app()
print(json.dumps(result))
`;

    const proc = spawn(python, ['-c', script], {
      cwd: backend,
      env: { ...process.env }
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    proc.on('close', (code) => {
      if (code === 0) {
        try {
          // Parse the last line that contains JSON
          const lines = stdout.trim().split('\n');
          const jsonLine = lines[lines.length - 1];
          const result = JSON.parse(jsonLine);
          resolve(result);
        } catch (e) {
          console.error('[analytics-handlers] Failed to parse init_app output:', stdout);
          resolve({ terminal_tracking: false, analytics_enabled: false });
        }
      } else {
        console.error('[analytics-handlers] init_app failed:', stderr);
        resolve({ terminal_tracking: false, analytics_enabled: false });
      }
    });

    proc.on('error', (err) => {
      console.error('[analytics-handlers] Failed to spawn Python:', err);
      reject(err);
    });
  });
}

/**
 * Get terminal tracking status from Python backend
 */
async function getTerminalTrackingStatus(pythonPath?: string, backendPath?: string): Promise<Record<string, unknown>> {
  const python = pythonPath || 'python3';
  const backend = backendPath || join(app.getPath('userData'), '..', 'auto-claude', 'apps', 'backend');

  return new Promise((resolve, reject) => {
    const script = `
import sys
sys.path.insert(0, '${backend.replace(/\\/g, '/')}')
import json
from init import get_terminal_tracking_status
result = get_terminal_tracking_status()
print(json.dumps(result))
`;

    const proc = spawn(python, ['-c', script], {
      cwd: backend,
      env: { ...process.env }
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    proc.on('close', (code) => {
      if (code === 0) {
        try {
          const lines = stdout.trim().split('\n');
          const jsonLine = lines[lines.length - 1];
          const result = JSON.parse(jsonLine);
          resolve(result);
        } catch (e) {
          console.error('[analytics-handlers] Failed to parse status output:', stdout);
          resolve({ error: 'parse_error', hook_installed: false });
        }
      } else {
        console.error('[analytics-handlers] get_terminal_tracking_status failed:', stderr);
        resolve({ error: stderr, hook_installed: false });
      }
    });

    proc.on('error', (err) => {
      console.error('[analytics-handlers] Failed to spawn Python:', err);
      reject(err);
    });
  });
}

/**
 * Get the analytics service instance (for cleanup on app quit)
 */
export function getAnalyticsService(): AnalyticsService | null {
  return analyticsService;
}

/**
 * Initialize terminal tracking on app startup.
 * This should be called during Electron app initialization.
 */
export async function initializeTerminalTrackingOnStartup(settings: { pythonPath?: string; autoBuildPath?: string }): Promise<void> {
  try {
    const result = await initializeTerminalTracking(settings.pythonPath, settings.autoBuildPath);
    console.log('[analytics-handlers] Terminal tracking initialized on startup:', result);
  } catch (error) {
    console.error('[analytics-handlers] Failed to initialize terminal tracking on startup:', error);
    // Don't throw - this shouldn't prevent app startup
  }
}
