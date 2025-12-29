import { Key, ExternalLink, Loader2, Globe, Cloud, Users, Server, CheckCircle2 } from 'lucide-react';
import { CollapsibleSection } from './CollapsibleSection';
import { StatusBadge } from './StatusBadge';
import { PasswordInput } from './PasswordInput';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { cn } from '../../lib/utils';
import type { ProjectEnvConfig } from '../../../shared/types';

type AuthMode = 'oauth' | 'azure-foundry' | 'auth-token';

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
  // Determine current auth mode
  const currentAuthMode: AuthMode = envConfig?.authMode || 'oauth';

  // Check if Azure Foundry is configured
  const isAzureConfigured = !!(
    envConfig?.azureFoundryApiKey &&
    envConfig?.azureFoundryBaseUrl
  );

  // Check if Auth Token is configured
  const isAuthTokenConfigured = !!envConfig?.authToken;

  // Get overall auth status based on mode
  const getAuthStatusForMode = (): 'configured' | 'not_configured' => {
    switch (currentAuthMode) {
      case 'oauth':
        return authStatus === 'authenticated' ? 'configured' : 'not_configured';
      case 'azure-foundry':
        return isAzureConfigured ? 'configured' : 'not_configured';
      case 'auth-token':
        return isAuthTokenConfigured ? 'configured' : 'not_configured';
      default:
        return 'not_configured';
    }
  };

  const currentStatus = getAuthStatusForMode();

  // Get status description based on auth mode
  const getStatusDescription = (): string => {
    if (isCheckingAuth) return 'Checking...';

    switch (currentAuthMode) {
      case 'oauth':
        return authStatus === 'authenticated'
          ? 'Authenticated via OAuth'
          : 'Not authenticated';
      case 'azure-foundry':
        return isAzureConfigured
          ? 'Azure Foundry configured'
          : 'Azure Foundry not configured';
      case 'auth-token':
        return isAuthTokenConfigured
          ? 'Auth Token configured'
          : 'Auth Token not configured';
      default:
        return 'Status unknown';
    }
  };

  // Get auth mode label
  const getAuthModeLabel = (): string => {
    switch (currentAuthMode) {
      case 'oauth': return 'OAuth';
      case 'azure-foundry': return 'Azure Foundry';
      case 'auth-token': return 'Auth Token';
      default: return 'Unknown';
    }
  };

  const badge = currentStatus === 'configured' ? (
    <StatusBadge status="success" label="Connected" />
  ) : (
    <StatusBadge status="warning" label="Not Connected" />
  );

  return (
    <CollapsibleSection
      title="Claude Authentication"
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
        <div className="space-y-4">
          {/* Auth Mode Indicator */}
          <div className="rounded-lg border border-border bg-muted/30 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {/* Auth Mode Icon */}
                <div className={cn(
                  "flex items-center justify-center w-8 h-8 rounded-lg",
                  currentStatus === 'configured' ? "bg-success/10" : "bg-muted"
                )}>
                  {currentAuthMode === 'oauth' && (
                    <Users className={cn("h-4 w-4", currentStatus === 'configured' ? "text-success" : "text-muted-foreground")} />
                  )}
                  {currentAuthMode === 'azure-foundry' && (
                    <Cloud className={cn("h-4 w-4", currentStatus === 'configured' ? "text-success" : "text-muted-foreground")} />
                  )}
                  {currentAuthMode === 'auth-token' && (
                    <Server className={cn("h-4 w-4", currentStatus === 'configured' ? "text-success" : "text-muted-foreground")} />
                  )}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-foreground">
                      {getAuthModeLabel()}
                    </p>
                    {currentStatus === 'configured' && (
                      <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {getStatusDescription()}
                  </p>
                </div>
              </div>

              {/* Action Button - Only show for OAuth mode */}
              {currentAuthMode === 'oauth' && (
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
              )}
            </div>

            {/* Azure Foundry Details */}
            {currentAuthMode === 'azure-foundry' && isAzureConfigured && (
              <div className="mt-3 pt-3 border-t border-border/50 space-y-1">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-medium">Endpoint:</span>
                  <code className="px-1.5 py-0.5 bg-muted rounded text-[10px]">
                    {envConfig.azureFoundryBaseUrl}
                  </code>
                </div>
                {envConfig.azureFoundryResource && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="font-medium">Resource:</span>
                    <span>{envConfig.azureFoundryResource}</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* OAuth Token Input - Only show for OAuth mode */}
          {currentAuthMode === 'oauth' && (
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
                placeholder={envConfig.claudeTokenIsGlobal ? 'Enter to override global token...' : 'your-oauth-token-here'}
              />
            </div>
          )}

          {/* Auth Token Input - Only show for Auth Token mode */}
          {currentAuthMode === 'auth-token' && (
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                Auth Token (CCR/Proxy)
              </Label>
              <p className="text-xs text-muted-foreground">
                Token for CCR or custom proxy authentication
              </p>
              <PasswordInput
                value={envConfig.authToken || ''}
                onChange={(value) => onUpdateConfig({
                  authToken: value || undefined,
                })}
                placeholder="Enter your auth token..."
              />
            </div>
          )}

          {/* Info about changing auth mode */}
          <p className="text-xs text-muted-foreground italic">
            To change authentication mode, go to the Environment section above.
          </p>
        </div>
      ) : envError ? (
        <p className="text-sm text-destructive">{envError}</p>
      ) : null}
    </CollapsibleSection>
  );
}
