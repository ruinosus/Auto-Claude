import { useState, useEffect } from 'react';
import { useAnalyticsStore } from '../../stores/analytics-store';
import { useAnalyticsData } from '../../hooks/useAnalyticsData';
import { OverviewCards } from './OverviewCards';
import { CostChart } from './CostChart';
import { TokensChart } from './TokensChart';
import { ModelDistributionChart } from './ModelDistributionChart';
import { SessionDurationChart } from './SessionDurationChart';
import { BudgetManager } from './BudgetManager';

interface AnalyticsProps {
  projectId?: string;
}

export function Analytics({ projectId }: AnalyticsProps) {
  const data = useAnalyticsStore((state) => state.data);
  const [budgetLimit, setBudgetLimit] = useState<number | undefined>(undefined);
  const [dbPath, setDbPath] = useState<string | null>(null);
  const [isLoadingPath, setIsLoadingPath] = useState(true);

  // Fetch analytics DB path from Electron
  useEffect(() => {
    if (!projectId) {
      setIsLoadingPath(false);
      setDbPath(null);
      return;
    }

    setIsLoadingPath(true);
    window.electronAPI
      .getAnalyticsDbPath(projectId)
      .then((result) => {
        if (result.success) {
          setDbPath(result.data ?? null);
        } else {
          console.error('Failed to get analytics DB path:', result.error);
          setDbPath(null);
        }
      })
      .catch((error) => {
        console.error('Error fetching analytics DB path:', error);
        setDbPath(null);
      })
      .finally(() => {
        setIsLoadingPath(false);
      });
  }, [projectId]);

  // Start polling (polling interval is now handled by analytics service in main process)
  useAnalyticsData(dbPath);

  if (isLoadingPath) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Loading Analytics...</h2>
          <p className="text-muted-foreground">Initializing analytics dashboard</p>
        </div>
      </div>
    );
  }

  if (!projectId) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">No Project Selected</h2>
          <p className="text-muted-foreground">Please select a project to view analytics</p>
        </div>
      </div>
    );
  }

  if (!dbPath) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">No Analytics Data</h2>
          <p className="text-muted-foreground">
            Analytics database not found. Run some tasks to generate analytics data.
          </p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Loading Analytics...</h2>
          <p className="text-muted-foreground">Fetching analytics data</p>
        </div>
      </div>
    );
  }

  // Transform data for TokensChart (by spec)
  const tokensChartData = Object.entries(
    data.conversations.reduce((acc, conv) => {
      if (!acc[conv.specId]) {
        acc[conv.specId] = { spec_id: conv.specId, input_tokens: 0, output_tokens: 0 };
      }
      acc[conv.specId].input_tokens += conv.tokens.input;
      acc[conv.specId].output_tokens += conv.tokens.output;
      return acc;
    }, {} as Record<string, { spec_id: string; input_tokens: number; output_tokens: number }>)
  ).map(([_, value]) => value);

  // Transform data for ModelDistributionChart
  const modelDistribution = Object.entries(
    data.conversations.reduce((acc, conv) => {
      // For now, use phase as a proxy for model (TODO: add model field to ConversationAnalytics)
      const model = conv.phase || 'unknown';
      acc[model] = (acc[model] || 0) + 1;
      return acc;
    }, {} as Record<string, number>)
  ).map(([model, count]) => {
    const total = data.conversations.length;
    return {
      model,
      count,
      percentage: (count / total) * 100
    };
  });

  // Transform data for SessionDurationChart
  // For now, use empty array (TODO: calculate durations from conversations)
  const sessionDurationData: Array<{ phase: string; avg_duration_seconds: number }> = [];

  // Calculate budget progress
  const budgetProgress = budgetLimit ? (data.totalCost / budgetLimit) * 100 : undefined;
  const budgetRemaining = budgetLimit ? budgetLimit - data.totalCost : 0;

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground">Monitor your Auto-Claude usage and costs</p>
        </div>

        {/* Overview Cards */}
        <OverviewCards
          data={{
            totalCost: data.totalCost,
            totalTokens: data.totalTokens,
            activeSessions: data.activeSessions,
            budgetRemaining: budgetRemaining,
            budgetProgress: budgetProgress
          }}
        />

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CostChart
            data={data.chartData.costOverTime.map((point) => ({
              timestamp: point.timestamp.toISOString(),
              cost: point.value
            }))}
            budgetLimit={budgetLimit}
          />
          <TokensChart data={tokensChartData} />
          <ModelDistributionChart data={modelDistribution} />
          <SessionDurationChart data={sessionDurationData} />
        </div>

        {/* Budget Manager */}
        <BudgetManager
          currentCost={data.totalCost}
          budgetLimit={budgetLimit}
          onBudgetChange={setBudgetLimit}
        />
      </div>
    </div>
  );
}
