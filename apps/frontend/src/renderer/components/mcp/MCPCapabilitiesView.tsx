import { useState, useEffect } from 'react';
import { ChevronUp, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { MCPToolsList } from './MCPToolsList';
import { MCPPromptsList } from './MCPPromptsList';
import { MCPResourcesList } from './MCPResourcesList';
import type { MCPServer, MCPTool, MCPPrompt, MCPResource } from '../../../shared/types/mcp';

interface MCPCapabilitiesViewProps {
  server: MCPServer;
  expanded: boolean;
  onToggle: () => void;
}

export function MCPCapabilitiesView({ server, expanded, onToggle }: MCPCapabilitiesViewProps) {
  const [activeTab, setActiveTab] = useState<'tools' | 'prompts' | 'resources'>('tools');
  const [loading, setLoading] = useState(false);
  const [capabilities, setCapabilities] = useState<{
    tools: MCPTool[];
    prompts: MCPPrompt[];
    resources: MCPResource[];
  } | null>(null);

  // Load capabilities when expanded
  useEffect(() => {
    if (expanded && !capabilities) {
      loadCapabilities();
    }
  }, [expanded]);

  const loadCapabilities = async () => {
    setLoading(true);
    try {
      const caps = await window.electronAPI.mcp.getCapabilities(server.id);
      setCapabilities(caps);
    } catch (error) {
      console.error('Failed to load capabilities:', error);
      setCapabilities({ tools: [], prompts: [], resources: [] });
    } finally {
      setLoading(false);
    }
  };

  if (!expanded) return null;

  if (loading) {
    return (
      <div className="border-t p-8 bg-muted/50 flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading capabilities...</span>
      </div>
    );
  }

  const tools = capabilities?.tools || server.capabilities?.tools || [];
  const prompts = capabilities?.prompts || server.capabilities?.prompts || [];
  const resources = capabilities?.resources || server.capabilities?.resources || [];

  return (
    <div className="border-t p-4 bg-muted/50">
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'tools' | 'prompts' | 'resources')}>
        <TabsList>
          <TabsTrigger value="tools">
            🔧 Tools ({server.toolCount})
          </TabsTrigger>
          <TabsTrigger value="prompts">
            📝 Prompts ({server.promptCount})
          </TabsTrigger>
          <TabsTrigger value="resources">
            📁 Resources ({server.resourceCount})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="tools">
          <MCPToolsList
            tools={tools}
            serverId={server.id}
            serverName={server.name}
          />
        </TabsContent>

        <TabsContent value="prompts">
          <MCPPromptsList prompts={prompts} />
        </TabsContent>

        <TabsContent value="resources">
          <MCPResourcesList resources={resources} />
        </TabsContent>
      </Tabs>

      <Button variant="ghost" size="sm" onClick={onToggle} className="mt-2">
        <ChevronUp className="h-4 w-4 mr-1" />
        Hide Capabilities
      </Button>
    </div>
  );
}
