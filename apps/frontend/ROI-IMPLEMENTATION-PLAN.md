# ROI System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a comprehensive ROI tracking system that measures cost savings, time saved, and efficiency per spec/demand.

**Architecture:** SQLite database stores ROI data (settings, project overrides, spec metrics). Main process handles DB operations via IPC. Renderer uses Zustand store for state, with React components for UI. ROI Calculator computes derived metrics from raw data.

**Tech Stack:** TypeScript, Electron IPC, SQLite (better-sqlite3), Zustand, React, Recharts, Tailwind CSS, Lucide icons

---

## Phase 0: Backend Integration (Python)

### Task 0.1: Add ROI Tables to Backend Storage

**Files:**
- Modify: `apps/backend/analytics/storage.py`

**Step 1: Add ROI tables to SCHEMA_SQL**

Add after the existing schema:

```sql
-- ROI Settings (global)
CREATE TABLE IF NOT EXISTS roi_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    developer_hourly_rate REAL DEFAULT 75.0,
    primary_currency TEXT DEFAULT 'USD',
    secondary_currency TEXT DEFAULT 'BRL',
    exchange_rate REAL DEFAULT 6.20,
    exchange_rate_updated_at TIMESTAMP,
    auto_estimate_hours INTEGER DEFAULT 1,
    minutes_per_line REAL DEFAULT 2.5,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ROI per spec (with git diff and QA tracking)
CREATE TABLE IF NOT EXISTS spec_roi (
    spec_id TEXT PRIMARY KEY,
    project_id TEXT,
    estimated_business_value REAL DEFAULT 0,
    estimated_hours_manual REAL,
    developer_rate_override REAL,
    actual_cost REAL DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    execution_time_seconds INTEGER DEFAULT 0,
    qa_attempts INTEGER DEFAULT 0,
    qa_passed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_spec_roi_project ON spec_roi(project_id);
```

**Step 2: Add ROI methods to AnalyticsStorage class**

```python
async def get_roi_settings(self) -> Dict:
    """Get global ROI settings."""
    loop = asyncio.get_event_loop()

    def _get():
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM roi_settings WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {
            'developer_hourly_rate': 75.0,
            'primary_currency': 'USD',
            'secondary_currency': 'BRL',
            'exchange_rate': 6.20,
            'auto_estimate_hours': True,
            'minutes_per_line': 2.5
        }

    return await loop.run_in_executor(None, _get)

async def save_roi_settings(self, settings: Dict):
    """Save global ROI settings."""
    loop = asyncio.get_event_loop()

    def _save():
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO roi_settings (id, developer_hourly_rate, primary_currency,
                secondary_currency, exchange_rate, auto_estimate_hours, minutes_per_line)
            VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                developer_hourly_rate = excluded.developer_hourly_rate,
                primary_currency = excluded.primary_currency,
                secondary_currency = excluded.secondary_currency,
                exchange_rate = excluded.exchange_rate,
                auto_estimate_hours = excluded.auto_estimate_hours,
                minutes_per_line = excluded.minutes_per_line,
                updated_at = CURRENT_TIMESTAMP
        """, (
            settings.get('developer_hourly_rate', 75.0),
            settings.get('primary_currency', 'USD'),
            settings.get('secondary_currency', 'BRL'),
            settings.get('exchange_rate', 6.20),
            1 if settings.get('auto_estimate_hours', True) else 0,
            settings.get('minutes_per_line', 2.5)
        ))
        conn.commit()
        conn.close()

    await loop.run_in_executor(None, _save)

async def save_spec_roi(self, spec_id: str, data: Dict):
    """Save or update spec ROI data."""
    loop = asyncio.get_event_loop()

    def _save():
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO spec_roi (
                spec_id, project_id, estimated_business_value, estimated_hours_manual,
                developer_rate_override, actual_cost, total_tokens, lines_added,
                lines_removed, files_changed, execution_time_seconds, qa_attempts,
                qa_passed, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(spec_id) DO UPDATE SET
                project_id = excluded.project_id,
                estimated_business_value = excluded.estimated_business_value,
                estimated_hours_manual = excluded.estimated_hours_manual,
                developer_rate_override = excluded.developer_rate_override,
                actual_cost = excluded.actual_cost,
                total_tokens = excluded.total_tokens,
                lines_added = excluded.lines_added,
                lines_removed = excluded.lines_removed,
                files_changed = excluded.files_changed,
                execution_time_seconds = excluded.execution_time_seconds,
                qa_attempts = excluded.qa_attempts,
                qa_passed = excluded.qa_passed,
                completed_at = excluded.completed_at
        """, (
            spec_id,
            data.get('project_id', ''),
            data.get('estimated_business_value', 0),
            data.get('estimated_hours_manual'),
            data.get('developer_rate_override'),
            data.get('actual_cost', 0),
            data.get('total_tokens', 0),
            data.get('lines_added', 0),
            data.get('lines_removed', 0),
            data.get('files_changed', 0),
            data.get('execution_time_seconds', 0),
            data.get('qa_attempts', 0),
            1 if data.get('qa_passed') else 0,
            data.get('completed_at')
        ))
        conn.commit()
        conn.close()

    await loop.run_in_executor(None, _save)

async def get_spec_roi(self, spec_id: str) -> Optional[Dict]:
    """Get ROI data for a spec."""
    loop = asyncio.get_event_loop()

    def _get():
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM spec_roi WHERE spec_id = ?", (spec_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    return await loop.run_in_executor(None, _get)

async def get_all_spec_roi(self, project_id: Optional[str] = None) -> List[Dict]:
    """Get all spec ROI data, optionally filtered by project."""
    loop = asyncio.get_event_loop()

    def _get():
        conn = self._get_connection()
        cursor = conn.cursor()
        if project_id:
            cursor.execute(
                "SELECT * FROM spec_roi WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,)
            )
        else:
            cursor.execute("SELECT * FROM spec_roi ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    return await loop.run_in_executor(None, _get)
```

**Step 3: Commit**

```bash
git add apps/backend/analytics/storage.py
git commit -m "feat(roi): Add ROI tables and methods to backend storage"
```

---

### Task 0.2: Create ROI Tracker for Git Diff and QA

**Files:**
- Create: `apps/backend/analytics/roi_tracker.py`

**Step 1: Create ROI tracker**

