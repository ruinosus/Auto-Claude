import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { getArtifacts, ArtifactTrace, Artifact } from '../../../services/analytics-api';
import { formatCurrency } from '../utils/formatters';
import { MermaidPreview } from './MermaidPreview';
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
  traceId: string;
  artifact: Artifact;
}

export function ArtifactsPanel({ projectId, projectPath, className = '', filterByTab, title }: ArtifactsPanelProps) {
  const { t } = useTranslation(['analytics']);
  const [traces, setTraces] = useState<ArtifactTrace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTraces, setExpandedTraces] = useState<Set<string>>(new Set());
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedArtifact, setSelectedArtifact] = useState<SelectedArtifact | null>(null);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  useEffect(() => {
    async function fetchArtifacts() {
      try {
        setLoading(true);
        // Pass project_path to load full artifact content from local storage
        const response = await getArtifacts({
          project_id: projectId,
          project_path: projectPath,
          limit: 20
        });
        setTraces(response.artifacts);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load artifacts');
      } finally {
        setLoading(false);
      }
    }

    fetchArtifacts();
  }, [projectId, projectPath]);

  // Filter traces by date range
  const filterByDateRange = (tracesToFilter: ArtifactTrace[]): ArtifactTrace[] => {
    if (!startDate && !endDate) return tracesToFilter;

    return tracesToFilter.filter(trace => {
      const traceDate = new Date(trace.timestamp);
      // Set time to start of day for comparison
      const traceDateOnly = new Date(traceDate.getFullYear(), traceDate.getMonth(), traceDate.getDate());

      if (startDate) {
        const start = new Date(startDate);
        if (traceDateOnly < start) return false;
      }

      if (endDate) {
        const end = new Date(endDate);
        // Include the end date by checking if trace is before end of day
        if (traceDateOnly > end) return false;
      }

      return true;
    });
  };

  // Clear date filters
  const clearDateFilters = () => {
    setStartDate('');
    setEndDate('');
  };

  // Filter artifacts by tab if specified
  const allowedTypes = filterByTab ? TAB_ARTIFACT_TYPES[filterByTab] : [];
  const tabFilteredTraces = traces.map(trace => {
    if (allowedTypes.length === 0) return trace; // No filter, show all

    const filteredArtifacts = trace.artifacts.filter(a =>
      allowedTypes.includes(a.type as ArtifactType) ||
      (a.tab && a.tab === filterByTab)
    );

    if (filteredArtifacts.length === 0) return null;

    // Recalculate value for filtered artifacts
    const filteredValue = filteredArtifacts.reduce((sum, a) => sum + a.value_usd, 0);

    return {
      ...trace,
      artifacts: filteredArtifacts,
      artifact_count: filteredArtifacts.length,
      total_value_usd: filteredValue,
    };
  }).filter((trace): trace is ArtifactTrace => trace !== null);

  // Apply date range filter after tab filter
  const filteredTraces = filterByDateRange(tabFilteredTraces);

  const displayTitle = title || (filterByTab
    ? `${filterByTab.charAt(0).toUpperCase() + filterByTab.slice(1)} Artifacts`
    : 'Generated Artifacts');

  const toggleTrace = (traceId: string) => {
    setExpandedTraces(prev => {
      const next = new Set(prev);
      if (next.has(traceId)) {
        next.delete(traceId);
      } else {
        next.add(traceId);
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

  if (filteredTraces.length === 0) {
    return (
      <div className={`bg-[#1e1e2e] rounded-lg p-6 ${className}`}>
        <h3 className="text-lg font-semibold text-white mb-2">{displayTitle}</h3>
        <p className="text-gray-400 text-sm">
          {filterByTab
            ? `No ${filterByTab} artifacts found yet.`
            : 'No artifacts found. Run an Insights chat to generate diagrams, recommendations, and more.'}
        </p>
      </div>
    );
  }

  // Calculate totals
  const totalValue = filteredTraces.reduce((sum, t) => sum + t.total_value_usd, 0);
  const totalArtifacts = filteredTraces.reduce((sum, t) => sum + t.artifact_count, 0);

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

      {/* Traces list */}
      <div className="space-y-3">
        {filteredTraces.map((trace) => {
          const isExpanded = expandedTraces.has(trace.trace_id);

          return (
            <div
              key={trace.trace_id}
              className="border border-gray-700 rounded-lg overflow-hidden"
            >
              {/* Trace header */}
              <button
                onClick={() => toggleTrace(trace.trace_id)}
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
                      {trace.query}
                    </p>
                    <p className="text-gray-500 text-xs mt-1">
                      {formatTimestamp(trace.timestamp)} • {trace.artifact_count} artifacts
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {/* Value breakdown pills - dynamically generated for all artifact types */}
                  <div className="flex gap-2 flex-wrap">
                    {Object.entries(trace.value_breakdown)
                      .filter(([_, value]) => value > 0)
                      .slice(0, 4) // Limit to 4 pills to avoid overflow
                      .map(([type, value]) => {
                        // Map type to display label and colors
                        const typeConfig: Record<string, { label: string; bgColor: string; textColor: string }> = {
                          diagrams: { label: 'Diagrams', bgColor: 'bg-purple-500/10', textColor: 'text-purple-400' },
                          diagram: { label: 'Diagram', bgColor: 'bg-purple-500/10', textColor: 'text-purple-400' },
                          security: { label: 'Security', bgColor: 'bg-red-500/10', textColor: 'text-red-400' },
                          security_finding: { label: 'Security', bgColor: 'bg-red-500/10', textColor: 'text-red-400' },
                          recommendations: { label: 'Recs', bgColor: 'bg-yellow-500/10', textColor: 'text-yellow-400' },
                          recommendation: { label: 'Rec', bgColor: 'bg-yellow-500/10', textColor: 'text-yellow-400' },
                          code_explanations: { label: 'Code', bgColor: 'bg-blue-500/10', textColor: 'text-blue-400' },
                          code_example: { label: 'Code', bgColor: 'bg-blue-500/10', textColor: 'text-blue-400' },
                          architecture_insight: { label: 'Arch', bgColor: 'bg-indigo-500/10', textColor: 'text-indigo-400' },
                          documentation: { label: 'Docs', bgColor: 'bg-cyan-500/10', textColor: 'text-cyan-400' },
                          api_design: { label: 'API', bgColor: 'bg-indigo-500/10', textColor: 'text-indigo-400' },
                          performance_insight: { label: 'Perf', bgColor: 'bg-pink-500/10', textColor: 'text-pink-400' },
                          bug_fix: { label: 'Fix', bgColor: 'bg-orange-500/10', textColor: 'text-orange-400' },
                          test_case: { label: 'Test', bgColor: 'bg-green-500/10', textColor: 'text-green-400' },
                        };
                        const config = typeConfig[type] || {
                          label: type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
                          bgColor: 'bg-gray-500/10',
                          textColor: 'text-gray-400'
                        };
                        return (
                          <span key={type} className={`px-2 py-1 text-xs rounded-full ${config.bgColor} ${config.textColor}`}>
                            {config.label}: {formatCurrency(value as number)}
                          </span>
                        );
                      })}
                  </div>

                  <span className="text-emerald-400 font-semibold">
                    {formatCurrency(trace.total_value_usd)}
                  </span>
                </div>
              </button>

              {/* Expanded content */}
              {isExpanded && trace.artifacts.length > 0 && (
                <div className="border-t border-gray-700 p-4 bg-gray-900/30">
                  {/* Full query display */}
                  <div className="mb-4 p-3 bg-gray-800/50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-gray-500 uppercase tracking-wide">Request</span>
                      <button
                        onClick={() => copyToClipboard(trace.query, `query-${trace.trace_id}`)}
                        className="p-1 hover:bg-gray-700 rounded transition-colors"
                        title="Copy query"
                      >
                        {copiedId === `query-${trace.trace_id}` ? (
                          <Check className="h-3 w-3 text-green-400" />
                        ) : (
                          <Copy className="h-3 w-3 text-gray-400" />
                        )}
                      </button>
                    </div>
                    <p className="text-sm text-gray-300 whitespace-pre-wrap">{trace.query}</p>
                  </div>

                  <div className="space-y-3">
                    {trace.artifacts.map((artifact, idx) => {
                      const config = ARTIFACT_CONFIG[artifact.type] || ARTIFACT_CONFIG.code_example;
                      const artifactId = `${trace.trace_id}-${idx}`;

                      return (
                        <div
                          key={artifactId}
                          className={`rounded-lg p-4 ${config.bg}`}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className={config.color}>{config.icon}</span>
                              <span className="text-white font-medium">{artifact.description}</span>
                              <span className="text-xs text-gray-500">({artifact.format})</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`text-sm font-medium ${config.color}`}>
                                {formatCurrency(artifact.value_usd)}
                              </span>
                              <button
                                onClick={() => setSelectedArtifact({
                                  id: artifact.id || artifactId,
                                  traceId: trace.trace_id,
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

                  {/* Trace ID link */}
                  <div className="mt-4 pt-3 border-t border-gray-700 flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      Trace ID: <code className="text-gray-400">{trace.trace_id}</code>
                    </span>
                    <a
                      href={`http://localhost:3001/traces/${trace.trace_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300"
                    >
                      View in Langfuse <ExternalLink className="h-3 w-3" />
                    </a>
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
            value_usd: selectedArtifact.artifact.value_usd,
            description: selectedArtifact.artifact.description,
            format: selectedArtifact.artifact.format,
            trace_id: selectedArtifact.traceId,
          }}
        />
      )}
    </div>
  );
}
