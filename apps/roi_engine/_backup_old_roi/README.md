# Backup - Old ROI System Files

This directory contains backup copies of the old ROI calculation system files
that were replaced by the new artifact-based ROI Engine.

## Backup Date
2024-01-11

## Files Backed Up

| File | Original Location | Description |
|------|-------------------|-------------|
| `roi_publisher.py` | `apps/backend/analytics/` | Unified ROI publishing to Langfuse |
| `roi_score_publisher.py` | `apps/backend/analytics/` | Spec-based ROI score calculation |
| `unified_roi_calculator.py` | `apps/backend/analytics/` | 4-dimension ROI calculation model |
| `roi_model.py` | `apps/backend/analytics/` | Data models for old ROI system |
| `api/roi_calculator.py` | `apps/backend/analytics/api/` | API endpoint for ROI calculation |

## Why Replaced?

The old system used an abstract 4-dimension model (Execution, Decision, Prevention, Knowledge)
with fixed artifact values. The new ROI Engine uses a concrete artifact-based approach:

- **Each artifact** is valued based on the **role** that would produce it
- **Value = Hourly Rate × Estimated Hours**
- **ROI = (Total Artifact Value - Token Cost) / Token Cost × 100%**

## New System Location

The new ROI Engine is located at `apps/roi_engine/` and provides:
- Role-based artifact valuation
- Squad configuration support
- Simpler, more understandable ROI calculations
- TypeScript SDK for frontend integration

## Restoration

If needed, these files can be restored to their original locations.
However, the new system is designed to be a complete replacement.
