import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card';
import {
  TrendingUp,
  TrendingDown,
  Users,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Minus,
  RefreshCcw,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { analyticsApi, type SatisfactionMetrics } from '../../../services/analytics-api';
import { useProjectPath } from '../../../hooks/useProjectPath';

interface NPSGaugeProps {
  score: number;
  isLoading?: boolean;
}

/**
 * NPS Gauge Component
 * Displays a semi-circular gauge showing NPS from -100 to +100
 */
function NPSGauge({ score, isLoading }: NPSGaugeProps) {
  const { t } = useTranslation(['analytics']);

  // Calculate rotation angle for the needle (180 degrees total range)
  // -100 = 0deg, 0 = 90deg, +100 = 180deg
  const normalizedScore = Math.max(-100, Math.min(100, score));
  const rotation = ((normalizedScore + 100) / 200) * 180;

  // Determine color based on score
  const getScoreColor = (s: number): string => {
    if (s >= 50) return 'text-green-500';
    if (s >= 0) return 'text-amber-500';
    return 'text-red-500';
  };

  const getScoreLabel = (s: number): string => {
    if (s >= 70) return t('analytics:satisfaction.nps.excellent');
    if (s >= 50) return t('analytics:satisfaction.nps.great');
    if (s >= 30) return t('analytics:satisfaction.nps.good');
    if (s >= 0) return t('analytics:satisfaction.nps.okay');
    if (s >= -30) return t('analytics:satisfaction.nps.needsWork');
    return t('analytics:satisfaction.nps.critical');
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center p-6 animate-pulse">
        <div className="w-48 h-24 bg-muted rounded-t-full" />
        <div className="h-8 w-16 bg-muted rounded mt-2" />
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center p-4">
      {/* Gauge SVG */}
      <div className="relative w-48 h-24">
        {/* Background arc */}
        <svg viewBox="0 0 200 100" className="w-full h-full">
          {/* Gradient definition */}
          <defs>
            <linearGradient id="npsGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#ef4444" />
              <stop offset="50%" stopColor="#f59e0b" />
              <stop offset="100%" stopColor="#22c55e" />
            </linearGradient>
          </defs>

          {/* Background arc */}
          <path
            d="M 10 100 A 90 90 0 0 1 190 100"
            fill="none"
            stroke="url(#npsGradient)"
            strokeWidth="12"
            strokeLinecap="round"
            className="opacity-30"
          />

          {/* Foreground arc (progress) */}
          <path
            d="M 10 100 A 90 90 0 0 1 190 100"
            fill="none"
            stroke="url(#npsGradient)"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${((normalizedScore + 100) / 200) * 283} 283`}
          />

          {/* Needle */}
          <g transform={`rotate(${rotation - 90}, 100, 100)`}>
            <line
              x1="100"
              y1="100"
              x2="100"
              y2="25"
              stroke="currentColor"
              strokeWidth="2"
              className="text-foreground"
            />
            <circle cx="100" cy="100" r="6" fill="currentColor" className="text-foreground" />
          </g>

          {/* Scale labels */}
          <text x="10" y="95" className="text-xs fill-muted-foreground" textAnchor="start">
            -100
          </text>
          <text x="100" y="20" className="text-xs fill-muted-foreground" textAnchor="middle">
            0
          </text>
          <text x="190" y="95" className="text-xs fill-muted-foreground" textAnchor="end">
            +100
          </text>
        </svg>
      </div>

      {/* Score display */}
      <div className="text-center mt-2">
        <div className={`text-4xl font-bold ${getScoreColor(score)}`}>
          {score > 0 ? '+' : ''}
          {score.toFixed(0)}
        </div>
        <div className="text-sm text-muted-foreground mt-1">{getScoreLabel(score)}</div>
      </div>
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  iconColor?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
}

function MetricCard({ title, value, subtitle, icon: Icon, iconColor = 'text-muted-foreground', trend }: MetricCardProps) {
  return (
    <Card className="shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          <Icon className={`h-5 w-5 ${iconColor}`} aria-hidden="true" />
        </div>
        <div className="text-2xl font-bold">{value}</div>
        {trend && (
          <div className={`flex items-center gap-1 text-sm mt-1 ${trend.isPositive ? 'text-green-500' : 'text-red-500'}`}>
            {trend.isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
            <span>{Math.abs(trend.value).toFixed(1)}%</span>
          </div>
        )}
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}

interface ResponseBreakdownProps {
  promoters: number;
  passives: number;
  detractors: number;
  total: number;
}

function ResponseBreakdown({ promoters, passives, detractors, total }: ResponseBreakdownProps) {
  const { t } = useTranslation(['analytics']);

  const promoterPct = total > 0 ? (promoters / total) * 100 : 0;
  const passivePct = total > 0 ? (passives / total) * 100 : 0;
  const detractorPct = total > 0 ? (detractors / total) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <ThumbsUp className="h-4 w-4 text-green-500" />
          <span className="text-sm">{t('analytics:satisfaction.breakdown.promoters')}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{promoters}</span>
          <span className="text-xs text-muted-foreground">({promoterPct.toFixed(0)}%)</span>
        </div>
      </div>

      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Minus className="h-4 w-4 text-amber-500" />
          <span className="text-sm">{t('analytics:satisfaction.breakdown.passives')}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{passives}</span>
          <span className="text-xs text-muted-foreground">({passivePct.toFixed(0)}%)</span>
        </div>
      </div>

      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <ThumbsDown className="h-4 w-4 text-red-500" />
          <span className="text-sm">{t('analytics:satisfaction.breakdown.detractors')}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{detractors}</span>
          <span className="text-xs text-muted-foreground">({detractorPct.toFixed(0)}%)</span>
        </div>
      </div>

      {/* Stacked bar */}
      <div className="h-3 rounded-full overflow-hidden flex bg-muted">
        {promoterPct > 0 && (
          <div
            className="bg-green-500 transition-all"
            style={{ width: `${promoterPct}%` }}
          />
        )}
        {passivePct > 0 && (
          <div
            className="bg-amber-500 transition-all"
            style={{ width: `${passivePct}%` }}
          />
        )}
        {detractorPct > 0 && (
          <div
            className="bg-red-500 transition-all"
            style={{ width: `${detractorPct}%` }}
          />
        )}
      </div>
    </div>
  );
}

interface FeedbackThemesProps {
  themes: string[];
}

function FeedbackThemes({ themes }: FeedbackThemesProps) {
  const { t } = useTranslation(['analytics']);

  if (themes.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">{t('analytics:satisfaction.themes.noThemes')}</p>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {themes.map((theme) => (
        <span
          key={theme}
          className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm"
        >
          {t(`analytics:satisfaction.themes.${theme}`, { defaultValue: theme })}
        </span>
      ))}
    </div>
  );
}

interface SatisfactionDashboardProps {
  days?: number;
}

export function SatisfactionDashboard({ days = 30 }: SatisfactionDashboardProps) {
  const { t } = useTranslation(['analytics']);
  const { projectPath } = useProjectPath();
  const [metrics, setMetrics] = useState<SatisfactionMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    if (!projectPath) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await analyticsApi.getSatisfactionMetrics(projectPath, { days });
      setMetrics(data);
    } catch (err) {
      console.error('Failed to fetch satisfaction metrics:', err);
      setError(t('analytics:satisfaction.error.fetchFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, [projectPath, days]);

  if (error) {
    return (
      <Card>
        <CardContent className="p-6 text-center">
          <p className="text-destructive mb-4">{error}</p>
          <Button onClick={fetchMetrics} variant="outline" size="sm">
            <RefreshCcw className="h-4 w-4 mr-2" />
            {t('analytics:common.refresh')}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{t('analytics:satisfaction.title')}</h2>
          <p className="text-muted-foreground">{t('analytics:satisfaction.subtitle')}</p>
        </div>
        <Button onClick={fetchMetrics} variant="outline" size="sm" disabled={isLoading}>
          <RefreshCcw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          {t('analytics:common.refresh')}
        </Button>
      </div>

      {/* NPS Gauge and Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>{t('analytics:satisfaction.nps.title')}</CardTitle>
            <CardDescription>{t('analytics:satisfaction.nps.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <NPSGauge score={metrics?.nps_score ?? 0} isLoading={isLoading} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('analytics:satisfaction.breakdown.title')}</CardTitle>
            <CardDescription>{t('analytics:satisfaction.breakdown.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4 animate-pulse">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-6 bg-muted rounded" />
                ))}
              </div>
            ) : (
              <ResponseBreakdown
                promoters={metrics?.promoters_count ?? 0}
                passives={metrics?.passives_count ?? 0}
                detractors={metrics?.detractors_count ?? 0}
                total={metrics?.response_count ?? 0}
              />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Satisfaction Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title={t('analytics:satisfaction.metrics.overallSatisfaction')}
          value={metrics ? `${metrics.avg_satisfaction.toFixed(1)}/5` : '-'}
          icon={ThumbsUp}
          iconColor={
            (metrics?.avg_satisfaction ?? 0) >= 4
              ? 'text-green-500'
              : (metrics?.avg_satisfaction ?? 0) >= 3
                ? 'text-amber-500'
                : 'text-red-500'
          }
          trend={
            metrics?.satisfaction_trend
              ? { value: metrics.satisfaction_trend, isPositive: metrics.satisfaction_trend > 0 }
              : undefined
          }
        />

        <MetricCard
          title={t('analytics:satisfaction.metrics.outputQuality')}
          value={metrics ? `${metrics.avg_output_quality.toFixed(1)}/5` : '-'}
          icon={ThumbsUp}
          iconColor={
            (metrics?.avg_output_quality ?? 0) >= 4
              ? 'text-green-500'
              : (metrics?.avg_output_quality ?? 0) >= 3
                ? 'text-amber-500'
                : 'text-red-500'
          }
        />

        <MetricCard
          title={t('analytics:satisfaction.metrics.timeSaved')}
          value={metrics ? `${metrics.avg_time_saved.toFixed(1)}/5` : '-'}
          icon={ThumbsUp}
          iconColor={
            (metrics?.avg_time_saved ?? 0) >= 4
              ? 'text-green-500'
              : (metrics?.avg_time_saved ?? 0) >= 3
                ? 'text-amber-500'
                : 'text-red-500'
          }
        />

        <MetricCard
          title={t('analytics:satisfaction.metrics.responseRate')}
          value={metrics?.response_count ?? 0}
          subtitle={t('analytics:satisfaction.metrics.totalResponses')}
          icon={Users}
          iconColor="text-blue-500"
        />
      </div>

      {/* Feedback Themes */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            {t('analytics:satisfaction.themes.title')}
          </CardTitle>
          <CardDescription>{t('analytics:satisfaction.themes.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex gap-2 animate-pulse">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-8 w-24 bg-muted rounded-full" />
              ))}
            </div>
          ) : (
            <FeedbackThemes themes={metrics?.top_feedback_themes ?? []} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default SatisfactionDashboard;
