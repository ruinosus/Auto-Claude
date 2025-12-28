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
  baseUrl: string;
  resourceName: string;
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

  const isConfigComplete = config.apiKey.trim() && config.baseUrl.trim();

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
      // Basic URL validation - supports both Azure Foundry endpoint formats
      const url = config.baseUrl.trim();
      const isAzureFoundry = url.includes('services.ai.azure.com') || url.includes('openai.azure.com');

      if (!isAzureFoundry) {
        setError('Base URL should be an Azure Foundry endpoint (e.g., https://your-resource.services.ai.azure.com)');
        setIsValidating(false);
        return;
      }

      // Call validation API - the handler will normalize the URL
      const result = await window.electronAPI.validateAzureFoundryConfig({
        apiKey: config.apiKey.trim(),
        baseUrl: url,
        resourceName: config.resourceName.trim() || undefined
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
      // Save to global settings
      const result = await window.electronAPI.saveSettings({
        azureFoundryApiKey: config.apiKey.trim(),
        azureFoundryBaseUrl: config.baseUrl.trim(),
        azureFoundryResourceName: config.resourceName.trim() || undefined,
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
                  placeholder="Enter your Azure OpenAI API key"
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

            {/* Base URL */}
            <div className="space-y-2">
              <Label htmlFor="baseUrl">Base URL *</Label>
              <Input
                id="baseUrl"
                type="text"
                placeholder="https://your-resource.openai.azure.com/anthropic"
                value={config.baseUrl}
                onChange={(e) => handleChange('baseUrl', e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Your Azure OpenAI endpoint. The /anthropic suffix will be added automatically if needed.
              </p>
            </div>

            {/* Resource Name (optional) */}
            <div className="space-y-2">
              <Label htmlFor="resourceName">Resource Name (optional)</Label>
              <Input
                id="resourceName"
                type="text"
                placeholder="your-resource-name"
                value={config.resourceName}
                onChange={(e) => handleChange('resourceName', e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                The name of your Azure OpenAI resource (extracted from URL if not provided).
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
