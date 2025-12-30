import { DollarSign, Clock, TrendingUp, CheckCircle, Users, Banknote } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent } from '../../ui/card';
import type { ROIAggregateMetrics, ROISettings, Currency } from '../../../../shared/types/roi';

interface ROIOverviewCardProps {
  title: string;
  value: string;
  subtitle?: string;
  highlight?: string;
  icon: React.ElementType;
  iconColor?: string;
  valueColor?: string;
  size?: 'normal' | 'large';
}

function ROIOverviewCard({
  title,
  value,
  subtitle,
  highlight,
  icon: Icon,
  iconColor = 'text-muted-foreground',
  valueColor = '',
  size = 'normal'
}: ROIOverviewCardProps) {
  return (
    <Card className={`shadow-sm ${size === 'large' ? 'bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20 border-green-200 dark:border-green-800' : ''}`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          <Icon className={`h-5 w-5 ${iconColor}`} aria-hidden="true" />
        </div>
        <div className={`font-bold ${size === 'large' ? 'text-3xl' : 'text-2xl'} ${valueColor}`}>
          {value}
        </div>
        {highlight && (
          <p className="text-sm font-medium text-green-600 dark:text-green-400 mt-1">{highlight}</p>
        )}
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}

function LoadingCard() {
  return (
    <Card className="shadow-sm animate-pulse">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="h-4 w-24 bg-muted rounded" />
          <div className="h-4 w-4 bg-muted rounded" />
        </div>
        <div className="h-8 w-32 bg-muted rounded" />
      </CardContent>
    </Card>
  );
}

export interface ROIOverviewCardsProps {
  aggregate: ROIAggregateMetrics | null;
  settings: ROISettings;
  isLoading?: boolean;
}

/**
 * Formats currency values with proper locale formatting
 */
function formatCurrencyValue(amount: number, currency: Currency): string {
  const localeMap: Record<Currency, string> = {
    USD: 'en-US',
    EUR: 'de-DE',
    BRL: 'pt-BR',
  };

  return new Intl.NumberFormat(localeMap[currency], {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function ROIOverviewCards({ aggregate, settings, isLoading }: ROIOverviewCardsProps) {
  const { t } = useTranslation(['analytics']);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <LoadingCard key={i} />
        ))}
      </div>
    );
  }

  const totalSavings = aggregate?.totalSavings ?? 0;
  const secondaryAmount = settings.secondaryCurrency
    ? totalSavings * settings.exchangeRate
    : null;

  const totalROI = aggregate?.totalROI ?? 0;
  const successRate = aggregate?.successRate ?? 0;
  const totalHoursSaved = aggregate?.totalHoursSaved ?? 0;
  const specsCount = aggregate?.specsCount ?? 0;
  const totalCost = aggregate?.totalCost ?? 0;

  // Calculate FTE equivalent (assuming 160 hours/month for a full-time developer)
  const fteEquivalent = totalHoursSaved / 160;
  const fteText = fteEquivalent >= 1
    ? `≈ ${fteEquivalent.toFixed(1)} ${t('analytics:roi.fteMonths')}`
    : `≈ ${(totalHoursSaved / 8).toFixed(1)} ${t('analytics:roi.workDays')}`;

  // Calculate what human development would have cost
  const humanCostEquivalent = totalHoursSaved * settings.developerHourlyRate;

  return (
    <div className="space-y-4">
      {/* Primary KPI - Total Savings (highlighted) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ROIOverviewCard
          title={t('analytics:roi.totalSavings')}
          value={formatCurrencyValue(totalSavings, settings.primaryCurrency)}
          subtitle={secondaryAmount !== null && settings.secondaryCurrency
            ? formatCurrencyValue(secondaryAmount, settings.secondaryCurrency)
            : undefined}
          highlight={t('analytics:roi.vsHumanCost', {
            cost: formatCurrencyValue(humanCostEquivalent, settings.primaryCurrency)
          })}
          icon={Banknote}
          iconColor="text-green-600"
          size="large"
        />
        <ROIOverviewCard
          title={t('analytics:roi.roiPercentage')}
          value={`${totalROI.toFixed(0)}%`}
          highlight={totalROI > 1000 ? t('analytics:roi.exceptionalROI') : undefined}
          subtitle={t('analytics:roi.aiCost', {
            cost: formatCurrencyValue(totalCost, settings.primaryCurrency)
          })}
          icon={TrendingUp}
          iconColor={totalROI > 0 ? 'text-green-600' : 'text-muted-foreground'}
          valueColor={totalROI > 0 ? 'text-green-600' : ''}
          size="large"
        />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ROIOverviewCard
          title={t('analytics:roi.hoursSaved')}
          value={`${totalHoursSaved.toFixed(0)} ${t('analytics:roi.hours')}`}
          subtitle={fteText}
          icon={Clock}
          iconColor="text-blue-500"
        />
        <ROIOverviewCard
          title={t('analytics:roi.successRate')}
          value={`${successRate.toFixed(0)}%`}
          subtitle={t('analytics:roi.completedTasks', { count: specsCount })}
          icon={CheckCircle}
          iconColor={successRate >= 80 ? 'text-green-500' : 'text-amber-500'}
        />
        <ROIOverviewCard
          title={t('analytics:roi.teamEfficiency')}
          value={fteEquivalent >= 0.1 ? `+${fteEquivalent.toFixed(1)} FTE` : `+${(totalHoursSaved / 8).toFixed(0)} days`}
          subtitle={t('analytics:roi.capacityGained')}
          icon={Users}
          iconColor="text-purple-500"
        />
      </div>
    </div>
  );
}
