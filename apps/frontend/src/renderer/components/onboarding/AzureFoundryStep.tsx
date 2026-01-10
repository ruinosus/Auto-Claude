import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Cloud,
  Eye,
  EyeOff,
  Info,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  ExternalLink
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Card, CardContent } from '../ui/card';

interface AzureFoundryStepProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

interface AzureConfig {
  apiKey: string;
  // IMPORTANT: resourceName OR baseUrl - they are mutually exclusive!
  // If resourceName is provided, SDK constructs the URL automatically
  // If baseUrl is provided, it's used directly (for custom endpoints)
  resourceName: string;
  baseUrl: string;
  // Model deployment names in Azure Foundry
  sonnetModel: string;
  haikuModel: string;
  opusModel: string;
}

/**
 * Azure Foundry configuration step for the onboarding wizard.
 * Collects Azure OpenAI credentials for Anthropic model access.
 */
export function AzureFoundryStep({ onNext, onBack, onSkip }: AzureFoundryStepProps) {
  const { t } = useTranslation('onboarding');

  const [config, setConfig] = useState<AzureConfig>({
    apiKey: '',
    baseUrl: '',
    resourceName: '',
    sonnetModel: 'claude-sonnet-4-5',
    haikuModel: 'claude-haiku-4-5',
    opusModel: 'claude-opus-4-5'
  });
  const [showApiKey, setShowApiKey] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isValid, setIsValid] = useState(false);

  // Config is complete if we have API key AND (Resource Name OR Base URL)
  // Resource Name and Base URL are mutually exclusive - SDK uses one or the other
  const hasEndpoint = config.resourceName.trim() || config.baseUrl.trim();
  const isConfigComplete = config.apiKey.trim() && hasEndpoint;

  const handleChange = (field: keyof AzureConfig, value: string) => {
    setConfig(prev => ({ ...prev, [field]: value }));
    setIsValid(false);
    setError(null);
  };

  const handleValidate = async () => {
    if (!isConfigComplete) return;

    setIsValidating(true);
    setError(null);

    try {
      const resourceName = config.resourceName.trim();
      const baseUrl = config.baseUrl.trim();

      // If Resource Name is provided, construct the URL for validation
      // If Base URL is provided directly, validate it
      let urlToValidate = baseUrl;

      if (resourceName && !baseUrl) {
        // Construct URL from Resource Name (SDK format)
        urlToValidate = `https://${resourceName}.services.ai.azure.com/anthropic`;
      } else if (baseUrl) {
        // Validate the provided URL format
        const isAzureFoundry = baseUrl.includes('services.ai.azure.com') || baseUrl.includes('openai.azure.com');
        if (!isAzureFoundry) {
          setError('Base URL should be an Azure Foundry endpoint (e.g., https://your-resource.services.ai.azure.com)');
          setIsValidating(false);
          return;
        }
      }

      // Call validation API - the handler will normalize the URL
      const result = await window.electronAPI.validateAzureFoundryConfig({
        apiKey: config.apiKey.trim(),
        baseUrl: urlToValidate,
        resourceName: resourceName || undefined
      });

      if (result.success) {
        setIsValid(true);
      } else {
        setError(result.error || 'Validation failed. Please check your credentials.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validation failed');
    } finally {
      setIsValidating(false);
    }
  };

  const handleContinue = async () => {
    if (!isConfigComplete) return;

    setIsSaving(true);
    setError(null);

    try {
      const resourceName = config.resourceName.trim();
      const baseUrl = config.baseUrl.trim();

      // IMPORTANT: Resource Name and Base URL are mutually exclusive!
      // If Resource Name is provided, SDK constructs the URL automatically
      // If only Base URL is provided, use it directly
      let normalizedBaseUrl: string | undefined;

      if (!resourceName && baseUrl) {
        // Only set Base URL if Resource Name is NOT provided
        normalizedBaseUrl = baseUrl.replace(/\/$/, '');
        if (!normalizedBaseUrl.endsWith('/anthropic')) {
          normalizedBaseUrl = `${normalizedBaseUrl}/anthropic`;
        }
      }
      // If Resource Name is provided, don't set Base URL - SDK will construct it

      // Save to global settings
      const result = await window.electronAPI.saveSettings({
        azureFoundryApiKey: config.apiKey.trim(),
        // Only set one of these - they are mutually exclusive
        azureFoundryResourceName: resourceName || undefined,
        azureFoundryBaseUrl: normalizedBaseUrl,
        // Model deployment names
        azureFoundrySonnetModel: config.sonnetModel.trim() || undefined,
        azureFoundryHaikuModel: config.haikuModel.trim() || undefined,
        azureFoundryOpusModel: config.opusModel.trim() || undefined,
        defaultAuthMode: 'azure-foundry'
      });

      if (result?.success) {
        onNext();
      } else {
        setError(result?.error || 'Failed to save configuration');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex h-full flex-col items-center justify-center px-8 py-6">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-blue-500/10 text-blue-500">
              <Cloud className="h-7 w-7" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">
            Configure Azure Foundry
          </h1>
          <p className="mt-2 text-muted-foreground">
            Enter your Azure OpenAI credentials for Anthropic model access
          </p>
        </div>

        <div className="space-y-6">
          {/* Info card */}
          <Card className="border border-info/30 bg-info/10">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <Info className="h-5 w-5 text-info shrink-0 mt-0.5" />
                <div className="text-sm text-muted-foreground">
                  <p>
                    Azure Foundry provides access to Claude models through Azure OpenAI Service.
                    You'll need your Azure OpenAI endpoint and API key.
                  </p>
                  <a
                    href="https://learn.microsoft.com/en-us/azure/ai-services/openai/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-info hover:underline mt-2"
                  >
                    Learn more about Azure OpenAI
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Error banner */}
          {error && (
            <Card className="border border-destructive/30 bg-destructive/10">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                  <p className="text-sm text-destructive">{error}</p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Configuration form */}
          <div className="space-y-4">
            {/* API Key */}
            <div className="space-y-2">
              <Label htmlFor="apiKey">API Key *</Label>
              <div className="relative">
                <Input
                  id="apiKey"
                  type={showApiKey ? 'text' : 'password'}
                  placeholder="Enter your Azure AI Foundry API key"
                  value={config.apiKey}
                  onChange={(e) => handleChange('apiKey', e.target.value)}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Resource Name (Recommended) */}
            <div className="space-y-2">
              <Label htmlFor="resourceName">Resource Name * (Recommended)</Label>
              <Input
                id="resourceName"
                type="text"
                placeholder="aif-your-resource-name"
                value={config.resourceName}
                onChange={(e) => handleChange('resourceName', e.target.value)}
                disabled={!!config.baseUrl.trim()}
              />
              <p className="text-xs text-muted-foreground">
                The name of your Azure AI Foundry resource. The SDK will automatically construct the endpoint URL.
                Example: <code className="bg-muted px-1 rounded">aif-cockpit-br-prd01</code>
              </p>
            </div>

            {/* Divider with OR */}
            <div className="flex items-center gap-4 py-2">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs text-muted-foreground uppercase">or</span>
              <div className="h-px flex-1 bg-border" />
            </div>

            {/* Base URL (Advanced) */}
            <div className="space-y-2">
              <Label htmlFor="baseUrl" className="text-muted-foreground">Base URL (Advanced)</Label>
              <Input
                id="baseUrl"
                type="text"
                placeholder="https://your-resource.services.ai.azure.com"
                value={config.baseUrl}
                onChange={(e) => handleChange('baseUrl', e.target.value)}
                disabled={!!config.resourceName.trim()}
                className={config.resourceName.trim() ? 'opacity-50' : ''}
              />
              <p className="text-xs text-muted-foreground">
                Only use if you need a custom endpoint. The <code className="bg-muted px-1 rounded">/anthropic</code> suffix will be added automatically.
              </p>
            </div>

            {/* Model Deployment Names */}
            <div className="space-y-4 pt-4 border-t border-border">
              <div>
                <h3 className="text-sm font-medium text-foreground mb-1">Model Deployment Names</h3>
                <p className="text-xs text-muted-foreground">
                  Map your Azure Foundry deployment names to Claude models. These are the names you created when deploying the models in Azure.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="sonnetModel">Sonnet</Label>
                  <Input
                    id="sonnetModel"
                    type="text"
                    placeholder="claude-sonnet-4-5"
                    value={config.sonnetModel}
                    onChange={(e) => handleChange('sonnetModel', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="haikuModel">Haiku</Label>
                  <Input
                    id="haikuModel"
                    type="text"
                    placeholder="claude-haiku-4-5"
                    value={config.haikuModel}
                    onChange={(e) => handleChange('haikuModel', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="opusModel">Opus</Label>
                  <Input
                    id="opusModel"
                    type="text"
                    placeholder="claude-opus-4-5"
                    value={config.opusModel}
                    onChange={(e) => handleChange('opusModel', e.target.value)}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Validation button */}
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={handleValidate}
              disabled={!isConfigComplete || isValidating}
              className="gap-2"
            >
              {isValidating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : isValid ? (
                <CheckCircle2 className="h-4 w-4 text-success" />
              ) : null}
              {isValid ? 'Validated' : 'Validate Connection'}
            </Button>
            {isValid && (
              <span className="text-sm text-success flex items-center gap-1">
                <CheckCircle2 className="h-4 w-4" />
                Connection successful
              </span>
            )}
          </div>

          {/* Success state */}
          {isValid && (
            <Card className="border border-success/30 bg-success/10">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-success shrink-0 mt-0.5" />
                  <p className="text-sm text-success">
                    Azure Foundry configuration validated. You can now continue.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between items-center mt-10 pt-6 border-t border-border">
          <Button
            variant="ghost"
            onClick={onBack}
            className="text-muted-foreground hover:text-foreground"
          >
            Back
          </Button>
          <div className="flex gap-4">
            <Button
              variant="ghost"
              onClick={onSkip}
              className="text-muted-foreground hover:text-foreground"
            >
              Skip for now
            </Button>
            <Button
              onClick={handleContinue}
              disabled={!isConfigComplete || isSaving}
              className="gap-2"
            >
              {isSaving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              Continue
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
