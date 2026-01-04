import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Search,
  Filter,
  X,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  Tag,
  Gauge,
  DollarSign,
  Bot
} from 'lucide-react';
import type { ArtifactSearchParams } from '../../../../shared/types/analytics-v2';

interface ArtifactSearchProps {
  onSearch: (params: ArtifactSearchParams) => void;
  isLoading?: boolean;
  className?: string;
}

const ARTIFACT_TYPES = [
  'roadmap_feature',
  'security_issue',
  'ideation_item',
  'idea',
  'recommendation',
  'diagram',
  'code_example',
  'documentation',
  'insight',
];

const PRIORITIES = ['must', 'should', 'could', 'wont'];

const AGENT_TYPES = [
  'roadmap_generator',
  'ideation',
  'insights',
  'insight_extractor',
  'spec_creation',
  'qa_reviewer',
  'qa_fixer',
  'coder',
  'planner',
];

export function ArtifactSearch({ onSearch, isLoading, className = '' }: ArtifactSearchProps) {
  const { t } = useTranslation(['analytics']);

  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedPriorities, setSelectedPriorities] = useState<string[]>([]);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [hasRationale, setHasRationale] = useState<boolean | undefined>(undefined);
  const [hasAcceptanceCriteria, setHasAcceptanceCriteria] = useState<boolean | undefined>(undefined);
  const [hasUserStories, setHasUserStories] = useState<boolean | undefined>(undefined);
  const [minValue, setMinValue] = useState<string>('');
  const [maxValue, setMaxValue] = useState<string>('');

  const handleSearch = useCallback(() => {
    const params: ArtifactSearchParams = {
      query: query || undefined,
      types: selectedTypes.length > 0 ? selectedTypes : undefined,
      priorities: selectedPriorities.length > 0 ? selectedPriorities : undefined,
      agent_types: selectedAgents.length > 0 ? selectedAgents : undefined,
      has_rationale: hasRationale,
      has_acceptance_criteria: hasAcceptanceCriteria,
      has_user_stories: hasUserStories,
      min_value: minValue ? parseFloat(minValue) : undefined,
      max_value: maxValue ? parseFloat(maxValue) : undefined,
    };
    onSearch(params);
  }, [
    query,
    selectedTypes,
    selectedPriorities,
    selectedAgents,
    hasRationale,
    hasAcceptanceCriteria,
    hasUserStories,
    minValue,
    maxValue,
    onSearch,
  ]);

  const clearFilters = () => {
    setQuery('');
    setSelectedTypes([]);
    setSelectedPriorities([]);
    setSelectedAgents([]);
    setHasRationale(undefined);
    setHasAcceptanceCriteria(undefined);
    setHasUserStories(undefined);
    setMinValue('');
    setMaxValue('');
    onSearch({});
  };

  const hasActiveFilters =
    query ||
    selectedTypes.length > 0 ||
    selectedPriorities.length > 0 ||
    selectedAgents.length > 0 ||
    hasRationale !== undefined ||
    hasAcceptanceCriteria !== undefined ||
    hasUserStories !== undefined ||
    minValue ||
    maxValue;

  const toggleArrayValue = (arr: string[], value: string, setter: (v: string[]) => void) => {
    if (arr.includes(value)) {
      setter(arr.filter((v) => v !== value));
    } else {
      setter([...arr, value]);
    }
  };

  const toggleBooleanFilter = (
    current: boolean | undefined,
    setter: (v: boolean | undefined) => void
  ) => {
    if (current === undefined) {
      setter(true);
    } else if (current === true) {
      setter(false);
    } else {
      setter(undefined);
    }
  };

  const getBooleanButtonClass = (value: boolean | undefined) => {
    if (value === true) return 'bg-green-500/20 text-green-400 border-green-500/30';
    if (value === false) return 'bg-red-500/20 text-red-400 border-red-500/30';
    return 'bg-gray-700 text-gray-400 border-gray-600';
  };

  const getBooleanLabel = (value: boolean | undefined, label: string) => {
    if (value === true) return `${label}`;
    if (value === false) return `No ${label}`;
    return label;
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Search Bar */}
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder={t('analytics:artifacts.searchPlaceholder')}
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 text-sm"
          />
        </div>

        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
            hasActiveFilters
              ? 'bg-purple-500/20 border-purple-500/30 text-purple-400'
              : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'
          }`}
        >
          <Filter className="h-4 w-4" />
          {t('analytics:artifacts.filters')}
          {showFilters ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>

        <button
          onClick={handleSearch}
          disabled={isLoading}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors disabled:opacity-50 text-sm font-medium"
        >
          {t('analytics:artifacts.search')}
        </button>
      </div>

      {/* Expanded Filters */}
      {showFilters && (
        <div className="bg-gray-800/50 rounded-lg p-4 space-y-4 border border-gray-700">
          {/* Type Filter */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-400 mb-2">
              <Tag className="h-4 w-4" />
              {t('analytics:artifacts.type')}
            </label>
            <div className="flex flex-wrap gap-2">
              {ARTIFACT_TYPES.map((type) => (
                <button
                  key={type}
                  onClick={() => toggleArrayValue(selectedTypes, type, setSelectedTypes)}
                  className={`px-3 py-1 rounded-full text-xs transition-colors ${
                    selectedTypes.includes(type)
                      ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      : 'bg-gray-700 text-gray-400 border border-gray-600 hover:bg-gray-600'
                  }`}
                >
                  {t(`analytics:artifacts.types.${type}`, type.replace(/_/g, ' '))}
                </button>
              ))}
            </div>
          </div>

          {/* Priority Filter */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-400 mb-2">
              <Gauge className="h-4 w-4" />
              {t('analytics:artifacts.priority')}
            </label>
            <div className="flex flex-wrap gap-2">
              {PRIORITIES.map((priority) => (
                <button
                  key={priority}
                  onClick={() =>
                    toggleArrayValue(selectedPriorities, priority, setSelectedPriorities)
                  }
                  className={`px-3 py-1 rounded-full text-xs transition-colors ${
                    selectedPriorities.includes(priority)
                      ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                      : 'bg-gray-700 text-gray-400 border border-gray-600 hover:bg-gray-600'
                  }`}
                >
                  {t(`analytics:artifacts.priorities.${priority}`, priority)}
                </button>
              ))}
            </div>
          </div>

          {/* Agent Type Filter */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-400 mb-2">
              <Bot className="h-4 w-4" />
              {t('analytics:artifacts.metadata.agent')}
            </label>
            <div className="flex flex-wrap gap-2">
              {AGENT_TYPES.map((agent) => (
                <button
                  key={agent}
                  onClick={() => toggleArrayValue(selectedAgents, agent, setSelectedAgents)}
                  className={`px-3 py-1 rounded-full text-xs transition-colors ${
                    selectedAgents.includes(agent)
                      ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                      : 'bg-gray-700 text-gray-400 border border-gray-600 hover:bg-gray-600'
                  }`}
                >
                  {agent.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Quality Filters */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-400 mb-2">
              <CheckCircle className="h-4 w-4" />
              {t('analytics:artifacts.quality.title')}
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => toggleBooleanFilter(hasRationale, setHasRationale)}
                className={`px-3 py-1 rounded-full text-xs border transition-colors ${getBooleanButtonClass(
                  hasRationale
                )}`}
              >
                {getBooleanLabel(hasRationale, t('analytics:artifacts.quality.hasRationale'))}
              </button>
              <button
                onClick={() =>
                  toggleBooleanFilter(hasAcceptanceCriteria, setHasAcceptanceCriteria)
                }
                className={`px-3 py-1 rounded-full text-xs border transition-colors ${getBooleanButtonClass(
                  hasAcceptanceCriteria
                )}`}
              >
                {getBooleanLabel(
                  hasAcceptanceCriteria,
                  t('analytics:artifacts.quality.hasAcceptanceCriteria')
                )}
              </button>
              <button
                onClick={() => toggleBooleanFilter(hasUserStories, setHasUserStories)}
                className={`px-3 py-1 rounded-full text-xs border transition-colors ${getBooleanButtonClass(
                  hasUserStories
                )}`}
              >
                {getBooleanLabel(hasUserStories, t('analytics:artifacts.quality.hasUserStories'))}
              </button>
            </div>
          </div>

          {/* Value Range */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-gray-400 mb-2">
              <DollarSign className="h-4 w-4" />
              Value Range
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={minValue}
                onChange={(e) => setMinValue(e.target.value)}
                placeholder="Min $"
                className="w-24 px-3 py-1 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              />
              <span className="text-gray-500">to</span>
              <input
                type="number"
                value={maxValue}
                onChange={(e) => setMaxValue(e.target.value)}
                placeholder="Max $"
                className="w-24 px-3 py-1 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Clear Filters Button */}
          {hasActiveFilters && (
            <div className="flex justify-end pt-2 border-t border-gray-700">
              <button
                onClick={clearFilters}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-300 hover:text-white bg-gray-700 hover:bg-gray-600 rounded transition-colors"
              >
                <X className="h-4 w-4" />
                {t('analytics:artifacts.clearFilters')}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
