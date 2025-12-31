import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useProjectStore } from '../../stores/project-store';
import { useUsageSummary, useAnalyticsHealth } from '../../hooks/useAnalyticsQuery';
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
  const [budgetLimit, setBudgetLimit] = useState<number | undefined>(undefined);
  const [activeTab, setActiveTab] = useState<'usage' | 'roi'>(initialTab);

  // Get project name from store - this is the directory name used by the backend
  // IMPORTANT: Backend uses directory name (project.name), not UUID (project.id)
  const projects = useProjectStore((state) => state.projects);
  const project = projects.find((p) => p.id === projectId);
  const projectName = project?.name;

  // Fetch data from Langfuse via FastAPI service
  // Use project name (directory name) for data isolation, not UUID
  const health = useAnalyticsHealth();
  const usageSummary = useUsageSummary(
    { project_id: projectName },
    { enabled: !!projectName && health.data?.langfuse_configured }
  );

  // Sync activeTab with initialTab when navigation changes
  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  // Fetch saved budget from Electron
  useEffect(() => {
    if (!projectId) return;

    window.electronAPI.getBudget(projectId)
      .then((budgetResult) => {
        if (budgetResult.success && budgetResult.data !== undefined) {
          setBudgetLimit(budgetResult.data);
        }
      })
      .catch((error: Error) => {
        console.error('Error fetching budget:', error);
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

  // Loading state
  if (health.isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">{t('analytics:loading.title', 'Loading Analytics...')}</h2>
          <p className="text-muted-foreground">{t('analytics:loading.subtitle', 'Checking Langfuse connection')}</p>
        </div>
      </div>
    );
  }

  if (!projectId || !projectName) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">{t('analytics:noProject.title', 'No Project Selected')}</h2>
          <p className="text-muted-foreground">{t('analytics:noProject.subtitle', 'Please select a project to view analytics')}</p>
        </div>
      </div>
    );
  }

  // Check if Langfuse is configured
  if (!health.data?.langfuse_configured) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">{t('analytics:notConfigured.title', 'Langfuse Not Configured')}</h2>
          <p className="text-muted-foreground">
            {t('analytics:notConfigured.subtitle', 'Please configure Langfuse in Settings to view analytics.')}
          </p>
        </div>
      </div>
    );
  }

  if (usageSummary.isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">{t('analytics:loading.title', 'Loading Analytics...')}</h2>
          <p className="text-muted-foreground">{t('analytics:loading.fetching', 'Fetching analytics data')}</p>
        </div>
      </div>
    );
  }

  // Get data from Langfuse
  const data = usageSummary.data;

  // Transform cost over time data for CostChart
  const costChartData = (data?.cost_over_time || []).map((point) => ({
    timestamp: point.date, // Already in YYYY-MM-DD format
    cost: point.cost
  }));

  // Transform tokens by spec data for TokensChart
  const tokensChartData = (data?.tokens_by_spec || []).map((item) => ({
    spec_id: item.spec_id,
    input_tokens: item.input_tokens,
    output_tokens: item.output_tokens
  }));

  // Transform model distribution for ModelDistributionChart
  const modelDistribution = (data?.model_distribution || []).map((item) => ({
    model: item.model,
    count: item.generation_count,
    percentage: item.percentage
  }));

  // Transform duration by phase for SessionDurationChart (ms to seconds)
  const sessionDurationData = (data?.duration_by_phase || []).map((item) => ({
    phase: item.phase,
    avg_duration_seconds: item.avg_duration_ms / 1000
  }));

  // Transform feature usage for FeatureUsageSection (mapping to expected format)
  const featureUsage = (data?.feature_usage || []).map((item) => ({
    featureType: item.feature,
    totalSessions: item.trace_count,
    totalCost: item.cost,
    totalInputTokens: Math.floor(item.tokens * 0.3), // Estimate: 30% input tokens
    totalOutputTokens: Math.floor(item.tokens * 0.7), // Estimate: 70% output tokens
    lastUsed: null as Date | null // Not available from summary endpoint
  }));

  // Calculate budget progress
  const totalCost = data?.total_cost || 0;
  const budgetProgress = budgetLimit ? (totalCost / budgetLimit) * 100 : undefined;
  const budgetRemaining = budgetLimit ? budgetLimit - totalCost : 0;

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
            {/* Usage analytics content - powered by Langfuse */}
            <div className="space-y-6">
              {/* Overview Cards */}
              <OverviewCards
                data={{
                  totalCost: totalCost,
                  totalTokens: {
                    // Use real token counts when available from API, fallback to estimated split
                    input: data?.total_input_tokens ?? Math.floor((data?.total_tokens || 0) * 0.3),
                    output: data?.total_output_tokens ?? Math.floor((data?.total_tokens || 0) * 0.7)
                  },
                  activeSessions: data?.active_specs || 0,
                  budgetRemaining: budgetRemaining,
                  budgetProgress: budgetProgress
                }}
              />

              {/* Charts Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <CostChart
                  data={costChartData}
                  budgetLimit={budgetLimit}
                />
                <TokensChart data={tokensChartData} />
                <ModelDistributionChart data={modelDistribution} />
                <SessionDurationChart data={sessionDurationData} />
              </div>

              {/* Feature Usage Section */}
              {featureUsage.length > 0 && (
                <FeatureUsageSection
                  featureUsage={featureUsage}
                  totalCost={totalCost}
                />
              )}

              {/* Budget Manager */}
              <BudgetManager
                currentCost={totalCost}
                budgetLimit={budgetLimit}
                onBudgetChange={handleBudgetChange}
              />
            </div>
          </TabsContent>

          <TabsContent value="roi" className="mt-6">
            <ROIDashboard projectName={projectName} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
