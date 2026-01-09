// apps/frontend/src/main/services/squad-service.ts
//
// Squad Service - Manages squad configurations for team-based ROI calculations
//
// Architecture:
// - Squads: stored in ~/.config/auto-claude/store/squads.json (global)
// - Project-Squad associations: stored in settings.json under roi.projectSquads
// - Squad config for builds: written to {project}/.auto-claude/squad_config.json

import path from 'path';
import { existsSync, readFileSync, writeFileSync, mkdirSync, unlinkSync } from 'fs';
import { app } from 'electron';
import { v4 as uuidv4 } from 'uuid';
import type {
  Squad,
  SquadsFile,
  SquadFormData,
} from '../../shared/types/squad';
import {
  DEFAULT_SQUAD_CONFIG,
  SQUADS_FILE_VERSION,
} from '../../shared/types/squad';

export class SquadService {
  private squadsPath: string;
  private settingsPath: string;

  constructor() {
    const userDataPath = app.getPath('userData');
    const storeDir = path.join(userDataPath, 'store');

    // Ensure store directory exists
    if (!existsSync(storeDir)) {
      mkdirSync(storeDir, { recursive: true });
    }

    this.squadsPath = path.join(storeDir, 'squads.json');
    this.settingsPath = path.join(userDataPath, 'settings.json');
  }

  // ============ Squads File Operations ============

  /**
   * Read the squads.json file
   */
  private readSquadsFile(): SquadsFile {
    if (!existsSync(this.squadsPath)) {
      return { squads: [], version: SQUADS_FILE_VERSION };
    }
    try {
      const content = readFileSync(this.squadsPath, 'utf-8');
      const data = JSON.parse(content) as SquadsFile;

      // Migration if needed
      if (!data.version) {
        data.version = SQUADS_FILE_VERSION;
      }

      return data;
    } catch (error) {
      console.error('[squad-service] Failed to read squads.json:', error);
      return { squads: [], version: SQUADS_FILE_VERSION };
    }
  }

  /**
   * Write to squads.json
   */
  private writeSquadsFile(data: SquadsFile): void {
    try {
      writeFileSync(this.squadsPath, JSON.stringify(data, null, 2), 'utf-8');
      console.log('[squad-service] Squads saved to squads.json');
    } catch (error) {
      console.error('[squad-service] Failed to write squads.json:', error);
      throw error;
    }
  }

  /**
   * Read settings.json file
   */
  private readSettingsFile(): Record<string, unknown> {
    if (!existsSync(this.settingsPath)) {
      return {};
    }
    try {
      const content = readFileSync(this.settingsPath, 'utf-8');
      return JSON.parse(content);
    } catch {
      return {};
    }
  }

  /**
   * Write settings.json file
   */
  private writeSettingsFile(settings: Record<string, unknown>): void {
    writeFileSync(this.settingsPath, JSON.stringify(settings, null, 2), 'utf-8');
  }

  // ============ Squad CRUD Operations ============

  /**
   * Get all squads
   */
  getAllSquads(): Squad[] {
    const data = this.readSquadsFile();
    return data.squads;
  }

  /**
   * Get a squad by ID
   */
  getSquad(id: string): Squad | null {
    const data = this.readSquadsFile();
    return data.squads.find(s => s.id === id) || null;
  }

  /**
   * Create a new squad
   */
  createSquad(formData: SquadFormData): Squad {
    const data = this.readSquadsFile();

    const now = Date.now();
    const newSquad: Squad = {
      id: uuidv4(),
      name: formData.name,
      description: formData.description,
      stakeholderRates: formData.stakeholderRates || DEFAULT_SQUAD_CONFIG.stakeholderRates,
      defaultHourlyRate: formData.defaultHourlyRate || DEFAULT_SQUAD_CONFIG.defaultHourlyRate,
      timeSavings: formData.timeSavings || DEFAULT_SQUAD_CONFIG.timeSavings,
      preventionValues: formData.preventionValues || DEFAULT_SQUAD_CONFIG.preventionValues,
      qualityMultipliers: formData.qualityMultipliers || DEFAULT_SQUAD_CONFIG.qualityMultipliers,
      featureMultipliers: formData.featureMultipliers,
      createdAt: now,
      updatedAt: now,
    };

    data.squads.push(newSquad);
    this.writeSquadsFile(data);

    console.log('[squad-service] Created squad:', newSquad.name);
    return newSquad;
  }

