import path from 'path';
import { getOAuthModeClearVars } from '../../../agent/env-utils';
import { getAPIProfileEnv } from '../../../services/profile';
import { getProfileEnv } from '../../../rate-limit-detector';
import { pythonEnvManager } from '../../../python-env-manager';

/**
 * Get environment variables for Python runner subprocesses.
 *
 * Environment variable precedence (lowest to highest):
 * 1. pythonEnv - Python environment including PYTHONPATH for bundled packages (fixes #139)
 * 2. apiProfileEnv - Custom Anthropic-compatible API profile (ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN)
 * 3. oauthModeClearVars - Clears stale ANTHROPIC_* vars when in OAuth mode
 * 4. profileEnv - Claude OAuth token from profile manager (CLAUDE_CODE_OAUTH_TOKEN)
 * 5. extraEnv - Caller-specific vars (e.g., USE_CLAUDE_MD)
 *
 * The pythonEnv is critical for packaged apps (#139) - without PYTHONPATH, Python
 * cannot find bundled dependencies like dotenv, claude_agent_sdk, etc.
 *
 * The profileEnv is critical for OAuth authentication (#563) - it retrieves the
 * decrypted OAuth token from the profile manager's encrypted storage (macOS Keychain
 * via Electron's safeStorage API).
 *
 * @param extraEnv - Additional environment variables to include
 * @param autoBuildSource - Optional path to the auto-build source (apps/backend). If provided,
 *                          the parent directory (apps/) will be added to PYTHONPATH to allow
 *                          importing sibling packages like roi_engine.
 */
export async function getRunnerEnv(
  extraEnv?: Record<string, string>,
  autoBuildSource?: string
): Promise<Record<string, string>> {
  const pythonEnv = pythonEnvManager.getPythonEnv();
  const apiProfileEnv = await getAPIProfileEnv();
  const oauthModeClearVars = getOAuthModeClearVars(apiProfileEnv);
  const profileEnv = getProfileEnv();

  // Build combined PYTHONPATH: bundled site-packages + autoBuildSource + parent dir (for roi_engine)
  const pythonPathParts: string[] = [];
  if (pythonEnv.PYTHONPATH) {
    pythonPathParts.push(pythonEnv.PYTHONPATH);
  }
  if (autoBuildSource) {
    pythonPathParts.push(autoBuildSource);
    // Add parent directory (apps/) so roi_engine and other sibling packages can be imported
    const appsDir = path.dirname(autoBuildSource);
    if (appsDir && appsDir !== autoBuildSource) {
      pythonPathParts.push(appsDir);
    }
  }
  const combinedPythonPath = pythonPathParts.length > 0
    ? pythonPathParts.join(process.platform === 'win32' ? ';' : ':')
    : undefined;

  return {
    ...pythonEnv,  // Python environment including base PYTHONPATH (fixes #139)
    ...apiProfileEnv,
    ...oauthModeClearVars,
    ...profileEnv,  // OAuth token from profile manager (fixes #563)
    ...extraEnv,
    ...(combinedPythonPath ? { PYTHONPATH: combinedPythonPath } : {}),
  };
}