```python
# apps/backend/analytics/roi_tracker.py
"""
ROI Tracker - captures git diff stats and QA results for ROI calculation.
"""

import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from .storage import get_analytics_storage


class ROITracker:
    """
    Tracks ROI-related data during spec execution:
    - Git diff stats (lines added/removed, files changed)
    - QA attempts and results
    - Execution time
    """

    def __init__(self, spec_id: str, project_dir: Path):
        self.spec_id = spec_id
        self.project_dir = project_dir
        self.storage = get_analytics_storage()

        self.start_time = datetime.utcnow()
        self.qa_attempts = 0
        self.qa_passed = False

        # Capture initial commit for diff calculation
        self.initial_commit = self._get_current_commit()

    def _get_current_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def _get_git_diff_stats(self) -> Dict:
        """Calculate git diff stats since initial commit."""
        if not self.initial_commit:
            return {'lines_added': 0, 'lines_removed': 0, 'files_changed': 0}

        try:
            # Get diff stats
            result = subprocess.run(
                ['git', 'diff', '--numstat', self.initial_commit, 'HEAD'],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return {'lines_added': 0, 'lines_removed': 0, 'files_changed': 0}

            lines_added = 0
            lines_removed = 0
            files_changed = 0

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 2:
                    try:
                        added = int(parts[0]) if parts[0] != '-' else 0
                        removed = int(parts[1]) if parts[1] != '-' else 0
                        lines_added += added
                        lines_removed += removed
                        files_changed += 1
                    except ValueError:
                        continue

            return {
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                'files_changed': files_changed
            }
        except Exception:
            return {'lines_added': 0, 'lines_removed': 0, 'files_changed': 0}

    def record_qa_attempt(self, passed: bool):
        """Record a QA attempt."""
        self.qa_attempts += 1
        self.qa_passed = passed

    async def finalize(self, total_cost: float = 0, total_tokens: int = 0):
        """Finalize ROI tracking and save to database."""
        end_time = datetime.utcnow()
        execution_time = int((end_time - self.start_time).total_seconds())

        # Get git diff stats
        diff_stats = self._get_git_diff_stats()

        # Get existing data to preserve user inputs
        existing = await self.storage.get_spec_roi(self.spec_id)

        # Merge with existing data
        roi_data = {
            'project_id': existing.get('project_id', '') if existing else '',
            'estimated_business_value': existing.get('estimated_business_value', 0) if existing else 0,
            'estimated_hours_manual': existing.get('estimated_hours_manual') if existing else None,
            'developer_rate_override': existing.get('developer_rate_override') if existing else None,
            'actual_cost': total_cost,
            'total_tokens': total_tokens,
            'lines_added': diff_stats['lines_added'],
            'lines_removed': diff_stats['lines_removed'],
            'files_changed': diff_stats['files_changed'],
            'execution_time_seconds': execution_time,
            'qa_attempts': self.qa_attempts,
            'qa_passed': self.qa_passed,
            'completed_at': end_time.isoformat() if self.qa_passed else None
        }

        await self.storage.save_spec_roi(self.spec_id, roi_data)


# Helper function for integration
async def create_roi_tracker(spec_id: str, project_dir: Path) -> ROITracker:
    """Create and return ROI tracker instance."""
    return ROITracker(spec_id, project_dir)
```

**Step 2: Commit**

```bash
git add apps/backend/analytics/roi_tracker.py
git commit -m "feat(roi): Add ROI tracker for git diff and QA tracking"
```

---

### Task 0.3: Integrate ROI Tracker with Agent Session

**Files:**
- Modify: `apps/backend/agents/session.py`

**Step 1: Import and integrate ROITracker**

Add at the top:
```python
from analytics.roi_tracker import create_roi_tracker, ROITracker
```

**Step 2: Create ROI tracker at session start**

In `run_agent_session()`, after creating UsageTracker:
```python
# ROI tracking
roi_tracker: Optional[ROITracker] = None
if ANALYTICS_AVAILABLE and is_tracking_enabled() and spec_id:
    roi_tracker = await create_roi_tracker(spec_id, project_dir)
```

**Step 3: Finalize ROI tracker at session end**

In the finally block:
```python
if roi_tracker:
    total_cost = usage_tracker.total_cost_usd if usage_tracker else 0
    total_tokens = (usage_tracker.total_input_tokens + usage_tracker.total_output_tokens) if usage_tracker else 0
    await roi_tracker.finalize(total_cost, total_tokens)
```

**Step 4: Commit**

```bash
git add apps/backend/agents/session.py
git commit -m "feat(roi): Integrate ROI tracker with agent session"
```

---

### Task 0.4: Integrate ROI Tracker with QA Agent

**Files:**
- Modify: `apps/backend/agents/qa_reviewer.py`
- Modify: `apps/backend/agents/qa_fixer.py`

**Step 1: Pass ROI tracker to QA agents**

Update QA agents to call `roi_tracker.record_qa_attempt(passed)` when QA completes.

**Step 2: Commit**

```bash
git add apps/backend/agents/qa_reviewer.py apps/backend/agents/qa_fixer.py
git commit -m "feat(roi): Track QA attempts in ROI tracker"
```

---

### Task 0.5: Export ROI to analytics.db

**Files:**
- Modify: `apps/backend/analytics/__init__.py`

**Step 1: Export ROI functions**

```python
from .roi_tracker import ROITracker, create_roi_tracker
```

**Step 2: Commit**

```bash
git add apps/backend/analytics/__init__.py
git commit -m "feat(roi): Export ROI tracker from analytics module"
```

---

## Phase 1: Foundation (Types & Database)

### Task 1: Create TypeScript Types

**Files:**
- Create: `apps/frontend/src/shared/types/roi.ts`
- Modify: `apps/frontend/src/shared/types/index.ts`

**Step 1: Create roi.ts types file**

