/**
 * API Validation Service
 *
 * Provides validation for external LLM API providers (OpenAI, Anthropic, Google, etc.)
 * Used by the Graphiti memory integration for embedding and LLM operations.
 */

export interface ApiValidationResult {
  success: boolean;
  message: string;
  details?: {
    provider?: string;
    model?: string;
    latencyMs?: number;
  };
}

/**
 * Validate OpenAI API key by attempting to list models
 * @param apiKey - OpenAI API key
 */
export async function validateOpenAIApiKey(
  apiKey: string
): Promise<ApiValidationResult> {
  if (!apiKey || !apiKey.trim()) {
    return {
      success: false,
      message: 'API key is required',
    };
  }

  // Basic format validation
  const trimmedKey = apiKey.trim();
  if (!trimmedKey.startsWith('sk-') && !trimmedKey.startsWith('sess-')) {
    return {
      success: false,
      message: 'Invalid API key format. OpenAI API keys should start with "sk-" or "sess-"',
    };
  }

  try {
    const startTime = Date.now();

    // Use native https module to avoid additional dependencies
    const result = await new Promise<ApiValidationResult>((resolve) => {
      const https = require('https');

      const options = {
        hostname: 'api.openai.com',
        port: 443,
        path: '/v1/models',
        method: 'GET',
        headers: {
          Authorization: `Bearer ${trimmedKey}`,
          'Content-Type': 'application/json',
        },
        timeout: 15000,
      };

      const req = https.request(options, (res: { statusCode: number; on: (event: string, callback: (chunk: Buffer) => void) => void }) => {
        let data = '';

        res.on('data', (chunk: Buffer) => {
          data += chunk;
        });

        res.on('end', () => {
          const latencyMs = Date.now() - startTime;

          if (res.statusCode === 200) {
            resolve({
              success: true,
              message: 'OpenAI API key is valid',
              details: {
                provider: 'openai',
                latencyMs,
              },
            });
          } else if (res.statusCode === 401) {
            resolve({
              success: false,
              message: 'Invalid API key. Please check your OpenAI API key.',
            });
          } else if (res.statusCode === 429) {
            // Rate limited but key is valid
            resolve({
              success: true,
              message: 'OpenAI API key is valid (rate limited, please wait)',
              details: {
                provider: 'openai',
                latencyMs,
              },
            });
          } else {
            try {
              const errorData = JSON.parse(data);
              resolve({
                success: false,
                message: errorData.error?.message || `API error: ${res.statusCode}`,
              });
            } catch {
              resolve({
                success: false,
                message: `API error: ${res.statusCode}`,
              });
            }
          }
        });
      });

      req.on('error', (error: Error) => {
        resolve({
          success: false,
          message: `Connection error: ${error.message}`,
        });
      });

      req.on('timeout', () => {
        req.destroy();
        resolve({
          success: false,
          message: 'Connection timeout. Please check your network connection.',
        });
      });

      req.end();
    });

    return result;
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
}

/**
 * Validate Anthropic API key
 * @param apiKey - Anthropic API key
 */
export async function validateAnthropicApiKey(
  apiKey: string
): Promise<ApiValidationResult> {
  if (!apiKey || !apiKey.trim()) {
    return {
      success: false,
      message: 'API key is required',
    };
  }

  const trimmedKey = apiKey.trim();
  if (!trimmedKey.startsWith('sk-ant-')) {
    return {
      success: false,
      message: 'Invalid API key format. Anthropic API keys should start with "sk-ant-"',
    };
  }

  // For now, just validate format - full validation would require an API call
  return {
    success: true,
    message: 'Anthropic API key format is valid',
    details: {
      provider: 'anthropic',
    },
  };
}

/**
 * Validate Google AI API key
 * @param apiKey - Google AI API key
 */
export async function validateGoogleApiKey(
  apiKey: string
): Promise<ApiValidationResult> {
  if (!apiKey || !apiKey.trim()) {
    return {
      success: false,
      message: 'API key is required',
    };
  }

  const trimmedKey = apiKey.trim();
  if (!trimmedKey.startsWith('AIza')) {
    return {
      success: false,
      message: 'Invalid API key format. Google AI API keys should start with "AIza"',
    };
  }

  return {
    success: true,
    message: 'Google AI API key format is valid',
    details: {
      provider: 'google',
    },
  };
}

/**
 * Validate an LLM provider API key based on provider type
 * @param provider - The LLM provider (openai, anthropic, google, etc.)
 * @param apiKey - The API key to validate
 */
export async function validateLLMApiKey(
  provider: string,
  apiKey: string
): Promise<ApiValidationResult> {
  switch (provider) {
    case 'openai':
      return validateOpenAIApiKey(apiKey);
    case 'anthropic':
      return validateAnthropicApiKey(apiKey);
    case 'google':
      return validateGoogleApiKey(apiKey);
    case 'ollama':
      // Ollama is local, no API key needed
      return {
        success: true,
        message: 'Ollama runs locally, no API key required',
        details: { provider: 'ollama' },
      };
    case 'azure_openai':
      // Azure OpenAI uses different auth, just validate presence
      if (!apiKey || !apiKey.trim()) {
        return {
          success: false,
          message: 'Azure OpenAI API key is required',
        };
      }
      return {
        success: true,
        message: 'Azure OpenAI API key format accepted',
        details: { provider: 'azure_openai' },
      };
    default:
      return {
        success: false,
        message: `Unknown provider: ${provider}`,
      };
  }
}

/**
 * Validate Azure Foundry connection
 * @param apiKey - Azure Foundry API key
 * @param baseUrl - Azure Foundry base URL (must end with /anthropic)
 */
export async function validateAzureFoundryConnection(
  apiKey: string,
  baseUrl: string
): Promise<ApiValidationResult> {
  if (!apiKey || !apiKey.trim()) {
    return {
      success: false,
      message: 'API key is required',
    };
  }

  if (!baseUrl || !baseUrl.trim()) {
    return {
      success: false,
      message: 'Base URL is required',
    };
  }

  const trimmedUrl = baseUrl.trim();
  if (!trimmedUrl.endsWith('/anthropic')) {
    return {
      success: false,
      message: 'Base URL must end with /anthropic',
    };
  }

  try {
    const startTime = Date.now();
    const url = new URL(trimmedUrl);

    // Use native https module to make a simple request to verify connectivity
    const result = await new Promise<ApiValidationResult>((resolve) => {
      const https = require('https');

      const options = {
        hostname: url.hostname,
        port: url.port || 443,
        path: `${url.pathname}/v1/messages`,
        method: 'POST',
        headers: {
          'x-api-key': apiKey.trim(),
          'anthropic-version': '2023-06-01',
          'Content-Type': 'application/json',
        },
        timeout: 15000,
      };

      // Send a minimal request that should fail with a validation error
      // but proves the credentials work
      const postData = JSON.stringify({
        model: 'claude-3-5-sonnet-20241022',
        max_tokens: 1,
        messages: [{ role: 'user', content: 'test' }]
      });

      const req = https.request(options, (res: { statusCode: number; on: (event: string, callback: (chunk: Buffer) => void) => void }) => {
        let data = '';

        res.on('data', (chunk: Buffer) => {
          data += chunk;
        });

        res.on('end', () => {
          const latencyMs = Date.now() - startTime;

          // 200 = success, 401 = invalid auth, other = likely valid auth but other issue
          if (res.statusCode === 200) {
            resolve({
              success: true,
              message: 'Azure Foundry connection successful',
              details: {
                provider: 'azure_foundry',
                latencyMs,
              },
            });
          } else if (res.statusCode === 401 || res.statusCode === 403) {
            resolve({
              success: false,
              message: 'Authentication failed. Please check your API key.',
            });
          } else if (res.statusCode === 400) {
            // 400 Bad Request likely means auth worked but request was malformed
            // This is actually success for connection testing
            resolve({
              success: true,
              message: 'Azure Foundry connection successful (auth validated)',
              details: {
                provider: 'azure_foundry',
                latencyMs,
              },
            });
          } else if (res.statusCode === 429) {
            // Rate limited but connection works
            resolve({
              success: true,
              message: 'Azure Foundry connection successful (rate limited)',
              details: {
                provider: 'azure_foundry',
                latencyMs,
              },
            });
          } else {
            try {
              const errorData = JSON.parse(data);
              // Check if it's an auth error vs other error
              if (errorData.error?.type === 'authentication_error') {
                resolve({
                  success: false,
                  message: 'Authentication failed. Please check your API key.',
                });
              } else {
                // Other errors likely mean auth worked
                resolve({
                  success: true,
                  message: 'Azure Foundry connection successful',
                  details: {
                    provider: 'azure_foundry',
                    latencyMs,
                  },
                });
              }
            } catch {
              resolve({
                success: false,
                message: `Unexpected response: ${res.statusCode}`,
              });
            }
          }
        });
      });

      req.on('error', (error: Error) => {
        resolve({
          success: false,
          message: `Connection error: ${error.message}`,
        });
      });

      req.on('timeout', () => {
        req.destroy();
        resolve({
          success: false,
          message: 'Connection timeout. Please check your Base URL and network connection.',
        });
      });

      req.write(postData);
      req.end();
    });

    return result;
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Invalid URL format',
    };
  }
}
