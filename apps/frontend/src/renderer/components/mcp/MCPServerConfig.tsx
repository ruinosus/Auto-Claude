import { useState } from 'react';
import { X, Eye, EyeOff, ExternalLink } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import type { MCPServer, MCPServerConfig } from '../../../shared/types/mcp';

interface MCPServerConfigProps {
  server: MCPServer;
  open: boolean;
  onClose: () => void;
  onSave: (config: MCPServerConfig) => Promise<void>;
}

export function MCPServerConfig({ server, open, onClose, onSave }: MCPServerConfigProps) {
  const [config, setConfig] = useState<MCPServerConfig>({
    enabled: false,
    envVars: {},
    scope: 'global'
  });
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message?: string } | null>(null);

  const handleEnvVarChange = (key: string, value: string) => {
    setConfig(prev => ({
      ...prev,
      envVars: { ...prev.envVars, [key]: value }
    }));
  };

  const toggleShowSecret = (key: string) => {
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleTestConnection = async () => {
    try {
      setTesting(true);
      setTestResult(null);

      const result = await window.electronAPI.mcp.testConnection(server.id, config);

      setTestResult({
        success: result.success,
        message: result.message || (result.success ? 'Connection successful!' : 'Connection failed')
      });
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Connection test failed'
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await onSave(config);
      onClose();
    } catch (error) {
      console.error('Failed to save config:', error);
      alert('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const allRequiredFilled = server.requiredEnvVars.every(key =>
    config.envVars[key] && config.envVars[key].trim().length > 0
  );

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configure {server.name}</DialogTitle>
          <DialogDescription>
            {server.description}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Required env vars */}
          {server.requiredEnvVars.map(key => (
            <div key={key} className="space-y-2">
              <Label htmlFor={key}>
                {formatEnvVarLabel(key)} <span className="text-red-500">*</span>
              </Label>
              <div className="relative">
                <Input
                  id={key}
                  type={showSecrets[key] ? 'text' : 'password'}
                  value={config.envVars[key] || ''}
                  onChange={(e) => handleEnvVarChange(key, e.target.value)}
                  placeholder={`Enter ${formatEnvVarLabel(key).toLowerCase()}`}
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 top-1/2 -translate-y-1/2"
                  onClick={() => toggleShowSecret(key)}
                >
                  {showSecrets[key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              {server.configUrl && (
                <p className="text-xs text-muted-foreground">
                  Get your key at:{' '}
                  <a
                    href={server.configUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline inline-flex items-center gap-1"
                  >
                    {server.configUrl}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </p>
              )}
            </div>
          ))}

          {/* Optional env vars */}
          {server.optionalEnvVars && server.optionalEnvVars.length > 0 && (
            <div className="space-y-2 pt-2 border-t">
              <Label className="text-sm text-muted-foreground">Optional Settings</Label>
              {server.optionalEnvVars.map(key => (
                <div key={key} className="space-y-2">
                  <Label htmlFor={key}>{formatEnvVarLabel(key)}</Label>
                  <Input
                    id={key}
                    type="text"
                    value={config.envVars[key] || ''}
                    onChange={(e) => handleEnvVarChange(key, e.target.value)}
                    placeholder={`Optional: ${formatEnvVarLabel(key).toLowerCase()}`}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Enable toggle */}
          <div className="flex items-center space-x-2 pt-2">
            <Checkbox
              id="enabled"
              checked={config.enabled}
              onCheckedChange={(checked) => setConfig(prev => ({ ...prev, enabled: !!checked }))}
            />
            <Label htmlFor="enabled" className="text-sm font-normal cursor-pointer">
              Enable {server.name} integration
            </Label>
          </div>

          {/* Connection test */}
          <div className="border-t pt-4">
            <div className="flex items-center justify-between mb-2">
              <Label>Connection Status</Label>
              <Button
                variant="outline"
                size="sm"
                onClick={handleTestConnection}
                disabled={!allRequiredFilled || testing}
              >
                {testing ? 'Testing...' : 'Test Connection'}
              </Button>
            </div>
            {testResult && (
              <div className={`text-sm p-2 rounded ${testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                {testResult.success ? '✓' : '✗'} {testResult.message}
              </div>
            )}
          </div>

          {/* Capabilities preview */}
          {server.toolCount > 0 && (
            <div className="border-t pt-4">
              <Label className="text-sm">Available Capabilities</Label>
              <p className="text-xs text-muted-foreground mt-1">
                • Tools: {server.toolCount}
                {server.promptCount > 0 && ` • Prompts: ${server.promptCount}`}
                {server.resourceCount > 0 && ` • Resources: ${server.resourceCount}`}
              </p>
            </div>
          )}

          {/* Requirements */}
          {(server.pythonVersion || server.systemRequirements) && (
            <div className="border-t pt-4">
              <Label className="text-sm">Requirements</Label>
              <div className="text-xs text-muted-foreground mt-1 space-y-1">
                {server.pythonVersion && <p>• Python {server.pythonVersion}</p>}
                {server.systemRequirements?.map(req => (
                  <p key={req}>• {req}</p>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={handleSave}
            disabled={!allRequiredFilled || saving}
          >
            {saving ? 'Saving...' : 'Save & Connect'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function formatEnvVarLabel(key: string): string {
  return key
    .split('_')
    .map(word => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ');
}
