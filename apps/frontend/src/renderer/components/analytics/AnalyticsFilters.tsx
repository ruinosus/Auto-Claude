// apps/frontend/src/renderer/components/analytics/AnalyticsFilters.tsx
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Filter, X } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { useAnalyticsStore } from '../../stores/analytics-store';
import type { DateRange, AnalyticsFilters as FiltersType } from '../../../shared/types/analytics-v2';

const DATE_RANGES: { value: DateRange; labelKey: string }[] = [
  { value: '7d', labelKey: 'analytics:dateRanges.7d' },
  { value: '30d', labelKey: 'analytics:dateRanges.30d' },
  { value: '90d', labelKey: 'analytics:dateRanges.90d' },
  { value: 'all', labelKey: 'analytics:dateRanges.all' },
];

const PHASES = ['planning', 'coding', 'validation'] as const;

export function AnalyticsFilters() {
  const { t } = useTranslation(['analytics']);
  const [isExpanded, setIsExpanded] = useState(false);
  const { filters, setFilters, clearFilters, setDateRange } = useAnalyticsStore();

  const activeFilterCount = [
    filters.specIds.length > 0,
    filters.phases.length > 0,
    filters.models.length > 0,
    filters.costRange.max !== Infinity,
  ].filter(Boolean).length;

  const handlePhaseToggle = (phase: typeof PHASES[number]) => {
    const newPhases = filters.phases.includes(phase)
      ? filters.phases.filter(p => p !== phase)
      : [...filters.phases, phase];
    setFilters({ phases: newPhases });
  };

  return (
    <div className="space-y-4">
      {/* Date Range Selector - Always visible */}
      <div className="flex items-center gap-4">
        <Select
          value={filters.dateRange}
          onValueChange={(value: DateRange) => setDateRange(value)}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {DATE_RANGES.map(({ value, labelKey }) => (
              <SelectItem key={value} value={value}>
                {t(labelKey)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <Filter className="h-4 w-4 mr-2" />
          {t('analytics:filters.title')}
          {activeFilterCount > 0 && (
            <Badge variant="secondary" className="ml-2">
              {activeFilterCount}
            </Badge>
          )}
        </Button>

        {activeFilterCount > 0 && (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            <X className="h-4 w-4 mr-2" />
            {t('analytics:filters.clear')}
          </Button>
        )}
      </div>

      {/* Expanded Filters */}
      {isExpanded && (
        <div className="p-4 border rounded-lg bg-muted/50 space-y-4">
          {/* Phase Filter */}
          <div>
            <label className="text-sm font-medium mb-2 block">
              {t('analytics:filters.phases')}
            </label>
            <div className="flex gap-2">
              {PHASES.map(phase => (
                <Badge
                  key={phase}
                  variant={filters.phases.includes(phase) ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => handlePhaseToggle(phase)}
                >
                  {phase}
                </Badge>
              ))}
            </div>
          </div>

          {/* Active Filter Badges */}
          {activeFilterCount > 0 && (
            <div className="flex flex-wrap gap-2 pt-2 border-t">
              {filters.phases.map(phase => (
                <Badge key={phase} variant="secondary">
                  Phase: {phase}
                  <X
                    className="h-3 w-3 ml-1 cursor-pointer"
                    onClick={() => handlePhaseToggle(phase)}
                  />
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
