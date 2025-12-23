import { useState } from 'react';
import { ChevronUp } from 'lucide-react';
import { Button } from '../ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { MCPToolsList } from './MCPToolsList';
import { MCPPromptsList } from './MCPPromptsList';
import { MCPResourcesList } from './MCPResourcesList';
import type { MCPServer } from '../../../shared/types/mcp';

interface MCPCapabilitiesViewProps {
  server: MCPServer;
  expanded: boolean;
  onToggle: () => void;
}

export function MCPCapabilitiesView({ server, expanded, onToggle }: MCPCapabilitiesViewProps) {
  const [activeTab, setActiveTab] = useState<'tools' | 'prompts' | 'resources'>('tools');

  if (!expanded) return null;

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
          <MCPToolsList tools={server.capabilities.tools || []} />
        </TabsContent>

        <TabsContent value="prompts">
          <MCPPromptsList prompts={server.capabilities.prompts || []} />
        </TabsContent>

        <TabsContent value="resources">
          <MCPResourcesList resources={server.capabilities.resources || []} />
        </TabsContent>
      </Tabs>

      <Button variant="ghost" size="sm" onClick={onToggle} className="mt-2">
        <ChevronUp className="h-4 w-4 mr-1" />
        Hide Capabilities
      </Button>
    </div>
  );
}
