/**
 * Artifact Breakdown Card
 * =======================
 *
 * Displays artifact value breakdown by type and role.
 * Uses ROI Engine API to fetch value breakdown data.
 *
 * Phase M3: Artifact Visualization Component
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  PieChart,
  BarChart3,
  DollarSign,
  FileCode,
  Users,
  TrendingUp,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import * as roiEngineApi from '../../../services/roi-engine-api';
import type { ValueBreakdownResponse, ValueBreakdownItem } from '../../../services/roi-engine-api';

interface ArtifactBreakdownCardProps {
  projectDir: string;
  specId?: string;
  className?: string;
}

// Role colors for consistent styling
const ROLE_COLORS: Record<string, string> = {
  architect: 'bg-purple-500',
  developer: 'bg-blue-500',
  qa: 'bg-green-500',
  tech_lead: 'bg-indigo-500',
  pm: 'bg-amber-500',
  devops: 'bg-rose-500',
};

// Type colors for consistent styling
const TYPE_COLORS: Record<string, string> = {
  diagram: 'bg-blue-400',
  spec_document: 'bg-purple-400',
  implementation_plan: 'bg-indigo-400',
  code_example: 'bg-green-400',
  test_case: 'bg-emerald-400',
  security_finding: 'bg-red-400',
  architecture_insight: 'bg-violet-400',
  qa_verdict: 'bg-teal-400',
  default: 'bg-gray-400',
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function BreakdownBar({
  items,
  colorMap,
  maxItems = 5,
}: {
  items: ValueBreakdownItem[];
  colorMap: Record<string, string>;
  maxItems?: number;
}) {
  const topItems = items.slice(0, maxItems);
  const othersValue = items.slice(maxItems).reduce((sum, item) => sum + item.value, 0);
  const othersPercentage = items.slice(maxItems).reduce((sum, item) => sum + item.percentage, 0);

  return (
    <div className="space-y-2">
      {/* Stacked bar */}
      <div className="h-4 flex rounded-full overflow-hidden bg-gray-200 dark:bg-gray-700">
        {topItems.map((item, index) => (
          <div
            key={item.category}
            className={`${colorMap[item.category.toLowerCase()] || colorMap.default || 'bg-gray-400'} transition-all duration-300`}
            style={{ width: `${item.percentage}%` }}
            title={`${item.category}: ${formatCurrency(item.value)} (${item.percentage.toFixed(1)}%)`}
          />
        ))}
        {othersValue > 0 && (
          <div
            className="bg-gray-400"
            style={{ width: `${othersPercentage}%` }}
            title={`Others: ${formatCurrency(othersValue)} (${othersPercentage.toFixed(1)}%)`}
          />
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-2 text-xs">
        {topItems.map((item) => (
          <div key={item.category} className="flex items-center gap-1">
            <div
              className={`w-2 h-2 rounded-full ${colorMap[item.category.toLowerCase()] || colorMap.default || 'bg-gray-400'}`}
            />
            <span className="text-gray-600 dark:text-gray-400 capitalize">
              {item.category.replace(/_/g, ' ')}
            </span>
            <span className="text-gray-500 dark:text-gray-500">
              ({item.percentage.toFixed(0)}%)
            </span>
          </div>
        ))}
        {othersValue > 0 && (
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-gray-400" />
            <span className="text-gray-600 dark:text-gray-400">Others</span>
            <span className="text-gray-500 dark:text-gray-500">
              ({othersPercentage.toFixed(0)}%)
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export function ArtifactBreakdownCard({
  projectDir,
  specId,
  className = '',
}: ArtifactBreakdownCardProps) {
  const { t } = useTranslation(['analytics']);
  const [data, setData] = useState<ValueBreakdownResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'role' | 'type'>('role');

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
          <span className="ml-2 text-gray-500 dark:text-gray-400">Loading breakdown...</span>
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

  if (!data) {
    return null;
  }

  const activeItems = activeTab === 'role' ? data.by_role : data.by_type;
  const colorMap = activeTab === 'role' ? ROLE_COLORS : TYPE_COLORS;

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('analytics:artifacts.breakdown.title', 'Artifact Value Breakdown')}
          </h3>
        </div>

        {/* Tabs */}
        <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('role')}
            className={`flex items-center gap-1 px-3 py-1 rounded text-sm font-medium transition-colors ${
              activeTab === 'role'
                ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <Users className="h-4 w-4" />
            {t('analytics:artifacts.breakdown.byRole', 'By Role')}
          </button>
          <button
            onClick={() => setActiveTab('type')}
            className={`flex items-center gap-1 px-3 py-1 rounded text-sm font-medium transition-colors ${
              activeTab === 'type'
                ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <FileCode className="h-4 w-4" />
            {t('analytics:artifacts.breakdown.byType', 'By Type')}
          </button>
        </div>
      </div>

      {/* Total Value */}
      <div className="flex items-center gap-2 mb-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <DollarSign className="h-5 w-5 text-green-500" />
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {t('analytics:artifacts.breakdown.totalValue', 'Total Value')}:
        </span>
        <span className="text-lg font-bold text-gray-900 dark:text-white">
          {formatCurrency(data.total_value)}
        </span>
      </div>

      {/* Breakdown Bar */}
      {activeItems.length > 0 ? (
        <BreakdownBar items={activeItems} colorMap={colorMap} maxItems={5} />
      ) : (
        <div className="text-center py-4 text-gray-500 dark:text-gray-400">
          {t('analytics:artifacts.breakdown.noData', 'No artifact data available')}
        </div>
      )}

      {/* Top Items List */}
      {activeItems.length > 0 && (
        <div className="mt-4 space-y-2">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {activeTab === 'role'
              ? t('analytics:artifacts.breakdown.topRoles', 'Top Roles')
              : t('analytics:artifacts.breakdown.topTypes', 'Top Artifact Types')}
          </h4>
          <div className="space-y-1">
            {activeItems.slice(0, 5).map((item) => (
              <div
                key={item.category}
                className="flex items-center justify-between py-1 text-sm"
              >
                <div className="flex items-center gap-2">
                  <div
                    className={`w-3 h-3 rounded-full ${colorMap[item.category.toLowerCase()] || colorMap.default || 'bg-gray-400'}`}
                  />
                  <span className="text-gray-700 dark:text-gray-300 capitalize">
                    {item.category.replace(/_/g, ' ')}
                  </span>
                  <span className="text-gray-400 dark:text-gray-500">
                    ({item.count} {item.count === 1 ? 'artifact' : 'artifacts'})
                  </span>
                </div>
                <span className="font-medium text-gray-900 dark:text-white">
                  {formatCurrency(item.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default ArtifactBreakdownCard;
