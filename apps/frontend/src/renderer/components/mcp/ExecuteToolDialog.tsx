import { useState, useEffect } from 'react';
import { Play, Loader2, CheckCircle, XCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import type { MCPTool } from '../../../shared/types/mcp';

interface ExecuteToolDialogProps {
  open: boolean;
  onClose: () => void;
  tool: MCPTool;
  serverId: string;
  serverName: string;
}

export function ExecuteToolDialog({
  open,
  onClose,
  tool,
  serverId,
  serverName
}: ExecuteToolDialogProps) {
  const [toolArgs, setToolArgs] = useState<Record<string, any>>({});
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      console.log(`[ExecuteToolDialog] Dialog opened for tool:`, tool.name);
      console.log(`[ExecuteToolDialog] tool.inputSchema:`, tool.inputSchema);
      console.log(`[ExecuteToolDialog] inputSchema.properties:`, tool.inputSchema?.properties);

      setToolArgs({});
      setResult(null);
      setError(null);
    }
  }, [open, tool]);

  const handleExecute = async () => {
    setError(null);
    setExecuting(true);

    try {
      console.log('[ExecuteToolDialog] Calling tool:', tool.name, 'with args:', toolArgs);

      const toolResult = await window.electronAPI.mcp.callTool(
        serverId,
        tool.name,
        toolArgs
      );

      console.log('[ExecuteToolDialog] Tool result:', toolResult);
      setResult(toolResult);
    } catch (err) {
      console.error('[ExecuteToolDialog] Error executing tool:', err);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setExecuting(false);
    }
  };

  const renderInputField = (propName: string, propSchema: any) => {
    const isRequired = tool.inputSchema?.required?.includes(propName);

    // Boolean type
    if (propSchema.type === 'boolean') {
      return (
        <div key={propName} className="space-y-2">
          <div className="flex items-center space-x-2">
            <Switch
              id={propName}
              checked={Boolean(toolArgs[propName])}
              onCheckedChange={(checked) => setToolArgs({ ...toolArgs, [propName]: checked })}
            />
            <Label htmlFor={propName}>
              {propName} {isRequired && <span className="text-red-500">*</span>}
            </Label>
          </div>
          {propSchema.description && (
            <p className="text-sm text-muted-foreground">{propSchema.description}</p>
          )}
        </div>
      );
    }

    // Long text (textarea)
    if (propSchema.type === 'string' && propSchema.description?.length > 100) {
      return (
        <div key={propName} className="space-y-2">
          <Label>
            {propName} {isRequired && <span className="text-red-500">*</span>}
          </Label>
          {propSchema.description && (
            <p className="text-sm text-muted-foreground">{propSchema.description}</p>
          )}
          <Textarea
            value={toolArgs[propName] || ''}
            onChange={(e) => setToolArgs({ ...toolArgs, [propName]: e.target.value })}
            placeholder={propSchema.description || propName}
            rows={4}
          />
        </div>
      );
    }

    // Object or Array (JSON input)
    if (propSchema.type === 'object' || propSchema.type === 'array') {
      return (
        <div key={propName} className="space-y-2">
          <Label>
            {propName} {isRequired && <span className="text-red-500">*</span>}
            <Badge variant="secondary" className="ml-2 text-xs">{propSchema.type}</Badge>
          </Label>
          {propSchema.description && (
            <p className="text-sm text-muted-foreground">{propSchema.description}</p>
          )}
          <Textarea
            value={typeof toolArgs[propName] === 'string' ? toolArgs[propName] : JSON.stringify(toolArgs[propName] || {}, null, 2)}
            onChange={(e) => setToolArgs({ ...toolArgs, [propName]: e.target.value })}
            placeholder={`Enter valid JSON ${propSchema.type}`}
            className="font-mono text-sm"
            rows={4}
          />
        </div>
      );
    }

    // Default: string or number input
    return (
      <div key={propName} className="space-y-2">
        <Label>
          {propName} {isRequired && <span className="text-red-500">*</span>}
        </Label>
        {propSchema.description && (
          <p className="text-sm text-muted-foreground">{propSchema.description}</p>
        )}
        <Input
          type={propSchema.type === 'number' ? 'number' : 'text'}
          value={toolArgs[propName] || ''}
          onChange={(e) => setToolArgs({ ...toolArgs, [propName]: e.target.value })}
          placeholder={propSchema.description || propName}
        />
      </div>
    );
  };

  const hasInputs = tool.inputSchema?.properties && Object.keys(tool.inputSchema.properties).length > 0;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Play className="h-5 w-5" />
            Execute Tool
          </DialogTitle>
          <DialogDescription asChild>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <code className="font-mono text-sm">{tool.name}</code>
                <span className="text-muted-foreground">from</span>
                <span className="font-medium">{serverName}</span>
              </div>
              <div className="text-sm text-muted-foreground">{tool.description}</div>
            </div>
          </DialogDescription>
        </DialogHeader>

        {hasInputs && !result && (
          <div className="space-y-4 py-4">
            <div className="text-sm font-medium">Parameters:</div>
            {Object.entries(tool.inputSchema!.properties!).map(([key, schema]) =>
              renderInputField(key, schema)
            )}
          </div>
        )}

        {!hasInputs && !result && (
          <div className="py-4 text-sm text-muted-foreground text-center">
            This tool has no parameters. Click Execute to run it.
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-destructive/10 border border-destructive/30 p-3">
            <div className="flex items-start gap-2">
              <XCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="text-sm font-medium text-destructive">Error</div>
                <pre className="text-xs text-destructive/80 mt-1 whitespace-pre-wrap font-mono">
                  {error}
                </pre>
              </div>
            </div>
          </div>
        )}

        {result && (
          <div className="rounded-lg bg-success/10 border border-success/30 p-3">
            <div className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-success shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="text-sm font-medium text-success">Success</div>
                <pre className="text-xs text-foreground/80 mt-2 whitespace-pre-wrap font-mono bg-background/50 p-2 rounded">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          {result ? (
            <>
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
              <Button
                onClick={() => {
                  setResult(null);
                  setError(null);
                  setToolArgs({});
                }}
              >
                Execute Again
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button onClick={handleExecute} disabled={executing}>
                {executing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Executing...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Execute
                  </>
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
