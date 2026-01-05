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

/**
 * Build environment variables for memory/Graphiti and auth configuration from app settings.
 *
 * @param settings - App-wide settings from settings.json
 * @returns Record of environment variables to inject into agent processes
 */
export function buildMemoryEnvVars(settings: AppSettings): Record<string, string> {
  const env: Record<string, string> = {};

  // =========================================================================
  // AZURE FOUNDRY AUTHENTICATION (Claude API)
  // =========================================================================
  // These settings are configured in the Onboarding Wizard (AzureFoundryStep)
  // and must be passed to Python agent processes for Claude SDK to work.

  if (settings.defaultAuthMode === 'azure-foundry') {
    env.CLAUDE_CODE_USE_FOUNDRY = '1';

    if (settings.azureFoundryApiKey) {
      env.ANTHROPIC_FOUNDRY_API_KEY = settings.azureFoundryApiKey;
      env.ANTHROPIC_AUTH_TOKEN = settings.azureFoundryApiKey; // Fallback for some SDK versions
    }

    if (settings.azureFoundryBaseUrl) {
      env.ANTHROPIC_FOUNDRY_BASE_URL = settings.azureFoundryBaseUrl;
    }

    if (settings.azureFoundryResourceName) {
      env.ANTHROPIC_FOUNDRY_RESOURCE = settings.azureFoundryResourceName;
    }

    // Model deployment names
    if (settings.azureFoundrySonnetModel) {
      env.ANTHROPIC_DEFAULT_SONNET_MODEL = settings.azureFoundrySonnetModel;
    }

    if (settings.azureFoundryHaikuModel) {
      env.ANTHROPIC_DEFAULT_HAIKU_MODEL = settings.azureFoundryHaikuModel;
    }

    if (settings.azureFoundryOpusModel) {
      env.ANTHROPIC_DEFAULT_OPUS_MODEL = settings.azureFoundryOpusModel;
    }
  }

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
