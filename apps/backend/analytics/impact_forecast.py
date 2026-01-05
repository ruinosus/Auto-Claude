"""
Impact Forecasting Module
=========================

Predicts ROI before execution and compares with actual results.
Uses historical data to improve prediction accuracy over time.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ImpactForecast:
    """Predicted impact metrics for a spec before execution."""
    spec_id: str
    predicted_value_usd: float
    predicted_cost_usd: float
    predicted_roi: float
    confidence_interval: Tuple[float, float]  # 95% CI (low, high)
    prediction_factors: Dict[str, float]
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "spec_id": self.spec_id,
            "predicted_value_usd": self.predicted_value_usd,
            "predicted_cost_usd": self.predicted_cost_usd,
            "predicted_roi": self.predicted_roi,
            "confidence_interval": list(self.confidence_interval),
            "prediction_factors": self.prediction_factors,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ImpactForecast":
        """Create from dictionary."""
        return cls(
            spec_id=data["spec_id"],
            predicted_value_usd=data["predicted_value_usd"],
            predicted_cost_usd=data["predicted_cost_usd"],
            predicted_roi=data["predicted_roi"],
            confidence_interval=tuple(data["confidence_interval"]),
            prediction_factors=data["prediction_factors"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class ForecastComparison:
    """Comparison between predicted and actual ROI."""
    spec_id: str
    predicted_roi: float
    actual_roi: float
    predicted_value_usd: float
    actual_value_usd: float
    predicted_cost_usd: float
    actual_cost_usd: float
    accuracy_percentage: float  # How close the prediction was (100 = perfect)
    prediction_error: float  # Signed error (positive = overestimated)
    within_confidence: bool  # Was actual ROI within confidence interval

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "spec_id": self.spec_id,
            "predicted_roi": self.predicted_roi,
            "actual_roi": self.actual_roi,
            "predicted_value_usd": self.predicted_value_usd,
            "actual_value_usd": self.actual_value_usd,
            "predicted_cost_usd": self.predicted_cost_usd,
            "actual_cost_usd": self.actual_cost_usd,
            "accuracy_percentage": self.accuracy_percentage,
            "prediction_error": self.prediction_error,
            "within_confidence": self.within_confidence,
        }


@dataclass
class ModelAccuracyMetrics:
    """Overall model accuracy statistics."""
    total_predictions: int
    mean_accuracy: float  # Average accuracy percentage
    mean_absolute_error: float  # Mean absolute ROI error
    root_mean_square_error: float  # RMSE for ROI
    within_confidence_rate: float  # % of predictions within CI
    bias: float  # Average signed error (positive = tends to overestimate)
    recent_accuracy: float  # Accuracy of last 10 predictions

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "total_predictions": self.total_predictions,
            "mean_accuracy": self.mean_accuracy,
            "mean_absolute_error": self.mean_absolute_error,
            "root_mean_square_error": self.root_mean_square_error,
            "within_confidence_rate": self.within_confidence_rate,
            "bias": self.bias,
            "recent_accuracy": self.recent_accuracy,
        }


class ImpactForecastModel:
    """
    Machine learning model for predicting spec ROI before execution.

    Uses historical data to improve predictions over time.
    Factors considered:
    - Spec complexity (simple, standard, complex)
    - Estimated lines of code
    - Feature type (bugfix, feature, refactor, etc.)
    - Historical similar specs
    """

    # Base value estimates by complexity (USD)
    BASE_VALUES = {
        "simple": 500,
        "standard": 2000,
        "complex": 5000,
    }

    # Base cost estimates by complexity (USD)
    BASE_COSTS = {
        "simple": 0.50,
        "standard": 2.00,
        "complex": 8.00,
    }

    # Feature type multipliers
    FEATURE_TYPE_MULTIPLIERS = {
        "bugfix": 1.2,  # Bugs often have hidden value
        "feature": 1.0,
        "refactor": 0.8,
        "test": 0.6,
        "documentation": 0.4,
        "security": 1.5,
        "performance": 1.3,
    }

    # Confidence interval width factors
    CI_WIDTH_FACTORS = {
        "simple": 0.3,  # +/- 30%
        "standard": 0.4,  # +/- 40%
        "complex": 0.5,  # +/- 50%
    }

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the forecast model.

        Args:
            storage_path: Path to store forecast history. If None, uses in-memory only.
        """
        self.storage_path = storage_path
        self.history: List[Tuple[ImpactForecast, float]] = []  # (forecast, actual_roi)
        self.forecasts: Dict[str, ImpactForecast] = {}  # spec_id -> forecast

        if storage_path:
            self._load_history()

    def _load_history(self) -> None:
        """Load historical predictions from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            history_file = self.storage_path / "forecast_history.json"
            if history_file.exists():
                with open(history_file, "r") as f:
                    data = json.load(f)
                    self.history = [
                        (ImpactForecast.from_dict(item["forecast"]), item["actual_roi"])
                        for item in data.get("history", [])
                    ]
                    self.forecasts = {
                        k: ImpactForecast.from_dict(v)
                        for k, v in data.get("forecasts", {}).items()
                    }
                logger.info(f"Loaded {len(self.history)} historical predictions")
        except Exception as e:
            logger.warning(f"Failed to load forecast history: {e}")

    def _save_history(self) -> None:
        """Save forecast history to storage."""
        if not self.storage_path:
            return

        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            history_file = self.storage_path / "forecast_history.json"

            data = {
                "history": [
                    {"forecast": f.to_dict(), "actual_roi": actual}
                    for f, actual in self.history
                ],
                "forecasts": {k: v.to_dict() for k, v in self.forecasts.items()},
            }

            with open(history_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save forecast history: {e}")

    def _get_similar_factor(self, historical_similar: Optional[List[str]]) -> float:
        """
        Calculate adjustment factor based on similar historical specs.

        Returns a multiplier based on actual ROI of similar specs.
        """
        if not historical_similar:
            return 1.0

        similar_rois = []
        for spec_id in historical_similar:
            for forecast, actual_roi in self.history:
                if forecast.spec_id == spec_id:
                    similar_rois.append(actual_roi)
                    break

        if not similar_rois:
            return 1.0

        # Use average ROI of similar specs to adjust prediction
        avg_similar_roi = sum(similar_rois) / len(similar_rois)

        # Convert to multiplier (100% ROI = 1.0 multiplier)
        # Higher similar ROI -> higher value prediction
        return max(0.5, min(2.0, 1.0 + (avg_similar_roi / 1000)))

    def _estimate_cost(self, spec_complexity: str, estimated_lines: int) -> float:
        """
        Estimate the AI cost for executing a spec.

        Based on complexity and estimated lines of code.
        """
        base_cost = self.BASE_COSTS.get(spec_complexity, 2.0)

        # Lines factor: more lines = more tokens = higher cost
        # Rough estimate: 1 line = ~10 tokens average
        lines_cost_factor = 1.0 + (estimated_lines / 1000) * 0.5

        # Use historical data to adjust if available
        if self.history:
            avg_historical_cost = sum(
                f.predicted_cost_usd for f, _ in self.history[-20:]
            ) / min(20, len(self.history))
            # Blend with base estimate
            base_cost = (base_cost + avg_historical_cost) / 2

        return base_cost * lines_cost_factor

    def _calculate_confidence_interval(
        self,
        predicted_roi: float,
        spec_complexity: str,
    ) -> Tuple[float, float]:
        """
        Calculate 95% confidence interval for ROI prediction.

        Width is based on complexity and historical accuracy.
        """
        base_width = self.CI_WIDTH_FACTORS.get(spec_complexity, 0.4)

        # Adjust based on historical accuracy if available
        if len(self.history) >= 10:
            recent_errors = [
                abs(f.predicted_roi - actual)
                for f, actual in self.history[-10:]
            ]
            avg_error = sum(recent_errors) / len(recent_errors)
            # Convert error to percentage of prediction
            if predicted_roi != 0:
                error_pct = avg_error / abs(predicted_roi)
                # Blend with base width
                base_width = (base_width + error_pct) / 2

        ci_low = predicted_roi * (1 - base_width)
        ci_high = predicted_roi * (1 + base_width)

        return (ci_low, ci_high)

    def predict(
        self,
        spec_id: str,
        spec_complexity: str = "standard",
        estimated_lines: int = 200,
        feature_type: str = "feature",
        historical_similar: Optional[List[str]] = None,
    ) -> ImpactForecast:
        """
        Predict ROI before running a spec.

        Args:
            spec_id: Unique identifier for the spec
            spec_complexity: One of "simple", "standard", "complex"
            estimated_lines: Estimated lines of code to be changed
            feature_type: Type of feature (bugfix, feature, refactor, etc.)
            historical_similar: List of similar spec_ids for adjustment

        Returns:
            ImpactForecast with predicted metrics
        """
        # Normalize complexity
        spec_complexity = spec_complexity.lower()
        if spec_complexity not in self.BASE_VALUES:
            spec_complexity = "standard"

        # Base value estimation
        base_value = self.BASE_VALUES[spec_complexity]

        # Lines factor: more lines = more value, with diminishing returns
        lines_factor = min(estimated_lines / 500, 3.0)
        lines_factor = max(0.2, lines_factor)  # Minimum 0.2

        # Feature type multiplier
        feature_multiplier = self.FEATURE_TYPE_MULTIPLIERS.get(
            feature_type.lower(), 1.0
        )

        # Similar specs factor
        similar_factor = self._get_similar_factor(historical_similar)

        # Calculate predicted value
        predicted_value = base_value * lines_factor * feature_multiplier * similar_factor

        # Estimate cost
        predicted_cost = self._estimate_cost(spec_complexity, estimated_lines)

        # Calculate ROI
        if predicted_cost > 0:
            predicted_roi = ((predicted_value - predicted_cost) / predicted_cost) * 100
        else:
            predicted_roi = 10000.0  # Infinite ROI when cost is zero

        # Calculate confidence interval
        confidence_interval = self._calculate_confidence_interval(
            predicted_roi, spec_complexity
        )

        # Create forecast
        forecast = ImpactForecast(
            spec_id=spec_id,
            predicted_value_usd=round(predicted_value, 2),
            predicted_cost_usd=round(predicted_cost, 2),
            predicted_roi=round(predicted_roi, 2),
            confidence_interval=(
                round(confidence_interval[0], 2),
                round(confidence_interval[1], 2),
            ),
            prediction_factors={
                "complexity": spec_complexity,
                "lines_factor": round(lines_factor, 3),
                "feature_type": feature_type,
                "feature_multiplier": feature_multiplier,
                "similar_factor": round(similar_factor, 3),
                "base_value": base_value,
            },
        )

        # Store forecast
        self.forecasts[spec_id] = forecast
        self._save_history()

        logger.info(
            f"Predicted ROI for {spec_id}: {predicted_roi:.1f}% "
            f"(value: ${predicted_value:.2f}, cost: ${predicted_cost:.2f})"
        )

        return forecast

    def compare_with_actual(
        self,
        spec_id: str,
        actual_roi: float,
        actual_value_usd: float = 0.0,
        actual_cost_usd: float = 0.0,
    ) -> Optional[ForecastComparison]:
        """
        Compare prediction with actual result.

        Args:
            spec_id: Spec identifier
            actual_roi: Actual ROI percentage achieved
            actual_value_usd: Actual value generated
            actual_cost_usd: Actual cost incurred

        Returns:
            ForecastComparison or None if no forecast exists
        """
        forecast = self.forecasts.get(spec_id)
        if not forecast:
            logger.warning(f"No forecast found for spec {spec_id}")
            return None

        # Calculate prediction error (positive = overestimated)
        prediction_error = forecast.predicted_roi - actual_roi

        # Calculate accuracy (100% - normalized error)
        if forecast.predicted_roi != 0:
            relative_error = abs(prediction_error) / abs(forecast.predicted_roi)
        else:
            relative_error = abs(prediction_error) / 100 if actual_roi != 0 else 0

        accuracy = max(0, 100 - (relative_error * 100))

        # Check if actual was within confidence interval
        ci_low, ci_high = forecast.confidence_interval
        within_confidence = ci_low <= actual_roi <= ci_high

        comparison = ForecastComparison(
            spec_id=spec_id,
            predicted_roi=forecast.predicted_roi,
            actual_roi=actual_roi,
            predicted_value_usd=forecast.predicted_value_usd,
            actual_value_usd=actual_value_usd,
            predicted_cost_usd=forecast.predicted_cost_usd,
            actual_cost_usd=actual_cost_usd,
            accuracy_percentage=round(accuracy, 2),
            prediction_error=round(prediction_error, 2),
            within_confidence=within_confidence,
        )

        # Add to history for model improvement
        self.history.append((forecast, actual_roi))
        self._save_history()

        logger.info(
            f"Forecast comparison for {spec_id}: "
            f"predicted={forecast.predicted_roi:.1f}%, actual={actual_roi:.1f}%, "
            f"accuracy={accuracy:.1f}%"
        )

        return comparison

    def get_forecast(self, spec_id: str) -> Optional[ImpactForecast]:
        """Get existing forecast for a spec."""
        return self.forecasts.get(spec_id)

    def get_model_accuracy(self) -> ModelAccuracyMetrics:
        """
        Get overall model accuracy from history.

        Returns:
            ModelAccuracyMetrics with various accuracy statistics
        """
        if not self.history:
            return ModelAccuracyMetrics(
                total_predictions=0,
                mean_accuracy=0.0,
                mean_absolute_error=0.0,
                root_mean_square_error=0.0,
                within_confidence_rate=0.0,
                bias=0.0,
                recent_accuracy=0.0,
            )

        errors = []
        accuracies = []
        within_ci_count = 0

        for forecast, actual_roi in self.history:
            error = forecast.predicted_roi - actual_roi
            errors.append(error)

            # Calculate accuracy
            if forecast.predicted_roi != 0:
                relative_error = abs(error) / abs(forecast.predicted_roi)
            else:
                relative_error = abs(error) / 100 if actual_roi != 0 else 0
            accuracy = max(0, 100 - (relative_error * 100))
            accuracies.append(accuracy)

            # Check confidence interval
            ci_low, ci_high = forecast.confidence_interval
            if ci_low <= actual_roi <= ci_high:
                within_ci_count += 1

        n = len(self.history)

        # Mean Absolute Error
        mae = sum(abs(e) for e in errors) / n

        # Root Mean Square Error
        rmse = (sum(e**2 for e in errors) / n) ** 0.5

        # Bias (average signed error)
        bias = sum(errors) / n

        # Mean accuracy
        mean_accuracy = sum(accuracies) / n

        # Within confidence rate
        within_ci_rate = (within_ci_count / n) * 100

        # Recent accuracy (last 10)
        recent_accuracies = accuracies[-10:] if len(accuracies) >= 10 else accuracies
        recent_accuracy = sum(recent_accuracies) / len(recent_accuracies)

        return ModelAccuracyMetrics(
            total_predictions=n,
            mean_accuracy=round(mean_accuracy, 2),
            mean_absolute_error=round(mae, 2),
            root_mean_square_error=round(rmse, 2),
            within_confidence_rate=round(within_ci_rate, 2),
            bias=round(bias, 2),
            recent_accuracy=round(recent_accuracy, 2),
        )

    def get_history_summary(self, limit: int = 20) -> List[Dict]:
        """
        Get recent forecast history with comparisons.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of forecast/actual comparison dictionaries
        """
        recent = self.history[-limit:] if len(self.history) > limit else self.history

        summaries = []
        for forecast, actual_roi in recent:
            error = forecast.predicted_roi - actual_roi
            ci_low, ci_high = forecast.confidence_interval

            summaries.append({
                "spec_id": forecast.spec_id,
                "predicted_roi": forecast.predicted_roi,
                "actual_roi": actual_roi,
                "error": round(error, 2),
                "within_ci": ci_low <= actual_roi <= ci_high,
                "created_at": forecast.created_at.isoformat(),
            })

        return summaries


# Singleton instance for the application
_forecast_model: Optional[ImpactForecastModel] = None


def get_forecast_model(storage_path: Optional[Path] = None) -> ImpactForecastModel:
    """
    Get the singleton forecast model instance.

    Args:
        storage_path: Optional path to store forecast history

    Returns:
        ImpactForecastModel instance
    """
    global _forecast_model

    if _forecast_model is None:
        _forecast_model = ImpactForecastModel(storage_path)

    return _forecast_model
