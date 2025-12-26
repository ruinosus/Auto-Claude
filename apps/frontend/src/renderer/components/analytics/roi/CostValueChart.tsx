import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis, Cell, ReferenceLine } from 'recharts';
import { useChartColors } from '../utils/useChartColors';
import type { SpecROIWithMetrics } from '../../../../shared/types/roi';

export interface CostValueChartProps {
  specs: SpecROIWithMetrics[];
  isLoading?: boolean;
}

export function CostValueChart({ specs, isLoading }: CostValueChartProps) {
  const { t } = useTranslation(['analytics']);
  const colors = useChartColors();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="h-5 w-40 bg-muted rounded animate-pulse" />
          <div className="h-4 w-56 bg-muted rounded animate-pulse mt-1" />
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
          <CardTitle>{t('analytics:roi.costValue.title')}</CardTitle>
          <CardDescription>{t('analytics:roi.costValue.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            {t('analytics:roi.costValue.noData')}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Prepare data - actual cost vs estimated manual cost
  const chartData = specs.map((spec) => ({
    x: spec.actualCost,
    y: spec.metrics.estimatedManualCost,
    z: spec.linesAdded + spec.linesRemoved, // bubble size based on lines changed
    name: spec.specId.slice(0, 12),
    savings: spec.metrics.costSavings,
    passed: spec.qaPassed,
  }));

  // Calculate max for axis domain
  const maxValue = Math.max(
    ...chartData.map(d => Math.max(d.x, d.y)),
    10 // minimum max value
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('analytics:roi.costValue.title')}</CardTitle>
        <CardDescription>{t('analytics:roi.costValue.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis
                type="number"
                dataKey="x"
                name={t('analytics:roi.costValue.actualCost')}
                tick={{ fontSize: 12, fill: colors.muted }}
                tickFormatter={(value) => `$${value.toFixed(0)}`}
                domain={[0, maxValue * 1.1]}
              />
              <YAxis
                type="number"
                dataKey="y"
                name={t('analytics:roi.costValue.estimatedCost')}
                tick={{ fontSize: 12, fill: colors.muted }}
                tickFormatter={(value) => `$${value.toFixed(0)}`}
                domain={[0, maxValue * 1.1]}
              />
              <ZAxis type="number" dataKey="z" range={[50, 400]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: colors.card,
                  borderColor: colors.border,
                  borderRadius: '6px'
                }}
                formatter={(value: number, name: string) => [`$${value.toFixed(2)}`, name]}
              />
              {/* Reference line where cost = value (break-even) */}
              <ReferenceLine
                segment={[{ x: 0, y: 0 }, { x: maxValue, y: maxValue }]}
                stroke={colors.muted}
                strokeDasharray="5 5"
              />
              <Scatter data={chartData}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.savings > 0 ? colors.chart2 : colors.chart5}
                    opacity={entry.passed ? 1 : 0.5}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
        <p className="text-xs text-muted-foreground text-center mt-2">
          {t('analytics:roi.costValue.hint')}
        </p>
      </CardContent>
    </Card>
  );
}
