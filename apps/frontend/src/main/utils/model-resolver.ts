/**
 * Model Resolver Utility
 * Resolves model shorthand names to the correct model IDs based on the active profile.
 * For Azure Foundry mode, uses deployment names instead of full model IDs.
 */

import { getClaudeProfileManager } from '../claude-profile-manager';
import { MODEL_ID_MAP, AZURE_FOUNDRY_MODEL_MAP } from '../../shared/constants/models';

/**
 * Check if the active profile is using Azure Foundry mode
 */
export function isAzureFoundryMode(): boolean {
  const profileManager = getClaudeProfileManager();
  const profile = profileManager.getActiveProfile();

  if (!profile?.proxyEnabled || !profile.proxyBaseUrl) {
    return false;
  }

  return profile.proxyBaseUrl.includes('.azure.com') ||
         profile.proxyBaseUrl.includes('azure') ||
         profile.proxyBaseUrl.includes('foundry');
}

/**
 * Get the correct model ID for the given model shorthand.
 * Returns Azure Foundry deployment name if Azure Foundry mode is active,
 * otherwise returns the full Anthropic model ID.
 *
 * @param modelShort - Model shorthand ('opus', 'sonnet', 'haiku')
 * @param defaultModel - Default model shorthand if modelShort is not found
 * @returns The resolved model ID
 */
export function resolveModelId(modelShort: string, defaultModel: string = 'opus'): string {
  const isAzure = isAzureFoundryMode();
  const modelMap = isAzure ? AZURE_FOUNDRY_MODEL_MAP : MODEL_ID_MAP;

  const resolvedModel = modelMap[modelShort] ?? modelMap[defaultModel] ?? modelMap['opus'];

  if (isAzure) {
    console.warn('[ModelResolver] Azure Foundry mode - using deployment name:', resolvedModel);
  }

  return resolvedModel;
}

/**
 * Get the appropriate model map based on the active profile.
 * Returns Azure Foundry model map if Azure Foundry mode is active,
 * otherwise returns the standard MODEL_ID_MAP.
 */
export function getActiveModelMap(): Record<string, string> {
  return isAzureFoundryMode() ? AZURE_FOUNDRY_MODEL_MAP : MODEL_ID_MAP;
}

/**
 * Get environment variables needed for Claude SDK/CLI calls.
 * Includes model overrides for Azure Foundry mode.
 */
export function getModelEnvVars(): Record<string, string> {
  const profileManager = getClaudeProfileManager();
  return profileManager.getActiveProfileEnv();
}