```typescript
// apps/frontend/src/shared/types/roi.ts

/**
 * ROI System Types
 */

export type Currency = 'USD' | 'BRL' | 'EUR';

export interface ROISettings {
  developerHourlyRate: number;
  primaryCurrency: Currency;
  secondaryCurrency: Currency | null;
  exchangeRate: number;
  exchangeRateUpdatedAt: string | null;
  autoEstimateHours: boolean;
  minutesPerLine: number;
}

export interface ProjectROISettings {
  projectId: string;
  developerHourlyRate: number | null;
  updatedAt: string;
}

export interface SpecROI {
  specId: string;
  projectId: string;

  // User inputs (with defaults)
  estimatedBusinessValue: number;
  estimatedHoursManual: number | null;
  developerRateOverride: number | null;

  // Auto-tracked
  actualCost: number;
  totalTokens: number;
  linesAdded: number;
  linesRemoved: number;
  filesChanged: number;
  executionTimeSeconds: number;
  qaAttempts: number;
  qaPassed: boolean;

  // Timestamps
  createdAt: string;
  completedAt: string | null;
}

export interface ROIMetrics {
  // Per-spec calculated
  effectiveHourlyRate: number;
  estimatedManualCost: number;
  costSavings: number;
  roiPercentage: number;
  costPerLine: number;
  efficiencyScore: number;
}

export interface ROIAggregateMetrics {
  totalROI: number;
  totalSavings: number;
  totalHoursSaved: number;
  totalCost: number;
  successRate: number;
  specsCount: number;
}

export interface SpecROIWithMetrics extends SpecROI {
  metrics: ROIMetrics;
}

// Default values
export const DEFAULT_ROI_SETTINGS: ROISettings = {
  developerHourlyRate: 75,
  primaryCurrency: 'USD',
  secondaryCurrency: 'BRL',
  exchangeRate: 6.20,
  exchangeRateUpdatedAt: null,
  autoEstimateHours: true,
  minutesPerLine: 2.5
};
```

**Step 2: Export from index.ts**

Add to `apps/frontend/src/shared/types/index.ts`:

```typescript
export * from './roi';
```

**Step 3: Commit**

```bash
git add apps/frontend/src/shared/types/roi.ts apps/frontend/src/shared/types/index.ts
git commit -m "feat(roi): Add TypeScript types for ROI system"
```

---

### Task 2: Add ROI IPC Channels

**Files:**
- Modify: `apps/frontend/src/shared/constants/ipc.ts`

**Step 1: Add ROI IPC channel constants**

Add after `ANALYTICS_DATA_UPDATE` in `apps/frontend/src/shared/constants/ipc.ts`:

```typescript
  // ROI operations
  ROI_GET_SETTINGS: 'roi:getSettings',
  ROI_SAVE_SETTINGS: 'roi:saveSettings',
  ROI_GET_PROJECT_SETTINGS: 'roi:getProjectSettings',
  ROI_SAVE_PROJECT_SETTINGS: 'roi:saveProjectSettings',
  ROI_GET_SPEC: 'roi:getSpec',
  ROI_SAVE_SPEC: 'roi:saveSpec',
  ROI_GET_ALL_SPECS: 'roi:getAllSpecs',
  ROI_GET_AGGREGATE: 'roi:getAggregate',
  ROI_DELETE_SPEC: 'roi:deleteSpec',
```

**Step 2: Commit**

```bash
git add apps/frontend/src/shared/constants/ipc.ts
git commit -m "feat(roi): Add IPC channel constants for ROI operations"
```

---

### Task 3: Create ROI Service (Main Process)

**Files:**
- Create: `apps/frontend/src/main/services/roi-service.ts`

**Step 1: Create ROI service with SQLite integration**

