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
