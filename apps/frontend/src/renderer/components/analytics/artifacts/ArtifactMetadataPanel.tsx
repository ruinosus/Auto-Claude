import { useTranslation } from 'react-i18next';
import {
  CheckCircle,
  XCircle,
  BookOpen,
  ListChecks,
  Users,
  GitBranch,
  Tag,
  Gauge,
  Zap,
  Clock,
  Hash,
  Bot
} from 'lucide-react';
import type { RichLocalArtifact, ArtifactMetadata } from '../../../../shared/types/analytics-v2';

interface ArtifactMetadataPanelProps {
  artifact: RichLocalArtifact;
  className?: string;
}

/**
 * Quality badge component for displaying has_* flags
 */
function QualityBadge({
  hasValue,
  label,
  icon: Icon
}: {
  hasValue: boolean;
  label: string;
  icon: React.ElementType;
}) {
  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${
        hasValue
          ? 'bg-green-500/10 text-green-400 border border-green-500/20'
          : 'bg-gray-500/10 text-gray-500 border border-gray-500/20'
      }`}
    >
      {hasValue ? (
        <CheckCircle className="h-3 w-3" />
      ) : (
        <XCircle className="h-3 w-3" />
      )}
      <span>{label}</span>
    </div>
  );
}

/**
 * Priority badge with MoSCoW colors
 */
function PriorityBadge({ priority }: { priority: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    must: { bg: 'bg-red-500/10', text: 'text-red-400', label: 'Must Have' },
    should: { bg: 'bg-orange-500/10', text: 'text-orange-400', label: 'Should Have' },
    could: { bg: 'bg-blue-500/10', text: 'text-blue-400', label: 'Could Have' },
    wont: { bg: 'bg-gray-500/10', text: 'text-gray-400', label: "Won't Have" },
  };

  const c = config[priority.toLowerCase()] || { bg: 'bg-purple-500/10', text: 'text-purple-400', label: priority };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
}

/**
 * Complexity badge
 */
function ComplexityBadge({ complexity }: { complexity: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    low: { bg: 'bg-green-500/10', text: 'text-green-400' },
    medium: { bg: 'bg-yellow-500/10', text: 'text-yellow-400' },
    high: { bg: 'bg-orange-500/10', text: 'text-orange-400' },
    very_high: { bg: 'bg-red-500/10', text: 'text-red-400' },
  };

  const c = config[complexity.toLowerCase()] || { bg: 'bg-gray-500/10', text: 'text-gray-400' };
  const label = complexity.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      <Gauge className="h-3 w-3" />
      {label}
    </span>
  );
}

/**
 * Impact badge
 */
function ImpactBadge({ impact }: { impact: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    low: { bg: 'bg-blue-500/10', text: 'text-blue-400' },
    medium: { bg: 'bg-purple-500/10', text: 'text-purple-400' },
    high: { bg: 'bg-pink-500/10', text: 'text-pink-400' },
  };

  const c = config[impact.toLowerCase()] || { bg: 'bg-gray-500/10', text: 'text-gray-400' };
  const label = impact.charAt(0).toUpperCase() + impact.slice(1) + ' Impact';

  return (
    <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      <Zap className="h-3 w-3" />
      {label}
    </span>
  );
}

export function ArtifactMetadataPanel({ artifact, className = '' }: ArtifactMetadataPanelProps) {
  const { t } = useTranslation(['analytics']);
  const metadata = artifact.metadata || {};

  const hasQualityFields =
    metadata.has_rationale ||
    metadata.has_acceptance_criteria ||
    metadata.has_user_stories ||
    (metadata.dependency_count && metadata.dependency_count > 0);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Quality Indicators */}
      <div>
        <h4 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
          <CheckCircle className="h-4 w-4" />
          {t('analytics:artifacts.quality.title')}
        </h4>
        <div className="flex flex-wrap gap-2">
          <QualityBadge
            hasValue={!!metadata.has_rationale}
            label={t('analytics:artifacts.quality.hasRationale')}
            icon={BookOpen}
          />
          <QualityBadge
            hasValue={!!metadata.has_acceptance_criteria}
            label={t('analytics:artifacts.quality.hasAcceptanceCriteria')}
            icon={ListChecks}
          />
          <QualityBadge
            hasValue={!!metadata.has_user_stories}
            label={t('analytics:artifacts.quality.hasUserStories')}
            icon={Users}
          />
          <QualityBadge
            hasValue={(metadata.dependency_count || 0) > 0}
            label={`${t('analytics:artifacts.quality.hasDependencies')} (${metadata.dependency_count || 0})`}
            icon={GitBranch}
          />
        </div>
      </div>

      {/* Priority, Complexity, Impact */}
      {(metadata.priority || metadata.complexity || metadata.impact) && (
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
            <Tag className="h-4 w-4" />
            {t('analytics:artifacts.metadata.title')}
          </h4>
          <div className="flex flex-wrap gap-2">
            {metadata.priority && <PriorityBadge priority={metadata.priority} />}
            {metadata.complexity && <ComplexityBadge complexity={metadata.complexity} />}
            {metadata.impact && <ImpactBadge impact={metadata.impact} />}
          </div>
        </div>
      )}

      {/* Strategic Rationale */}
      {artifact.rationale && (
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
            <BookOpen className="h-4 w-4" />
            {t('analytics:artifacts.metadata.strategicRationale')}
          </h4>
          <div className="bg-gray-800/50 rounded-lg p-3 text-sm text-gray-200 leading-relaxed">
            {artifact.rationale}
          </div>
        </div>
      )}

      {/* Acceptance Criteria */}
      {artifact.acceptance_criteria && artifact.acceptance_criteria.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
            <ListChecks className="h-4 w-4" />
            {t('analytics:artifacts.metadata.acceptanceCriteria')}
          </h4>
          <ul className="space-y-1">
            {artifact.acceptance_criteria.map((criterion, idx) => (
              <li
                key={idx}
                className="flex items-start gap-2 text-sm text-gray-300 bg-gray-800/30 rounded px-3 py-2"
              >
                <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0 mt-0.5" />
                <span>{criterion}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* User Stories */}
      {artifact.user_stories && artifact.user_stories.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
            <Users className="h-4 w-4" />
            {t('analytics:artifacts.metadata.userStories')}
          </h4>
          <ul className="space-y-1">
            {artifact.user_stories.map((story, idx) => (
              <li
                key={idx}
                className="text-sm text-gray-300 bg-blue-500/10 rounded px-3 py-2 italic"
              >
                "{story}"
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Dependencies */}
      {artifact.dependencies && artifact.dependencies.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
            <GitBranch className="h-4 w-4" />
            {t('analytics:artifacts.metadata.dependencies')}
          </h4>
          <div className="flex flex-wrap gap-2">
            {artifact.dependencies.map((dep, idx) => (
              <span
                key={idx}
                className="px-2 py-1 text-xs bg-purple-500/10 text-purple-400 rounded-full"
              >
                {dep}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Additional Info */}
      <div className="border-t border-gray-700 pt-4">
        <div className="grid grid-cols-2 gap-3 text-xs">
          {artifact.agent_type && (
            <div className="flex items-center gap-2 text-gray-400">
              <Bot className="h-3.5 w-3.5" />
              <span>{t('analytics:artifacts.metadata.agent')}:</span>
              <span className="text-gray-300">{artifact.agent_type}</span>
            </div>
          )}
          {artifact.session_num !== undefined && (
            <div className="flex items-center gap-2 text-gray-400">
              <Hash className="h-3.5 w-3.5" />
              <span>{t('analytics:artifacts.metadata.session')}:</span>
              <span className="text-gray-300">#{artifact.session_num}</span>
            </div>
          )}
          {artifact.created_at && (
            <div className="flex items-center gap-2 text-gray-400">
              <Clock className="h-3.5 w-3.5" />
              <span>{t('analytics:artifacts.metadata.createdAt')}:</span>
              <span className="text-gray-300">
                {new Date(artifact.created_at).toLocaleString()}
              </span>
            </div>
          )}
          {artifact.trace_id && (
            <div className="flex items-center gap-2 text-gray-400">
              <Hash className="h-3.5 w-3.5" />
              <span>{t('analytics:artifacts.metadata.traceId')}:</span>
              <code className="text-gray-300 text-xs">{artifact.trace_id.slice(0, 12)}...</code>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
