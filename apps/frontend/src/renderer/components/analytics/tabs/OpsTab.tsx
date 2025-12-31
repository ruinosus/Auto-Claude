import { useTranslation } from 'react-i18next';
import { MetricCard } from '../shared/MetricCard';
import { AlertBadge } from '../shared/AlertBadge';
import { DataTable } from '../shared/DataTable';
import { formatDuration, formatPercent, formatRelativeTime } from '../utils/formatters';

interface Alert {
  id: string;
  severity: 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
}

interface ErrorTrace {
  specId: string;
  error: string;
  timestamp: string;
  agentType: string;
}

interface OpsTabProps {
  data: {
    health: { status: 'healthy' | 'degraded' | 'unhealthy'; services: { name: string; status: string }[] };
    alerts: Alert[];
    errorRate: number;
    avgLatency: number;
    requestsPerHour: number;
    recentErrors: ErrorTrace[];
  };
  loading?: boolean;
}

export function OpsTab({ data, loading }: OpsTabProps) {
  const { t } = useTranslation(['analytics']);

  const healthColor = {
    healthy: 'text-green-600',
    degraded: 'text-yellow-600',
    unhealthy: 'text-red-600',
  };

  const errorColumns = [
    { key: 'specId', header: 'ops.specId' },
    { key: 'agentType', header: 'ops.agent' },
    { key: 'error', header: 'ops.error', className: 'max-w-xs truncate' },
    { key: 'timestamp', header: 'ops.when', render: (row: ErrorTrace) => formatRelativeTime(row.timestamp) },
  ];

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Health and key metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">{t('ops.healthStatus')}</p>
          <p className={`text-2xl font-bold mt-1 capitalize ${healthColor[data.health.status]}`}>
            {data.health.status}
          </p>
          <div className="mt-2 space-y-1">
            {data.health.services.map((svc) => (
              <div key={svc.name} className="flex items-center gap-2 text-xs">
                <span className={`w-2 h-2 rounded-full ${svc.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-gray-600 dark:text-gray-400">{svc.name}</span>
              </div>
            ))}
          </div>
        </div>
        <MetricCard
          title="ops.errorRate"
          value={formatPercent(data.errorRate)}
          trend={{ value: data.errorRate, isPositive: data.errorRate < 5 }}
        />
        <MetricCard
          title="ops.avgLatency"
          value={formatDuration(data.avgLatency)}
        />
        <MetricCard
          title="ops.requestsPerHour"
          value={data.requestsPerHour.toString()}
        />
      </div>

      {/* Active alerts */}
      {data.alerts.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            {t('ops.activeAlerts')} ({data.alerts.length})
          </h3>
          <div className="space-y-2">
            {data.alerts.map((alert) => (
              <AlertBadge key={alert.id} severity={alert.severity} message={alert.message} />
            ))}
          </div>
        </div>
      )}

      {/* Recent errors */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
          {t('ops.recentErrors')}
        </h3>
        <DataTable
          columns={errorColumns}
          data={data.recentErrors}
          emptyMessage="ops.noErrors"
        />
      </div>
    </div>
  );
}

export default OpsTab;
