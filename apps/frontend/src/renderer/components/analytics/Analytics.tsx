import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAnalyticsStore } from '../../stores/analytics-store';
import { useAnalyticsData } from '../../hooks/useAnalyticsData';
import { OverviewCards } from './OverviewCards';
import { CostChart } from './CostChart';
import { TokensChart } from './TokensChart';
import { ModelDistributionChart } from './ModelDistributionChart';
import { SessionDurationChart } from './SessionDurationChart';
import { BudgetManager } from './BudgetManager';
import { FeatureUsageSection } from './FeatureUsageSection';
import { ROIDashboard } from './roi/ROIDashboard';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';

interface AnalyticsProps {
  projectId?: string;
  initialTab?: 'usage' | 'roi';
}

export function Analytics({ projectId, initialTab = 'usage' }: AnalyticsProps) {
  const { t } = useTranslation(['analytics']);
  const data = useAnalyticsStore((state) => state.data);
  const [budgetLimit, setBudgetLimit] = useState<number | undefined>(undefined);
  const [dbPath, setDbPath] = useState<string | null>(null);
  const [isLoadingPath, setIsLoadingPath] = useState(true);
  const [activeTab, setActiveTab] = useState<'usage' | 'roi'>(initialTab);

  // Sync activeTab with initialTab when navigation changes
  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  // Fetch analytics DB path and budget from Electron
  useEffect(() => {
    if (!projectId) {
      setIsLoadingPath(false);
      setDbPath(null);
      return;
    }

    setIsLoadingPath(true);

    // Fetch both DB path and saved budget in parallel
    Promise.all([
      window.electronAPI.getAnalyticsDbPath(projectId),
      window.electronAPI.getBudget(projectId)
    ])
      .then(([dbPathResult, budgetResult]) => {
        if (dbPathResult.success) {
          setDbPath(dbPathResult.data ?? null);
        } else {
          console.error('Failed to get analytics DB path:', dbPathResult.error);
          setDbPath(null);
        }

        if (budgetResult.success && budgetResult.data !== undefined) {
          setBudgetLimit(budgetResult.data);
        }
      })
      .catch((error) => {
        console.error('Error fetching analytics data:', error);
        setDbPath(null);
      })
      .finally(() => {
        setIsLoadingPath(false);
      });
  }, [projectId]);

  // Save budget when it changes
  const handleBudgetChange = (newBudget: number) => {
    if (!projectId) return;

    setBudgetLimit(newBudget);
    window.electronAPI.saveBudget(projectId, newBudget)
      .then((result: { success: boolean; error?: string }) => {
        if (!result.success) {
          console.error('Failed to save budget:', result.error);
        }
      })
      .catch((error: Error) => {
        console.error('Error saving budget:', error);
      });
  };

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

  // Get model distribution from chartData (calculated in AnalyticsService)
  const modelDistribution = data.chartData.modelDistribution || [];

  // Get session duration from chartData (calculated in AnalyticsService)
  const sessionDurationData = data.chartData.sessionDuration || [];

  // Calculate budget progress
  const budgetProgress = budgetLimit ? (data.totalCost / budgetLimit) * 100 : undefined;
  const budgetRemaining = budgetLimit ? budgetLimit - data.totalCost : 0;

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">{t('analytics:header.title')}</h1>
          <p className="text-muted-foreground">{t('analytics:header.subtitle')}</p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'usage' | 'roi')}>
          <TabsList>
            <TabsTrigger value="usage">{t('analytics:tabs.usage')}</TabsTrigger>
            <TabsTrigger value="roi">{t('analytics:tabs.roi')}</TabsTrigger>
          </TabsList>

          <TabsContent value="usage" className="mt-6">
            {/* Existing usage analytics content */}
            <div className="space-y-6">
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

              {/* Feature Usage Section */}
              {data.featureUsage && data.featureUsage.length > 0 && (
                <FeatureUsageSection
                  featureUsage={data.featureUsage}
                  totalCost={data.totalCost}
                />
              )}

              {/* Budget Manager */}
              <BudgetManager
                currentCost={data.totalCost}
                budgetLimit={budgetLimit}
                onBudgetChange={handleBudgetChange}
              />
            </div>
          </TabsContent>

          <TabsContent value="roi" className="mt-6">
            <ROIDashboard projectId={projectId} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
