import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { useChartColors } from './utils/useChartColors';
import { useAnalyticsStore } from '../../stores/analytics-store';

// Intent types for token breakdown
export interface IntentBreakdownData {
  specId: string;
  promptTokens: number;
  systemTokens: number;
  contextTokens: number;
}

export interface IntentBreakdownChartProps {
  data?: IntentBreakdownData[];
  isLoading?: boolean;
}

// Format large token numbers for display
function formatTokens(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
  return value.toString();
}

export function IntentBreakdownChart({ data: propData, isLoading }: IntentBreakdownChartProps) {
  const { t } = useTranslation(['analytics']);
  const colors = useChartColors();
  const storeData = useAnalyticsStore((state) => state.data);

  // Color scheme: Blue for prompt, Green for system, Orange for context
  const intentColors = useMemo(() => ({
    prompt: colors.chart3,   // Blue
    system: colors.chart2,   // Green
    context: '#F97316'       // Orange (fixed color for consistency)
  }), [colors]);

  // Derive data from store if not provided as prop
  const chartData = useMemo(() => {
    if (propData) return propData;

    // If no prop data, derive from store conversations
    if (!storeData?.conversations || storeData.conversations.length === 0) {
      return [];
    }

    // Group by specId and estimate token distribution
    // Note: In real implementation, these would come from actual breakdown data
    // For now, we estimate based on typical distributions:
    // - ~20% prompt tokens (user input)
    // - ~15% system tokens (system prompts)
    // - ~65% context tokens (file context, MCP context)
    const specMap = new Map<string, IntentBreakdownData>();

    for (const conv of storeData.conversations) {
      const existing = specMap.get(conv.specId);
      const inputTokens = conv.tokens.input;

      // Estimate breakdown (in production, this would come from actual data)
      const promptTokens = Math.round(inputTokens * 0.20);
      const systemTokens = Math.round(inputTokens * 0.15);
      const contextTokens = inputTokens - promptTokens - systemTokens;

      if (existing) {
        existing.promptTokens += promptTokens;
        existing.systemTokens += systemTokens;
        existing.contextTokens += contextTokens;
      } else {
        specMap.set(conv.specId, {
          specId: conv.specId.slice(0, 12),
          promptTokens,
          systemTokens,
          contextTokens
        });
      }
    }

    return Array.from(specMap.values());
  }, [propData, storeData]);

  // Calculate totals for legend
  const totals = useMemo(() => {
    return chartData.reduce(
      (acc, item) => ({
        prompt: acc.prompt + item.promptTokens,
        system: acc.system + item.systemTokens,
        context: acc.context + item.contextTokens
      }),
      { prompt: 0, system: 0, context: 0 }
    );
  }, [chartData]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="h-5 w-48 bg-muted rounded animate-pulse" />
          <div className="h-4 w-64 bg-muted rounded animate-pulse mt-1" />
        </CardHeader>
        <CardContent>
          <div className="h-[300px] bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('analytics:intentBreakdown.title')}</CardTitle>
          <CardDescription>{t('analytics:intentBreakdown.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            {t('analytics:intentBreakdown.noData')}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    const total = payload.reduce((sum: number, entry: any) => sum + (entry.value || 0), 0);

    return (
      <div
        style={{
          backgroundColor: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: '8px',
          padding: '12px'
        }}
      >
        <p className="font-semibold mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            <span>{entry.name}:</span>
            <span className="font-mono">{formatTokens(entry.value)}</span>
            <span className="text-muted-foreground">
              ({((entry.value / total) * 100).toFixed(1)}%)
            </span>
          </div>
        ))}
        <div className="mt-2 pt-2 border-t text-sm">
          <span className="font-semibold">{t('analytics:intentBreakdown.total')}:</span>
          <span className="font-mono ml-2">{formatTokens(total)}</span>
        </div>
      </div>
    );
  };

  // Custom legend with totals
  const renderLegend = () => {
    const items = [
      { key: 'prompt', label: t('analytics:intentBreakdown.types.prompt'), color: intentColors.prompt, total: totals.prompt },
      { key: 'system', label: t('analytics:intentBreakdown.types.system'), color: intentColors.system, total: totals.system },
      { key: 'context', label: t('analytics:intentBreakdown.types.context'), color: intentColors.context, total: totals.context }
    ];

    return (
      <div className="flex flex-wrap justify-center gap-4 mt-4">
        {items.map((item) => (
          <div key={item.key} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: item.color }}
            />
            <span>{item.label}</span>
            <span className="text-muted-foreground font-mono">
              ({formatTokens(item.total)})
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('analytics:intentBreakdown.title')}</CardTitle>
        <CardDescription>{t('analytics:intentBreakdown.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis
                dataKey="specId"
                tick={{ fontSize: 12, fill: colors.muted }}
                tickLine={{ stroke: colors.border }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: colors.muted }}
                tickLine={{ stroke: colors.border }}
                tickFormatter={formatTokens}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar
                dataKey="promptTokens"
                stackId="tokens"
                fill={intentColors.prompt}
                name={t('analytics:intentBreakdown.types.prompt')}
              />
              <Bar
                dataKey="systemTokens"
                stackId="tokens"
                fill={intentColors.system}
                name={t('analytics:intentBreakdown.types.system')}
              />
              <Bar
                dataKey="contextTokens"
                stackId="tokens"
                fill={intentColors.context}
                name={t('analytics:intentBreakdown.types.context')}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
        {renderLegend()}
      </CardContent>
    </Card>
  );
}
