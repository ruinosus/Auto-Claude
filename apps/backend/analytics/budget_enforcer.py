# apps/backend/analytics/budget_enforcer.py
"""Budget enforcement for spec execution.

G04 refers to Gap 04 in the analytics evolution plan: Budget Enforcement.
This gap identified the need for proactive cost controls to prevent
runaway agent execution costs. This module implements:
- Per-spec budget limits with configurable thresholds
- Warning alerts at configurable percentage thresholds
- Optional hard blocking when budgets are exceeded
- Override capability with audit trail
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict
import logging
import sqlite3

from .storage import AnalyticsStorage

logger = logging.getLogger(__name__)


@dataclass
class BudgetCheckResult:
    """Result of a budget check operation."""
    allowed: bool
    remaining: float
    percentage_used: float
    reason: Optional[str] = None


@dataclass
class BudgetSettings:
    """Global budget enforcement settings."""
    enforce_blocking: bool = False
    warn_threshold_percent: float = 80.0
    block_threshold_percent: float = 100.0
    notification_enabled: bool = True
    override_allowed: bool = True


class BudgetEnforcer:
    """Enforces budget limits for spec execution.

    Provides budget checking, blocking, and override functionality
    for controlling spec execution costs.

    Usage:
        enforcer = BudgetEnforcer(storage)

        # Simple check
        if enforcer.can_proceed("001-feature"):
            run_agent()

        # Detailed check with estimated cost
        result = enforcer.check_budget("001-feature", estimated_additional_cost=0.50)
        if result.allowed:
            run_agent()
        elif result.reason:
            print(f"Budget issue: {result.reason}")
    """

    def __init__(self, storage: AnalyticsStorage):
        """Initialize budget enforcer.

        Args:
            storage: AnalyticsStorage instance for database access.
        """
        self.storage = storage

    def _get_connection(self):
        """Get database connection from storage."""
        return self.storage._get_connection()

    def get_settings(self) -> BudgetSettings:
        """Get current budget settings.

        Returns:
            BudgetSettings with current configuration.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM budget_settings WHERE id = 1')
            row = cursor.fetchone()

            if not row:
                return BudgetSettings()

            return BudgetSettings(
                enforce_blocking=bool(row['enforce_blocking']),
                warn_threshold_percent=row['warn_threshold_percent'],
                block_threshold_percent=row['block_threshold_percent'],
                notification_enabled=bool(row['notification_enabled']),
                override_allowed=bool(row['override_allowed'])
            )
        except sqlite3.Error as e:
            logger.error(f"Database error getting budget settings: {e}")
            return BudgetSettings()
        finally:
            conn.close()

    def save_settings(self, settings: BudgetSettings) -> None:
        """Save budget settings.

        Args:
            settings: BudgetSettings to persist.

        Raises:
            ValueError: If threshold percentages are invalid (< 0 or > 100).
        """
        # Validate threshold percentages
        if not (0 <= settings.warn_threshold_percent <= 100):
            raise ValueError(
                f"warn_threshold_percent must be between 0 and 100, got {settings.warn_threshold_percent}"
            )
        if not (0 <= settings.block_threshold_percent <= 100):
            raise ValueError(
                f"block_threshold_percent must be between 0 and 100, got {settings.block_threshold_percent}"
            )

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO budget_settings
                (id, enforce_blocking, warn_threshold_percent, block_threshold_percent,
                 notification_enabled, override_allowed, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?)
            ''', (
                int(settings.enforce_blocking),
                settings.warn_threshold_percent,
                settings.block_threshold_percent,
                int(settings.notification_enabled),
                int(settings.override_allowed),
                datetime.now().isoformat()
            ))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error saving budget settings: {e}")
            raise
        finally:
            conn.close()

    def get_spec_budgets(self) -> Dict[str, float]:
        """Get all spec budgets.

        Returns:
            Dict mapping spec_id to budget amount in USD.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Get budgets from spec_roi.estimated_business_value as budget proxy
            # In a full implementation, this would be a separate budget field
            cursor.execute('''
                SELECT spec_id, estimated_business_value as budget
                FROM spec_roi
                WHERE estimated_business_value > 0
            ''')
            rows = cursor.fetchall()
            return {row['spec_id']: row['budget'] for row in rows}
        except sqlite3.Error as e:
            logger.error(f"Database error getting spec budgets: {e}")
            return {}
        finally:
            conn.close()

    def set_spec_budget(self, spec_id: str, budget: float) -> None:
        """Set budget for a specific spec.

        Args:
            spec_id: The spec identifier.
            budget: Budget amount in USD (must be >= 0).

        Raises:
            ValueError: If budget is negative.
        """
        # Validate budget is non-negative
        if budget < 0:
            raise ValueError(f"Budget must be non-negative, got {budget}")

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Upsert into spec_roi with budget as estimated_business_value
            cursor.execute('''
                INSERT INTO spec_roi (spec_id, estimated_business_value)
                VALUES (?, ?)
                ON CONFLICT(spec_id) DO UPDATE SET
                    estimated_business_value = excluded.estimated_business_value
            ''', (spec_id, budget))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error setting budget for {spec_id}: {e}")
            raise
        finally:
            conn.close()

    def get_budget(self, spec_id: str) -> Optional[float]:
        """Get budget for a spec.

        Args:
            spec_id: The spec identifier.

        Returns:
            Budget amount in USD, or None if not set.
        """
        budgets = self.get_spec_budgets()
        return budgets.get(spec_id)

    def get_current_cost(self, spec_id: str) -> float:
        """Get current total cost for a spec.

        Args:
            spec_id: The spec identifier.

        Returns:
            Total cost in USD for all conversations in this spec.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COALESCE(SUM(total_cost_usd), 0) as total
                FROM conversations WHERE spec_id = ?
            ''', (spec_id,))
            row = cursor.fetchone()
            return row['total'] if row else 0.0
        except sqlite3.Error as e:
            logger.error(f"Database error getting current cost for {spec_id}: {e}")
            return 0.0
        finally:
            conn.close()

    def check_budget(
        self,
        spec_id: str,
        estimated_additional_cost: float = 0.0
    ) -> BudgetCheckResult:
        """Check if execution can proceed within budget.

        Args:
            spec_id: The spec identifier.
            estimated_additional_cost: Estimated cost of the next operation.

        Returns:
            BudgetCheckResult with allowed status, remaining budget,
            percentage used, and optional reason message.
        """
        settings = self.get_settings()
        budget = self.get_budget(spec_id)

        # No budget set = always allowed
        if budget is None or budget <= 0:
            return BudgetCheckResult(
                allowed=True,
                remaining=float('inf'),
                percentage_used=0.0
            )

        current_cost = self.get_current_cost(spec_id)
        projected_cost = current_cost + estimated_additional_cost
        # Use Decimal for precise percentage calculation to avoid floating-point errors
        percentage_used = float(
            (Decimal(str(projected_cost)) / Decimal(str(budget))) * Decimal('100')
        )
        remaining = budget - projected_cost

        # Check if blocked
        if settings.enforce_blocking and percentage_used >= settings.block_threshold_percent:
            return BudgetCheckResult(
                allowed=False,
                remaining=remaining,
                percentage_used=percentage_used,
                reason=f"Budget exceeded: {percentage_used:.1f}% used (limit: {settings.block_threshold_percent}%)"
            )

        # Allowed but maybe warn
        result = BudgetCheckResult(
            allowed=True,
            remaining=remaining,
            percentage_used=percentage_used
        )

        if percentage_used >= settings.warn_threshold_percent:
            result.reason = f"Warning: {percentage_used:.1f}% of budget used"
            logger.warning(f"Budget warning for {spec_id}: {result.reason}")

        return result

    def can_proceed(self, spec_id: str) -> bool:
        """Simple check if execution can proceed.

        Args:
            spec_id: The spec identifier.

        Returns:
            True if execution is allowed, False if blocked.
        """
        return self.check_budget(spec_id).allowed

    def record_override(self, spec_id: str, reason: str, user: str = "system") -> None:
        """Record when a budget block was overridden.

        This creates an anomaly record of type 'budget_override' for audit trail.

        Args:
            spec_id: The spec identifier.
            reason: Reason for the override.
            user: User who performed the override.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO anomalies
                (detected_at, anomaly_type, severity, metric_name, spec_id,
                 expected_value, actual_value, dismissed, dismissed_by)
                VALUES (?, 'budget_override', 'info', 'budget', ?, 0, 0, 1, ?)
            ''', (datetime.now().isoformat(), spec_id, f"{user}: {reason}"))
            conn.commit()
            logger.info(f"Budget override recorded for {spec_id}: {reason}")
        except sqlite3.Error as e:
            logger.error(f"Database error recording override for {spec_id}: {e}")
            raise
        finally:
            conn.close()

    def get_budget_status(self, spec_id: str) -> Dict:
        """Get comprehensive budget status for a spec.

        Args:
            spec_id: The spec identifier.

        Returns:
            Dict with budget, current_cost, remaining, percentage_used,
            is_warning, and is_blocked status.
        """
        settings = self.get_settings()
        budget = self.get_budget(spec_id)
        current_cost = self.get_current_cost(spec_id)

        if budget is None or budget <= 0:
            return {
                "spec_id": spec_id,
                "budget": None,
                "current_cost": current_cost,
                "remaining": None,
                "percentage_used": 0.0,
                "is_warning": False,
                "is_blocked": False,
                "enforce_blocking": settings.enforce_blocking
            }

        # Use Decimal for precise percentage calculation to avoid floating-point errors
        percentage_used = float(
            (Decimal(str(current_cost)) / Decimal(str(budget))) * Decimal('100')
        )
        remaining = budget - current_cost

        return {
            "spec_id": spec_id,
            "budget": budget,
            "current_cost": current_cost,
            "remaining": remaining,
            "percentage_used": percentage_used,
            "is_warning": percentage_used >= settings.warn_threshold_percent,
            "is_blocked": settings.enforce_blocking and percentage_used >= settings.block_threshold_percent,
            "enforce_blocking": settings.enforce_blocking
        }
