import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, FileText, FileJson, FileSpreadsheet, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '../ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { useAnalyticsStore } from '../../stores/analytics-store';
import type { ExportOptions } from '../../../shared/types/analytics-v2';

type ExportFormat = 'csv' | 'json' | 'pdf';

interface ExportStatus {
  type: 'success' | 'error';
  message: string;
}

/**
 * ExportButton component for exporting analytics data
 * Provides a dropdown menu with CSV, JSON, and PDF export options
 */
export function ExportButton() {
  const { t } = useTranslation(['analytics']);
  const [isExporting, setIsExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState<ExportFormat | null>(null);
  const [status, setStatus] = useState<ExportStatus | null>(null);
  const filters = useAnalyticsStore((state) => state.filters);

  const handleExport = async (format: ExportFormat) => {
    setIsExporting(true);
    setExportFormat(format);
    setStatus(null);

    try {
      const exportOptions: ExportOptions = {
        format,
        dateRange: filters.dateRange,
        filters,
        includeMetrics: ['cost', 'tokens', 'sessions']
      };

      const result = await window.electronAPI.export.data(exportOptions);

      if (result.success && result.filePath) {
        setStatus({
          type: 'success',
          message: t('analytics:export.success.description', { filePath: result.filePath })
        });
        // Clear success message after 5 seconds
        setTimeout(() => setStatus(null), 5000);
      } else {
        throw new Error(result.error || 'Unknown error');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      setStatus({
        type: 'error',
        message: t('analytics:export.error.description', { error: errorMessage })
      });
      // Clear error message after 8 seconds
      setTimeout(() => setStatus(null), 8000);
    } finally {
      setIsExporting(false);
      setExportFormat(null);
    }
  };

  const formatIcons: Record<ExportFormat, React.ElementType> = {
    csv: FileSpreadsheet,
    json: FileJson,
    pdf: FileText,
  };

  const formats: ExportFormat[] = ['csv', 'json', 'pdf'];

  return (
    <div className="flex items-center gap-2">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            disabled={isExporting}
            aria-label={t('analytics:export.title')}
            aria-haspopup="menu"
          >
            {isExporting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" aria-hidden="true" />
            ) : (
              <Download className="h-4 w-4 mr-2" aria-hidden="true" />
            )}
            {t('analytics:export.title')}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {formats.map((format) => {
            const Icon = formatIcons[format];
            const isCurrentlyExporting = isExporting && exportFormat === format;
            return (
              <DropdownMenuItem
                key={format}
                onClick={() => handleExport(format)}
                disabled={isExporting}
                aria-label={t(`analytics:export.${format}`)}
              >
                {isCurrentlyExporting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" aria-hidden="true" />
                ) : (
                  <Icon className="h-4 w-4 mr-2" aria-hidden="true" />
                )}
                {t(`analytics:export.${format}`)}
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Inline status feedback */}
      {status && (
        <div
          className={`flex items-center gap-1.5 text-xs ${
            status.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
          }`}
          role="status"
          aria-live="polite"
        >
          {status.type === 'success' ? (
            <CheckCircle className="h-3.5 w-3.5" aria-hidden="true" />
          ) : (
            <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          <span className="max-w-[200px] truncate" title={status.message}>
            {status.type === 'success'
              ? t('analytics:export.success.title')
              : t('analytics:export.error.title')}
          </span>
        </div>
      )}
    </div>
  );
}
