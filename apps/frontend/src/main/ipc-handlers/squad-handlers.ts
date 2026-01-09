// apps/frontend/src/main/ipc-handlers/squad-handlers.ts

import { ipcMain, dialog, BrowserWindow } from 'electron';
import { writeFileSync, readFileSync } from 'fs';
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { getSquadService } from '../services/squad-service';
import { projectStore } from '../project-store';
import type { SquadFormData } from '../../shared/types/squad';

/**
 * Helper to get project path from project ID
 */
function getProjectPath(projectId?: string): string | undefined {
  if (!projectId) return undefined;
  const project = projectStore.getProject(projectId);
  return project?.path;
}

export function setupSquadHandlers(): void {
  const squadService = getSquadService();

  // Get all squads
  ipcMain.handle(IPC_CHANNELS.SQUAD_GET_ALL, () => {
    return squadService.getAllSquads();
  });

  // Get a specific squad by ID
  ipcMain.handle(IPC_CHANNELS.SQUAD_GET, (_event, squadId: string) => {
    return squadService.getSquad(squadId);
  });

  // Create a new squad
  ipcMain.handle(IPC_CHANNELS.SQUAD_CREATE, (_event, formData: SquadFormData) => {
    try {
      const squad = squadService.createSquad(formData);
      return { success: true, squad };
    } catch (error) {
      console.error('[squad-handlers] Failed to create squad:', error);
      return { success: false, error: String(error) };
    }
  });

  // Update an existing squad
  ipcMain.handle(IPC_CHANNELS.SQUAD_UPDATE, (_event, squadId: string, formData: Partial<SquadFormData>) => {
    try {
      const squad = squadService.updateSquad(squadId, formData);
      if (!squad) {
        return { success: false, error: 'Squad not found' };
      }
      return { success: true, squad };
    } catch (error) {
      console.error('[squad-handlers] Failed to update squad:', error);
      return { success: false, error: String(error) };
    }
  });

  // Delete a squad
  ipcMain.handle(IPC_CHANNELS.SQUAD_DELETE, (_event, squadId: string) => {
    try {
      const success = squadService.deleteSquad(squadId);
      return { success };
    } catch (error) {
      console.error('[squad-handlers] Failed to delete squad:', error);
      return { success: false, error: String(error) };
    }
  });

  // Get the squad associated with a project
  ipcMain.handle(IPC_CHANNELS.SQUAD_GET_PROJECT_SQUAD, (_event, projectId: string) => {
    const projectPath = getProjectPath(projectId);
    if (!projectPath) {
      return null;
    }
    return squadService.getProjectSquad(projectPath);
  });

  // Set the squad for a project
  ipcMain.handle(IPC_CHANNELS.SQUAD_SET_PROJECT_SQUAD, (_event, projectId: string, squadId: string | null) => {
    const projectPath = getProjectPath(projectId);
    if (!projectPath) {
      return { success: false, error: 'Project not found' };
    }

    try {
      const success = squadService.setProjectSquad(projectPath, squadId);
      return { success };
    } catch (error) {
      console.error('[squad-handlers] Failed to set project squad:', error);
      return { success: false, error: String(error) };
    }
  });

  // Write squad config to project (for build startup)
  ipcMain.handle(IPC_CHANNELS.SQUAD_WRITE_CONFIG_TO_PROJECT, (_event, projectId: string) => {
    const projectPath = getProjectPath(projectId);
    if (!projectPath) {
      return { success: false, error: 'Project not found' };
    }

    try {
      const success = squadService.writeSquadConfigToProject(projectPath);
      return { success };
    } catch (error) {
      console.error('[squad-handlers] Failed to write squad config to project:', error);
      return { success: false, error: String(error) };
    }
  });

  // Export squads to JSON file
  ipcMain.handle(IPC_CHANNELS.SQUAD_EXPORT, async (_event, squadIds?: string[]) => {
    try {
      const { data, filename } = squadService.exportSquads(squadIds);

      // Show save dialog
      const win = BrowserWindow.getFocusedWindow();
      const dialogOptions: Electron.SaveDialogOptions = {
        title: 'Export Squads',
        defaultPath: filename,
        filters: [
          { name: 'JSON Files', extensions: ['json'] },
          { name: 'All Files', extensions: ['*'] }
        ]
      };

      const result = win
        ? await dialog.showSaveDialog(win, dialogOptions)
        : await dialog.showSaveDialog(dialogOptions);

      if (result.canceled || !result.filePath) {
        return { success: false, canceled: true };
      }

      // Write file
      writeFileSync(result.filePath, data, 'utf-8');
      console.log('[squad-handlers] Exported squads to:', result.filePath);

      return { success: true, filePath: result.filePath };
    } catch (error) {
      console.error('[squad-handlers] Failed to export squads:', error);
      return { success: false, error: String(error) };
    }
  });

  // Import squads from JSON file
  ipcMain.handle(IPC_CHANNELS.SQUAD_IMPORT, async (_event, options?: { overwriteExisting?: boolean }) => {
    try {
      // Show open dialog
      const win = BrowserWindow.getFocusedWindow();
      const dialogOptions: Electron.OpenDialogOptions = {
        title: 'Import Squads',
        filters: [
          { name: 'JSON Files', extensions: ['json'] },
          { name: 'All Files', extensions: ['*'] }
        ],
        properties: ['openFile']
      };

      const result = win
        ? await dialog.showOpenDialog(win, dialogOptions)
        : await dialog.showOpenDialog(dialogOptions);

      if (result.canceled || result.filePaths.length === 0) {
        return { success: false, canceled: true };
      }

      // Read file
      const filePath = result.filePaths[0];
      const jsonData = readFileSync(filePath, 'utf-8');

      // Import squads
      const importResult = squadService.importSquads(jsonData, options);

      // Refresh the squad list after import
      const allSquads = squadService.getAllSquads();

      return {
        success: true,
        imported: importResult.imported,
        skipped: importResult.skipped,
        errors: importResult.errors,
        allSquads, // Return updated list
      };
    } catch (error) {
      console.error('[squad-handlers] Failed to import squads:', error);
      return { success: false, error: String(error) };
    }
  });

  console.log('[squad-handlers] Squad IPC handlers registered');
}
