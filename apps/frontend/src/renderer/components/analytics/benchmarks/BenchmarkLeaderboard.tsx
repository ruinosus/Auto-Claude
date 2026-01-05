/**
 * BenchmarkLeaderboard Component
 * ===============================
 *
 * Displays project rankings with metrics comparison, best practices insights,
 * and improvement suggestions. Part of Module 6: Team/Project Benchmarks.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  useProjectRankings,
  useBestPractices,
  useImprovementSuggestions,
  usePercentileComparison,
} from '../../../hooks/useAnalyticsQuery';
import type {
  ProjectBenchmark,
  BestPractice,
  ProjectRankingsParams,
} from '../../../services/analytics-api';
import { formatCurrency, formatPercent } from '../utils/formatters';
import {
  Trophy,
  Medal,
  Award,
  TrendingUp,
  TrendingDown,
  Lightbulb,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Target,
  CheckCircle,
  XCircle,
  Minus,
  Info,
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../ui/select';
import { Badge } from '../../ui/badge';

// Medal icons for top 3 ranks
const RANK_ICONS: Record<number, React.ReactNode> = {
  1: <Trophy className="h-5 w-5 text-yellow-500" />,
  2: <Medal className="h-5 w-5 text-gray-400" />,
  3: <Award className="h-5 w-5 text-amber-600" />,
};

// Impact badge colors
const IMPACT_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
};

// Category badge colors
const CATEGORY_COLORS: Record<string, string> = {
  general: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  qa: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  agent: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
  iteration: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400',
  complexity: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
};

interface BenchmarkLeaderboardProps {
  currentProjectId?: string;
}

export function BenchmarkLeaderboard({ currentProjectId }: BenchmarkLeaderboardProps) {
  const { t } = useTranslation(['analytics']);

  // State for filters
  const [metric, setMetric] = useState<ProjectRankingsParams['metric']>('roi');
  const [period, setPeriod] = useState<ProjectRankingsParams['period']>('30d');
  const [expandedProject, setExpandedProject] = useState<string | null>(null);

  // Fetch data
  const { data: rankingsData, isLoading: rankingsLoading, error: rankingsError } = useProjectRankings({
    metric,
    period,
    limit: 10,
  });

  const { data: practicesData, isLoading: practicesLoading } = useBestPractices({
    top_n: 10,
  });

  const { data: suggestionsData } = useImprovementSuggestions(
    currentProjectId || null
  );

  const { data: percentileData } = usePercentileComparison(
    currentProjectId || null,
    { percentile: 50 }
  );

  // Loading state
  if (rankingsLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded-lg w-1/3" />
        <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      </div>
    );
  }

  // Error state
  if (rankingsError) {
    return (
      <div className="text-center py-8">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <p className="text-gray-600 dark:text-gray-400">
          {t('projectBenchmarks.error', 'Failed to load benchmark data')}
        </p>
      </div>
    );
  }

  const rankings = rankingsData?.rankings || [];
  const practices = practicesData?.practices || [];
  const suggestions = suggestionsData?.suggestions || [];

  return (
    <div className="space-y-6">
      {/* Header with filters */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200">
          {t('projectBenchmarks.title', 'Project Leaderboard')}
        </h2>

        <div className="flex items-center gap-3">
          {/* Metric selector */}
          <Select value={metric} onValueChange={(v) => setMetric(v as ProjectRankingsParams['metric'])}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder={t('projectBenchmarks.selectMetric', 'Select metric')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="roi">{t('projectBenchmarks.metrics.roi', 'Total ROI')}</SelectItem>
              <SelectItem value="value">{t('projectBenchmarks.metrics.value', 'Value Generated')}</SelectItem>
              <SelectItem value="success_rate">{t('projectBenchmarks.metrics.successRate', 'Success Rate')}</SelectItem>
            </SelectContent>
          </Select>

          {/* Period selector */}
          <Select value={period} onValueChange={(v) => setPeriod(v as ProjectRankingsParams['period'])}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder={t('projectBenchmarks.selectPeriod', 'Period')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">{t('dateRanges.7d', 'Last 7 days')}</SelectItem>
              <SelectItem value="30d">{t('dateRanges.30d', 'Last 30 days')}</SelectItem>
              <SelectItem value="90d">{t('dateRanges.90d', 'Last 90 days')}</SelectItem>
              <SelectItem value="all">{t('dateRanges.all', 'All time')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Current Project Percentile Comparison */}
      {currentProjectId && percentileData && Object.keys(percentileData.metrics).length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2 mb-3">
            <Target className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <h3 className="font-medium text-blue-800 dark:text-blue-200">
              {t('projectBenchmarks.yourPosition', 'Your Position vs Median')}
            </h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(percentileData.metrics).map(([metricName, comparison]) => (
              <div key={metricName} className="flex flex-col">
                <span className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                  {metricName.replace(/_/g, ' ')}
                </span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-800 dark:text-gray-200">
                    {metricName.includes('roi') || metricName.includes('rate')
                      ? formatPercent(comparison.project_value)
                      : metricName.includes('value') || metricName.includes('cost')
                        ? formatCurrency(comparison.project_value)
                        : comparison.project_value.toFixed(1)}
                  </span>
                  {comparison.status === 'above' && (
                    <TrendingUp className="h-4 w-4 text-green-500" />
                  )}
                  {comparison.status === 'below' && (
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  )}
                  {comparison.status === 'equal' && (
                    <Minus className="h-4 w-4 text-gray-400" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rankings Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('projectBenchmarks.rank', 'Rank')}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('projectBenchmarks.project', 'Project')}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('projectBenchmarks.totalROI', 'Total ROI')}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('projectBenchmarks.value', 'Value')}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('projectBenchmarks.successRate', 'Success')}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('projectBenchmarks.specs', 'Specs')}
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('projectBenchmarks.details', 'Details')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {rankings.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                    {t('projectBenchmarks.noData', 'No benchmark data available')}
                  </td>
                </tr>
              ) : (
                rankings.map((project) => (
                  <ProjectRow
                    key={project.project_id}
                    project={project}
                    isCurrentProject={project.project_id === currentProjectId}
                    isExpanded={expandedProject === project.project_id}
                    onToggle={() => setExpandedProject(
                      expandedProject === project.project_id ? null : project.project_id
                    )}
                    t={t}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Best Practices Panel */}
      {practices.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb className="h-5 w-5 text-yellow-500" />
            <h3 className="font-semibold text-gray-800 dark:text-gray-200">
              {t('projectBenchmarks.bestPractices', 'Best Practices from Top Performers')}
            </h3>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            {t('projectBenchmarks.bestPracticesDesc', 'Patterns identified from analyzing the top {{count}} performing projects', { count: practicesData?.analyzed_projects || 10 })}
          </p>
          <div className="space-y-4">
            {practices.map((practice, index) => (
              <BestPracticeCard key={index} practice={practice} t={t} />
            ))}
          </div>
        </div>
      )}

      {/* Improvement Suggestions */}
      {currentProjectId && suggestions.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <Info className="h-5 w-5 text-blue-500" />
            <h3 className="font-semibold text-gray-800 dark:text-gray-200">
              {t('projectBenchmarks.suggestions', 'Improvement Suggestions')}
            </h3>
            {suggestionsData?.current_rank && (
              <Badge variant="outline" className="ml-2">
                {t('projectBenchmarks.currentRank', 'Rank #{{rank}} of {{total}}', {
                  rank: suggestionsData.current_rank,
                  total: suggestionsData.total_projects,
                })}
              </Badge>
            )}
          </div>
          <ul className="space-y-3">
            {suggestions.map((suggestion, index) => (
              <li key={index} className="flex items-start gap-3">
                <div className="mt-1 p-1 rounded-full bg-blue-100 dark:bg-blue-900/30">
                  <Target className="h-3 w-3 text-blue-600 dark:text-blue-400" />
                </div>
                <span className="text-sm text-gray-700 dark:text-gray-300">{suggestion}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// Helper component for project row
interface ProjectRowProps {
  project: ProjectBenchmark;
  isCurrentProject: boolean;
  isExpanded: boolean;
  onToggle: () => void;
  t: ReturnType<typeof useTranslation>['t'];
}

function ProjectRow({ project, isCurrentProject, isExpanded, onToggle, t }: ProjectRowProps) {
  const rankIcon = RANK_ICONS[project.rank];

  return (
    <>
      <tr className={`${isCurrentProject ? 'bg-blue-50 dark:bg-blue-900/20' : ''} hover:bg-gray-50 dark:hover:bg-gray-900/30`}>
        <td className="px-4 py-4">
          <div className="flex items-center gap-2">
            {rankIcon || <span className="w-5 text-center text-gray-500">#{project.rank}</span>}
          </div>
        </td>
        <td className="px-4 py-4">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-800 dark:text-gray-200 truncate max-w-[200px]">
              {project.project_id}
            </span>
            {isCurrentProject && (
              <Badge variant="outline" className="text-xs">
                {t('projectBenchmarks.you', 'You')}
              </Badge>
            )}
          </div>
        </td>
        <td className="px-4 py-4 text-right">
          <span className={`font-semibold ${project.total_roi > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
            {formatPercent(project.total_roi)}
          </span>
        </td>
        <td className="px-4 py-4 text-right">
          <span className="text-gray-700 dark:text-gray-300">
            {formatCurrency(project.total_value_generated)}
          </span>
        </td>
        <td className="px-4 py-4 text-right">
          <span className="text-gray-700 dark:text-gray-300">
            {formatPercent(project.success_rate)}
          </span>
        </td>
        <td className="px-4 py-4 text-right">
          <span className="text-gray-500 dark:text-gray-400">{project.specs_count}</span>
        </td>
        <td className="px-4 py-4 text-center">
          <button
            onClick={onToggle}
            className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-gray-500" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-500" />
            )}
          </button>
        </td>
      </tr>
      {isExpanded && (
        <tr className={isCurrentProject ? 'bg-blue-50/50 dark:bg-blue-900/10' : 'bg-gray-50 dark:bg-gray-900/20'}>
          <td colSpan={7} className="px-4 py-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('projectBenchmarks.avgROI', 'Avg ROI/Spec')}</span>
                <p className="font-medium text-gray-800 dark:text-gray-200">{formatPercent(project.avg_roi_per_spec)}</p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('projectBenchmarks.totalCost', 'Total Cost')}</span>
                <p className="font-medium text-gray-800 dark:text-gray-200">{formatCurrency(project.total_cost)}</p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('projectBenchmarks.avgQAAttempts', 'Avg QA Attempts')}</span>
                <p className="font-medium text-gray-800 dark:text-gray-200">{project.avg_qa_attempts.toFixed(1)}</p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('projectBenchmarks.bestFeature', 'Best Feature')}</span>
                <p className="font-medium text-gray-800 dark:text-gray-200 capitalize">{project.best_feature_type.replace(/_/g, ' ')}</p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// Helper component for best practice card
interface BestPracticeCardProps {
  practice: BestPractice;
  t: ReturnType<typeof useTranslation>['t'];
}

function BestPracticeCard({ practice, t }: BestPracticeCardProps) {
  return (
    <div className="flex items-start gap-4 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/30">
      <div className="mt-1">
        <CheckCircle className="h-5 w-5 text-green-500" />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-gray-800 dark:text-gray-200 capitalize">
            {practice.pattern.replace(/_/g, ' ')}
          </span>
          <Badge className={IMPACT_COLORS[practice.impact]}>
            {t(`projectBenchmarks.impact.${practice.impact}`, practice.impact)}
          </Badge>
          <Badge className={CATEGORY_COLORS[practice.category]}>
            {practice.category}
          </Badge>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
          {practice.description}
        </p>
        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
          <span>
            {t('projectBenchmarks.adoptionRate', '{{rate}}% adoption rate', { rate: practice.adoption_rate.toFixed(0) })}
          </span>
          {practice.examples.length > 0 && (
            <span>
              {t('projectBenchmarks.examples', 'Examples: {{examples}}', { examples: practice.examples.slice(0, 2).join(', ') })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default BenchmarkLeaderboard;
