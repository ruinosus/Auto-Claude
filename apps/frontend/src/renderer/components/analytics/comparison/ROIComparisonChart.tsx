import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  TooltipProps,
} from 'recharts';
import { Trophy, TrendingUp, TrendingDown, Award } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card';
import { Badge } from '../../ui/badge';
import { formatCurrency } from '../utils/formatters';

/**
 * Market benchmark thresholds for reference lines
 */
const MARKET_BENCHMARKS = {
  average: 370,
  topPerformers: 1030,
  median: 250,
  lowPerformers: 100,
};

/**
 * ROI comparison result for a project
 */
export interface ROIComparisonData {
  projectId: string;
  projectName?: string;
  roiPercentage: number;
  costPerDollarValue: number;
  breakEvenDays: number | null;
  vsMarketAvg: number;
  percentile: number;
  marketPosition: 'top_performer' | 'above_average' | 'average' | 'below_average' | 'needs_improvement';
  totalValueUsd: number;
  totalCostUsd: number;
  netValueUsd: number;
}

export interface ROIComparisonChartProps {
  /** Comparison data for projects */
  data: ROIComparisonData[];
  /** Optional title override */
  title?: string;
  /** Optional description override */
  description?: string;
  /** Show market benchmark reference lines */
  showBenchmarks?: boolean;
  /** Highlight the best performer */
  highlightBest?: boolean;
  /** Maximum projects to show (sorted by ROI) */
  maxProjects?: number;
  /** Chart height in pixels */
  height?: number;
  /** Loading state */
  isLoading?: boolean;
}

/**
 * Get color for market position
 */
function getPositionColor(position: ROIComparisonData['marketPosition']): string {
  switch (position) {
    case 'top_performer':
      return 'hsl(var(--chart-1))'; // Primary green
    case 'above_average':
      return 'hsl(var(--chart-2))'; // Blue
    case 'average':
      return 'hsl(var(--chart-3))'; // Yellow
    case 'below_average':
      return 'hsl(var(--chart-4))'; // Orange
    case 'needs_improvement':
      return 'hsl(var(--chart-5))'; // Red
    default:
      return 'hsl(var(--muted-foreground))';
  }
}

/**
 * Get badge variant for market position
 */
function getPositionBadgeVariant(
  position: ROIComparisonData['marketPosition']
): 'default' | 'secondary' | 'destructive' | 'outline' | 'success' {
  switch (position) {
    case 'top_performer':
      return 'success';
    case 'above_average':
      return 'default';
    case 'average':
      return 'secondary';
    case 'below_average':
    case 'needs_improvement':
      return 'destructive';
    default:
      return 'outline';
  }
}

/**
 * Custom tooltip for the chart
 */
