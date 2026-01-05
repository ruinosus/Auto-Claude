/**
 * ImpactForecastCard Component
 * =============================
 *
 * Displays ROI prediction before spec execution and comparison with actual results.
 * Uses a RadialBarChart (gauge) to visualize prediction accuracy.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
  PolarAngleAxis,
  Cell,
  Tooltip,
} from 'recharts';
import { TrendingUp, Target, AlertCircle, CheckCircle, XCircle, Activity } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card';
import { useChartColors } from '../utils/useChartColors';
import {
  getForecast,
  getForecastComparison,
  getForecastAccuracy,
  predictROI,
  type ImpactForecastResponse,
  type ForecastComparisonResponse,
  type ModelAccuracyResponse,
  type ForecastPredictRequest,
} from '../../../services/analytics-api';

export type ForecastMode = 'pre-spec' | 'post-spec';

export interface ImpactForecastCardProps {
  specId: string;
  mode: ForecastMode;
  // Pre-spec prediction parameters (only used in 'pre-spec' mode)
  predictionParams?: Omit<ForecastPredictRequest, 'spec_id'>;
  // Callback when prediction is made
  onPredictionMade?: (forecast: ImpactForecastResponse) => void;
  // Loading state override
  isLoading?: boolean;
  className?: string;
}

/**
 * Formats currency values for display
 */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Formats percentage for display
 */
function formatPercent(value: number): string {
  return `${value.toFixed(0)}%`;
}

/**
 * Formats percentage with compact notation for large values
 */
function formatPercentCompact(value: number): string {
  const absValue = Math.abs(value);
  if (absValue >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M%`;
  }
  if (absValue >= 10_000) {
    return `${(value / 1_000).toFixed(0)}K%`;
  }
  if (absValue >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K%`;
  }
  return `${value.toFixed(0)}%`;
}

/**
 * Loading skeleton component
 */
function LoadingSkeleton() {
  return (
    <Card className="animate-pulse">
      <CardHeader>
        <div className="h-5 w-40 bg-muted rounded" />
        <div className="h-4 w-56 bg-muted rounded mt-1" />
      </CardHeader>
      <CardContent>
        <div className="h-[200px] bg-muted rounded" />
      </CardContent>
    </Card>
  );
}

/**
 * Model accuracy badge component
 */
