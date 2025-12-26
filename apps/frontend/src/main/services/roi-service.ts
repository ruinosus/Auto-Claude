// apps/frontend/src/main/services/roi-service.ts
//
// ROI Service - Manages ROI settings and reads spec data from project analytics
//
// Architecture:
// - Global settings (roi_settings, project_roi_settings): stored in {userData}/roi.db
// - Spec ROI data: read from {project}/.auto-claude/analytics.db (written by Python backend)

import Database from 'better-sqlite3';
import path from 'path';
import { app } from 'electron';
import { existsSync } from 'fs';
import type {
  ROISettings,
  ProjectROISettings,
  SpecROI,
  ROIMetrics,
  ROIAggregateMetrics,
  SpecROIWithMetrics
} from '../../shared/types/roi';
import { DEFAULT_ROI_SETTINGS } from '../../shared/types/roi';

export class ROIService {
  private settingsDb: Database.Database | null = null;
  private settingsDbPath: string;

  constructor() {
    const userDataPath = app.getPath('userData');
    this.settingsDbPath = path.join(userDataPath, 'roi.db');
  }

  private ensureSettingsDb(): Database.Database {
    if (!this.settingsDb) {
      this.settingsDb = new Database(this.settingsDbPath);
      this.initializeSettingsSchema();
    }
    return this.settingsDb;
  }

  private initializeSettingsSchema(): void {
    const db = this.settingsDb!;

    db.exec(`
      CREATE TABLE IF NOT EXISTS roi_settings (
        id INTEGER PRIMARY KEY DEFAULT 1,
        developer_hourly_rate REAL DEFAULT 75.0,
        primary_currency TEXT DEFAULT 'USD',
        secondary_currency TEXT DEFAULT 'BRL',
        exchange_rate REAL DEFAULT 6.20,
        exchange_rate_updated_at TEXT,
        auto_estimate_hours INTEGER DEFAULT 1,
        minutes_per_line REAL DEFAULT 2.5,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
      );

      CREATE TABLE IF NOT EXISTS project_roi_settings (
        project_id TEXT PRIMARY KEY,
        developer_hourly_rate REAL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
      );

      INSERT OR IGNORE INTO roi_settings (id) VALUES (1);
    `);
  }

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

  // ============ Settings Operations (from userData/roi.db) ============

  getSettings(): ROISettings {
    const db = this.ensureSettingsDb();
    const row = db.prepare('SELECT * FROM roi_settings WHERE id = 1').get() as Record<string, unknown> | undefined;

    if (!row) {
      return { ...DEFAULT_ROI_SETTINGS };
    }

    return {
      developerHourlyRate: row.developer_hourly_rate as number,
      primaryCurrency: row.primary_currency as ROISettings['primaryCurrency'],
      secondaryCurrency: row.secondary_currency as ROISettings['secondaryCurrency'],
      exchangeRate: row.exchange_rate as number,
      exchangeRateUpdatedAt: row.exchange_rate_updated_at as string | null,
      autoEstimateHours: Boolean(row.auto_estimate_hours),
      minutesPerLine: row.minutes_per_line as number
    };
  }

  saveSettings(settings: Partial<ROISettings>): void {
    const db = this.ensureSettingsDb();
    const current = this.getSettings();
    const merged = { ...current, ...settings };

    db.prepare(`
      UPDATE roi_settings SET
        developer_hourly_rate = ?,
        primary_currency = ?,
        secondary_currency = ?,
        exchange_rate = ?,
        exchange_rate_updated_at = ?,
        auto_estimate_hours = ?,
        minutes_per_line = ?,
        updated_at = CURRENT_TIMESTAMP
      WHERE id = 1
    `).run(
      merged.developerHourlyRate,
      merged.primaryCurrency,
      merged.secondaryCurrency,
      merged.exchangeRate,
      merged.exchangeRateUpdatedAt,
      merged.autoEstimateHours ? 1 : 0,
      merged.minutesPerLine
    );
  }

  // ============ Project Settings (from userData/roi.db) ============

  getProjectSettings(projectId: string): ProjectROISettings | null {
    const db = this.ensureSettingsDb();
    const row = db.prepare('SELECT * FROM project_roi_settings WHERE project_id = ?').get(projectId) as Record<string, unknown> | undefined;
    if (!row) return null;
    return {
      projectId: row.project_id as string,
      developerHourlyRate: row.developer_hourly_rate as number | null,
      updatedAt: row.updated_at as string
    };
  }

  saveProjectSettings(projectId: string, hourlyRate: number | null): void {
    const db = this.ensureSettingsDb();
    if (hourlyRate === null) {
      db.prepare('DELETE FROM project_roi_settings WHERE project_id = ?').run(projectId);
    } else {
      db.prepare(`
        INSERT INTO project_roi_settings (project_id, developer_hourly_rate, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(project_id) DO UPDATE SET
          developer_hourly_rate = excluded.developer_hourly_rate,
          updated_at = CURRENT_TIMESTAMP
      `).run(projectId, hourlyRate);
    }
  }

  // ============ Spec ROI Operations (from project's analytics.db) ============

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

  // Note: saveSpec and deleteSpec are not implemented for project's analytics.db
  // The backend Python code handles writing to that database
  // These methods could be used for manual entries in the settings db if needed

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
    projectSettings: ProjectROISettings | null
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

  close(): void {
    if (this.settingsDb) {
      this.settingsDb.close();
      this.settingsDb = null;
    }
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
