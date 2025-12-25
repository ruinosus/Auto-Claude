/**
 * Claude Integration Handler
 * Manages Claude-specific operations including profile switching, rate limiting, and OAuth token detection
 */

import * as os from 'os';
import * as fs from 'fs';
import * as path from 'path';
import { app } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import { getClaudeProfileManager } from '../claude-profile-manager';
import * as OutputParser from './output-parser';
import * as SessionHandler from './session-handler';
import { debugLog, debugError } from '../../shared/utils/debug-logger';
import { escapeShellArg, buildCdCommand } from '../../shared/utils/shell-escape';
import { parseEnvFile } from '../ipc-handlers/utils';
import { getProfileEnv } from '../rate-limit-detector';
import type {
  TerminalProcess,
  WindowGetter,
  RateLimitEvent,
  OAuthTokenEvent
} from './types';

/**
 * Handle rate limit detection and profile switching
 */
export function handleRateLimit(
  terminal: TerminalProcess,
  data: string,
  lastNotifiedRateLimitReset: Map<string, string>,
  getWindow: WindowGetter,
  switchProfileCallback: (terminalId: string, profileId: string) => Promise<void>
): void {
  const resetTime = OutputParser.extractRateLimitReset(data);
  if (!resetTime) {
    return;
  }

  const lastNotifiedReset = lastNotifiedRateLimitReset.get(terminal.id);
  if (resetTime === lastNotifiedReset) {
    return;
  }

  lastNotifiedRateLimitReset.set(terminal.id, resetTime);
  console.warn('[ClaudeIntegration] Rate limit detected, reset:', resetTime);

  const profileManager = getClaudeProfileManager();
  const currentProfileId = terminal.claudeProfileId || 'default';

  try {
    const rateLimitEvent = profileManager.recordRateLimitEvent(currentProfileId, resetTime);
    console.warn('[ClaudeIntegration] Recorded rate limit event:', rateLimitEvent.type);
  } catch (err) {
    console.error('[ClaudeIntegration] Failed to record rate limit event:', err);
  }

  const autoSwitchSettings = profileManager.getAutoSwitchSettings();
  const bestProfile = profileManager.getBestAvailableProfile(currentProfileId);

  const win = getWindow();
  if (win) {
    win.webContents.send(IPC_CHANNELS.TERMINAL_RATE_LIMIT, {
      terminalId: terminal.id,
      resetTime,
      detectedAt: new Date().toISOString(),
      profileId: currentProfileId,
      suggestedProfileId: bestProfile?.id,
      suggestedProfileName: bestProfile?.name,
      autoSwitchEnabled: autoSwitchSettings.autoSwitchOnRateLimit
    } as RateLimitEvent);
  }

  if (autoSwitchSettings.enabled && autoSwitchSettings.autoSwitchOnRateLimit && bestProfile) {
    console.warn('[ClaudeIntegration] Auto-switching to profile:', bestProfile.name);
    switchProfileCallback(terminal.id, bestProfile.id).then(_result => {
      console.warn('[ClaudeIntegration] Auto-switch completed');
    }).catch(err => {
      console.error('[ClaudeIntegration] Auto-switch failed:', err);
    });
  }
}

/**
 * Handle OAuth token detection and auto-save
 */
