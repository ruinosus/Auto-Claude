import { useState } from 'react';
import { Copy, Eye, Loader2, Check, FileText, FileJson, FileCode } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import type { MCPResource } from '../../../shared/types/mcp';

interface MCPResourcesListProps {
  resources: MCPResource[];
  serverId: string;
}

export function MCPResourcesList({ resources, serverId }: MCPResourcesListProps) {
  const [selectedResource, setSelectedResource] = useState<MCPResource | null>(null);
  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState<string | null>(null);
  const [mimeType, setMimeType] = useState<string>('text/plain');
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (resources.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 text-center">
        No resources available
      </div>
    );
  }

  const handleViewResource = async (resource: MCPResource) => {
    setSelectedResource(resource);
    setLoading(true);
    setError(null);
    setContent(null);

    try {
      const response = await window.electronAPI.mcp.readResource(serverId, resource.uri);

      if (response.error) {
        setError(response.error);
      } else {
        setContent(response.content);
        setMimeType(response.mimeType || resource.mimeType || 'text/plain');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setSelectedResource(null);
    setContent(null);
    setError(null);
    setCopied(false);
  };

  const getMimeTypeIcon = (mime: string) => {
    if (mime.includes('json')) return <FileJson className="h-4 w-4" />;
    if (mime.includes('markdown') || mime.includes('text')) return <FileText className="h-4 w-4" />;
    return <FileCode className="h-4 w-4" />;
  };

  const formatContent = (content: string, mime: string) => {
    if (mime.includes('json')) {
      try {
        return JSON.stringify(JSON.parse(content), null, 2);
      } catch {
        return content;
      }
    }
    return content;
  };

  return (
    <>
      <div className="space-y-2">
        {resources.map(resource => (
          <div key={resource.uri} className="border rounded p-3">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <code className="font-mono text-sm bg-muted px-1 rounded">{resource.uri}</code>
                  {resource.isTemplate && (
                    <Badge variant="secondary">Template</Badge>
                  )}
                </div>

                <div className="text-sm font-medium mt-1">{resource.name}</div>

                {resource.description && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {resource.description}
                  </p>
                )}

                {resource.mimeType && (
                  <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                    {getMimeTypeIcon(resource.mimeType)}
                    {resource.mimeType}
                  </div>
                )}

                {resource.templateParams && resource.templateParams.length > 0 && (
                  <div className="text-xs text-muted-foreground mt-1">
                    Parameters: {resource.templateParams.map(p => `{${p}}`).join(', ')}
                  </div>
                )}
              </div>

              <div className="flex gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleViewResource(resource)}
                  title="View content"
                >
                  <Eye className="h-3 w-3 mr-1" />
                  View
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(resource.uri)}
                  title="Copy URI"
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Resource View Dialog */}
      <Dialog open={!!selectedResource} onOpenChange={(open) => !open && handleClose()}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedResource?.mimeType && getMimeTypeIcon(selectedResource.mimeType)}
              {selectedResource?.name || selectedResource?.uri}
            </DialogTitle>
            <DialogDescription>
              <code className="text-xs">{selectedResource?.uri}</code>
              {selectedResource?.description && (
                <span className="block mt-1">{selectedResource.description}</span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">Loading resource...</span>
              </div>
            ) : error ? (
              <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm">
                {error}
              </div>
            ) : content ? (
              <div className="relative h-full">
                <div className="absolute top-2 right-2 z-10">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => copyToClipboard(content)}
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
                <pre className="bg-muted p-4 rounded-md font-mono text-sm whitespace-pre-wrap overflow-y-auto max-h-[400px]">
                  {formatContent(content, mimeType)}
                </pre>
              </div>
            ) : null}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
