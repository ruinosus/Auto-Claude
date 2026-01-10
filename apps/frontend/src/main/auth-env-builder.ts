/**
 * Auth Environment Variable Builder
 *
 * Centralized authentication configuration based on user's choice.
 * This respects the user's `defaultAuthMode` setting without complex fallbacks.
 *
 * Principle: If user chose azure-foundry → use azure-foundry. No priorities.
 */

import * as fs from 'fs';
import * as path from 'path';
import { app } from 'electron';
import { readSettingsFile } from './settings-utils';
import { parseEnvFile } from './ipc-handlers/utils';
import type { AppSettings } from '../shared/types/settings';
import { debugLog, debugError } from '../shared/utils/debug-logger';

/**
 * Azure Foundry environment variable keys (per Microsoft Foundry documentation)
 * Reference: https://code.claude.com/docs/en/microsoft-foundry
 *
 * IMPORTANT: Do NOT include ANTHROPIC_AUTH_TOKEN or ANTHROPIC_BASE_URL
 * These are for different authentication methods and will confuse the SDK!
 */
const AZURE_FOUNDRY_VARS = [
  'CLAUDE_CODE_USE_FOUNDRY',
  'ANTHROPIC_FOUNDRY_API_KEY',
  'ANTHROPIC_FOUNDRY_BASE_URL',
  'ANTHROPIC_FOUNDRY_RESOURCE',
  'ANTHROPIC_DEFAULT_SONNET_MODEL',
  'ANTHROPIC_DEFAULT_HAIKU_MODEL',
  'ANTHROPIC_DEFAULT_OPUS_MODEL'
] as const;

/**
 * Returns environment variables based on user's auth mode choice.
 * No priorities. The user's choice in settings.json is respected.
 *
 * @returns Record of environment variables for the chosen auth mode
 */
export function getAuthEnvVars(): Record<string, string> {
  const settings = readSettingsFile() as unknown as AppSettings | null;
  const authMode = settings?.defaultAuthMode;

  // Always log for debugging Azure Foundry issues
  console.warn('[AuthEnvBuilder] getAuthEnvVars called:', {
    hasSettings: !!settings,
    authMode: authMode || '(not set)',
    hasResourceName: !!settings?.azureFoundryResourceName,
    hasApiKey: !!settings?.azureFoundryApiKey
  });

  if (authMode === 'azure-foundry') {
    const envVars = getAzureFoundryEnvVars(settings);
    console.warn('[AuthEnvBuilder] Returning Azure Foundry vars:', Object.keys(envVars));
    return envVars;
  }

  // OAuth or other modes - return empty (use default OAuth mechanism)
  console.warn('[AuthEnvBuilder] Not azure-foundry mode, returning empty');
  return {};
}

/**
 * Get Azure Foundry environment variables.
 * Tries settings.json first, then falls back to apps/backend/.env
 */
