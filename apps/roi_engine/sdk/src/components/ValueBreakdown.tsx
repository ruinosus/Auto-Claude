/**
 * ValueBreakdown Component
 *
 * Displays a visual breakdown of value by role and/or artifact type.
 */

import React, { useMemo } from 'react';
import type { ValueBreakdownProps, Role } from '../types';
import { ROLE_LABELS, ROLE_COLORS } from '../types';

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
 * Bar item in the breakdown chart.
 */
interface BreakdownBarProps {
  label: string;
  value: number;
  percentage: number;
  color: string;
}

function BreakdownBar({
  label,
  value,
  percentage,
  color,
}: BreakdownBarProps): React.ReactElement {
  return (
    <div className="value-breakdown__bar-container">
      <div className="value-breakdown__bar-header">
        <span className="value-breakdown__bar-label">{label}</span>
        <span className="value-breakdown__bar-value">{formatCurrency(value)}</span>
      </div>
      <div className="value-breakdown__bar-track">
        <div
          className="value-breakdown__bar-fill"
          style={{
            width: `${Math.min(percentage, 100)}%`,
            backgroundColor: color,
          }}
        />
      </div>
      <span className="value-breakdown__bar-percentage">
        {percentage.toFixed(1)}%
      </span>
    </div>
  );
}

/**
 * Generate a color for artifact types (deterministic based on name).
 */
function getArtifactTypeColor(type: string): string {
  const colors = [
    '#3B82F6', // blue
    '#10B981', // green
    '#8B5CF6', // purple
    '#F59E0B', // amber
    '#EF4444', // red
    '#06B6D4', // cyan
    '#EC4899', // pink
    '#84CC16', // lime
  ];

  // Simple hash function to get consistent color
  let hash = 0;
  for (let i = 0; i < type.length; i++) {
    hash = ((hash << 5) - hash + type.charCodeAt(i)) | 0;
  }

  return colors[Math.abs(hash) % colors.length];
}

/**
 * Value Breakdown Component
 *
 * @example
 * ```tsx
 * <ValueBreakdown
 *   byRole={roi.by_role}
 *   byType={roi.by_type}
 *   tokenCost={roi.token_cost}
 * />
 * ```
 */
export function ValueBreakdown({
  byRole,
  byType,
  tokenCost = 0,
  className = '',
}: ValueBreakdownProps): React.ReactElement {
  const roleBreakdown = useMemo(() => {
    if (!byRole) return [];

    const total = Object.values(byRole).reduce((sum, v) => sum + v, 0);

    return Object.entries(byRole)
      .map(([role, value]) => ({
        label: ROLE_LABELS[role as Role] || role,
        value,
        percentage: total > 0 ? (value / total) * 100 : 0,
        color: ROLE_COLORS[role as Role] || '#6B7280',
      }))
      .sort((a, b) => b.value - a.value);
  }, [byRole]);

  const typeBreakdown = useMemo(() => {
    if (!byType) return [];

    const total = Object.values(byType).reduce((sum, v) => sum + v, 0);

    return Object.entries(byType)
      .map(([type, value]) => ({
        label: type.replace(/_/g, ' '),
        value,
        percentage: total > 0 ? (value / total) * 100 : 0,
        color: getArtifactTypeColor(type),
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 10); // Show top 10 types
  }, [byType]);

  const totalValue = useMemo(() => {
    if (byRole) {
      return Object.values(byRole).reduce((sum, v) => sum + v, 0);
    }
    if (byType) {
      return Object.values(byType).reduce((sum, v) => sum + v, 0);
    }
    return 0;
  }, [byRole, byType]);

  const netValue = totalValue - tokenCost;

  const hasData = roleBreakdown.length > 0 || typeBreakdown.length > 0;

  if (!hasData) {
    return (
      <div className={`value-breakdown value-breakdown--empty ${className}`}>
        <p>No breakdown data available</p>
      </div>
    );
  }

  return (
    <div className={`value-breakdown ${className}`}>
      {/* Summary */}
      <div className="value-breakdown__summary">
        <div className="value-breakdown__summary-item">
          <span className="value-breakdown__summary-label">Total Value</span>
          <span className="value-breakdown__summary-value positive">
            {formatCurrency(totalValue)}
          </span>
        </div>
        {tokenCost > 0 && (
          <>
            <div className="value-breakdown__summary-item">
              <span className="value-breakdown__summary-label">Token Cost</span>
              <span className="value-breakdown__summary-value negative">
                -{formatCurrency(tokenCost)}
              </span>
            </div>
            <div className="value-breakdown__summary-item value-breakdown__summary-item--highlight">
              <span className="value-breakdown__summary-label">Net Value</span>
              <span className={`value-breakdown__summary-value ${netValue >= 0 ? 'positive' : 'negative'}`}>
                {formatCurrency(netValue)}
              </span>
            </div>
          </>
        )}
      </div>

      {/* By Role */}
      {roleBreakdown.length > 0 && (
        <div className="value-breakdown__section">
          <h4 className="value-breakdown__section-title">By Role</h4>
          <div className="value-breakdown__bars">
            {roleBreakdown.map((item) => (
              <BreakdownBar key={item.label} {...item} />
            ))}
          </div>
        </div>
      )}

      {/* By Type */}
      {typeBreakdown.length > 0 && (
        <div className="value-breakdown__section">
          <h4 className="value-breakdown__section-title">By Artifact Type</h4>
          <div className="value-breakdown__bars">
            {typeBreakdown.map((item) => (
              <BreakdownBar key={item.label} {...item} />
            ))}
          </div>
          {byType && Object.keys(byType).length > 10 && (
            <p className="value-breakdown__more">
              +{Object.keys(byType).length - 10} more types
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default ValueBreakdown;
