import { useState } from 'react';
import { Plus, X, FolderOpen } from 'lucide-react';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { RadioGroup, RadioGroupItem } from '../ui/radio-group';

export type Scope = 'global' | 'project';

export interface StdioServerFormData {
  name: string;
  description?: string;
  command: string;
  args?: string;
  workingDir?: string;
  env: Record<string, string>;
  scope: Scope;
}

export interface StdioServerFormProps {
  initialValues?: Partial<StdioServerFormData>;
  onSubmit: (data: StdioServerFormData) => void;
  onCancel: () => void;
  onBrowseCommand: () => void;
  onBrowseWorkingDir: () => void;
}

interface EnvVarEntry {
  id: string;
  key: string;
  value: string;
}

export function StdioServerForm({
  initialValues,
  onSubmit,
  onCancel,
  onBrowseCommand,
  onBrowseWorkingDir,
}: StdioServerFormProps) {
  // Form state
  const [name, setName] = useState(initialValues?.name || '');
  const [description, setDescription] = useState(initialValues?.description || '');
  const [command, setCommand] = useState(initialValues?.command || '');
  const [args, setArgs] = useState(initialValues?.args || '');
  const [workingDir, setWorkingDir] = useState(initialValues?.workingDir || '');
  const [scope, setScope] = useState<Scope>(initialValues?.scope || 'global');

  // Environment variables state
  const [envVars, setEnvVars] = useState<EnvVarEntry[]>(() => {
    if (initialValues?.env) {
      return Object.entries(initialValues.env).map(([key, value], index) => ({
        id: `env-${index}`,
        key,
        value,
      }));
    }
    return [];
  });

  const addEnvVar = () => {
    setEnvVars([
      ...envVars,
      {
        id: `env-${Date.now()}`,
        key: '',
        value: '',
      },
    ]);
  };

  const removeEnvVar = (id: string) => {
    setEnvVars(envVars.filter((v) => v.id !== id));
  };

  const updateEnvVarKey = (id: string, key: string) => {
    setEnvVars(envVars.map((v) => (v.id === id ? { ...v, key } : v)));
  };

  const updateEnvVarValue = (id: string, value: string) => {
    setEnvVars(envVars.map((v) => (v.id === id ? { ...v, value } : v)));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate required fields
    if (!name.trim() || !command.trim()) {
      return;
    }

    // Build environment variables object
    const env: Record<string, string> = {};
    envVars.forEach((v) => {
      if (v.key.trim() && v.value.trim()) {
        env[v.key] = v.value;
      }
    });

    // Build form data
    const formData: StdioServerFormData = {
      name: name.trim(),
      description: description.trim() || undefined,
      command: command.trim(),
      args: args.trim() || undefined,
      workingDir: workingDir.trim() || undefined,
      env,
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
            onChange={(e) => setName(e.target.value)}
            placeholder="My stdio Server"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Input
            id="description"
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Local MCP server via..."
          />
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-border" />

      {/* Command Configuration */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-foreground">Command Configuration</h3>

        <div className="space-y-2">
          <Label htmlFor="command">
            Command <span className="text-destructive">*</span>
          </Label>
          <div className="flex gap-2">
            <Input
              id="command"
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder="python3"
              required
              className="flex-1"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onBrowseCommand}
              aria-label="Browse Command"
            >
              <FolderOpen className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="arguments">Arguments</Label>
          <Input
            id="arguments"
            type="text"
            value={args}
            onChange={(e) => setArgs(e.target.value)}
            placeholder="server.py --port 8000"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="working-directory">Working Directory (optional)</Label>
          <div className="flex gap-2">
            <Input
              id="working-directory"
              type="text"
              value={workingDir}
              onChange={(e) => setWorkingDir(e.target.value)}
              placeholder="/path/to/server/"
              className="flex-1"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onBrowseWorkingDir}
              aria-label="Browse Working Directory"
            >
              <FolderOpen className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-border" />

      {/* Environment Variables */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-foreground">Environment Variables (optional)</h3>
          <Button type="button" variant="outline" size="sm" onClick={addEnvVar}>
            <Plus className="h-4 w-4 mr-2" />
            Add Variable
          </Button>
        </div>

        {envVars.length > 0 && (
          <div className="space-y-2">
            {envVars.map((envVar) => (
              <div key={envVar.id} className="flex items-center gap-2">
                <Input
                  type="text"
                  value={envVar.key}
                  onChange={(e) => updateEnvVarKey(envVar.id, e.target.value)}
                  placeholder="Variable Name"
                  className="flex-1"
                />
                <Input
                  type="text"
                  value={envVar.value}
                  onChange={(e) => updateEnvVarValue(envVar.id, e.target.value)}
                  placeholder="Variable Value"
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeEnvVar(envVar.id)}
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
