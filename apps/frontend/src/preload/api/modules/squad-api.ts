import { IPC_CHANNELS } from '../../../shared/constants';
import type { Squad, SquadFormData } from '../../../shared/types/squad';
import { invokeIpc } from './ipc-utils';

/**
 * Export result type
 */
export interface SquadExportResult {
  success: boolean;
  canceled?: boolean;
  filePath?: string;
  error?: string;
}

/**
 * Import result type
 */
export interface SquadImportResult {
  success: boolean;
  canceled?: boolean;
  imported?: Squad[];
  skipped?: string[];
  errors?: string[];
  allSquads?: Squad[];
  error?: string;
}

/**
 * Squad API operations (nested under 'squad' property)
 */
export interface SquadAPI {
  squad: {
    getAll: () => Promise<Squad[]>;
    get: (squadId: string) => Promise<Squad | null>;
    create: (formData: SquadFormData) => Promise<{ success: boolean; squad?: Squad; error?: string }>;
    update: (squadId: string, formData: Partial<SquadFormData>) => Promise<{ success: boolean; squad?: Squad; error?: string }>;
    delete: (squadId: string) => Promise<{ success: boolean; error?: string }>;
    getProjectSquad: (projectId: string) => Promise<Squad | null>;
    setProjectSquad: (projectId: string, squadId: string | null) => Promise<{ success: boolean; error?: string }>;
    writeConfigToProject: (projectId: string) => Promise<{ success: boolean; error?: string }>;
    export: (squadIds?: string[]) => Promise<SquadExportResult>;
    import: (options?: { overwriteExisting?: boolean }) => Promise<SquadImportResult>;
  };
}

/**
 * Creates the Squad API implementation
 */
export const createSquadAPI = (): SquadAPI => ({
  squad: {
    getAll: (): Promise<Squad[]> =>
      invokeIpc(IPC_CHANNELS.SQUAD_GET_ALL),

    get: (squadId: string): Promise<Squad | null> =>
      invokeIpc(IPC_CHANNELS.SQUAD_GET, squadId),

    create: (formData: SquadFormData): Promise<{ success: boolean; squad?: Squad; error?: string }> =>
      invokeIpc(IPC_CHANNELS.SQUAD_CREATE, formData),

    update: (squadId: string, formData: Partial<SquadFormData>): Promise<{ success: boolean; squad?: Squad; error?: string }> =>
      invokeIpc(IPC_CHANNELS.SQUAD_UPDATE, squadId, formData),

    delete: (squadId: string): Promise<{ success: boolean; error?: string }> =>
      invokeIpc(IPC_CHANNELS.SQUAD_DELETE, squadId),

    getProjectSquad: (projectId: string): Promise<Squad | null> =>
      invokeIpc(IPC_CHANNELS.SQUAD_GET_PROJECT_SQUAD, projectId),

    setProjectSquad: (projectId: string, squadId: string | null): Promise<{ success: boolean; error?: string }> =>
      invokeIpc(IPC_CHANNELS.SQUAD_SET_PROJECT_SQUAD, projectId, squadId),

    writeConfigToProject: (projectId: string): Promise<{ success: boolean; error?: string }> =>
      invokeIpc(IPC_CHANNELS.SQUAD_WRITE_CONFIG_TO_PROJECT, projectId),

    export: (squadIds?: string[]): Promise<SquadExportResult> =>
      invokeIpc(IPC_CHANNELS.SQUAD_EXPORT, squadIds),

    import: (options?: { overwriteExisting?: boolean }): Promise<SquadImportResult> =>
      invokeIpc(IPC_CHANNELS.SQUAD_IMPORT, options)
  }
});
