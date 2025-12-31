import { useTranslation } from 'react-i18next';
import { MetricCard } from '../shared/MetricCard';
import { DataTable } from '../shared/DataTable';
import { formatCurrency, formatHours, formatPercent } from '../utils/formatters';

interface TopSpec {
  name: string;
  value: number;
  roi: number;
}

interface BusinessTabProps {
  data: {
    investment: number;
    valueGenerated: number;
    netSavings: number;
    hoursImpact: number;
    topSpecs: TopSpec[];
    annualProjection: { investment: number; value: number; roi: number };
  };
  loading?: boolean;
  onExportPDF?: () => void;
}

export function BusinessTab({ data, loading, onExportPDF }: BusinessTabProps) {
  const { t } = useTranslation(['analytics']);

  const roiValue = data.investment > 0
    ? ((data.valueGenerated - data.investment) / data.investment) * 100
    : 0;

  const topSpecColumns = [
    { key: 'name', header: 'business.specName' },
    { key: 'value', header: 'business.value', render: (row: TopSpec) => formatCurrency(row.value) },
    { key: 'roi', header: 'business.roi', render: (row: TopSpec) => (
      <span className={row.roi >= 0 ? 'text-green-600' : 'text-red-600'}>
        {formatPercent(row.roi)}
      </span>
    )},
  ];

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-40 bg-gray-200 dark:bg-gray-700 rounded-lg" />
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
      {/* Executive summary - big ROI display */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-blue-100 text-sm">{t('business.executiveSummary')}</p>
            <p className="text-5xl font-bold mt-2">{formatPercent(roiValue)}</p>
            <p className="text-blue-100 mt-1">Return on Investment</p>
          </div>
          {onExportPDF && (
            <button
              onClick={onExportPDF}
              className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition"
            >
              {t('business.exportPdf')}
            </button>
          )}
        </div>
      </div>

      {/* Key business metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          title="business.investment"
          value={formatCurrency(data.investment)}
          subtitle="Total AI costs"
        />
        <MetricCard
          title="business.valueGenerated"
          value={formatCurrency(data.valueGenerated)}
          subtitle="Equivalent dev time"
          trend={{ value: 25, isPositive: true }}
        />
        <MetricCard
          title="business.netSavings"
          value={formatCurrency(data.netSavings)}
          trend={{ value: data.netSavings > 0 ? 15 : -15, isPositive: data.netSavings > 0 }}
        />
      </div>

      {/* Hours impact visual */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
          {t('business.hoursImpact')}
        </h3>
        <div className="flex items-center gap-4">
          <div className="text-4xl font-bold text-blue-600">{formatHours(data.hoursImpact)}</div>
          <div className="text-gray-500 dark:text-gray-400">
            <p>Developer hours saved</p>
            <p className="text-sm">{(data.hoursImpact / 160).toFixed(1)} FTE-months</p>
          </div>
        </div>
      </div>

      {/* Top performing specs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
          {t('business.topSpecs')}
        </h3>
        <DataTable
          columns={topSpecColumns}
          data={data.topSpecs}
          emptyMessage="business.noSpecs"
        />
      </div>

      {/* Annual projection */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
          {t('business.annualProjection')}
        </h3>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatCurrency(data.annualProjection.investment)}
            </p>
            <p className="text-sm text-gray-500">Projected Investment</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-green-600">
              {formatCurrency(data.annualProjection.value)}
            </p>
            <p className="text-sm text-gray-500">Projected Value</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-blue-600">
              {formatPercent(data.annualProjection.roi)}
            </p>
            <p className="text-sm text-gray-500">Projected ROI</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BusinessTab;
