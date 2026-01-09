/**
 * Utility functions for managing environment variables in agent spawning
 */

import { readSettingsFile } from '../settings-utils';
import type { AppSettings } from '../../shared/types/settings';

/**
 * Get environment variables to clear ANTHROPIC_* vars when in OAuth mode
 *
 * When switching from API Profile mode to OAuth mode, residual ANTHROPIC_*
 * environment variables from process.env can cause authentication failures.
 * This function returns an object with empty strings for these vars when
 * no API profile is active, ensuring OAuth tokens are used correctly.
 *
 * **Why empty strings?** Setting environment variables to empty strings (rather than
 * undefined) ensures they override any stale values from process.env. Python's SDK
 * treats empty strings as falsy in conditional checks like `if token:`, so empty
 * strings effectively disable these authentication parameters without leaving
 * undefined values that might be ignored during object spreading.
 *
 * **IMPORTANT:** When Azure Foundry is configured via settings.json (defaultAuthMode),
 * we MUST NOT clear the ANTHROPIC_DEFAULT_*_MODEL variables, as they are set by
 * buildMemoryEnvVars() and are required for correct model deployment name resolution.
 *
 * @param apiProfileEnv - Environment variables from getAPIProfileEnv()
 * @returns Object with empty ANTHROPIC_* vars if in OAuth mode, empty object otherwise
 */
export function getOAuthModeClearVars(apiProfileEnv: Record<string, string>): Record<string, string> {
  // If API profile is active (has ANTHROPIC_* vars), don't clear anything
  if (apiProfileEnv && Object.keys(apiProfileEnv).some(key => key.startsWith('ANTHROPIC_'))) {
    return {};
  }

  // Check if Azure Foundry is configured via settings.json
  // In this case, we should NOT clear the ANTHROPIC_DEFAULT_*_MODEL vars
  // because they are set by buildMemoryEnvVars() for correct model resolution
  try {
    const settings = readSettingsFile() as AppSettings | undefined;
    if (settings?.defaultAuthMode === 'azure-foundry') {
      // Azure Foundry mode via settings - only clear API key/token vars, NOT model vars
      // The model vars are configured by buildMemoryEnvVars() and must be preserved
      console.warn('[EnvUtils] Azure Foundry mode detected - preserving model deployment names');
      return {
        ANTHROPIC_API_KEY: '',
        // Note: NOT clearing ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL, or ANTHROPIC_DEFAULT_*_MODEL
        // because buildMemoryEnvVars() sets the correct Azure Foundry values for these
      };
    }
  } catch {
    // Ignore errors reading settings
  }

  // In OAuth mode (no API profile, no Azure Foundry), clear all ANTHROPIC_* vars
  // Setting to empty string ensures they override any values from process.env
  // Python's `if token:` checks treat empty strings as falsy
  //
  // IMPORTANT: ANTHROPIC_API_KEY is included to prevent Claude Code from using
  // API keys that may be present in the shell environment instead of OAuth tokens.
  // Without clearing this, Claude Code would show "Claude API" instead of "Claude Max".
  return {
    ANTHROPIC_API_KEY: '',
    ANTHROPIC_AUTH_TOKEN: '',
    ANTHROPIC_BASE_URL: '',
    ANTHROPIC_MODEL: '',
    ANTHROPIC_DEFAULT_HAIKU_MODEL: '',
    ANTHROPIC_DEFAULT_SONNET_MODEL: '',
    ANTHROPIC_DEFAULT_OPUS_MODEL: ''
  };
}
