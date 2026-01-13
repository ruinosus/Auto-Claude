/**
 * Langfuse ROI Dashboard
 * ======================
 *
 * ROI Dashboard that fetches data from the ROI Engine API (port 8002).
 * Uses artifact-based valuation with role-based hourly rates.
 *
 * Settings are loaded from Electron IPC (user preferences).
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, RefreshCw, Settings, TrendingUp } from 'lucide-react';
import { useROIEngineHealth, useROIEngineUnified, useROIEngineValueBreakdown } from '../../../hooks/useROIEngineQuery';
import { ROIOverviewCards } from './ROIOverviewCards';
import { ROIChart } from './ROIChart';
import { CostValueChart } from './CostValueChart';
import { ROITable } from './ROITable';
import { Button } from '../../ui/button';
import { Card, CardContent } from '../../ui/card';
import type { ROIAggregateMetrics, ROISettings, SpecROIWithMetrics } from '../../../../shared/types/roi';
import { DEFAULT_ROI_SETTINGS } from '../../../../shared/types/roi';
import type { UnifiedROIResponse, ValueBreakdownResponse } from '../../../services/roi-engine-api';

/**
 * Transform ROI Engine unified data to the expected component format
 */
function transformToAggregate(data: UnifiedROIResponse | undefined): ROIAggregateMetrics | null {
  if (!data) return null;

  // Estimate hours saved based on total artifact value and average hourly rate
  // Using default senior developer rate of $125/hr for estimation
  const avgHourlyRate = 125;
  const estimatedHoursSaved = data.total_artifact_value / avgHourlyRate;

  // Calculate success rate based on positive ROI
  const specCount = Object.keys(data.by_spec || {}).length;
  const successRate = data.roi_percentage > 0 ? 100 : 0; // Simplified for now

  return {
    totalROI: data.roi_percentage,
    totalSavings: data.net_value,
    totalHoursSaved: estimatedHoursSaved,
    totalCost: data.total_token_cost,
    successRate: successRate,
    specsCount: specCount,
  };
}

/**
 * Transform ROI Engine unified response to SpecROIWithMetrics
 * Uses by_spec breakdown to create per-spec entries
 * @param data - Unified ROI response from ROI Engine
 * @param valueBreakdown - Value breakdown response for detailed per-spec info
 * @param hourlyRate - Developer hourly rate from settings
 */
function transformToSpecs(
  data: UnifiedROIResponse | undefined,
  valueBreakdown: ValueBreakdownResponse | undefined,
  hourlyRate: number
): SpecROIWithMetrics[] {
  if (!data || !data.by_spec) return [];

  const now = new Date().toISOString();

  // Create spec entries from the by_spec breakdown
  return Object.entries(data.by_spec).map(([specId, specValue]) => {
    // Get additional spec info from value breakdown if available
    const specBreakdown = valueBreakdown?.by_spec?.find(
      (item) => item.category === specId
    );

    // Estimate token cost per spec proportionally
    const totalValue = data.total_artifact_value || 1;
    const specCostRatio = specValue / totalValue;
    const specCost = data.total_token_cost * specCostRatio;

    // Calculate ROI for this spec
    const specNetValue = specValue - specCost;
    const specROI = specCost > 0 ? (specNetValue / specCost) * 100 : 0;

    // Estimate hours saved for this spec
    const estimatedHours = specValue / hourlyRate;

    return {
      specId: specId,
      projectId: specId.split('-')[0] || '',
      estimatedBusinessValue: specValue,
      estimatedHoursManual: estimatedHours,
      developerRateOverride: null,
      actualCost: specCost,
      totalTokens: 0, // Not available per-spec
      linesAdded: 0, // Not tracked by ROI Engine
      linesRemoved: 0,
      filesChanged: 0,
      executionTimeSeconds: 0,
      qaAttempts: 0,
      qaPassed: true, // Assume passed if artifact exists
      createdAt: now,
      completedAt: now,
      metrics: {
        effectiveHourlyRate: hourlyRate,
        estimatedManualCost: estimatedHours * hourlyRate,
        costSavings: specNetValue,
        roiPercentage: specROI,
        costPerLine: 0, // Not tracked
        efficiencyScore: specBreakdown?.percentage || (specValue / totalValue) * 100,
      },
    };
  });
}

