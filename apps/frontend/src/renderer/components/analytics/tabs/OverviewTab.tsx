import { useTranslation } from 'react-i18next';
import { MetricCard } from '../shared/MetricCard';
import { formatCurrency, formatTokens, formatHours, formatPercent } from '../utils/formatters';
import {
  Zap,
  MessageCircle,
  Sparkles,
  GitPullRequest,
  Code,
  Cpu,
  CheckCircle,
  FileText,
  TrendingUp,
  Activity,
  BarChart3,
} from 'lucide-react';

// Feature icons with colors
const FEATURE_ICONS: Record<string, React.ReactNode> = {
  ideation: <Zap className="h-4 w-4" />,
  insights: <MessageCircle className="h-4 w-4" />,
  roadmap: <Sparkles className="h-4 w-4" />,
  pr_review: <GitPullRequest className="h-4 w-4" />,
  pr_review_engine: <GitPullRequest className="h-4 w-4" />,
  planner: <FileText className="h-4 w-4" />,
  coder: <Code className="h-4 w-4" />,
  qa_reviewer: <CheckCircle className="h-4 w-4" />,
  qa_fixer: <CheckCircle className="h-4 w-4" />,
  spec: <FileText className="h-4 w-4" />,
  phase: <Activity className="h-4 w-4" />,
  insight: <MessageCircle className="h-4 w-4" />,
};

// Feature display names
const FEATURE_NAMES: Record<string, string> = {
  coder: 'Build - Coder',
  planner: 'Build - Planner',
  qa_reviewer: 'QA Review',
  qa_fixer: 'QA Fixer',
  ideation_code_improvements: 'Ideation: Code',
  ideation_documentation: 'Ideation: Docs',
  ideation_security: 'Ideation: Security',
  ideation_performance: 'Ideation: Performance',
  ideation_ui_ux: 'Ideation: UI/UX',
  insights: 'Insights Chat',
  insight_extractor: 'Insight Extraction',
  roadmap_features: 'Roadmap: Features',
  roadmap_discovery: 'Roadmap: Discovery',
  roadmap_competitor_analysis: 'Roadmap: Competitors',
  spec_writer: 'Spec: Writer',
  spec_complexity_assessor: 'Spec: Complexity',
  spec_gatherer: 'Spec: Gatherer',
  spec_researcher: 'Spec: Research',
  phase_compaction: 'Phase Compaction',
  other: 'Other',
};

// Feature colors for bars
const FEATURE_COLORS: Record<string, string> = {
  coder: 'bg-purple-500',
  planner: 'bg-blue-500',
  ideation: 'bg-yellow-500',
  insights: 'bg-green-500',
  insight: 'bg-green-400',
  roadmap: 'bg-cyan-500',
  spec: 'bg-indigo-500',
  qa: 'bg-teal-500',
  phase: 'bg-orange-500',
  other: 'bg-gray-500',
};

interface FeatureUsage {
  feature: string;
  tokens: number;
  cost: number;
  percentage: number;
  trace_count?: number;
}

interface HourlyMetric {
  hour: string;
  requests: number;
  cost: number;
  tokens: number;
}

interface OverviewTabProps {
  data: {
    totalCost: number;
    totalTokens: number;
    hoursSaved: number;
    avgROI: number;
    specsCompleted: number;
    specsInProgress: number;
    totalTraces?: number;
    allFeatures?: FeatureUsage[];
    hourlyData?: HourlyMetric[];
  };
  loading?: boolean;
}

function getFeatureColor(feature: string): string {
  const baseFeature = feature.split('_')[0];
  return FEATURE_COLORS[baseFeature] || FEATURE_COLORS.other;
}

function getFeatureName(feature: string): string {
  return FEATURE_NAMES[feature] || feature.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
}

function getFeatureIcon(feature: string): React.ReactNode {
  const baseFeature = feature.split('_')[0];
  return FEATURE_ICONS[baseFeature] || FEATURE_ICONS[feature] || <Cpu className="h-4 w-4" />;
}

