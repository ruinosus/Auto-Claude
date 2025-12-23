import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';
import { Checkbox } from '../ui/checkbox';

export type AuthType = 'none' | 'apiKey' | 'bearerToken';
export type Scope = 'global' | 'project';

export interface SseServerFormData {
  name: string;
  description?: string;
  sseEndpoint: string;
  reconnectOnDisconnect: boolean;
  reconnectDelay?: number;
  authType: AuthType;
  authValue?: string;
  scope: Scope;
}

export interface SseServerFormProps {
  initialValues?: Partial<SseServerFormData>;
  onSubmit: (data: SseServerFormData) => void;
  onCancel: () => void;
}

export function SseServerForm({ initialValues, onSubmit, onCancel }: SseServerFormProps) {
  // Form state
  const [name, setName] = useState(initialValues?.name || '');
  const [description, setDescription] = useState(initialValues?.description || '');
  const [sseEndpoint, setSseEndpoint] = useState(initialValues?.sseEndpoint || '');
  const [reconnectOnDisconnect, setReconnectOnDisconnect] = useState(
    initialValues?.reconnectOnDisconnect ?? true
  );
  const [reconnectDelay, setReconnectDelay] = useState(
    initialValues?.reconnectDelay?.toString() || '5'
  );
  const [authType, setAuthType] = useState<AuthType>(initialValues?.authType || 'none');
  const [authValue, setAuthValue] = useState(initialValues?.authValue || '');
  const [showPassword, setShowPassword] = useState(false);
  const [scope, setScope] = useState<Scope>(initialValues?.scope || 'global');

  // URL validation
  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate required fields
    if (!name.trim() || !sseEndpoint.trim()) {
      return;
    }

    // Validate URL format
    if (!isValidUrl(sseEndpoint)) {
      return;
    }

    // Build form data
    const formData: SseServerFormData = {
      name: name.trim(),
      description: description.trim() || undefined,
      sseEndpoint: sseEndpoint.trim(),
      reconnectOnDisconnect,
      reconnectDelay: reconnectOnDisconnect ? parseInt(reconnectDelay, 10) : undefined,
      authType,
      authValue: authType !== 'none' ? authValue : undefined,
      scope,
    };

    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Information */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-foreground">Basic Information</h3>

        <div className="space-y-2">
          <Label htmlFor="server-name">
            Server Name <span className="text-destructive">*</span>
          </Label>
          <Input
            id="server-name"
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="My SSE Server"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Input
            id="description"
            type="text"
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Event stream MCP server"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="sse-endpoint">
            SSE Endpoint URL <span className="text-destructive">*</span>
          </Label>
          <Input
            id="sse-endpoint"
            type="text"
            value={sseEndpoint}
            onChange={e => setSseEndpoint(e.target.value)}
            placeholder="http://localhost:8000/events"
            required
          />
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-border" />

      {/* Connection Options */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-foreground">Connection Options</h3>

        <div className="flex items-center space-x-2">
          <Checkbox
            id="auto-reconnect"
            checked={reconnectOnDisconnect}
            onCheckedChange={(checked) => setReconnectOnDisconnect(checked === true)}
          />
          <Label
            htmlFor="auto-reconnect"
            className="text-sm font-normal cursor-pointer"
          >
            Auto-reconnect on disconnect
          </Label>
        </div>

        {reconnectOnDisconnect && (
          <div className="space-y-2">
            <Label htmlFor="reconnect-delay">Reconnect Delay (seconds)</Label>
            <Input
              id="reconnect-delay"
              type="number"
              min="1"
              value={reconnectDelay}
              onChange={e => setReconnectDelay(e.target.value)}
              placeholder="5"
            />
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-border" />

      {/* Authentication */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-foreground">Authentication</h3>

        <div className="space-y-3">
          <Label>Auth Type</Label>
          <RadioGroup value={authType} onValueChange={(value) => setAuthType(value as AuthType)}>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="none" id="auth-none" />
              <Label htmlFor="auth-none" className="font-normal cursor-pointer">
                None
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="apiKey" id="auth-api-key" />
              <Label htmlFor="auth-api-key" className="font-normal cursor-pointer">
                API Key
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="bearerToken" id="auth-bearer-token" />
              <Label htmlFor="auth-bearer-token" className="font-normal cursor-pointer">
                Bearer Token
              </Label>
            </div>
          </RadioGroup>
        </div>

        {authType !== 'none' && (
          <div className="space-y-2">
            <Label htmlFor="auth-value">
              {authType === 'apiKey' ? 'API Key Value' : 'Bearer Token Value'}{' '}
              <span className="text-destructive">*</span>
            </Label>
            <div className="relative">
              <Input
                id="auth-value"
                type={showPassword ? 'text' : 'password'}
                value={authValue}
                onChange={e => setAuthValue(e.target.value)}
                placeholder="Enter your key or token"
                required={authType !== 'none'}
                className="pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide' : 'Show'}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-border" />

      {/* Scope */}
      <div className="space-y-4">
        <div className="space-y-3">
          <Label>Save to:</Label>
          <RadioGroup value={scope} onValueChange={(value) => setScope(value as Scope)}>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="global" id="scope-global" />
              <Label htmlFor="scope-global" className="font-normal cursor-pointer">
                Global (~/.auto-claude/)
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="project" id="scope-project" />
              <Label htmlFor="scope-project" className="font-normal cursor-pointer">
                Project (./auto-claude/)
              </Label>
            </div>
          </RadioGroup>
        </div>
      </div>

      {/* Form Actions */}
      <div className="flex items-center justify-end gap-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Back
        </Button>
        <Button type="submit">Next</Button>
      </div>
    </form>
  );
}