export function handleOAuthToken(
  terminal: TerminalProcess,
  data: string,
  getWindow: WindowGetter
): void {
  const token = OutputParser.extractOAuthToken(data);
  if (!token) {
    return;
  }

  console.warn('[ClaudeIntegration] OAuth token detected, length:', token.length);

  const email = OutputParser.extractEmail(terminal.outputBuffer);
  // Match both custom profiles (profile-123456) and the default profile
  const profileIdMatch = terminal.id.match(/claude-login-(profile-\d+|default)-/);

  if (profileIdMatch) {
    // Save to specific profile (profile login terminal)
    const profileId = profileIdMatch[1];
    const profileManager = getClaudeProfileManager();
    const success = profileManager.setProfileToken(profileId, token, email || undefined);

    if (success) {
      console.warn('[ClaudeIntegration] OAuth token auto-saved to profile:', profileId);

      const win = getWindow();
      if (win) {
        win.webContents.send(IPC_CHANNELS.TERMINAL_OAUTH_TOKEN, {
          terminalId: terminal.id,
          profileId,
          email,
          success: true,
          detectedAt: new Date().toISOString()
        } as OAuthTokenEvent);
      }
    } else {
      console.error('[ClaudeIntegration] Failed to save OAuth token to profile:', profileId);
    }
  } else {
    // No profile-specific terminal, save to active profile (GitHub OAuth flow, etc.)
    console.warn('[ClaudeIntegration] OAuth token detected in non-profile terminal, saving to active profile');
    const profileManager = getClaudeProfileManager();
    const activeProfile = profileManager.getActiveProfile();

    // Defensive null check for active profile
    if (!activeProfile) {
      console.error('[ClaudeIntegration] Failed to save OAuth token: no active profile found');
      const win = getWindow();
      if (win) {
        win.webContents.send(IPC_CHANNELS.TERMINAL_OAUTH_TOKEN, {
          terminalId: terminal.id,
          profileId: undefined,
          email,
          success: false,
          message: 'No active profile found',
          detectedAt: new Date().toISOString()
        } as OAuthTokenEvent);
      }
      return;
    }

    const success = profileManager.setProfileToken(activeProfile.id, token, email || undefined);

    if (success) {
      console.warn('[ClaudeIntegration] OAuth token auto-saved to active profile:', activeProfile.name);

      const win = getWindow();
      if (win) {
        win.webContents.send(IPC_CHANNELS.TERMINAL_OAUTH_TOKEN, {
          terminalId: terminal.id,
          profileId: activeProfile.id,
          email,
          success: true,
          detectedAt: new Date().toISOString()
        } as OAuthTokenEvent);
      }
    } else {
      console.error('[ClaudeIntegration] Failed to save OAuth token to active profile:', activeProfile.name);
      const win = getWindow();
      if (win) {
        win.webContents.send(IPC_CHANNELS.TERMINAL_OAUTH_TOKEN, {
          terminalId: terminal.id,
          profileId: activeProfile?.id,
          email,
          success: false,
          message: 'Failed to save token to active profile',
          detectedAt: new Date().toISOString()
        } as OAuthTokenEvent);
      }
    }
  }
}

/**
 * Handle Claude session ID capture
 */
export function handleClaudeSessionId(
  terminal: TerminalProcess,
  sessionId: string,
  getWindow: WindowGetter
): void {
  terminal.claudeSessionId = sessionId;
  console.warn('[ClaudeIntegration] Captured Claude session ID:', sessionId);

  if (terminal.projectPath) {
    SessionHandler.updateClaudeSessionId(terminal.projectPath, terminal.id, sessionId);
  }

  const win = getWindow();
  if (win) {
    win.webContents.send(IPC_CHANNELS.TERMINAL_CLAUDE_SESSION, terminal.id, sessionId);
  }
}

/**
 * Extract Azure resource name from Foundry URL
 * @param url - Azure Foundry base URL (e.g., https://aif-cockpit-br-prd01.services.ai.azure.com/anthropic)
 * @returns Resource name (e.g., aif-cockpit-br-prd01) or undefined
 */
function extractAzureResourceFromUrl(url: string): string | undefined {
  try {
    const urlObj = new URL(url);
    const hostname = urlObj.hostname;

    // Extract resource name from hostname patterns:
    // Pattern 1: resource-name.openai.azure.com
    // Pattern 2: resource-name.services.ai.azure.com
    const match = hostname.match(/^([^.]+)\.(openai\.azure\.com|services\.ai\.azure\.com)$/);

    if (match) {
      return match[1];
    }
  } catch (error) {
    debugError('[ClaudeIntegration:extractAzureResourceFromUrl] Invalid URL:', error);
  }

  return undefined;
}

/**
 * Find the backend directory by trying multiple possible paths
 * @returns Path to backend directory or undefined if not found
 */
