import { create } from 'zustand';
import type { ROISettings, SpecROIWithMetrics, ROIAggregateMetrics } from '../../shared/types/roi';
import { DEFAULT_ROI_SETTINGS } from '../../shared/types/roi';

interface ROIState {
  settings: ROISettings;
  specs: SpecROIWithMetrics[];
  aggregate: ROIAggregateMetrics | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setSettings: (settings: ROISettings) => void;
  setSpecs: (specs: SpecROIWithMetrics[]) => void;
  setAggregate: (aggregate: ROIAggregateMetrics | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  settings: DEFAULT_ROI_SETTINGS,
  specs: [],
  aggregate: null,
  isLoading: false,
  error: null,
};

export const useROIStore = create<ROIState>((set) => ({
  ...initialState,

  setSettings: (settings) => set({ settings }),
  setSpecs: (specs) => set({ specs }),
  setAggregate: (aggregate) => set({ aggregate }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));

// Helper functions for external use

export function setROISettings(settings: ROISettings): void {
  useROIStore.getState().setSettings(settings);
}

export function setROISpecs(specs: SpecROIWithMetrics[]): void {
  useROIStore.getState().setSpecs(specs);
}

export function setROIAggregate(aggregate: ROIAggregateMetrics | null): void {
  useROIStore.getState().setAggregate(aggregate);
}

export function setROILoading(loading: boolean): void {
  useROIStore.getState().setLoading(loading);
}

export function setROIError(error: string | null): void {
  useROIStore.getState().setError(error);
}

export function resetROIStore(): void {
  useROIStore.getState().reset();
}

// Get current state snapshots
export function getROISettings(): ROISettings {
  return useROIStore.getState().settings;
}

export function getROISpecs(): SpecROIWithMetrics[] {
  return useROIStore.getState().specs;
}

export function getROIAggregate(): ROIAggregateMetrics | null {
  return useROIStore.getState().aggregate;
}

export function isROILoading(): boolean {
  return useROIStore.getState().isLoading;
}

export function getROIError(): string | null {
  return useROIStore.getState().error;
}
