// apps/frontend/src/main/ipc-handlers/roi-handlers.ts

import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { getROIService } from '../services/roi-service';
import { projectStore } from '../project-store';
import type { ROISettings } from '../../shared/types/roi';

/**
 * Helper to get project path from project ID
 */
function getProjectPath(projectId?: string): string | undefined {
  if (!projectId) return undefined;
  const project = projectStore.getProject(projectId);
  return project?.path;
}

export function setupROIHandlers(): void {
  const roiService = getROIService();

  // Settings handlers (global, stored in userData/roi.db)
  ipcMain.handle(IPC_CHANNELS.ROI_GET_SETTINGS, () => {
    return roiService.getSettings();
  });

  ipcMain.handle(IPC_CHANNELS.ROI_SAVE_SETTINGS, (_event, settings: Partial<ROISettings>) => {
    roiService.saveSettings(settings);
    return { success: true };
  });

  // Project settings handlers (stored in userData/roi.db)
  ipcMain.handle(IPC_CHANNELS.ROI_GET_PROJECT_SETTINGS, (_event, projectId: string) => {
    const projectPath = getProjectPath(projectId);
    return roiService.getProjectSettings(projectPath || projectId);
  });

  ipcMain.handle(IPC_CHANNELS.ROI_SAVE_PROJECT_SETTINGS, (_event, projectId: string, hourlyRate: number | null) => {
    const projectPath = getProjectPath(projectId);
    roiService.saveProjectSettings(projectPath || projectId, hourlyRate);
    return { success: true };
  });

  // Spec ROI handlers (read from project's analytics.db)
  ipcMain.handle(IPC_CHANNELS.ROI_GET_SPEC, (_event, specId: string, projectId?: string) => {
    const projectPath = getProjectPath(projectId);
    return roiService.getSpec(specId, projectPath);
  });

  ipcMain.handle(IPC_CHANNELS.ROI_GET_ALL_SPECS, (_event, projectId?: string) => {
    const projectPath = getProjectPath(projectId);
    console.log('[roi-handlers] getAllSpecs for project:', projectId, '-> path:', projectPath);
    return roiService.getAllSpecs(projectPath);
  });

  ipcMain.handle(IPC_CHANNELS.ROI_GET_AGGREGATE, (_event, projectId?: string) => {
    const projectPath = getProjectPath(projectId);
    console.log('[roi-handlers] getAggregate for project:', projectId, '-> path:', projectPath);
    return roiService.getAggregate(projectPath);
  });

  // Note: saveSpec and deleteSpec are handled by Python backend writing to analytics.db
  // These handlers are kept for backwards compatibility but may not work
  ipcMain.handle(IPC_CHANNELS.ROI_SAVE_SPEC, (_event, _spec) => {
    console.log('[roi-handlers] saveSpec called - spec data is managed by backend');
    return { success: true, message: 'Spec ROI is managed by backend' };
  });

  ipcMain.handle(IPC_CHANNELS.ROI_DELETE_SPEC, (_event, _specId: string) => {
    console.log('[roi-handlers] deleteSpec called - spec data is managed by backend');
    return { success: true, message: 'Spec ROI is managed by backend' };
  });

  console.log('[roi-handlers] ROI IPC handlers registered');
}