function findBackendDir(): string | undefined {
  const possiblePaths = [
    // New apps structure: from out/main -> apps/backend
    path.resolve(__dirname, '..', '..', '..', 'backend'),
    path.resolve(app.getAppPath(), '..', 'backend'),
    path.resolve(process.cwd(), 'apps', 'backend'),
    // Legacy paths for backwards compatibility
    path.resolve(__dirname, '..', '..', '..', 'auto-claude'),
    path.resolve(app.getAppPath(), '..', 'auto-claude'),
    path.resolve(process.cwd(), 'auto-claude')
  ];

  for (const backendPath of possiblePaths) {
    if (fs.existsSync(backendPath)) {
      return backendPath;
    }
  }

  return undefined;
}

/**
 * Load Azure Foundry configuration from backend .env file
 * @returns Object with all Azure Foundry environment variables
 */
function loadBackendAzureFoundryConfig(): Record<string, string> {
  const backendDir = findBackendDir();
  if (!backendDir) {
    debugLog('[ClaudeIntegration:loadBackendAzureFoundryConfig] Backend directory not found');
    return {};
  }

  const backendEnvPath = path.join(backendDir, '.env');

  if (!fs.existsSync(backendEnvPath)) {
    debugLog('[ClaudeIntegration:loadBackendAzureFoundryConfig] Backend .env not found at:', backendEnvPath);
    return {};
  }

  try {
    const envContent = fs.readFileSync(backendEnvPath, 'utf-8');
    const vars = parseEnvFile(envContent);
    const config: Record<string, string> = {};

    // Extract all Azure Foundry related variables
    const azureFoundryVars = [
      'CLAUDE_CODE_USE_FOUNDRY',
      'ANTHROPIC_FOUNDRY_API_KEY',
      'ANTHROPIC_FOUNDRY_BASE_URL',
      'ANTHROPIC_FOUNDRY_RESOURCE',
      'ANTHROPIC_BASE_URL',
      'ANTHROPIC_API_KEY',
      'ANTHROPIC_AUTH_TOKEN',
      'ANTHROPIC_DEFAULT_SONNET_MODEL',
      'ANTHROPIC_DEFAULT_HAIKU_MODEL',
      'ANTHROPIC_DEFAULT_OPUS_MODEL'
    ];

    for (const varName of azureFoundryVars) {
      if (vars[varName]) {
        config[varName] = vars[varName];
      }
    }

    if (Object.keys(config).length > 0) {
      debugLog('[ClaudeIntegration:loadBackendAzureFoundryConfig] Loaded Azure Foundry config:', {
        hasFoundryFlag: !!config['CLAUDE_CODE_USE_FOUNDRY'],
        hasApiKey: !!config['ANTHROPIC_FOUNDRY_API_KEY'],
        hasBaseUrl: !!config['ANTHROPIC_BASE_URL'],
        modelOverrides: {
          sonnet: !!config['ANTHROPIC_DEFAULT_SONNET_MODEL'],
          haiku: !!config['ANTHROPIC_DEFAULT_HAIKU_MODEL'],
          opus: !!config['ANTHROPIC_DEFAULT_OPUS_MODEL']
        }
      });
    }

    return config;
  } catch (error) {
    debugError('[ClaudeIntegration:loadBackendAzureFoundryConfig] Failed to load backend .env:', error);
    return {};
  }
}

/**
 * Build environment variables for terminal session.
 *
 * Priority:
 * 1. Active profile configuration (global)
 * 2. Project .env (legacy/per-project config)
 * 3. OAuth token (fallback)
 *
 * @param projectPath - Path to the project (to locate .env file)
 * @param oauthToken - OAuth token from Claude profile (fallback)
 * @returns Shell export commands as a string
 */
