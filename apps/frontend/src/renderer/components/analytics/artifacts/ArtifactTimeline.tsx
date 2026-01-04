import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Calendar, TrendingUp, DollarSign, Hash } from 'lucide-react';
import type { ArtifactTimelineResponse, ArtifactTimelineEntry } from '../../../../shared/types/analytics-v2';
import { formatCurrency } from '../utils/formatters';

interface ArtifactTimelineProps {
  data: ArtifactTimelineResponse;
  isLoading?: boolean;
  onGranularityChange?: (granularity: 'hour' | 'day' | 'week') => void;
  className?: string;
}

// Colors for different artifact types in stacked bars
const TYPE_COLORS: Record<string, string> = {
  roadmap_feature: '#3b82f6', // blue
  security_issue: '#ef4444', // red
  ideation_item: '#eab308', // yellow
  idea: '#f59e0b', // amber
  recommendation: '#fbbf24', // yellow-400
  diagram: '#a855f7', // purple
  code_example: '#06b6d4', // cyan
  documentation: '#22d3ee', // cyan-400
  insight: '#10b981', // emerald
  other: '#6b7280', // gray
};

// Format date for display based on granularity
function formatDateLabel(dateStr: string, granularity: string): string {
  const date = new Date(dateStr);

  if (granularity === 'hour') {
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
    });
  } else if (granularity === 'week') {
    return `Week ${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
  } else {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  }
}

// Custom tooltip for the chart
function CustomTooltip({
  active,
  payload,
  label,
  granularity,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
  granularity: string;
}) {
  if (!active || !payload || !label) return null;

  const countEntry = payload.find((p) => p.name === 'count');
  const valueEntry = payload.find((p) => p.name === 'value_usd');

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-lg">
      <p className="text-gray-400 text-xs mb-2">{formatDateLabel(label, granularity)}</p>
      <div className="space-y-1">
        {countEntry && (
          <div className="flex items-center gap-2 text-sm">
            <Hash className="h-3 w-3 text-blue-400" />
            <span className="text-gray-300">Count:</span>
            <span className="text-white font-medium">{countEntry.value}</span>
          </div>
        )}
        {valueEntry && (
          <div className="flex items-center gap-2 text-sm">
            <DollarSign className="h-3 w-3 text-emerald-400" />
            <span className="text-gray-300">Value:</span>
            <span className="text-emerald-400 font-medium">{formatCurrency(valueEntry.value)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function ArtifactTimeline({
  data,
  isLoading,
  onGranularityChange,
  className = '',
}: ArtifactTimelineProps) {
  const { t } = useTranslation(['analytics']);
  const [showValue, setShowValue] = useState(true);
  const [granularity, setGranularity] = useState<'hour' | 'day' | 'week'>(
    (data.granularity as 'hour' | 'day' | 'week') || 'day'
  );

  const handleGranularityChange = (newGranularity: 'hour' | 'day' | 'week') => {
    setGranularity(newGranularity);
    onGranularityChange?.(newGranularity);
  };

  // Transform data for chart
  const chartData = data.timeline.map((entry) => ({
    date: entry.date,
    count: entry.count,
    value_usd: entry.value_usd,
    label: formatDateLabel(entry.date, granularity),
  }));

  if (isLoading) {
    return (
      <div className={`bg-[#1e1e2e] rounded-lg p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="h-64 bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  if (!data.timeline || data.timeline.length === 0) {
    return (
      <div className={`bg-[#1e1e2e] rounded-lg p-6 ${className}`}>
        <h3 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-blue-400" />
          {t('analytics:artifacts.timeline.title')}
        </h3>
        <p className="text-gray-400 text-sm">{t('analytics:common.noData')}</p>
      </div>
    );
  }

  return (
    <div className={`bg-[#1e1e2e] rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-blue-400" />
          {t('analytics:artifacts.timeline.title')}
        </h3>

        <div className="flex items-center gap-4">
          {/* Summary stats */}
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1 text-gray-400">
              <Hash className="h-4 w-4" />
              <span className="text-white font-medium">{data.total_count}</span>
              <span>artifacts</span>
            </div>
            <div className="flex items-center gap-1 text-emerald-400">
              <DollarSign className="h-4 w-4" />
              <span className="font-medium">{formatCurrency(data.total_value)}</span>
            </div>
          </div>

          {/* Granularity selector */}
          <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
            {(['hour', 'day', 'week'] as const).map((g) => (
              <button
                key={g}
                onClick={() => handleGranularityChange(g)}
                className={`px-3 py-1 text-xs rounded transition-colors ${
                  granularity === g
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {t(`analytics:artifacts.timeline.${g}`)}
              </button>
            ))}
          </div>

          {/* Value/Count toggle */}
          <button
            onClick={() => setShowValue(!showValue)}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              showValue
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-blue-500/20 text-blue-400'
            }`}
          >
            {showValue
              ? t('analytics:artifacts.timeline.value')
              : t('analytics:artifacts.timeline.count')}
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="label"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              axisLine={{ stroke: '#374151' }}
              tickLine={{ stroke: '#374151' }}
            />
            <YAxis
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              axisLine={{ stroke: '#374151' }}
              tickLine={{ stroke: '#374151' }}
              tickFormatter={(value) =>
                showValue ? `$${value}` : value.toString()
              }
            />
            <Tooltip
              content={
                <CustomTooltip
                  granularity={granularity}
                />
              }
            />
            <Bar
              dataKey={showValue ? 'value_usd' : 'count'}
              name={showValue ? 'value_usd' : 'count'}
              fill={showValue ? '#10b981' : '#3b82f6'}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
