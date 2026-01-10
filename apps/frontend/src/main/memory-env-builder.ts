/**
 * Memory & Auth Environment Variable Builder
 *
 * Converts app-wide settings from settings.json into environment variables
 * that can be injected into Python agent processes.
 *
 * This bridges the gap between frontend settings storage and backend configuration.
 *
 * Handles:
 * - Graphiti/Memory configuration
 * - Azure Foundry authentication (Claude API)
 */

import type { AppSettings } from '../shared/types/settings';
import { getMemoriesDir } from './config-paths';
import { getAuthEnvVars } from './auth-env-builder';

/**
 * Centralized Azure Foundry mode detection.
 * Use this function instead of duplicating detection logic across files.
 *
 * @param settings - Optional AppSettings to check defaultAuthMode
 * @param url - Optional URL to check for Azure Foundry patterns
 * @returns true if Azure Foundry mode is detected
 */
export function isAzureFoundryMode(settings?: Partial<AppSettings> | null, url?: string): boolean {
  // Check via settings.defaultAuthMode
  if (settings?.defaultAuthMode === 'azure-foundry') {
    return true;
  }

  // Check via URL patterns
  if (url) {
    const lowerUrl = url.toLowerCase();
    if (
      lowerUrl.includes('.azure.com') ||
      lowerUrl.includes('services.ai.azure.com') ||
      lowerUrl.includes('foundry')
    ) {
      return true;
    }
  }

  return false;
}

/**
 * Build environment variables for memory/Graphiti and auth configuration from app settings.
 *
 * SIMPLIFIED: Uses centralized getAuthEnvVars() for Azure Foundry configuration.
 * This ensures consistent auth handling across terminal, agents, and all other components.
 *
 * @param settings - App-wide settings from settings.json
 * @returns Record of environment variables to inject into agent processes
 */
export function buildMemoryEnvVars(settings: AppSettings): Record<string, string> {
  // =========================================================================
  // AZURE FOUNDRY AUTHENTICATION (Claude API)
  // =========================================================================
  // Use centralized auth env builder - respects user's choice from settings.json
  // and falls back to apps/backend/.env if needed
  const env: Record<string, string> = { ...getAuthEnvVars() };

  // =========================================================================
  // GRAPHITI/MEMORY CONFIGURATION
  // =========================================================================

  // If memory is not enabled, return empty env
  if (!settings.memoryEnabled) {
    return env;
  }

  // Enable Graphiti
  env.GRAPHITI_ENABLED = 'true';

  // Set database path and name (where LadybugDB stores data)
  env.GRAPHITI_DB_PATH = getMemoriesDir();
  env.GRAPHITI_DATABASE = 'auto_claude_memory';

  // Set embedder provider (default to ollama)
  const embeddingProvider = settings.memoryEmbeddingProvider || 'ollama';
  env.GRAPHITI_EMBEDDER_PROVIDER = embeddingProvider;

  // Provider-specific configuration
  switch (embeddingProvider) {
    case 'ollama':
      env.OLLAMA_BASE_URL = settings.ollamaBaseUrl || 'http://localhost:11434';
      if (settings.memoryOllamaEmbeddingModel) {
        env.OLLAMA_EMBEDDING_MODEL = settings.memoryOllamaEmbeddingModel;
      }
      if (settings.memoryOllamaEmbeddingDim) {
        env.OLLAMA_EMBEDDING_DIM = String(settings.memoryOllamaEmbeddingDim);
      }
      break;

    case 'openai':
      if (settings.globalOpenAIApiKey) {
        env.OPENAI_API_KEY = settings.globalOpenAIApiKey;
      }
      break;

    case 'voyage':
      if (settings.memoryVoyageApiKey) {
        env.VOYAGE_API_KEY = settings.memoryVoyageApiKey;
      }
      break;

    case 'google':
      if (settings.globalGoogleApiKey) {
        env.GOOGLE_API_KEY = settings.globalGoogleApiKey;
      }
      break;

    case 'azure_openai':
      if (settings.memoryAzureApiKey) {
        env.AZURE_OPENAI_API_KEY = settings.memoryAzureApiKey;
      }
      if (settings.memoryAzureBaseUrl) {
        env.AZURE_OPENAI_BASE_URL = settings.memoryAzureBaseUrl;
      }
      if (settings.memoryAzureEmbeddingDeployment) {
        env.AZURE_OPENAI_EMBEDDING_DEPLOYMENT = settings.memoryAzureEmbeddingDeployment;
      }
      break;

    case 'openrouter':
      if (settings.globalOpenRouterApiKey) {
        env.OPENROUTER_API_KEY = settings.globalOpenRouterApiKey;
      }
      break;
  }

  return env;
}
