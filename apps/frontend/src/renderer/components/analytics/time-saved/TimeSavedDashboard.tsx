/**
 * Time Saved Dashboard
 * ====================
 *
 * Visualizes developer time saved through AI assistance.
 * Features animated clock, side-by-side comparison, and task breakdown.
 *
 * Now uses ROI Engine API via the API Bridge for artifact-based time savings.
 */

import { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Clock, Timer, TrendingUp, Users, Calendar, BarChart2 } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
  LineChart,
  Line,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { useChartColors, useChartColorArray } from '../utils/useChartColors';
import { formatHours } from '../utils/formatters';
import { apiBridge } from '../../../services/api-bridge';
import type { TimeSavedDashboardResponse } from '../../../services/analytics-api';

interface TimeSavedDashboardProps {
  /** Path to the project directory (required for ROI Engine) */
  projectPath: string;
  /** Optional date range filter */
  fromDate?: string;
  toDate?: string;
}

/**
 * Animated clock component showing hours saved
 */
function AnimatedClock({ hours }: { hours: number }) {
  const [displayHours, setDisplayHours] = useState(0);

  useEffect(() => {
    // Animate from 0 to hours
    const duration = 2000; // 2 seconds
    const startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Easing function for smooth animation
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayHours(Math.round(hours * eased * 10) / 10);
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    animate();
  }, [hours]);

  return (
    <div className="relative flex items-center justify-center">
      <div className="absolute inset-0 bg-gradient-to-br from-green-100 to-emerald-100 dark:from-green-900/20 dark:to-emerald-900/20 rounded-full opacity-50" />
      <div className="relative flex flex-col items-center justify-center w-48 h-48 rounded-full border-4 border-green-500 dark:border-green-400">
        <Clock className="h-8 w-8 text-green-600 dark:text-green-400 mb-2" />
        <div className="text-4xl font-bold text-green-700 dark:text-green-300">
          {displayHours.toFixed(1)}
        </div>
        <div className="text-sm text-green-600 dark:text-green-400 font-medium">
          hours saved
        </div>
      </div>
    </div>
  );
}

/**
 * Comparison card showing AI vs human time
 */
