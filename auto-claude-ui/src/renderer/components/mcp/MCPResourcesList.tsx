import { Copy } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import type { MCPResource } from '../../../shared/types/mcp';

interface MCPResourcesListProps {
  resources: MCPResource[];
}

export function MCPResourcesList({ resources }: MCPResourcesListProps) {
  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
  };

  if (resources.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 text-center">
        No resources available
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {resources.map(resource => (
        <div key={resource.uri} className="border rounded p-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <code className="font-mono text-sm">{resource.uri}</code>
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
                <div className="text-xs text-muted-foreground mt-1">
                  Type: {resource.mimeType}
                </div>
              )}

              {resource.templateParams && resource.templateParams.length > 0 && (
                <div className="text-xs text-muted-foreground mt-1">
                  Parameters: {resource.templateParams.map(p => `{${p}}`).join(', ')}
                </div>
              )}
            </div>

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
      ))}
    </div>
  );
}
