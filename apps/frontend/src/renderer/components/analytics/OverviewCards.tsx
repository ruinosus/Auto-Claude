import { DollarSign, Cpu, Activity, PiggyBank } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { formatLargeNumber, formatCurrencyDual, formatCurrency, formatCurrencyBRL } from './utils/formatters';

interface OverviewCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  progress?: number; // 0-100
}

function OverviewCard({ title, value, subtitle, icon: Icon, progress }: OverviewCardProps) {
  return (
    <Card className="shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
        {progress !== undefined && (
          <div className="mt-2">
            <div className="h-2 rounded-full bg-secondary">
              <div
                className={`h-full rounded-full transition-all ${
                  progress >= 90 ? 'bg-destructive' : progress >= 80 ? 'bg-yellow-500' : 'bg-primary'
                }`}
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export interface OverviewCardsData {
  totalCost: number;
  totalTokens: {
    input: number;
    output: number;
  };
  activeSessions: number;
  budgetRemaining: number;
  budgetProgress?: number; // 0-100
}

export function OverviewCards({ data }: { data: OverviewCardsData }) {
  const { totalCost, totalTokens, activeSessions, budgetRemaining, budgetProgress } = data;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <OverviewCard
        title="Total Cost"
        value={formatCurrency(totalCost, 2)}
        subtitle={formatCurrencyBRL(totalCost, 2)}
        icon={DollarSign}
      />
      <OverviewCard
        title="Total Tokens"
        value={`${formatLargeNumber(totalTokens.input + totalTokens.output)}`}
        subtitle={`${formatLargeNumber(totalTokens.input)} input / ${formatLargeNumber(totalTokens.output)} output`}
        icon={Cpu}
      />
      <OverviewCard
        title="Active Sessions"
        value={activeSessions.toString()}
        icon={Activity}
      />
      <OverviewCard
        title="Budget Remaining"
        value={formatCurrency(budgetRemaining, 2)}
        subtitle={formatCurrencyBRL(budgetRemaining, 2)}
        icon={PiggyBank}
        progress={budgetProgress}
      />
    </div>
  );
}
