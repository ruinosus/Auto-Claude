import { create } from 'zustand';
import type { Squad, SquadFormData } from '../../shared/types/squad';

interface SquadState {
  squads: Squad[];
  selectedSquadId: string | null;
  projectSquads: Map<string, string>; // projectId -> squadId
  isLoading: boolean;
  error: string | null;

  // Actions
  setSquads: (squads: Squad[]) => void;
  addSquad: (squad: Squad) => void;
  updateSquad: (squadId: string, updates: Partial<Squad>) => void;
  removeSquad: (squadId: string) => void;
  setSelectedSquadId: (squadId: string | null) => void;
  setProjectSquad: (projectId: string, squadId: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  squads: [],
  selectedSquadId: null,
  projectSquads: new Map<string, string>(),
  isLoading: false,
  error: null,
};

export const useSquadStore = create<SquadState>((set, get) => ({
  ...initialState,

  setSquads: (squads) => set({ squads }),

  addSquad: (squad) => set((state) => ({
    squads: [...state.squads, squad],
  })),

  updateSquad: (squadId, updates) => set((state) => ({
    squads: state.squads.map((s) =>
      s.id === squadId ? { ...s, ...updates } : s
    ),
  })),

  removeSquad: (squadId) => set((state) => ({
    squads: state.squads.filter((s) => s.id !== squadId),
    selectedSquadId: state.selectedSquadId === squadId ? null : state.selectedSquadId,
  })),

  setSelectedSquadId: (squadId) => set({ selectedSquadId: squadId }),

  setProjectSquad: (projectId, squadId) => set((state) => {
    const newProjectSquads = new Map(state.projectSquads);
    if (squadId) {
      newProjectSquads.set(projectId, squadId);
    } else {
      newProjectSquads.delete(projectId);
    }
    return { projectSquads: newProjectSquads };
  }),

  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));

// =============================================================================
// API Functions (interface with IPC)
// =============================================================================

/**
 * Fetch all squads from storage
 */
export async function fetchSquads(): Promise<Squad[]> {
  const store = useSquadStore.getState();
  store.setLoading(true);
  store.setError(null);

  try {
    const squads = await window.electronAPI.squad.getAll();
    store.setSquads(squads);
    return squads;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to fetch squads';
    store.setError(message);
    throw error;
  } finally {
    store.setLoading(false);
  }
}

/**
 * Fetch a single squad by ID
 */
export async function fetchSquad(squadId: string): Promise<Squad | null> {
  try {
    return await window.electronAPI.squad.get(squadId);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to fetch squad';
    useSquadStore.getState().setError(message);
    throw error;
  }
}

/**
 * Create a new squad
 */
export async function createSquad(formData: SquadFormData): Promise<Squad> {
  const store = useSquadStore.getState();
  store.setLoading(true);
  store.setError(null);

  try {
    const result = await window.electronAPI.squad.create(formData);
    if (!result.success || !result.squad) {
      throw new Error(result.error || 'Failed to create squad');
    }
    store.addSquad(result.squad);
    return result.squad;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to create squad';
    store.setError(message);
    throw error;
  } finally {
    store.setLoading(false);
  }
}

/**
 * Update an existing squad
 */
export async function updateSquad(squadId: string, formData: Partial<SquadFormData>): Promise<Squad> {
  const store = useSquadStore.getState();
  store.setLoading(true);
  store.setError(null);

  try {
    const result = await window.electronAPI.squad.update(squadId, formData);
    if (!result.success || !result.squad) {
      throw new Error(result.error || 'Failed to update squad');
    }
    store.updateSquad(squadId, result.squad);
    return result.squad;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to update squad';
    store.setError(message);
    throw error;
  } finally {
    store.setLoading(false);
  }
}

/**
 * Delete a squad
 */
export async function deleteSquad(squadId: string): Promise<void> {
  const store = useSquadStore.getState();
  store.setLoading(true);
  store.setError(null);

  try {
    const result = await window.electronAPI.squad.delete(squadId);
    if (!result.success) {
      throw new Error(result.error || 'Failed to delete squad');
    }
    store.removeSquad(squadId);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to delete squad';
    store.setError(message);
    throw error;
  } finally {
    store.setLoading(false);
  }
}

/**
 * Get the squad associated with a project
 */
export async function fetchProjectSquad(projectId: string): Promise<Squad | null> {
  try {
    return await window.electronAPI.squad.getProjectSquad(projectId);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to fetch project squad';
    useSquadStore.getState().setError(message);
    throw error;
  }
}

/**
 * Set the squad for a project
 */
export async function setProjectSquad(projectId: string, squadId: string | null): Promise<void> {
  const store = useSquadStore.getState();

  try {
    const result = await window.electronAPI.squad.setProjectSquad(projectId, squadId);
    if (!result.success) {
      throw new Error(result.error || 'Failed to set project squad');
    }
    store.setProjectSquad(projectId, squadId);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to set project squad';
    store.setError(message);
    throw error;
  }
}

/**
 * Write squad config to project for build startup
 */
export async function writeSquadConfigToProject(projectId: string): Promise<void> {
  try {
    const result = await window.electronAPI.squad.writeConfigToProject(projectId);
    if (!result.success) {
      throw new Error(result.error || 'Failed to write squad config to project');
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to write squad config';
    useSquadStore.getState().setError(message);
    throw error;
  }
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get all squads from store
 */
export function getSquads(): Squad[] {
  return useSquadStore.getState().squads;
}

/**
 * Get a squad by ID from store
 */
export function getSquadById(squadId: string): Squad | undefined {
  return useSquadStore.getState().squads.find((s) => s.id === squadId);
}

/**
 * Get the selected squad from store
 */
export function getSelectedSquad(): Squad | undefined {
  const { squads, selectedSquadId } = useSquadStore.getState();
  return selectedSquadId ? squads.find((s) => s.id === selectedSquadId) : undefined;
}

/**
 * Get squad ID for a project from store
 */
export function getProjectSquadId(projectId: string): string | undefined {
  return useSquadStore.getState().projectSquads.get(projectId);
}

/**
 * Check if store is loading
 */
export function isSquadLoading(): boolean {
  return useSquadStore.getState().isLoading;
}

/**
 * Get current error from store
 */
export function getSquadError(): string | null {
  return useSquadStore.getState().error;
}

/**
 * Reset the squad store
 */
export function resetSquadStore(): void {
  useSquadStore.getState().reset();
}
