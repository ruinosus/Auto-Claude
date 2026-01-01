import { useState } from 'react';
import { Loader2, Copy, Check } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import type { MCPPrompt } from '../../../shared/types/mcp';

interface MCPPromptsListProps {
  prompts: MCPPrompt[];
  serverId: string;
}

export function MCPPromptsList({ prompts, serverId }: MCPPromptsListProps) {
  const [selectedPrompt, setSelectedPrompt] = useState<MCPPrompt | null>(null);
  const [args, setArgs] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (prompts.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 text-center">
        No prompts available
      </div>
    );
  }

  const handleOpenPrompt = (prompt: MCPPrompt) => {
    setSelectedPrompt(prompt);
    setArgs({});
    setResult(null);
    setError(null);
    setCopied(false);
  };

  const handleClose = () => {
    setSelectedPrompt(null);
    setArgs({});
    setResult(null);
    setError(null);
    setCopied(false);
  };

  const handleExecute = async () => {
    if (!selectedPrompt) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Filter out empty string values - only send args that have actual values
      const filteredArgs: Record<string, string> = {};
      for (const [key, value] of Object.entries(args)) {
        if (value && value.trim() !== '') {
          filteredArgs[key] = value;
        }
      }

      const response = await window.electronAPI.mcp.getPrompt(
        serverId,
        selectedPrompt.name,
        Object.keys(filteredArgs).length > 0 ? filteredArgs : undefined
      );

      if (response.error) {
        setError(response.error);
      } else {
        setResult(response.content);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (result) {
      await navigator.clipboard.writeText(result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleArgChange = (argName: string, value: string) => {
    setArgs(prev => ({ ...prev, [argName]: value }));
  };

  return (
    <>
      <div className="space-y-2">
        {prompts.map(prompt => (
          <div key={prompt.name} className="border rounded p-3">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="font-medium">{prompt.displayName || prompt.name}</div>
                <p className="text-sm text-muted-foreground">{prompt.description}</p>

                {prompt.arguments && prompt.arguments.length > 0 && (
                  <div className="mt-2 text-sm">
                    <span className="font-medium">Arguments: </span>
                    {prompt.arguments.map(arg => (
                      <span key={arg.name} className="mr-2">
                        <code className="bg-muted px-1 rounded">{arg.name}</code>
                        {arg.required && <span className="text-red-500">*</span>}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => handleOpenPrompt(prompt)}
              >
                Use prompt →
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Prompt Execution Dialog */}
      <Dialog open={!!selectedPrompt} onOpenChange={(open) => !open && handleClose()}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>
              {selectedPrompt?.displayName || selectedPrompt?.name}
            </DialogTitle>
            <DialogDescription>
              {selectedPrompt?.description}
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto space-y-4 py-4">
            {/* Arguments Form */}
            {selectedPrompt?.arguments && selectedPrompt.arguments.length > 0 && (
              <div className="space-y-3">
                <Label className="text-sm font-medium">Arguments</Label>
                {selectedPrompt.arguments.map(arg => (
                  <div key={arg.name} className="space-y-1">
                    <Label htmlFor={arg.name} className="text-sm">
                      {arg.name}
                      {arg.required && <span className="text-red-500 ml-1">*</span>}
                    </Label>
                    {arg.description && (
                      <p className="text-xs text-muted-foreground">{arg.description}</p>
                    )}
                    <Input
                      id={arg.name}
                      value={args[arg.name] || ''}
                      onChange={(e) => handleArgChange(arg.name, e.target.value)}
                      placeholder={`Enter ${arg.name}...`}
                    />
                  </div>
                ))}
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm">
                {error}
              </div>
            )}

            {/* Result Display */}
            {result && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium">Generated Prompt</Label>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopy}
                    className="h-8"
                  >
                    {copied ? (
                      <>
                        <Check className="h-3 w-3 mr-1" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3 mr-1" />
                        Copy
                      </>
                    )}
                  </Button>
                </div>
                <div className="bg-muted p-3 rounded-md font-mono text-sm whitespace-pre-wrap max-h-[300px] overflow-y-auto">
                  {result}
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              Close
            </Button>
            <Button onClick={handleExecute} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                'Generate Prompt'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
