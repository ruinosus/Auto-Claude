/**
 * Export Service - Exports analytics data to CSV, JSON, and PDF formats
 *
 * This service runs in the main process (Node.js) and handles
 * exporting analytics data to various file formats.
 */

import { app } from 'electron';
import * as fs from 'fs';
import * as path from 'path';
import type { ExportOptions } from '../../shared/types/analytics-v2';

export interface AnalyticsExportData {
  conversations?: Array<{
    spec_id: string;
    phase?: string;
    total_cost_usd?: number;
    total_input_tokens?: number;
    total_output_tokens?: number;
    started_at?: string;
  }>;
  totals?: {
    totalCost?: number;
    totalTokens?: number;
    activeSessions?: number;
  };
  featureUsage?: Record<string, number>;
}

export class ExportService {
  private static instance: ExportService;

  static getInstance(): ExportService {
    if (!ExportService.instance) {
      ExportService.instance = new ExportService();
    }
    return ExportService.instance;
  }

  async exportToCSV(data: AnalyticsExportData, options: ExportOptions): Promise<string> {
    const rows: string[] = [];

    // Header
    const headers = ['Spec ID', 'Phase', 'Cost (USD)', 'Input Tokens', 'Output Tokens', 'Started At'];
    rows.push(headers.join(','));

    // Data rows
    for (const conv of data.conversations || []) {
      const row = [
        this.escapeCSV(conv.spec_id),
        this.escapeCSV(conv.phase || ''),
        conv.total_cost_usd?.toFixed(4) || '0',
        conv.total_input_tokens?.toString() || '0',
        conv.total_output_tokens?.toString() || '0',
        conv.started_at || ''
      ];
      rows.push(row.join(','));
    }

    return rows.join('\n');
  }

  async exportToJSON(data: AnalyticsExportData, options: ExportOptions): Promise<string> {
    const exportData = {
      exportedAt: new Date().toISOString(),
      dateRange: options.dateRange,
      totals: data.totals,
      conversations: data.conversations,
      featureUsage: data.featureUsage
    };
    return JSON.stringify(exportData, null, 2);
  }

  async exportToPDF(data: AnalyticsExportData, options: ExportOptions): Promise<Buffer> {
    // Simplified text-based PDF generation
    const content = `Analytics Report\n\nGenerated: ${new Date().toISOString()}\n\n` +
      `Total Cost: $${data.totals?.totalCost?.toFixed(2) || '0'}\n` +
      `Total Tokens: ${data.totals?.totalTokens || 0}\n` +
      `Sessions: ${data.totals?.activeSessions || 0}\n`;

    return Buffer.from(content, 'utf-8');
  }

  async saveExport(
    content: string | Buffer,
    filename: string,
    format: 'csv' | 'json' | 'pdf'
  ): Promise<string> {
    const downloadsPath = app.getPath('downloads');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const fullFilename = `${filename}-${timestamp}.${format}`;
    const filePath = path.join(downloadsPath, fullFilename);

    await fs.promises.writeFile(filePath, content);
    return filePath;
  }

  private escapeCSV(value: string): string {
    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
      return `"${value.replace(/"/g, '""')}"`;
    }
    return value;
  }
}
