# apps/backend/analytics/anomaly_detector.py
"""Anomaly detection for analytics (G05)"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import statistics
import logging

from .storage import AnalyticsStorage

logger = logging.getLogger(__name__)


@dataclass
class Anomaly:
    id: Optional[int]
    detected_at: str  # ISO format
    anomaly_type: str  # 'cost_spike', 'token_spike', 'duration_spike'
    severity: str  # 'info', 'warning', 'critical'
    metric_name: str
    expected_value: float
    actual_value: float
    z_score: float
    spec_id: Optional[str] = None
    dismissed: bool = False


class AnomalyDetector:
    """Detects anomalies in analytics data using z-score method"""

    def __init__(
        self,
        storage: AnalyticsStorage,
        sensitivity: float = 2.0,
        window_days: int = 30
    ):
        self.storage = storage
        self.sensitivity = sensitivity  # Z-score threshold
        self.window_days = window_days

    @property
    def conn(self):
        """Get database connection from storage."""
        return self.storage._get_connection()

    def detect_cost_anomalies(self) -> List[Anomaly]:
        """Detect unusual cost spikes"""
        conn = self.conn
        cursor = conn.cursor()

        cursor.execute('''
            SELECT date(started_at) as date, SUM(total_cost_usd) as daily_cost
            FROM conversations
            WHERE started_at >= datetime('now', ?)
            GROUP BY date(started_at)
            ORDER BY date
        ''', (f'-{self.window_days} days',))

        rows = cursor.fetchall()
        conn.close()

        if len(rows) < 3:
            return []

        costs = [row['daily_cost'] for row in rows]
        dates = [row['date'] for row in rows]

        return self._detect_anomalies(
            values=costs,
            dates=dates,
            metric_name='daily_cost',
            anomaly_type='cost_spike'
        )

    def detect_token_anomalies(self) -> List[Anomaly]:
        """Detect unusual token usage"""
        conn = self.conn
        cursor = conn.cursor()

        cursor.execute('''
            SELECT date(started_at) as date,
                   SUM(total_input_tokens + total_output_tokens) as daily_tokens
            FROM conversations
            WHERE started_at >= datetime('now', ?)
            GROUP BY date(started_at)
            ORDER BY date
        ''', (f'-{self.window_days} days',))

        rows = cursor.fetchall()
        conn.close()

        if len(rows) < 3:
            return []

        tokens = [row['daily_tokens'] for row in rows]
        dates = [row['date'] for row in rows]

        return self._detect_anomalies(
            values=tokens,
            dates=dates,
            metric_name='daily_tokens',
            anomaly_type='token_spike'
        )

    def _detect_anomalies(
        self,
        values: List[float],
        dates: Optional[List[str]],
        metric_name: str,
        anomaly_type: str,
        spec_ids: Optional[List[str]] = None
    ) -> List[Anomaly]:
        """Generic z-score based anomaly detection"""
        if len(values) < 3:
            return []

        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0

        if stdev == 0:
            return []

        anomalies = []
        for i, value in enumerate(values):
            z_score = (value - mean) / stdev

            if abs(z_score) >= self.sensitivity:
                severity = self._get_severity(z_score)
                anomaly = Anomaly(
                    id=None,
                    detected_at=datetime.now().isoformat(),
                    anomaly_type=anomaly_type,
                    severity=severity,
                    metric_name=metric_name,
                    expected_value=mean,
                    actual_value=value,
                    z_score=z_score,
                    spec_id=spec_ids[i] if spec_ids else None
                )
                anomalies.append(anomaly)

        return anomalies

    def _get_severity(self, z_score: float) -> str:
        """Determine severity based on z-score magnitude"""
        abs_z = abs(z_score)
        if abs_z >= 4.0:
            return 'critical'
        elif abs_z >= 3.0:
            return 'warning'
        else:
            return 'info'

    def run_detection(self) -> List[Anomaly]:
        """Run all anomaly detection and persist results"""
        all_anomalies = []

        all_anomalies.extend(self.detect_cost_anomalies())
        all_anomalies.extend(self.detect_token_anomalies())

        # Persist new anomalies
        for anomaly in all_anomalies:
            self._save_anomaly(anomaly)

        logger.info(f"Detected {len(all_anomalies)} anomalies")
        return all_anomalies

    def _save_anomaly(self, anomaly: Anomaly) -> None:
        """Persist anomaly to database"""
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO anomalies
            (detected_at, anomaly_type, severity, metric_name,
             expected_value, actual_value, z_score, spec_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            anomaly.detected_at,
            anomaly.anomaly_type,
            anomaly.severity,
            anomaly.metric_name,
            anomaly.expected_value,
            anomaly.actual_value,
            anomaly.z_score,
            anomaly.spec_id
        ))
        conn.commit()
        conn.close()

    def get_active_anomalies(self) -> List[Anomaly]:
        """Get non-dismissed anomalies"""
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM anomalies
            WHERE dismissed = 0
            ORDER BY detected_at DESC
            LIMIT 50
        ''')

        rows = cursor.fetchall()
        conn.close()

        return [
            Anomaly(
                id=row['id'],
                detected_at=row['detected_at'],
                anomaly_type=row['anomaly_type'],
                severity=row['severity'],
                metric_name=row['metric_name'],
                expected_value=row['expected_value'],
                actual_value=row['actual_value'],
                z_score=row['z_score'],
                spec_id=row['spec_id'],
                dismissed=bool(row['dismissed'])
            )
            for row in rows
        ]

    def dismiss_anomaly(self, anomaly_id: int, dismissed_by: str = "user") -> None:
        """Mark an anomaly as dismissed"""
        conn = self.conn
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE anomalies
            SET dismissed = 1, dismissed_at = ?, dismissed_by = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), dismissed_by, anomaly_id))
        conn.commit()
        conn.close()
