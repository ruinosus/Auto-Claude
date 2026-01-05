/**
 * Cost Avoidance Panel
 * ====================
 *
 * Displays costs avoided through bug prevention, security fixes, and rework avoidance.
 * Shows total cost avoided, events list with severity badges, and trend chart.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Shield, Bug, RefreshCw, AlertTriangle, CheckCircle2, TrendingDown } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { Badge } from '../../ui/badge';
import { Button } from '../../ui/button';
import { formatCurrency, formatRelativeTime } from '../utils/formatters';
import type {
  CostAvoidanceSummary,
  CostAvoidanceEvent,
  CostAvoidanceTrendResponse,
} from '../../../services/analytics-api';

// =============================================================================
// Types
// =============================================================================

interface CostAvoidancePanelProps {
  summary: CostAvoidanceSummary | null;
  trend: CostAvoidanceTrendResponse | null;
  isLoading?: boolean;
  onRefresh?: () => void;
}

// =============================================================================
// Helper Functions
// =============================================================================

function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'bg-red-500 hover:bg-red-600 text-white';
    case 'high':
      return 'bg-orange-500 hover:bg-orange-600 text-white';
    case 'medium':
      return 'bg-yellow-500 hover:bg-yellow-600 text-black';
    case 'low':
      return 'bg-blue-500 hover:bg-blue-600 text-white';
    default:
      return 'bg-gray-500 hover:bg-gray-600 text-white';
  }
}

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    bug_production: 'Bug Prevention',
    security_breach: 'Security Fix',
    rework_avoided: 'Rework Avoided',
    duplicate_feature: 'Duplicate Prevented',
    wrong_architecture: 'Architecture Fix',
  };
  return labels[type] || type;
}

function getTypeIcon(type: string) {
  switch (type) {
    case 'security_breach':
      return <Shield className="h-4 w-4" />;
    case 'bug_production':
      return <Bug className="h-4 w-4" />;
    case 'rework_avoided':
      return <RefreshCw className="h-4 w-4" />;
    case 'wrong_architecture':
      return <AlertTriangle className="h-4 w-4" />;
    default:
      return <CheckCircle2 className="h-4 w-4" />;
  }
}

// =============================================================================
// Summary Card Component
// =============================================================================

interface SummaryCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  iconColor?: string;
  valueColor?: string;
  highlight?: boolean;
}

function SummaryCard({
  title,
  value,
  subtitle,
  icon,
  iconColor = 'text-muted-foreground',
  valueColor = '',
  highlight = false,
}: SummaryCardProps) {
  return (
    <Card className={highlight ? 'bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20 border-green-200 dark:border-green-800' : ''}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          <div className={iconColor}>{icon}</div>
        </div>
        <div className={`text-2xl font-bold ${valueColor}`}>{value}</div>
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Event List Component
// =============================================================================

interface EventListProps {
  events: CostAvoidanceEvent[];
}

function EventList({ events }: EventListProps) {
  const { t } = useTranslation(['analytics']);

  if (events.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <CheckCircle2 className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p>{t('analytics:costAvoidance.noEvents', 'No cost avoidance events recorded yet')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto">
      {events.slice(0, 10).map((event) => (
        <div
          key={event.id}
          className="flex items-start gap-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
        >
          <div className="mt-0.5 text-muted-foreground">
            {getTypeIcon(event.type)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium truncate">{getTypeLabel(event.type)}</span>
              <Badge className={`text-xs ${getSeverityColor(event.severity)}`}>
                {event.severity}
              </Badge>
            </div>
            {event.description && (
              <p className="text-sm text-muted-foreground truncate">{event.description}</p>
            )}
            <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
              <span>Detected by: {event.detected_by}</span>
              <span>{formatRelativeTime(event.created_at)}</span>
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className="text-lg font-semibold text-green-600 dark:text-green-400">
              {formatCurrency(event.estimated_cost_avoided)}
            </div>
            <div className="text-xs text-muted-foreground">
              {Math.round(event.confidence * 100)}% confidence
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// Trend Chart Component
// =============================================================================

interface TrendChartProps {
  data: CostAvoidanceTrendResponse | null;
}

function TrendChart({ data }: TrendChartProps) {
  const { t } = useTranslation(['analytics']);

  if (!data || data.trend.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <TrendingDown className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>{t('analytics:costAvoidance.noTrend', 'Not enough data for trend chart')}</p>
        </div>
      </div>
    );
  }

  // Transform data for Recharts
  const chartData = data.trend.map((point) => ({
    date: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    costAvoided: point.cost_avoided,
    events: point.event_count,
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="costAvoidedGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            className="text-muted-foreground"
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `$${value >= 1000 ? `${(value / 1000).toFixed(0)}k` : value}`}
            className="text-muted-foreground"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
            }}
            formatter={(value: number, name: string) => [
              name === 'costAvoided' ? formatCurrency(value) : value,
              name === 'costAvoided' ? 'Cost Avoided' : 'Events',
            ]}
          />
          <Area
            type="monotone"
            dataKey="costAvoided"
            stroke="#22c55e"
            strokeWidth={2}
            fill="url(#costAvoidedGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// =============================================================================
// Breakdown by Type Component
// =============================================================================

interface TypeBreakdownProps {
  byType: Record<string, number>;
  total: number;
}

function TypeBreakdown({ byType, total }: TypeBreakdownProps) {
  const sortedTypes = Object.entries(byType).sort(([, a], [, b]) => b - a);

  if (sortedTypes.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {sortedTypes.map(([type, value]) => {
        const percentage = total > 0 ? (value / total) * 100 : 0;
        return (
          <div key={type} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                {getTypeIcon(type)}
                <span>{getTypeLabel(type)}</span>
              </div>
              <span className="font-medium">{formatCurrency(value)}</span>
            </div>
            <div className="h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full transition-all"
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// =============================================================================
// Main Panel Component
// =============================================================================

export function CostAvoidancePanel({
  summary,
  trend,
  isLoading = false,
  onRefresh,
}: CostAvoidancePanelProps) {
  const { t } = useTranslation(['analytics']);
  const [showAllEvents, setShowAllEvents] = useState(false);

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="h-4 w-24 bg-muted rounded mb-2" />
                <div className="h-8 w-32 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card>
          <CardContent className="p-4">
            <div className="h-64 bg-muted rounded" />
          </CardContent>
        </Card>
      </div>
    );
  }

  // No data state
  if (!summary || summary.event_count === 0) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="text-center">
            <Shield className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
            <h3 className="text-lg font-semibold mb-2">
              {t('analytics:costAvoidance.noData.title', 'No Cost Avoidance Data')}
            </h3>
            <p className="text-muted-foreground max-w-md mx-auto">
              {t(
                'analytics:costAvoidance.noData.description',
                'Cost avoidance events will appear here when bugs are prevented, security issues are fixed, or rework is avoided during QA reviews.'
              )}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with refresh button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">
            {t('analytics:costAvoidance.title', 'Cost Avoidance')}
          </h2>
          <p className="text-muted-foreground">
            {t('analytics:costAvoidance.subtitle', 'Costs avoided through prevention and early detection')}
          </p>
        </div>
        {onRefresh && (
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            {t('common:refresh', 'Refresh')}
          </Button>
        )}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryCard
          title={t('analytics:costAvoidance.totalAvoided', 'Total Cost Avoided')}
          value={formatCurrency(summary.total_cost_avoided)}
          subtitle={`${summary.event_count} event${summary.event_count !== 1 ? 's' : ''}`}
          icon={<Shield className="h-5 w-5" />}
          iconColor="text-green-600"
          valueColor="text-green-600 dark:text-green-400"
          highlight
        />
        <SummaryCard
          title={t('analytics:costAvoidance.bugsPrevented', 'Bugs Prevented')}
          value={formatCurrency(summary.by_type?.bug_production || 0)}
          subtitle={t('analytics:costAvoidance.productionBugs', 'Production bugs')}
          icon={<Bug className="h-5 w-5" />}
          iconColor="text-orange-500"
        />
        <SummaryCard
          title={t('analytics:costAvoidance.securityFixed', 'Security Issues')}
          value={formatCurrency(summary.by_type?.security_breach || 0)}
          subtitle={t('analytics:costAvoidance.vulnerabilities', 'Vulnerabilities fixed')}
          icon={<Shield className="h-5 w-5" />}
          iconColor="text-red-500"
        />
      </div>

      {/* Trend Chart and Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>
              {t('analytics:costAvoidance.trendTitle', 'Cost Avoidance Trend')}
            </CardTitle>
            <CardDescription>
              {t('analytics:costAvoidance.trendDescription', 'Weekly breakdown of avoided costs')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <TrendChart data={trend} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              {t('analytics:costAvoidance.breakdownTitle', 'Breakdown by Type')}
            </CardTitle>
            <CardDescription>
              {t('analytics:costAvoidance.breakdownDescription', 'Distribution of avoided costs')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <TypeBreakdown byType={summary.by_type} total={summary.total_cost_avoided} />
          </CardContent>
        </Card>
      </div>

      {/* Recent Events */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>
                {t('analytics:costAvoidance.recentEvents', 'Recent Events')}
              </CardTitle>
              <CardDescription>
                {t('analytics:costAvoidance.recentEventsDescription', 'Latest cost avoidance events')}
              </CardDescription>
            </div>
            {summary.events.length > 10 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAllEvents(!showAllEvents)}
              >
                {showAllEvents
                  ? t('common:showLess', 'Show Less')
                  : t('common:showAll', `Show All (${summary.events.length})`)}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <EventList events={showAllEvents ? summary.events : summary.events.slice(0, 10)} />
        </CardContent>
      </Card>

      {/* Confidence & Detection Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {t('analytics:costAvoidance.byDetector', 'By Detection Source')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(summary.by_detector).map(([detector, value]) => (
                <div key={detector} className="flex items-center justify-between text-sm">
                  <span className="capitalize">{detector.replace(/_/g, ' ')}</span>
                  <span className="font-medium">{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {t('analytics:costAvoidance.bySeverity', 'By Severity')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {['critical', 'high', 'medium', 'low'].map((severity) => {
                const value = summary.by_severity[severity] || 0;
                if (value === 0) return null;
                return (
                  <div key={severity} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <Badge className={`text-xs ${getSeverityColor(severity)}`}>{severity}</Badge>
                    </div>
                    <span className="font-medium">{formatCurrency(value)}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default CostAvoidancePanel;
