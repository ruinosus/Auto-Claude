import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { getLocalArtifacts, Artifact, searchArtifacts } from '../../../services/analytics-api';
import { formatCurrency } from '../utils/formatters';
import { ArtifactSearch } from './ArtifactSearch';
import type { ArtifactSearchParams, RichLocalArtifact } from '../../../../shared/types/analytics-v2';

// Group artifacts by agent_type for display (similar to trace grouping)
interface ArtifactGroup {
  agent_type: string;
  label: string;
  timestamp: string;
  artifacts: Artifact[];
  total_value_usd: number;
  artifact_count: number;
}
import { MermaidPreview } from './MermaidPreview';
import { MarkdownPreview } from './MarkdownPreview';
import { ArtifactDetailModal } from './ArtifactDetailModal';
import {
  GitBranch,
  Code,
  Shield,
  Lightbulb,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Copy,
  Check,
  Bug,
  TestTube,
  FileText,
  Server,
  Gauge,
  DollarSign,
  MessageSquare,
  Wrench,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ListChecks,
  Target,
  GitCommit,
  Layers,
  Search,
  Brain,
  BookOpen,
  GitMerge,
  Tag,
  Users,
  Zap,
  Eye,
  ClipboardList,
  Maximize2
} from 'lucide-react';
import { ArtifactTab, ArtifactType } from '../../../services/analytics-api';

