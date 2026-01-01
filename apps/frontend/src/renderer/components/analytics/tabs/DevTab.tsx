import { useTranslation } from 'react-i18next';
import { MetricCard } from '../shared/MetricCard';
import { DataTable } from '../shared/DataTable';
import { ArtifactsPanel } from '../artifacts/ArtifactsPanel';
import { formatCurrency, formatHours, formatPercent } from '../utils/formatters';
import { BarChart3, TrendingUp, Clock, CheckCircle, XCircle, Activity } from 'lucide-react';

interface Spec {
  id: string;
  name: string;
  status: string;
  cost: number;
  timeSaved: number;
  roi: number;
}

interface DevTabProps {
  data: {
    mySpecs: Spec[];
    totalCost: number;
    totalTimeSaved: number;
    successRate: number;
  };
  loading?: boolean;
  onSpecClick?: (spec: Spec) => void;
}

export function DevTab({ data, loading, onSpecClick }: DevTabProps) {
  const { t } = useTranslation(['analytics']);

  // Calculate derived metrics
  const totalSpecs = data.mySpecs.length;
  const completedSpecs = data.mySpecs.filter((s) => s.status === 'completed').length;
  const inProgressSpecs = data.mySpecs.filter((s) => s.status === 'in_progress').length;
  const avgCostPerSpec = totalSpecs > 0 ? data.totalCost / totalSpecs : 0;
  const avgTimeSavedPerSpec = totalSpecs > 0 ? data.totalTimeSaved / totalSpecs : 0;
  const positiveROISpecs = data.mySpecs.filter((s) => s.roi > 0).length;

  // Get top 5 specs by cost for chart
  const topSpecsByCost = [...data.mySpecs]
    .sort((a, b) => b.cost - a.cost)
    .slice(0, 5);
  const maxCost = Math.max(...topSpecsByCost.map((s) => s.cost), 0.01);

  const columns = [
    { key: 'name', header: 'dev.specName' },
    { key: 'status', header: 'dev.status', render: (row: Spec) => (
      <span className={`px-2 py-1 rounded text-xs ${
        row.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
        row.status === 'in_progress' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
        'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
      }`}>
        {row.status}
      </span>
    )},
    { key: 'cost', header: 'dev.cost', render: (row: Spec) => formatCurrency(row.cost) },
    { key: 'timeSaved', header: 'dev.timeSaved', render: (row: Spec) => formatHours(row.timeSaved) },
    { key: 'roi', header: 'dev.roi', render: (row: Spec) => (
      <span className={row.roi >= 0 ? 'text-green-600' : 'text-red-600'}>
        {formatPercent(row.roi)}
      </span>
    )},
  ];

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
          ))}
        </div>
        <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Primary metrics row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="dev.myCost"
          value={formatCurrency(data.totalCost)}
          subtitle={`${formatCurrency(avgCostPerSpec)} avg/spec`}
        />
        <MetricCard
          title="dev.timeSaved"
          value={formatHours(data.totalTimeSaved)}
          subtitle={`${formatHours(avgTimeSavedPerSpec)} avg/spec`}
          trend={{ value: data.totalTimeSaved > 0 ? 15 : 0, isPositive: data.totalTimeSaved > 0 }}
        />
        <MetricCard
          title="dev.successRate"
          value={formatPercent(data.successRate)}
          trend={{ value: data.successRate, isPositive: data.successRate >= 80 }}
        />
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">{t('dev.productivityMetrics', 'Productivity')}</p>
          <p className="text-2xl font-bold mt-1 text-blue-600">{totalSpecs}</p>
          <p className="text-xs text-gray-400 mt-1">{positiveROISpecs} with positive ROI</p>
        </div>
      </div>

      {/* Status overview and cost chart row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Status Overview */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="h-4 w-4 text-blue-500" />
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">Spec Status</h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Completed</span>
              </div>
              <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded text-sm font-bold">
                {completedSpecs}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-blue-500" />
                <span className="text-sm text-gray-600 dark:text-gray-400">In Progress</span>
              </div>
              <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-sm font-bold">
                {inProgressSpecs}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-purple-500" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Positive ROI</span>
              </div>
              <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded text-sm font-bold">
                {positiveROISpecs}
              </span>
            </div>
          </div>
        </div>

        {/* Cost by Spec Chart */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-4 w-4 text-purple-500" />
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">{t('dev.costBySpec', 'Cost by Spec')}</h3>
          </div>
          {topSpecsByCost.length === 0 ? (
            <div className="h-32 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <XCircle className="h-8 w-8 mx-auto mb-2" />
                <p>No specs with cost data yet</p>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {topSpecsByCost.map((spec, idx) => {
                const widthPercent = (spec.cost / maxCost) * 100;
                return (
                  <div key={`${spec.id}-${idx}`} className="flex items-center gap-3 group cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 p-1 rounded" onClick={() => onSpecClick?.(spec)}>
                    <div className="w-32 truncate text-sm text-gray-600 dark:text-gray-400" title={spec.name}>
                      {spec.name}
                    </div>
                    <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${spec.status === 'completed' ? 'bg-green-500' : 'bg-blue-500'}`}
                        style={{ width: `${Math.max(2, widthPercent)}%` }}
                      />
                    </div>
                    <div className="w-20 text-right text-sm font-medium text-gray-700 dark:text-gray-300">
                      {formatCurrency(spec.cost)}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* My specs table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
          {t('dev.mySpecs')}
        </h3>
        <DataTable
          columns={columns}
          data={data.mySpecs}
          loading={loading}
          onRowClick={onSpecClick}
          emptyMessage="dev.noSpecs"
        />
      </div>

      {/* Developer Artifacts - Code, Bug Fixes, Tests */}
      <ArtifactsPanel filterByTab="dev" title="Code Artifacts" />
    </div>
  );
}

export default DevTab;
