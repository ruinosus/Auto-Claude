import React from 'react';
import { useTranslation } from 'react-i18next';
import { useROIData } from '../../../hooks/useROIData';
import { ROIOverviewCards } from './ROIOverviewCards';
import { ROIChart } from './ROIChart';
import { CostValueChart } from './CostValueChart';
import { ROITable } from './ROITable';

interface ROIDashboardProps {
  projectId?: string;
}

export function ROIDashboard({ projectId }: ROIDashboardProps) {
  const { t } = useTranslation(['analytics']);
  const { settings, specs, aggregate, isLoading, error, refreshAll } = useROIData(projectId);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <p className="text-destructive mb-4">{error}</p>
        <button
          onClick={refreshAll}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          {t('analytics:roi.dashboard.retry')}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <ROIOverviewCards
        aggregate={aggregate}
        settings={settings}
        isLoading={isLoading}
      />

      {/* Charts Row */}
      <div className="grid gap-6 md:grid-cols-2">
        <ROIChart
          specs={specs}
          isLoading={isLoading}
        />
        <CostValueChart
          specs={specs}
          isLoading={isLoading}
        />
      </div>

      {/* Details Table */}
      <ROITable
        specs={specs}
        isLoading={isLoading}
      />
    </div>
  );
}