  /**
   * Update an existing squad
   */
  updateSquad(id: string, formData: Partial<SquadFormData>): Squad | null {
    const data = this.readSquadsFile();
    const index = data.squads.findIndex(s => s.id === id);

    if (index === -1) {
      console.error('[squad-service] Squad not found:', id);
      return null;
    }

    const existingSquad = data.squads[index];
    const updatedSquad: Squad = {
      ...existingSquad,
      ...formData,
      id: existingSquad.id, // Preserve ID
      createdAt: existingSquad.createdAt, // Preserve creation time
      updatedAt: Date.now(),
    };

    data.squads[index] = updatedSquad;
    this.writeSquadsFile(data);

    console.log('[squad-service] Updated squad:', updatedSquad.name);
    return updatedSquad;
  }

  /**
   * Delete a squad
   */
  deleteSquad(id: string): boolean {
    const data = this.readSquadsFile();
    const initialLength = data.squads.length;
    data.squads = data.squads.filter(s => s.id !== id);

    if (data.squads.length === initialLength) {
      console.error('[squad-service] Squad not found for deletion:', id);
      return false;
    }

    this.writeSquadsFile(data);

    // Also remove any project associations for this squad
    this.removeSquadAssociations(id);

    console.log('[squad-service] Deleted squad:', id);
    return true;
  }

  // ============ Project-Squad Association ============

  /**
   * Get the squad associated with a project
   */
  getProjectSquad(projectPath: string): Squad | null {
    const allSettings = this.readSettingsFile();
    const roi = allSettings.roi as Record<string, unknown> | undefined;
    if (!roi) return null;

    const projectSquads = roi.projectSquads as Record<string, string> | undefined;
    if (!projectSquads) return null;

    const squadId = projectSquads[projectPath];
    if (!squadId) return null;

    return this.getSquad(squadId);
  }

  /**
   * Get the squad ID associated with a project
   */
  getProjectSquadId(projectPath: string): string | null {
    const allSettings = this.readSettingsFile();
    const roi = allSettings.roi as Record<string, unknown> | undefined;
    if (!roi) return null;

    const projectSquads = roi.projectSquads as Record<string, string> | undefined;
    if (!projectSquads) return null;

    return projectSquads[projectPath] || null;
  }

  /**
   * Set the squad for a project
   */
  setProjectSquad(projectPath: string, squadId: string | null): boolean {
    const allSettings = this.readSettingsFile();
    const roi = (allSettings.roi as Record<string, unknown>) || {};
    const projectSquads = (roi.projectSquads as Record<string, string>) || {};

    if (squadId === null) {
      // Remove association
      delete projectSquads[projectPath];
      console.log('[squad-service] Removed squad association for project:', projectPath);

      // Also remove squad_config.json from project
      this.clearSquadConfigFromProject(projectPath);
    } else {
      // Verify squad exists
      const squad = this.getSquad(squadId);
      if (!squad) {
        console.error('[squad-service] Cannot associate project with non-existent squad:', squadId);
        return false;
      }

      projectSquads[projectPath] = squadId;
      console.log('[squad-service] Associated project', projectPath, 'with squad:', squad.name);
    }

    roi.projectSquads = projectSquads;
    allSettings.roi = roi;
    this.writeSettingsFile(allSettings);

    return true;
  }

  /**
   * Remove all project associations for a specific squad
   */
  private removeSquadAssociations(squadId: string): void {
    const allSettings = this.readSettingsFile();
    const roi = allSettings.roi as Record<string, unknown> | undefined;
    if (!roi) return;

    const projectSquads = roi.projectSquads as Record<string, string> | undefined;
    if (!projectSquads) return;

    let changed = false;
    for (const [projectPath, id] of Object.entries(projectSquads)) {
      if (id === squadId) {
        delete projectSquads[projectPath];
        changed = true;

        // Also remove squad_config.json from the project
        this.clearSquadConfigFromProject(projectPath);
      }
    }

    if (changed) {
      roi.projectSquads = projectSquads;
      allSettings.roi = roi;
      this.writeSettingsFile(allSettings);
      console.log('[squad-service] Removed all associations for deleted squad:', squadId);
    }
  }

