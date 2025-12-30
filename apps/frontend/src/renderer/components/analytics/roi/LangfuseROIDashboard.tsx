/**
 * Langfuse ROI Dashboard
 * ======================
 *
 * ROI Dashboard that fetches data from the FastAPI analytics service,
 * which gets data from Langfuse as the source of truth.
 *
 * Settings are loaded from Electron IPC (user preferences).
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, RefreshCw, Settings } from 'lucide-react';
import { useROISummary, useAnalyticsHealth } from '../../../hooks/useAnalyticsQuery';
import { ROIOverviewCards } from './ROIOverviewCards';
import { ROIChart } from './ROIChart';
import { CostValueChart } from './CostValueChart';
import { ROITable } from './ROITable';
import { Button } from '../../ui/button';
import { Card, CardContent } from '../../ui/card';
import type { ROIAggregateMetrics, ROISettings, SpecROIWithMetrics } from '../../../../shared/types/roi';
import { DEFAULT_ROI_SETTINGS } from '../../../../shared/types/roi';
import type { ROISummaryResponse, ROIResponse } from '../../../services/analytics-api';

/**
 * Transform Langfuse ROI data to the expected component format
 */
function transformToAggregate(data: ROISummaryResponse | undefined): ROIAggregateMetrics | null {
  if (!data) return null;

  return {
    totalROI: data.total_roi_percentage,
    totalSavings: data.total_business_value_usd - data.total_actual_cost_usd,
    totalHoursSaved: data.total_dev_hours_saved,
    totalCost: data.total_actual_cost_usd,
    successRate: data.spec_count > 0 ? (data.specs_with_positive_roi / data.spec_count) * 100 : 0,
    specsCount: data.spec_count,
  };
}

/**
 * Transform Langfuse ROI response to SpecROIWithMetrics
 * @param data - ROI summary response from API
 * @param hourlyRate - Developer hourly rate from settings
 */
function transformToSpecs(
  data: ROISummaryResponse | undefined,
  hourlyRate: number
): SpecROIWithMetrics[] {
  if (!data || !data.by_spec) return [];

  return data.by_spec.map((spec: ROIResponse) => ({
    specId: spec.spec_id,
    projectId: spec.spec_id.split('-')[0] || '', // Extract project from spec ID if available
    estimatedBusinessValue: spec.metrics.business_value_usd,
    estimatedHoursManual: spec.metrics.dev_hours_saved,
    developerRateOverride: null,
    actualCost: spec.metrics.actual_cost_usd,
    totalTokens: 0, // Not available from Langfuse ROI endpoint
    linesAdded: spec.metrics.lines_added,
    linesRemoved: spec.metrics.lines_removed,
    filesChanged: spec.metrics.files_changed,
    executionTimeSeconds: 0, // Not available from Langfuse ROI endpoint
    qaAttempts: spec.metrics.qa_attempts,
    qaPassed: spec.metrics.qa_passed,
    createdAt: spec.calculated_at,
    completedAt: spec.metrics.qa_passed ? spec.calculated_at : null,
    metrics: {
      effectiveHourlyRate: hourlyRate,
      estimatedManualCost: spec.metrics.dev_hours_saved * hourlyRate,
      costSavings: spec.metrics.business_value_usd - spec.metrics.actual_cost_usd,
      roiPercentage: spec.metrics.roi_percentage,
      costPerLine: spec.metrics.lines_added > 0
        ? spec.metrics.actual_cost_usd / spec.metrics.lines_added
        : 0,
      efficiencyScore: spec.metrics.confidence_score * 100,
    },
  }));
}

interface LangfuseROIDashboardProps {
  /** Project name (directory name) - used for Langfuse data isolation */
  projectName?: string;
}

/**
 * Langfuse ROI Dashboard component
 *
 * IMPORTANT: projectName is the directory name, NOT the UUID.
 * The backend stores project_id as directory name in Langfuse metadata.
 */
export function LangfuseROIDashboard({ projectName }: LangfuseROIDashboardProps) {
  const { t } = useTranslation(['analytics']);

  // Load ROI settings from Electron IPC (user preferences)
  const [settings, setSettings] = useState<ROISettings>(DEFAULT_ROI_SETTINGS);
  const [settingsLoaded, setSettingsLoaded] = useState(false);

  useEffect(() => {
    // Fetch user ROI settings from Electron
    window.electronAPI.roi
      .getSettings()
      .then((userSettings) => {
        setSettings(userSettings);
        setSettingsLoaded(true);
      })
      .catch((err) => {
        console.error('Failed to load ROI settings:', err);
        setSettingsLoaded(true); // Use defaults on error
      });
  }, []);

  // Check if Langfuse is configured
  const health = useAnalyticsHealth();

  // Fetch ROI summary with project_id filter for data isolation
  // NOTE: project_id is the directory name (projectName), not UUID
  const {
    data: roiSummary,
    isLoading,
    isError,
    error,
    refetch,
  } = useROISummary(
    { project_id: projectName },
    {
      enabled: health.data?.langfuse_configured === true && settingsLoaded && !!projectName,
    }
  );

  // Show configuration needed message
  if (health.isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
        <p className="text-muted-foreground">{t('analytics:roi.dashboard.loading')}</p>
      </div>
    );
  }

  if (!health.data?.langfuse_configured) {
    return (
      <Card className="mx-auto max-w-lg">
        <CardContent className="p-6 text-center">
          <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">
            {t('analytics:roi.dashboard.notConfigured')}
          </h3>
          <p className="text-muted-foreground mb-4">
            {t('analytics:roi.dashboard.configureMessage')}
          </p>
          <div className="text-sm text-muted-foreground bg-muted p-3 rounded-md font-mono">
            LANGFUSE_PUBLIC_KEY=pk-lf-xxx
            <br />
            LANGFUSE_SECRET_KEY=sk-lf-xxx
            <br />
            LANGFUSE_HOST=http://localhost:3001
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!projectName) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertCircle className="h-8 w-8 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">
          {t('analytics:roi.dashboard.noProject', 'No project selected')}
        </p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertCircle className="h-8 w-8 text-destructive mb-4" />
        <p className="text-destructive mb-4">
          {error instanceof Error ? error.message : t('analytics:roi.dashboard.error')}
        </p>
        <Button onClick={() => refetch()} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          {t('analytics:roi.dashboard.retry')}
        </Button>
      </div>
    );
  }

  // Transform data for existing components using user settings
  const aggregate = transformToAggregate(roiSummary);
  const specs = transformToSpecs(roiSummary, settings.developerHourlyRate);

  return (
    <div className="space-y-6">
      {/* Source indicator and settings info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span>{t('analytics:roi.dashboard.dataSource')}: Langfuse</span>
          </div>
          <div className="flex items-center gap-1 text-xs">
            <Settings className="h-3 w-3" />
            <span>
              {t('analytics:roi.dashboard.hourlyRate', { rate: settings.developerHourlyRate })}
            </span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => refetch()}
          disabled={isLoading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          {t('analytics:roi.dashboard.refresh')}
        </Button>
      </div>

      {/* Overview Cards */}
      <ROIOverviewCards
        aggregate={aggregate}
        settings={settings}
        isLoading={isLoading}
      />

      {/* Charts Row */}
      <div className="grid gap-6 md:grid-cols-2">
        <ROIChart
          specs={specs}
          isLoading={isLoading}
        />
        <CostValueChart
          specs={specs}
          isLoading={isLoading}
        />
      </div>

      {/* Details Table */}
      <ROITable
        specs={specs}
        isLoading={isLoading}
      />
    </div>
  );
}