function buildTerminalEnvVars(projectPath: string | undefined, oauthToken: string | undefined): string {
  const envVars: string[] = [];

  // PRIORITY 1: Use active profile configuration (global)
  const profileEnv = getProfileEnv();

  if (profileEnv.ANTHROPIC_BASE_URL && profileEnv.ANTHROPIC_AUTH_TOKEN) {
    // Profile is in proxy mode (Azure Foundry)
    debugLog('[ClaudeIntegration:buildTerminalEnvVars] Using Azure Foundry profile configuration');

    const baseUrl = profileEnv.ANTHROPIC_BASE_URL;
    const apiKey = profileEnv.ANTHROPIC_AUTH_TOKEN;

    // Export Azure Foundry variables
    envVars.push('export CLAUDE_CODE_USE_FOUNDRY=1');
    envVars.push(`export ANTHROPIC_FOUNDRY_API_KEY="${apiKey}"`);
    envVars.push(`export ANTHROPIC_FOUNDRY_BASE_URL="${baseUrl}"`);

    // Export proxy mode variables for SDK compatibility
    // NOTE: When using ANTHROPIC_BASE_URL, do NOT export ANTHROPIC_FOUNDRY_RESOURCE
    // as they are mutually exclusive in the Claude SDK
    envVars.push(`export ANTHROPIC_BASE_URL="${baseUrl}"`);
    envVars.push(`export ANTHROPIC_AUTH_TOKEN="${apiKey}"`);

    // Load and export ALL Azure Foundry config from backend .env
    const backendConfig = loadBackendAzureFoundryConfig();
    for (const [key, value] of Object.entries(backendConfig)) {
      // Skip if already exported from profile, or if mutually exclusive with base URL
      if (key === 'ANTHROPIC_BASE_URL' ||
          key === 'ANTHROPIC_AUTH_TOKEN' ||
          key === 'ANTHROPIC_FOUNDRY_RESOURCE') {
        continue;
      }
      envVars.push(`export ${key}="${value}"`);
    }

    debugLog('[ClaudeIntegration:buildTerminalEnvVars] Azure Foundry profile env vars:', {
      hasApiKey: !!apiKey,
      hasBaseUrl: !!baseUrl,
      backendConfigVars: Object.keys(backendConfig)
    });

    return envVars.join('\n') + '\n';
  }

  if (profileEnv.CLAUDE_CODE_OAUTH_TOKEN) {
    // Profile has OAuth token
    debugLog('[ClaudeIntegration:buildTerminalEnvVars] Using OAuth token from profile');
    envVars.push(`export CLAUDE_CODE_OAUTH_TOKEN="${profileEnv.CLAUDE_CODE_OAUTH_TOKEN}"`);
    return envVars.join('\n') + '\n';
  }

  if (profileEnv.CLAUDE_CONFIG_DIR) {
    // Profile uses config dir (legacy)
    debugLog('[ClaudeIntegration:buildTerminalEnvVars] Using config dir from profile');
    envVars.push(`export CLAUDE_CONFIG_DIR="${profileEnv.CLAUDE_CONFIG_DIR}"`);
    return envVars.join('\n') + '\n';
  }

  // PRIORITY 2: Try to load Azure Foundry configuration from project .env (legacy)
  if (projectPath) {
    const projectEnvPath = path.join(projectPath, '.auto-claude', '.env');

    if (fs.existsSync(projectEnvPath)) {
      try {
        const envContent = fs.readFileSync(projectEnvPath, 'utf-8');
        const vars = parseEnvFile(envContent);

        // Check if Azure Foundry is enabled
        const isFoundryEnabled = vars['CLAUDE_CODE_USE_FOUNDRY'] === '1' ||
                                  vars['CLAUDE_CODE_USE_FOUNDRY'] === 'true';

        if (isFoundryEnabled) {
          debugLog('[ClaudeIntegration:buildTerminalEnvVars] Azure Foundry detected in project .env (legacy)');

          // Export Azure Foundry flag
          envVars.push('export CLAUDE_CODE_USE_FOUNDRY=1');

          // Export Azure Foundry API Key
          if (vars['ANTHROPIC_FOUNDRY_API_KEY']) {
            envVars.push(`export ANTHROPIC_FOUNDRY_API_KEY="${vars['ANTHROPIC_FOUNDRY_API_KEY']}"`);
          }

          // Export Azure Foundry Base URL
          if (vars['ANTHROPIC_FOUNDRY_BASE_URL']) {
            envVars.push(`export ANTHROPIC_FOUNDRY_BASE_URL="${vars['ANTHROPIC_FOUNDRY_BASE_URL']}"`);
          }

          // Export Azure Foundry Resource
          if (vars['ANTHROPIC_FOUNDRY_RESOURCE']) {
            envVars.push(`export ANTHROPIC_FOUNDRY_RESOURCE="${vars['ANTHROPIC_FOUNDRY_RESOURCE']}"`);
          }

          // Export Azure Foundry Model Overrides
          if (vars['ANTHROPIC_DEFAULT_SONNET_MODEL']) {
            envVars.push(`export ANTHROPIC_DEFAULT_SONNET_MODEL="${vars['ANTHROPIC_DEFAULT_SONNET_MODEL']}"`);
          }
          if (vars['ANTHROPIC_DEFAULT_HAIKU_MODEL']) {
            envVars.push(`export ANTHROPIC_DEFAULT_HAIKU_MODEL="${vars['ANTHROPIC_DEFAULT_HAIKU_MODEL']}"`);
          }
          if (vars['ANTHROPIC_DEFAULT_OPUS_MODEL']) {
            envVars.push(`export ANTHROPIC_DEFAULT_OPUS_MODEL="${vars['ANTHROPIC_DEFAULT_OPUS_MODEL']}"`);
          }

          // Export base URL if set (for consistency)
          if (vars['ANTHROPIC_BASE_URL']) {
            envVars.push(`export ANTHROPIC_BASE_URL="${vars['ANTHROPIC_BASE_URL']}"`);
          }

          debugLog('[ClaudeIntegration:buildTerminalEnvVars] Azure Foundry env vars (project):', {
            hasApiKey: !!vars['ANTHROPIC_FOUNDRY_API_KEY'],
            hasBaseUrl: !!vars['ANTHROPIC_FOUNDRY_BASE_URL'],
            hasResource: !!vars['ANTHROPIC_FOUNDRY_RESOURCE'],
            modelOverrides: {
              sonnet: !!vars['ANTHROPIC_DEFAULT_SONNET_MODEL'],
              haiku: !!vars['ANTHROPIC_DEFAULT_HAIKU_MODEL'],
              opus: !!vars['ANTHROPIC_DEFAULT_OPUS_MODEL']
            }
          });

          return envVars.join('\n') + '\n';
        }
      } catch (error) {
        debugError('[ClaudeIntegration:buildTerminalEnvVars] Failed to load project .env:', error);
      }
    }
  }

  // PRIORITY 3: Fallback to OAuth token (original behavior)
  if (oauthToken) {
    debugLog('[ClaudeIntegration:buildTerminalEnvVars] Using OAuth token (fallback)');
    envVars.push(`export CLAUDE_CODE_OAUTH_TOKEN="${oauthToken}"`);
  }

  return envVars.join('\n') + '\n';
}

