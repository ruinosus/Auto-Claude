import { useTranslation } from 'react-i18next';
import { MetricCard } from '../shared/MetricCard';
import { formatCurrency, formatPercent, formatTokens } from '../utils/formatters';
import { Sparkles, Zap, MessageCircle, GitPullRequest, Cpu, Code, CheckCircle, FileText } from 'lucide-react';
import { ArtifactsPanel } from '../artifacts';

// Feature type icons
const FEATURE_ICONS: Record<string, React.ReactNode> = {
  ideation: <Zap className="h-4 w-4" />,
  insights: <MessageCircle className="h-4 w-4" />,
  roadmap: <Sparkles className="h-4 w-4" />,
  pr_review: <GitPullRequest className="h-4 w-4" />,
  pr_review_engine: <GitPullRequest className="h-4 w-4" />,
  batch_analyzer: <FileText className="h-4 w-4" />,
  planner: <FileText className="h-4 w-4" />,
  coder: <Code className="h-4 w-4" />,
  qa_reviewer: <CheckCircle className="h-4 w-4" />,
  qa_fixer: <CheckCircle className="h-4 w-4" />,
};

// Feature display names
const FEATURE_NAMES: Record<string, string> = {
  ideation: 'Ideation',
  ideation_code_improvements: 'Code Improvements',
  ideation_ui_ux: 'UI/UX Ideas',
  ideation_security: 'Security Ideas',
  ideation_performance: 'Performance Ideas',
  insights: 'Insights Chat',
  roadmap: 'Roadmap',
  roadmap_analyzer: 'Roadmap Analysis',
  pr_review: 'PR Review',
  pr_review_engine: 'PR Review',
  batch_analyzer: 'Batch Analysis',
  planner: 'Build - Planner',
  coder: 'Build - Coder',
  qa_reviewer: 'Build - QA Review',
  qa_fixer: 'Build - QA Fixer',
  spec_gatherer: 'Spec - Gatherer',
  spec_writer: 'Spec - Writer',
};

interface FeatureUsage {
  feature: string;
  tokens: number;
  cost: number;
  trace_count: number;
  percentage: number;
}

interface ModelUsage {
  model: string;
  tokens: number;
  cost: number;
  percentage: number;
}

interface TechLeadTabProps {
  data: {
    budget: { used: number; total: number; projected: number };
    teamMetrics: { specsCompleted: number; avgROI: number; efficiency: string };
    featureUsage: FeatureUsage[];
    modelDistribution: ModelUsage[];
  };
  loading?: boolean;
  projectId?: string;
}

export function TechLeadTab({ data, loading, projectId }: TechLeadTabProps) {
  const { t } = useTranslation(['analytics']);

  const budgetPercent = (data.budget.used / data.budget.total) * 100;
  const isOverBudget = data.budget.projected > data.budget.total;

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg" />
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
      {/* Budget tracker */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('techLead.budgetTracker')}
          </h3>
          <span className={`text-sm font-bold ${isOverBudget ? 'text-red-600' : 'text-green-600'}`}>
            {formatCurrency(data.budget.used)} / {formatCurrency(data.budget.total)}
          </span>
        </div>
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full ${budgetPercent > 80 ? 'bg-red-500' : budgetPercent > 60 ? 'bg-yellow-500' : 'bg-green-500'}`}
            style={{ width: `${Math.min(100, budgetPercent)}%` }}
          />
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
          {t('techLead.projected')}: {formatCurrency(data.budget.projected)}
          {isOverBudget && <span className="text-red-500 ml-2">{t('techLead.overBudget')}</span>}
        </p>
      </div>

      {/* Team metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          title="techLead.specsCompleted"
          value={data.teamMetrics.specsCompleted}
        />
        <MetricCard
          title="techLead.avgROI"
          value={formatPercent(data.teamMetrics.avgROI)}
          trend={{ value: data.teamMetrics.avgROI, isPositive: data.teamMetrics.avgROI > 0 }}
        />
        <MetricCard
          title="techLead.efficiency"
          value={data.teamMetrics.efficiency}
        />
      </div>

      {/* Feature Usage - Where is money being spent? */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
          {t('techLead.featureUsage', 'Cost by Feature')}
        </h3>
        {data.featureUsage.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('techLead.noFeatureData', 'No feature usage data yet. Run some AI features to see cost breakdown.')}
          </p>
        ) : (
          <div className="space-y-3">
            {data.featureUsage.map((feature) => {
              const icon = FEATURE_ICONS[feature.feature] || FEATURE_ICONS[feature.feature.split('_')[0]] || <Cpu className="h-4 w-4" />;
              const displayName = FEATURE_NAMES[feature.feature] || feature.feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

              return (
                <div key={feature.feature} className="flex items-center gap-3">
                  <div className="flex items-center gap-2 w-40">
                    <span className="text-blue-500">{icon}</span>
                    <span className="text-sm text-gray-600 dark:text-gray-400 truncate">{displayName}</span>
                  </div>
                  <div className="flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500" style={{ width: `${feature.percentage}%` }} />
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="w-16 text-right text-gray-500">{formatTokens(feature.tokens)}</span>
                    <span className="w-20 text-right font-medium text-gray-700 dark:text-gray-300">
                      {formatCurrency(feature.cost)}
                    </span>
                    <span className="w-12 text-right text-gray-400">{feature.percentage.toFixed(1)}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Model Distribution - Which models are being used? */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
          {t('techLead.modelDistribution', 'Cost by Model')}
        </h3>
        {data.modelDistribution.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('techLead.noModelData', 'No model usage data yet.')}
          </p>
        ) : (
          <div className="space-y-3">
            {data.modelDistribution.map((model) => {
              // Shorten model names for display
              const displayName = model.model
                .replace('claude-', '')
                .replace('-20250514', '')
                .replace('-20251101', '')
                .replace('opus-4-5', 'Opus 4.5')
                .replace('sonnet-4', 'Sonnet 4')
                .replace('haiku-3-5', 'Haiku 3.5');

              return (
                <div key={model.model} className="flex items-center gap-3">
                  <div className="flex items-center gap-2 w-32">
                    <Cpu className="h-4 w-4 text-purple-500" />
                    <span className="text-sm text-gray-600 dark:text-gray-400 truncate">{displayName}</span>
                  </div>
                  <div className="flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div className="h-full bg-purple-500" style={{ width: `${model.percentage}%` }} />
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="w-16 text-right text-gray-500">{formatTokens(model.tokens)}</span>
                    <span className="w-20 text-right font-medium text-gray-700 dark:text-gray-300">
                      {formatCurrency(model.cost)}
                    </span>
                    <span className="w-12 text-right text-gray-400">{model.percentage.toFixed(1)}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Generated Artifacts - What was actually produced? */}
      <ArtifactsPanel projectId={projectId} />
    </div>
  );
}

export default TechLeadTab;