// Artifact type icons and colors
const ARTIFACT_CONFIG: Record<string, { icon: React.ReactNode; color: string; bg: string; label: string }> = {
  // Roadmap artifacts
  roadmap_feature: { icon: <Target className="h-4 w-4" />, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Feature' },
  roadmap_item: { icon: <ListChecks className="h-4 w-4" />, color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: 'Roadmap Item' },
  roadmap_phase: { icon: <Layers className="h-4 w-4" />, color: 'text-indigo-400', bg: 'bg-indigo-500/10', label: 'Phase' },
  milestone: { icon: <Target className="h-4 w-4" />, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Milestone' },
  priority_decision: { icon: <Zap className="h-4 w-4" />, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Priority' },
  priority_recommendation: { icon: <Zap className="h-4 w-4" />, color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Priority Rec' },

  // Ideation artifacts
  idea: { icon: <Lightbulb className="h-4 w-4" />, color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'Idea' },

  // Insights & General
  diagram: { icon: <GitBranch className="h-4 w-4" />, color: 'text-purple-400', bg: 'bg-purple-500/10', label: 'Diagram' },
  code_example: { icon: <Code className="h-4 w-4" />, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Code' },
  security_finding: { icon: <Shield className="h-4 w-4" />, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Security' },
  recommendation: { icon: <Lightbulb className="h-4 w-4" />, color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'Recommendation' },
  bug_fix: { icon: <Bug className="h-4 w-4" />, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Bug Fix' },
  test_case: { icon: <TestTube className="h-4 w-4" />, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Test' },
  documentation: { icon: <FileText className="h-4 w-4" />, color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: 'Docs' },
  api_design: { icon: <Server className="h-4 w-4" />, color: 'text-indigo-400', bg: 'bg-indigo-500/10', label: 'API' },
  performance_insight: { icon: <Gauge className="h-4 w-4" />, color: 'text-pink-400', bg: 'bg-pink-500/10', label: 'Performance' },
  cost_analysis: { icon: <DollarSign className="h-4 w-4" />, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Cost' },

  // PR/MR Review
  review_comment: { icon: <MessageSquare className="h-4 w-4" />, color: 'text-blue-300', bg: 'bg-blue-500/10', label: 'Comment' },
  code_suggestion: { icon: <Code className="h-4 w-4" />, color: 'text-teal-400', bg: 'bg-teal-500/10', label: 'Suggestion' },
  security_issue: { icon: <Shield className="h-4 w-4" />, color: 'text-red-500', bg: 'bg-red-500/10', label: 'Security Issue' },
  bug_detected: { icon: <Bug className="h-4 w-4" />, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Bug Detected' },
  approval_decision: { icon: <CheckCircle className="h-4 w-4" />, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Approval' },
  style_issue: { icon: <Eye className="h-4 w-4" />, color: 'text-gray-400', bg: 'bg-gray-500/10', label: 'Style' },

  // QA
  qa_finding: { icon: <Search className="h-4 w-4" />, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'QA Finding' },
  qa_verdict: { icon: <CheckCircle className="h-4 w-4" />, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Verdict' },
  test_suggestion: { icon: <TestTube className="h-4 w-4" />, color: 'text-lime-400', bg: 'bg-lime-500/10', label: 'Test Suggestion' },
  acceptance_check: { icon: <ListChecks className="h-4 w-4" />, color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: 'Acceptance' },
  fix_applied: { icon: <Wrench className="h-4 w-4" />, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Fix Applied' },
  issue_resolution: { icon: <CheckCircle className="h-4 w-4" />, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Resolved' },
  test_fix: { icon: <TestTube className="h-4 w-4" />, color: 'text-green-300', bg: 'bg-green-500/10', label: 'Test Fix' },

  // Planning & Build
  implementation_plan: { icon: <ClipboardList className="h-4 w-4" />, color: 'text-purple-400', bg: 'bg-purple-500/10', label: 'Plan' },
  subtask_definition: { icon: <ListChecks className="h-4 w-4" />, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Subtask' },
  architecture_decision: { icon: <Layers className="h-4 w-4" />, color: 'text-indigo-400', bg: 'bg-indigo-500/10', label: 'Architecture' },
  risk_assessment: { icon: <AlertTriangle className="h-4 w-4" />, color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Risk' },
  dependency_identified: { icon: <GitBranch className="h-4 w-4" />, color: 'text-gray-400', bg: 'bg-gray-500/10', label: 'Dependency' },
  code_implementation: { icon: <Code className="h-4 w-4" />, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Implementation' },
  commit_summary: { icon: <GitCommit className="h-4 w-4" />, color: 'text-gray-400', bg: 'bg-gray-500/10', label: 'Commit' },
  refactoring: { icon: <Wrench className="h-4 w-4" />, color: 'text-violet-400', bg: 'bg-violet-500/10', label: 'Refactor' },
  test_written: { icon: <TestTube className="h-4 w-4" />, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Test Written' },

  // Spec Creation
  spec_document: { icon: <FileText className="h-4 w-4" />, color: 'text-purple-500', bg: 'bg-purple-500/10', label: 'Spec' },
  requirement_captured: { icon: <Target className="h-4 w-4" />, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Requirement' },
  context_discovered: { icon: <Search className="h-4 w-4" />, color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: 'Context' },
  complexity_assessment: { icon: <Gauge className="h-4 w-4" />, color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Complexity' },

  // Analysis
  architecture_insight: { icon: <Layers className="h-4 w-4" />, color: 'text-indigo-400', bg: 'bg-indigo-500/10', label: 'Architecture' },
  tech_debt_item: { icon: <AlertTriangle className="h-4 w-4" />, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Tech Debt' },
  security_audit: { icon: <Shield className="h-4 w-4" />, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Audit' },
  performance_bottleneck: { icon: <Zap className="h-4 w-4" />, color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'Bottleneck' },
  code_quality_score: { icon: <Target className="h-4 w-4" />, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Quality' },
  pattern_discovered: { icon: <Brain className="h-4 w-4" />, color: 'text-purple-400', bg: 'bg-purple-500/10', label: 'Pattern' },
  gotcha_identified: { icon: <AlertTriangle className="h-4 w-4" />, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Gotcha' },
  best_practice: { icon: <CheckCircle className="h-4 w-4" />, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Best Practice' },
  lesson_learned: { icon: <BookOpen className="h-4 w-4" />, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Lesson' },

  // Merge & Collaboration
  conflict_resolution: { icon: <GitMerge className="h-4 w-4" />, color: 'text-green-400', bg: 'bg-green-500/10', label: 'Resolution' },
  merge_decision: { icon: <GitMerge className="h-4 w-4" />, color: 'text-purple-400', bg: 'bg-purple-500/10', label: 'Merge' },
  code_choice: { icon: <Code className="h-4 w-4" />, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Choice' },

  // Issue Triage
  triage_classification: { icon: <Tag className="h-4 w-4" />, color: 'text-cyan-400', bg: 'bg-cyan-500/10', label: 'Classification' },
  priority_assignment: { icon: <Target className="h-4 w-4" />, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Priority' },
  label_suggestion: { icon: <Tag className="h-4 w-4" />, color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Label' },
  duplicate_detected: { icon: <XCircle className="h-4 w-4" />, color: 'text-gray-400', bg: 'bg-gray-500/10', label: 'Duplicate' },
  assignee_suggestion: { icon: <Users className="h-4 w-4" />, color: 'text-purple-400', bg: 'bg-purple-500/10', label: 'Assignee' },
};

// Map tabs to their relevant artifact types
const TAB_ARTIFACT_TYPES: Record<ArtifactTab, ArtifactType[]> = {
  overview: [], // Empty means show all
  dev: [
    'code_example', 'bug_fix', 'test_case', 'code_suggestion', 'bug_detected',
    'style_issue', 'test_suggestion', 'acceptance_check', 'fix_applied',
    'issue_resolution', 'test_fix', 'subtask_definition', 'dependency_identified',
    'code_implementation', 'commit_summary', 'refactoring', 'test_written',
    'tech_debt_item', 'code_quality_score', 'label_suggestion', 'code_choice'
  ],
  techlead: [
    'diagram', 'documentation', 'api_design', 'implementation_plan',
    'architecture_decision', 'spec_document', 'requirement_captured',
    'context_discovered', 'complexity_assessment', 'architecture_insight',
    'pattern_discovered', 'best_practice', 'merge_decision'
  ],
  ops: [
    'security_finding', 'performance_insight', 'security_issue', 'qa_finding',
    'qa_verdict', 'risk_assessment', 'security_audit', 'performance_bottleneck',
    'gotcha_identified', 'conflict_resolution', 'triage_classification',
    'duplicate_detected', 'assignee_suggestion'
  ],
  business: [
    'recommendation', 'cost_analysis', 'review_comment', 'approval_decision',
    'lesson_learned', 'priority_assignment'
  ],
};

interface ArtifactsPanelProps {
  projectId?: string;
  projectPath?: string;  // Project directory path for loading full artifact content
  className?: string;
  filterByTab?: ArtifactTab;
  title?: string;
}

// Selected artifact state for modal
interface SelectedArtifact {
  id: string;
  agentType: string;
  artifact: Artifact;
}

// Agent type labels for display
const AGENT_TYPE_LABELS: Record<string, string> = {
  roadmap_generator: 'Roadmap Generator',
  roadmap_features: 'Roadmap Features',
  ideation: 'Ideation',
  insights: 'Insights',
  insight_extractor: 'Insight Extractor',
  spec_creation: 'Spec Creation',
  competitor_analyzer: 'Competitor Analyzer',
  qa_reviewer: 'QA Reviewer',
  qa_fixer: 'QA Fixer',
  coder: 'Coder Agent',
  planner: 'Planner Agent',
  unknown: 'Other',
};

export function ArtifactsPanel({ projectId, projectPath, className = '', filterByTab, title }: ArtifactsPanelProps) {
  const { t } = useTranslation(['analytics']);
  const [groups, setGroups] = useState<ArtifactGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedArtifact, setSelectedArtifact] = useState<SelectedArtifact | null>(null);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [searchParams, setSearchParams] = useState<ArtifactSearchParams>({});
  const [isSearching, setIsSearching] = useState(false);

  // Handle search callback
  const handleSearch = useCallback(async (params: ArtifactSearchParams) => {
    setSearchParams(params);
    // Search will be applied via the useEffect below
  }, []);

  useEffect(() => {
    async function fetchArtifacts() {
      // Require projectPath to load local artifacts
      if (!projectPath) {
        setGroups([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setIsSearching(Object.keys(searchParams).length > 0);

        let artifacts: Artifact[] = [];

        // Use search if we have search params, otherwise use regular fetch
        const hasSearchParams = searchParams.query ||
          (searchParams.types && searchParams.types.length > 0) ||
          (searchParams.priorities && searchParams.priorities.length > 0) ||
          (searchParams.agent_types && searchParams.agent_types.length > 0) ||
          searchParams.has_rationale !== undefined ||
          searchParams.has_acceptance_criteria !== undefined ||
          searchParams.has_user_stories !== undefined ||
          searchParams.min_value !== undefined ||
          searchParams.max_value !== undefined;

        if (hasSearchParams) {
          const searchResponse = await searchArtifacts(projectPath, {
            ...searchParams,
            from_date: startDate || undefined,
            to_date: endDate || undefined,
            limit: 200,
          });
          // Cast RichLocalArtifact to Artifact (compatible base structure)
          artifacts = searchResponse.artifacts as unknown as Artifact[];
        } else {
          // Fetch directly from local storage - bypasses Langfuse trace_id requirement
          const response = await getLocalArtifacts({
            project_path: projectPath,
            from_date: startDate || undefined,
            to_date: endDate || undefined,
            limit: 200  // Higher limit since local storage
          });
          artifacts = response.artifacts as unknown as Artifact[];
        }

        // Group artifacts by agent_type
        const groupedByAgent = new Map<string, Artifact[]>();
        for (const artifact of artifacts) {
          const agentType = artifact.agent_type || 'unknown';
          if (!groupedByAgent.has(agentType)) {
            groupedByAgent.set(agentType, []);
          }
          groupedByAgent.get(agentType)!.push(artifact);
        }

        // Convert to ArtifactGroup format
        const artifactGroups: ArtifactGroup[] = Array.from(groupedByAgent.entries())
          .map(([agentType, artifacts]) => {
            // Sort artifacts by created_at descending
            artifacts.sort((a, b) => {
              const dateA = a.created_at || '';
              const dateB = b.created_at || '';
              return dateB.localeCompare(dateA);
            });

            const latestTimestamp = artifacts[0]?.created_at || new Date().toISOString();
            const totalValue = artifacts.reduce((sum, a) => sum + (a.value_usd || 0), 0);

            return {
              agent_type: agentType,
              label: AGENT_TYPE_LABELS[agentType] || agentType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
              timestamp: latestTimestamp,
              artifacts,
              total_value_usd: totalValue,
              artifact_count: artifacts.length,
            };
          })
          // Sort groups by total value descending
          .sort((a, b) => b.total_value_usd - a.total_value_usd);

        setGroups(artifactGroups);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load artifacts');
      } finally {
        setLoading(false);
      }
    }

    fetchArtifacts();
  }, [projectPath, startDate, endDate, searchParams]);

  // Clear date filters
  const clearDateFilters = () => {
    setStartDate('');
    setEndDate('');
  };

  // Filter artifacts by tab if specified
  const allowedTypes = filterByTab ? TAB_ARTIFACT_TYPES[filterByTab] : [];
  const filteredGroups = groups.map(group => {
    if (allowedTypes.length === 0) return group; // No filter, show all

    const filteredArtifacts = group.artifacts.filter(a =>
      allowedTypes.includes(a.type as ArtifactType) ||
      (a.tab && a.tab === filterByTab)
    );

    if (filteredArtifacts.length === 0) return null;

    // Recalculate value for filtered artifacts
    const filteredValue = filteredArtifacts.reduce((sum, a) => sum + (a.value_usd || 0), 0);

    return {
      ...group,
      artifacts: filteredArtifacts,
      artifact_count: filteredArtifacts.length,
      total_value_usd: filteredValue,
    };
  }).filter((group): group is ArtifactGroup => group !== null);

  const displayTitle = title || (filterByTab
    ? `${filterByTab.charAt(0).toUpperCase() + filterByTab.slice(1)} Artifacts`
    : 'Generated Artifacts');

  const toggleGroup = (agentType: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(agentType)) {
        next.delete(agentType);
      } else {
        next.add(agentType);
      }
      return next;
    });
  };

  const copyToClipboard = async (content: string, id: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const formatTimestamp = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className={`bg-[#1e1e2e] rounded-lg p-6 ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-1/3"></div>
          <div className="h-20 bg-gray-700 rounded"></div>
          <div className="h-20 bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-[#1e1e2e] rounded-lg p-6 ${className}`}>
        <p className="text-red-400">Error: {error}</p>
      </div>
    );
  }

  if (filteredGroups.length === 0) {
    return (
      <div className={`bg-[#1e1e2e] rounded-lg p-6 ${className}`}>
        <h3 className="text-lg font-semibold text-white mb-2">{displayTitle}</h3>
        <p className="text-gray-400 text-sm">
          {!projectPath
            ? 'Select a project to view artifacts.'
            : filterByTab
            ? `No ${filterByTab} artifacts found yet.`
            : 'No artifacts found. Run Roadmap, Ideation, or Insights to generate artifacts.'}
        </p>
      </div>
    );
  }

  // Calculate totals
  const totalValue = filteredGroups.reduce((sum, g) => sum + g.total_value_usd, 0);
  const totalArtifacts = filteredGroups.reduce((sum, g) => sum + g.artifact_count, 0);

  return (
    <div className={`bg-[#1e1e2e] rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">{displayTitle}</h3>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-gray-400">
            {totalArtifacts} artifacts
          </span>
          <span className="text-emerald-400 font-medium">
            {formatCurrency(totalValue)} value
          </span>
        </div>
      </div>

      {/* Artifact Search */}
      <ArtifactSearch
        onSearch={handleSearch}
        isLoading={loading || isSearching}
        className="mb-4"
      />

      {/* Date Range Filter */}
      <div className="flex items-center gap-3 mb-4 p-3 bg-gray-800/50 rounded-lg">
        <span className="text-sm text-gray-400">Date Range:</span>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="Start date"
          />
          <span className="text-gray-500">to</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:outline-none focus:border-blue-500"
            placeholder="End date"
          />
        </div>
        {(startDate || endDate) && (
          <button
            onClick={clearDateFilters}
            className="px-3 py-1.5 text-sm text-gray-300 hover:text-white bg-gray-700 hover:bg-gray-600 rounded border border-gray-600 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Artifact groups list */}
      <div className="space-y-3">
        {filteredGroups.map((group) => {
          const isExpanded = expandedGroups.has(group.agent_type);

          // Calculate artifact type breakdown
          const typeBreakdown = group.artifacts.reduce((acc, a) => {
            const type = a.type || 'unknown';
            if (!acc[type]) acc[type] = { count: 0, value: 0 };
            acc[type].count++;
            acc[type].value += a.value_usd || 0;
            return acc;
          }, {} as Record<string, { count: number; value: number }>);

          return (
            <div
              key={group.agent_type}
              className="border border-gray-700 rounded-lg overflow-hidden"
            >
              {/* Group header */}
              <button
                onClick={() => toggleGroup(group.agent_type)}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-400" />
                  )}
                  <div className="text-left">
                    <p className="text-white font-medium truncate max-w-md">
                      {group.label}
                    </p>
                    <p className="text-gray-500 text-xs mt-1">
                      {formatTimestamp(group.timestamp)} • {group.artifact_count} artifacts
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {/* Type breakdown pills */}
                  <div className="flex gap-2 flex-wrap">
                    {Object.entries(typeBreakdown)
                      .filter(([_, data]) => data.value > 0)
                      .sort((a, b) => b[1].value - a[1].value)
                      .slice(0, 4)
                      .map(([type, data]) => {
                        const artifactConfig = ARTIFACT_CONFIG[type];
                        const bgColor = artifactConfig?.bg || 'bg-gray-500/10';
                        const textColor = artifactConfig?.color || 'text-gray-400';
                        const label = artifactConfig?.label || type.replace(/_/g, ' ');
                        return (
                          <span key={type} className={`px-2 py-1 text-xs rounded-full ${bgColor} ${textColor}`}>
                            {label}: {formatCurrency(data.value)}
                          </span>
                        );
                      })}
                  </div>

                  <span className="text-emerald-400 font-semibold">
                    {formatCurrency(group.total_value_usd)}
                  </span>
                </div>
              </button>

              {/* Expanded content */}
              {isExpanded && group.artifacts.length > 0 && (
                <div className="border-t border-gray-700 p-4 bg-gray-900/30">
                  <div className="space-y-3">
                    {group.artifacts.map((artifact, idx) => {
                      const config = ARTIFACT_CONFIG[artifact.type] || ARTIFACT_CONFIG.code_example;
                      const artifactId = artifact.id || `${group.agent_type}-${idx}`;

                      return (
                        <div
                          key={artifactId}
                          className={`rounded-lg p-4 ${config.bg}`}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className={config.color}>{config.icon}</span>
                              <span className="text-white font-medium">{artifact.description || config.label}</span>
                              <span className="text-xs text-gray-500">({artifact.format})</span>
                              {artifact.created_at && (
                                <span className="text-xs text-gray-500">
                                  • {formatTimestamp(artifact.created_at)}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`text-sm font-medium ${config.color}`}>
                                {formatCurrency(artifact.value_usd || 0)}
                              </span>
                              <button
                                onClick={() => setSelectedArtifact({
                                  id: artifactId,
                                  agentType: group.agent_type,
                                  artifact
                                })}
                                className="p-1 hover:bg-gray-700 rounded transition-colors"
                                title="View full content"
                              >
                                <Maximize2 className="h-4 w-4 text-gray-400" />
                              </button>
                              <button
                                onClick={() => copyToClipboard(artifact.content || '', artifactId)}
                                className="p-1 hover:bg-gray-700 rounded transition-colors"
                                title="Copy content"
                              >
                                {copiedId === artifactId ? (
                                  <Check className="h-4 w-4 text-green-400" />
                                ) : (
                                  <Copy className="h-4 w-4 text-gray-400" />
                                )}
                              </button>
                            </div>
                          </div>

                          {/* Content preview - render based on type */}
                          {artifact.type === 'diagram' && artifact.format === 'mermaid' ? (
                            <MermaidPreview content={artifact.content || ''} />
                          ) : artifact.format === 'markdown' || artifact.type === 'documentation' ? (
                            <MarkdownPreview content={artifact.content || ''} />
                          ) : artifact.type === 'recommendation' ? (
                            <div className="bg-black/30 rounded p-4 text-sm text-gray-200 leading-relaxed">
                              <Lightbulb className="h-4 w-4 text-yellow-400 inline mr-2" />
                              {artifact.content || '(No content)'}
                            </div>
                          ) : artifact.type === 'security_finding' ? (
                            <div className="bg-black/30 rounded p-4 text-sm text-gray-200 leading-relaxed">
                              <div className="flex items-start gap-2">
                                <Shield className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
                                <div>
                                  {artifact.keyword && (
                                    <span className="inline-block px-2 py-0.5 mb-2 text-xs bg-red-500/20 text-red-300 rounded">
                                      {artifact.keyword}
                                    </span>
                                  )}
                                  <p>{artifact.content || '(No content)'}</p>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <pre className="text-xs text-gray-300 bg-black/30 rounded p-3 overflow-x-auto max-h-48">
                              {(artifact.content?.length || 0) > 500
                                ? artifact.content?.slice(0, 500) + '...'
                                : artifact.content || '(No content)'}
                            </pre>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Agent type info */}
                  <div className="mt-4 pt-3 border-t border-gray-700 flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      Agent: <code className="text-gray-400">{group.agent_type}</code>
                      {' • '}Source: <code className="text-gray-400">Local Storage</code>
                    </span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Artifact Detail Modal */}
      {selectedArtifact && (
        <ArtifactDetailModal
          isOpen={!!selectedArtifact}
          onClose={() => setSelectedArtifact(null)}
          projectId={projectId || ''}
          artifactId={selectedArtifact.id}
          initialArtifact={{
            type: selectedArtifact.artifact.type,
            content: selectedArtifact.artifact.content,
            value_usd: selectedArtifact.artifact.value_usd || 0,
            description: selectedArtifact.artifact.description || '',
            format: selectedArtifact.artifact.format,
            trace_id: selectedArtifact.artifact.trace_id,
            agent_type: selectedArtifact.agentType,
          }}
        />
      )}
    </div>
  );
}