/**
 * Invoke Claude with optional profile override
 */
export function invokeClaude(
  terminal: TerminalProcess,
  cwd: string | undefined,
  profileId: string | undefined,
  getWindow: WindowGetter,
  onSessionCapture: (terminalId: string, projectPath: string, startTime: number) => void
): void {
  debugLog('[ClaudeIntegration:invokeClaude] ========== INVOKE CLAUDE START ==========');
  debugLog('[ClaudeIntegration:invokeClaude] Terminal ID:', terminal.id);
  debugLog('[ClaudeIntegration:invokeClaude] Requested profile ID:', profileId);
  debugLog('[ClaudeIntegration:invokeClaude] CWD:', cwd);

  terminal.isClaudeMode = true;
  terminal.claudeSessionId = undefined;

  const startTime = Date.now();
  const projectPath = cwd || terminal.projectPath || terminal.cwd;

  const profileManager = getClaudeProfileManager();
  const activeProfile = profileId
    ? profileManager.getProfile(profileId)
    : profileManager.getActiveProfile();

  const previousProfileId = terminal.claudeProfileId;
  terminal.claudeProfileId = activeProfile?.id;

  debugLog('[ClaudeIntegration:invokeClaude] Profile resolution:', {
    previousProfileId,
    newProfileId: activeProfile?.id,
    profileName: activeProfile?.name,
    hasOAuthToken: !!activeProfile?.oauthToken,
    isDefault: activeProfile?.isDefault
  });

  // Use safe shell escaping to prevent command injection
  const cwdCommand = buildCdCommand(cwd);

  // Export environment variables for:
  // 1. Proxy mode profiles (Azure Foundry) - ALWAYS, even if default
  // 2. Non-default profiles with OAuth tokens or configDir
  const isProxyMode = activeProfile?.proxyEnabled && activeProfile?.proxyBaseUrl;
  const needsEnvExport = isProxyMode || (activeProfile && !activeProfile.isDefault);

  if (needsEnvExport && activeProfile) {
    const token = profileManager.getProfileToken(activeProfile.id);
    debugLog('[ClaudeIntegration:invokeClaude] Profile needs env export:', {
      profileName: activeProfile.name,
      isDefault: activeProfile.isDefault,
      isProxyMode,
      hasToken: !!token,
      hasConfigDir: !!activeProfile.configDir,
      tokenLength: token?.length
    });

    if (token || activeProfile.configDir || isProxyMode) {
      const tempFile = path.join(os.tmpdir(), `.claude-token-${Date.now()}`);
      debugLog('[ClaudeIntegration:invokeClaude] Writing environment variables to temp file:', tempFile);

      // Build env vars (Azure Foundry if configured via profile, otherwise OAuth token)
      const envContent = buildTerminalEnvVars(terminal.projectPath, token);
      fs.writeFileSync(tempFile, envContent, { mode: 0o600 });

      // Clear terminal and run command without adding to shell history:
      // - HISTFILE= disables history file writing for the current command
      // - HISTCONTROL=ignorespace causes commands starting with space to be ignored
      // - Leading space ensures the command is ignored even if HISTCONTROL was already set
      // - Uses subshell (...) to isolate environment changes
      // This prevents temp file paths from appearing in shell history
      const command = `clear && ${cwdCommand} HISTFILE= HISTCONTROL=ignorespace bash -c 'source "${tempFile}" && rm -f "${tempFile}" && exec claude'\r`;
      debugLog('[ClaudeIntegration:invokeClaude] Executing command (env vars exported via temp file)');
      terminal.pty.write(command);
      debugLog('[ClaudeIntegration:invokeClaude] ========== INVOKE CLAUDE COMPLETE (with env vars) ==========');
      return;
    } else {
      debugLog('[ClaudeIntegration:invokeClaude] WARNING: No token, configDir, or proxy config available');
    }
  }

  // Default behavior (no env vars needed)
  const command = `${cwdCommand}claude\r`;
  debugLog('[ClaudeIntegration:invokeClaude] Executing command (default, no env vars):', command);
  terminal.pty.write(command);

  if (activeProfile) {
    profileManager.markProfileUsed(activeProfile.id);
  }

  const win = getWindow();
  if (win) {
    const title = activeProfile && !activeProfile.isDefault
      ? `Claude (${activeProfile.name})`
      : 'Claude';
    win.webContents.send(IPC_CHANNELS.TERMINAL_TITLE_CHANGE, terminal.id, title);
  }

  if (terminal.projectPath) {
    SessionHandler.persistSession(terminal);
  }

  if (projectPath) {
    onSessionCapture(terminal.id, projectPath, startTime);
  }

  debugLog('[ClaudeIntegration:invokeClaude] ========== INVOKE CLAUDE COMPLETE (default) ==========');
}

