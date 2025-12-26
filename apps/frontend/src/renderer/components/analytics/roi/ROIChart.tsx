import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useChartColors } from '../utils/useChartColors';
import type { SpecROIWithMetrics } from '../../../../shared/types/roi';

export interface ROIChartProps {
  specs: SpecROIWithMetrics[];
  isLoading?: boolean;
}

export function ROIChart({ specs, isLoading }: ROIChartProps) {
  const { t } = useTranslation(['analytics']);
  const colors = useChartColors();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="h-5 w-32 bg-muted rounded animate-pulse" />
          <div className="h-4 w-48 bg-muted rounded animate-pulse mt-1" />
        </CardHeader>
        <CardContent>
          <div className="h-[300px] bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  if (specs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('analytics:roi.chart.title')}</CardTitle>
          <CardDescription>{t('analytics:roi.chart.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            {t('analytics:roi.chart.noData')}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Prepare data - last 10 specs, sorted by date
  const chartData = specs
    .slice(0, 10)
    .reverse()
    .map((spec) => ({
      name: spec.specId.slice(0, 12),
      roi: spec.metrics.roiPercentage,
      fullId: spec.specId,
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('analytics:roi.chart.title')}</CardTitle>
        <CardDescription>{t('analytics:roi.chart.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 12, fill: colors.muted }}
                tickLine={{ stroke: colors.border }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: colors.muted }}
                tickLine={{ stroke: colors.border }}
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: colors.card,
                  borderColor: colors.border,
                  borderRadius: '6px'
                }}
                formatter={(value: number) => [`${value.toFixed(1)}%`, t('analytics:roi.chart.roiLabel')]}
                labelFormatter={(label) => `Spec: ${label}`}
              />
              <Bar dataKey="roi" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.roi >= 0 ? colors.chart2 : colors.chart5}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
