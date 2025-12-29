import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Wifi, WifiOff, Loader2, CheckCircle2, XCircle, Activity } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { SettingsSection } from './SettingsSection';
import { cn } from '../../lib/utils';

/**
 * OTEL Settings - Connection status types
 */
type ConnectionStatus = 'disconnected' | 'testing' | 'connected' | 'error';

/**
 * OTEL Settings configuration
 */
interface OTELSettingsConfig {
  enabled: boolean;
  endpoint: string;
}

/**
 * Default OTEL settings
 */
const DEFAULT_OTEL_SETTINGS: OTELSettingsConfig = {
  enabled: false,
  endpoint: 'http://localhost:4318',
};

/**
 * OpenTelemetry Settings component
 * Allows users to enable/disable OTEL telemetry and configure the endpoint
 */
export function OTELSettings() {
  const { t } = useTranslation(['settings', 'common']);
  const [settings, setSettings] = useState<OTELSettingsConfig>(DEFAULT_OTEL_SETTINGS);
  const [isLoading, setIsLoading] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      // TODO: Replace with actual IPC call when backend is implemented
      // const result = await window.electronAPI.otel.getSettings();
      // For now, use default settings
      setSettings(DEFAULT_OTEL_SETTINGS);
    } catch (error) {
      console.error('Failed to load OTEL settings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const saveSettings = useCallback(async (updates: Partial<OTELSettingsConfig>) => {
    const newSettings = { ...settings, ...updates };
    try {
      // TODO: Replace with actual IPC call when backend is implemented
      // await window.electronAPI.otel.saveSettings(newSettings);
      setSettings(newSettings);

      // Reset connection status if endpoint changed or disabled
      if (updates.endpoint !== undefined || updates.enabled === false) {
        setConnectionStatus('disconnected');
        setConnectionError(null);
      }
    } catch (error) {
      console.error('Failed to save OTEL settings:', error);
    }
  }, [settings]);

  const testConnection = async () => {
    if (!settings.endpoint) {
      setConnectionError(t('settings:otel.endpointRequired'));
      setConnectionStatus('error');
      return;
    }

    setConnectionStatus('testing');
    setConnectionError(null);

    try {
      // TODO: Replace with actual IPC call when backend is implemented
      // const result = await window.electronAPI.otel.testConnection(settings.endpoint);

      // Simulate connection test for now
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Validate endpoint URL format
      try {
        new URL(settings.endpoint);
        setConnectionStatus('connected');
      } catch {
        setConnectionStatus('error');
        setConnectionError(t('settings:otel.invalidEndpoint'));
      }
    } catch (error) {
      setConnectionStatus('error');
      setConnectionError(
        error instanceof Error ? error.message : t('settings:otel.connectionFailed')
      );
    }
  };

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <CheckCircle2 className="h-5 w-5 text-success" />;
      case 'testing':
        return <Loader2 className="h-5 w-5 text-info animate-spin" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-destructive" />;
      default:
        return <WifiOff className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return t('settings:otel.statusConnected');
      case 'testing':
        return t('settings:otel.statusTesting');
      case 'error':
        return connectionError || t('settings:otel.statusError');
      default:
        return t('settings:otel.statusDisconnected');
    }
  };

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'bg-success/20 border-success/50 text-success';
      case 'testing':
        return 'bg-info/20 border-info/50 text-info';
      case 'error':
        return 'bg-destructive/20 border-destructive/50 text-destructive';
      default:
        return 'bg-muted border-border text-muted-foreground';
    }
  };

  if (isLoading) {
    return (
      <SettingsSection
        title={t('settings:otel.title')}
        description={t('settings:otel.description')}
      >
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-10 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </SettingsSection>
    );
  }

  return (
    <SettingsSection
      title={t('settings:otel.title')}
      description={t('settings:otel.description')}
    >
      <div className="space-y-6">
        {/* Enable/Disable Toggle */}
        <div className="flex items-center justify-between p-4 rounded-lg border border-border">
          <div className="flex items-center gap-3">
            <Activity className="h-5 w-5 text-muted-foreground" />
            <div className="space-y-1">
              <Label className="font-medium text-foreground">
                {t('settings:otel.enableTelemetry')}
              </Label>
              <p className="text-sm text-muted-foreground">
                {t('settings:otel.enableTelemetryDescription')}
              </p>
            </div>
          </div>
          <Switch
            checked={settings.enabled}
            onCheckedChange={(checked) => saveSettings({ enabled: checked })}
          />
        </div>

        {/* Endpoint Configuration (only shown when enabled) */}
        {settings.enabled && (
          <>
            {/* Endpoint URL Input */}
            <div className="space-y-2">
              <Label htmlFor="otel-endpoint">
                {t('settings:otel.endpoint')}
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="otel-endpoint"
                  type="url"
                  placeholder="http://localhost:4318"
                  value={settings.endpoint}
                  onChange={(e) => saveSettings({ endpoint: e.target.value })}
                  className="flex-1 font-mono text-sm"
                />
                <Button
                  variant="outline"
                  onClick={testConnection}
                  disabled={connectionStatus === 'testing' || !settings.endpoint}
                  className="shrink-0"
                >
                  {connectionStatus === 'testing' ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Wifi className="h-4 w-4 mr-2" />
                  )}
                  {t('settings:otel.testConnection')}
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                {t('settings:otel.endpointHint')}
              </p>
            </div>

            {/* Connection Status Indicator */}
            <div className={cn(
              'flex items-center gap-3 p-4 rounded-lg border',
              getStatusColor()
            )}>
              {getStatusIcon()}
              <div className="flex-1">
                <p className="text-sm font-medium">{getStatusText()}</p>
                {connectionStatus === 'connected' && (
                  <p className="text-xs opacity-80">
                    {t('settings:otel.connectedTo')} {settings.endpoint}
                  </p>
                )}
              </div>
            </div>
          </>
        )}

        {/* Info Box */}
        <div className="rounded-lg bg-info/10 border border-info/30 p-4">
          <div className="flex items-start gap-3">
            <Activity className="h-4 w-4 text-info shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t('settings:otel.infoText')}
              </p>
            </div>
          </div>
        </div>
      </div>
    </SettingsSection>
  );
}
