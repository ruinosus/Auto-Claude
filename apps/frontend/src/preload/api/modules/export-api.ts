import { IPC_CHANNELS } from '../../../shared/constants';
import type { ExportOptions } from '../../../shared/types/analytics-v2';
import { invokeIpc } from './ipc-utils';

/**
 * Export result type
 */
export interface ExportResult {
  success: boolean;
  filePath?: string;
  error?: string;
}

/**
 * Export API operations (nested under 'export' property)
 */
export interface ExportAPI {
  export: {
    data: (options: ExportOptions) => Promise<ExportResult>;
  };
}

/**
 * Creates the Export API implementation
 */
export const createExportAPI = (): ExportAPI => ({
  export: {
    data: (options: ExportOptions): Promise<ExportResult> =>
      invokeIpc(IPC_CHANNELS.EXPORT_DATA, options)
  }
});