function getAzureFoundryEnvVars(settings: AppSettings | null): Record<string, string> {
  const env: Record<string, string> = {};

  // 1. Try to read from settings.json (configured via UI)
  if (settings?.azureFoundryResourceName || settings?.azureFoundryBaseUrl) {
    env.CLAUDE_CODE_USE_FOUNDRY = '1';

    // CRITICAL: RESOURCE and BASE_URL are mutually exclusive
    // SDK expects ONE OR THE OTHER, not both
    // Priority: RESOURCE (if present) > BASE_URL
    if (settings.azureFoundryResourceName) {
      env.ANTHROPIC_FOUNDRY_RESOURCE = settings.azureFoundryResourceName;
      // Do NOT set BASE_URL when RESOURCE is present
    } else if (settings.azureFoundryBaseUrl) {
      // Only set BASE_URL if RESOURCE is not configured
      env.ANTHROPIC_FOUNDRY_BASE_URL = settings.azureFoundryBaseUrl;
      // NEVER set ANTHROPIC_BASE_URL - backend removes it in Foundry mode
    }

    if (settings.azureFoundryApiKey) {
      env.ANTHROPIC_FOUNDRY_API_KEY = settings.azureFoundryApiKey;
      // NOTE: Do NOT set ANTHROPIC_AUTH_TOKEN - that's for proxy/CCR mode, not Azure Foundry
    }
    if (settings.azureFoundrySonnetModel) {
      env.ANTHROPIC_DEFAULT_SONNET_MODEL = settings.azureFoundrySonnetModel;
    }
    if (settings.azureFoundryHaikuModel) {
      env.ANTHROPIC_DEFAULT_HAIKU_MODEL = settings.azureFoundryHaikuModel;
    }
    if (settings.azureFoundryOpusModel) {
      env.ANTHROPIC_DEFAULT_OPUS_MODEL = settings.azureFoundryOpusModel;
    }

    debugLog('[AuthEnvBuilder] Azure Foundry env vars from settings:', {
      resource: env.ANTHROPIC_FOUNDRY_RESOURCE || '(not set)',
      baseUrl: env.ANTHROPIC_FOUNDRY_BASE_URL || '(not set - using RESOURCE)',
      hasApiKey: !!env.ANTHROPIC_FOUNDRY_API_KEY,
      models: {
        sonnet: env.ANTHROPIC_DEFAULT_SONNET_MODEL,
        haiku: env.ANTHROPIC_DEFAULT_HAIKU_MODEL,
        opus: env.ANTHROPIC_DEFAULT_OPUS_MODEL
      }
    });

    return env;
  }

  // 2. If settings.json doesn't have values, read from apps/backend/.env
  const backendEnv = loadBackendEnv();
  if (backendEnv.CLAUDE_CODE_USE_FOUNDRY) {
    debugLog('[AuthEnvBuilder] Using Azure Foundry config from apps/backend/.env');
    return backendEnv;
  }

  // 3. Azure Foundry selected but not configured - clear error
  debugError('[AuthEnvBuilder] Azure Foundry selected but not configured!');
  console.error('[Auth] Azure Foundry mode selected but no configuration found.');
  console.error('[Auth] Please configure in Settings or add values to apps/backend/.env');

  return {};
}

/**
 * Load Azure Foundry configuration from apps/backend/.env
 */
function loadBackendEnv(): Record<string, string> {
  const possiblePaths = [
    // From Electron app path
    path.resolve(app.getAppPath(), '..', 'backend', '.env'),
    // From current working directory
    path.resolve(process.cwd(), 'apps', 'backend', '.env'),
    // Development paths
    path.resolve(__dirname, '..', '..', '..', 'backend', '.env'),
  ];

  for (const envPath of possiblePaths) {
    if (fs.existsSync(envPath)) {
      try {
        const content = fs.readFileSync(envPath, 'utf-8');
        const vars = parseEnvFile(content);

        // Filter only Azure Foundry related variables
        const azureVars: Record<string, string> = {};
        for (const key of AZURE_FOUNDRY_VARS) {
          if (vars[key]) {
            azureVars[key] = vars[key];
          }
        }

        if (Object.keys(azureVars).length > 0) {
          debugLog('[AuthEnvBuilder] Loaded backend .env from:', envPath);
          debugLog('[AuthEnvBuilder] Azure vars found:', Object.keys(azureVars));
          return azureVars;
        }
      } catch (error) {
        debugError('[AuthEnvBuilder] Failed to load backend .env:', error);
      }
    }
  }

  return {};
}

/**
 * Check if Azure Foundry mode is enabled based on settings.
 * Use this instead of duplicating detection logic.
 */
export function isAzureFoundryEnabled(): boolean {
  const settings = readSettingsFile() as unknown as AppSettings | null;
  return settings?.defaultAuthMode === 'azure-foundry';
}

/**
 * Get auth environment variables as shell export commands.
 * Useful for terminal integration.
 */
export function getAuthEnvVarsAsExports(): string {
  const env = getAuthEnvVars();

  if (Object.keys(env).length === 0) {
    return '';
  }

  return Object.entries(env)
    .map(([key, value]) => `export ${key}="${value}"`)
    .join('\n') + '\n';
}
