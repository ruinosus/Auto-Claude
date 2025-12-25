import { Key, ExternalLink, Loader2, Globe, Cloud, Shield } from 'lucide-react';
import { CollapsibleSection } from './CollapsibleSection';
import { StatusBadge } from './StatusBadge';
import { PasswordInput } from './PasswordInput';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import type { ProjectEnvConfig } from '../../../shared/types';

interface ClaudeAuthSectionProps {
  isExpanded: boolean;
  onToggle: () => void;
  envConfig: ProjectEnvConfig | null;
  isLoadingEnv: boolean;
  envError: string | null;
  isCheckingAuth: boolean;
  authStatus: 'checking' | 'authenticated' | 'not_authenticated' | 'error';
  onClaudeSetup: () => void;
  onUpdateConfig: (updates: Partial<ProjectEnvConfig>) => void;
}

export function ClaudeAuthSection({
  isExpanded,
  onToggle,
  envConfig,
  isLoadingEnv,
  envError,
  isCheckingAuth,
  authStatus,
  onClaudeSetup,
  onUpdateConfig,
}: ClaudeAuthSectionProps) {
  const authMode = envConfig?.authMode || 'oauth';

  // Determine overall status based on auth mode
  const getOverallStatus = () => {
    if (authMode === 'oauth') {
      return authStatus === 'authenticated' ? 'success' : 'warning';
    } else if (authMode === 'azure-foundry') {
      return envConfig?.azureFoundryAuthStatus === 'configured' ? 'success' : 'warning';
    } else if (authMode === 'auth-token') {
      return envConfig?.authTokenStatus === 'configured' ? 'success' : 'warning';
    }
    return 'warning';
  };

  const getStatusLabel = () => {
    const status = getOverallStatus();
    return status === 'success' ? 'Connected' : 'Not Connected';
  };

  const badge = <StatusBadge status={getOverallStatus()} label={getStatusLabel()} />;

  return (
    <CollapsibleSection
      title="Authentication"
      icon={<Key className="h-4 w-4" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      badge={badge}
    >
      {isLoadingEnv ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading configuration...
        </div>
      ) : envConfig ? (
        <Tabs
          value={authMode}
          onValueChange={(value) => onUpdateConfig({ authMode: value as 'oauth' | 'azure-foundry' | 'auth-token' })}
          className="w-full"
        >
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="oauth" className="flex items-center gap-1.5">
              <Key className="h-3.5 w-3.5" />
              OAuth
            </TabsTrigger>
            <TabsTrigger value="azure-foundry" className="flex items-center gap-1.5">
              <Cloud className="h-3.5 w-3.5" />
              Azure Foundry
            </TabsTrigger>
            <TabsTrigger value="auth-token" className="flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5" />
              Auth Token
            </TabsTrigger>
          </TabsList>

          {/* OAuth Mode */}
          <TabsContent value="oauth" className="space-y-4 mt-4">
            {/* Claude CLI Status */}
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Claude CLI</p>
                  <p className="text-xs text-muted-foreground">
                    {isCheckingAuth ? 'Checking...' :
                      authStatus === 'authenticated' ? 'Authenticated via OAuth' :
                      authStatus === 'not_authenticated' ? 'Not authenticated' :
                      'Status unknown'}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={onClaudeSetup}
                  disabled={isCheckingAuth}
                >
                  {isCheckingAuth ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <ExternalLink className="h-4 w-4 mr-2" />
                      {authStatus === 'authenticated' ? 'Re-authenticate' : 'Setup OAuth'}
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Manual OAuth Token */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium text-foreground">
                  OAuth Token {envConfig.claudeTokenIsGlobal ? '(Override)' : ''}
                </Label>
                {envConfig.claudeTokenIsGlobal && (
                  <span className="flex items-center gap-1 text-xs text-info">
                    <Globe className="h-3 w-3" />
                    Using global token
                  </span>
                )}
              </div>
              {envConfig.claudeTokenIsGlobal ? (
                <p className="text-xs text-muted-foreground">
                  Using token from App Settings. Enter a project-specific token below to override.
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Paste a token from <code className="px-1 bg-muted rounded">claude setup-token</code>
                </p>
              )}
              <PasswordInput
                value={envConfig.claudeTokenIsGlobal ? '' : (envConfig.claudeOAuthToken || '')}
                onChange={(value) => onUpdateConfig({
                  claudeOAuthToken: value || undefined,
                })}
                placeholder={envConfig.claudeTokenIsGlobal ? 'Enter to override global token...' : 'sk-ant-oat01-...'}
              />
            </div>
          </TabsContent>

          {/* Azure Foundry Mode */}
          <TabsContent value="azure-foundry" className="space-y-4 mt-4">
            <div className="rounded-lg border border-info/20 bg-info/5 p-3">
              <p className="text-sm text-muted-foreground">
                <span className="font-medium text-foreground">Azure Foundry</span> is for enterprise Azure deployments.
                Configure your Azure OpenAI resource details below.
              </p>
            </div>

            {/* API Key */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                Azure Foundry API Key
              </Label>
              <p className="text-xs text-muted-foreground">
                Your Azure OpenAI API key (from Azure Portal)
              </p>
              <PasswordInput
                value={envConfig.azureFoundryApiKey || ''}
                onChange={(value) => onUpdateConfig({
                  azureFoundryApiKey: value || undefined,
                  azureFoundryAuthStatus: value ? 'configured' : 'not_configured'
                })}
                placeholder="Enter your Azure API key..."
              />
            </div>

            {/* Base URL */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                Base URL
              </Label>
              <p className="text-xs text-muted-foreground">
                Your Azure Foundry endpoint (must end with /anthropic)
              </p>
              <Input
                type="url"
                value={envConfig.azureFoundryBaseUrl || ''}
                onChange={(e) => onUpdateConfig({
                  azureFoundryBaseUrl: e.target.value || undefined
                })}
                placeholder="https://your-resource.openai.azure.com/anthropic"
                className="font-mono text-sm"
              />
            </div>

            {/* Resource Name */}
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                Resource Name
              </Label>
              <p className="text-xs text-muted-foreground">
                Your Azure resource name
              </p>
              <Input
                value={envConfig.azureFoundryResource || ''}
                onChange={(e) => onUpdateConfig({
                  azureFoundryResource: e.target.value || undefined
                })}
                placeholder="your-resource-name"
                className="font-mono text-sm"
              />
            </div>
          </TabsContent>

          {/* Auth Token Mode */}
          <TabsContent value="auth-token" className="space-y-4 mt-4">
            <div className="rounded-lg border border-warning/20 bg-warning/5 p-3">
              <p className="text-sm text-muted-foreground">
                <span className="font-medium text-foreground">Auth Token</span> mode is for custom proxy/CCR setups.
                Only use this if you have a custom Anthropic API proxy.
              </p>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                ANTHROPIC_AUTH_TOKEN
              </Label>
              <p className="text-xs text-muted-foreground">
                Authentication token for your proxy/CCR setup
              </p>
              <PasswordInput
                value={envConfig.anthropicAuthToken || ''}
                onChange={(value) => onUpdateConfig({
                  anthropicAuthToken: value || undefined,
                  authTokenStatus: value ? 'configured' : 'not_configured'
                })}
                placeholder="Enter your auth token..."
              />
            </div>
          </TabsContent>
        </Tabs>
      ) : envError ? (
        <p className="text-sm text-destructive">{envError}</p>
      ) : null}
    </CollapsibleSection>
  );
}