```typescript
// apps/frontend/src/main/services/roi-service.ts

import Database from 'better-sqlite3';
import path from 'path';
import { app } from 'electron';
import type {
  ROISettings,
  ProjectROISettings,
  SpecROI,
  ROIMetrics,
  ROIAggregateMetrics,
  SpecROIWithMetrics,
  DEFAULT_ROI_SETTINGS
} from '../../shared/types/roi';

export class ROIService {
  private db: Database.Database | null = null;
  private dbPath: string;

  constructor() {
    const userDataPath = app.getPath('userData');
    this.dbPath = path.join(userDataPath, 'roi.db');
  }

  private ensureDb(): Database.Database {
    if (!this.db) {
      this.db = new Database(this.dbPath);
      this.initializeSchema();
    }
    return this.db;
  }

  private initializeSchema(): void {
    const db = this.db!;

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

      CREATE TABLE IF NOT EXISTS spec_roi (
        spec_id TEXT PRIMARY KEY,
        project_id TEXT,
        estimated_business_value REAL DEFAULT 0,
        estimated_hours_manual REAL,
        developer_rate_override REAL,
        actual_cost REAL DEFAULT 0,
        total_tokens INTEGER DEFAULT 0,
        lines_added INTEGER DEFAULT 0,
        lines_removed INTEGER DEFAULT 0,
        files_changed INTEGER DEFAULT 0,
        execution_time_seconds INTEGER DEFAULT 0,
        qa_attempts INTEGER DEFAULT 0,
        qa_passed INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT
      );

      CREATE INDEX IF NOT EXISTS idx_spec_roi_project ON spec_roi(project_id);
      CREATE INDEX IF NOT EXISTS idx_spec_roi_completed ON spec_roi(completed_at);

      -- Insert default settings if not exists
      INSERT OR IGNORE INTO roi_settings (id) VALUES (1);
    `);
  }

  // Settings operations
  getSettings(): ROISettings {
    const db = this.ensureDb();
    const row = db.prepare('SELECT * FROM roi_settings WHERE id = 1').get() as any;

    if (!row) {
      return { ...DEFAULT_ROI_SETTINGS };
    }

    return {
      developerHourlyRate: row.developer_hourly_rate,
      primaryCurrency: row.primary_currency,
      secondaryCurrency: row.secondary_currency,
      exchangeRate: row.exchange_rate,
      exchangeRateUpdatedAt: row.exchange_rate_updated_at,
      autoEstimateHours: Boolean(row.auto_estimate_hours),
      minutesPerLine: row.minutes_per_line
    };
  }

  saveSettings(settings: Partial<ROISettings>): void {
    const db = this.ensureDb();
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

  // Project settings operations
  getProjectSettings(projectId: string): ProjectROISettings | null {
    const db = this.ensureDb();
    const row = db.prepare('SELECT * FROM project_roi_settings WHERE project_id = ?').get(projectId) as any;

    if (!row) return null;

    return {
      projectId: row.project_id,
      developerHourlyRate: row.developer_hourly_rate,
      updatedAt: row.updated_at
    };
  }

  saveProjectSettings(projectId: string, hourlyRate: number | null): void {
    const db = this.ensureDb();

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

  // Spec ROI operations
  getSpec(specId: string): SpecROI | null {
    const db = this.ensureDb();
    const row = db.prepare('SELECT * FROM spec_roi WHERE spec_id = ?').get(specId) as any;

    if (!row) return null;

    return this.rowToSpecROI(row);
  }

  saveSpec(spec: Partial<SpecROI> & { specId: string }): void {
    const db = this.ensureDb();
    const existing = this.getSpec(spec.specId);

    if (existing) {
      // Update
      const merged = { ...existing, ...spec };
      db.prepare(`
        UPDATE spec_roi SET
          project_id = ?,
          estimated_business_value = ?,
          estimated_hours_manual = ?,
          developer_rate_override = ?,
          actual_cost = ?,
          total_tokens = ?,
          lines_added = ?,
          lines_removed = ?,
          files_changed = ?,
          execution_time_seconds = ?,
          qa_attempts = ?,
          qa_passed = ?,
          completed_at = ?
        WHERE spec_id = ?
      `).run(
        merged.projectId,
        merged.estimatedBusinessValue,
        merged.estimatedHoursManual,
        merged.developerRateOverride,
        merged.actualCost,
        merged.totalTokens,
        merged.linesAdded,
        merged.linesRemoved,
        merged.filesChanged,
        merged.executionTimeSeconds,
        merged.qaAttempts,
        merged.qaPassed ? 1 : 0,
        merged.completedAt,
        spec.specId
      );
    } else {
      // Insert
      db.prepare(`
        INSERT INTO spec_roi (
          spec_id, project_id, estimated_business_value, estimated_hours_manual,
          developer_rate_override, actual_cost, total_tokens, lines_added,
          lines_removed, files_changed, execution_time_seconds, qa_attempts,
          qa_passed, created_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
      `).run(
        spec.specId,
        spec.projectId || '',
        spec.estimatedBusinessValue || 0,
        spec.estimatedHoursManual || null,
        spec.developerRateOverride || null,
        spec.actualCost || 0,
        spec.totalTokens || 0,
        spec.linesAdded || 0,
        spec.linesRemoved || 0,
        spec.filesChanged || 0,
        spec.executionTimeSeconds || 0,
        spec.qaAttempts || 0,
        spec.qaPassed ? 1 : 0,
        spec.completedAt || null
      );
    }
  }

  getAllSpecs(projectId?: string): SpecROIWithMetrics[] {
    const db = this.ensureDb();
    const settings = this.getSettings();

    let rows: any[];
    if (projectId) {
      rows = db.prepare('SELECT * FROM spec_roi WHERE project_id = ? ORDER BY created_at DESC').all(projectId) as any[];
    } else {
      rows = db.prepare('SELECT * FROM spec_roi ORDER BY created_at DESC').all() as any[];
    }

    return rows.map(row => {
      const spec = this.rowToSpecROI(row);
      const projectSettings = this.getProjectSettings(spec.projectId);
      const metrics = this.calculateMetrics(spec, settings, projectSettings);
      return { ...spec, metrics };
    });
  }

  getAggregate(projectId?: string): ROIAggregateMetrics {
    const specs = this.getAllSpecs(projectId);

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

  deleteSpec(specId: string): void {
    const db = this.ensureDb();
    db.prepare('DELETE FROM spec_roi WHERE spec_id = ?').run(specId);
  }

  // Helper methods
  private rowToSpecROI(row: any): SpecROI {
    return {
      specId: row.spec_id,
      projectId: row.project_id,
      estimatedBusinessValue: row.estimated_business_value,
      estimatedHoursManual: row.estimated_hours_manual,
      developerRateOverride: row.developer_rate_override,
      actualCost: row.actual_cost,
      totalTokens: row.total_tokens,
      linesAdded: row.lines_added,
      linesRemoved: row.lines_removed,
      filesChanged: row.files_changed,
      executionTimeSeconds: row.execution_time_seconds,
      qaAttempts: row.qa_attempts,
      qaPassed: Boolean(row.qa_passed),
      createdAt: row.created_at,
      completedAt: row.completed_at
    };
  }

  private calculateMetrics(
    spec: SpecROI,
    settings: ROISettings,
    projectSettings: ProjectROISettings | null
  ): ROIMetrics {
    // Cascade: spec override > project override > global
    const effectiveHourlyRate =
      spec.developerRateOverride ??
      projectSettings?.developerHourlyRate ??
      settings.developerHourlyRate;

    // Calculate estimated hours if not provided
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
    if (this.db) {
      this.db.close();
      this.db = null;
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
```

**Step 2: Commit**

```bash
git add apps/frontend/src/main/services/roi-service.ts
git commit -m "feat(roi): Add ROI service with SQLite database operations"
```

---

### Task 4: Create ROI IPC Handlers

**Files:**
- Create: `apps/frontend/src/main/ipc-handlers/roi-handlers.ts`
- Modify: `apps/frontend/src/main/ipc-handlers/index.ts`

**Step 1: Create ROI IPC handlers**

```typescript
// apps/frontend/src/main/ipc-handlers/roi-handlers.ts

import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import { getROIService } from '../services/roi-service';
import type { ROISettings, SpecROI } from '../../shared/types/roi';

export function setupROIHandlers(): void {
  const roiService = getROIService();

  // Get global settings
  ipcMain.handle(IPC_CHANNELS.ROI_GET_SETTINGS, () => {
    return roiService.getSettings();
  });

  // Save global settings
  ipcMain.handle(IPC_CHANNELS.ROI_SAVE_SETTINGS, (_event, settings: Partial<ROISettings>) => {
    roiService.saveSettings(settings);
    return { success: true };
  });

  // Get project settings
  ipcMain.handle(IPC_CHANNELS.ROI_GET_PROJECT_SETTINGS, (_event, projectId: string) => {
    return roiService.getProjectSettings(projectId);
  });

  // Save project settings
  ipcMain.handle(IPC_CHANNELS.ROI_SAVE_PROJECT_SETTINGS, (_event, projectId: string, hourlyRate: number | null) => {
    roiService.saveProjectSettings(projectId, hourlyRate);
    return { success: true };
  });

  // Get spec ROI
  ipcMain.handle(IPC_CHANNELS.ROI_GET_SPEC, (_event, specId: string) => {
    return roiService.getSpec(specId);
  });

  // Save spec ROI
  ipcMain.handle(IPC_CHANNELS.ROI_SAVE_SPEC, (_event, spec: Partial<SpecROI> & { specId: string }) => {
    roiService.saveSpec(spec);
    return { success: true };
  });

  // Get all specs with metrics
  ipcMain.handle(IPC_CHANNELS.ROI_GET_ALL_SPECS, (_event, projectId?: string) => {
    return roiService.getAllSpecs(projectId);
  });

  // Get aggregate metrics
  ipcMain.handle(IPC_CHANNELS.ROI_GET_AGGREGATE, (_event, projectId?: string) => {
    return roiService.getAggregate(projectId);
  });

  // Delete spec ROI
  ipcMain.handle(IPC_CHANNELS.ROI_DELETE_SPEC, (_event, specId: string) => {
    roiService.deleteSpec(specId);
    return { success: true };
  });

  console.log('[roi-handlers] ROI IPC handlers registered');
}
```

**Step 2: Register handlers in index.ts**

Add import and call in `apps/frontend/src/main/ipc-handlers/index.ts`:

```typescript
import { setupROIHandlers } from './roi-handlers';

// In the setup function, add:
setupROIHandlers();
```

**Step 3: Commit**

```bash
git add apps/frontend/src/main/ipc-handlers/roi-handlers.ts apps/frontend/src/main/ipc-handlers/index.ts
git commit -m "feat(roi): Add IPC handlers for ROI operations"
```

---

## Phase 2: Frontend State & Logic

### Task 5: Create ROI Zustand Store

**Files:**
- Create: `apps/frontend/src/renderer/stores/roi-store.ts`

**Step 1: Create ROI store**

```typescript
// apps/frontend/src/renderer/stores/roi-store.ts

import { create } from 'zustand';
import type {
  ROISettings,
  ProjectROISettings,
  SpecROIWithMetrics,
  ROIAggregateMetrics,
  DEFAULT_ROI_SETTINGS
} from '../../shared/types/roi';

interface ROIState {
  // Data
  settings: ROISettings;
  projectSettings: Record<string, ProjectROISettings>;
  specs: SpecROIWithMetrics[];
  aggregate: ROIAggregateMetrics | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setSettings: (settings: ROISettings) => void;
  setProjectSettings: (projectId: string, settings: ProjectROISettings | null) => void;
  setSpecs: (specs: SpecROIWithMetrics[]) => void;
  setAggregate: (aggregate: ROIAggregateMetrics) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  updateSpec: (specId: string, data: Partial<SpecROIWithMetrics>) => void;
  removeSpec: (specId: string) => void;
}

export const useROIStore = create<ROIState>((set) => ({
  settings: { ...DEFAULT_ROI_SETTINGS },
  projectSettings: {},
  specs: [],
  aggregate: null,
  isLoading: false,
  error: null,

  setSettings: (settings) => set({ settings }),

  setProjectSettings: (projectId, settings) =>
    set((state) => ({
      projectSettings: settings
        ? { ...state.projectSettings, [projectId]: settings }
        : Object.fromEntries(
            Object.entries(state.projectSettings).filter(([id]) => id !== projectId)
          )
    })),

  setSpecs: (specs) => set({ specs }),

  setAggregate: (aggregate) => set({ aggregate }),

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  updateSpec: (specId, data) =>
    set((state) => ({
      specs: state.specs.map((s) =>
        s.specId === specId ? { ...s, ...data } : s
      )
    })),

  removeSpec: (specId) =>
    set((state) => ({
      specs: state.specs.filter((s) => s.specId !== specId)
    }))
}));

// Helper functions for external use
export function getROISettings(): ROISettings {
  return useROIStore.getState().settings;
}

export function getEffectiveHourlyRate(projectId: string, specOverride?: number | null): number {
  const state = useROIStore.getState();
  return (
    specOverride ??
    state.projectSettings[projectId]?.developerHourlyRate ??
    state.settings.developerHourlyRate
  );
}
```

**Step 2: Commit**

```bash
git add apps/frontend/src/renderer/stores/roi-store.ts
git commit -m "feat(roi): Add Zustand store for ROI state management"
```

---

### Task 6: Create ROI Data Hook

**Files:**
- Create: `apps/frontend/src/renderer/hooks/useROIData.ts`

**Step 1: Create useROIData hook**

```typescript
// apps/frontend/src/renderer/hooks/useROIData.ts

import { useEffect, useCallback } from 'react';
import { useROIStore } from '../stores/roi-store';
import type { ROISettings, SpecROI } from '../../shared/types/roi';

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
    setError,
    setProjectSettings
  } = useROIStore();

  // Fetch all data
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [settingsData, specsData, aggregateData] = await Promise.all([
        window.electronAPI.roiGetSettings(),
        window.electronAPI.roiGetAllSpecs(projectId),
        window.electronAPI.roiGetAggregate(projectId)
      ]);

      setSettings(settingsData);
      setSpecs(specsData);
      setAggregate(aggregateData);

      if (projectId) {
        const projectSettings = await window.electronAPI.roiGetProjectSettings(projectId);
        setProjectSettings(projectId, projectSettings);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch ROI data');
    } finally {
      setLoading(false);
    }
  }, [projectId, setSettings, setSpecs, setAggregate, setLoading, setError, setProjectSettings]);

  // Save settings
  const saveSettings = useCallback(async (newSettings: Partial<ROISettings>) => {
    try {
      await window.electronAPI.roiSaveSettings(newSettings);
      setSettings({ ...settings, ...newSettings });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    }
  }, [settings, setSettings, setError]);

  // Save project hourly rate
  const saveProjectHourlyRate = useCallback(async (projId: string, hourlyRate: number | null) => {
    try {
      await window.electronAPI.roiSaveProjectSettings(projId, hourlyRate);
      if (hourlyRate !== null) {
        setProjectSettings(projId, {
          projectId: projId,
          developerHourlyRate: hourlyRate,
          updatedAt: new Date().toISOString()
        });
      } else {
        setProjectSettings(projId, null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save project settings');
    }
  }, [setProjectSettings, setError]);

  // Save spec ROI
  const saveSpecROI = useCallback(async (spec: Partial<SpecROI> & { specId: string }) => {
    try {
      await window.electronAPI.roiSaveSpec(spec);
      await fetchData(); // Refresh to get calculated metrics
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save spec ROI');
    }
  }, [fetchData, setError]);

  // Delete spec ROI
  const deleteSpecROI = useCallback(async (specId: string) => {
    try {
      await window.electronAPI.roiDeleteSpec(specId);
      useROIStore.getState().removeSpec(specId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete spec ROI');
    }
  }, [setError]);

  // Fetch on mount and when projectId changes
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    settings,
    specs,
    aggregate,
    isLoading,
    error,
    refetch: fetchData,
    saveSettings,
    saveProjectHourlyRate,
    saveSpecROI,
    deleteSpecROI
  };
}
```

**Step 2: Commit**

```bash
git add apps/frontend/src/renderer/hooks/useROIData.ts
git commit -m "feat(roi): Add useROIData hook for data fetching"
```

---

### Task 7: Add ROI to Electron API

**Files:**
- Modify: `apps/frontend/src/preload/api/index.ts`

**Step 1: Add ROI methods to electronAPI**

Add to the electronAPI object in preload:

```typescript
// ROI operations
roiGetSettings: () => ipcRenderer.invoke(IPC_CHANNELS.ROI_GET_SETTINGS),
roiSaveSettings: (settings: Partial<ROISettings>) =>
  ipcRenderer.invoke(IPC_CHANNELS.ROI_SAVE_SETTINGS, settings),
roiGetProjectSettings: (projectId: string) =>
  ipcRenderer.invoke(IPC_CHANNELS.ROI_GET_PROJECT_SETTINGS, projectId),
roiSaveProjectSettings: (projectId: string, hourlyRate: number | null) =>
  ipcRenderer.invoke(IPC_CHANNELS.ROI_SAVE_PROJECT_SETTINGS, projectId, hourlyRate),
roiGetSpec: (specId: string) =>
  ipcRenderer.invoke(IPC_CHANNELS.ROI_GET_SPEC, specId),
roiSaveSpec: (spec: Partial<SpecROI> & { specId: string }) =>
  ipcRenderer.invoke(IPC_CHANNELS.ROI_SAVE_SPEC, spec),
roiGetAllSpecs: (projectId?: string) =>
  ipcRenderer.invoke(IPC_CHANNELS.ROI_GET_ALL_SPECS, projectId),
roiGetAggregate: (projectId?: string) =>
  ipcRenderer.invoke(IPC_CHANNELS.ROI_GET_AGGREGATE, projectId),
roiDeleteSpec: (specId: string) =>
  ipcRenderer.invoke(IPC_CHANNELS.ROI_DELETE_SPEC, specId),
```

**Step 2: Commit**

```bash
git add apps/frontend/src/preload/api/index.ts
git commit -m "feat(roi): Add ROI methods to Electron preload API"
```

---

## Phase 3: UI Components

### Task 8: Create ROI Overview Cards

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/ROIOverviewCards.tsx`

**Step 1: Create the component**

```typescript
// apps/frontend/src/renderer/components/analytics/ROIOverviewCards.tsx

import { TrendingUp, DollarSign, Clock, CheckCircle } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { formatCurrency } from './utils/formatters';
import type { ROIAggregateMetrics } from '../../../shared/types/roi';

interface ROICardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  trend?: 'up' | 'down' | 'neutral';
}

function ROICard({ title, value, subtitle, icon: Icon, trend }: ROICardProps) {
  return (
    <Card className="shadow-sm">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className={`text-2xl font-bold ${
          trend === 'up' ? 'text-green-600' :
          trend === 'down' ? 'text-red-600' : ''
        }`}>
          {value}
        </div>
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}

interface ROIOverviewCardsProps {
  data: ROIAggregateMetrics;
}

export function ROIOverviewCards({ data }: ROIOverviewCardsProps) {
  const { totalROI, totalSavings, totalHoursSaved, successRate, specsCount } = data;

  const formatHours = (hours: number): string => {
    if (hours >= 24) {
      const days = hours / 24;
      return `${days.toFixed(1)} days`;
    }
    return `${hours.toFixed(1)}h`;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <ROICard
        title="Total ROI"
        value={`${totalROI >= 0 ? '+' : ''}${totalROI.toFixed(0)}%`}
        subtitle={`Across ${specsCount} specs`}
        icon={TrendingUp}
        trend={totalROI >= 0 ? 'up' : 'down'}
      />
      <ROICard
        title="Total Savings"
        value={formatCurrency(totalSavings, 2)}
        subtitle={totalSavings >= 0 ? 'Cost avoided' : 'Over budget'}
        icon={DollarSign}
        trend={totalSavings >= 0 ? 'up' : 'down'}
      />
      <ROICard
        title="Hours Saved"
        value={formatHours(totalHoursSaved)}
        subtitle="Developer time"
        icon={Clock}
        trend="up"
      />
      <ROICard
        title="Success Rate"
        value={`${successRate.toFixed(0)}%`}
        subtitle="QA pass rate"
        icon={CheckCircle}
        trend={successRate >= 80 ? 'up' : successRate >= 50 ? 'neutral' : 'down'}
      />
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/ROIOverviewCards.tsx
git commit -m "feat(roi): Add ROI overview cards component"
```

---

### Task 9: Create ROI Chart Component

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/ROIChart.tsx`

**Step 1: Create ROI line chart**

```typescript
// apps/frontend/src/renderer/components/analytics/ROIChart.tsx

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { useChartColors } from './utils/useChartColors';
import type { SpecROIWithMetrics } from '../../../shared/types/roi';

interface ROIChartProps {
  data: SpecROIWithMetrics[];
}

export function ROIChart({ data }: ROIChartProps) {
  const chartColors = useChartColors();

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>ROI Over Time</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <p className="text-muted-foreground">No data available</p>
        </CardContent>
      </Card>
    );
  }

  // Sort by date and calculate cumulative ROI
  const sortedData = [...data]
    .filter(d => d.completedAt)
    .sort((a, b) => new Date(a.completedAt!).getTime() - new Date(b.completedAt!).getTime());

  let cumulativeSavings = 0;
  let cumulativeCost = 0;
  const chartData = sortedData.map(spec => {
    cumulativeSavings += spec.metrics.costSavings;
    cumulativeCost += spec.actualCost;
    const cumulativeROI = cumulativeCost > 0 ? (cumulativeSavings / cumulativeCost) * 100 : 0;

    return {
      date: format(parseISO(spec.completedAt!), 'MMM dd'),
      roi: cumulativeROI,
      specId: spec.specId
    };
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>ROI Over Time</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tick={{ fill: chartColors.muted }}
            />
            <YAxis
              tick={{ fill: chartColors.muted }}
              tickFormatter={(v) => `${v.toFixed(0)}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: chartColors.card,
                border: `1px solid ${chartColors.border}`,
                borderRadius: '8px'
              }}
              formatter={(value: number) => [`${value.toFixed(1)}%`, 'ROI']}
            />
            <ReferenceLine y={0} stroke={chartColors.muted} strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="roi"
              stroke={chartColors.chart1}
              strokeWidth={2}
              dot={{ fill: chartColors.chart1 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/ROIChart.tsx
git commit -m "feat(roi): Add ROI over time chart component"
```

---

### Task 10: Create Cost vs Value Chart

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/CostValueChart.tsx`

**Step 1: Create the component**

```typescript
// apps/frontend/src/renderer/components/analytics/CostValueChart.tsx

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { useChartColors } from './utils/useChartColors';
import { formatCurrency } from './utils/formatters';
import type { SpecROIWithMetrics } from '../../../shared/types/roi';

interface CostValueChartProps {
  data: SpecROIWithMetrics[];
}

export function CostValueChart({ data }: CostValueChartProps) {
  const chartColors = useChartColors();

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Cost vs Value by Spec</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <p className="text-muted-foreground">No data available</p>
        </CardContent>
      </Card>
    );
  }

  // Take top 10 specs by value
  const chartData = [...data]
    .sort((a, b) => b.estimatedBusinessValue - a.estimatedBusinessValue)
    .slice(0, 10)
    .map(spec => ({
      name: spec.specId.length > 15 ? spec.specId.slice(0, 15) + '...' : spec.specId,
      value: spec.estimatedBusinessValue,
      cost: spec.actualCost
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost vs Value by Spec</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              type="number"
              tick={{ fill: chartColors.muted }}
              tickFormatter={(v) => formatCurrency(v, 0)}
            />
            <YAxis
              dataKey="name"
              type="category"
              tick={{ fill: chartColors.muted }}
              width={100}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: chartColors.card,
                border: `1px solid ${chartColors.border}`,
                borderRadius: '8px'
              }}
              formatter={(value: number, name: string) => [
                formatCurrency(value, 2),
                name === 'value' ? 'Business Value' : 'Actual Cost'
              ]}
            />
            <Legend />
            <Bar dataKey="value" name="Business Value" fill={chartColors.chart1} />
            <Bar dataKey="cost" name="Actual Cost" fill={chartColors.chart2} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/CostValueChart.tsx
git commit -m "feat(roi): Add cost vs value chart component"
```

---

### Task 11: Create ROI Table Component

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/ROITable.tsx`

**Step 1: Create the table component**

```typescript
// apps/frontend/src/renderer/components/analytics/ROITable.tsx

import { useState } from 'react';
import { ArrowUpDown, ChevronDown, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { formatCurrency } from './utils/formatters';
import type { SpecROIWithMetrics } from '../../../shared/types/roi';

interface ROITableProps {
  data: SpecROIWithMetrics[];
}

type SortField = 'specId' | 'actualCost' | 'roiPercentage' | 'costSavings' | 'completedAt';
type SortOrder = 'asc' | 'desc';

export function ROITable({ data }: ROITableProps) {
  const [search, setSearch] = useState('');
  const [sortField, setSortField] = useState<SortField>('completedAt');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const filteredData = data.filter(spec =>
    spec.specId.toLowerCase().includes(search.toLowerCase())
  );

  const sortedData = [...filteredData].sort((a, b) => {
    let aVal: number | string;
    let bVal: number | string;

    switch (sortField) {
      case 'actualCost':
        aVal = a.actualCost;
        bVal = b.actualCost;
        break;
      case 'roiPercentage':
        aVal = a.metrics.roiPercentage;
        bVal = b.metrics.roiPercentage;
        break;
      case 'costSavings':
        aVal = a.metrics.costSavings;
        bVal = b.metrics.costSavings;
        break;
      case 'completedAt':
        aVal = a.completedAt || '';
        bVal = b.completedAt || '';
        break;
      default:
        aVal = a.specId;
        bVal = b.specId;
    }

    if (typeof aVal === 'string') {
      return sortOrder === 'asc' ? aVal.localeCompare(bVal as string) : (bVal as string).localeCompare(aVal);
    }
    return sortOrder === 'asc' ? aVal - (bVal as number) : (bVal as number) - aVal;
  });

  const SortHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <th className="text-left p-2">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleSort(field)}
        className="h-auto p-1 font-medium"
      >
        {children}
        <ArrowUpDown className="ml-1 h-3 w-3" />
      </Button>
    </th>
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Spec Details</CardTitle>
          <Input
            placeholder="Search specs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64"
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b">
              <tr>
                <th className="w-8"></th>
                <SortHeader field="specId">Spec</SortHeader>
                <SortHeader field="actualCost">Cost</SortHeader>
                <SortHeader field="roiPercentage">ROI</SortHeader>
                <SortHeader field="costSavings">Savings</SortHeader>
                <th className="text-left p-2">QA</th>
              </tr>
            </thead>
            <tbody>
              {sortedData.map((spec) => (
                <>
                  <tr
                    key={spec.specId}
                    className="border-b hover:bg-muted/50 cursor-pointer"
                    onClick={() => setExpandedRow(expandedRow === spec.specId ? null : spec.specId)}
                  >
                    <td className="p-2">
                      {expandedRow === spec.specId ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </td>
                    <td className="p-2 font-medium">{spec.specId}</td>
                    <td className="p-2">{formatCurrency(spec.actualCost, 2)}</td>
                    <td className={`p-2 font-medium ${
                      spec.metrics.roiPercentage >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {spec.metrics.roiPercentage >= 0 ? '+' : ''}{spec.metrics.roiPercentage.toFixed(0)}%
                    </td>
                    <td className={`p-2 ${
                      spec.metrics.costSavings >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatCurrency(spec.metrics.costSavings, 2)}
                    </td>
                    <td className="p-2">
                      {spec.qaPassed ? (
                        <span className="text-green-600">✓ {spec.qaAttempts}</span>
                      ) : (
                        <span className="text-red-600">✗ {spec.qaAttempts}</span>
                      )}
                    </td>
                  </tr>
                  {expandedRow === spec.specId && (
                    <tr key={`${spec.specId}-expanded`} className="bg-muted/30">
                      <td colSpan={6} className="p-4">
                        <div className="grid grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">Business Value:</span>
                            <span className="ml-2 font-medium">{formatCurrency(spec.estimatedBusinessValue, 2)}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Est. Hours:</span>
                            <span className="ml-2 font-medium">{spec.estimatedHoursManual?.toFixed(1) || 'Auto'}h</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Lines Changed:</span>
                            <span className="ml-2 font-medium">{spec.linesAdded + spec.linesRemoved}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Files:</span>
                            <span className="ml-2 font-medium">{spec.filesChanged}</span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
          {sortedData.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              No specs found
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/ROITable.tsx
git commit -m "feat(roi): Add ROI data table with sorting and expansion"
```

---

### Task 12: Create ROI Dashboard

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/ROIDashboard.tsx`

**Step 1: Create the dashboard component**

```typescript
// apps/frontend/src/renderer/components/analytics/ROIDashboard.tsx

import { useROIData } from '../../hooks/useROIData';
import { ROIOverviewCards } from './ROIOverviewCards';
import { ROIChart } from './ROIChart';
import { CostValueChart } from './CostValueChart';
import { ROITable } from './ROITable';

interface ROIDashboardProps {
  projectId?: string;
}

export function ROIDashboard({ projectId }: ROIDashboardProps) {
  const { specs, aggregate, isLoading, error } = useROIData(projectId);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Loading ROI Data...</h2>
          <p className="text-muted-foreground">Calculating metrics</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center text-red-600">
          <h2 className="text-xl font-semibold mb-2">Error Loading ROI Data</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!aggregate || specs.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">No ROI Data</h2>
          <p className="text-muted-foreground">
            Complete some specs to start tracking ROI
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <ROIOverviewCards data={aggregate} />

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ROIChart data={specs} />
        <CostValueChart data={specs} />
      </div>

      {/* Detailed Table */}
      <ROITable data={specs} />
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/ROIDashboard.tsx
git commit -m "feat(roi): Add ROI dashboard component"
```

---

## Phase 4: Integration

### Task 13: Add ROI Tab to Analytics

**Files:**
- Modify: `apps/frontend/src/renderer/components/analytics/Analytics.tsx`

**Step 1: Add tabs and ROI tab**

Update Analytics.tsx to include tabs for Overview and ROI, importing ROIDashboard.

**Step 2: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/Analytics.tsx
git commit -m "feat(roi): Add ROI tab to Analytics dashboard"
```

---

### Task 14: Add ROI Settings Section

**Files:**
- Create: `apps/frontend/src/renderer/components/settings/ROISettings.tsx`
- Modify: `apps/frontend/src/renderer/components/settings/AppSettings.tsx`

**Step 1: Create ROI settings component**

Create a settings section for ROI configuration with fields for hourly rate, currencies, and estimation options.

**Step 2: Add to AppSettings**

Import and add ROISettings component to the settings page.

**Step 3: Commit**

```bash
git add apps/frontend/src/renderer/components/settings/ROISettings.tsx apps/frontend/src/renderer/components/settings/AppSettings.tsx
git commit -m "feat(roi): Add ROI settings section"
```

---

### Task 15: Add ROI to Sidebar Navigation

**Files:**
- Modify: `apps/frontend/src/renderer/components/Sidebar.tsx`
- Modify: `apps/frontend/src/shared/i18n/locales/en/navigation.json`
- Modify: `apps/frontend/src/shared/i18n/locales/fr/navigation.json`

**Step 1: Add ROI view type and nav item**

Add 'roi' to SidebarView type and add nav item with TrendingUp icon.

**Step 2: Add translations**

Add translation keys for ROI menu item.

**Step 3: Commit**

```bash
git add apps/frontend/src/renderer/components/Sidebar.tsx apps/frontend/src/shared/i18n/locales/*/navigation.json
git commit -m "feat(roi): Add ROI item to sidebar navigation"
```

---

## Phase 5: Testing

### Task 16: Add Unit Tests for ROI Calculator

**Files:**
- Create: `apps/frontend/src/renderer/lib/__tests__/roi-calculator.test.ts`

**Step 1: Write tests for ROI calculations**

Test cases for costSavings, roiPercentage, efficiencyScore, etc.

**Step 2: Run tests**

```bash
npm test -- roi-calculator.test.ts
```

**Step 3: Commit**

```bash
git add apps/frontend/src/renderer/lib/__tests__/roi-calculator.test.ts
git commit -m "test(roi): Add unit tests for ROI calculator"
```

---

### Task 17: Add Component Tests

**Files:**
- Create: `apps/frontend/src/renderer/components/analytics/__tests__/ROIOverviewCards.test.tsx`
- Create: `apps/frontend/src/renderer/components/analytics/__tests__/ROITable.test.tsx`

**Step 1: Write component tests**

Test rendering, data display, and interactions.

**Step 2: Run tests**

```bash
npm test -- ROI
```

**Step 3: Commit**

```bash
git add apps/frontend/src/renderer/components/analytics/__tests__/ROI*.test.tsx
git commit -m "test(roi): Add component tests for ROI UI"
```

---

## Summary

**Total Tasks:** 17
**Estimated Time:** 4-6 hours

**Key Files Created:**
- `apps/frontend/src/shared/types/roi.ts` - Types
- `apps/frontend/src/main/services/roi-service.ts` - Database service
- `apps/frontend/src/main/ipc-handlers/roi-handlers.ts` - IPC handlers
- `apps/frontend/src/renderer/stores/roi-store.ts` - Zustand store
- `apps/frontend/src/renderer/hooks/useROIData.ts` - Data hook
- `apps/frontend/src/renderer/components/analytics/ROIDashboard.tsx` - Main dashboard
- `apps/frontend/src/renderer/components/analytics/ROIOverviewCards.tsx` - Summary cards
- `apps/frontend/src/renderer/components/analytics/ROIChart.tsx` - ROI over time
- `apps/frontend/src/renderer/components/analytics/CostValueChart.tsx` - Cost vs value
- `apps/frontend/src/renderer/components/analytics/ROITable.tsx` - Detailed table
- `apps/frontend/src/renderer/components/settings/ROISettings.tsx` - Settings UI
