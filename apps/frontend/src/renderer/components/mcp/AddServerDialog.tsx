import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Globe, Zap } from 'lucide-react';
import { AddExistingServerForm } from './AddExistingServerForm';
import { FastMCPWizard } from './wizard/FastMCPWizard';
import type { CustomServerConfig, FastMCPServerConfig } from '../../../shared/types/mcp';

interface AddServerDialogProps {
  open: boolean;
  onClose: () => void;
  onServerAdded?: () => void;
}

export function AddServerDialog({ open, onClose, onServerAdded }: AddServerDialogProps) {
  const [mode, setMode] = useState<'choose' | 'existing' | 'fastmcp'>('choose');

  const handleBack = () => {
    setMode('choose');
  };

  const handleComplete = async (config: CustomServerConfig) => {
    try {
      // Save the server config via IPC
      await window.electronAPI.mcp.addCustomServer(config, 'global');
      // Reload the servers list
      onServerAdded?.();
      // Close the dialog after successful save
      onClose();
    } catch (error) {
      console.error('Failed to save custom MCP server:', error);
      // TODO: Show error message to user
    }
  };

  const handleCancel = () => {
    setMode('choose');
  };

  const handleFastMCPComplete = async (config: FastMCPServerConfig) => {
    console.log('[Renderer] handleFastMCPComplete called with config:', config);
    try {
      console.log('[Renderer] Calling window.electronAPI.mcp.generateFastMCPServer...');
      const result = await window.electronAPI.mcp.generateFastMCPServer(config);
      console.log('[Renderer] Result from IPC:', result);
      // Reload the servers list
      onServerAdded?.();
      // Close dialog on success
      onClose();
    } catch (error) {
      console.error('[Renderer] Failed to generate FastMCP server:', error);
      // TODO: Show error message to user
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
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
          <AddExistingServerForm
            onComplete={handleComplete}
            onCancel={handleCancel}
          />
        )}

        {mode === 'fastmcp' && (
          <FastMCPWizard
            onComplete={handleFastMCPComplete}
            onCancel={handleCancel}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
