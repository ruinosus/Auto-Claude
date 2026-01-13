/**
 * ROISummaryCard Component
 *
 * Displays a summary of ROI calculation results.
 */

import React from 'react';
import type { ROISummaryCardProps, ROIResult, ROISummary } from '../types';

/**
 * Format a number as currency.
 */
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format a percentage.
 */
function formatPercentage(value: number): string {
  if (value >= 10000) {
    return `${(value / 1000).toFixed(1)}k%`;
  }
  return `${value.toFixed(1)}%`;
}

/**
 * Check if the value is an ROIResult (has scope property).
 */
function isROIResult(value: ROIResult | ROISummary): value is ROIResult {
  return 'scope' in value;
}

/**
 * ROI Summary Card Component
 *
 * @example
 * ```tsx
 * <ROISummaryCard roi={roiResult} showBreakdown />
 * ```
 */
export function ROISummaryCard({
  roi,
  loading = false,
  showBreakdown = true,
  className = '',
}: ROISummaryCardProps): React.ReactElement {
  if (loading) {
    return (
      <div className={`roi-summary-card roi-summary-card--loading ${className}`}>
        <div className="roi-summary-card__skeleton" />
      </div>
    );
  }

  if (!roi) {
    return (
      <div className={`roi-summary-card roi-summary-card--empty ${className}`}>
        <p>No ROI data available</p>
      </div>
    );
  }

  // Normalize to common fields
  const totalValue = isROIResult(roi) ? roi.total_artifact_value : roi.total_value;
  const tokenCost = isROIResult(roi) ? roi.token_cost : roi.total_cost;
  const netValue = roi.net_value;
  const roiPercentage = roi.roi_percentage;
  const artifactCount = isROIResult(roi) ? roi.artifact_count : roi.artifact_count;

  const isPositive = netValue >= 0;

  return (
    <div className={`roi-summary-card ${className}`}>
      {/* Main ROI Display */}
      <div className="roi-summary-card__main">
        <div className="roi-summary-card__percentage">
          <span className={`roi-summary-card__value ${isPositive ? 'positive' : 'negative'}`}>
            {formatPercentage(roiPercentage)}
          </span>
          <span className="roi-summary-card__label">ROI</span>
        </div>
      </div>

      {/* Value Breakdown */}
      <div className="roi-summary-card__breakdown">
        <div className="roi-summary-card__metric">
          <span className="roi-summary-card__metric-label">Artifact Value</span>
          <span className="roi-summary-card__metric-value positive">
            {formatCurrency(totalValue)}
          </span>
        </div>

        <div className="roi-summary-card__metric">
          <span className="roi-summary-card__metric-label">Token Cost</span>
          <span className="roi-summary-card__metric-value negative">
            {formatCurrency(tokenCost)}
          </span>
        </div>

        <div className="roi-summary-card__metric roi-summary-card__metric--highlight">
          <span className="roi-summary-card__metric-label">Net Value</span>
          <span className={`roi-summary-card__metric-value ${isPositive ? 'positive' : 'negative'}`}>
            {formatCurrency(netValue)}
          </span>
        </div>
      </div>

      {/* Artifact Count */}
      <div className="roi-summary-card__footer">
        <span className="roi-summary-card__artifact-count">
          Based on {artifactCount} artifact{artifactCount !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Role Breakdown (if available and requested) */}
      {showBreakdown && isROIResult(roi) && roi.by_role && (
        <div className="roi-summary-card__roles">
          <h4 className="roi-summary-card__roles-title">Value by Role</h4>
          <div className="roi-summary-card__roles-list">
            {Object.entries(roi.by_role)
              .sort(([, a], [, b]) => b - a)
              .map(([role, value]) => (
                <div key={role} className="roi-summary-card__role">
                  <span className="roi-summary-card__role-name">{role}</span>
                  <span className="roi-summary-card__role-value">
                    {formatCurrency(value)}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default ROISummaryCard;
