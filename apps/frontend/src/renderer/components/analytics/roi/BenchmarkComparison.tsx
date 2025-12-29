import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../ui/select';
import type { Benchmark } from '../../../../shared/types/analytics-v2';
import { formatCurrency } from '../utils/formatters';

export interface BenchmarkComparisonProps {
  actualCost: number;
  estimatedHours: number;
  linesOfCode?: number;
}

/**
 * Default benchmark data for different regions and seniority levels
 */
const BENCHMARKS: Benchmark[] = [
  // US benchmarks
  { region: 'us', seniority: 'junior', hourlyRate: 50, minutesPerLine: 3.0 },
  { region: 'us', seniority: 'mid', hourlyRate: 85, minutesPerLine: 2.0 },
  { region: 'us', seniority: 'senior', hourlyRate: 150, minutesPerLine: 1.5 },
  // LATAM benchmarks
  { region: 'latam', seniority: 'junior', hourlyRate: 25, minutesPerLine: 3.5 },
  { region: 'latam', seniority: 'mid', hourlyRate: 45, minutesPerLine: 2.5 },
  { region: 'latam', seniority: 'senior', hourlyRate: 80, minutesPerLine: 1.8 },
  // EU benchmarks
  { region: 'eu', seniority: 'junior', hourlyRate: 40, minutesPerLine: 3.2 },
  { region: 'eu', seniority: 'mid', hourlyRate: 70, minutesPerLine: 2.2 },
  { region: 'eu', seniority: 'senior', hourlyRate: 120, minutesPerLine: 1.6 },
];

type RegionType = 'us' | 'latam' | 'eu';
type SeniorityType = 'junior' | 'mid' | 'senior';

/**
 * Compares actual AI cost against market benchmark costs for human developers
 */
export function BenchmarkComparison({
  actualCost,
  estimatedHours,
  linesOfCode,
}: BenchmarkComparisonProps) {
  const { t } = useTranslation(['analytics']);

  const [region, setRegion] = useState<RegionType>('us');
  const [seniority, setSeniority] = useState<SeniorityType>('mid');

  const regionOptions = [
    { value: 'us' as const, label: t('analytics:benchmarks.regions.us') },
    { value: 'latam' as const, label: t('analytics:benchmarks.regions.latam') },
    { value: 'eu' as const, label: t('analytics:benchmarks.regions.eu') },
  ];

  const seniorityOptions = [
    { value: 'junior' as const, label: t('analytics:benchmarks.seniorities.junior') },
    { value: 'mid' as const, label: t('analytics:benchmarks.seniorities.mid') },
    { value: 'senior' as const, label: t('analytics:benchmarks.seniorities.senior') },
  ];

  const selectedBenchmark = useMemo(() => {
    return BENCHMARKS.find((b) => b.region === region && b.seniority === seniority);
  }, [region, seniority]);

  const humanCost = useMemo(() => {
    if (!selectedBenchmark) return 0;

    // Use estimated hours if provided, otherwise calculate from lines of code
    if (estimatedHours > 0) {
      return selectedBenchmark.hourlyRate * estimatedHours;
    }

    if (linesOfCode && linesOfCode > 0) {
      const estimatedMinutes = linesOfCode * selectedBenchmark.minutesPerLine;
      const estimatedHrs = estimatedMinutes / 60;
      return selectedBenchmark.hourlyRate * estimatedHrs;
    }

    return 0;
  }, [selectedBenchmark, estimatedHours, linesOfCode]);

  const savings = humanCost - actualCost;
  const savingsPercentage = humanCost > 0 ? (savings / humanCost) * 100 : 0;
  const isPositiveSavings = savings > 0;

  const benchmarkLabel = selectedBenchmark
    ? `${regionOptions.find((r) => r.value === region)?.label} ${seniorityOptions.find((s) => s.value === seniority)?.label}`
    : '';

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('analytics:benchmarks.title')}</CardTitle>
        <CardDescription>{t('analytics:benchmarks.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Region and Seniority Selectors */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="region-select"
                className="block text-sm font-medium text-muted-foreground mb-1"
              >
                {t('analytics:benchmarks.region')}
              </label>
              <Select value={region} onValueChange={(v) => setRegion(v as RegionType)}>
                <SelectTrigger id="region-select" aria-label={t('analytics:benchmarks.region')}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {regionOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label
                htmlFor="seniority-select"
                className="block text-sm font-medium text-muted-foreground mb-1"
              >
                {t('analytics:benchmarks.seniority')}
              </label>
              <Select value={seniority} onValueChange={(v) => setSeniority(v as SeniorityType)}>
                <SelectTrigger id="seniority-select" aria-label={t('analytics:benchmarks.seniority')}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {seniorityOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Cost Comparison */}
          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
            <div className="space-y-1">
              <span className="text-sm text-muted-foreground">
                {t('analytics:benchmarks.humanCost')}
              </span>
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <span className="text-xl font-semibold">{formatCurrency(humanCost, 2)}</span>
              </div>
              {selectedBenchmark && (
                <span className="text-xs text-muted-foreground">
                  @ {formatCurrency(selectedBenchmark.hourlyRate, 0)}/hr
                </span>
              )}
            </div>

            <div className="space-y-1">
              <span className="text-sm text-muted-foreground">
                {t('analytics:benchmarks.aiCost')}
              </span>
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <span className="text-xl font-semibold">{formatCurrency(actualCost, 2)}</span>
              </div>
            </div>
          </div>

          {/* Savings Display */}
          <div
            className={`p-4 rounded-lg ${
              isPositiveSavings ? 'bg-green-500/10' : 'bg-red-500/10'
            }`}
            role="status"
            aria-live="polite"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isPositiveSavings ? (
                  <TrendingUp className="h-5 w-5 text-green-500" aria-hidden="true" />
                ) : (
                  <TrendingDown className="h-5 w-5 text-red-500" aria-hidden="true" />
                )}
                <span className="text-sm font-medium">
                  {t('analytics:benchmarks.savings')}
                </span>
              </div>
              <span
                className={`text-lg font-bold ${
                  isPositiveSavings ? 'text-green-500' : 'text-red-500'
                }`}
              >
                {isPositiveSavings ? '+' : ''}
                {formatCurrency(savings, 2)}
              </span>
            </div>

            <p className="text-sm text-muted-foreground mt-2">
              {t('analytics:benchmarks.comparison', {
                percent: Math.abs(savingsPercentage).toFixed(0),
                benchmark: benchmarkLabel,
              })}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
