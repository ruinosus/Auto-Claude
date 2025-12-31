import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useProjectStore } from '../../stores/project-store';
import { useUsageSummary, useROISummary, useAnalyticsHealth } from '../../hooks/useAnalyticsQuery';
import { OverviewTab } from './tabs/OverviewTab';
import { DevTab } from './tabs/DevTab';
import { TechLeadTab } from './tabs/TechLeadTab';
import { OpsTab } from './tabs/OpsTab';
import { BusinessTab } from './tabs/BusinessTab';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';

type TabId = 'overview' | 'dev' | 'techlead' | 'ops' | 'business';

interface AnalyticsProps {
  projectId?: string;
  initialTab?: TabId;
}

export function Analytics({ projectId, initialTab = 'overview' }: AnalyticsProps) {
  const { t } = useTranslation(['analytics']);
  const [budgetLimit, setBudgetLimit] = useState<number | undefined>(undefined);
  const [activeTab, setActiveTab] = useState<TabId>(initialTab);

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
  const roiSummary = useROISummary(
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

  // Tab configuration
  const tabs: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'tabs.overview' },
    { id: 'dev', label: 'tabs.dev' },
    { id: 'techlead', label: 'tabs.techLead' },
    { id: 'ops', label: 'tabs.ops' },
    { id: 'business', label: 'tabs.business' },
  ];

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

  const isLoading = usageSummary.isLoading || roiSummary.isLoading;

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">{t('analytics:loading.title', 'Loading Analytics...')}</h2>
          <p className="text-muted-foreground">{t('analytics:loading.fetching', 'Fetching analytics data')}</p>
        </div>
      </div>
    );
  }

  // Get data from APIs
  const usageData = usageSummary.data;
  const roiData = roiSummary.data;

  // Calculate totals
  const totalCost = usageData?.total_cost || 0;
  const totalTokens = usageData?.total_tokens || 0;
  const hoursSaved = roiData?.total_dev_hours_saved || 0;
  const avgROI = roiData?.total_roi_percentage || 0;
  const specsCompleted = roiData?.specs_with_positive_roi || 0;
  const specsInProgress = (usageData?.active_specs || 0) - specsCompleted;

  // Transform data for OverviewTab
  const overviewData = {
    totalCost,
    totalTokens,
    hoursSaved,
    avgROI,
    specsCompleted,
    specsInProgress: Math.max(0, specsInProgress),
  };

  // Transform data for DevTab - extract individual specs from ROI data
  const devSpecs = (roiData?.by_spec || []).map((spec) => ({
    id: spec.spec_id,
    name: spec.spec_id,
    status: spec.metrics.qa_passed ? 'completed' : 'in_progress',
    cost: spec.metrics.actual_cost_usd,
    timeSaved: spec.metrics.dev_hours_saved,
    roi: spec.metrics.roi_percentage,
  }));

  const devData = {
    mySpecs: devSpecs,
    totalCost,
    totalTimeSaved: hoursSaved,
    successRate: roiData?.spec_count ? (specsCompleted / roiData.spec_count) * 100 : 0,
  };

  // Transform data for TechLeadTab
  const costByAgent = (usageData?.model_distribution || []).map((model) => ({
    agent: model.model,
    cost: model.cost,
    percentage: model.percentage,
  }));

  const techLeadData = {
    budget: {
      used: totalCost,
      total: budgetLimit || totalCost * 1.5, // Default to 150% of current if no budget set
      projected: totalCost * 1.2, // Estimate 20% growth
    },
    teamMetrics: {
      specsCompleted,
      avgROI,
      efficiency: avgROI > 100 ? 'High' : avgROI > 50 ? 'Medium' : 'Low',
    },
    costByAgent,
  };

  // Transform data for OpsTab
  const opsData = {
    health: {
      status: 'healthy' as const,
      services: [
        { name: 'Langfuse', status: 'healthy' },
        { name: 'API', status: 'healthy' },
      ],
    },
    alerts: [] as { id: string; severity: 'info' | 'warning' | 'error'; message: string; timestamp: string }[],
    errorRate: 0,
    avgLatency: (usageData?.duration_by_phase || []).reduce((sum, p) => sum + p.avg_duration_ms, 0) /
      Math.max(1, usageData?.duration_by_phase?.length || 1),
    requestsPerHour: usageData?.total_traces || 0,
    recentErrors: [] as { specId: string; error: string; timestamp: string; agentType: string }[],
  };

  // Transform data for BusinessTab
  const topSpecs = (roiData?.by_spec || [])
    .sort((a, b) => b.metrics.roi_percentage - a.metrics.roi_percentage)
    .slice(0, 5)
    .map((spec) => ({
      name: spec.spec_id,
      value: spec.metrics.business_value_usd,
      roi: spec.metrics.roi_percentage,
    }));

  const businessData = {
    investment: totalCost,
    valueGenerated: roiData?.total_business_value_usd || 0,
    netSavings: (roiData?.total_business_value_usd || 0) - totalCost,
    hoursImpact: hoursSaved,
    topSpecs,
    annualProjection: {
      investment: totalCost * 12,
      value: (roiData?.total_business_value_usd || 0) * 12,
      roi: avgROI,
    },
  };

  // Handle PDF export for BusinessTab
  const handleExportPDF = () => {
    // TODO: Implement PDF export
    console.log('Export PDF clicked');
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">{t('analytics:header.title')}</h1>
          <p className="text-muted-foreground">{t('analytics:header.subtitle')}</p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabId)}>
          <TabsList className="grid w-full grid-cols-5">
            {tabs.map((tab) => (
              <TabsTrigger key={tab.id} value={tab.id}>
                {t(`analytics:${tab.label}`)}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            <OverviewTab data={overviewData} loading={isLoading} />
          </TabsContent>

          <TabsContent value="dev" className="mt-6">
            <DevTab data={devData} loading={isLoading} />
          </TabsContent>

          <TabsContent value="techlead" className="mt-6">
            <TechLeadTab data={techLeadData} loading={isLoading} />
          </TabsContent>

          <TabsContent value="ops" className="mt-6">
            <OpsTab data={opsData} loading={isLoading} />
          </TabsContent>

          <TabsContent value="business" className="mt-6">
            <BusinessTab
              data={businessData}
              loading={isLoading}
              onExportPDF={handleExportPDF}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
