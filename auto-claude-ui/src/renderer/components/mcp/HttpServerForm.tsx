import { useState } from 'react';
import { Eye, EyeOff, Plus, X } from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';

export type AuthType = 'none' | 'apiKey' | 'bearerToken';
export type Scope = 'global' | 'project';

export interface HttpServerFormData {
  name: string;
  description?: string;
  baseUrl: string;
  authType: AuthType;
  authValue?: string;
  customHeaders: Record<string, string>;
  scope: Scope;
}

export interface HttpServerFormProps {
  initialValues?: Partial<HttpServerFormData>;
  onSubmit: (data: HttpServerFormData) => void;
  onCancel: () => void;
}

interface HeaderEntry {
  id: string;
  key: string;
  value: string;
}

export function HttpServerForm({ initialValues, onSubmit, onCancel }: HttpServerFormProps) {
  // Form state
  const [name, setName] = useState(initialValues?.name || '');
  const [description, setDescription] = useState(initialValues?.description || '');
  const [baseUrl, setBaseUrl] = useState(initialValues?.baseUrl || '');
  const [authType, setAuthType] = useState<AuthType>(initialValues?.authType || 'none');
  const [authValue, setAuthValue] = useState(initialValues?.authValue || '');
  const [showPassword, setShowPassword] = useState(false);
  const [scope, setScope] = useState<Scope>(initialValues?.scope || 'global');

  // Custom headers state
  const [headers, setHeaders] = useState<HeaderEntry[]>(() => {
    if (initialValues?.customHeaders) {
      return Object.entries(initialValues.customHeaders).map(([key, value], index) => ({
        id: `header-${index}`,
        key,
        value,
      }));
    }
    return [];
  });

  const addHeader = () => {
    setHeaders([
      ...headers,
      {
        id: `header-${Date.now()}`,
        key: '',
        value: '',
      },
    ]);
  };

  const removeHeader = (id: string) => {
    setHeaders(headers.filter(h => h.id !== id));
  };

  const updateHeaderKey = (id: string, key: string) => {
    setHeaders(headers.map(h => (h.id === id ? { ...h, key } : h)));
  };

  const updateHeaderValue = (id: string, value: string) => {
    setHeaders(headers.map(h => (h.id === id ? { ...h, value } : h)));
  };

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
    if (!name.trim() || !baseUrl.trim()) {
      return;
    }

    // Validate URL format
    if (!isValidUrl(baseUrl)) {
      return;
    }

    // Build custom headers object
    const customHeaders: Record<string, string> = {};
    headers.forEach(h => {
      if (h.key.trim() && h.value.trim()) {
        customHeaders[h.key] = h.value;
      }
    });

    // Build form data
    const formData: HttpServerFormData = {
      name: name.trim(),
      description: description.trim() || undefined,
      baseUrl: baseUrl.trim(),
      authType,
      authValue: authType !== 'none' ? authValue : undefined,
      customHeaders,
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
            placeholder="My Custom Server"
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
            placeholder="Custom MCP server for..."
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="base-url">
            Base URL <span className="text-destructive">*</span>
          </Label>
          <Input
            id="base-url"
            type="text"
            value={baseUrl}
            onChange={e => setBaseUrl(e.target.value)}
            placeholder="http://localhost:8000"
            required
          />
        </div>
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

      {/* Custom Headers */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-foreground">Custom Headers (optional)</h3>
          <Button type="button" variant="outline" size="sm" onClick={addHeader}>
            <Plus className="h-4 w-4 mr-2" />
            Add Header
          </Button>
        </div>

        {headers.length > 0 && (
          <div className="space-y-2">
            {headers.map(header => (
              <div key={header.id} className="flex items-center gap-2">
                <Input
                  type="text"
                  value={header.key}
                  onChange={e => updateHeaderKey(header.id, e.target.value)}
                  placeholder="Header Key"
                  className="flex-1"
                />
                <Input
                  type="text"
                  value={header.value}
                  onChange={e => updateHeaderValue(header.id, e.target.value)}
                  placeholder="Header Value"
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeHeader(header.id)}
                  aria-label="Remove"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
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
