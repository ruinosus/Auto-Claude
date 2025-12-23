import { useState, useEffect, useCallback } from 'react';
import { Plug, Search, RefreshCw } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { MCPServerCard } from './MCPServerCard';
import { useProjectStore } from '../../stores/project-store';
import type { MCPServer } from '../../../shared/types/mcp';

export function MCPManager() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedServer, setSelectedServer] = useState<MCPServer | null>(null);

  const selectedProject = useProjectStore((state) => state.getSelectedProject());

  const loadServers = useCallback(async () => {
    try {
      setLoading(true);
      const projectPath = selectedProject?.path;
      const mcpServers = await window.electronAPI.mcp.list(projectPath);
      setServers(mcpServers);
    } catch (error) {
      console.error('Failed to load MCP servers:', error);
      setServers([]);
    } finally {
      setLoading(false);
    }
  }, [selectedProject?.path]);

  useEffect(() => {
    loadServers();
  }, [loadServers]);

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      await loadServers();
    } finally {
      setRefreshing(false);
    }
  };

  const handleConfigure = (server: MCPServer) => {
    setSelectedServer(server);
    // Modal will be opened once Task 9 is implemented
  };

  // Filter servers by search query
  const filteredServers = servers.filter(server =>
    server.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    server.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    server.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group by category
  const connectedServers = filteredServers.filter(s => s.status === 'connected');
  const requiresSetup = filteredServers.filter(s => !s.enabled && s.requiredEnvVars.length > 0);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Plug className="h-5 w-5" />
          <h2 className="text-lg font-semibold">MCP Servers</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            disabled={refreshing}
            title="Refresh servers list"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="p-4 border-b">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search MCP servers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Stats */}
      <div className="px-4 py-2 border-b bg-muted/50">
        <p className="text-sm text-muted-foreground">
          {servers.length} servers available • {connectedServers.length} connected • {requiresSetup.length} require setup
        </p>
      </div>

      {/* Servers List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="text-center py-8 text-muted-foreground">
            Loading MCP servers...
          </div>
        ) : filteredServers.length === 0 ? (
          <div className="text-center py-8">
            <Plug className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground mb-2">
              {searchQuery ? 'No servers match your search' : 'No MCP servers available'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredServers.map(server => (
              <MCPServerCard
                key={server.id}
                server={server}
                onConfigure={handleConfigure}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
