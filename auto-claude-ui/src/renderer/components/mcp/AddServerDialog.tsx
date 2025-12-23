import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Globe, Zap } from 'lucide-react';

interface AddServerDialogProps {
  open: boolean;
  onClose: () => void;
}

export function AddServerDialog({ open, onClose }: AddServerDialogProps) {
  const [mode, setMode] = useState<'choose' | 'existing' | 'fastmcp'>('choose');

  const handleBack = () => {
    setMode('choose');
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        {mode === 'choose' && (
          <div className="space-y-4">
            <DialogHeader>
              <DialogTitle>Add MCP Server</DialogTitle>
            </DialogHeader>
            <p className="text-sm text-muted-foreground">
              Choose how to add your server:
            </p>

            <Button
              variant="outline"
              className="w-full h-auto p-4 flex flex-col items-start"
              onClick={() => setMode('existing')}
            >
              <div className="flex items-center gap-2 mb-1">
                <Globe className="h-5 w-5" />
                <span className="font-semibold">Connect to Existing Server</span>
              </div>
              <span className="text-sm text-muted-foreground">
                Connect to a running MCP server
              </span>
            </Button>

            <Button
              variant="outline"
              className="w-full h-auto p-4 flex flex-col items-start"
              onClick={() => setMode('fastmcp')}
            >
              <div className="flex items-center gap-2 mb-1">
                <Zap className="h-5 w-5" />
                <span className="font-semibold">Create New with FastMCP</span>
              </div>
              <span className="text-sm text-muted-foreground">
                Generate a custom server with wizard
              </span>
            </Button>

            <Button variant="ghost" onClick={onClose} className="w-full">
              Cancel
            </Button>
          </div>
        )}

        {mode === 'existing' && (
          <div>
            <p>Select connection type</p>
            <Button variant="ghost" onClick={handleBack}>
              ← Back
            </Button>
          </div>
        )}

        {mode === 'fastmcp' && (
          <div>
            <p>FastMCP Wizard (Phase 3)</p>
            <Button variant="ghost" onClick={handleBack}>
              ← Back
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
