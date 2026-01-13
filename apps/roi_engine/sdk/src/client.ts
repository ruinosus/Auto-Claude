/**
 * ROI Engine API Client
 *
 * Provides a type-safe client for interacting with the ROI Engine REST API.
 */

import type {
  ROIResult,
  ROISummary,
  ArtifactValue,
  ArtifactListResponse,
  ArtifactValuePreviewRequest,
  ArtifactValuePreviewResponse,
  RateTableResponse,
  ArtifactTypesResponse,
  RolesResponse,
  HealthResponse,
  SpecROIRequest,
  TraceROIRequest,
} from './types';

/**
 * Configuration options for ROIClient.
 */
export interface ROIClientConfig {
  /**
   * Base URL for the ROI Engine API.
   * @default 'http://localhost:8002'
   */
  baseUrl?: string;

  /**
   * Request timeout in milliseconds.
   * @default 30000
   */
  timeout?: number;

  /**
   * Custom headers to include in all requests.
   */
  headers?: Record<string, string>;
}

/**
 * Options for listing artifacts.
 */
export interface ListArtifactsOptions {
  projectDir: string;
  specId?: string;
  traceId?: string;
  artifactType?: string;
  limit?: number;
}

/**
 * API client for the ROI Engine.
 */
export class ROIClient {
  private baseUrl: string;
  private timeout: number;
  private headers: Record<string, string>;

  constructor(config: ROIClientConfig = {}) {
    this.baseUrl = config.baseUrl ?? 'http://localhost:8002';
    this.timeout = config.timeout ?? 30000;
    this.headers = {
      'Content-Type': 'application/json',
      ...config.headers,
    };
  }

  /**
   * Make an HTTP request to the API.
   */
  private async request<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    path: string,
    body?: unknown,
    queryParams?: Record<string, string | number | undefined>
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);

    // Add query parameters
    if (queryParams) {
      Object.entries(queryParams).forEach(([key, value]) => {
        if (value !== undefined) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url.toString(), {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || error.error || `HTTP ${response.status}`);
      }

      return response.json();
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // Health & Config
  // ═══════════════════════════════════════════════════════════════

  /**
   * Check API health status.
   */
  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>('GET', '/health');
  }

  /**
   * Get the rate table (hourly rates by seniority and role).
   */
  async getRates(): Promise<RateTableResponse> {
    return this.request<RateTableResponse>('GET', '/api/config/rates');
  }

  /**
   * Get all artifact types with their role mappings.
   */
  async getArtifactTypes(): Promise<ArtifactTypesResponse> {
    return this.request<ArtifactTypesResponse>('GET', '/api/config/artifact-types');
  }

  /**
   * Get all roles with descriptions.
   */
  async getRoles(): Promise<RolesResponse> {
    return this.request<RolesResponse>('GET', '/api/config/roles');
  }

  // ═══════════════════════════════════════════════════════════════
  // ROI Calculation
  // ═══════════════════════════════════════════════════════════════

  /**
   * Calculate ROI for a spec.
   */
  async calculateROIForSpec(request: SpecROIRequest): Promise<ROIResult> {
    return this.request<ROIResult>('POST', '/api/roi/spec', request);
  }

  /**
   * Calculate ROI for a trace.
   */
  async calculateROIForTrace(request: TraceROIRequest): Promise<ROIResult> {
    return this.request<ROIResult>('POST', '/api/roi/trace', request);
  }

  /**
   * Get ROI for a spec (convenience GET method).
   */
  async getROIForSpec(
    specId: string,
    projectDir: string,
    tokenCost = 0
  ): Promise<ROIResult> {
    return this.request<ROIResult>('GET', `/api/roi/spec/${specId}`, undefined, {
      project_dir: projectDir,
      token_cost: tokenCost,
    });
  }

  /**
   * Get simplified ROI summary for a spec.
   */
  async getROISummary(
    specId: string,
    projectDir: string,
    tokenCost = 0
  ): Promise<ROISummary> {
    return this.request<ROISummary>('GET', `/api/roi/summary/${specId}`, undefined, {
      project_dir: projectDir,
      token_cost: tokenCost,
    });
  }

  // ═══════════════════════════════════════════════════════════════
  // Artifacts
  // ═══════════════════════════════════════════════════════════════

  /**
   * List artifacts with optional filters.
   */
  async listArtifacts(options: ListArtifactsOptions): Promise<ArtifactListResponse> {
    return this.request<ArtifactListResponse>('GET', '/api/artifacts', undefined, {
      project_dir: options.projectDir,
      spec_id: options.specId,
      trace_id: options.traceId,
      artifact_type: options.artifactType,
      limit: options.limit,
    });
  }

  /**
   * Get a single artifact by ID.
   */
  async getArtifact(artifactId: string, projectDir: string): Promise<ArtifactValue> {
    return this.request<ArtifactValue>(
      'GET',
      `/api/artifacts/${artifactId}`,
      undefined,
      { project_dir: projectDir }
    );
  }

  /**
   * Preview value calculation for an artifact type.
   */
  async previewArtifactValue(
    request: ArtifactValuePreviewRequest
  ): Promise<ArtifactValuePreviewResponse> {
    return this.request<ArtifactValuePreviewResponse>(
      'POST',
      '/api/artifacts/preview',
      request
    );
  }
}

/**
 * Default client instance.
 */
let defaultClient: ROIClient | null = null;

/**
 * Get or create the default ROI client.
 */
export function getDefaultClient(config?: ROIClientConfig): ROIClient {
  if (!defaultClient || config) {
    defaultClient = new ROIClient(config);
  }
  return defaultClient;
}

/**
 * Create a new ROI client with custom configuration.
 */
export function createClient(config?: ROIClientConfig): ROIClient {
  return new ROIClient(config);
}
