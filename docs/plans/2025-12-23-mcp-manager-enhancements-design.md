# MCP Manager Enhancements - Design Document

**Created:** December 23, 2025
**Status:** Design Complete - Ready for Implementation
**Previous Work:** Phase 1 MCP Manager (basic server list + configuration)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Architecture Design](#architecture-design)
5. [Feature 1: Capabilities View](#feature-1-capabilities-view)
6. [Feature 2: Add Existing Server](#feature-2-add-existing-server)
7. [Feature 3: FastMCP Wizard](#feature-3-fastmcp-wizard)
8. [Feature 4: Process Management](#feature-4-process-management)
9. [Feature 5: Server CRUD Operations](#feature-5-server-crud-operations)
10. [Data Models & Storage](#data-models--storage)
11. [Error Handling & Validation](#error-handling--validation)
12. [UI Organization & Navigation](#ui-organization--navigation)
13. [Implementation Plan](#implementation-plan)
14. [Testing Strategy](#testing-strategy)

---

## Executive Summary

### The Problem

Phase 1 MCP Manager provides basic server list and configuration, but users are missing critical functionality:

1. **"Capabilities view coming soon..."** - Placeholder instead of actual tools/prompts/resources display
2. **No custom server support** - Cannot add their own MCP servers manually
3. **No FastMCP integration** - Cannot create custom servers easily
4. **Limited management** - Cannot edit, duplicate, or export server configurations

### The Solution

Implement comprehensive MCP Manager enhancements covering:

✅ **Full Capabilities View** - Detailed tabs showing tools/prompts/resources with parameters
✅ **Add Existing Servers** - Connect to running MCP servers (HTTP/stdio/SSE)
✅ **FastMCP Wizard** - Generate custom servers with 4-step wizard
✅ **Process Management** - Full lifecycle management for FastMCP servers
✅ **Server CRUD** - Edit, delete, duplicate, export/import configurations

### Impact

- **Better Discovery**: Users can see exactly what each server provides
- **Extensibility**: Users can add any MCP server or create their own
- **Developer Experience**: FastMCP wizard makes custom servers trivial
- **Professional Management**: Full CRUD with process lifecycle control

---

## Problem Statement

### Current Limitations

**From Phase 1 Implementation:**
- MCPServerCard shows placeholder: "Capabilities view coming soon..." (line 93-95)
- Only built-in servers supported (Context7, Linear, Graphiti, Electron, Puppeteer, Auto-Claude Tools)
- No way to add custom/external MCP servers
- No FastMCP integration despite design document planning it
- Basic enable/disable only - no advanced management

**User Pain Points:**
1. **Discovery**: "What tools does this server actually provide?"
2. **Extensibility**: "How do I add my own MCP server?"
3. **Creation**: "Can I create a simple custom server without writing all the boilerplate?"
4. **Management**: "Can I edit server configuration after adding it?"
5. **Process Control**: "How do I start/stop/restart my FastMCP servers?"

---

## Solution Overview

### Three Major Feature Areas

**1. Capabilities View (Replace Placeholder)**
- Tabbed interface: Tools / Prompts / Resources
- Detailed parameter information with types and descriptions
- Copy buttons for easy usage
- Expandable/collapsible individual items

**2. Custom Server Management**
- Two paths: "Add Existing Server" or "Create New with FastMCP"
- Support HTTP, stdio, and SSE connection types
- Auto-discovery of capabilities
- Full CRUD operations (Edit, Delete, Duplicate, Export/Import)

**3. Process Management**
- Start/Stop/Restart FastMCP servers
- Real-time status and uptime tracking
- Process logs viewer with filtering
- Auto-recovery on crashes

---

## Architecture Design

### Component Hierarchy

```
AppSettingsDialog
└── MCP Servers Section
    └── MCPManager (enhanced)
        ├── Header
        │   ├── [+ Add Server] button → AddServerDialog
        │   └── [⚙️ Settings] dropdown → ProcessManager, Import/Export
        ├── Filters & Search
        ├── Server List
        │   ├── MCPServerCard (built-in servers)
        │   │   ├── MCPStatusIndicator
        │   │   ├── MCPServerConfig (existing)
        │   │   └── MCPCapabilitiesView (NEW)
        │   │       ├── Tabs component
        │   │       ├── MCPToolsList (NEW)
        │   │       ├── MCPPromptsList (NEW)
        │   │       └── MCPResourcesList (NEW)
        │   └── CustomServerCard (NEW - for custom servers)
        │       ├── MCPStatusIndicator
        │       ├── ServerProcessControls (NEW - Start/Stop/Logs)
        │       ├── ServerEditDialog (NEW)
        │       └── MCPCapabilitiesView
        └── Dialogs
            ├── AddServerDialog (NEW)
            │   ├── AddExistingServerForm (NEW)
            │   └── FastMCPWizard (NEW)
            ├── ServerEditDialog (NEW)
            ├── ProcessLogsViewer (NEW)
            ├── ExportImportDialog (NEW)
            └── DeleteConfirmDialog (NEW)
```

### Data Flow

```
User Action (UI)
    ↓
IPC Call (electronAPI.mcp.*)
    ↓
Main Process Handler (mcp-manager.ts / mcp-fastmcp.ts / mcp-config.ts)
    ↓
File System / Process / Network Operation
    ↓
Response
    ↓
UI Update (React State)
```

### New Files to Create

```
auto-claude-ui/
├── src/
│   ├── main/
│   │   ├── mcp-manager.ts (UPDATE - add new handlers)
│   │   ├── mcp-fastmcp.ts (NEW - FastMCP process management)
│   │   ├── mcp-config.ts (UPDATE - custom server registry)
│   │   └── mcp-discovery.ts (NEW - auto-discover capabilities)
│   ├── preload/
│   │   └── api/modules/mcp-api.ts (UPDATE - add new IPC calls)
│   ├── renderer/components/mcp/
│   │   ├── MCPCapabilitiesView.tsx (NEW)
│   │   ├── MCPToolsList.tsx (NEW)
│   │   ├── MCPPromptsList.tsx (NEW)
│   │   ├── MCPResourcesList.tsx (NEW)
│   │   ├── AddServerDialog.tsx (NEW)
│   │   ├── AddExistingServerForm.tsx (NEW)
│   │   ├── FastMCPWizard.tsx (NEW)
│   │   ├── CustomServerCard.tsx (NEW)
│   │   ├── ServerProcessControls.tsx (NEW)
│   │   ├── ServerEditDialog.tsx (NEW)
│   │   ├── ProcessLogsViewer.tsx (NEW)
│   │   ├── ExportImportDialog.tsx (NEW)
│   │   ├── DeleteConfirmDialog.tsx (NEW)
│   │   ├── MCPManager.tsx (UPDATE - add filters, custom servers)
│   │   └── MCPServerCard.tsx (UPDATE - replace placeholder)
│   └── shared/types/
│       └── mcp.ts (UPDATE - add new types)
```

### New IPC Handlers Required

```typescript
// Custom server management
'mcp:add-custom-server'
'mcp:edit-server'
'mcp:delete-server'
'mcp:duplicate-server'
'mcp:export-config'
'mcp:import-config'

// Capabilities discovery
'mcp:discover-capabilities'
'mcp:refresh-capabilities'

// FastMCP process management
'mcp:start-fastmcp-server'
'mcp:stop-fastmcp-server'
'mcp:restart-fastmcp-server'
'mcp:get-process-status'
'mcp:get-process-logs'
'mcp:generate-fastmcp-server'

// Registry management
'mcp:load-custom-servers'
'mcp:save-custom-servers'
```

---

## Feature 1: Capabilities View

### Overview

Replace the "Capabilities view coming soon..." placeholder with a full-featured tabbed interface showing all MCP primitives.

### UI Design

**Collapsed State (existing):**
```
┌──────────────────────────────────────────┐
│ 📚 Context7                 [🟢 Active]  │
│ Real-time documentation lookup           │
│ 2 tools • 0 prompts • 0 resources        │
│ [▼ Show Capabilities]                    │
└──────────────────────────────────────────┘
```

**Expanded State (NEW):**
```
┌──────────────────────────────────────────────────────┐
│ 📚 Context7                            [🟢 Active]   │
│ Real-time documentation lookup                       │
├──────────────────────────────────────────────────────┤
│ [🔧 Tools (2)] [📝 Prompts (0)] [📁 Resources (0)]  │
├──────────────────────────────────────────────────────┤
│ 🔧 TOOLS                                             │
│                                                       │
│ ▸ mcp__context7__resolve-library-id                 │
│   Resolve package name to Context7 library ID        │
│   Parameters:                                         │
│   • libraryName (string, required)                   │
│     Library name to search for                       │
│   [📋 Copy tool name]                                │
│                                                       │
│ ▸ mcp__context7__get-library-docs                   │
│   Fetch documentation for a library                  │
│   Parameters:                                         │
│   • context7CompatibleLibraryID (string, required)   │
│     Exact library ID from resolve-library-id         │
│   • mode (string, optional) - Default: "code"        │
│     Documentation mode: "code" or "info"             │
│   • topic (string, optional)                         │
│     Topic to focus documentation on                  │
│   • page (number, optional) - Default: 1             │
│     Page number for pagination (1-10)                │
│   [📋 Copy tool name]                                │
│                                                       │
│ [▲ Hide Capabilities]                                │
└──────────────────────────────────────────────────────┘
```

### Component: MCPCapabilitiesView

```typescript
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
      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
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
```

### Component: MCPToolsList

**Features:**
- Expandable/collapsible individual tools
- Parameter type indicators with icons:
  - 📝 string
  - 🔢 number
  - ✅ boolean
  - 📦 object
  - 📚 array
- Required/optional badges
- Default values displayed
- Copy tool name button
- Syntax highlighting for code examples in descriptions

```typescript
export function MCPToolsList({ tools }: { tools: MCPTool[] }) {
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  const toggleTool = (toolName: string) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(toolName)) {
      newExpanded.delete(toolName);
    } else {
      newExpanded.add(toolName);
    }
    setExpandedTools(newExpanded);
  };

  return (
    <div className="space-y-2">
      {tools.map(tool => (
        <div key={tool.name} className="border rounded p-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <button
                onClick={() => toggleTool(tool.name)}
                className="flex items-center gap-2 text-left w-full hover:text-primary"
              >
                {expandedTools.has(tool.name) ? '▾' : '▸'}
                <code className="font-mono text-sm">{tool.displayName}</code>
              </button>
              <p className="text-sm text-muted-foreground mt-1 ml-6">
                {tool.description}
              </p>
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => copyToClipboard(tool.name)}
              title="Copy tool name"
            >
              <Copy className="h-3 w-3" />
            </Button>
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
                      <Badge variant="destructive" className="ml-2">required</Badge>
                    )}
                    {!param.required && (
                      <Badge variant="secondary" className="ml-2">optional</Badge>
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
    </div>
  );
}
```

### Component: MCPPromptsList

**Features:**
- Similar to tools but shows arguments instead of parameters
- Template preview (first 2-3 lines with "..." if longer)
- "Use this prompt" button that opens argument fill dialog

```typescript
export function MCPPromptsList({ prompts }: { prompts: MCPPrompt[] }) {
  const [selectedPrompt, setSelectedPrompt] = useState<MCPPrompt | null>(null);

  return (
    <>
      <div className="space-y-2">
        {prompts.map(prompt => (
          <div key={prompt.name} className="border rounded p-3">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="font-medium">{prompt.displayName}</div>
                <p className="text-sm text-muted-foreground">{prompt.description}</p>

                {prompt.arguments && (
                  <div className="mt-2 text-sm">
                    <span className="font-medium">Arguments: </span>
                    {prompt.arguments.map(arg => (
                      <span key={arg.name} className="mr-2">
                        <code>{arg.name}</code>
                        {arg.required && <span className="text-red-500">*</span>}
                      </span>
                    ))}
                  </div>
                )}

                {prompt.template && (
                  <div className="mt-2 text-xs text-muted-foreground font-mono bg-muted p-2 rounded">
                    {prompt.template.split('\n').slice(0, 3).join('\n')}
                    {prompt.template.split('\n').length > 3 && '\n...'}
                  </div>
                )}
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedPrompt(prompt)}
              >
                Use this prompt →
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Prompt argument fill dialog would go here */}
    </>
  );
}
```

### Component: MCPResourcesList

**Features:**
- Shows full URI
- Template indicator badge if URI contains `{params}`
- Lists extracted template parameters
- MIME type indicator
- Copy URI button

```typescript
export function MCPResourcesList({ resources }: { resources: MCPResource[] }) {
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
```

---

## Feature 2: Add Existing Server

### Overview

Allow users to connect to existing/running MCP servers via HTTP, stdio, or SSE.

### User Flow

**Step 1: Add Server Dialog - Choose Type**

```
┌─────────────────────────────────────────┐
│ Add MCP Server                     [×]  │
├─────────────────────────────────────────┤
│ Choose how to add your server:          │
│                                          │
│ ┌─────────────────────────────────┐    │
│ │ 🌐 Connect to Existing Server   │    │
│ │ Connect to a running MCP server │    │
│ │              [Select →]          │    │
│ └─────────────────────────────────┘    │
│                                          │
│ ┌─────────────────────────────────┐    │
│ │ ⚡ Create New with FastMCP      │    │
│ │ Generate a custom server        │    │
│ │              [Select →]          │    │
│ └─────────────────────────────────┘    │
│                                          │
│                            [Cancel]     │
└─────────────────────────────────────────┘
```

**Step 2: Choose Connection Type**

```
┌─────────────────────────────────────────┐
│ Connect to Existing Server              │
├─────────────────────────────────────────┤
│ Select connection type:                  │
│                                          │
│ ○ HTTP/HTTPS                            │
│   REST API endpoint                      │
│   Example: http://localhost:8000        │
│                                          │
│ ○ stdio (Standard I/O)                  │
│   Execute local command                  │
│   Example: python server.py             │
│                                          │
│ ○ SSE (Server-Sent Events)              │
│   Event stream connection                │
│   Example: http://localhost:8000/events │
│                                          │
│                    [← Back] [Next →]    │
└─────────────────────────────────────────┘
```

**Step 3a: HTTP Connection Details**

```
┌─────────────────────────────────────────┐
│ HTTP Server Configuration               │
├─────────────────────────────────────────┤
│ Basic Information                        │
│                                          │
│ Server Name *                            │
│ [My Custom Server_______________]       │
│                                          │
│ Description                              │
│ [Custom MCP server for...______]        │
│                                          │
│ Base URL *                               │
│ [http://localhost:8000_________]        │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Authentication                           │
│                                          │
│ Auth Type                                │
│ ○ None                                   │
│ ○ API Key                                │
│ ○ Bearer Token                           │
│                                          │
│ [If API Key selected]                   │
│ API Key *                                │
│ [••••••••••••••••••••] [👁️ Show]        │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Custom Headers (optional)                │
│ [+ Add Header]                           │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Save to:                                 │
│ ○ Global (~/.auto-claude/)              │
│ ○ Project (./auto-claude/)              │
│                                          │
│                    [← Back] [Next →]    │
└─────────────────────────────────────────┘
```

**Step 3b: stdio Connection Details**

```
┌─────────────────────────────────────────┐
│ stdio Server Configuration              │
├─────────────────────────────────────────┤
│ Basic Information                        │
│                                          │
│ Server Name *                            │
│ [My stdio Server________________]       │
│                                          │
│ Description                              │
│ [Local MCP server via...________]       │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Command Configuration                    │
│                                          │
│ Command *                                │
│ [python3_______] [📁 Browse]            │
│                                          │
│ Arguments                                │
│ [server.py --port 8000_________]        │
│                                          │
│ Working Directory (optional)             │
│ [/path/to/server/_______________] [📁]  │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Environment Variables (optional)         │
│ [+ Add Variable]                         │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Save to:                                 │
│ ○ Global (~/.auto-claude/)              │
│ ○ Project (./auto-claude/)              │
│                                          │
│                    [← Back] [Next →]    │
└─────────────────────────────────────────┘
```

**Step 3c: SSE Connection Details**

```
┌─────────────────────────────────────────┐
│ SSE Server Configuration                │
├─────────────────────────────────────────┤
│ Basic Information                        │
│                                          │
│ Server Name *                            │
│ [My SSE Server__________________]       │
│                                          │
│ Description                              │
│ [Event stream MCP server________]       │
│                                          │
│ SSE Endpoint URL *                       │
│ [http://localhost:8000/events__]        │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Connection Options                       │
│                                          │
│ ☑ Auto-reconnect on disconnect          │
│                                          │
│ Reconnect Delay (seconds)                │
│ [5____]                                  │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Authentication (same as HTTP)            │
│ ...                                      │
│                                          │
│                    [← Back] [Next →]    │
└─────────────────────────────────────────┘
```

**Step 4: Test Connection & Auto-Discovery**

```
┌─────────────────────────────────────────┐
│ Test Connection & Discover              │
├─────────────────────────────────────────┤
│ Testing connection...                    │
│ [════════════════════] 100%              │
│                                          │
│ ✓ Connection successful                 │
│ ✓ Server responding                      │
│ ✓ Discovering capabilities...            │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Capabilities Found:                      │
│                                          │
│ 🔧 Tools: 12                             │
│   • custom_tool_1                        │
│   • custom_tool_2                        │
│   • ... (10 more)                        │
│                                          │
│ 📝 Prompts: 3                            │
│   • analyze-code                         │
│   • debug-with-context                   │
│   • review-pr                            │
│                                          │
│ 📁 Resources: 5                          │
│   • myserver://docs/{id}                 │
│   • myserver://config                    │
│   • ... (3 more)                         │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ ☑ Enable server immediately              │
│                                          │
│            [← Back] [Add Server]        │
└─────────────────────────────────────────┘
```

### Component: AddServerDialog

```typescript
export function AddServerDialog({ open, onClose }: AddServerDialogProps) {
  const [mode, setMode] = useState<'choose' | 'existing' | 'fastmcp'>('choose');

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        {mode === 'choose' && (
          <div className="space-y-4">
            <DialogTitle>Add MCP Server</DialogTitle>
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
          </div>
        )}

        {mode === 'existing' && (
          <AddExistingServerForm onBack={() => setMode('choose')} onComplete={onClose} />
        )}

        {mode === 'fastmcp' && (
          <FastMCPWizard onBack={() => setMode('choose')} onComplete={onClose} />
        )}
      </DialogContent>
    </Dialog>
  );
}
```

### Component: AddExistingServerForm

Multi-step form with validation:

```typescript
export function AddExistingServerForm({ onBack, onComplete }: FormProps) {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [connectionType, setConnectionType] = useState<'http' | 'stdio' | 'sse'>('http');
  const [config, setConfig] = useState<CustomServerConfig>({ /* ... */ });
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  // Step 1: Choose connection type
  // Step 2: Fill connection details
  // Step 3: Test & discover
  // Step 4: Confirm & save

  const handleTest = async () => {
    setTesting(true);
    const result = await window.electronAPI.mcp.testConnection(config);
    setTestResult(result);
    setTesting(false);
  };

  const handleSave = async () => {
    await window.electronAPI.mcp.addCustomServer(config);
    onComplete();
  };

  // Render appropriate step UI
}
```

---

## Feature 3: FastMCP Wizard

### Overview

4-step wizard to generate FastMCP server code with tools/prompts/resources.

### Wizard Steps

**Step 1: Server Details**

```typescript
interface ServerDetails {
  name: string;        // Alphanumeric + hyphens only
  description: string;
  version: string;     // Semver format
  port?: number;       // Optional, auto-assign if empty
}
```

**UI:**
```
┌─────────────────────────────────────────┐
│ Create FastMCP Server - Step 1/4   [×] │
├─────────────────────────────────────────┤
│ Server Information                       │
│                                          │
│ Server Name *                            │
│ [my-project-tools____________]          │
│ Alphanumeric and hyphens only           │
│                                          │
│ Description                              │
│ [Custom tools for my project...]        │
│                                          │
│ Version                                  │
│ [1.0.0]                                  │
│                                          │
│ Port (optional)                          │
│ [8000] Auto-assign if empty             │
│                                          │
│              [Cancel] [Next: Add Tools →]│
└─────────────────────────────────────────┘
```

**Step 2: Add Tools (Optional)**

```
┌─────────────────────────────────────────┐
│ Create FastMCP Server - Step 2/4        │
├─────────────────────────────────────────┤
│ Add Tools (executable functions)        │
│                                          │
│ ┌─────────────────────────────────┐    │
│ │ ✓ analyze_code                  │    │
│ │   Analyze Python code quality   │    │
│ │   Returns: object               │    │
│ │   Parameters: 2                 │    │
│ │   [Edit] [Remove] [↕ Reorder]   │    │
│ └─────────────────────────────────┘    │
│                                          │
│ ┌─────────────────────────────────┐    │
│ │ ✓ run_tests                     │    │
│ │   Execute project test suite    │    │
│ │   Returns: object               │    │
│ │   Parameters: 1                 │    │
│ │   [Edit] [Remove] [↕]           │    │
│ └─────────────────────────────────┘    │
│                                          │
│ [+ Add Tool]                             │
│                                          │
│ Tools allow agents to execute functions │
│ and interact with external systems.     │
│                                          │
│        [← Back] [Skip] [Next: Prompts →]│
└─────────────────────────────────────────┘
```

**Add/Edit Tool Dialog:**
```
┌─────────────────────────────────────────┐
│ Add Tool                            [×] │
├─────────────────────────────────────────┤
│ Tool Name *                              │
│ [analyze_code_______________]           │
│ Use snake_case format                   │
│                                          │
│ Description *                            │
│ [Analyze Python code quality and...]    │
│                                          │
│ Return Type                              │
│ ○ string  ○ number  ○ boolean           │
│ ● object  ○ array                        │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Parameters                               │
│                                          │
│ ┌─────────────────────────────────┐    │
│ │ file_path (string, required)    │    │
│ │ Path to Python file             │    │
│ │ [Edit] [Remove] [↕]             │    │
│ └─────────────────────────────────┘    │
│                                          │
│ ┌─────────────────────────────────┐    │
│ │ rules (array, optional)         │    │
│ │ Linting rules to apply          │    │
│ │ Default: []                      │    │
│ │ [Edit] [Remove] [↕]             │    │
│ └─────────────────────────────────┘    │
│                                          │
│ [+ Add Parameter]                        │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Code Preview:                            │
│ ```python                                │
│ @mcp.tool()                              │
│ def analyze_code(                        │
│     file_path: str,                      │
│     rules: list = []                     │
│ ) -> dict:                               │
│     """Analyze Python code quality"""   │
│     # Your implementation here           │
│     return {}                            │
│ ```                                      │
│                                          │
│                      [Cancel] [Add Tool]│
└─────────────────────────────────────────┘
```

**Step 3: Add Prompts (Optional)**

Similar to Step 2, but for prompts:
- Prompt name (snake_case)
- Description
- Arguments (not parameters - prompts use arguments)
- Template content (large textarea with syntax highlighting)
- Preview shows `@mcp.prompt()` decorator

**Step 4: Add Resources (Optional)**

```
┌─────────────────────────────────────────┐
│ Create FastMCP Server - Step 4/5        │
├─────────────────────────────────────────┤
│ Add Resources (optional)                 │
│                                          │
│ ┌─────────────────────────────────┐    │
│ │ ✓ myserver://docs/{id}          │    │
│ │   Documentation by ID            │    │
│ │   Template params: {id}          │    │
│ │   MIME: application/json         │    │
│ │   [Edit] [Remove]                │    │
│ └─────────────────────────────────┘    │
│                                          │
│ [+ Add Resource]                         │
│                                          │
│ Resources provide data to agents via    │
│ URI templates.                           │
│                                          │
│       [← Back] [Skip] [Next: Review →]  │
└─────────────────────────────────────────┘
```

**Step 5: Review & Generate**

```
┌─────────────────────────────────────────┐
│ Create FastMCP Server - Step 5/5        │
├─────────────────────────────────────────┤
│ Review & Generate                        │
│                                          │
│ Server Summary:                          │
│ • Name: my-project-tools                 │
│ • Description: Custom tools for...       │
│ • Version: 1.0.0                         │
│ • Port: 8000                             │
│ • Tools: 2                               │
│ • Prompts: 1                             │
│ • Resources: 1                           │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Generated Files:                         │
│ 📁 ~/.auto-claude/mcp-servers/           │
│    my-project-tools/                     │
│   ├─ 📄 server.py (FastMCP code)        │
│   ├─ 📄 requirements.txt                │
│   ├─ 📄 README.md                       │
│   └─ 📄 .env.example                    │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Post-Generation Options:                 │
│                                          │
│ ☑ Install dependencies automatically    │
│   (pip install -r requirements.txt)     │
│                                          │
│ ☑ Start server after generation         │
│   (Quick Start)                          │
│                                          │
│ ☑ Add to MCP Manager                    │
│   (Enable immediately)                   │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ The server will be accessible at:       │
│ http://localhost:8000                    │
│                                          │
│            [← Back] [Generate & Start]  │
└─────────────────────────────────────────┘
```

### Generated Code Template

```python
# ~/.auto-claude/mcp-servers/my-project-tools/server.py

"""
My Project Tools
Custom tools for my project

Generated by Auto-Claude MCP Manager
Version: 1.0.0
"""

from fastmcp import FastMCP
from typing import Any, Dict, List
import os

# Initialize FastMCP server
mcp = FastMCP(
    name="my-project-tools",
    version="1.0.0",
    description="Custom tools for my project"
)

# ============================================
# TOOLS
# ============================================

@mcp.tool()
def analyze_code(file_path: str, rules: List[str] = []) -> Dict[str, Any]:
    """
    Analyze Python code quality

    Args:
        file_path: Path to Python file
        rules: Linting rules to apply

    Returns:
        Analysis results
    """
    # TODO: Implement your logic here
    return {
        "file": file_path,
        "issues": [],
        "score": 100
    }

@mcp.tool()
def run_tests(test_path: str) -> Dict[str, Any]:
    """
    Execute project test suite

    Args:
        test_path: Path to test file or directory

    Returns:
        Test results
    """
    # TODO: Implement your logic here
    return {
        "passed": 0,
        "failed": 0,
        "total": 0
    }

# ============================================
# PROMPTS
# ============================================

@mcp.prompt()
def code_review_prompt(file_path: str, focus: str = "general") -> str:
    """
    Generate code review prompt

    Args:
        file_path: Path to file to review
        focus: What to focus on (general, security, performance)

    Returns:
        Formatted prompt
    """
    return f"""
Review the code in {file_path} with focus on {focus}.

Please provide:
1. Overall assessment
2. Key issues or concerns
3. Suggestions for improvement
"""

# ============================================
# RESOURCES
# ============================================

@mcp.resource("myserver://docs/{id}")
def get_documentation(id: str) -> str:
    """
    Documentation by ID

    Args:
        id: Document identifier

    Returns:
        Documentation content
    """
    # TODO: Implement your logic here
    return f"Documentation for {id}"

# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    # Start the MCP server
    mcp.run(port=8000)
```

### Component: FastMCPWizard

```typescript
export function FastMCPWizard({ onBack, onComplete }: WizardProps) {
  const [step, setStep] = useState<1 | 2 | 3 | 4 | 5>(1);
  const [wizardState, setWizardState] = useState<FastMCPWizardState>({
    step: 1,
    serverInfo: { name: '', description: '', version: '1.0.0' },
    tools: [],
    prompts: [],
    resources: []
  });

  const handleGenerate = async () => {
    const outputPath = path.join(
      os.homedir(),
      '.auto-claude',
      'mcp-servers',
      wizardState.serverInfo.name
    );

    const result = await window.electronAPI.mcp.generateFastMCPServer(
      wizardState,
      outputPath
    );

    if (result.success) {
      // Optionally start the server
      if (shouldAutoStart) {
        await window.electronAPI.mcp.startFastMCPServer(result.serverPath);
      }
      onComplete();
    }
  };

  // Render appropriate step
}
```

---

## Feature 4: Process Management

### Overview

Full lifecycle management for FastMCP servers: start, stop, restart, monitor status, view logs.

### UI Components

**Custom Server Card with Process Controls:**

```
┌──────────────────────────────────────────────────┐
│ ⚡ my-project-tools          [🟢 Running]        │
│ Custom tools for my project                      │
│ Port: 8000 • PID: 12345 • Uptime: 2h 15m         │
│ 5 tools • 2 prompts • 1 resource                 │
│                                                   │
│ [⏸ Stop] [🔄 Restart] [📋 Logs] [✏️ Edit] [🗑️]  │
│ [▼ Show Capabilities]                            │
└──────────────────────────────────────────────────┘
```

**Process States:**

```typescript
type ProcessStatus = 'running' | 'stopped' | 'starting' | 'crashed';

interface ProcessInfo {
  pid?: number;
  port?: number;
  status: ProcessStatus;
  uptime?: number;      // seconds
  lastError?: string;
  logFile?: string;
  restartCount?: number;
}
```

**Status Indicators:**
- 🟢 **Running** - Green, shows PID and uptime
- 🔴 **Stopped** - Red, shows "Start" button
- 🟡 **Starting** - Yellow, animated spinner
- 🔴 **Crashed** - Red, shows last error + "Restart" button

### Process Logs Viewer

```
┌────────────────────────────────────────────────────┐
│ Process Logs: my-project-tools              [×]   │
├────────────────────────────────────────────────────┤
│ [All] [Errors] [Warnings] [Info]  [🔍 Search...]  │
│ ☑ Auto-scroll                     [Clear] [Download]│
├────────────────────────────────────────────────────┤
│ [INFO] 2025-12-23 14:30:15 - Server starting...   │
│ [INFO] 2025-12-23 14:30:16 - Loaded 5 tools       │
│ [INFO] 2025-12-23 14:30:16 - Server running on... │
│ [DEBUG] 2025-12-23 14:30:20 - Tool called: analy..│
│ [ERROR] 2025-12-23 14:30:25 - Tool failed: Modul..│
│ [WARN] 2025-12-23 14:30:30 - High memory usage   │
│                                                    │
│ ...                                                │
│                                                    │
│                                                    │
└────────────────────────────────────────────────────┘
```

**Features:**
- Real-time streaming (tail -f style)
- Auto-scroll toggle
- Filters: All / Errors / Warnings / Info / Debug
- Search with highlight
- Clear logs
- Download as .txt file
- Color coding by log level

### Auto-Recovery

**Strategy:**
- Crash detected → Wait 1 second → Restart (attempt 1)
- Crash again → Wait 2 seconds → Restart (attempt 2)
- Crash again → Wait 4 seconds → Restart (attempt 3)
- 3 failures → Stop auto-restart, notify user, manual restart only

**Toast Notification:**
```
⚠️ Server "my-project-tools" crashed 3 times

Last error: ModuleNotFoundError: No module named 'fastmcp'

[View Logs] [Install Dependencies] [Restart Manually]
```

### Component: ServerProcessControls

```typescript
export function ServerProcessControls({ server }: { server: MCPServer }) {
  const [logsOpen, setLogsOpen] = useState(false);
  const processInfo = server.processInfo;

  const handleStart = async () => {
    await window.electronAPI.mcp.startFastMCPServer(server.customConfig.sourceFiles.serverPy);
  };

  const handleStop = async () => {
    await window.electronAPI.mcp.stopFastMCPServer(server.id);
  };

  const handleRestart = async () => {
    await window.electronAPI.mcp.restartFastMCPServer(server.id);
  };

  if (processInfo?.status === 'stopped') {
    return (
      <Button onClick={handleStart} size="sm">
        <Play className="h-4 w-4 mr-2" />
        Start
      </Button>
    );
  }

  if (processInfo?.status === 'running') {
    return (
      <div className="flex gap-2">
        <Button onClick={handleStop} size="sm" variant="outline">
          <Square className="h-4 w-4 mr-2" />
          Stop
        </Button>
        <Button onClick={handleRestart} size="sm" variant="outline">
          <RotateCw className="h-4 w-4 mr-2" />
          Restart
        </Button>
        <Button onClick={() => setLogsOpen(true)} size="sm" variant="outline">
          <FileText className="h-4 w-4 mr-2" />
          Logs
        </Button>
      </div>
    );
  }

  // starting or crashed states...
}
```

### Main Process: Process Manager

```typescript
// main/mcp-fastmcp.ts

import { spawn, ChildProcess } from 'child_process';
import { ipcMain } from 'electron';

const runningProcesses = new Map<string, ChildProcess>();

ipcMain.handle('mcp:start-fastmcp-server', async (event, serverPath: string) => {
  try {
    const process = spawn('python', ['-m', 'fastmcp', 'run', serverPath], {
      cwd: path.dirname(serverPath),
      env: { ...process.env }
    });

    const serverId = path.basename(path.dirname(serverPath));
    runningProcesses.set(serverId, process);

    // Capture logs
    process.stdout.on('data', (data) => {
      appendLog(serverId, 'INFO', data.toString());
    });

    process.stderr.on('data', (data) => {
      appendLog(serverId, 'ERROR', data.toString());
    });

    process.on('exit', (code) => {
      if (code !== 0) {
        handleCrash(serverId, code);
      }
      runningProcesses.delete(serverId);
    });

    return { success: true, pid: process.pid };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('mcp:stop-fastmcp-server', async (event, serverId: string) => {
  const process = runningProcesses.get(serverId);
  if (process) {
    process.kill('SIGTERM');
    return { success: true };
  }
  return { success: false, error: 'Process not found' };
});

// Auto-recovery logic
let restartAttempts = new Map<string, number>();

async function handleCrash(serverId: string, exitCode: number) {
  const attempts = restartAttempts.get(serverId) || 0;

  if (attempts < 3) {
    const delay = Math.pow(2, attempts) * 1000; // 1s, 2s, 4s
    setTimeout(() => {
      startFastMCPServer(serverId);
      restartAttempts.set(serverId, attempts + 1);
    }, delay);
  } else {
    // Notify user via main window
    notifyUser({
      type: 'error',
      title: 'Server Crashed',
      message: `Server "${serverId}" crashed 3 times. Manual restart required.`
    });
    restartAttempts.delete(serverId);
  }
}
```

---

## Feature 5: Server CRUD Operations

### Edit Server

**UI:**
```
┌─────────────────────────────────────────┐
│ Edit Server: my-custom-http        [×] │
├─────────────────────────────────────────┤
│ [Tabs: Basic Info | Connection | Advanced]│
├─────────────────────────────────────────┤
│ Basic Info                               │
│                                          │
│ Server Name *                            │
│ [my-custom-http_____________]           │
│                                          │
│ Description                              │
│ [Custom HTTP MCP server_____]           │
│                                          │
│ Connection Type: HTTP (read-only)       │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Connection Details                       │
│                                          │
│ Base URL *                               │
│ [http://localhost:9000_________]        │
│                                          │
│ [Test Connection]                        │
│ ✓ Connection successful                 │
│                                          │
│ ─────────────────────────────────────   │
│                                          │
│ Scope                                    │
│ ● Global (~/.auto-claude/)              │
│ ○ Project (./auto-claude/)              │
│                                          │
│               [Cancel] [Save Changes]   │
└─────────────────────────────────────────┘
```

**For FastMCP Servers:**
- Can edit tools/prompts/resources
- Re-generates `server.py` with changes
- Asks: "Server is running. Restart now?"
- Option to keep old version as backup

### Delete Server

**Confirmation Dialog:**
```
┌────────────────────────────────────┐
│ Delete MCP Server?            [×] │
├────────────────────────────────────┤
│ ⚠️  Are you sure?                  │
│                                    │
│ Server: my-project-tools           │
│ Type: Custom (FastMCP)             │
│                                    │
│ This will:                         │
│ • Stop the running process (PID...)│
│ • Remove from MCP Manager          │
│ • Remove from registry.json        │
│                                    │
│ ☐ Also delete server files        │
│   (~/.auto-claude/mcp-servers/...) │
│   (Cannot be undone!)              │
│                                    │
│ Type server name to confirm:       │
│ [_________________________]        │
│                                    │
│         [Cancel] [Delete Server]  │
└────────────────────────────────────┘
```

**Safety:**
- Requires typing exact server name
- Built-in servers cannot be deleted (only disabled)
- Warns if server is currently running
- Option to keep or delete files
- Stops process before deleting

### Duplicate Server

**Flow:**
1. Copy entire configuration
2. Add " (copy)" to name
3. Open Edit dialog pre-filled
4. User can modify before saving
5. For FastMCP: copies code files to new directory

**Use case:** Create variant server with different config/tools

### Export/Import

**Export Single Server:**
```json
{
  "version": "1.0",
  "exportedAt": "2025-12-23T14:30:00Z",
  "server": {
    "name": "my-custom-http",
    "description": "Custom HTTP MCP server",
    "type": "custom",
    "customConfig": {
      "connectionType": "http",
      "baseUrl": "http://localhost:9000",
      "authType": "bearer",
      "authValue": "REDACTED"
    },
    "requiredEnvVars": ["CUSTOM_API_KEY"]
  }
}
```

**Export All Servers:**
```json
{
  "version": "1.0",
  "exportedAt": "2025-12-23T14:30:00Z",
  "servers": [
    { /* server 1 */ },
    { /* server 2 */ },
    { /* server 3 */ }
  ]
}
```

**Import Dialog:**
```
┌────────────────────────────────────┐
│ Import MCP Server Config      [×] │
├────────────────────────────────────┤
│ Import Method:                     │
│                                    │
│ ○ Upload JSON File                │
│   [Choose File]                    │
│                                    │
│ ○ Paste JSON                       │
│   [Show text area]                 │
│                                    │
│ ─────────────────────────────────  │
│                                    │
│ [After selecting file/pasting]     │
│                                    │
│ ✓ Valid configuration found        │
│                                    │
│ Servers to import: 3               │
│ • my-custom-http                   │
│ • another-server                   │
│ • third-server ⚠️  (already exists)│
│                                    │
│ Conflict Resolution:               │
│ ○ Skip existing servers            │
│ ○ Overwrite existing servers       │
│ ○ Rename imported (add suffix)     │
│                                    │
│           [Cancel] [Import]       │
└────────────────────────────────────┘
```

**Validation:**
- Schema validation (JSON structure)
- Required fields check
- Connection type validity
- Name uniqueness

---

## Data Models & Storage

### Extended TypeScript Types

```typescript
// shared/types/mcp.ts (UPDATES)

export interface MCPServer {
  // ... existing fields

  // Custom server fields
  isCustom?: boolean;
  customConfig?: CustomServerConfig;
  processInfo?: ProcessInfo;
  editableFields?: string[];  // Which fields can be edited
  createdAt?: string;
  updatedAt?: string;
}

export interface CustomServerConfig {
  connectionType: 'http' | 'stdio' | 'sse';

  // HTTP/SSE fields
  baseUrl?: string;
  authType?: 'none' | 'api-key' | 'bearer';
  authValue?: string;
  headers?: Record<string, string>;

  // stdio fields
  command?: string;
  args?: string[];
  workingDir?: string;
  env?: Record<string, string>;

  // SSE specific
  reconnectOnDisconnect?: boolean;
  reconnectDelay?: number;

  // FastMCP specific
  isFastMCP?: boolean;
  generatedFrom?: 'wizard' | 'manual';
  sourceFiles?: {
    serverPy: string;
    requirementsTxt: string;
    readmeMd: string;
  };
}

export interface ProcessInfo {
  pid?: number;
  port?: number;
  status: 'running' | 'stopped' | 'starting' | 'crashed';
  uptime?: number;        // seconds
  startedAt?: string;     // ISO timestamp
  lastError?: string;
  logFile?: string;
  restartCount?: number;
}

export interface MCPServerExport {
  version: '1.0';
  exportedAt: string;
  server: {
    name: string;
    description: string;
    type: MCPServerType;
    customConfig: CustomServerConfig;
    requiredEnvVars: string[];
  };
}

export interface MCPServersExport {
  version: '1.0';
  exportedAt: string;
  servers: MCPServerExport['server'][];
}
```

### Storage Strategy

**Built-in Servers:**
- Hardcoded in `main/mcp-manager.ts`
- Configuration (credentials): `.env` files
- No persistence needed for server definitions

**Custom Servers:**

**Registry File:** `~/.auto-claude/mcp-servers/registry.json`
```json
{
  "version": "1.0",
  "servers": [
    {
      "id": "my-custom-http",
      "name": "My Custom HTTP Server",
      "description": "Custom HTTP MCP server",
      "type": "custom",
      "isCustom": true,
      "customConfig": {
        "connectionType": "http",
        "baseUrl": "http://localhost:9000",
        "authType": "bearer"
      },
      "createdAt": "2025-12-23T14:00:00Z",
      "updatedAt": "2025-12-23T14:30:00Z"
    },
    {
      "id": "my-fastmcp-tools",
      "name": "My Project Tools",
      "description": "Custom tools for my project",
      "type": "custom",
      "isCustom": true,
      "customConfig": {
        "connectionType": "http",
        "isFastMCP": true,
        "generatedFrom": "wizard",
        "sourceFiles": {
          "serverPy": "/Users/user/.auto-claude/mcp-servers/my-project-tools/server.py",
          "requirementsTxt": "/Users/user/.auto-claude/mcp-servers/my-project-tools/requirements.txt",
          "readmeMd": "/Users/user/.auto-claude/mcp-servers/my-project-tools/README.md"
        }
      },
      "processInfo": {
        "port": 8000,
        "status": "running",
        "startedAt": "2025-12-23T12:00:00Z"
      },
      "createdAt": "2025-12-23T10:00:00Z",
      "updatedAt": "2025-12-23T12:00:00Z"
    }
  ]
}
```

**FastMCP Server Files:**
```
~/.auto-claude/mcp-servers/
├── registry.json
├── .pids/
│   ├── my-project-tools.json      # PID tracking
│   └── another-server.json
├── my-project-tools/
│   ├── server.py                   # Generated code
│   ├── requirements.txt
│   ├── README.md
│   ├── .env.example
│   └── logs/
│       └── server.log              # Process logs
└── another-server/
    ├── server.py
    ├── requirements.txt
    └── ...
```

**Project-Scoped Servers:**
```
{project-path}/auto-claude/
└── .mcp-servers.json               # Similar to registry.json
```

**Note:** FastMCP code is always global (`~/.auto-claude/mcp-servers/`), but can be referenced from project config.

### IPC Handler Updates

```typescript
// main/mcp-manager.ts (UPDATES)

// Load all servers (built-in + custom)
ipcMain.handle('mcp:list', async (event, projectPath?: string) => {
  const builtInServers = getBuiltInServers();
  const customServers = await loadCustomServers(projectPath);
  return [...builtInServers, ...customServers];
});

// Add custom server
ipcMain.handle('mcp:add-custom-server', async (event, config: CustomServerConfig, scope: 'global' | 'project', projectPath?: string) => {
  const registry = await loadRegistry(scope, projectPath);

  const newServer: MCPServer = {
    id: generateId(config.name),
    name: config.name,
    description: config.description || '',
    type: 'custom',
    isCustom: true,
    customConfig: config,
    status: 'disconnected',
    enabled: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    // ... other fields
  };

  registry.servers.push(newServer);
  await saveRegistry(registry, scope, projectPath);

  return { success: true, serverId: newServer.id };
});

// Edit server
ipcMain.handle('mcp:edit-server', async (event, serverId: string, updates: Partial<MCPServer>) => {
  const registry = await loadRegistry();
  const server = registry.servers.find(s => s.id === serverId);

  if (!server) {
    return { success: false, error: 'Server not found' };
  }

  Object.assign(server, updates);
  server.updatedAt = new Date().toISOString();

  await saveRegistry(registry);

  // If FastMCP and tools/prompts changed, regenerate server.py
  if (server.customConfig?.isFastMCP && updates.capabilities) {
    await regenerateFastMCPServer(server);
  }

  return { success: true };
});

// Delete server
ipcMain.handle('mcp:delete-server', async (event, serverId: string, deleteFiles: boolean) => {
  const registry = await loadRegistry();
  const serverIndex = registry.servers.findIndex(s => s.id === serverId);

  if (serverIndex === -1) {
    return { success: false, error: 'Server not found' };
  }

  const server = registry.servers[serverIndex];

  // Stop process if running
  if (server.processInfo?.status === 'running') {
    await stopFastMCPServer(serverId);
  }

  // Remove from registry
  registry.servers.splice(serverIndex, 1);
  await saveRegistry(registry);

  // Optionally delete files
  if (deleteFiles && server.customConfig?.sourceFiles) {
    const serverDir = path.dirname(server.customConfig.sourceFiles.serverPy);
    await fs.rm(serverDir, { recursive: true, force: true });
  }

  return { success: true };
});

// Duplicate server
ipcMain.handle('mcp:duplicate-server', async (event, serverId: string) => {
  const registry = await loadRegistry();
  const original = registry.servers.find(s => s.id === serverId);

  if (!original) {
    return { success: false, error: 'Server not found' };
  }

  const duplicate = JSON.parse(JSON.stringify(original));
  duplicate.id = generateId(original.name + '-copy');
  duplicate.name = original.name + ' (copy)';
  duplicate.createdAt = new Date().toISOString();
  duplicate.updatedAt = new Date().toISOString();

  // For FastMCP, copy files to new directory
  if (duplicate.customConfig?.isFastMCP) {
    const newDir = path.join(
      os.homedir(),
      '.auto-claude',
      'mcp-servers',
      duplicate.id
    );
    await fs.cp(
      path.dirname(original.customConfig.sourceFiles.serverPy),
      newDir,
      { recursive: true }
    );
    duplicate.customConfig.sourceFiles.serverPy = path.join(newDir, 'server.py');
    // Update other file paths...
  }

  registry.servers.push(duplicate);
  await saveRegistry(registry);

  return { success: true, serverId: duplicate.id };
});

// Export/Import
ipcMain.handle('mcp:export-config', async (event, serverId?: string) => {
  const registry = await loadRegistry();

  if (serverId) {
    // Export single server
    const server = registry.servers.find(s => s.id === serverId);
    if (!server) {
      return { success: false, error: 'Server not found' };
    }

    const exported: MCPServerExport = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      server: {
        name: server.name,
        description: server.description,
        type: server.type,
        customConfig: server.customConfig,
        requiredEnvVars: server.requiredEnvVars || []
      }
    };

    return { success: true, data: exported };
  } else {
    // Export all servers
    const exported: MCPServersExport = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      servers: registry.servers.map(s => ({
        name: s.name,
        description: s.description,
        type: s.type,
        customConfig: s.customConfig,
        requiredEnvVars: s.requiredEnvVars || []
      }))
    };

    return { success: true, data: exported };
  }
});

ipcMain.handle('mcp:import-config', async (event, importData: MCPServerExport | MCPServersExport, conflictResolution: 'skip' | 'overwrite' | 'rename') => {
  // Validate JSON schema
  if (!validateImportSchema(importData)) {
    return { success: false, error: 'Invalid configuration format' };
  }

  const registry = await loadRegistry();
  const serversToImport = 'servers' in importData ? importData.servers : [importData.server];

  for (const serverData of serversToImport) {
    const existingIndex = registry.servers.findIndex(s => s.name === serverData.name);

    if (existingIndex !== -1) {
      // Conflict
      if (conflictResolution === 'skip') {
        continue;
      } else if (conflictResolution === 'overwrite') {
        registry.servers[existingIndex] = createServerFromImport(serverData);
      } else if (conflictResolution === 'rename') {
        serverData.name = serverData.name + ' (imported)';
        registry.servers.push(createServerFromImport(serverData));
      }
    } else {
      registry.servers.push(createServerFromImport(serverData));
    }
  }

  await saveRegistry(registry);
  return { success: true, imported: serversToImport.length };
});
```

---

## Error Handling & Validation

### Input Validation

**Server Name:**
- Required field
- Alphanumeric + hyphens only
- Unique across all servers
- Length: 3-50 characters
- Real-time validation with error message

**URL Validation:**
- Valid HTTP/HTTPS format
- Port number if specified
- Reachable (tested during connection test)

**Command Validation (stdio):**
- File exists and is executable
- Command in PATH or absolute path
- Arguments parsed correctly

**Port Validation:**
- Number between 1-65535
- Not already in use by another server
- Available to bind

### Connection Testing

**Test Result Types:**

```typescript
type TestResult =
  | { status: 'success', capabilities: MCPCapabilities }
  | { status: 'connection_failed', error: string, suggestion?: string }
  | { status: 'auth_failed', error: string, suggestion?: string }
  | { status: 'invalid_response', error: string, suggestion?: string }
  | { status: 'timeout', error: string, suggestion?: string };
```

**Error Messages with Suggestions:**

**Connection Failed:**
```
❌ Cannot connect to http://localhost:8000

Possible causes:
• Server is not running
• Port 8000 is blocked by firewall
• Wrong URL or endpoint path

Suggestions:
• Check if server is running: curl http://localhost:8000
• Try different port
• Check firewall settings

[Retry] [Edit URL] [View Logs]
```

**Auth Failed:**
```
❌ Authentication failed (401 Unauthorized)

Your API key may be:
• Incorrect or expired
• Missing required permissions
• From wrong workspace/account

Suggestions:
• Generate new API key
• Check key has correct permissions
• Verify you're using production (not test) key

[Get New Key →] [Try Again] [Contact Support]
```

**Invalid Response:**
```
❌ Invalid MCP response

Server responded but format is incorrect.

Expected: MCP protocol response
Received: {"error": "not found"}

This might not be an MCP server. Please verify the endpoint.

[Check Documentation] [Try Different URL]
```

**Timeout:**
```
❌ Connection timeout after 10 seconds

Server did not respond in time.

Possible causes:
• Server is slow to start
• Network latency
• Server hung or crashed

[Increase Timeout] [Retry] [View Server Logs]
```

### Process Crash Handling

**Auto-Recovery Strategy:**

```typescript
// Exponential backoff with maximum attempts
const MAX_RESTART_ATTEMPTS = 3;
const BACKOFF_DELAYS = [1000, 2000, 4000]; // 1s, 2s, 4s

async function handleProcessCrash(serverId: string, exitCode: number, signal: string) {
  const attempts = restartAttempts.get(serverId) || 0;

  if (attempts < MAX_RESTART_ATTEMPTS) {
    const delay = BACKOFF_DELAYS[attempts];

    logger.warn(`Server ${serverId} crashed (exit code ${exitCode}). Restarting in ${delay}ms... (attempt ${attempts + 1}/${MAX_RESTART_ATTEMPTS})`);

    setTimeout(async () => {
      try {
        await startFastMCPServer(serverId);
        restartAttempts.set(serverId, attempts + 1);
      } catch (error) {
        logger.error(`Failed to restart server ${serverId}:`, error);
      }
    }, delay);
  } else {
    // Max attempts reached
    logger.error(`Server ${serverId} crashed ${MAX_RESTART_ATTEMPTS} times. Giving up.`);

    // Notify user
    notifyUser({
      type: 'error',
      title: `Server "${serverId}" Failed`,
      message: `Server crashed ${MAX_RESTART_ATTEMPTS} times. Manual restart required.`,
      actions: [
        { label: 'View Logs', action: () => openLogsViewer(serverId) },
        { label: 'Restart', action: () => restartFastMCPServer(serverId) }
      ]
    });

    restartAttempts.delete(serverId);
  }
}
```

**Crash Notification:**
```
┌────────────────────────────────────────┐
│ ⚠️  Server Crashed                     │
├────────────────────────────────────────┤
│ Server: my-project-tools               │
│ Crashed 3 times in 5 minutes           │
│                                         │
│ Last error:                             │
│ ModuleNotFoundError: No module named   │
│ 'fastmcp'                               │
│                                         │
│ Likely cause:                           │
│ Missing Python dependency               │
│                                         │
│ Suggested fix:                          │
│ pip install -r requirements.txt        │
│                                         │
│ [Install Dependencies] [View Full Logs]│
│ [Restart Server] [Dismiss]             │
└────────────────────────────────────────┘
```

### Rollback on Errors

**Edit Server:**
- Test connection before saving
- If test fails, don't save changes
- Show error, allow user to correct

**Delete Server:**
- Stop process first
- If process stop fails, warn user but allow delete
- Only delete files if explicitly requested and confirmed

**Import:**
- Validate entire import before applying any changes
- If any server invalid, reject entire import
- Show validation errors clearly

### Toast Notifications

**Success:**
```
✓ Server "my-custom-http" added successfully
  Connected • 5 tools available
```

**Error:**
```
✗ Failed to start server "my-project-tools"
  ModuleNotFoundError: No module named 'fastmcp'
  [View Details]
```

**Warning:**
```
⚠ Server "my-project-tools" restarted 3 times in 5 minutes
  Check server logs for issues
  [View Logs]
```

**Info:**
```
ℹ Discovering capabilities for "my-custom-http"...
  This may take a few seconds
```

---

## UI Organization & Navigation

### MCP Manager Layout (Updated)

```
┌───────────────────────────────────────────────────────┐
│ 🔌 MCP Servers      [+ Add Server] [⚙️ Settings] [🔄] │
├───────────────────────────────────────────────────────┤
│ 🔍 [Search servers by name, description, category...] │
├───────────────────────────────────────────────────────┤
│ 📊 12 total • 6 connected • 3 custom • 2 running      │
├───────────────────────────────────────────────────────┤
│ Filters:  [All] [Built-in] [Custom] [Running]        │
│ Sort by:  [Status ▼] [Name] [Type] [Activity]        │
├───────────────────────────────────────────────────────┤
│                                                        │
│ Built-in Servers                                       │
│ ┌────────────────────────────────────────────────┐   │
│ │ 📚 Context7               [🟢 Active]          │   │
│ │ Real-time documentation lookup                 │   │
│ │ 2 tools • 0 prompts • 0 resources              │   │
│ │ [▼ Show Capabilities]                          │   │
│ └────────────────────────────────────────────────┘   │
│                                                        │
│ │ ⚡ Linear                  [⚪ Disabled]        │   │
│ │ Project management integration                 │   │
│ │ Requires: LINEAR_API_KEY                       │   │
│ │ [⚙️ Configure]                                  │   │
│ └────────────────────────────────────────────────┘   │
│                                                        │
│ Custom Servers                                         │
│ ┌────────────────────────────────────────────────┐   │
│ │ ⚡ my-project-tools       [🟢 Running]         │   │
│ │ Custom tools for my project                    │   │
│ │ Port: 8000 • PID: 12345 • Uptime: 2h 15m       │   │
│ │ 5 tools • 2 prompts • 1 resource               │   │
│ │                                                 │   │
│ │ [⏸ Stop] [🔄] [📋] [✏️ Edit] [📋 Dup] [🗑️]    │   │
│ │ [▼ Show Capabilities]                          │   │
│ └────────────────────────────────────────────────┘   │
│                                                        │
│ ┌────────────────────────────────────────────────┐   │
│ │ 🌐 my-http-server        [🔴 Stopped]          │   │
│ │ Custom HTTP MCP server                         │   │
│ │ http://localhost:9000                          │   │
│ │ 8 tools • 0 prompts • 0 resources              │   │
│ │                                                 │   │
│ │ [▶ Start] [✏️ Edit] [📋 Duplicate] [🗑️]       │   │
│ │ [▼ Show Capabilities]                          │   │
│ └────────────────────────────────────────────────┘   │
│                                                        │
│ [Load More...]                                         │
│                                                        │
└───────────────────────────────────────────────────────┘
```

### Action Buttons by Server Type

**Built-in Servers (Enabled):**
- Show Capabilities (expand/collapse)
- Disable (turns off)
- Configure (edit credentials)

**Built-in Servers (Disabled):**
- Configure (setup credentials)
- Show Info (what it does)

**Custom HTTP/stdio/SSE (Connected):**
- Show Capabilities
- Edit (modify config)
- Duplicate (copy config)
- Export (download JSON)
- Delete (remove)
- Disable (disconnect)

**Custom HTTP/stdio/SSE (Disconnected):**
- Test Connection
- Edit
- Duplicate
- Export
- Delete
- Enable (connect)

**Custom FastMCP (Running):**
- Stop (stop process)
- Restart (restart process)
- Logs (view logs)
- Show Capabilities
- Edit (modify + regenerate)
- Duplicate
- Export
- Delete

**Custom FastMCP (Stopped):**
- Start (start process)
- Edit
- Duplicate
- Export
- Delete

### Settings Dropdown (⚙️)

```
┌─────────────────────────────┐
│ ⚙️  Settings                │
├─────────────────────────────┤
│ Import Server Configuration │
│ Export All Servers          │
│ ─────────────────────────── │
│ Process Manager             │
│ Clear Logs                  │
│ ─────────────────────────── │
│ Reset to Defaults           │
└─────────────────────────────┘
```

**Process Manager:**
Shows overview of all FastMCP servers with process status, resource usage, logs.

### Filters & Sorting

**Filters:**
- **All** - Show all servers (built-in + custom)
- **Built-in** - Only built-in servers
- **Custom** - Only custom servers (HTTP/stdio/SSE/FastMCP)
- **Running** - Only servers with running processes
- **Requires Setup** - Disabled servers needing configuration

**Sorting:**
- **By Status** - Connected first, then disabled, then stopped
- **By Name** - Alphabetical A-Z
- **By Type** - Built-in, then custom
- **By Activity** - Recently used first (based on last API call)

### Keyboard Shortcuts

```
Cmd/Ctrl + K      Quick search servers
Cmd/Ctrl + N      Add new server
Cmd/Ctrl + E      Edit selected server
Space             Expand/collapse capabilities
Delete            Delete selected server (with confirmation)
Cmd/Ctrl + D      Duplicate selected server
Cmd/Ctrl + R      Refresh server list
```

### Responsive Design

**Desktop (wide):**
- 2-column layout for server cards
- Full action buttons visible
- Expanded capabilities inline

**Tablet (medium):**
- 1-column layout
- Action buttons in dropdown menu
- Capabilities in modal

**Mobile (narrow):**
- Simplified card view
- Essential info only
- All actions in menu

---

## Implementation Plan

### Phase 1: Capabilities View (2-3 days)

**Tasks:**
1. Create `MCPCapabilitiesView` component with tabs
2. Create `MCPToolsList` component with expandable tools
3. Create `MCPPromptsList` component with "Use prompt" button
4. Create `MCPResourcesList` component with URI display
5. Update `MCPServerCard` to replace placeholder with `MCPCapabilitiesView`
6. Add IPC handler `mcp:get-capabilities` (if not already present)
7. Add real data fetching for capabilities
8. Test with all 6 built-in servers
9. Ensure expand/collapse animation is smooth
10. Add copy-to-clipboard functionality for tool names and URIs

**Deliverables:**
- Users can view detailed tools/prompts/resources for any server
- Full parameter information with types
- Smooth expand/collapse animations
- Copy buttons for easy usage

### Phase 2: Add Existing Server (3-4 days)

**Tasks:**
1. Create `AddServerDialog` with type selection
2. Create `AddExistingServerForm` with multi-step flow
3. Implement HTTP connection form (URL, auth, headers)
4. Implement stdio connection form (command, args, env vars)
5. Implement SSE connection form (endpoint, reconnect options)
6. Add connection testing logic (per connection type)
7. Add auto-discovery of capabilities
8. Add IPC handlers:
   - `mcp:add-custom-server`
   - `mcp:test-custom-connection`
   - `mcp:discover-capabilities`
9. Update `MCPManager` to show custom servers separately
10. Create `CustomServerCard` component
11. Add validation for all inputs
12. Test adding HTTP/stdio/SSE servers
13. Test connection failures and error messages

**Deliverables:**
- Users can add existing MCP servers (HTTP/stdio/SSE)
- Connection testing with helpful error messages
- Auto-discovery of capabilities
- Custom servers appear in MCP Manager

### Phase 3: FastMCP Wizard (4-5 days)

**Tasks:**
1. Create `FastMCPWizard` component with 5 steps
2. Implement Step 1: Server details form
3. Implement Step 2: Add tools with parameter builder
4. Implement Step 3: Add prompts with template editor
5. Implement Step 4: Add resources with URI builder
6. Implement Step 5: Review & generate
7. Create tool/prompt/resource edit dialogs
8. Add drag & drop reordering for parameters
9. Create code generation logic:
   - Generate `server.py` from wizard state
   - Generate `requirements.txt`
   - Generate `README.md`
   - Generate `.env.example`
10. Add IPC handler `mcp:generate-fastmcp-server`
11. Add validation for all wizard inputs
12. Add code preview in wizard
13. Test wizard flow end-to-end
14. Test generated server actually runs

**Deliverables:**
- Complete 5-step wizard for FastMCP generation
- Generated server code is valid and runnable
- User-friendly parameter/argument builders
- Code preview shows what will be generated

### Phase 4: Process Management (3-4 days)

**Tasks:**
1. Create `ServerProcessControls` component
2. Add Start/Stop/Restart buttons
3. Create `ProcessLogsViewer` component
4. Implement real-time log streaming
5. Add log filtering (All/Errors/Warnings/Info)
6. Add log search functionality
7. Add log download as .txt
8. Implement process status tracking (PID, uptime, etc)
9. Add IPC handlers:
   - `mcp:start-fastmcp-server`
   - `mcp:stop-fastmcp-server`
   - `mcp:restart-fastmcp-server`
   - `mcp:get-process-status`
   - `mcp:get-process-logs`
10. Implement auto-recovery logic (3 attempts with backoff)
11. Add crash notifications
12. Update `CustomServerCard` to show process info
13. Test process start/stop/restart
14. Test auto-recovery on crash
15. Test log viewer with real logs

**Deliverables:**
- Users can start/stop/restart FastMCP servers
- Real-time log viewer with filtering
- Process status (PID, uptime) displayed
- Auto-recovery on crashes (3 attempts)
- Crash notifications with helpful suggestions

### Phase 5: Server CRUD (2-3 days)

**Tasks:**
1. Create `ServerEditDialog` component
2. Implement edit flow for custom servers
3. Add re-generation logic for FastMCP edits
4. Create `DeleteConfirmDialog` with server name validation
5. Implement delete with optional file deletion
6. Implement duplicate server functionality
7. Create `ExportImportDialog` component
8. Implement export single server to JSON
9. Implement export all servers to JSON
10. Implement import from JSON with conflict resolution
11. Add schema validation for imports
12. Add IPC handlers:
    - `mcp:edit-server`
    - `mcp:delete-server`
    - `mcp:duplicate-server`
    - `mcp:export-config`
    - `mcp:import-config`
13. Test edit → test → save flow
14. Test delete with file deletion
15. Test export/import round-trip

**Deliverables:**
- Users can edit custom servers
- Users can delete servers (with confirmation)
- Users can duplicate servers
- Users can export/import configurations
- All operations have proper validation

### Phase 6: UI Polish & Testing (2-3 days)

**Tasks:**
1. Add filters (All/Built-in/Custom/Running)
2. Add sorting (Status/Name/Type/Activity)
3. Add keyboard shortcuts
4. Improve search functionality
5. Add loading states and skeletons
6. Add empty states (no servers, no results)
7. Error boundaries for all components
8. Comprehensive error handling
9. Toast notifications for all actions
10. Accessibility improvements (ARIA labels, keyboard nav)
11. Write unit tests for new components
12. Write integration tests for workflows
13. Manual testing on all platforms (macOS/Windows/Linux)
14. Performance testing with 20+ servers
15. Update documentation

**Deliverables:**
- Polished, responsive UI
- Comprehensive error handling
- Full keyboard navigation
- Loading/empty states
- Test coverage >80%
- Updated documentation

**Total Estimated Time:** 16-22 days

---

## Testing Strategy

### Unit Tests

**Component Tests:**

```typescript
// MCPCapabilitiesView.test.tsx
describe('MCPCapabilitiesView', () => {
  it('renders tabs with correct counts', () => {
    const server = mockServerWithCapabilities();
    render(<MCPCapabilitiesView server={server} expanded={true} />);

    expect(screen.getByText('🔧 Tools (5)')).toBeInTheDocument();
    expect(screen.getByText('📝 Prompts (2)')).toBeInTheDocument();
    expect(screen.getByText('📁 Resources (3)')).toBeInTheDocument();
  });

  it('switches tabs on click', () => {
    const server = mockServerWithCapabilities();
    render(<MCPCapabilitiesView server={server} expanded={true} />);

    fireEvent.click(screen.getByText('📝 Prompts (2)'));

    expect(screen.getByText('code-review-prompt')).toBeInTheDocument();
  });
});

// MCPToolsList.test.tsx
describe('MCPToolsList', () => {
  it('expands tool to show parameters', () => {
    const tools = mockTools();
    render(<MCPToolsList tools={tools} />);

    fireEvent.click(screen.getByText('▸ analyze_code'));

    expect(screen.getByText('Parameters:')).toBeInTheDocument();
    expect(screen.getByText('file_path')).toBeInTheDocument();
    expect(screen.getByText('(string)')).toBeInTheDocument();
  });

  it('copies tool name to clipboard', async () => {
    const tools = mockTools();
    render(<MCPToolsList tools={tools} />);

    const copyButton = screen.getAllByTitle('Copy tool name')[0];
    fireEvent.click(copyButton);

    const clipboardText = await navigator.clipboard.readText();
    expect(clipboardText).toBe('mcp__myserver__analyze_code');
  });
});

// AddExistingServerForm.test.tsx
describe('AddExistingServerForm', () => {
  it('validates server name format', () => {
    render(<AddExistingServerForm />);

    const nameInput = screen.getByLabelText('Server Name *');
    fireEvent.change(nameInput, { target: { value: 'Invalid Name!' } });
    fireEvent.blur(nameInput);

    expect(screen.getByText('Use alphanumeric and hyphens only')).toBeInTheDocument();
  });

  it('tests HTTP connection successfully', async () => {
    window.electronAPI.mcp.testConnection = jest.fn().mockResolvedValue({
      status: 'success',
      capabilities: mockCapabilities()
    });

    render(<AddExistingServerForm />);

    // Fill form...
    fireEvent.click(screen.getByText('Next →'));

    await waitFor(() => {
      expect(screen.getByText('✓ Connection successful')).toBeInTheDocument();
    });
  });
});

// FastMCPWizard.test.tsx
describe('FastMCPWizard', () => {
  it('completes full wizard flow', async () => {
    const mockGenerate = jest.fn().mockResolvedValue({
      success: true,
      serverPath: '/path/to/server.py'
    });
    window.electronAPI.mcp.generateFastMCPServer = mockGenerate;

    render(<FastMCPWizard />);

    // Step 1: Server details
    fireEvent.change(screen.getByLabelText('Server Name *'), {
      target: { value: 'my-test-server' }
    });
    fireEvent.click(screen.getByText('Next: Add Tools →'));

    // Step 2: Add tool
    fireEvent.click(screen.getByText('+ Add Tool'));
    // ... fill tool form
    fireEvent.click(screen.getByText('Next: Prompts →'));

    // ... continue through wizard

    fireEvent.click(screen.getByText('Generate & Start'));

    await waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledWith(
        expect.objectContaining({
          serverInfo: { name: 'my-test-server', ... }
        }),
        expect.any(String)
      );
    });
  });
});
```

### Integration Tests

```typescript
// mcp-manager-integration.test.tsx
describe('MCP Manager Integration', () => {
  it('adds HTTP server and views capabilities', async () => {
    render(<MCPManager />);

    // Open add dialog
    fireEvent.click(screen.getByText('+ Add Server'));
    fireEvent.click(screen.getByText('Connect to Existing Server'));

    // Choose HTTP
    fireEvent.click(screen.getByLabelText('HTTP/HTTPS'));
    fireEvent.click(screen.getByText('Next →'));

    // Fill details
    fireEvent.change(screen.getByLabelText('Server Name *'), {
      target: { value: 'test-http-server' }
    });
    fireEvent.change(screen.getByLabelText('Base URL *'), {
      target: { value: 'http://localhost:9000' }
    });

    // Mock test connection
    window.electronAPI.mcp.testConnection = jest.fn().mockResolvedValue({
      status: 'success',
      capabilities: {
        tools: [{ name: 'tool1', displayName: 'Tool 1', description: 'Test tool' }],
        prompts: [],
        resources: []
      }
    });

    fireEvent.click(screen.getByText('Next →'));

    // Wait for test & discovery
    await waitFor(() => {
      expect(screen.getByText('✓ Connection successful')).toBeInTheDocument();
      expect(screen.getByText('🔧 Tools: 1')).toBeInTheDocument();
    });

    // Save
    fireEvent.click(screen.getByText('Add Server'));

    // Server should appear in list
    await waitFor(() => {
      expect(screen.getByText('test-http-server')).toBeInTheDocument();
    });

    // Expand capabilities
    fireEvent.click(screen.getByText('▼ Show Capabilities'));

    expect(screen.getByText('tool1')).toBeInTheDocument();
  });

  it('generates FastMCP server and starts process', async () => {
    window.electronAPI.mcp.generateFastMCPServer = jest.fn().mockResolvedValue({
      success: true,
      serverPath: '/tmp/my-server/server.py'
    });
    window.electronAPI.mcp.startFastMCPServer = jest.fn().mockResolvedValue({
      success: true,
      pid: 12345,
      port: 8000
    });

    render(<MCPManager />);

    // Open wizard
    fireEvent.click(screen.getByText('+ Add Server'));
    fireEvent.click(screen.getByText('Create New with FastMCP'));

    // Complete wizard (simplified)
    // ... steps 1-5

    fireEvent.click(screen.getByText('Generate & Start'));

    await waitFor(() => {
      expect(window.electronAPI.mcp.generateFastMCPServer).toHaveBeenCalled();
      expect(window.electronAPI.mcp.startFastMCPServer).toHaveBeenCalled();
    });

    // Server should appear with "Running" status
    await waitFor(() => {
      expect(screen.getByText('my-server')).toBeInTheDocument();
      expect(screen.getByText('[🟢 Running]')).toBeInTheDocument();
      expect(screen.getByText('PID: 12345')).toBeInTheDocument();
    });
  });

  it('edits server and re-tests connection', async () => {
    // Setup: server already exists
    const mockServers = [
      {
        id: 'custom-1',
        name: 'My Server',
        customConfig: { connectionType: 'http', baseUrl: 'http://localhost:8000' }
      }
    ];
    window.electronAPI.mcp.list = jest.fn().mockResolvedValue(mockServers);

    render(<MCPManager />);

    await waitFor(() => {
      expect(screen.getByText('My Server')).toBeInTheDocument();
    });

    // Click edit
    fireEvent.click(screen.getByText('✏️ Edit'));

    // Change URL
    fireEvent.change(screen.getByLabelText('Base URL *'), {
      target: { value: 'http://localhost:9000' }
    });

    // Test connection
    window.electronAPI.mcp.testConnection = jest.fn().mockResolvedValue({
      status: 'success'
    });

    fireEvent.click(screen.getByText('Test Connection'));

    await waitFor(() => {
      expect(screen.getByText('✓ Connection successful')).toBeInTheDocument();
    });

    // Save
    window.electronAPI.mcp.editServer = jest.fn().mockResolvedValue({ success: true });
    fireEvent.click(screen.getByText('Save Changes'));

    expect(window.electronAPI.mcp.editServer).toHaveBeenCalledWith(
      'custom-1',
      expect.objectContaining({
        customConfig: expect.objectContaining({
          baseUrl: 'http://localhost:9000'
        })
      })
    );
  });
});
```

### Manual Testing Checklist

**Capabilities View:**
- [ ] Tools expand/collapse smoothly
- [ ] All parameter types display correctly (string/number/boolean/object/array)
- [ ] Required/optional badges show correctly
- [ ] Default values display when present
- [ ] Copy tool name works
- [ ] Prompts show arguments correctly
- [ ] Resources show URI templates correctly
- [ ] Template parameters extracted from `{param}` syntax
- [ ] Tabs switch correctly
- [ ] Empty states show when no capabilities

**Add Existing Server:**
- [ ] HTTP form validates URL format
- [ ] stdio form validates command exists
- [ ] SSE form validates endpoint
- [ ] Auth types (none/api-key/bearer) work correctly
- [ ] Custom headers can be added/removed
- [ ] Environment variables can be added/removed
- [ ] Connection test succeeds for valid servers
- [ ] Connection test fails with helpful errors for invalid servers
- [ ] Auto-discovery finds all capabilities
- [ ] Server appears in list after adding
- [ ] Global vs project scope saves correctly

**FastMCP Wizard:**
- [ ] All 5 steps navigate correctly
- [ ] Server name validation works
- [ ] Port validation works (1-65535, not in use)
- [ ] Tools can be added/edited/removed
- [ ] Parameters can be reordered with drag & drop
- [ ] Prompts can be added with templates
- [ ] Resources URI templates work
- [ ] Code preview shows correct Python code
- [ ] Generated server files are valid
- [ ] Generated server runs successfully
- [ ] Auto-start option works

**Process Management:**
- [ ] Start button starts server
- [ ] Stop button stops server
- [ ] Restart button restarts server
- [ ] Process status updates in real-time
- [ ] PID and uptime display correctly
- [ ] Logs viewer shows real-time logs
- [ ] Log filtering works (All/Errors/Warnings/Info)
- [ ] Log search works
- [ ] Log download works
- [ ] Auto-recovery triggers on crash (3 attempts)
- [ ] Crash notification shows after 3 failures
- [ ] Manual restart works after auto-recovery gives up

**Server CRUD:**
- [ ] Edit dialog pre-fills current values
- [ ] Edit saves changes correctly
- [ ] Edit re-tests connection before saving
- [ ] FastMCP edit re-generates code
- [ ] Delete requires server name confirmation
- [ ] Delete stops process before deleting
- [ ] Delete optionally removes files
- [ ] Duplicate creates copy with " (copy)" suffix
- [ ] Duplicate works for HTTP/stdio/SSE/FastMCP
- [ ] Export single server generates valid JSON
- [ ] Export all servers generates valid JSON
- [ ] Import validates JSON schema
- [ ] Import conflict resolution works (skip/overwrite/rename)

**UI/UX:**
- [ ] Filters work (All/Built-in/Custom/Running)
- [ ] Sorting works (Status/Name/Type/Activity)
- [ ] Search finds servers by name/description/category
- [ ] Keyboard shortcuts work
- [ ] Loading states show during async operations
- [ ] Empty states show when no servers
- [ ] Error boundaries catch errors gracefully
- [ ] Toast notifications show for all actions
- [ ] UI responsive on different screen sizes
- [ ] No console errors
- [ ] Smooth animations

**Cross-platform:**
- [ ] Works on macOS
- [ ] Works on Windows
- [ ] Works on Linux
- [ ] File paths work on all platforms
- [ ] Process management works on all platforms

---

## Success Criteria

### Functional Requirements

✅ **Capabilities View:**
- Users can view all tools with full parameter details
- Users can view all prompts with arguments and templates
- Users can view all resources with URI templates
- Copy buttons work for tool names and URIs
- Expandable/collapsible interface is smooth

✅ **Add Existing Server:**
- Users can add HTTP servers with auth
- Users can add stdio servers with commands
- Users can add SSE servers with reconnect options
- Connection testing provides helpful error messages
- Auto-discovery finds all capabilities
- Custom servers appear in MCP Manager

✅ **FastMCP Wizard:**
- Complete 5-step wizard guides server creation
- Users can define tools with parameters
- Users can define prompts with templates
- Users can define resources with URI templates
- Generated code is valid Python with FastMCP
- Generated server runs successfully

✅ **Process Management:**
- Users can start/stop/restart FastMCP servers
- Process status (PID, uptime) displays correctly
- Real-time log viewer with filtering works
- Auto-recovery attempts 3 times on crash
- Crash notifications provide helpful suggestions

✅ **Server CRUD:**
- Users can edit custom servers
- Users can delete servers with confirmation
- Users can duplicate servers
- Users can export/import configurations
- All operations validated and safe

### Non-Functional Requirements

✅ **Performance:**
- Server list loads <500ms for 20 servers
- Capabilities expand <100ms
- Process start/stop <2s
- Log streaming has minimal lag (<100ms)

✅ **Usability:**
- UI follows existing design patterns
- Error messages are clear and actionable
- No complex jargon without explanations
- Keyboard navigation works throughout

✅ **Reliability:**
- No crashes on invalid input
- Graceful degradation on errors
- Auto-recovery for transient failures
- Data loss prevention (confirmations for destructive actions)

✅ **Maintainability:**
- Code follows existing patterns
- Components are reusable
- Types are comprehensive
- Documentation is complete

---

## Conclusion

This comprehensive design extends the MCP Manager with essential features for discoverability, extensibility, and management:

**Capabilities View** replaces the placeholder with full detailed information about tools/prompts/resources, solving the "what does this server do?" problem.

**Custom Server Management** enables users to add any MCP server (HTTP/stdio/SSE) or generate their own with the FastMCP wizard, making the system truly extensible.

**Process Management** provides full lifecycle control for FastMCP servers with auto-recovery, logs, and clear status indicators.

**Server CRUD** gives users complete control with edit/delete/duplicate/export/import operations, all with proper validation and safety measures.

**Impact:**
- Users can see exactly what each MCP server provides
- Users can add any existing MCP server
- Users can create custom servers without writing boilerplate
- Users can manage server lifecycles professionally
- All operations are safe with validation and confirmation

**Next Step:** Create detailed implementation plan with task breakdown for each phase.

---

**Document Version:** 1.0
**Last Updated:** December 23, 2025
**Status:** Ready for Implementation
