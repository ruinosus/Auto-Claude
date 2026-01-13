/**
 * Role Distribution Chart
 * =======================
 *
 * Pie/donut chart showing artifact value distribution by role.
 * Uses ROI Engine API to fetch value breakdown data.
 *
 * Phase M3: Artifact Visualization Component
 */

import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Users,
  AlertCircle,
  Loader2,
  HardHat,
  Code2,
  TestTube,
  Settings,
  Briefcase,
  Server,
} from 'lucide-react';
import * as roiEngineApi from '../../../services/roi-engine-api';
import type { ValueBreakdownResponse, ValueBreakdownItem, Role } from '../../../services/roi-engine-api';

interface RoleDistributionChartProps {
  projectDir: string;
  specId?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showLegend?: boolean;
}

// Role configuration
const ROLE_CONFIG: Record<string, {
  color: string;
  bgColor: string;
  textColor: string;
  icon: React.ReactNode;
  label: string;
}> = {
  architect: {
    color: '#8B5CF6', // violet-500
    bgColor: 'bg-violet-500',
    textColor: 'text-violet-500',
    icon: <HardHat className="h-4 w-4" />,
    label: 'Architect',
  },
  developer: {
    color: '#3B82F6', // blue-500
    bgColor: 'bg-blue-500',
    textColor: 'text-blue-500',
    icon: <Code2 className="h-4 w-4" />,
    label: 'Developer',
  },
  qa: {
    color: '#10B981', // emerald-500
    bgColor: 'bg-emerald-500',
    textColor: 'text-emerald-500',
    icon: <TestTube className="h-4 w-4" />,
    label: 'QA',
  },
  tech_lead: {
    color: '#6366F1', // indigo-500
    bgColor: 'bg-indigo-500',
    textColor: 'text-indigo-500',
    icon: <Settings className="h-4 w-4" />,
    label: 'Tech Lead',
  },
  pm: {
    color: '#F59E0B', // amber-500
    bgColor: 'bg-amber-500',
    textColor: 'text-amber-500',
    icon: <Briefcase className="h-4 w-4" />,
    label: 'PM',
  },
  devops: {
    color: '#EF4444', // red-500
    bgColor: 'bg-red-500',
    textColor: 'text-red-500',
    icon: <Server className="h-4 w-4" />,
    label: 'DevOps',
  },
};

const SIZE_CONFIG = {
  sm: { width: 120, strokeWidth: 16 },
  md: { width: 160, strokeWidth: 20 },
  lg: { width: 200, strokeWidth: 24 },
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function DonutChart({
  items,
  size = 'md',
  totalValue,
}: {
  items: ValueBreakdownItem[];
  size: 'sm' | 'md' | 'lg';
  totalValue: number;
}) {
  const { width, strokeWidth } = SIZE_CONFIG[size];
  const radius = (width - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = width / 2;

  // Calculate segments
  const segments = useMemo(() => {
    let currentAngle = -90; // Start from top
    return items.map((item) => {
      const angle = (item.percentage / 100) * 360;
      const startAngle = currentAngle;
      currentAngle += angle;
      return {
        ...item,
        startAngle,
        angle,
        color: ROLE_CONFIG[item.category.toLowerCase()]?.color || '#9CA3AF',
      };
    });
  }, [items]);

  return (
    <div className="relative" style={{ width, height: width }}>
      <svg width={width} height={width} viewBox={`0 0 ${width} ${width}`}>
        {/* Background circle */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-gray-200 dark:text-gray-700"
        />

        {/* Segments */}
        {segments.map((segment, index) => {
          const dashArray = (segment.percentage / 100) * circumference;
          const dashOffset = segments
            .slice(0, index)
            .reduce((acc, s) => acc - (s.percentage / 100) * circumference, 0);

          return (
            <circle
              key={segment.category}
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke={segment.color}
              strokeWidth={strokeWidth}
              strokeDasharray={`${dashArray} ${circumference - dashArray}`}
              strokeDashoffset={dashOffset}
              strokeLinecap="round"
              transform={`rotate(-90 ${center} ${center})`}
              className="transition-all duration-500"
            >
              <title>
                {segment.category}: {formatCurrency(segment.value)} ({segment.percentage.toFixed(1)}%)
              </title>
            </circle>
          );
        })}
      </svg>

      {/* Center label */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xs text-gray-500 dark:text-gray-400">Total</span>
        <span className="text-lg font-bold text-gray-900 dark:text-white">
          {formatCurrency(totalValue)}
        </span>
      </div>
    </div>
  );
}

export function RoleDistributionChart({
  projectDir,
  specId,
  className = '',
  size = 'md',
  showLegend = true,
}: RoleDistributionChartProps) {
  const { t } = useTranslation(['analytics']);
  const [data, setData] = useState<ValueBreakdownResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        const response = await roiEngineApi.getValueBreakdown({
          project_dir: projectDir,
          spec_id: specId,
        });
        setData(response);
      } catch (err) {
        console.error('Failed to fetch value breakdown:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch data');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [projectDir, specId]);

  if (loading) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
          <span className="ml-2 text-gray-500 dark:text-gray-400">Loading chart...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
        <div className="flex items-center gap-2 text-red-500">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  if (!data || data.by_role.length === 0) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
        <div className="flex items-center gap-2 mb-4">
          <Users className="h-5 w-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('analytics:artifacts.roleDistribution.title', 'Value by Role')}
          </h3>
        </div>
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          {t('analytics:artifacts.roleDistribution.noData', 'No role data available')}
        </div>
      </div>
    );
  }

  // Sort by value descending
  const sortedRoles = [...data.by_role].sort((a, b) => b.value - a.value);

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Users className="h-5 w-5 text-blue-500" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('analytics:artifacts.roleDistribution.title', 'Value by Role')}
        </h3>
      </div>

      {/* Chart and Legend */}
      <div className={`flex ${showLegend ? 'flex-col sm:flex-row' : ''} items-center justify-center gap-6`}>
        {/* Donut Chart */}
        <DonutChart items={sortedRoles} size={size} totalValue={data.total_value} />

        {/* Legend */}
        {showLegend && (
          <div className="flex flex-col gap-2">
            {sortedRoles.map((role) => {
              const config = ROLE_CONFIG[role.category.toLowerCase()];
              return (
                <div key={role.category} className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${config?.bgColor || 'bg-gray-400'}`} />
                  <div className="flex items-center gap-1 min-w-[100px]">
                    {config?.icon}
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      {config?.label || role.category}
                    </span>
                  </div>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatCurrency(role.value)}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    ({role.percentage.toFixed(0)}%)
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          {sortedRoles.slice(0, 4).map((role) => {
            const config = ROLE_CONFIG[role.category.toLowerCase()];
            return (
              <div key={role.category} className="px-2">
                <div className={`text-2xl font-bold ${config?.textColor || 'text-gray-500'}`}>
                  {role.count}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {config?.label || role.category} artifacts
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default RoleDistributionChart;