interface LangfuseROIDashboardProps {
  /** Project directory path - used for data isolation */
  projectName?: string;
}

/**
 * Langfuse ROI Dashboard component
 *
 * Now powered by ROI Engine API (port 8002) for artifact-based ROI calculation.
 * Uses role-based valuation: Value = Hourly Rate × Estimated Hours
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

  // Check if ROI Engine is healthy and connected
  const health = useROIEngineHealth({ enabled: settingsLoaded });

  // Fetch unified ROI data from ROI Engine
  const {
    data: unifiedROI,
    isLoading: isUnifiedLoading,
    isError: isUnifiedError,
    error: unifiedError,
    refetch: refetchUnified,
  } = useROIEngineUnified(
    { project_dir: projectName || '' },
    {
      enabled: health.data?.status === 'healthy' && settingsLoaded && !!projectName,
    }
  );

  // Fetch value breakdown for detailed spec information
  const {
    data: valueBreakdown,
    isLoading: isBreakdownLoading,
    refetch: refetchBreakdown,
  } = useROIEngineValueBreakdown(
    { project_dir: projectName || '' },
    {
      enabled: health.data?.status === 'healthy' && settingsLoaded && !!projectName,
    }
  );

  const isLoading = isUnifiedLoading || isBreakdownLoading;

  const refetch = () => {
    refetchUnified();
    refetchBreakdown();
  };

  // Show loading state while checking health
  if (health.isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
        <p className="text-muted-foreground">{t('analytics:roi.dashboard.loading')}</p>
      </div>
    );
  }

  // Show configuration needed if ROI Engine is not available
  if (!health.data || health.data.status !== 'healthy') {
    return (
      <Card className="mx-auto max-w-lg">
        <CardContent className="p-6 text-center">
          <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">
            ROI Engine Not Available
          </h3>
          <p className="text-muted-foreground mb-4">
            The ROI Engine API is not running. Start it to see artifact-based ROI metrics.
          </p>
          <div className="text-sm text-muted-foreground bg-muted p-3 rounded-md font-mono">
            cd apps/roi-engine && python -m api.app
          </div>
          {health.isError && (
            <p className="text-xs text-destructive mt-2">
              Error: {health.error instanceof Error ? health.error.message : 'Connection failed'}
            </p>
          )}
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

  if (isUnifiedError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertCircle className="h-8 w-8 text-destructive mb-4" />
        <p className="text-destructive mb-4">
          {unifiedError instanceof Error ? unifiedError.message : t('analytics:roi.dashboard.error')}
        </p>
        <Button onClick={() => refetch()} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          {t('analytics:roi.dashboard.retry')}
        </Button>
      </div>
    );
  }

  // Transform data for existing components using user settings
  const aggregate = transformToAggregate(unifiedROI);
  const specs = transformToSpecs(unifiedROI, valueBreakdown, settings.developerHourlyRate);

  return (
    <div className="space-y-6">
      {/* Source indicator and settings info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span>
              <TrendingUp className="h-3 w-3 inline mr-1" />
              ROI Engine (Artifact-Based)
            </span>
          </div>
          <div className="flex items-center gap-1 text-xs">
            <Settings className="h-3 w-3" />
            <span>
              {t('analytics:roi.dashboard.hourlyRate', { rate: settings.developerHourlyRate })}
            </span>
          </div>
          {unifiedROI && (
            <div className="text-xs">
              {unifiedROI.artifact_count} artifacts valued
            </div>
          )}
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