function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  const { t } = useTranslation(['analytics']);

  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0].payload as ROIComparisonData;

  return (
    <div className="bg-popover border border-border rounded-lg p-3 shadow-lg">
      <p className="font-medium text-sm mb-2">{data.projectName || data.projectId}</p>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">{t('analytics:roiComparison.roi')}:</span>
          <span className="font-medium">{data.roiPercentage.toFixed(0)}%</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">{t('analytics:roiComparison.vsMarket')}:</span>
          <span className={data.vsMarketAvg >= 0 ? 'text-green-500' : 'text-red-500'}>
            {data.vsMarketAvg >= 0 ? '+' : ''}{data.vsMarketAvg.toFixed(1)}%
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">{t('analytics:roiComparison.percentile')}:</span>
          <span className="font-medium">{t('analytics:roiComparison.top', { value: data.percentile })}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">{t('analytics:roiComparison.netValue')}:</span>
          <span className={data.netValueUsd >= 0 ? 'text-green-500' : 'text-red-500'}>
            {formatCurrency(data.netValueUsd, 2)}
          </span>
        </div>
        {data.breakEvenDays !== null && (
          <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">{t('analytics:roiComparison.breakEven')}:</span>
            <span className="font-medium">
              {data.breakEvenDays === 0
                ? t('analytics:roiComparison.profitable')
                : t('analytics:roiComparison.days', { count: data.breakEvenDays })}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Percentile indicator badge
 */
function PercentileIndicator({ percentile }: { percentile: number }) {
  const { t } = useTranslation(['analytics']);

  return (
    <div className="flex items-center gap-2">
      {percentile <= 5 && <Trophy className="h-4 w-4 text-yellow-500" aria-hidden="true" />}
      {percentile <= 25 && percentile > 5 && <Award className="h-4 w-4 text-blue-500" aria-hidden="true" />}
      <span className="text-sm font-medium">
        {t('analytics:roiComparison.top', { value: percentile })}
      </span>
    </div>
  );
}

/**
 * ROI Comparison Chart Component
 *
 * Displays a bar chart comparing ROI across projects with market benchmark reference lines.
 * Shows percentile rankings and market position indicators.
 */
export function ROIComparisonChart({
  data,
  title,
  description,
  showBenchmarks = true,
  highlightBest = true,
  maxProjects = 10,
  height = 400,
  isLoading = false,
}: ROIComparisonChartProps) {
  const { t } = useTranslation(['analytics']);

  // Sort and limit data
  const chartData = useMemo(() => {
    const sorted = [...data].sort((a, b) => b.roiPercentage - a.roiPercentage);
    return sorted.slice(0, maxProjects).map((item) => ({
      ...item,
      name: item.projectName || item.projectId.slice(0, 12),
    }));
  }, [data, maxProjects]);

  // Find best performer
  const bestPerformer = useMemo(() => {
    if (chartData.length === 0) return null;
    return chartData[0];
  }, [chartData]);

  // Calculate chart domain
  const maxRoi = useMemo(() => {
    if (chartData.length === 0) return MARKET_BENCHMARKS.topPerformers;
    const maxData = Math.max(...chartData.map((d) => d.roiPercentage));
    return Math.max(maxData * 1.1, MARKET_BENCHMARKS.average * 1.2);
  }, [chartData]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title || t('analytics:roiComparison.title')}</CardTitle>
          <CardDescription>{description || t('analytics:roiComparison.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] flex items-center justify-center">
            <div className="animate-pulse text-muted-foreground">
              {t('analytics:common.loading')}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title || t('analytics:roiComparison.title')}</CardTitle>
          <CardDescription>{description || t('analytics:roiComparison.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] flex items-center justify-center text-muted-foreground">
            {t('analytics:roiComparison.noData')}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{title || t('analytics:roiComparison.title')}</CardTitle>
            <CardDescription>
              {description || t('analytics:roiComparison.description')}
            </CardDescription>
          </div>
          {bestPerformer && highlightBest && (
            <div className="flex items-center gap-2">
              <PercentileIndicator percentile={bestPerformer.percentile} />
              <Badge variant={getPositionBadgeVariant(bestPerformer.marketPosition)}>
                {t(`analytics:roiComparison.positions.${bestPerformer.marketPosition}`)}
              </Badge>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 20, right: 30, left: 80, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              type="number"
              domain={[0, maxRoi]}
              tickFormatter={(value) => `${value}%`}
              className="text-xs fill-muted-foreground"
            />
            <YAxis
              type="category"
              dataKey="name"
              width={75}
              className="text-xs fill-muted-foreground"
              tick={{ fontSize: 11 }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              verticalAlign="top"
              height={36}
              formatter={(value) => {
                if (value === 'roiPercentage') return t('analytics:roiComparison.roi');
                return value;
              }}
            />

            {/* Market benchmark reference lines */}
            {showBenchmarks && (
              <>
                <ReferenceLine
                  x={MARKET_BENCHMARKS.average}
                  stroke="hsl(var(--warning))"
                  strokeDasharray="5 5"
                  label={{
                    value: t('analytics:roiComparison.marketAverage'),
                    position: 'top',
                    fill: 'hsl(var(--warning))',
                    fontSize: 10,
                  }}
                />
                <ReferenceLine
                  x={MARKET_BENCHMARKS.topPerformers}
                  stroke="hsl(var(--success))"
                  strokeDasharray="5 5"
                  label={{
                    value: t('analytics:roiComparison.topPerformers'),
                    position: 'top',
                    fill: 'hsl(var(--success))',
                    fontSize: 10,
                  }}
                />
              </>
            )}

            <Bar
              dataKey="roiPercentage"
              name="roiPercentage"
              radius={[0, 4, 4, 0]}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={getPositionColor(entry.marketPosition)}
                  opacity={highlightBest && index === 0 ? 1 : 0.8}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Market position legend */}
        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex flex-wrap gap-4 justify-center">
            {[
              { position: 'top_performer', icon: Trophy, color: 'text-green-500' },
              { position: 'above_average', icon: TrendingUp, color: 'text-blue-500' },
              { position: 'average', icon: null, color: 'text-yellow-500' },
              { position: 'below_average', icon: TrendingDown, color: 'text-orange-500' },
            ].map(({ position, icon: Icon, color }) => (
              <div key={position} className="flex items-center gap-1.5 text-xs">
                {Icon && <Icon className={`h-3.5 w-3.5 ${color}`} aria-hidden="true" />}
                <span
                  className="w-3 h-3 rounded-sm"
                  style={{ backgroundColor: getPositionColor(position as ROIComparisonData['marketPosition']) }}
                  aria-hidden="true"
                />
                <span className="text-muted-foreground">
                  {t(`analytics:roiComparison.positions.${position}`)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Summary stats */}
        {chartData.length > 1 && (
          <div className="mt-4 grid grid-cols-3 gap-4 text-center">
            <div className="p-3 bg-muted/30 rounded-lg">
              <div className="text-2xl font-bold text-green-500">
                {chartData.filter((d) => d.roiPercentage >= MARKET_BENCHMARKS.average).length}
              </div>
              <div className="text-xs text-muted-foreground">
                {t('analytics:roiComparison.aboveAverage')}
              </div>
            </div>
            <div className="p-3 bg-muted/30 rounded-lg">
              <div className="text-2xl font-bold">
                {Math.round(chartData.reduce((sum, d) => sum + d.roiPercentage, 0) / chartData.length)}%
              </div>
              <div className="text-xs text-muted-foreground">
                {t('analytics:roiComparison.avgRoi')}
              </div>
            </div>
            <div className="p-3 bg-muted/30 rounded-lg">
              <div className="text-2xl font-bold text-blue-500">
                {formatCurrency(chartData.reduce((sum, d) => sum + d.netValueUsd, 0), 0)}
              </div>
              <div className="text-xs text-muted-foreground">
                {t('analytics:roiComparison.totalNetValue')}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default ROIComparisonChart;
