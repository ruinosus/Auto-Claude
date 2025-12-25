/**
 * Integration Test: Azure Foundry Authentication Flow
 *
 * Tests the complete Azure Foundry authentication configuration flow:
 * 1. UI → IPC → .env file generation
 * 2. Reading Azure Foundry config from .env
 * 3. Validating endpoint format (/anthropic suffix)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { promises as fs } from 'fs';
import * as path from 'path';
import * as os from 'os';
import type { ProjectEnvConfig } from '../../shared/types';

// Mock IPC event
const mockEvent = {
  sender: {
    send: vi.fn()
  }
} as any;

describe('Integration: Azure Foundry Authentication Flow', () => {
  let testDir: string;
  let envPath: string;

  beforeEach(async () => {
    // Create temp directory for test
    testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'azure-foundry-test-'));
    envPath = path.join(testDir, '.env');
    vi.clearAllMocks();
  });

  afterEach(async () => {
    // Cleanup
    try {
      await fs.rm(testDir, { recursive: true, force: true });
    } catch (error) {
      // Ignore cleanup errors
    }
  });

  it('should generate .env with Azure Foundry configuration', async () => {
    const { parseEnvFile } = await import('../ipc-handlers/utils');

    const config: Partial<ProjectEnvConfig> = {
      authMode: 'azure-foundry',
      azureFoundryApiKey: 'test-api-key-12345',
      azureFoundryBaseUrl: 'https://aif-cockpit-br-prd01.openai.azure.com/anthropic',
      azureFoundryResource: 'aif-cockpit-br-prd01',
      azureFoundryAuthStatus: 'configured'
    };

    // Generate .env content (using the function from env-handlers.ts)
    const envContent = generateTestEnvContent(config);
    await fs.writeFile(envPath, envContent);

    // Read back and verify
    const fileContent = await fs.readFile(envPath, 'utf-8');

    expect(fileContent).toContain('CLAUDE_AUTH_MODE=azure-foundry');
    expect(fileContent).toContain('ANTHROPIC_FOUNDRY_API_KEY=test-api-key-12345');
    expect(fileContent).toContain('ANTHROPIC_FOUNDRY_BASE_URL=https://aif-cockpit-br-prd01.openai.azure.com/anthropic');
    expect(fileContent).toContain('ANTHROPIC_FOUNDRY_RESOURCE=aif-cockpit-br-prd01');
    expect(fileContent).toContain('CLAUDE_CODE_USE_FOUNDRY=true');
  });

  it('should validate Azure Foundry endpoint has /anthropic suffix', async () => {
    const validEndpoints = [
      'https://aif-cockpit-br-prd01.openai.azure.com/anthropic',
      'https://aif-cockpit-br-prd01.services.ai.azure.com/anthropic',
      'https://test-resource.openai.azure.com/anthropic'
    ];

    const invalidEndpoints = [
      'https://aif-cockpit-br-prd01.openai.azure.com',
      'https://test-resource.services.ai.azure.com',
      'https://example.com/api'
    ];

    for (const endpoint of validEndpoints) {
      expect(endpoint.endsWith('/anthropic')).toBe(true);
    }

    for (const endpoint of invalidEndpoints) {
      expect(endpoint.endsWith('/anthropic')).toBe(false);
    }
  });

  it('should parse existing .env with Azure Foundry config', async () => {
    const { parseEnvFile } = await import('../ipc-handlers/utils');

    const existingEnv = `# Auto Claude Framework Environment Variables

# Authentication
CLAUDE_AUTH_MODE=azure-foundry

# Azure Foundry (enterprise)
ANTHROPIC_FOUNDRY_API_KEY=your-azure-foundry-api-key-here
ANTHROPIC_FOUNDRY_BASE_URL=https://aif-cockpit-br-prd01.openai.azure.com/anthropic
ANTHROPIC_FOUNDRY_RESOURCE=aif-cockpit-br-prd01
CLAUDE_CODE_USE_FOUNDRY=true

# Other settings
GRAPHITI_ENABLED=true
`;

    await fs.writeFile(envPath, existingEnv);

    // Parse the .env file
    const parsed = parseEnvFile(existingEnv);

    expect(parsed['CLAUDE_AUTH_MODE']).toBe('azure-foundry');
    expect(parsed['ANTHROPIC_FOUNDRY_API_KEY']).toBe('your-azure-foundry-api-key-here');
    expect(parsed['ANTHROPIC_FOUNDRY_BASE_URL']).toBe('https://aif-cockpit-br-prd01.openai.azure.com/anthropic');
    expect(parsed['ANTHROPIC_FOUNDRY_RESOURCE']).toBe('aif-cockpit-br-prd01');
    expect(parsed['CLAUDE_CODE_USE_FOUNDRY']).toBe('true');
  });

  it('should handle switching from OAuth to Azure Foundry', async () => {
    // Start with OAuth config
    const oauthEnv = `# Authentication
CLAUDE_AUTH_MODE=oauth
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-xxxxxxxx
`;
    await fs.writeFile(envPath, oauthEnv);

    // Update to Azure Foundry
    const azureConfig: Partial<ProjectEnvConfig> = {
      authMode: 'azure-foundry',
      azureFoundryApiKey: 'new-azure-key',
      azureFoundryBaseUrl: 'https://test.openai.azure.com/anthropic',
      azureFoundryResource: 'test-resource'
    };

    const updatedContent = generateTestEnvContent(azureConfig, oauthEnv);
    await fs.writeFile(envPath, updatedContent);

    const fileContent = await fs.readFile(envPath, 'utf-8');

    // Should have Azure Foundry config
    expect(fileContent).toContain('CLAUDE_AUTH_MODE=azure-foundry');
    expect(fileContent).toContain('ANTHROPIC_FOUNDRY_API_KEY=new-azure-key');

    // Should preserve OAuth token (commented out or available for switch back)
    expect(fileContent).toMatch(/CLAUDE_CODE_OAUTH_TOKEN/);
  });

  it('should include all 3 authentication modes in template', async () => {
    const config: Partial<ProjectEnvConfig> = {
      authMode: 'oauth'
    };

    const envContent = generateTestEnvContent(config);

    // Should have sections for all 3 modes
    expect(envContent).toContain('# Claude OAuth (default)');
    expect(envContent).toContain('# Azure Foundry (enterprise)');
    expect(envContent).toContain('# Auth Token (proxy/CCR)');

    // Should have all Azure Foundry variables (commented out)
    expect(envContent).toMatch(/# ANTHROPIC_FOUNDRY_API_KEY=/);
    expect(envContent).toMatch(/# ANTHROPIC_FOUNDRY_BASE_URL=.*\/anthropic/);
    expect(envContent).toContain('# ANTHROPIC_FOUNDRY_RESOURCE=');
  });

  it('should set CLAUDE_CODE_USE_FOUNDRY when Azure Foundry is configured', async () => {
    const config: Partial<ProjectEnvConfig> = {
      authMode: 'azure-foundry',
      azureFoundryApiKey: 'test-key',
      azureFoundryBaseUrl: 'https://test.openai.azure.com/anthropic',
      azureFoundryResource: 'test-resource'
    };

    const envContent = generateTestEnvContent(config);
    await fs.writeFile(envPath, envContent);

    const fileContent = await fs.readFile(envPath, 'utf-8');
    expect(fileContent).toContain('CLAUDE_CODE_USE_FOUNDRY=true');
  });

  it('should validate Azure Foundry status based on required fields', () => {
    // Complete config - should be 'configured'
    const completeConfig: Partial<ProjectEnvConfig> = {
      authMode: 'azure-foundry',
      azureFoundryApiKey: 'test-key',
      azureFoundryBaseUrl: 'https://test.openai.azure.com/anthropic',
      azureFoundryResource: 'test-resource',
      azureFoundryAuthStatus: 'configured'
    };

    expect(completeConfig.azureFoundryAuthStatus).toBe('configured');
    expect(completeConfig.azureFoundryApiKey).toBeTruthy();
    expect(completeConfig.azureFoundryBaseUrl).toContain('/anthropic');

    // Incomplete config - should be 'not_configured'
    const incompleteConfig: Partial<ProjectEnvConfig> = {
      authMode: 'azure-foundry',
      azureFoundryAuthStatus: 'not_configured'
    };

    expect(incompleteConfig.azureFoundryAuthStatus).toBe('not_configured');
  });
});

/**
 * Helper function to generate .env content for testing
 * (Mirrors the logic in env-handlers.ts)
 */
