/**
 * Model Resolver Utility
 * Resolves model shorthand names to the correct model IDs based on the active profile.
 * For Azure Foundry mode, uses deployment names instead of full model IDs.
 */

import { existsSync, readFileSync } from 'fs';
import * as path from 'path';
import { getClaudeProfileManager } from '../claude-profile-manager';
import { MODEL_ID_MAP, AZURE_FOUNDRY_MODEL_MAP } from '../../shared/constants/models';

/**
 * Check if auto-claude .env has Azure Foundry mode enabled
 */
function isFoundryModeInEnv(): boolean {
  try {
    // Use the same path detection logic as agent-process.ts
    const possiblePaths = [
      // Respect explicitly configured path
      process.env.AUTO_BUILD_SOURCE_PATH,
      // Dev mode: from dist/main -> ../../backend (apps/frontend/out/main -> apps/backend)
      path.resolve(__dirname, '..', '..', '..', 'backend'),
      // If running from repo root with apps structure
      path.resolve(process.cwd(), 'apps', 'backend'),
    ].filter(Boolean) as string[];

    for (const basePath of possiblePaths) {
      const envPath = path.join(basePath, '.env');
      if (existsSync(envPath)) {
        const content = readFileSync(envPath, 'utf-8');
        // Check if CLAUDE_CODE_USE_FOUNDRY=1 or =true is set
        const foundryMatch = content.match(/^CLAUDE_CODE_USE_FOUNDRY\s*=\s*(1|true|True)/m);
        if (foundryMatch) {
          console.warn('[ModelResolver] Azure Foundry mode detected from .env file at:', envPath);
          return true;
        }
      }
    }
  } catch {
    // Ignore errors
  }
  return false;
}

/**
 * Check if the active profile is using Azure Foundry mode
 * Checks both profile settings AND auto-claude .env file
 */
export function isAzureFoundryMode(): boolean {
  // First check profile settings (UI-configured)
  const profileManager = getClaudeProfileManager();
  const profile = profileManager.getActiveProfile();

  if (profile?.proxyEnabled && profile.proxyBaseUrl) {
    const isAzureProfile = profile.proxyBaseUrl.includes('.azure.com') ||
                           profile.proxyBaseUrl.includes('azure') ||
                           profile.proxyBaseUrl.includes('foundry');
    if (isAzureProfile) {
      return true;
    }
  }

  // Also check .env file for CLI-configured Foundry mode
  return isFoundryModeInEnv();
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