function ComparisonCard({
  taskType,
  withAI,
  withoutAI,
  percentageSaved,
}: {
  taskType: string;
  withAI: number;
  withoutAI: number;
  percentageSaved: number;
}) {
  const chartColors = useChartColors();

  // Format task type for display
  const formatTaskType = (type: string) => {
    return type
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex justify-between items-start mb-3">
        <span className="text-sm font-medium text-muted-foreground truncate max-w-[180px]">
          {formatTaskType(taskType)}
        </span>
        <span className="text-xs font-semibold text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30 px-2 py-1 rounded">
          -{percentageSaved.toFixed(0)}%
        </span>
      </div>

      {/* Side-by-side bars */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground w-16">With AI</span>
          <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all duration-500"
              style={{ width: `${Math.min((withAI / withoutAI) * 100, 100)}%` }}
            />
          </div>
          <span className="text-xs font-medium w-12 text-right">{formatHours(withAI)}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground w-16">Human</span>
          <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-slate-400 rounded-full"
              style={{ width: '100%' }}
            />
          </div>
          <span className="text-xs font-medium w-12 text-right">{formatHours(withoutAI)}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Main Time Saved Dashboard
 */
export function TimeSavedDashboard({ projectPath, fromDate, toDate }: TimeSavedDashboardProps) {
  const { t } = useTranslation(['analytics']);
  const chartColors = useChartColors();
  const colorArray = useChartColorArray();
  const [data, setData] = useState<TimeSavedDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      if (!projectPath) {
        setError('Project path is required');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        // Use API Bridge - routes to ROI Engine for time saved calculations
        const context = apiBridge.createContext(projectPath);
        const result = await apiBridge.timeSaved.getDashboard(context, {
          from_date: fromDate,
          to_date: toDate,
        });
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [projectPath, fromDate, toDate]);

  // Format chart data
  const barChartData = useMemo(() => {
    if (!data?.by_task_type) return [];
    return data.by_task_type.slice(0, 8).map((task, index) => ({
      name: task.task_type
        .split('_')
        .map(w => w.charAt(0).toUpperCase())
        .join(''),
      fullName: task.task_type
        .split('_')
        .map(w => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' '),
      withAI: task.total_actual_hours,
      benchmark: task.total_benchmark_hours,
      saved: task.total_saved_hours,
      color: colorArray[index % colorArray.length],
    }));
  }, [data, colorArray]);

  const trendChartData = useMemo(() => {
    if (!data?.trend) return [];
    return data.trend.map(point => ({
      date: point.date.split('T')[0],
      hoursSaved: point.time_saved_hours,
      benchmarkHours: point.benchmark_hours,
      actualHours: point.actual_hours,
    }));
  }, [data]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-24 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="text-center text-muted-foreground">
          <p>Failed to load time saved data</p>
          <p className="text-sm">{error}</p>
        </div>
      </Card>
    );
  }

  if (!data || data.summary.task_count === 0) {
    return (
      <Card className="p-6">
        <div className="text-center text-muted-foreground">
          <Clock className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="font-medium">No time saved data available</p>
          <p className="text-sm mt-1">Run some specs to start tracking time savings</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Section: Animated Clock + Key Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Animated Clock */}
        <Card className="lg:col-span-1">
          <CardContent className="p-6 flex items-center justify-center">
            <AnimatedClock hours={data.total_hours_saved} />
          </CardContent>
        </Card>

        {/* Key Metrics */}
        <div className="lg:col-span-2 grid grid-cols-2 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                  <Calendar className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Work Days Saved</p>
                  <p className="text-2xl font-bold">{data.equivalent_work_days}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
                  <Users className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Work Weeks Saved</p>
                  <p className="text-2xl font-bold">{data.equivalent_work_weeks}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
                  <TrendingUp className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Avg. Time Saved</p>
                  <p className="text-2xl font-bold">{data.summary.average_percentage_saved.toFixed(0)}%</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/30">
                  <Timer className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Tasks Completed</p>
                  <p className="text-2xl font-bold">{data.summary.task_count}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Comparison Chart: With AI vs Without AI */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart2 className="h-5 w-5" />
            Time Comparison by Task Type
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barChartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                type="number"
                tick={{ fill: chartColors.muted }}
                tickFormatter={(value) => `${value}h`}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fill: chartColors.muted }}
                width={60}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: chartColors.card,
                  border: `1px solid ${chartColors.border}`,
                  borderRadius: '8px',
                }}
                formatter={(value: number, name: string) => [
                  `${value.toFixed(1)}h`,
                  name === 'withAI' ? 'With AI' : 'Human Benchmark',
                ]}
                labelFormatter={(label) => {
                  const item = barChartData.find(d => d.name === label);
                  return item?.fullName || label;
                }}
              />
              <Legend />
              <Bar
                dataKey="benchmark"
                name="Human Benchmark"
                fill={chartColors.muted}
                radius={[0, 4, 4, 0]}
              />
              <Bar
                dataKey="withAI"
                name="With AI"
                fill={chartColors.chart2}
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Trend Chart */}
      {trendChartData.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Time Saved Over Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={trendChartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: chartColors.muted }}
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return `${date.getMonth() + 1}/${date.getDate()}`;
                  }}
                />
                <YAxis
                  tick={{ fill: chartColors.muted }}
                  tickFormatter={(value) => `${value}h`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: chartColors.card,
                    border: `1px solid ${chartColors.border}`,
                    borderRadius: '8px',
                  }}
                  formatter={(value: number) => [`${value.toFixed(1)}h`]}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="hoursSaved"
                  name="Hours Saved"
                  stroke={chartColors.chart2}
                  strokeWidth={2}
                  dot={{ fill: chartColors.chart2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Side-by-Side Comparison Cards */}
      {data.comparisons.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Task-by-Task Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.comparisons.slice(0, 6).map((comparison) => (
                <ComparisonCard
                  key={comparison.task_type}
                  taskType={comparison.task_type}
                  withAI={comparison.with_ai_hours}
                  withoutAI={comparison.without_ai_hours}
                  percentageSaved={comparison.percentage_saved}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default TimeSavedDashboard;
