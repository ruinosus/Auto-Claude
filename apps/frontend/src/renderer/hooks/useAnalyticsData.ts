import { useEffect } from 'react';
import { setAnalyticsData } from '../stores/analytics-store';
import type { AnalyticsData } from '../stores/analytics-store';

/**
 * Hook to receive analytics data from main process via IPC
 *
 * The main process polls the SQLite database and sends updates via 'analytics:data-update' events.
 * This hook listens for those updates and stores them in the Zustand store.
 *
 * @param dbPath - Path to analytics.db (triggers start/stop of polling in main process)
 */
export function useAnalyticsData(dbPath: string | null) {
  useEffect(() => {
    if (!dbPath) {
      // No database path - clear data
      setAnalyticsData(null);
      return;
    }

    console.log('[useAnalyticsData] Starting analytics polling via main process:', dbPath);

    // Request main process to start polling
    window.electronAPI.startAnalyticsPolling(dbPath);

    // Listen for data updates from main process
    const handleDataUpdate = (data: AnalyticsData) => {
      // Deserialize Date objects (they come as strings over IPC)
      const deserializedData: AnalyticsData = {
        ...data,
        conversations: data.conversations.map((conv) => ({
          ...conv,
          timestamp: new Date(conv.timestamp),
        })),
        chartData: {
          costOverTime: data.chartData.costOverTime.map((point) => ({
            ...point,
            timestamp: new Date(point.timestamp),
          })),
          tokensOverTime: data.chartData.tokensOverTime.map((point) => ({
            ...point,
            timestamp: new Date(point.timestamp),
          })),
          sessionActivity: data.chartData.sessionActivity.map((point) => ({
            ...point,
            timestamp: new Date(point.timestamp),
          })),
          sessionDuration: data.chartData.sessionDuration || [],
          modelDistribution: data.chartData.modelDistribution || [],
          featureCostDistribution: (data.chartData.featureCostDistribution || []).map((point) => ({
            ...point,
            timestamp: new Date(point.timestamp),
          })),
        },
      };

      setAnalyticsData(deserializedData);
    };

    // Use the window.electron IPC API to listen for updates
    const removeListener = window.electronAPI.onAnalyticsDataUpdate(handleDataUpdate);

    return () => {
      // Stop polling when component unmounts
      console.log('[useAnalyticsData] Stopping analytics polling');
      window.electronAPI.stopAnalyticsPolling();
      removeListener();
    };
  }, [dbPath]);
}
