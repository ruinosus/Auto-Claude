/**
 * AddExistingServerForm Component
 *
 * Multi-step wizard for adding custom MCP servers:
 * 1. Connection Type Selection (http/stdio/sse)
 * 2. Server Configuration (form based on connection type)
 * 3. Test Connection (verify server is reachable)
 */
import { useState } from 'react';
import { Button } from '../ui/button';
import { ConnectionTypeSelector } from './ConnectionTypeSelector';
import { HttpServerForm, type HttpServerFormData } from './HttpServerForm';
import { StdioServerForm, type StdioServerFormData } from './StdioServerForm';
import { SseServerForm, type SseServerFormData } from './SseServerForm';
import { TestConnectionStep } from './TestConnectionStep';
import type { CustomServerConfig } from '../../../shared/types/mcp';

interface AddExistingServerFormProps {
  onComplete: (config: CustomServerConfig) => void;
  onCancel: () => void;
  initialStep?: 1 | 2 | 3;
}

type Step = 1 | 2 | 3;
type ConnectionType = 'http' | 'stdio' | 'sse';

export function AddExistingServerForm({
  onComplete,
  onCancel,
  initialStep = 1,
}: AddExistingServerFormProps) {
  // Step management
  const [currentStep, setCurrentStep] = useState<Step>(initialStep);

  // Connection type selection (Step 1)
  const [connectionType, setConnectionType] = useState<ConnectionType>('http');

  // Form data storage (Step 2)
  const [httpData, setHttpData] = useState<HttpServerFormData | null>(null);
  const [stdioData, setStdioData] = useState<StdioServerFormData | null>(null);
  const [sseData, setSseData] = useState<SseServerFormData | null>(null);

  // Connection test result (Step 3)
  const [connectionSuccessful, setConnectionSuccessful] = useState(false);

  // Navigation handlers
  const handleNext = () => {
    if (currentStep < 3) {
      setCurrentStep((currentStep + 1) as Step);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((currentStep - 1) as Step);
    }
  };

  // Step 1: Connection type selection
  const handleConnectionTypeNext = () => {
    handleNext();
  };

  // Step 2: Form submission handlers
  const handleHttpSubmit = (data: HttpServerFormData) => {
    setHttpData(data);
    handleNext();
  };

  const handleStdioSubmit = (data: StdioServerFormData) => {
    setStdioData(data);
    handleNext();
  };

  const handleSseSubmit = (data: SseServerFormData) => {
    setSseData(data);
    handleNext();
  };

  const handleFormCancel = () => {
    handleBack();
  };

  // Step 3: Connection test handlers
  const handleConnectionSuccess = (capabilities: {
    tools: number;
    prompts: number;
    resources: number;
  }) => {
    setConnectionSuccessful(true);
  };

  const handleConnectionRetry = () => {
    setConnectionSuccessful(false);
  };

  // Final save handler
  const handleSave = () => {
    // Build the CustomServerConfig from collected data
    const config: CustomServerConfig = {
      connectionType,
    };

    if (connectionType === 'http' && httpData) {
      config.baseUrl = httpData.baseUrl;
      config.authType = httpData.authType === 'none' ? 'none' : httpData.authType === 'apiKey' ? 'api-key' : 'bearer';
      config.authValue = httpData.authValue;
      config.headers = httpData.customHeaders;
    } else if (connectionType === 'stdio' && stdioData) {
      config.command = stdioData.command;
      config.args = stdioData.args ? stdioData.args.split(' ').filter(Boolean) : [];
      config.workingDir = stdioData.workingDir;
      config.env = stdioData.env;
    } else if (connectionType === 'sse' && sseData) {
      config.baseUrl = sseData.sseEndpoint;
      config.reconnectOnDisconnect = sseData.reconnectOnDisconnect;
      config.reconnectDelay = sseData.reconnectDelay;
      config.authType = sseData.authType === 'none' ? 'none' : sseData.authType === 'apiKey' ? 'api-key' : 'bearer';
      config.authValue = sseData.authValue;
    }

    onComplete(config);
  };

  // Build server config for connection testing
  const getServerConfigForTesting = (): CustomServerConfig => {
    const config: CustomServerConfig = {
      connectionType,
    };

    if (connectionType === 'http' && httpData) {
      config.baseUrl = httpData.baseUrl;
      config.authType = httpData.authType === 'none' ? 'none' : httpData.authType === 'apiKey' ? 'api-key' : 'bearer';
      config.authValue = httpData.authValue;
      config.headers = httpData.customHeaders;
    } else if (connectionType === 'stdio' && stdioData) {
      config.command = stdioData.command;
      config.args = stdioData.args ? stdioData.args.split(' ').filter(Boolean) : [];
      config.workingDir = stdioData.workingDir;
      config.env = stdioData.env;
    } else if (connectionType === 'sse' && sseData) {
      config.baseUrl = sseData.sseEndpoint;
      config.reconnectOnDisconnect = sseData.reconnectOnDisconnect;
      config.reconnectDelay = sseData.reconnectDelay;
      config.authType = sseData.authType === 'none' ? 'none' : sseData.authType === 'apiKey' ? 'api-key' : 'bearer';
      config.authValue = sseData.authValue;
    }

    return config;
  };

  // Render step indicator
  const renderStepIndicator = () => (
    <div className="text-sm text-muted-foreground mb-4">
      Step {currentStep} of 3
    </div>
  );

  // Render current step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-6">
            {renderStepIndicator()}
            <ConnectionTypeSelector value={connectionType} onChange={setConnectionType} />
            <div className="flex items-center justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
              <Button type="button" variant="outline" onClick={handleBack} disabled={true}>
                Back
              </Button>
              <Button type="button" onClick={handleConnectionTypeNext}>
                Next
              </Button>
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            {renderStepIndicator()}
            {connectionType === 'http' && (
              <HttpServerForm
                initialValues={httpData || undefined}
                onSubmit={handleHttpSubmit}
                onCancel={handleFormCancel}
              />
            )}
            {connectionType === 'stdio' && (
              <StdioServerForm
                initialValues={stdioData || undefined}
                onSubmit={handleStdioSubmit}
                onCancel={handleFormCancel}
                onBrowseCommand={() => {
                  // TODO: Implement file browser dialog
                  console.log('Browse command clicked');
                }}
                onBrowseWorkingDir={() => {
                  // TODO: Implement directory browser dialog
                  console.log('Browse working dir clicked');
                }}
              />
            )}
            {connectionType === 'sse' && (
              <SseServerForm
                initialValues={sseData || undefined}
                onSubmit={handleSseSubmit}
                onCancel={handleFormCancel}
              />
            )}
          </div>
        );

      case 3:
        return (
          <div className="space-y-6">
            {renderStepIndicator()}
            <TestConnectionStep
              serverConfig={getServerConfigForTesting()}
              onSuccess={handleConnectionSuccess}
              onRetry={handleConnectionRetry}
            />
            <div className="flex items-center justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
              <Button type="button" variant="outline" onClick={handleBack}>
                Back
              </Button>
              {connectionSuccessful && (
                <Button type="button" onClick={handleSave}>
                  Save
                </Button>
              )}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return <div className="space-y-4">{renderStepContent()}</div>;
}
