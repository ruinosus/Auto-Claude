// apps/frontend/src/main/services/roi-service.ts
//
// ROI Service - Manages ROI settings and reads spec data from project analytics
//
// Architecture:
// - ROI Settings: stored in settings.json (same as other app settings)
// - Spec ROI data: read from {project}/.auto-claude/analytics.db (written by Python backend)
//
// NO SEPARATE DATABASE - uses existing settings.json for settings

import Database from 'better-sqlite3';
import path from 'path';
import { existsSync, readFileSync, writeFileSync } from 'fs';
import { app } from 'electron';
import type {
  ROISettings,
  SpecROI,
  ROIMetrics,
  ROIAggregateMetrics,
  SpecROIWithMetrics
} from '../../shared/types/roi';
import { DEFAULT_ROI_SETTINGS } from '../../shared/types/roi';

export class ROIService {
  private settingsPath: string;

  constructor() {
    this.settingsPath = path.join(app.getPath('userData'), 'settings.json');
  }

  // ============ Settings Operations (from settings.json) ============

  /**
   * Read the full settings.json file
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
   * Write to settings.json, preserving other settings
   */
  private writeSettingsFile(settings: Record<string, unknown>): void {
    writeFileSync(this.settingsPath, JSON.stringify(settings, null, 2), 'utf-8');
  }

  /**
   * Get ROI settings from settings.json
   */
  getSettings(): ROISettings {
    const allSettings = this.readSettingsFile();
    const roi = allSettings.roi as ROISettings | undefined;

    if (!roi) {
      return { ...DEFAULT_ROI_SETTINGS };
    }

    // Merge with defaults to ensure all fields exist
    return {
      ...DEFAULT_ROI_SETTINGS,
      ...roi
    };
  }

  /**
   * Save ROI settings to settings.json
   */
  saveSettings(settings: Partial<ROISettings>): void {
    const allSettings = this.readSettingsFile();
    const currentRoi = (allSettings.roi as ROISettings) || { ...DEFAULT_ROI_SETTINGS };

    allSettings.roi = {
      ...currentRoi,
      ...settings
    };

    this.writeSettingsFile(allSettings);
    console.log('[roi-service] Settings saved to settings.json');
  }

  // ============ Project Settings (stored inline in settings.json) ============

  /**
   * Get project-specific ROI settings (hourly rate override)
   * Stored in settings.json under roi.projectOverrides[projectPath]
   */
  getProjectSettings(projectPath: string): { developerHourlyRate: number | null } | null {
    const allSettings = this.readSettingsFile();
    const roi = allSettings.roi as Record<string, unknown> | undefined;
    if (!roi) return null;

    const overrides = roi.projectOverrides as Record<string, { developerHourlyRate: number }> | undefined;
    if (!overrides || !overrides[projectPath]) return null;

    return overrides[projectPath];
  }

  /**
   * Save project-specific ROI settings
   */
  saveProjectSettings(projectPath: string, hourlyRate: number | null): void {
    const allSettings = this.readSettingsFile();
    const roi = (allSettings.roi as Record<string, unknown>) || {};
    const overrides = (roi.projectOverrides as Record<string, unknown>) || {};

    if (hourlyRate === null) {
      delete overrides[projectPath];
    } else {
      overrides[projectPath] = { developerHourlyRate: hourlyRate };
    }

    roi.projectOverrides = overrides;
    allSettings.roi = roi;
    this.writeSettingsFile(allSettings);
  }

  // ============ Spec ROI Operations (from project's analytics.db) ============

  /**
   * Get the analytics.db path for a project
   */
  private getProjectAnalyticsDbPath(projectPath: string): string {
    return path.join(projectPath, '.auto-claude', 'analytics.db');
  }

