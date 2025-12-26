import { DollarSign, Clock, TrendingUp, CheckCircle } from 'lucide-react';
import { Card, CardContent } from '../../ui/card';
import type { ROIAggregateMetrics, ROISettings, Currency } from '../../../../shared/types/roi';

interface ROIOverviewCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  iconColor?: string;
}

function ROIOverviewCard({ title, value, subtitle, icon: Icon, iconColor = 'text-muted-foreground' }: ROIOverviewCardProps) {
  return (
    <Card className="shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          <Icon className={`h-4 w-4 ${iconColor}`} aria-hidden="true" />
        </div>
        <div className="text-2xl font-bold">{value}</div>
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

  const cards = [
    {
      title: 'Total Savings',
      value: formatCurrencyValue(totalSavings, settings.primaryCurrency),
      subtitle: secondaryAmount !== null && settings.secondaryCurrency
        ? formatCurrencyValue(secondaryAmount, settings.secondaryCurrency)
        : undefined,
      icon: DollarSign,
      iconColor: 'text-green-500',
    },
    {
      title: 'Hours Saved',
      value: `${totalHoursSaved.toFixed(1)} hrs`,
      icon: Clock,
      iconColor: 'text-blue-500',
    },
    {
      title: 'ROI',
      value: `${totalROI.toFixed(0)}%`,
      icon: TrendingUp,
      iconColor: totalROI > 0 ? 'text-green-500' : 'text-muted-foreground',
    },
    {
      title: 'Success Rate',
      value: `${successRate.toFixed(0)}%`,
      subtitle: `${specsCount} specs`,
      icon: CheckCircle,
      iconColor: 'text-primary',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <ROIOverviewCard
          key={card.title}
          title={card.title}
          value={card.value}
          subtitle={card.subtitle}
          icon={card.icon}
          iconColor={card.iconColor}
        />
      ))}
    </div>
  );
}
