/**
 * ArtifactsByRole Component
 *
 * Displays artifacts grouped by their responsible role.
 */

import React, { useMemo } from 'react';
import type { ArtifactsByRoleProps, ArtifactValue, Role } from '../types';
import { ROLE_LABELS, ROLE_COLORS } from '../types';
import { groupArtifactsByRole, calculateGroupValue } from '../hooks/useArtifacts';

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
 * Role section with artifacts
 */
interface RoleSectionProps {
  role: Role;
  artifacts: ArtifactValue[];
  totalValue: number;
  onArtifactClick?: (artifact: ArtifactValue) => void;
}

function RoleSection({
  role,
  artifacts,
  totalValue,
  onArtifactClick,
}: RoleSectionProps): React.ReactElement {
  const roleLabel = ROLE_LABELS[role] || role;
  const roleColor = ROLE_COLORS[role] || '#6B7280';

  return (
    <div className="artifacts-by-role__section">
      <div
        className="artifacts-by-role__header"
        style={{ borderLeftColor: roleColor }}
      >
        <div className="artifacts-by-role__role-info">
          <span
            className="artifacts-by-role__role-dot"
            style={{ backgroundColor: roleColor }}
          />
          <span className="artifacts-by-role__role-name">{roleLabel}</span>
          <span className="artifacts-by-role__artifact-count">
            ({artifacts.length})
          </span>
        </div>
        <span className="artifacts-by-role__role-value">
          {formatCurrency(totalValue)}
        </span>
      </div>

      <ul className="artifacts-by-role__list">
        {artifacts.map((artifact) => (
          <li
            key={artifact.artifact_id}
            className="artifacts-by-role__item"
            onClick={() => onArtifactClick?.(artifact)}
            role={onArtifactClick ? 'button' : undefined}
            tabIndex={onArtifactClick ? 0 : undefined}
          >
            <div className="artifacts-by-role__item-info">
              <span className="artifacts-by-role__item-type">
                {artifact.artifact_type}
              </span>
              <span className="artifacts-by-role__item-hours">
                {artifact.estimated_hours}h @ {formatCurrency(artifact.hourly_rate)}/hr
              </span>
            </div>
            <span className="artifacts-by-role__item-value">
              {formatCurrency(artifact.calculated_value)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Artifacts By Role Component
 *
 * @example
 * ```tsx
 * <ArtifactsByRole
 *   artifacts={artifacts}
 *   onArtifactClick={(artifact) => console.log(artifact)}
 * />
 * ```
 */
export function ArtifactsByRole({
  artifacts,
  onArtifactClick,
  className = '',
}: ArtifactsByRoleProps): React.ReactElement {
  const groupedArtifacts = useMemo(() => {
    const grouped = groupArtifactsByRole(artifacts);

    // Sort roles by total value (descending)
    return Object.entries(grouped)
      .map(([role, roleArtifacts]) => ({
        role: role as Role,
        artifacts: roleArtifacts,
        totalValue: calculateGroupValue(roleArtifacts),
      }))
      .sort((a, b) => b.totalValue - a.totalValue);
  }, [artifacts]);

  const totalValue = useMemo(
    () => calculateGroupValue(artifacts),
    [artifacts]
  );

  if (artifacts.length === 0) {
    return (
      <div className={`artifacts-by-role artifacts-by-role--empty ${className}`}>
        <p>No artifacts found</p>
      </div>
    );
  }

  return (
    <div className={`artifacts-by-role ${className}`}>
      <div className="artifacts-by-role__summary">
        <span className="artifacts-by-role__total-label">Total Value</span>
        <span className="artifacts-by-role__total-value">
          {formatCurrency(totalValue)}
        </span>
      </div>

      <div className="artifacts-by-role__sections">
        {groupedArtifacts.map(({ role, artifacts: roleArtifacts, totalValue: roleValue }) => (
          <RoleSection
            key={role}
            role={role}
            artifacts={roleArtifacts}
            totalValue={roleValue}
            onArtifactClick={onArtifactClick}
          />
        ))}
      </div>
    </div>
  );
}

export default ArtifactsByRole;
