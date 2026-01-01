import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useProjectStore } from '../../stores/project-store';
import { useUsageSummary, useROISummary, useUnifiedROI, useAnalyticsHealth, useHealthStatus, useErrorMetrics, useHourlyMetrics } from '../../hooks/useAnalyticsQuery';
import { OverviewTab } from './tabs/OverviewTab';
import { DevTab } from './tabs/DevTab';
import { TechLeadTab } from './tabs/TechLeadTab';
import { OpsTab } from './tabs/OpsTab';
import { BusinessTab } from './tabs/BusinessTab';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { ROIExplanation, ROIExplanationButton } from './shared/ROIExplanation';

type TabId = 'overview' | 'dev' | 'techlead' | 'ops' | 'business';

interface AnalyticsProps {
  projectId?: string;
  initialTab?: TabId;
}

export function Analytics({ projectId, initialTab = 'overview' }: AnalyticsProps) {
  const { t } = useTranslation(['analytics']);
  const [budgetLimit, setBudgetLimit] = useState<number | undefined>(undefined);
  const [activeTab, setActiveTab] = useState<TabId>(initialTab);
  const [showROIExplanation, setShowROIExplanation] = useState(false);

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

  // Fetch unified ROI data (new unified system with value breakdown)
  const unifiedROI = useUnifiedROI(
    { project_id: projectName },
    { enabled: !!projectName && health.data?.langfuse_configured }
  );

  // Fetch Ops tab data (health, errors, hourly metrics)
  // IMPORTANT: Pass projectName for data isolation
  const healthStatus = useHealthStatus({ enabled: health.data?.langfuse_configured });
  const errorMetrics = useErrorMetrics(24, projectName, { enabled: !!projectName && health.data?.langfuse_configured });
  const hourlyMetrics = useHourlyMetrics(24, projectName, { enabled: !!projectName && health.data?.langfuse_configured });

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

  const isLoading = usageSummary.isLoading || roiSummary.isLoading || unifiedROI.isLoading;

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
  // Get ALL features by cost for comprehensive overview
  const allFeatures = (usageData?.feature_usage || [])
    .sort((a, b) => b.cost - a.cost)
    .map((f) => ({
      feature: f.feature,
      tokens: f.tokens,
      cost: f.cost,
      percentage: f.percentage,
      trace_count: f.trace_count,
    }));

  // Get hourly metrics for timeline chart
  const hourlyData = (hourlyMetrics.data?.metrics || []).map((m) => ({
    hour: m.hour,
    requests: m.requests,
    cost: m.cost,
    tokens: m.tokens,
  }));

  const overviewData = {
    totalCost,
    totalTokens,
    hoursSaved,
    avgROI,
    specsCompleted,
    specsInProgress: Math.max(0, specsInProgress),
    totalTraces: usageData?.total_traces || 0,
    allFeatures,
    hourlyData,
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
  // Feature usage - where is money being spent (ideation, insights, roadmap, build, etc.)
  const featureUsage = (usageData?.feature_usage || []).map((f) => ({
    feature: f.feature,
    tokens: f.tokens,
    cost: f.cost,
    trace_count: f.trace_count,
    percentage: f.percentage,
  }));

  // Model distribution - which Claude models are being used
  const modelDistribution = (usageData?.model_distribution || []).map((m) => ({
    model: m.model,
    tokens: m.tokens,
    cost: m.cost,
    percentage: m.percentage,
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
    featureUsage,
    modelDistribution,
  };

  // Transform data for OpsTab using real API data
  const healthData = healthStatus.data;
  const errorData = errorMetrics.data;
  const opsHourlyData = hourlyMetrics.data;

  // Calculate requests per hour from hourly metrics
  const totalHourlyRequests = (opsHourlyData?.metrics || []).reduce((sum: number, m: { requests: number }) => sum + m.requests, 0);
  const avgRequestsPerHour = opsHourlyData?.metrics?.length
    ? Math.round(totalHourlyRequests / opsHourlyData.metrics.length)
    : 0;

  // Generate alerts based on error rate and health status
  const alerts: { id: string; severity: 'info' | 'warning' | 'error'; message: string; timestamp: string }[] = [];
  if (errorData && errorData.error_rate > 5) {
    alerts.push({
      id: 'high-error-rate',
      severity: 'error',
      message: `High error rate: ${errorData.error_rate.toFixed(1)}%`,
      timestamp: new Date().toISOString(),
    });
  }
  if (healthData?.overall_status === 'degraded') {
    alerts.push({
      id: 'degraded-health',
      severity: 'warning',
      message: 'System health is degraded',
      timestamp: healthData.checked_at,
    });
  }

  const opsData = {
    health: {
      status: (healthData?.overall_status || 'healthy') as 'healthy' | 'degraded' | 'unhealthy',
      services: (healthData?.services || []).map((s) => ({
        name: s.name,
        status: s.status,
      })),
    },
    alerts,
    errorRate: errorData?.error_rate || 0,
    avgLatency: (usageData?.duration_by_phase || []).reduce((sum, p) => sum + p.avg_duration_ms, 0) /
      Math.max(1, usageData?.duration_by_phase?.length || 1),
    requestsPerHour: avgRequestsPerHour || usageData?.total_traces || 0,
    recentErrors: (errorData?.recent_errors || []).map((e) => ({
      specId: e.spec_id,
      error: e.error,
      timestamp: e.timestamp,
      agentType: e.agent_type,
    })),
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

  // Get unified ROI data for value breakdown
  const unifiedData = unifiedROI.data?.summary;

  const businessData = {
    investment: totalCost,
    valueGenerated: unifiedData?.total_value_usd || roiData?.total_business_value_usd || 0,
    netSavings: unifiedData?.net_value_usd || (roiData?.total_business_value_usd || 0) - totalCost,
    hoursImpact: hoursSaved,
    topSpecs,
    annualProjection: {
      investment: totalCost * 12,
      value: (unifiedData?.total_value_usd || roiData?.total_business_value_usd || 0) * 12,
      roi: unifiedData?.total_roi_percentage || avgROI,
    },
    // New unified ROI value breakdown
    valueBreakdown: unifiedData?.value_distribution ? {
      execution: unifiedData.value_distribution.execution_value,
      decision: unifiedData.value_distribution.decision_value,
      prevention: unifiedData.value_distribution.prevention_value,
      knowledge: unifiedData.value_distribution.knowledge_value,
    } : undefined,
    // ROI by feature type
    roiByFeature: unifiedData?.by_feature_type ? Object.entries(unifiedData.by_feature_type).map(([type, metrics]) => ({
      feature: type,
      roi: metrics.roi_percentage,
      value: metrics.total_value_usd,
      cost: metrics.total_cost_usd,
    })) : [],
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
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold">{t('analytics:header.title')}</h1>
            <p className="text-muted-foreground">{t('analytics:header.subtitle')}</p>
          </div>
          <ROIExplanationButton onClick={() => setShowROIExplanation(true)} />
        </div>

        {/* ROI Explanation Modal */}
        <ROIExplanation isOpen={showROIExplanation} onClose={() => setShowROIExplanation(false)} />

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
            <TechLeadTab data={techLeadData} loading={isLoading} projectId={projectName} />
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
