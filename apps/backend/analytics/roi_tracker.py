# apps/backend/analytics/roi_tracker.py
"""
ROI Tracker - captures git diff stats and QA results for ROI calculation.
"""

import logging
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Optional, Union
from datetime import datetime

from .storage import get_analytics_storage

logger = logging.getLogger(__name__)

# Complexity factors based on language
COMPLEXITY_FACTORS = {
    'python': 1.0,
    'typescript': 0.9,
    'javascript': 1.1,
    'rust': 1.3,
    'go': 0.95,
    'java': 1.1,
    'kotlin': 1.0,
    'swift': 1.0,
    'c++': 1.4,
    'c#': 1.05,
}

# Additional complexity factors based on framework
FRAMEWORK_FACTORS = {
    'react': 1.0,
    'next.js': 1.1,
    'vue': 1.0,
    'angular': 1.15,
    'django': 1.0,
    'fastapi': 0.9,
    'flask': 0.95,
    'express': 0.95,
    'spring': 1.2,
    'electron': 1.1,
}


class ROITracker:
    """
    Tracks ROI-related data during spec execution:
    - Git diff stats (lines added/removed, files changed)
    - QA attempts and results
    - Execution time
    """

    def __init__(self, spec_id: str, project_dir: Path, storage=None):
        self.spec_id = spec_id
        self.project_dir = project_dir
        self.storage = storage if storage else get_analytics_storage()

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

    def calculate_complexity_factor(self, project_path: str) -> float:
        """
        Calculate complexity factor based on project analysis.

        Args:
            project_path: Path to the project directory

        Returns:
            float: Complexity factor (1.0 = baseline, >1.0 = more complex, <1.0 = simpler)
        """
        try:
            from project.analyzer import ProjectAnalyzer

            analyzer = ProjectAnalyzer(project_path)
            profile = analyzer.analyze()

            # Language factor
            lang = (profile.primary_language or 'unknown').lower()
            lang_factor = COMPLEXITY_FACTORS.get(lang, 1.0)

            # Framework factor
            framework = (profile.framework or 'unknown').lower()
            framework_factor = FRAMEWORK_FACTORS.get(framework, 1.0)

            # Size factor
            if getattr(profile, 'is_monorepo', False):
                size_factor = 1.2
            elif getattr(profile, 'file_count', 0) > 1000:
                size_factor = 1.15
            elif getattr(profile, 'file_count', 0) > 500:
                size_factor = 1.1
            else:
                size_factor = 1.0

            return round(lang_factor * framework_factor * size_factor, 2)
        except Exception as e:
            logger.warning(f"Could not calculate complexity factor: {e}")
            return 1.0

    def get_smart_estimate(
        self,
        project_path: str,
        lines_estimate: int,
        minutes_per_line: float = 2.5
    ) -> Dict[str, Union[float, str]]:
        """
        Get a smart time estimate based on complexity.

        Args:
            project_path: Path to the project
            lines_estimate: Estimated lines of code
            minutes_per_line: Base minutes per line (default: 2.5 for mid-level)

        Returns:
            dict with hours, confidence, basis, adjusted_minutes_per_line
        """
        if lines_estimate <= 0:
            return {
                'hours': 0.0,
                'confidence': 'low',
                'basis': 'No lines to estimate',
                'adjusted_minutes_per_line': minutes_per_line,
                'complexity_factor': 1.0
            }

        complexity_factor = self.calculate_complexity_factor(project_path)
        adjusted_minutes = minutes_per_line * complexity_factor
        hours = (lines_estimate * adjusted_minutes) / 60

        # Determine confidence based on data availability
        confidence = 'medium'  # Would be 'high' with historical data

        return {
            'hours': round(hours, 1),
            'confidence': confidence,
            'basis': f"Based on {adjusted_minutes:.1f} min/line with complexity factor {complexity_factor}",
            'adjusted_minutes_per_line': round(adjusted_minutes, 2),
            'complexity_factor': complexity_factor
        }

    async def finalize(self, total_cost: float = 0, total_tokens: int = 0):
        """Finalize ROI tracking and save to database."""
        end_time = datetime.utcnow()
        execution_time = int((end_time - self.start_time).total_seconds())

        # Get git diff stats
        diff_stats = self._get_git_diff_stats()

        # Get existing data to preserve user inputs
        existing = await self.storage.get_spec_roi(self.spec_id)

        # Merge with existing data
        # Use project_dir.name as project_id, or preserve existing if already set
        roi_data = {
            'project_id': (existing.get('project_id') if existing else None) or self.project_dir.name,
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
async def create_roi_tracker(spec_id: str, project_dir: Path, storage=None) -> ROITracker:
    """Create and return ROI tracker instance."""
    return ROITracker(spec_id, project_dir, storage)
