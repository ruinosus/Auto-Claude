"""
Analytics module for Auto-Claude usage metrics.

Provides:
- UsageTracker: Token usage and cost tracking for agent sessions
- AnalyticsStorage: SQLite + JSON dual persistence
- ModelsPricingProvider: Dynamic LLM pricing from models.dev
- OTelExporter: OpenTelemetry metrics export (optional)
"""

from .storage import (
    AnalyticsStorage,
    get_analytics_storage,
    is_tracking_enabled,
)

from .usage_tracker import UsageTracker

from .feature_tracker import (
    FeatureUsageTracker,
    create_feature_tracker,
    FEATURE_ROADMAP,
    FEATURE_IDEATION,
    FEATURE_INSIGHTS,
    FEATURE_PR_REVIEW,
    FEATURE_ISSUE_TRIAGE,
    FEATURE_AUTOFIX,
    FEATURE_CHANGELOG,
)

from .roi_tracker import ROITracker, create_roi_tracker

from .pricing_provider import (
    ModelPricing,
    ModelsPricingProvider,
    get_model_pricing,
    get_pricing_provider,
)

from .otel_exporter import (
    OTelExporter,
    get_otel_exporter,
    is_otel_enabled,
)

__all__ = [
    # Storage
    "AnalyticsStorage",
    "get_analytics_storage",
    "is_tracking_enabled",
    # Usage Tracker (spec-based)
    "UsageTracker",
    # Feature Tracker (feature-based)
    "FeatureUsageTracker",
    "create_feature_tracker",
    "FEATURE_ROADMAP",
    "FEATURE_IDEATION",
    "FEATURE_INSIGHTS",
    "FEATURE_PR_REVIEW",
    "FEATURE_ISSUE_TRIAGE",
    "FEATURE_AUTOFIX",
    "FEATURE_CHANGELOG",
    # ROI Tracker
    "ROITracker",
    "create_roi_tracker",
    # Pricing
    "ModelPricing",
    "ModelsPricingProvider",
    "get_model_pricing",
    "get_pricing_provider",
    # OpenTelemetry
    "OTelExporter",
    "get_otel_exporter",
    "is_otel_enabled",
]
