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

  /**
   * Returns the singleton instance of ExportService
   */
  static getInstance(): ExportService {
    if (!ExportService.instance) {
      ExportService.instance = new ExportService();
    }
    return ExportService.instance;
  }

  /**
   * Sanitizes a filename to prevent path traversal attacks.
   * Only allows alphanumeric characters, hyphens, and underscores.
   * @param filename - The filename to sanitize
   * @returns Sanitized filename safe for filesystem operations
   */
  private sanitizeFilename(filename: string): string {
    return filename.replace(/[^a-zA-Z0-9_-]/g, '_');
  }

  /**
   * Exports analytics data to CSV format
   * @param data - The analytics data to export
   * @param options - Export options including date range
   * @returns CSV formatted string
   */
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

  /**
   * Exports analytics data to JSON format
   * @param data - The analytics data to export
   * @param options - Export options including date range
   * @returns JSON formatted string
   */
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

  /**
   * Exports analytics data to PDF format
   * NOTE: This is a simplified text-based export. For proper PDF generation
   * with formatting, headers, and styling, consider using pdf-lib or similar.
   * @param data - The analytics data to export
   * @param options - Export options including date range
   * @returns Buffer containing the PDF content
   */
  async exportToPDF(data: AnalyticsExportData, options: ExportOptions): Promise<Buffer> {
    // Simplified text-based PDF generation
    // For a proper PDF with formatting, use pdf-lib or pdfkit
    const content = `Analytics Report\n\nGenerated: ${new Date().toISOString()}\n\n` +
      `Total Cost: $${data.totals?.totalCost?.toFixed(2) || '0'}\n` +
      `Total Tokens: ${data.totals?.totalTokens || 0}\n` +
      `Sessions: ${data.totals?.activeSessions || 0}\n`;

    return Buffer.from(content, 'utf-8');
  }

  /**
   * Saves exported content to a file in the downloads directory
   * @param content - The content to save (string or Buffer)
   * @param filename - Base filename (will be sanitized)
   * @param format - Export format determining file extension
   * @returns Full path to the saved file
   */
  async saveExport(
    content: string | Buffer,
    filename: string,
    format: 'csv' | 'json' | 'pdf'
  ): Promise<string> {
    const downloadsPath = app.getPath('downloads');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const sanitizedFilename = this.sanitizeFilename(filename);
    const fullFilename = `${sanitizedFilename}-${timestamp}.${format}`;
    const filePath = path.join(downloadsPath, fullFilename);

    await fs.promises.writeFile(filePath, content);
    return filePath;
  }

  /**
   * Escapes a value for safe inclusion in CSV output
   * @param value - The string value to escape
   * @returns Escaped string safe for CSV
   */
  private escapeCSV(value: string): string {
    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
      return `"${value.replace(/"/g, '""')}"`;
    }
    return value;
  }
}
