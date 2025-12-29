/**
 * Export IPC Handlers
 *
 * Handles export requests from renderer process for analytics data.
 */

import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { ExportService } from '../services/export-service';
import type { ExportOptions } from '../../shared/types/analytics-v2';

/**
 * Setup export IPC handlers
 */
export function setupExportHandlers(): void {
  const exportService = ExportService.getInstance();

  ipcMain.handle(IPC_CHANNELS.EXPORT_DATA, async (_, options: ExportOptions) => {
    try {
      // Validate format at runtime to prevent invalid input
      const validFormats = ['csv', 'json', 'pdf'] as const;
      if (!validFormats.includes(options.format as typeof validFormats[number])) {
        throw new Error(`Invalid export format: ${options.format}. Must be one of: csv, json, pdf`);
      }

      // In a real implementation, we would fetch data from analytics service
      // For now, return a stub response
      const data = {
        conversations: [],
        totals: { totalCost: 0, totalTokens: 0, activeSessions: 0 },
        featureUsage: {}
      };

      let content: string | Buffer;
      switch (options.format) {
        case 'csv':
          content = await exportService.exportToCSV(data, options);
          break;
        case 'json':
          content = await exportService.exportToJSON(data, options);
          break;
        case 'pdf':
          content = await exportService.exportToPDF(data, options);
          break;
        default:
          throw new Error(`Unknown format: ${options.format}`);
      }

      const filePath = await exportService.saveExport(
        content,
        'analytics-export',
        options.format
      );

      return { success: true, filePath };
    } catch (error) {
      console.error('[export-handlers] Export failed:', error);
      return { success: false, error: String(error) };
    }
  });

  console.log('[export-handlers] Export IPC handlers registered');
}