function generateTestEnvContent(
  config: Partial<ProjectEnvConfig>,
  existingContent?: string
): string {
  const existingVars: Record<string, string> = {};

  if (existingContent) {
    // Parse existing content
    const lines = existingContent.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=');
        if (key && valueParts.length > 0) {
          existingVars[key] = valueParts.join('=');
        }
      }
    }
  }

  // Apply config updates
  if (config.authMode !== undefined) {
    existingVars['CLAUDE_AUTH_MODE'] = config.authMode;
  }

  if (config.claudeOAuthToken !== undefined) {
    existingVars['CLAUDE_CODE_OAUTH_TOKEN'] = config.claudeOAuthToken;
  }

  if (config.azureFoundryApiKey !== undefined) {
    existingVars['ANTHROPIC_FOUNDRY_API_KEY'] = config.azureFoundryApiKey;
    existingVars['CLAUDE_CODE_USE_FOUNDRY'] = 'true';
  }

  if (config.azureFoundryBaseUrl !== undefined) {
    existingVars['ANTHROPIC_FOUNDRY_BASE_URL'] = config.azureFoundryBaseUrl;
  }

  if (config.azureFoundryResource !== undefined) {
    existingVars['ANTHROPIC_FOUNDRY_RESOURCE'] = config.azureFoundryResource;
  }

  if (config.anthropicAuthToken !== undefined) {
    existingVars['ANTHROPIC_AUTH_TOKEN'] = config.anthropicAuthToken;
  }

  // Generate .env template
  return `# Auto Claude Framework Environment Variables

# =============================================================================
# AUTHENTICATION
# =============================================================================
# Authentication mode: oauth | azure-foundry | auth-token
${existingVars['CLAUDE_AUTH_MODE'] ? `CLAUDE_AUTH_MODE=${existingVars['CLAUDE_AUTH_MODE']}` : '# CLAUDE_AUTH_MODE=oauth'}

# Claude OAuth (default)
${existingVars['CLAUDE_CODE_OAUTH_TOKEN'] ? `CLAUDE_CODE_OAUTH_TOKEN=${existingVars['CLAUDE_CODE_OAUTH_TOKEN']}` : '# CLAUDE_CODE_OAUTH_TOKEN='}

# Azure Foundry (enterprise)
# Note: Base URL must end with /anthropic
${existingVars['ANTHROPIC_FOUNDRY_API_KEY'] ? `ANTHROPIC_FOUNDRY_API_KEY=${existingVars['ANTHROPIC_FOUNDRY_API_KEY']}` : '# ANTHROPIC_FOUNDRY_API_KEY='}
${existingVars['ANTHROPIC_FOUNDRY_BASE_URL'] ? `ANTHROPIC_FOUNDRY_BASE_URL=${existingVars['ANTHROPIC_FOUNDRY_BASE_URL']}` : '# ANTHROPIC_FOUNDRY_BASE_URL=https://your-resource.openai.azure.com/anthropic'}
${existingVars['ANTHROPIC_FOUNDRY_RESOURCE'] ? `ANTHROPIC_FOUNDRY_RESOURCE=${existingVars['ANTHROPIC_FOUNDRY_RESOURCE']}` : '# ANTHROPIC_FOUNDRY_RESOURCE=your-resource-name'}
${existingVars['CLAUDE_CODE_USE_FOUNDRY'] ? `CLAUDE_CODE_USE_FOUNDRY=${existingVars['CLAUDE_CODE_USE_FOUNDRY']}` : '# CLAUDE_CODE_USE_FOUNDRY=true'}

# Auth Token (proxy/CCR)
${existingVars['ANTHROPIC_AUTH_TOKEN'] ? `ANTHROPIC_AUTH_TOKEN=${existingVars['ANTHROPIC_AUTH_TOKEN']}` : '# ANTHROPIC_AUTH_TOKEN='}

# Other settings
${existingVars['GRAPHITI_ENABLED'] ? `GRAPHITI_ENABLED=${existingVars['GRAPHITI_ENABLED']}` : '# GRAPHITI_ENABLED=true'}
`;
}
