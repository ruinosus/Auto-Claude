import { IPC_CHANNELS } from '../../../shared/constants';
import type {
  ROISettings,
  SpecROI,
  SpecROIWithMetrics,
  ROIAggregateMetrics,
  ProjectROISettings
} from '../../../shared/types/roi';
import { invokeIpc } from './ipc-utils';

/**
 * ROI API operations (nested under 'roi' property)
 */
export interface ROIAPI {
  roi: {
    getSettings: () => Promise<ROISettings>;
    saveSettings: (settings: Partial<ROISettings>) => Promise<{ success: boolean }>;
    getProjectSettings: (projectId: string) => Promise<ProjectROISettings | null>;
    saveProjectSettings: (projectId: string, hourlyRate: number | null) => Promise<{ success: boolean }>;
    getSpec: (specId: string) => Promise<SpecROI | null>;
    saveSpec: (spec: Partial<SpecROI> & { specId: string }) => Promise<{ success: boolean }>;
    getAllSpecs: (projectId?: string) => Promise<SpecROIWithMetrics[]>;
    getAggregate: (projectId?: string) => Promise<ROIAggregateMetrics>;
    deleteSpec: (specId: string) => Promise<{ success: boolean }>;
  };
}

/**
 * Creates the ROI API implementation
 */
export const createROIAPI = (): ROIAPI => ({
  roi: {
    getSettings: (): Promise<ROISettings> =>
      invokeIpc(IPC_CHANNELS.ROI_GET_SETTINGS),

    saveSettings: (settings: Partial<ROISettings>): Promise<{ success: boolean }> =>
      invokeIpc(IPC_CHANNELS.ROI_SAVE_SETTINGS, settings),

    getProjectSettings: (projectId: string): Promise<ProjectROISettings | null> =>
      invokeIpc(IPC_CHANNELS.ROI_GET_PROJECT_SETTINGS, projectId),

    saveProjectSettings: (projectId: string, hourlyRate: number | null): Promise<{ success: boolean }> =>
      invokeIpc(IPC_CHANNELS.ROI_SAVE_PROJECT_SETTINGS, projectId, hourlyRate),

    getSpec: (specId: string): Promise<SpecROI | null> =>
      invokeIpc(IPC_CHANNELS.ROI_GET_SPEC, specId),

    saveSpec: (spec: Partial<SpecROI> & { specId: string }): Promise<{ success: boolean }> =>
      invokeIpc(IPC_CHANNELS.ROI_SAVE_SPEC, spec),

    getAllSpecs: (projectId?: string): Promise<SpecROIWithMetrics[]> =>
      invokeIpc(IPC_CHANNELS.ROI_GET_ALL_SPECS, projectId),

    getAggregate: (projectId?: string): Promise<ROIAggregateMetrics> =>
      invokeIpc(IPC_CHANNELS.ROI_GET_AGGREGATE, projectId),

    deleteSpec: (specId: string): Promise<{ success: boolean }> =>
      invokeIpc(IPC_CHANNELS.ROI_DELETE_SPEC, specId)
  }
});
