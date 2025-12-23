import { useState } from 'react';
import { ChevronDown, ChevronUp, Settings } from 'lucide-react';
import { Button } from '../ui/button';
import { MCPStatusIndicator } from './MCPStatusIndicator';
import { MCPCapabilitiesView } from './MCPCapabilitiesView';
import type { MCPServer } from '../../../shared/types/mcp';

interface MCPServerCardProps {
  server: MCPServer;
  onConfigure: (server: MCPServer) => void;
}

export function MCPServerCard({ server, onConfigure }: MCPServerCardProps) {
  const [expanded, setExpanded] = useState(false);

  const showConfigure = !server.enabled && server.requiredEnvVars.length > 0;

  return (
    <div className="border rounded-lg overflow-hidden bg-card">
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            {/* Icon */}
            <div className="text-2xl mt-1">
              {getServerIcon(server.icon)}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-semibold text-base">{server.name}</h3>
                <MCPStatusIndicator status={server.status} />
              </div>

              <p className="text-sm text-muted-foreground mb-2">
                {server.description}
              </p>

              {/* Status info */}
              <div className="text-xs text-muted-foreground">
                {server.enabled ? (
                  <span>
                    {server.toolCount} tools • {server.promptCount} prompts • {server.resourceCount} resources
                  </span>
                ) : server.requiredEnvVars.length > 0 ? (
                  <span>Requires: {server.requiredEnvVars.join(', ')}</span>
                ) : (
                  <span>Ready to configure</span>
                )}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {showConfigure && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onConfigure(server)}
              >
                <Settings className="h-4 w-4 mr-2" />
                Configure
              </Button>
            )}

            {server.enabled && (server.toolCount > 0 || server.promptCount > 0 || server.resourceCount > 0) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? (
                  <>
                    <ChevronUp className="h-4 w-4 mr-1" />
                    Hide
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-4 w-4 mr-1" />
                    Show Details
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </div>

      <MCPCapabilitiesView
        server={server}
        expanded={expanded}
        onToggle={() => setExpanded(false)}
      />
    </div>
  );
}

function getServerIcon(iconName?: string): string {
  const icons: Record<string, string> = {
    Book: '📚',
    Zap: '⚡',
    Brain: '🧠',
    Monitor: '🖥️',
    Globe: '🌐',
    Wrench: '🔧',
  };
  return icons[iconName || ''] || '🔌';
}
