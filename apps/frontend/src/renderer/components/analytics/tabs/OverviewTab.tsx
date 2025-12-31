import { useTranslation } from 'react-i18next';
import { MetricCard } from '../shared/MetricCard';
import { formatCurrency, formatTokens, formatHours, formatPercent } from '../utils/formatters';

interface OverviewTabProps {
  data: {
    totalCost: number;
    totalTokens: number;
    hoursSaved: number;
    avgROI: number;
    specsCompleted: number;
    specsInProgress: number;
  };
  loading?: boolean;
}

export function OverviewTab({ data, loading }: OverviewTabProps) {
  const { t } = useTranslation(['analytics']);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top metrics row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="overview.totalCost"
          value={formatCurrency(data.totalCost)}
          trend={{ value: 0, isPositive: true }}
        />
        <MetricCard
          title="overview.totalTokens"
          value={formatTokens(data.totalTokens)}
        />
        <MetricCard
          title="overview.hoursSaved"
          value={formatHours(data.hoursSaved)}
          trend={{ value: 15, isPositive: true }}
        />
        <MetricCard
          title="overview.avgROI"
          value={formatPercent(data.avgROI)}
          trend={{ value: data.avgROI > 0 ? 5 : -5, isPositive: data.avgROI > 0 }}
        />
      </div>

      {/* Status quick view */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            {t('overview.statusQuick')}
          </h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">{t('overview.specsCompleted')}</span>
              <span className="font-bold text-green-600">{data.specsCompleted}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">{t('overview.inProgress')}</span>
              <span className="font-bold text-blue-600">{data.specsInProgress}</span>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            {t('overview.costVsValue')}
          </h3>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500"
              style={{ width: `${Math.min(100, Math.max(0, data.avgROI))}%` }}
            />
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Net: {formatCurrency(data.hoursSaved * 50 - data.totalCost)}
          </p>
        </div>
      </div>
    </div>
  );
}

export default OverviewTab;
