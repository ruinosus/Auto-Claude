import { useCallback, useEffect } from 'react';
import { useROIStore } from '../stores/roi-store';
import type { ROISettings, SpecROI } from '../../shared/types/roi';

/**
 * Hook to manage ROI data fetching and state
 *
 * Provides methods to fetch settings, specs, and aggregate metrics from the
 * main process via IPC, as well as save/update operations.
 *
 * @param projectId - Optional project ID to filter specs by
 */
export function useROIData(projectId?: string) {
  const {
    settings,
    specs,
    aggregate,
    isLoading,
    error,
    setSettings,
    setSpecs,
    setAggregate,
    setLoading,
    setError
  } = useROIStore();

  const fetchSettings = useCallback(async () => {
    try {
      const result = await window.electronAPI.roi.getSettings();
      setSettings(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch ROI settings');
    }
  }, [setSettings, setError]);

  const fetchSpecs = useCallback(async () => {
    try {
      const result = await window.electronAPI.roi.getAllSpecs(projectId);
      setSpecs(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch ROI specs');
    }
  }, [projectId, setSpecs, setError]);

  const fetchAggregate = useCallback(async () => {
    try {
      const result = await window.electronAPI.roi.getAggregate(projectId);
      setAggregate(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch ROI aggregate');
    }
  }, [projectId, setAggregate, setError]);

  const refreshAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([fetchSettings(), fetchSpecs(), fetchAggregate()]);
    } finally {
      setLoading(false);
    }
  }, [fetchSettings, fetchSpecs, fetchAggregate, setLoading, setError]);

  const saveSettings = useCallback(async (newSettings: Partial<ROISettings>) => {
    try {
      await window.electronAPI.roi.saveSettings(newSettings);
      await fetchSettings();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save ROI settings');
      throw err;
    }
  }, [fetchSettings, setError]);

  const saveSpec = useCallback(async (spec: Partial<SpecROI> & { specId: string }) => {
    try {
      await window.electronAPI.roi.saveSpec(spec);
      await fetchSpecs();
      await fetchAggregate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save spec ROI');
      throw err;
    }
  }, [fetchSpecs, fetchAggregate, setError]);

  const deleteSpec = useCallback(async (specId: string) => {
    try {
      await window.electronAPI.roi.deleteSpec(specId);
      await fetchSpecs();
      await fetchAggregate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete spec ROI');
      throw err;
    }
  }, [fetchSpecs, fetchAggregate, setError]);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  return {
    settings,
    specs,
    aggregate,
    isLoading,
    error,
    refreshAll,
    saveSettings,
    saveSpec,
    deleteSpec,
  };
}