/**
 * Resume Claude with optional session ID
 */
export function resumeClaude(
  terminal: TerminalProcess,
  sessionId: string | undefined,
  getWindow: WindowGetter
): void {
  terminal.isClaudeMode = true;

  let command: string;
  if (sessionId) {
    // SECURITY: Escape sessionId to prevent command injection
    command = `claude --resume ${escapeShellArg(sessionId)}`;
    terminal.claudeSessionId = sessionId;
  } else {
    command = 'claude --continue';
  }

  terminal.pty.write(`${command}\r`);

  const win = getWindow();
  if (win) {
    win.webContents.send(IPC_CHANNELS.TERMINAL_TITLE_CHANGE, terminal.id, 'Claude');
  }
}

/**
 * Configuration for waiting for Claude to exit
 */
interface WaitForExitConfig {
  /** Maximum time to wait for Claude to exit (ms) */
  timeout?: number;
  /** Interval between checks (ms) */
  pollInterval?: number;
}

/**
 * Result of waiting for Claude to exit
 */
interface WaitForExitResult {
  /** Whether Claude exited successfully */
  success: boolean;
  /** Error message if failed */
  error?: string;
  /** Whether the operation timed out */
  timedOut?: boolean;
}

/**
 * Shell prompt patterns that indicate Claude has exited and shell is ready
 * These patterns match common shell prompts across bash, zsh, fish, etc.
 */
