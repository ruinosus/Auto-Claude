import React from 'react';
import { useTranslation } from 'react-i18next';
import { X, Trophy } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import type { SpecROI } from '../../../../shared/types/roi';
import { formatCurrency } from '../utils/formatters';

export interface SpecComparisonViewProps {
  specs: SpecROI[];
  onClose: () => void;
}

interface MetricColumn {
  key: keyof SpecROI | 'roiPercentage';
  label: string;
  format: (value: number) => string;
  higherIsBetter: boolean;
}

/**
 * Displays side-by-side comparison of multiple specs with key metrics
 */
export function SpecComparisonView({ specs, onClose }: SpecComparisonViewProps) {
  const { t } = useTranslation(['analytics']);

  const metrics: MetricColumn[] = [
    {
      key: 'roiPercentage',
      label: t('analytics:roi.table.roi'),
      format: (v) => `${v.toFixed(0)}%`,
      higherIsBetter: true,
    },
    {
      key: 'actualCost',
      label: t('analytics:roi.table.actualCost'),
      format: (v) => formatCurrency(v, 2),
      higherIsBetter: false,
    },
    {
      key: 'totalTokens',
      label: t('analytics:filters.models'),
      format: (v) => v.toLocaleString(),
      higherIsBetter: false,
    },
    {
      key: 'executionTimeSeconds',
      label: t('analytics:comparison.time'),
      format: (v) => formatTime(v),
      higherIsBetter: false,
    },
    {
      key: 'qaAttempts',
      label: t('analytics:comparison.qaAttempts'),
      format: (v) => v.toString(),
      higherIsBetter: false,
    },
  ];

  /**
   * Finds the best value index for a given metric
   */
  function findBestIndex(metricKey: keyof SpecROI | 'roiPercentage', higherIsBetter: boolean): number {
    if (specs.length === 0) return -1;

    let bestIndex = 0;
    let bestValue = getMetricValue(specs[0], metricKey);

    for (let i = 1; i < specs.length; i++) {
      const value = getMetricValue(specs[i], metricKey);
      const isBetter = higherIsBetter ? value > bestValue : value < bestValue;
      if (isBetter) {
        bestValue = value;
        bestIndex = i;
      }
    }

    return bestIndex;
  }

  /**
   * Gets metric value from a spec, calculating ROI percentage if needed
   */
  function getMetricValue(spec: SpecROI, key: keyof SpecROI | 'roiPercentage'): number {
    if (key === 'roiPercentage') {
      // Calculate ROI percentage: (savings / cost) * 100
      const manualCost = spec.estimatedHoursManual
        ? spec.estimatedHoursManual * (spec.developerRateOverride || 75)
        : 0;
      const savings = manualCost - spec.actualCost;
      return spec.actualCost > 0 ? (savings / spec.actualCost) * 100 : 0;
    }
    const value = spec[key];
    return typeof value === 'number' ? value : 0;
  }

  if (specs.length === 0) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{t('analytics:comparison.title')}</CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label={t('analytics:comparison.close')}
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">{t('analytics:comparison.select')}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{t('analytics:comparison.title')}</CardTitle>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          aria-label={t('analytics:comparison.close')}
        >
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full" role="grid" aria-label={t('analytics:comparison.title')}>
            <thead>
              <tr>
                <th className="text-left p-2 text-sm font-medium text-muted-foreground">
                  {t('analytics:comparison.metric')}
                </th>
                {specs.map((spec) => (
                  <th
                    key={spec.specId}
                    className="text-center p-2 text-sm font-medium"
                    scope="col"
                  >
                    <span className="font-mono">{spec.specId.slice(0, 12)}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {metrics.map((metric) => {
                const bestIndex = findBestIndex(metric.key, metric.higherIsBetter);
                return (
                  <tr key={metric.key} className="border-t border-border">
                    <td className="p-2 text-sm text-muted-foreground">{metric.label}</td>
                    {specs.map((spec, index) => {
                      const value = getMetricValue(spec, metric.key);
                      const isBest = index === bestIndex && specs.length > 1;
                      return (
                        <td
                          key={spec.specId}
                          className="p-2 text-center"
                        >
                          <div className="flex items-center justify-center gap-1">
                            <span className={isBest ? 'font-semibold text-green-500' : ''}>
                              {metric.format(value)}
                            </span>
                            {isBest && (
                              <Badge variant="success" className="ml-1">
                                <Trophy className="h-3 w-3 mr-0.5" aria-hidden="true" />
                                {t('analytics:comparison.best')}
                              </Badge>
                            )}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Formats seconds into a human-readable time string
 */
function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(0)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}
