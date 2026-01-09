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
 * Azure Foundry uses 'api-key' header (not 'x-api-key')
 * See: https://platform.claude.com/docs/en/build-with-claude/claude-in-microsoft-foundry
 *
 * @param apiKey - Azure Foundry API key
 * @param baseUrl - Azure Foundry base URL (e.g., https://resource.services.ai.azure.com/anthropic)
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
  // Validate URL format - must be Azure Foundry endpoint
  const isAzureFoundry = trimmedUrl.includes('services.ai.azure.com') || trimmedUrl.includes('openai.azure.com');

  if (!isAzureFoundry) {
    return {
      success: false,
      message: 'Base URL should be an Azure Foundry endpoint (e.g., https://your-resource.services.ai.azure.com)',
    };
  }

  try {
    const startTime = Date.now();

    // Normalize URL to ensure it has the /anthropic path
    let normalizedUrl = trimmedUrl.replace(/\/$/, '');
    if (!normalizedUrl.includes('/anthropic')) {
      normalizedUrl = `${normalizedUrl}/anthropic`;
    }

    const url = new URL(normalizedUrl);

    // Use native https module to make a simple request to verify connectivity
    const result = await new Promise<ApiValidationResult>((resolve) => {
      const https = require('https');

      const options = {
        hostname: url.hostname,
        port: url.port || 443,
        path: `${url.pathname}/v1/messages`,
        method: 'POST',
        headers: {
          'x-api-key': apiKey.trim(), // Azure Foundry uses 'x-api-key' header
          'anthropic-version': '2023-06-01',
          'Content-Type': 'application/json',
        },
        timeout: 15000,
      };

      // Send a minimal request to verify connection
      const postData = JSON.stringify({
        model: 'claude-haiku-4-5', // Use Claude 4.5 model name for Azure Foundry
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

          // 200 = success
          if (res.statusCode === 200) {
            resolve({
              success: true,
              message: 'Azure Foundry connection successful',
              details: {
                provider: 'azure_foundry',
                latencyMs,
              },
            });
            return;
          }

          // 401/403 = invalid auth
          if (res.statusCode === 401 || res.statusCode === 403) {
            resolve({
              success: false,
              message: 'Authentication failed. Please check your API key.',
            });
            return;
          }

          // 429 = rate limited but auth works
          if (res.statusCode === 429) {
            resolve({
              success: true,
              message: 'Azure Foundry connection successful (rate limited)',
              details: {
                provider: 'azure_foundry',
                latencyMs,
              },
            });
            return;
          }

          // Parse error response for 400/404
          if (res.statusCode === 400 || res.statusCode === 404) {
            try {
              const errorData = JSON.parse(data);
              const errorType = errorData?.error?.type || '';
              const errorMessage = errorData?.error?.message || '';

              // Check for authentication errors in response
              if (errorType === 'authentication_error' || errorType === 'permission_error' ||
                  errorMessage.toLowerCase().includes('invalid api key') ||
                  errorMessage.toLowerCase().includes('unauthorized') ||
                  errorMessage.toLowerCase().includes('authentication')) {
                resolve({
                  success: false,
                  message: 'Authentication failed. Please check your API key.',
                });
                return;
              }

              // Model/deployment not found errors mean auth worked
              if (errorMessage.includes('model') || errorMessage.includes('deployment') ||
                  errorMessage.includes('not found') || errorMessage.includes('does not exist') ||
                  errorType === 'not_found_error') {
                resolve({
                  success: true,
                  message: 'Azure Foundry connection successful (deployment may need configuration)',
                  details: {
                    provider: 'azure_foundry',
                    latencyMs,
                  },
                });
                return;
              }

              // Input validation errors mean auth worked
              if (errorType === 'invalid_request_error') {
                resolve({
                  success: true,
                  message: 'Azure Foundry connection successful',
                  details: {
                    provider: 'azure_foundry',
                    latencyMs,
                  },
                });
                return;
              }

              // Unknown 400/404 error with an error message - report it
              if (errorMessage) {
                resolve({
                  success: false,
                  message: errorMessage,
                });
                return;
              }

              // Got a 400/404 with JSON but no message - likely auth worked but unknown issue
              resolve({
                success: true,
                message: 'Azure Foundry connection successful',
                details: {
                  provider: 'azure_foundry',
                  latencyMs,
                },
              });
            } catch {
              // JSON parse failed - endpoint was reached but returned non-JSON response
              // Since 401/403 would be returned for actual auth failures, assume auth worked
              resolve({
                success: true,
                message: 'Azure Foundry connection successful (endpoint reached)',
                details: {
                  provider: 'azure_foundry',
                  latencyMs,
                },
              });
            }
            return;
          }

          // Other status codes
          try {
            const errorData = JSON.parse(data);
            resolve({
              success: false,
              message: errorData?.error?.message || `Unexpected response: ${res.statusCode}`,
            });
          } catch {
            resolve({
              success: false,
              message: `Unexpected response: ${res.statusCode}`,
            });
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
