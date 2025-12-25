import { useState, useEffect } from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Textarea } from '../../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../ui/select';
import { FolderOpen } from 'lucide-react';

interface ServerConfigData {
  serverName: string;
  description: string;
  pythonVersion: '3.10' | '3.11' | '3.12' | '3.13';
  workingDir: string;
}

interface ServerConfigFormProps {
  onNext: (data: ServerConfigData) => void;
  onBack: () => void;
  initialData: ServerConfigData;
}

export function ServerConfigForm({ onNext, onBack, initialData }: ServerConfigFormProps) {
  const [serverName, setServerName] = useState(initialData.serverName);
  const [description, setDescription] = useState(initialData.description);
  const [pythonVersion, setPythonVersion] = useState<ServerConfigData['pythonVersion']>(initialData.pythonVersion);
  const [workingDir, setWorkingDir] = useState(initialData.workingDir);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [defaultDir, setDefaultDir] = useState('');

  // Get default directory on mount
  useEffect(() => {
    const getDefaultDir = async () => {
      try {
        const homeDir = await window.electronAPI.getDefaultProjectLocation();
        if (homeDir) {
          const baseDir = `${homeDir}/.auto-claude/fastmcp-servers`;
          setDefaultDir(baseDir);
          if (!initialData.workingDir) {
            setWorkingDir(baseDir);
          }
        }
      } catch (err) {
        console.error('Failed to get default directory:', err);
        // Fallback to a placeholder
        const fallbackDir = '~/.auto-claude/fastmcp-servers';
        setDefaultDir(fallbackDir);
        if (!initialData.workingDir) {
          setWorkingDir(fallbackDir);
        }
      }
    };
    getDefaultDir();
  }, [initialData.workingDir]);

  // Auto-generate working directory when server name changes
  useEffect(() => {
    if (serverName && defaultDir && !initialData.workingDir) {
      const generatedDir = `${defaultDir}/${serverName}`;
      setWorkingDir(generatedDir);
    }
  }, [serverName, defaultDir, initialData.workingDir]);

  const handleNext = () => {
    const newErrors: Record<string, string> = {};

    if (!serverName.trim()) {
      newErrors.serverName = 'Server name is required';
    }

    if (!workingDir.trim()) {
      newErrors.workingDir = 'Working directory is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    onNext({
      serverName: serverName.trim(),
      description: description.trim(),
      pythonVersion,
      workingDir: workingDir.trim()
    });
  };

  const handleBrowse = async () => {
    try {
      const result = await window.electronAPI.selectDirectory();
      if (result) {
        setWorkingDir(result);
      }
    } catch (err) {
      console.error('Failed to open directory dialog:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">Server Configuration</h3>
        <p className="text-sm text-muted-foreground">
          Configure your FastMCP server settings
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="serverName">Server Name *</Label>
          <Input
            id="serverName"
            value={serverName}
            onChange={(e) => {
              setServerName(e.target.value);
              setErrors(prev => ({ ...prev, serverName: '' }));
            }}
            placeholder="my-api-server"
            className={errors.serverName ? 'border-destructive' : ''}
          />
          {errors.serverName && (
            <p className="text-sm text-destructive">{errors.serverName}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief description of what this server does"
            rows={3}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="pythonVersion">Python Version *</Label>
          <Select value={pythonVersion} onValueChange={(v) => setPythonVersion(v as any)}>
            <SelectTrigger id="pythonVersion">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="3.10">Python 3.10</SelectItem>
              <SelectItem value="3.11">Python 3.11</SelectItem>
              <SelectItem value="3.12">Python 3.12</SelectItem>
              <SelectItem value="3.13">Python 3.13</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            uv will install this version automatically if needed
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="workingDir">Working Directory *</Label>
          <div className="flex gap-2">
            <Input
              id="workingDir"
              value={workingDir}
              onChange={(e) => {
                setWorkingDir(e.target.value);
                setErrors(prev => ({ ...prev, workingDir: '' }));
              }}
              className={errors.workingDir ? 'border-destructive' : ''}
            />
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={handleBrowse}
            >
              <FolderOpen className="h-4 w-4" />
            </Button>
          </div>
          {errors.workingDir && (
            <p className="text-sm text-destructive">{errors.workingDir}</p>
          )}
        </div>
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button onClick={handleNext}>
          Next
        </Button>
      </div>
    </div>
  );
}