  // ============ Squad Config File Operations (for backend) ============

  /**
   * Write squad config to project's .auto-claude directory
   * This is called when starting a build to make the config available to the Python backend
   */
  writeSquadConfigToProject(projectPath: string): boolean {
    const squad = this.getProjectSquad(projectPath);
    if (!squad) {
      // No squad assigned - clear any existing config file
      this.clearSquadConfigFromProject(projectPath);
      return false;
    }

    const autoClaudeDir = path.join(projectPath, '.auto-claude');
    const configPath = path.join(autoClaudeDir, 'squad_config.json');

    try {
      // Ensure .auto-claude directory exists
      if (!existsSync(autoClaudeDir)) {
        mkdirSync(autoClaudeDir, { recursive: true });
      }

      // Write squad config in the format expected by Python backend
      const config = {
        id: squad.id,
        name: squad.name,
        description: squad.description || '',
        stakeholderRates: squad.stakeholderRates,
        defaultHourlyRate: squad.defaultHourlyRate,
        timeSavings: squad.timeSavings,
        preventionValues: squad.preventionValues,
        qualityMultipliers: squad.qualityMultipliers,
        featureMultipliers: squad.featureMultipliers || {},
      };

      writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf-8');
      console.log('[squad-service] Wrote squad config to:', configPath);
      return true;
    } catch (error) {
      console.error('[squad-service] Failed to write squad config:', error);
      return false;
    }
  }

  /**
   * Clear squad config from project's .auto-claude directory
   */
  clearSquadConfigFromProject(projectPath: string): boolean {
    const configPath = path.join(projectPath, '.auto-claude', 'squad_config.json');

    try {
      if (existsSync(configPath)) {
        unlinkSync(configPath);
        console.log('[squad-service] Removed squad config from:', configPath);
      }
      return true;
    } catch (error) {
      console.error('[squad-service] Failed to remove squad config:', error);
      return false;
    }
  }

  // ============ Utility Methods ============

  /**
   * Get squads with usage statistics
   */
  getSquadsWithStats(): Array<Squad & { projectCount: number }> {
    const squads = this.getAllSquads();
    const allSettings = this.readSettingsFile();
    const roi = allSettings.roi as Record<string, unknown> | undefined;
    const projectSquads = (roi?.projectSquads as Record<string, string>) || {};

    // Count projects per squad
    const squadProjectCount: Record<string, number> = {};
    for (const squadId of Object.values(projectSquads)) {
      squadProjectCount[squadId] = (squadProjectCount[squadId] || 0) + 1;
    }

    return squads.map(squad => ({
      ...squad,
      projectCount: squadProjectCount[squad.id] || 0,
    }));
  }

  /**
   * Duplicate an existing squad with a new name
   */
  duplicateSquad(id: string, newName: string): Squad | null {
    const original = this.getSquad(id);
    if (!original) {
      console.error('[squad-service] Cannot duplicate non-existent squad:', id);
      return null;
    }

    const formData: SquadFormData = {
      name: newName,
      description: original.description ? `Copy of ${original.description}` : undefined,
      stakeholderRates: { ...original.stakeholderRates },
      defaultHourlyRate: original.defaultHourlyRate,
      timeSavings: { ...original.timeSavings },
      preventionValues: { ...original.preventionValues },
      qualityMultipliers: { ...original.qualityMultipliers },
      featureMultipliers: original.featureMultipliers ? { ...original.featureMultipliers } : undefined,
    };

    return this.createSquad(formData);
  }

  // ============ Import/Export Operations ============

