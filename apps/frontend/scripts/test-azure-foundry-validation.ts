#!/usr/bin/env npx tsx
/**
 * Test script for Azure Foundry validation
 *
 * Usage:
 *   npx tsx scripts/test-azure-foundry-validation.ts
 *
 * Environment variables:
 *   ANTHROPIC_FOUNDRY_API_KEY - Your Azure Foundry API key
 *   ANTHROPIC_FOUNDRY_BASE_URL - Your Azure Foundry base URL
 *
 * Example:
 *   ANTHROPIC_FOUNDRY_API_KEY=your-key ANTHROPIC_FOUNDRY_BASE_URL=https://your-resource.services.ai.azure.com npx tsx scripts/test-azure-foundry-validation.ts
 */

const apiKey = process.env.ANTHROPIC_FOUNDRY_API_KEY;
const baseUrl = process.env.ANTHROPIC_FOUNDRY_BASE_URL;

if (!apiKey || !baseUrl) {
  console.error('Missing required environment variables:');
  console.error('  ANTHROPIC_FOUNDRY_API_KEY - Your Azure Foundry API key');
  console.error('  ANTHROPIC_FOUNDRY_BASE_URL - Your Azure Foundry base URL');
  console.error('\nExample:');
  console.error('  ANTHROPIC_FOUNDRY_API_KEY=xxx ANTHROPIC_FOUNDRY_BASE_URL=https://your-resource.services.ai.azure.com npx tsx scripts/test-azure-foundry-validation.ts');
  process.exit(1);
}

console.log('Testing Azure Foundry validation...\n');
console.log('Configuration:');
console.log(`  Base URL: ${baseUrl}`);
console.log(`  API Key: ${apiKey.slice(0, 8)}...${apiKey.slice(-4)}`);
console.log('');

async function testValidation(): Promise<void> {
  // Normalize URL
  let normalizedUrl = baseUrl.replace(/\/$/, '');
  if (normalizedUrl.includes('services.ai.azure.com')) {
    const baseUrlPart = normalizedUrl.replace(/\/anthropic.*$/, '');
    normalizedUrl = `${baseUrlPart}/anthropic/v1/messages`;
  } else {
    if (!normalizedUrl.endsWith('/anthropic')) {
      normalizedUrl = `${normalizedUrl}/anthropic`;
    }
    normalizedUrl = `${normalizedUrl}/v1/messages`;
  }

  console.log(`Normalized URL: ${normalizedUrl}\n`);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    console.log('Making validation request...');
    console.log('  Method: POST');
    console.log('  Headers:');
    console.log('    api-key: [set]');
    console.log('    anthropic-version: 2023-06-01');
    console.log('    Content-Type: application/json');
    console.log('  Body:');
    console.log('    model: claude-haiku-4-5');
    console.log('    max_tokens: 1');
    console.log('    messages: [{ role: "user", content: "test" }]');
    console.log('');

    const response = await fetch(normalizedUrl, {
      method: 'POST',
      headers: {
        'api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5',
        max_tokens: 1,
        messages: [{ role: 'user', content: 'test' }]
      }),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    console.log(`Response Status: ${response.status} ${response.statusText}`);
    console.log('Response Headers:');
    response.headers.forEach((value, key) => {
      console.log(`  ${key}: ${value}`);
    });
    console.log('');

    const responseText = await response.text();
    console.log('Response Body:');
    try {
      const json = JSON.parse(responseText);
      console.log(JSON.stringify(json, null, 2));
    } catch {
      console.log(responseText || '(empty)');
    }
    console.log('');

    // Interpret result based on our validation logic
    console.log('=== VALIDATION RESULT ===\n');

    if (response.ok) {
      console.log('SUCCESS: Response OK (200)');
      console.log('Your Azure Foundry configuration is valid and working!');
      return;
    }

    if (response.status === 401) {
      console.log('FAILED: Invalid API key (401)');
      console.log('Please check your ANTHROPIC_FOUNDRY_API_KEY');
      return;
    }

    if (response.status === 403) {
      console.log('FAILED: Access denied (403)');
      console.log('Please check your API key permissions');
      return;
    }

    if (response.status === 429) {
      console.log('SUCCESS: Rate limited (429) - but credentials are valid!');
      return;
    }

    if (response.status === 400 || response.status === 404) {
      try {
        const errorData = JSON.parse(responseText);
        const errorType = errorData?.error?.type || '';
        const errorMessage = errorData?.error?.message || '';

        if (errorType === 'authentication_error' || errorType === 'permission_error') {
          console.log('FAILED: Authentication error in response body');
          console.log(`  Type: ${errorType}`);
          console.log(`  Message: ${errorMessage}`);
          return;
        }

        if (errorMessage.toLowerCase().includes('invalid api key') ||
            errorMessage.toLowerCase().includes('unauthorized') ||
            errorMessage.toLowerCase().includes('authentication failed')) {
          console.log('FAILED: Authentication failed');
          console.log(`  Message: ${errorMessage}`);
          return;
        }

        if (errorMessage.includes('model') || errorMessage.includes('deployment') ||
            errorMessage.includes('not found') || errorMessage.includes('does not exist') ||
            errorType === 'not_found_error') {
          console.log('SUCCESS: Model/deployment not found - but credentials are valid!');
          console.log('The claude-haiku-4-5 deployment may not exist, but auth works.');
          console.log('You may need to adjust the model name in your deployment.');
          return;
        }

        if (errorType === 'invalid_request_error') {
          console.log('SUCCESS: Invalid request error - but credentials are valid!');
          console.log('The endpoint is reachable and auth is working.');
          return;
        }

        if (errorMessage) {
          console.log(`FAILED: ${errorMessage}`);
          return;
        }

        console.log('SUCCESS: Got JSON response without error message - likely valid');
      } catch {
        console.log('SUCCESS: Non-JSON response but endpoint reached - likely valid');
        console.log('(401/403 would be returned for auth failures)');
      }
      return;
    }

    console.log(`UNCERTAIN: Unexpected status code ${response.status}`);
    console.log('Please check the response body above for more details.');

  } catch (error) {
    clearTimeout(timeoutId);
    console.log('ERROR:', error instanceof Error ? error.message : String(error));

    if (error instanceof Error && error.name === 'AbortError') {
      console.log('The request timed out after 15 seconds');
      console.log('Please check your Base URL and network connection');
    }
  }
}

testValidation().then(() => {
  console.log('\nDone.');
}).catch((err) => {
  console.error('Unexpected error:', err);
  process.exit(1);
});