  /**
   * Check if a project has analytics.db with spec_roi table
   */
  private hasSpecRoiTable(dbPath: string): boolean {
    if (!existsSync(dbPath)) return false;

    try {
      const db = new Database(dbPath, { readonly: true });
      const result = db.prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='spec_roi'"
      ).get();
      db.close();
      return !!result;
    } catch {
      return false;
    }
  }

  /**
   * Get a single spec's ROI data from the project's analytics.db
   */
  getSpec(specId: string, projectPath?: string): SpecROI | null {
    if (!projectPath) return null;

    const dbPath = this.getProjectAnalyticsDbPath(projectPath);
    if (!this.hasSpecRoiTable(dbPath)) return null;

    try {
      const db = new Database(dbPath, { readonly: true });
      const row = db.prepare('SELECT * FROM spec_roi WHERE spec_id = ?').get(specId) as Record<string, unknown> | undefined;
      db.close();

      if (!row) return null;
      return this.rowToSpecROI(row);
    } catch (error) {
      console.error('[roi-service] Failed to get spec:', error);
      return null;
    }
  }

  /**
   * Get all specs with metrics from the project's analytics.db
   */
  getAllSpecs(projectPath?: string): SpecROIWithMetrics[] {
    if (!projectPath) return [];

    const dbPath = this.getProjectAnalyticsDbPath(projectPath);
    if (!this.hasSpecRoiTable(dbPath)) {
      console.log('[roi-service] No spec_roi table found in:', dbPath);
      return [];
    }

    const settings = this.getSettings();

    try {
      const db = new Database(dbPath, { readonly: true });
      const rows = db.prepare('SELECT * FROM spec_roi ORDER BY created_at DESC').all() as Record<string, unknown>[];
      db.close();

      return rows.map(row => {
        const spec = this.rowToSpecROI(row);
        const projectSettings = this.getProjectSettings(projectPath);
        const metrics = this.calculateMetrics(spec, settings, projectSettings);
        return { ...spec, metrics };
      });
    } catch (error) {
      console.error('[roi-service] Failed to get all specs:', error);
      return [];
    }
  }

  /**
   * Get aggregate ROI metrics from the project's analytics.db
   */
  getAggregate(projectPath?: string): ROIAggregateMetrics {
    const specs = this.getAllSpecs(projectPath);

    if (specs.length === 0) {
      return {
        totalROI: 0,
        totalSavings: 0,
        totalHoursSaved: 0,
        totalCost: 0,
        successRate: 0,
        specsCount: 0
      };
    }

    const totalCost = specs.reduce((sum, s) => sum + s.actualCost, 0);
    const totalSavings = specs.reduce((sum, s) => sum + s.metrics.costSavings, 0);
    const settings = this.getSettings();
    const totalHoursSaved = totalSavings / settings.developerHourlyRate;
    const passedSpecs = specs.filter(s => s.qaPassed).length;

    return {
      totalROI: totalCost > 0 ? (totalSavings / totalCost) * 100 : 0,
      totalSavings,
      totalHoursSaved,
      totalCost,
      successRate: (passedSpecs / specs.length) * 100,
      specsCount: specs.length
    };
  }

  // ============ Helper Methods ============

  private rowToSpecROI(row: Record<string, unknown>): SpecROI {
    return {
      specId: row.spec_id as string,
      projectId: row.project_id as string,
      estimatedBusinessValue: (row.estimated_business_value as number) || 0,
      estimatedHoursManual: row.estimated_hours_manual as number | null,
      developerRateOverride: row.developer_rate_override as number | null,
      actualCost: (row.actual_cost as number) || 0,
      totalTokens: (row.total_tokens as number) || 0,
      linesAdded: (row.lines_added as number) || 0,
      linesRemoved: (row.lines_removed as number) || 0,
      filesChanged: (row.files_changed as number) || 0,
      executionTimeSeconds: (row.execution_time_seconds as number) || 0,
      qaAttempts: (row.qa_attempts as number) || 0,
      qaPassed: Boolean(row.qa_passed),
      createdAt: row.created_at as string,
      completedAt: row.completed_at as string | null
    };
  }

  private calculateMetrics(
    spec: SpecROI,
    settings: ROISettings,
    projectSettings: { developerHourlyRate: number | null } | null
  ): ROIMetrics {
    const effectiveHourlyRate =
      spec.developerRateOverride ??
      projectSettings?.developerHourlyRate ??
      settings.developerHourlyRate;

    const linesChanged = spec.linesAdded + spec.linesRemoved;
    const autoEstimatedHours = (linesChanged * settings.minutesPerLine) / 60;
    const estimatedHours = spec.estimatedHoursManual ?? autoEstimatedHours;

    const estimatedManualCost = estimatedHours * effectiveHourlyRate;
    const costSavings = estimatedManualCost - spec.actualCost;
    const roiPercentage = spec.actualCost > 0 ? (costSavings / spec.actualCost) * 100 : 0;
    const costPerLine = linesChanged > 0 ? spec.actualCost / linesChanged : 0;
    const efficiencyScore = spec.qaPassed ? (1 / Math.max(spec.qaAttempts, 1)) : 0;

    return {
      effectiveHourlyRate,
      estimatedManualCost,
      costSavings,
      roiPercentage,
      costPerLine,
      efficiencyScore
    };
  }
}

// Singleton instance
let roiService: ROIService | null = null;

export function getROIService(): ROIService {
  if (!roiService) {
    roiService = new ROIService();
  }
  return roiService;
}
