import { useTranslation } from 'react-i18next';
import { MetricCard } from '../shared/MetricCard';
import { DataTable } from '../shared/DataTable';
import { formatCurrency, formatHours, formatPercent } from '../utils/formatters';

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

  return (
    <div className="space-y-6">
      {/* Personal metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          title="dev.myCost"
          value={formatCurrency(data.totalCost)}
        />
        <MetricCard
          title="dev.timeSaved"
          value={formatHours(data.totalTimeSaved)}
        />
        <MetricCard
          title="dev.successRate"
          value={formatPercent(data.successRate)}
          trend={{ value: data.successRate, isPositive: data.successRate >= 80 }}
        />
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
    </div>
  );
}

export default DevTab;
