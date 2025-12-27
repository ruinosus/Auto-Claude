import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import type { FeatureUsageData } from '../../stores/analytics-store';
import { Sparkles, FileText, MessageCircle, GitPullRequest, Bug, Zap } from 'lucide-react';

interface FeatureUsageSectionProps {
  featureUsage: FeatureUsageData[];
  totalCost: number;
}

// Feature type to icon mapping
const FEATURE_ICONS: Record<string, React.ReactNode> = {
  roadmap: <Sparkles className="h-5 w-5" />,
  ideation: <Zap className="h-5 w-5" />,
  insights: <MessageCircle className="h-5 w-5" />,
  pr_review: <GitPullRequest className="h-5 w-5" />,
  issue_triage: <Bug className="h-5 w-5" />,
  autofix: <Bug className="h-5 w-5" />,
  changelog: <FileText className="h-5 w-5" />,
};

// Feature type to display name mapping
const FEATURE_NAMES: Record<string, string> = {
  roadmap: 'Roadmap',
  ideation: 'Ideation',
  insights: 'Insights',
  pr_review: 'PR Review',
  issue_triage: 'Issue Triage',
  autofix: 'Auto Fix',
  changelog: 'Changelog',
};

// Feature type to color class mapping
const FEATURE_COLORS: Record<string, string> = {
  roadmap: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  ideation: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  insights: 'bg-green-500/10 text-green-500 border-green-500/20',
  pr_review: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
  issue_triage: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  autofix: 'bg-red-500/10 text-red-500 border-red-500/20',
  changelog: 'bg-cyan-500/10 text-cyan-500 border-cyan-500/20',
};

function formatCost(cost: number): string {
  if (cost >= 1) {
    return `$${cost.toFixed(2)}`;
  }
  if (cost >= 0.01) {
    return `$${cost.toFixed(3)}`;
  }
  return `$${cost.toFixed(4)}`;
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) {
    return `${(tokens / 1_000_000).toFixed(1)}M`;
  }
  if (tokens >= 1_000) {
    return `${(tokens / 1_000).toFixed(1)}K`;
  }
  return tokens.toString();
}

function formatDate(date: Date | null): string {
  if (!date) return 'Never';
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);

  if (hours < 1) return 'Just now';
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
}

export function FeatureUsageSection({ featureUsage, totalCost }: FeatureUsageSectionProps) {
  const { t } = useTranslation(['analytics']);

  if (!featureUsage || featureUsage.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          {t('analytics:featureUsage.title', 'Feature Usage')}
        </CardTitle>
        <CardDescription>
          {t('analytics:featureUsage.description', 'Token usage breakdown by AI-powered features')}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {featureUsage.map((feature) => {
            const icon = FEATURE_ICONS[feature.featureType] || <Sparkles className="h-5 w-5" />;
            const name = FEATURE_NAMES[feature.featureType] || feature.featureType;
            const colorClass = FEATURE_COLORS[feature.featureType] || 'bg-gray-500/10 text-gray-500 border-gray-500/20';
            const percentage = totalCost > 0 ? (feature.totalCost / totalCost) * 100 : 0;

            return (
              <div
                key={feature.featureType}
                className={`p-4 rounded-lg border ${colorClass}`}
              >
                <div className="flex items-center gap-2 mb-3">
                  {icon}
                  <span className="font-semibold">{name}</span>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Cost</span>
                    <span className="font-mono font-medium">
                      {formatCost(feature.totalCost)}
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Tokens</span>
                    <span className="font-mono">
                      {formatTokens(feature.totalInputTokens + feature.totalOutputTokens)}
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Sessions</span>
                    <span className="font-mono">{feature.totalSessions}</span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Last Used</span>
                    <span className="text-xs">{formatDate(feature.lastUsed)}</span>
                  </div>

                  {/* Cost percentage bar */}
                  <div className="mt-2">
                    <div className="h-1.5 w-full bg-black/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-current rounded-full transition-all"
                        style={{ width: `${Math.min(percentage, 100)}%` }}
                      />
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 text-right">
                      {percentage.toFixed(1)}% of total
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
