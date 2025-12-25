/**
 * Unit Test: env-handlers Azure Foundry support
 *
 * Tests the env-handlers IPC logic for reading/writing Azure Foundry configuration
 */

import { describe, it, expect } from 'vitest';
import { parseEnvFile } from '../ipc-handlers/utils';

describe('env-handlers: Azure Foundry Support', () => {
  describe('parseEnvFile', () => {
    it('should parse Azure Foundry variables from .env content', () => {
      const envContent = `# Auto Claude Framework

# Authentication
CLAUDE_AUTH_MODE=azure-foundry

# Azure Foundry
ANTHROPIC_FOUNDRY_API_KEY=your-azure-foundry-api-key-here
ANTHROPIC_FOUNDRY_BASE_URL=https://aif-cockpit-br-prd01.openai.azure.com/anthropic
ANTHROPIC_FOUNDRY_RESOURCE=aif-cockpit-br-prd01
CLAUDE_CODE_USE_FOUNDRY=true
`;

      const parsed = parseEnvFile(envContent);

      expect(parsed).toEqual({
        CLAUDE_AUTH_MODE: 'azure-foundry',
        ANTHROPIC_FOUNDRY_API_KEY: 'your-azure-foundry-api-key-here',
        ANTHROPIC_FOUNDRY_BASE_URL: 'https://aif-cockpit-br-prd01.openai.azure.com/anthropic',
        ANTHROPIC_FOUNDRY_RESOURCE: 'aif-cockpit-br-prd01',
        CLAUDE_CODE_USE_FOUNDRY: 'true'
      });
    });

    it('should handle Azure Foundry with services.ai.azure.com endpoint', () => {
      const envContent = `ANTHROPIC_FOUNDRY_BASE_URL=https://aif-cockpit-br-prd01.services.ai.azure.com/anthropic`;

      const parsed = parseEnvFile(envContent);

      expect(parsed['ANTHROPIC_FOUNDRY_BASE_URL']).toBe('https://aif-cockpit-br-prd01.services.ai.azure.com/anthropic');
      expect(parsed['ANTHROPIC_FOUNDRY_BASE_URL']).toContain('/anthropic');
    });

    it('should handle quoted values', () => {
      const envContent = `ANTHROPIC_FOUNDRY_BASE_URL="https://test.openai.azure.com/anthropic"
ANTHROPIC_FOUNDRY_RESOURCE='test-resource'`;

      const parsed = parseEnvFile(envContent);

      expect(parsed['ANTHROPIC_FOUNDRY_BASE_URL']).toBe('https://test.openai.azure.com/anthropic');
      expect(parsed['ANTHROPIC_FOUNDRY_RESOURCE']).toBe('test-resource');
    });

    it('should skip comments and empty lines', () => {
      const envContent = `# This is a comment
# ANTHROPIC_FOUNDRY_API_KEY=commented-out

CLAUDE_AUTH_MODE=azure-foundry

# Another comment
ANTHROPIC_FOUNDRY_RESOURCE=real-resource
`;

      const parsed = parseEnvFile(envContent);

      expect(parsed['ANTHROPIC_FOUNDRY_API_KEY']).toBeUndefined();
      expect(parsed['CLAUDE_AUTH_MODE']).toBe('azure-foundry');
      expect(parsed['ANTHROPIC_FOUNDRY_RESOURCE']).toBe('real-resource');
    });

    it('should handle all three authentication modes', () => {
      const oauthEnv = `CLAUDE_AUTH_MODE=oauth
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-xxx`;

      const azureEnv = `CLAUDE_AUTH_MODE=azure-foundry
ANTHROPIC_FOUNDRY_API_KEY=azure-key-xxx
ANTHROPIC_FOUNDRY_BASE_URL=https://test.openai.azure.com/anthropic
ANTHROPIC_FOUNDRY_RESOURCE=test-resource`;

      const authTokenEnv = `CLAUDE_AUTH_MODE=auth-token
ANTHROPIC_AUTH_TOKEN=sk-zcf-x-ccr`;

      const oauthParsed = parseEnvFile(oauthEnv);
      expect(oauthParsed['CLAUDE_AUTH_MODE']).toBe('oauth');
      expect(oauthParsed['CLAUDE_CODE_OAUTH_TOKEN']).toBeTruthy();

      const azureParsed = parseEnvFile(azureEnv);
      expect(azureParsed['CLAUDE_AUTH_MODE']).toBe('azure-foundry');
      expect(azureParsed['ANTHROPIC_FOUNDRY_API_KEY']).toBeTruthy();
      expect(azureParsed['ANTHROPIC_FOUNDRY_BASE_URL']).toContain('/anthropic');

      const authTokenParsed = parseEnvFile(authTokenEnv);
      expect(authTokenParsed['CLAUDE_AUTH_MODE']).toBe('auth-token');
      expect(authTokenParsed['ANTHROPIC_AUTH_TOKEN']).toBeTruthy();
    });

    it('should handle malformed lines gracefully', () => {
      const envContent = `VALID_KEY=valid_value
NO_EQUALS_SIGN
=NO_KEY
ANOTHER_VALID=value
EMPTY_VALUE=
`;

      const parsed = parseEnvFile(envContent);

      expect(parsed['VALID_KEY']).toBe('valid_value');
      expect(parsed['ANOTHER_VALID']).toBe('value');
      expect(parsed['EMPTY_VALUE']).toBe('');
      expect(parsed['NO_EQUALS_SIGN']).toBeUndefined();
      expect(parsed['']).toBeUndefined();
    });

    it('should preserve complex URLs with query parameters', () => {
      const envContent = `ANTHROPIC_FOUNDRY_BASE_URL=https://test.openai.azure.com/anthropic?api-version=2023-06-01`;

      const parsed = parseEnvFile(envContent);

      expect(parsed['ANTHROPIC_FOUNDRY_BASE_URL']).toBe('https://test.openai.azure.com/anthropic?api-version=2023-06-01');
    });

    it('should handle values with = signs in them', () => {
      const envContent = `ANTHROPIC_FOUNDRY_API_KEY=key=with=equals=signs`;

      const parsed = parseEnvFile(envContent);

      expect(parsed['ANTHROPIC_FOUNDRY_API_KEY']).toBe('key=with=equals=signs');
    });
  });

  describe('Azure Foundry endpoint validation', () => {
    it('should validate correct Azure Foundry endpoint patterns', () => {
      const validPatterns = [
        'https://aif-cockpit-br-prd01.openai.azure.com/anthropic',
        'https://aif-cockpit-br-prd01.services.ai.azure.com/anthropic',
        'https://test-resource.openai.azure.com/anthropic',
        'https://my-resource-name.openai.azure.com/anthropic'
      ];

      for (const pattern of validPatterns) {
        expect(pattern).toMatch(/https:\/\/[^\/]+\.(openai\.azure\.com|services\.ai\.azure\.com)\/anthropic/);
        expect(pattern.endsWith('/anthropic')).toBe(true);
      }
    });

    it('should identify incorrect endpoint patterns', () => {
      const invalidPatterns = [
        { url: 'https://aif-cockpit-br-prd01.openai.azure.com', reason: 'Missing /anthropic' },
        { url: 'https://test.services.ai.azure.com', reason: 'Missing /anthropic' },
        { url: 'https://example.com/anthropic', reason: 'Wrong domain' },
        { url: 'http://test.openai.azure.com/anthropic', reason: 'HTTP instead of HTTPS' },
        { url: 'https://test.openai.azure.com/claude', reason: 'Wrong path' }
      ];

      for (const { url, reason } of invalidPatterns) {
        const isValidAzureFoundry =
          url.startsWith('https://') &&
          (url.includes('.openai.azure.com/anthropic') ||
           url.includes('.services.ai.azure.com/anthropic'));

        expect(isValidAzureFoundry).toBe(false);
      }
    });
  });
});