export function OverviewTab({ data, loading }: OverviewTabProps) {
  const { t } = useTranslation(['analytics']);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
          ))}
        </div>
        <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      </div>
    );
  }

  const maxHourlyCost = Math.max(...(data.hourlyData || []).map((h) => h.cost), 0.01);
  const netValue = data.hoursSaved * 50 - data.totalCost;

  return (
    <div className="space-y-6">
      {/* Top metrics row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="overview.totalCost"
          value={formatCurrency(data.totalCost)}
          subtitle={`${data.totalTraces || 0} traces`}
        />
        <MetricCard
          title="overview.totalTokens"
          value={formatTokens(data.totalTokens)}
          subtitle={data.totalTokens === 0 ? 'Syncing with Langfuse' : undefined}
        />
        <MetricCard
          title="overview.hoursSaved"
          value={formatHours(data.hoursSaved)}
          trend={{ value: data.hoursSaved > 0 ? 15 : 0, isPositive: data.hoursSaved > 0 }}
        />
        <MetricCard
          title="overview.avgROI"
          value={formatPercent(data.avgROI)}
          trend={{ value: data.avgROI, isPositive: data.avgROI > 100 }}
        />
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">Net Value</p>
          <p className={`text-2xl font-bold mt-1 ${netValue >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(netValue)}
          </p>
          <p className="text-xs text-gray-400 mt-1">Value - Cost</p>
        </div>
      </div>

      {/* Status and Timeline row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Status Quick View */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="h-4 w-4 text-blue-500" />
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">{t('overview.statusQuick')}</h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">{t('overview.specsCompleted')}</span>
              <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded text-sm font-bold">
                {data.specsCompleted}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">{t('overview.inProgress')}</span>
              <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-sm font-bold">
                {data.specsInProgress}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">Total Traces</span>
              <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded text-sm font-bold">
                {data.totalTraces || 0}
              </span>
            </div>
          </div>
        </div>

        {/* Cost Over Time Chart */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-4 w-4 text-purple-500" />
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">Cost Timeline (Last 24h)</h3>
          </div>
          {!data.hourlyData || data.hourlyData.length === 0 ? (
            <div className="h-32 flex items-center justify-center text-gray-400">
              <p>No hourly data available yet</p>
            </div>
          ) : (
            <div className="flex gap-1" style={{ height: '128px' }}>
              {data.hourlyData.map((h, idx) => {
                const heightPercent = Math.max(4, (h.cost / maxHourlyCost) * 100);
                const barHeight = Math.round((heightPercent / 100) * 100); // 100px max for bars
                const hourLabel = new Date(h.hour).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return (
                  <div key={idx} className="flex-1 flex flex-col items-center group relative justify-end">
                    {/* Bar container with fixed height */}
                    <div className="w-full flex items-end justify-center" style={{ height: '100px' }}>
                      <div
                        className="w-full max-w-[40px] bg-purple-500 rounded-t transition-all hover:bg-purple-600 cursor-pointer"
                        style={{ height: `${barHeight}px` }}
                        title={`${hourLabel}: ${formatCurrency(h.cost)}`}
                      />
                    </div>
                    <span className="text-[10px] text-gray-400 mt-1 truncate w-full text-center">{hourLabel}</span>
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-2 hidden group-hover:block z-10">
                      <div className="bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap">
                        {formatCurrency(h.cost)} | {h.requests} requests
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* All Features Breakdown */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-green-500" />
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('overview.costByFeature', 'Cost Breakdown by Feature')}
            </h3>
          </div>
          <span className="text-xs text-gray-500">
            {data.allFeatures?.length || 0} features tracked
          </span>
        </div>

        {!data.allFeatures || data.allFeatures.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <Cpu className="h-8 w-8 mx-auto mb-2" />
            <p>No feature usage data yet</p>
            <p className="text-xs mt-1">Run some AI features to see cost breakdown</p>
          </div>
        ) : (
          <div className="space-y-2">
            {data.allFeatures.map((feature) => {
              const icon = getFeatureIcon(feature.feature);
              const color = getFeatureColor(feature.feature);
              const name = getFeatureName(feature.feature);

              return (
                <div key={feature.feature} className="flex items-center gap-3">
                  <div className="flex items-center gap-2 w-44 min-w-[11rem]">
                    <span className="text-gray-500 dark:text-gray-400">{icon}</span>
                    <span className="text-sm text-gray-700 dark:text-gray-300 truncate" title={name}>
                      {name}
                    </span>
                  </div>
                  <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${color} transition-all`}
                      style={{ width: `${Math.max(2, feature.percentage)}%` }}
                    />
                  </div>
                  <div className="flex items-center gap-3 text-sm min-w-[10rem] justify-end">
                    <span className="text-gray-400 text-xs">
                      {feature.trace_count || 0} calls
                    </span>
                    <span className="font-medium text-gray-700 dark:text-gray-300 w-16 text-right">
                      {formatCurrency(feature.cost)}
                    </span>
                    <span className="text-gray-500 w-12 text-right">{feature.percentage.toFixed(1)}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default OverviewTab;
