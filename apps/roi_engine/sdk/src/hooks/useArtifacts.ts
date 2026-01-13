/**
 * useArtifacts Hook
 *
 * React hook for fetching and managing artifact data.
 */

import { useState, useEffect, useCallback } from 'react';
import type { ArtifactValue, UseArtifactsOptions, UseArtifactsResult } from '../types';
import { getDefaultClient } from '../client';

/**
 * Hook for fetching artifacts with optional filters.
 *
 * @example
 * ```tsx
 * function ArtifactList({ specId, projectDir }: Props) {
 *   const { artifacts, totalValue, loading, error } = useArtifacts({
 *     specId,
 *     projectDir,
 *     limit: 50,
 *   });
 *
 *   if (loading) return <Spinner />;
 *   if (error) return <Error message={error.message} />;
 *
 *   return (
 *     <div>
 *       <h2>Total Value: ${totalValue.toFixed(2)}</h2>
 *       <ul>
 *         {artifacts.map(artifact => (
 *           <li key={artifact.artifact_id}>
 *             {artifact.artifact_type}: ${artifact.calculated_value.toFixed(2)}
 *           </li>
 *         ))}
 *       </ul>
 *     </div>
 *   );
 * }
 * ```
 */
export function useArtifacts(options: UseArtifactsOptions): UseArtifactsResult {
  const {
    specId,
    traceId,
    projectDir,
    artifactType,
    limit = 100,
    enabled = true,
  } = options;

  const [artifacts, setArtifacts] = useState<ArtifactValue[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalValue, setTotalValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchArtifacts = useCallback(async () => {
    if (!enabled) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const client = getDefaultClient();
      const response = await client.listArtifacts({
        projectDir,
        specId,
        traceId,
        artifactType,
        limit,
      });

      setArtifacts(response.artifacts);
      setTotalCount(response.total_count);
      setTotalValue(response.total_value);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [specId, traceId, projectDir, artifactType, limit, enabled]);

  useEffect(() => {
    fetchArtifacts();
  }, [fetchArtifacts]);

  return {
    artifacts,
    totalCount,
    totalValue,
    loading,
    error,
    refetch: fetchArtifacts,
  };
}

/**
 * Group artifacts by role.
 */
export function groupArtifactsByRole(
  artifacts: ArtifactValue[]
): Record<string, ArtifactValue[]> {
  return artifacts.reduce((acc, artifact) => {
    const role = artifact.role;
    if (!acc[role]) {
      acc[role] = [];
    }
    acc[role].push(artifact);
    return acc;
  }, {} as Record<string, ArtifactValue[]>);
}

/**
 * Group artifacts by type.
 */
export function groupArtifactsByType(
  artifacts: ArtifactValue[]
): Record<string, ArtifactValue[]> {
  return artifacts.reduce((acc, artifact) => {
    const type = artifact.artifact_type;
    if (!acc[type]) {
      acc[type] = [];
    }
    acc[type].push(artifact);
    return acc;
  }, {} as Record<string, ArtifactValue[]>);
}

/**
 * Calculate total value for a group of artifacts.
 */
export function calculateGroupValue(artifacts: ArtifactValue[]): number {
  return artifacts.reduce((sum, a) => sum + a.calculated_value, 0);
}

export default useArtifacts;
