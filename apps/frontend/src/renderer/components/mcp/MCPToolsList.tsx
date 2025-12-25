import { useState } from 'react';
import { Copy, ChevronDown, ChevronUp, Play } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { ExecuteToolDialog } from './ExecuteToolDialog';
import type { MCPTool } from '../../../shared/types/mcp';

interface MCPToolsListProps {
  tools: MCPTool[];
  serverId?: string;
  serverName?: string;
}

export function MCPToolsList({ tools, serverId, serverName }: MCPToolsListProps) {
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null);
  const [executeDialogOpen, setExecuteDialogOpen] = useState(false);

  const toggleTool = (toolName: string) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(toolName)) {
      newExpanded.delete(toolName);
    } else {
      newExpanded.add(toolName);
    }
    setExpandedTools(newExpanded);
  };

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
  };

  const handleExecuteTool = (tool: MCPTool) => {
    setSelectedTool(tool);
    setExecuteDialogOpen(true);
  };

  const getTypeIcon = (type: string): string => {
    const icons: Record<string, string> = {
      string: '📝',
      number: '🔢',
      boolean: '✅',
      object: '📦',
      array: '📚'
    };
    return icons[type] || '❓';
  };

  if (tools.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 text-center">
        No tools available
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {tools.map(tool => (
        <div key={tool.name} className="border rounded p-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <button
                onClick={() => toggleTool(tool.name)}
                className="flex items-center gap-2 text-left w-full hover:text-primary transition-colors"
              >
                {expandedTools.has(tool.name) ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronUp className="h-4 w-4" />
                )}
                <code className="font-mono text-sm">{tool.displayName}</code>
              </button>
              <p className="text-sm text-muted-foreground mt-1 ml-6">
                {tool.description}
              </p>
            </div>

            <div className="flex gap-1">
              {serverId && serverName && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleExecuteTool(tool)}
                  title="Execute tool"
                >
                  <Play className="h-3 w-3" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => copyToClipboard(tool.name)}
                title="Copy tool name"
              >
                <Copy className="h-3 w-3" />
              </Button>
            </div>
          </div>

          {expandedTools.has(tool.name) && tool.parameters && (
            <div className="mt-3 ml-6 space-y-2">
              <div className="text-sm font-medium">Parameters:</div>
              {tool.parameters.map(param => (
                <div key={param.name} className="flex items-start gap-2 text-sm">
                  <span>{getTypeIcon(param.type)}</span>
                  <div className="flex-1">
                    <code className="font-mono">{param.name}</code>
                    <span className="text-muted-foreground"> ({param.type})</span>
                    {param.required && (
                      <Badge variant="destructive" className="ml-2 text-xs">required</Badge>
                    )}
                    {!param.required && (
                      <Badge variant="secondary" className="ml-2 text-xs">optional</Badge>
                    )}
                    {param.default !== undefined && (
                      <span className="text-muted-foreground ml-2">
                        - Default: <code>{JSON.stringify(param.default)}</code>
                      </span>
                    )}
                    <p className="text-muted-foreground mt-1">{param.description}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {selectedTool && serverId && serverName && (
        <ExecuteToolDialog
          open={executeDialogOpen}
          onClose={() => {
            setExecuteDialogOpen(false);
            setSelectedTool(null);
          }}
          tool={selectedTool}
          serverId={serverId}
          serverName={serverName}
        />
      )}
    </div>
  );
}