function AccuracyBadge({ accuracy }: { accuracy: ModelAccuracyResponse | null }) {
  const { t } = useTranslation(['analytics']);

  if (!accuracy || accuracy.total_predictions === 0) {
    return null;
  }

  const accuracyValue = accuracy.mean_accuracy;
  const color =
    accuracyValue >= 80
      ? 'text-green-600 bg-green-100 dark:bg-green-900/30'
      : accuracyValue >= 60
        ? 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30'
        : 'text-red-600 bg-red-100 dark:bg-red-900/30';

  return (
    <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${color}`}>
      <Activity className="h-3 w-3" />
      <span>
        {t('analytics:forecast.modelAccuracy', { accuracy: accuracyValue.toFixed(0) })}
      </span>
    </div>
  );
}

/**
 * Pre-spec prediction view
 */
function PreSpecView({
  forecast,
  accuracy,
  colors,
}: {
  forecast: ImpactForecastResponse;
  accuracy: ModelAccuracyResponse | null;
  colors: ReturnType<typeof useChartColors>;
}) {
  const { t } = useTranslation(['analytics']);

  const [ciLow, ciHigh] = forecast.confidence_interval;

  // Data for the gauge chart
  const gaugeData = [
    {
      name: 'ROI',
      value: Math.min(forecast.predicted_roi, 2000), // Cap for display
      fill: colors.chart2,
    },
  ];

  return (
    <div className="space-y-4">
      {/* Header with model accuracy */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="h-5 w-5 text-primary" />
          <span className="font-medium">{t('analytics:forecast.prediction')}</span>
        </div>
        <AccuracyBadge accuracy={accuracy} />
      </div>

      {/* Main prediction display */}
      <div className="grid grid-cols-3 gap-4">
        {/* Predicted Value */}
        <div className="text-center">
          <p className="text-sm text-muted-foreground">{t('analytics:forecast.predictedValue')}</p>
          <p className="text-xl font-bold text-green-600">{formatCurrency(forecast.predicted_value_usd)}</p>
        </div>

        {/* Predicted Cost */}
        <div className="text-center">
          <p className="text-sm text-muted-foreground">{t('analytics:forecast.predictedCost')}</p>
          <p className="text-xl font-bold text-muted-foreground">{formatCurrency(forecast.predicted_cost_usd)}</p>
        </div>

        {/* Predicted ROI */}
        <div className="text-center">
          <p className="text-sm text-muted-foreground">{t('analytics:forecast.predictedROI')}</p>
          <p className="text-xl font-bold text-primary whitespace-nowrap" title={`${forecast.predicted_roi.toFixed(0)}%`}>{formatPercentCompact(forecast.predicted_roi)}</p>
        </div>
      </div>

      {/* Confidence interval */}
      <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
        <span>{t('analytics:forecast.confidenceInterval')}</span>
        <span className="font-medium">
          {formatPercent(ciLow)} - {formatPercent(ciHigh)}
        </span>
      </div>

      {/* Gauge visualization */}
      <div className="h-[150px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="100%"
            innerRadius="60%"
            outerRadius="100%"
            barSize={20}
            data={gaugeData}
            startAngle={180}
            endAngle={0}
          >
            <PolarAngleAxis
              type="number"
              domain={[0, 2000]}
              angleAxisId={0}
              tick={false}
            />
            <RadialBar
              background
              dataKey="value"
              cornerRadius={10}
              animationDuration={1000}
            >
              {gaugeData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </RadialBar>
            <Tooltip
              formatter={(value: number) => [formatPercent(value), 'Predicted ROI']}
              contentStyle={{
                backgroundColor: colors.card,
                borderColor: colors.border,
                borderRadius: '6px',
              }}
            />
          </RadialBarChart>
        </ResponsiveContainer>
      </div>

      {/* Prediction factors */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('analytics:forecast.factors.complexity')}:</span>
          <span className="font-medium capitalize">{forecast.prediction_factors.complexity}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('analytics:forecast.factors.featureType')}:</span>
          <span className="font-medium capitalize">{forecast.prediction_factors.feature_type}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Post-spec comparison view
 */
function PostSpecView({
  comparison,
  colors,
}: {
  comparison: ForecastComparisonResponse;
  colors: ReturnType<typeof useChartColors>;
}) {
  const { t } = useTranslation(['analytics']);

  // Determine if prediction was accurate
  const isAccurate = comparison.accuracy_percentage >= 70;
  const wasWithinCI = comparison.within_confidence;

  // Calculate gauge data - accuracy percentage
  const gaugeData = [
    {
      name: 'Accuracy',
      value: comparison.accuracy_percentage,
      fill: isAccurate ? colors.chart2 : colors.chart5,
    },
  ];

  return (
    <div className="space-y-4">
      {/* Header with accuracy status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isAccurate ? (
            <CheckCircle className="h-5 w-5 text-green-600" />
          ) : (
            <XCircle className="h-5 w-5 text-red-600" />
          )}
          <span className="font-medium">
            {isAccurate
              ? t('analytics:forecast.accuratePrediction')
              : t('analytics:forecast.inaccuratePrediction')}
          </span>
        </div>
        <div
          className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
            wasWithinCI
              ? 'text-green-600 bg-green-100 dark:bg-green-900/30'
              : 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30'
          }`}
        >
          {wasWithinCI
            ? t('analytics:forecast.withinConfidence')
            : t('analytics:forecast.outsideConfidence')}
        </div>
      </div>

      {/* Comparison grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Predicted vs Actual ROI */}
        <div className="space-y-2 p-3 bg-muted/50 rounded-lg">
          <p className="text-sm font-medium">{t('analytics:forecast.predictedROI')}</p>
          <p className="text-2xl font-bold text-muted-foreground truncate" title={`${comparison.predicted_roi.toFixed(0)}%`}>
            {formatPercentCompact(comparison.predicted_roi)}
          </p>
        </div>
        <div className="space-y-2 p-3 bg-muted/50 rounded-lg">
          <p className="text-sm font-medium">{t('analytics:forecast.actualROI')}</p>
          <p className="text-2xl font-bold text-primary truncate" title={`${comparison.actual_roi.toFixed(0)}%`}>{formatPercentCompact(comparison.actual_roi)}</p>
        </div>
      </div>

      {/* Accuracy gauge */}
      <div className="h-[150px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="100%"
            innerRadius="60%"
            outerRadius="100%"
            barSize={20}
            data={gaugeData}
            startAngle={180}
            endAngle={0}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
            <RadialBar background dataKey="value" cornerRadius={10} animationDuration={1000}>
              {gaugeData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </RadialBar>
            <Tooltip
              formatter={(value: number) => [formatPercent(value), 'Prediction Accuracy']}
              contentStyle={{
                backgroundColor: colors.card,
                borderColor: colors.border,
                borderRadius: '6px',
              }}
            />
          </RadialBarChart>
        </ResponsiveContainer>
        <p className="text-center text-2xl font-bold -mt-12">
          {formatPercent(comparison.accuracy_percentage)}
          <span className="text-sm font-normal text-muted-foreground ml-1">
            {t('analytics:forecast.accuracy')}
          </span>
        </p>
      </div>

      {/* Error details */}
      <div className="flex items-center justify-center gap-4 text-sm">
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground">{t('analytics:forecast.predictionError')}:</span>
          <span
            className={`font-medium ${
              comparison.prediction_error > 0 ? 'text-yellow-600' : 'text-blue-600'
            }`}
          >
            {comparison.prediction_error > 0 ? '+' : ''}
            {formatPercent(comparison.prediction_error)}
          </span>
        </div>
      </div>

      {/* Value comparison */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('analytics:forecast.predictedValue')}:</span>
          <span className="font-medium">{formatCurrency(comparison.predicted_value_usd)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('analytics:forecast.actualValue')}:</span>
          <span className="font-medium">{formatCurrency(comparison.actual_value_usd)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('analytics:forecast.predictedCost')}:</span>
          <span className="font-medium">{formatCurrency(comparison.predicted_cost_usd)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">{t('analytics:forecast.actualCost')}:</span>
          <span className="font-medium">{formatCurrency(comparison.actual_cost_usd)}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * No data view
 */
function NoDataView({ mode }: { mode: ForecastMode }) {
  const { t } = useTranslation(['analytics']);

  return (
    <div className="flex flex-col items-center justify-center h-[200px] text-center">
      <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
      <p className="text-muted-foreground">
        {mode === 'pre-spec'
          ? t('analytics:forecast.noForecast')
          : t('analytics:forecast.noComparison')}
      </p>
    </div>
  );
}

/**
 * Main ImpactForecastCard component
 */
export function ImpactForecastCard({
  specId,
  mode,
  predictionParams,
  onPredictionMade,
  isLoading: externalLoading,
  className = '',
}: ImpactForecastCardProps) {
  const { t } = useTranslation(['analytics']);
  const colors = useChartColors();

  const [forecast, setForecast] = useState<ImpactForecastResponse | null>(null);
  const [comparison, setComparison] = useState<ForecastComparisonResponse | null>(null);
  const [accuracy, setAccuracy] = useState<ModelAccuracyResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!specId) return;

    setIsLoading(true);
    setError(null);

    try {
      if (mode === 'pre-spec') {
        // Try to get existing forecast first
        try {
          const existingForecast = await getForecast(specId);
          setForecast(existingForecast);
        } catch {
          // No existing forecast, create one if we have prediction params
          if (predictionParams) {
            const newForecast = await predictROI({
              spec_id: specId,
              ...predictionParams,
            });
            setForecast(newForecast);
            onPredictionMade?.(newForecast);
          }
        }

        // Also load model accuracy
        try {
          const accuracyData = await getForecastAccuracy();
          setAccuracy(accuracyData);
        } catch {
          // Accuracy data is optional
        }
      } else {
        // Post-spec mode: load comparison
        try {
          const comparisonData = await getForecastComparison(specId);
          setComparison(comparisonData);
        } catch {
          // Try to load just the forecast
          try {
            const forecastData = await getForecast(specId);
            setForecast(forecastData);
          } catch {
            // No data available
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load forecast data');
    } finally {
      setIsLoading(false);
    }
  }, [specId, mode, predictionParams, onPredictionMade]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (externalLoading || isLoading) {
    return <LoadingSkeleton />;
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          {t('analytics:forecast.title')}
        </CardTitle>
        <CardDescription>
          {mode === 'pre-spec'
            ? t('analytics:forecast.preSpecDescription')
            : t('analytics:forecast.postSpecDescription')}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="flex items-center justify-center h-[200px] text-center">
            <div className="text-red-600">
              <AlertCircle className="h-8 w-8 mx-auto mb-2" />
              <p>{error}</p>
            </div>
          </div>
        ) : mode === 'pre-spec' && forecast ? (
          <PreSpecView forecast={forecast} accuracy={accuracy} colors={colors} />
        ) : mode === 'post-spec' && comparison ? (
          <PostSpecView comparison={comparison} colors={colors} />
        ) : (
          <NoDataView mode={mode} />
        )}
      </CardContent>
    </Card>
  );
}

export default ImpactForecastCard;
