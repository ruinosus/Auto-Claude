import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Loader } from 'lucide-react';
import { Button } from '../ui/button';
import type { CustomServerConfig } from '../../../shared/types/mcp';

interface TestConnectionStepProps {
  serverConfig: CustomServerConfig;
  onSuccess: (capabilities: { tools: number; prompts: number; resources: number }) => void;
  onRetry: () => void;
}

interface TestConnectionResult {
  success: boolean;
  capabilities?: {
    tools: number;
    prompts: number;
    resources: number;
  };
  error?: string;
}

type ConnectionState = 'loading' | 'success' | 'error';

export function TestConnectionStep({
  serverConfig,
  onSuccess,
  onRetry,
}: TestConnectionStepProps) {
  const [state, setState] = useState<ConnectionState>('loading');
  const [result, setResult] = useState<TestConnectionResult | null>(null);

  const testConnection = async () => {
    setState('loading');
    setResult(null);

    try {
      // Call the IPC handler via window.electron
      const response = await (window as any).electron.testMCPConnection(serverConfig);

      if (response.success) {
        setState('success');
        setResult(response);

        // Call onSuccess with capabilities (if available)
        if (response.capabilities) {
          onSuccess(response.capabilities);
        } else {
          // If no capabilities returned, default to zeros
          onSuccess({ tools: 0, prompts: 0, resources: 0 });
        }
      } else {
        setState('error');
        setResult(response);
      }
    } catch (error) {
      setState('error');
      setResult({
        success: false,
        error: error instanceof Error ? error.message : 'Unexpected error',
      });
    }
  };

  // Test connection on mount
  useEffect(() => {
    testConnection();
  }, []);

  const handleRetry = () => {
    onRetry();
    testConnection();
  };

  return (
    <div className="space-y-4">
      {state === 'loading' && (
        <div className="flex flex-col items-center justify-center py-8 space-y-4">
          <Loader className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Testing connection...</p>
        </div>
      )}

      {state === 'success' && result && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle className="h-5 w-5" />
            <p className="font-medium">Connection successful!</p>
          </div>

          {result.capabilities && (
            <div className="rounded-md border p-4 space-y-2">
              <p className="text-sm font-medium">Capabilities Found:</p>
              <div className="space-y-1 text-sm text-muted-foreground">
                <div>
                  <span className="font-mono">
                    {result.capabilities.tools} {result.capabilities.tools === 1 ? 'tool' : 'tools'}
                  </span>
                </div>
                <div>
                  <span className="font-mono">
                    {result.capabilities.prompts} {result.capabilities.prompts === 1 ? 'prompt' : 'prompts'}
                  </span>
                </div>
                <div>
                  <span className="font-mono">
                    {result.capabilities.resources} {result.capabilities.resources === 1 ? 'resource' : 'resources'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {state === 'error' && result && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-red-600">
            <XCircle className="h-5 w-5" />
            <p className="font-medium">Connection Failed</p>
          </div>

          {result.error && (
            <div className="rounded-md border border-red-200 bg-red-50 p-4">
              <p className="text-sm text-red-800">{result.error}</p>
            </div>
          )}

          <Button variant="outline" onClick={handleRetry}>
            Retry
          </Button>
        </div>
      )}
    </div>
  );
}
