import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, AlertTriangle, CheckCircle, Code, Target } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Badge } from '../../ui/badge';
import type { QualityMetrics } from '../../../../shared/types/analytics-v2';

export interface QualityMetricsCardProps {
  metrics: QualityMetrics | null;
  isLoading?: boolean;
}

type GradeType = 'A' | 'B' | 'C' | 'D' | 'F';

/**
 * Maps quality grades to badge variants and colors
 */
function getGradeVariant(grade: GradeType): 'success' | 'warning' | 'destructive' | 'default' {
  switch (grade) {
    case 'A':
      return 'success';
    case 'B':
      return 'success';
    case 'C':
      return 'warning';
    case 'D':
      return 'warning';
    case 'F':
      return 'destructive';
    default:
      return 'default';
  }
}

/**
 * Gets the appropriate icon for each metric type
 */
function MetricIcon({
  type,
  className,
}: {
  type: 'errors' | 'warnings' | 'coverage' | 'complexity';
  className?: string;
}) {
  switch (type) {
    case 'errors':
      return <AlertCircle className={className} aria-hidden="true" />;
    case 'warnings':
      return <AlertTriangle className={className} aria-hidden="true" />;
    case 'coverage':
      return <Target className={className} aria-hidden="true" />;
    case 'complexity':
      return <Code className={className} aria-hidden="true" />;
    default:
      return null;
  }
}

/**
 * Loading skeleton for the quality metrics card
 */
function LoadingState() {
  return (
    <Card className="animate-pulse">
      <CardHeader>
        <div className="h-5 w-32 bg-muted rounded" />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="h-12 w-16 bg-muted rounded mx-auto" />
          <div className="grid grid-cols-2 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-16 bg-muted rounded" />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Displays quality metrics for a spec including grade, lint errors/warnings,
 * test coverage, and complexity score
 */
export function QualityMetricsCard({ metrics, isLoading }: QualityMetricsCardProps) {
  const { t } = useTranslation(['analytics']);

  if (isLoading) {
    return <LoadingState />;
  }

  if (!metrics) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('analytics:quality.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32 text-muted-foreground">
            {t('analytics:quality.noData')}
          </div>
        </CardContent>
      </Card>
    );
  }

  const metricItems = [
    {
      type: 'errors' as const,
      label: t('analytics:quality.lintErrors'),
      value: metrics.lintErrors,
      color: metrics.lintErrors > 0 ? 'text-red-500' : 'text-green-500',
      bgColor: metrics.lintErrors > 0 ? 'bg-red-500/10' : 'bg-green-500/10',
    },
    {
      type: 'warnings' as const,
      label: t('analytics:quality.lintWarnings'),
      value: metrics.lintWarnings,
      color: metrics.lintWarnings > 5 ? 'text-yellow-500' : 'text-green-500',
      bgColor: metrics.lintWarnings > 5 ? 'bg-yellow-500/10' : 'bg-green-500/10',
    },
    {
      type: 'coverage' as const,
      label: t('analytics:quality.coverage'),
      value:
        metrics.testCoveragePercent !== undefined
          ? `${metrics.testCoveragePercent.toFixed(0)}%`
          : '-',
      color:
        metrics.testCoveragePercent !== undefined
          ? metrics.testCoveragePercent >= 80
            ? 'text-green-500'
            : metrics.testCoveragePercent >= 50
              ? 'text-yellow-500'
              : 'text-red-500'
          : 'text-muted-foreground',
      bgColor:
        metrics.testCoveragePercent !== undefined
          ? metrics.testCoveragePercent >= 80
            ? 'bg-green-500/10'
            : metrics.testCoveragePercent >= 50
              ? 'bg-yellow-500/10'
              : 'bg-red-500/10'
          : 'bg-muted',
    },
    {
      type: 'complexity' as const,
      label: t('analytics:quality.complexity'),
      value: metrics.complexityScore !== undefined ? metrics.complexityScore.toFixed(1) : '-',
      color:
        metrics.complexityScore !== undefined
          ? metrics.complexityScore <= 10
            ? 'text-green-500'
            : metrics.complexityScore <= 20
              ? 'text-yellow-500'
              : 'text-red-500'
          : 'text-muted-foreground',
      bgColor:
        metrics.complexityScore !== undefined
          ? metrics.complexityScore <= 10
            ? 'bg-green-500/10'
            : metrics.complexityScore <= 20
              ? 'bg-yellow-500/10'
              : 'bg-red-500/10'
          : 'bg-muted',
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('analytics:quality.title')}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Grade Display */}
          <div className="flex flex-col items-center justify-center py-4">
            <span className="text-sm text-muted-foreground mb-2">
              {t('analytics:quality.grade')}
            </span>
            <Badge
              variant={getGradeVariant(metrics.qualityGrade)}
              className="text-3xl font-bold px-6 py-2"
              aria-label={`${t('analytics:quality.grade')}: ${metrics.qualityGrade}`}
            >
              {metrics.qualityGrade}
            </Badge>
            {metrics.qualityGrade === 'A' && (
              <div className="flex items-center gap-1 mt-2 text-green-500 text-sm">
                <CheckCircle className="h-4 w-4" aria-hidden="true" />
                {t('analytics:quality.excellent')}
              </div>
            )}
          </div>

          {/* Metric Grid */}
          <div className="grid grid-cols-2 gap-3">
            {metricItems.map((item) => (
              <div
                key={item.type}
                className={`p-3 rounded-lg ${item.bgColor}`}
                role="group"
                aria-label={item.label}
              >
                <div className="flex items-center gap-2 mb-1">
                  <MetricIcon type={item.type} className={`h-4 w-4 ${item.color}`} />
                  <span className="text-xs text-muted-foreground">{item.label}</span>
                </div>
                <span className={`text-lg font-semibold ${item.color}`}>{item.value}</span>
              </div>
            ))}
          </div>

          {/* Analyzed timestamp */}
          {metrics.analyzedAt && (
            <p className="text-xs text-muted-foreground text-center pt-2 border-t border-border">
              {t('analytics:quality.analyzedAt', {
                date: new Date(metrics.analyzedAt).toLocaleDateString(),
              })}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
