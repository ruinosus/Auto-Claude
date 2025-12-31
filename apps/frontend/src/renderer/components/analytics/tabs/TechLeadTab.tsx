import { useTranslation } from 'react-i18next';
import { MetricCard } from '../shared/MetricCard';
import { formatCurrency, formatPercent } from '../utils/formatters';

interface TechLeadTabProps {
  data: {
    budget: { used: number; total: number; projected: number };
    teamMetrics: { specsCompleted: number; avgROI: number; efficiency: string };
    costByAgent: { agent: string; cost: number; percentage: number }[];
  };
  loading?: boolean;
}

export function TechLeadTab({ data, loading }: TechLeadTabProps) {
  const { t } = useTranslation(['analytics']);

  const budgetPercent = (data.budget.used / data.budget.total) * 100;
  const isOverBudget = data.budget.projected > data.budget.total;

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        <div className="grid grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Budget tracker */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('techLead.budgetTracker')}
          </h3>
          <span className={`text-sm font-bold ${isOverBudget ? 'text-red-600' : 'text-green-600'}`}>
            {formatCurrency(data.budget.used)} / {formatCurrency(data.budget.total)}
          </span>
        </div>
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full ${budgetPercent > 80 ? 'bg-red-500' : budgetPercent > 60 ? 'bg-yellow-500' : 'bg-green-500'}`}
            style={{ width: `${Math.min(100, budgetPercent)}%` }}
          />
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
          {t('techLead.projected')}: {formatCurrency(data.budget.projected)}
          {isOverBudget && <span className="text-red-500 ml-2">{t('techLead.overBudget')}</span>}
        </p>
      </div>

      {/* Team metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          title="techLead.specsCompleted"
          value={data.teamMetrics.specsCompleted}
        />
        <MetricCard
          title="techLead.avgROI"
          value={formatPercent(data.teamMetrics.avgROI)}
          trend={{ value: data.teamMetrics.avgROI, isPositive: data.teamMetrics.avgROI > 0 }}
        />
        <MetricCard
          title="techLead.efficiency"
          value={data.teamMetrics.efficiency}
        />
      </div>

      {/* Agent distribution */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
          {t('techLead.agentDistribution')}
        </h3>
        <div className="space-y-3">
          {data.costByAgent.map((agent) => (
            <div key={agent.agent} className="flex items-center gap-3">
              <span className="w-24 text-sm text-gray-600 dark:text-gray-400 capitalize">{agent.agent}</span>
              <div className="flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500" style={{ width: `${agent.percentage}%` }} />
              </div>
              <span className="w-20 text-sm text-right text-gray-700 dark:text-gray-300">
                {formatCurrency(agent.cost)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default TechLeadTab;