  /**
   * Export squads to a JSON file
   * Returns the exported data as a string for the renderer to save
   */
  exportSquads(squadIds?: string[]): { data: string; filename: string } {
    const allSquads = this.getAllSquads();

    // If specific IDs provided, filter to those squads only
    const squadsToExport = squadIds
      ? allSquads.filter(s => squadIds.includes(s.id))
      : allSquads;

    if (squadsToExport.length === 0) {
      throw new Error('No squads to export');
    }

    const exportData = {
      version: SQUADS_FILE_VERSION,
      exportedAt: new Date().toISOString(),
      squads: squadsToExport.map(squad => ({
        // Export without internal IDs and timestamps (will be regenerated on import)
        name: squad.name,
        description: squad.description,
        stakeholderRates: squad.stakeholderRates,
        defaultHourlyRate: squad.defaultHourlyRate,
        timeSavings: squad.timeSavings,
        preventionValues: squad.preventionValues,
        qualityMultipliers: squad.qualityMultipliers,
        featureMultipliers: squad.featureMultipliers,
      })),
    };

    const filename = squadsToExport.length === 1
      ? `squad-${squadsToExport[0].name.toLowerCase().replace(/\s+/g, '-')}.json`
      : `squads-export-${new Date().toISOString().split('T')[0]}.json`;

    console.log('[squad-service] Exporting', squadsToExport.length, 'squads');
    return {
      data: JSON.stringify(exportData, null, 2),
      filename,
    };
  }

  /**
   * Import squads from JSON data
   * Returns the imported squads
   */
  importSquads(jsonData: string, options?: { overwriteExisting?: boolean }): {
    imported: Squad[];
    skipped: string[];
    errors: string[];
  } {
    const imported: Squad[] = [];
    const skipped: string[] = [];
    const errors: string[] = [];

    let parsed: {
      version?: number;
      squads?: Array<Partial<SquadFormData>>;
    };

    try {
      parsed = JSON.parse(jsonData);
    } catch (e) {
      errors.push('Invalid JSON format');
      return { imported, skipped, errors };
    }

    if (!parsed.squads || !Array.isArray(parsed.squads)) {
      errors.push('Invalid squad export format: missing "squads" array');
      return { imported, skipped, errors };
    }

    const existingSquads = this.getAllSquads();
    const existingNames = new Set(existingSquads.map(s => s.name.toLowerCase()));

    for (const squadData of parsed.squads) {
      try {
        // Validate required fields
        if (!squadData.name) {
          errors.push('Squad missing required "name" field');
          continue;
        }

        // Check for duplicate names
        const normalizedName = squadData.name.toLowerCase();
        if (existingNames.has(normalizedName)) {
          if (options?.overwriteExisting) {
            // Find and update existing squad
            const existing = existingSquads.find(s => s.name.toLowerCase() === normalizedName);
            if (existing) {
              const updated = this.updateSquad(existing.id, squadData as SquadFormData);
              if (updated) {
                imported.push(updated);
                continue;
              }
            }
          }
          skipped.push(`Squad "${squadData.name}" already exists`);
          continue;
        }

        // Create new squad with defaults for missing fields
        const formData: SquadFormData = {
          name: squadData.name,
          description: squadData.description,
          stakeholderRates: squadData.stakeholderRates || DEFAULT_SQUAD_CONFIG.stakeholderRates,
          defaultHourlyRate: squadData.defaultHourlyRate ?? DEFAULT_SQUAD_CONFIG.defaultHourlyRate,
          timeSavings: squadData.timeSavings || DEFAULT_SQUAD_CONFIG.timeSavings,
          preventionValues: squadData.preventionValues || DEFAULT_SQUAD_CONFIG.preventionValues,
          qualityMultipliers: squadData.qualityMultipliers || DEFAULT_SQUAD_CONFIG.qualityMultipliers,
          featureMultipliers: squadData.featureMultipliers,
        };

        const newSquad = this.createSquad(formData);
        imported.push(newSquad);
        existingNames.add(normalizedName);
      } catch (e) {
        const message = e instanceof Error ? e.message : 'Unknown error';
        errors.push(`Failed to import squad "${squadData.name || 'unknown'}": ${message}`);
      }
    }

    console.log('[squad-service] Import complete:', imported.length, 'imported,', skipped.length, 'skipped,', errors.length, 'errors');
    return { imported, skipped, errors };
  }
}

// Singleton instance
let squadService: SquadService | null = null;

export function getSquadService(): SquadService {
  if (!squadService) {
    squadService = new SquadService();
  }
  return squadService;
}