const SHELL_PROMPT_PATTERNS = [
  /[$%#>❯]\s*$/m,                    // Common prompt endings: $, %, #, >, ❯
  /\w+@[\w.-]+[:\s]/,                // user@hostname: format
  /^\s*\S+\s*[$%#>❯]\s*$/m,          // hostname/path followed by prompt char
  /\(.*\)\s*[$%#>❯]\s*$/m,           // (venv) or (branch) followed by prompt
];

/**
 * Wait for Claude to exit by monitoring terminal output for shell prompt
 *
 * Instead of using fixed delays, this monitors the terminal's outputBuffer
 * for patterns indicating that Claude has exited and the shell prompt is visible.
 */
async function waitForClaudeExit(
  terminal: TerminalProcess,
  config: WaitForExitConfig = {}
): Promise<WaitForExitResult> {
  const { timeout = 5000, pollInterval = 100 } = config;

  debugLog('[ClaudeIntegration:waitForClaudeExit] Waiting for Claude to exit...');
  debugLog('[ClaudeIntegration:waitForClaudeExit] Config:', { timeout, pollInterval });

  // Capture current buffer length to detect new output
  const initialBufferLength = terminal.outputBuffer.length;
  const startTime = Date.now();

  return new Promise((resolve) => {
    const checkForPrompt = () => {
      const elapsed = Date.now() - startTime;

      // Check for timeout
      if (elapsed >= timeout) {
        console.warn('[ClaudeIntegration:waitForClaudeExit] Timeout waiting for Claude to exit after', timeout, 'ms');
        debugLog('[ClaudeIntegration:waitForClaudeExit] Timeout reached, Claude may not have exited cleanly');
        resolve({
          success: false,
          error: `Timeout waiting for Claude to exit after ${timeout}ms`,
          timedOut: true
        });
        return;
      }

      // Get new output since we started waiting
      const newOutput = terminal.outputBuffer.slice(initialBufferLength);

      // Check if we can see a shell prompt in the new output
      for (const pattern of SHELL_PROMPT_PATTERNS) {
        if (pattern.test(newOutput)) {
          debugLog('[ClaudeIntegration:waitForClaudeExit] Shell prompt detected after', elapsed, 'ms');
          debugLog('[ClaudeIntegration:waitForClaudeExit] Matched pattern:', pattern.toString());
          resolve({ success: true });
          return;
        }
      }

      // Also check if isClaudeMode was cleared (set by other handlers)
      if (!terminal.isClaudeMode) {
        debugLog('[ClaudeIntegration:waitForClaudeExit] isClaudeMode flag cleared after', elapsed, 'ms');
        resolve({ success: true });
        return;
      }

      // Continue polling
      setTimeout(checkForPrompt, pollInterval);
    };

    // Start checking
    checkForPrompt();
  });
}

/**
 * Switch terminal to a different Claude profile
 */
export async function switchClaudeProfile(
  terminal: TerminalProcess,
  profileId: string,
  getWindow: WindowGetter,
  invokeClaudeCallback: (terminalId: string, cwd: string | undefined, profileId: string) => void,
  clearRateLimitCallback: (terminalId: string) => void
): Promise<{ success: boolean; error?: string }> {
  // Always-on tracing
  console.warn('[ClaudeIntegration:switchClaudeProfile] Called for terminal:', terminal.id, '| profileId:', profileId);
  console.warn('[ClaudeIntegration:switchClaudeProfile] Terminal state: isClaudeMode=', terminal.isClaudeMode);

  debugLog('[ClaudeIntegration:switchClaudeProfile] ========== SWITCH PROFILE START ==========');
  debugLog('[ClaudeIntegration:switchClaudeProfile] Terminal ID:', terminal.id);
  debugLog('[ClaudeIntegration:switchClaudeProfile] Target profile ID:', profileId);
  debugLog('[ClaudeIntegration:switchClaudeProfile] Terminal state:', {
    isClaudeMode: terminal.isClaudeMode,
    currentProfileId: terminal.claudeProfileId,
    claudeSessionId: terminal.claudeSessionId,
    projectPath: terminal.projectPath,
    cwd: terminal.cwd
  });

  const profileManager = getClaudeProfileManager();
  const profile = profileManager.getProfile(profileId);

  console.warn('[ClaudeIntegration:switchClaudeProfile] Profile found:', profile?.name || 'NOT FOUND');
  debugLog('[ClaudeIntegration:switchClaudeProfile] Target profile:', profile ? {
    id: profile.id,
    name: profile.name,
    hasOAuthToken: !!profile.oauthToken,
    isDefault: profile.isDefault
  } : 'NOT FOUND');

  if (!profile) {
    console.error('[ClaudeIntegration:switchClaudeProfile] Profile not found, aborting');
    debugError('[ClaudeIntegration:switchClaudeProfile] Profile not found, aborting');
    return { success: false, error: 'Profile not found' };
  }

  console.warn('[ClaudeIntegration:switchClaudeProfile] Switching to profile:', profile.name);
  debugLog('[ClaudeIntegration:switchClaudeProfile] Switching to Claude profile:', profile.name);

  if (terminal.isClaudeMode) {
    console.warn('[ClaudeIntegration:switchClaudeProfile] Sending exit commands (Ctrl+C, /exit)');
    debugLog('[ClaudeIntegration:switchClaudeProfile] Terminal is in Claude mode, sending exit commands');

    // Send Ctrl+C to interrupt any ongoing operation
    debugLog('[ClaudeIntegration:switchClaudeProfile] Sending Ctrl+C (\\x03)');
    terminal.pty.write('\x03');

    // Wait briefly for Ctrl+C to take effect before sending /exit
    await new Promise(resolve => setTimeout(resolve, 100));

    // Send /exit command
    debugLog('[ClaudeIntegration:switchClaudeProfile] Sending /exit command');
    terminal.pty.write('/exit\r');

    // Wait for Claude to actually exit by monitoring for shell prompt
    const exitResult = await waitForClaudeExit(terminal, { timeout: 5000, pollInterval: 100 });

    if (exitResult.timedOut) {
      console.warn('[ClaudeIntegration:switchClaudeProfile] Timed out waiting for Claude to exit, proceeding with caution');
      debugLog('[ClaudeIntegration:switchClaudeProfile] Exit timeout - terminal may be in inconsistent state');

      // Even on timeout, we'll try to proceed but log the warning
      // The alternative would be to abort, but that could leave users stuck
      // If this becomes a problem, we could add retry logic or abort option
    } else if (!exitResult.success) {
      console.error('[ClaudeIntegration:switchClaudeProfile] Failed to exit Claude:', exitResult.error);
      debugError('[ClaudeIntegration:switchClaudeProfile] Exit failed:', exitResult.error);
      // Continue anyway - the /exit command was sent
    } else {
      console.warn('[ClaudeIntegration:switchClaudeProfile] Claude exited successfully');
      debugLog('[ClaudeIntegration:switchClaudeProfile] Claude exited, ready to switch profile');
    }
  } else {
    console.warn('[ClaudeIntegration:switchClaudeProfile] NOT in Claude mode, skipping exit commands');
    debugLog('[ClaudeIntegration:switchClaudeProfile] Terminal NOT in Claude mode, skipping exit commands');
  }

  debugLog('[ClaudeIntegration:switchClaudeProfile] Clearing rate limit state for terminal');
  clearRateLimitCallback(terminal.id);

  const projectPath = terminal.projectPath || terminal.cwd;
  console.warn('[ClaudeIntegration:switchClaudeProfile] Invoking Claude with profile:', profileId, '| cwd:', projectPath);
  debugLog('[ClaudeIntegration:switchClaudeProfile] Invoking Claude with new profile:', {
    terminalId: terminal.id,
    projectPath,
    profileId
  });
  invokeClaudeCallback(terminal.id, projectPath, profileId);

  debugLog('[ClaudeIntegration:switchClaudeProfile] Setting active profile in profile manager');
  profileManager.setActiveProfile(profileId);

  console.warn('[ClaudeIntegration:switchClaudeProfile] COMPLETE');
  debugLog('[ClaudeIntegration:switchClaudeProfile] ========== SWITCH PROFILE COMPLETE ==========');
  return { success: true };
}
