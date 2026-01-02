import { IPC_CHANNELS } from '../../../shared/constants';
import type { LocalArtifact, ArtifactFilters } from '../../../shared/types/analytics-v2';
import type { IPCResult } from '../../../shared/types/common';
import { invokeIpc } from './ipc-utils';

/**
 * Artifact API operations (nested under 'artifact' property)
 * Provides access to locally stored full artifact content
 */
export interface ArtifactAPI {
  artifact: {
    get: (projectId: string, artifactId: string) => Promise<IPCResult<LocalArtifact>>;
    list: (projectId: string, filters?: ArtifactFilters) => Promise<IPCResult<LocalArtifact[]>>;
    getByTrace: (projectId: string, traceId: string) => Promise<IPCResult<LocalArtifact[]>>;
  };
}

/**
 * Creates the Artifact API implementation
 */
export const createArtifactAPI = (): ArtifactAPI => ({
  artifact: {
    get: (projectId: string, artifactId: string): Promise<IPCResult<LocalArtifact>> =>
      invokeIpc(IPC_CHANNELS.ARTIFACT_GET, projectId, artifactId),
    list: (projectId: string, filters?: ArtifactFilters): Promise<IPCResult<LocalArtifact[]>> =>
      invokeIpc(IPC_CHANNELS.ARTIFACT_LIST, projectId, filters),
    getByTrace: (projectId: string, traceId: string): Promise<IPCResult<LocalArtifact[]>> =>
      invokeIpc(IPC_CHANNELS.ARTIFACT_GET_BY_TRACE, projectId, traceId)
  }
});
