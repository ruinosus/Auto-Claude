/**
 * useROI Hook
 *
 * React hook for fetching and managing ROI data.
 */

import { useState, useEffect, useCallback } from 'react';
import type { ROIResult, ROISummary, UseROIOptions, UseROIResult } from '../types';
import { getDefaultClient } from '../client';

/**
 * Hook for fetching ROI data for a spec or trace.
 *
 * @example
 * ```tsx
 * function SpecROI({ specId, projectDir }: Props) {
 *   const { roi, summary, loading, error } = useROI({
 *     specId,
 *     projectDir,
 *     tokenCost: 0.85,
 *   });
 *
 *   if (loading) return <Spinner />;
 *   if (error) return <Error message={error.message} />;
 *
 *   return (
 *     <div>
 *       <h2>ROI: {roi?.roi_percentage.toFixed(1)}%</h2>
 *       <p>Value: ${roi?.total_artifact_value.toFixed(2)}</p>
 *     </div>
 *   );
 * }
 * ```
 */
export function useROI(options: UseROIOptions): UseROIResult {
  const { specId, traceId, projectDir, tokenCost = 0, enabled = true } = options;

  const [roi, setRoi] = useState<ROIResult | null>(null);
  const [summary, setSummary] = useState<ROISummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchROI = useCallback(async () => {
    if (!enabled || (!specId && !traceId)) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const client = getDefaultClient();

      if (specId) {
        // Fetch both full ROI and summary for spec
        const [roiResult, summaryResult] = await Promise.all([
          client.getROIForSpec(specId, projectDir, tokenCost),
          client.getROISummary(specId, projectDir, tokenCost),
        ]);
        setRoi(roiResult);
        setSummary(summaryResult);
      } else if (traceId) {
        // For trace, calculate ROI
        const roiResult = await client.calculateROIForTrace({
          trace_id: traceId,
          project_dir: projectDir,
          token_cost: tokenCost,
        });
        setRoi(roiResult);
        // Create summary from ROI result
        setSummary({
          total_value: roiResult.total_artifact_value,
          total_cost: roiResult.token_cost,
          net_value: roiResult.net_value,
          roi_percentage: roiResult.roi_percentage,
          artifact_count: roiResult.artifact_count,
          top_role: undefined,
          top_role_value: 0,
          top_artifact_type: undefined,
          top_artifact_type_value: 0,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [specId, traceId, projectDir, tokenCost, enabled]);

  useEffect(() => {
    fetchROI();
  }, [fetchROI]);

  return {
    roi,
    summary,
    loading,
    error,
    refetch: fetchROI,
  };
}

export default useROI;
