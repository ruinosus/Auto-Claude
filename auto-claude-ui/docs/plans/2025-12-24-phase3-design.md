# Phase 3 Design: FastMCP Wizard + Process Management + Server CRUD

**Date:** 2025-12-24
**Status:** Design Complete - Ready for Implementation
**Builds on:** Phase 2 (Add Existing Server functionality)

## Overview

Phase 3 extends MCP Manager with three integrated systems:
1. **FastMCP Wizard** - Hybrid template-based server generation
2. **Process Manager** - Local server process management (Two-Tier approach)
3. **Server CRUD** - Edit, Delete, Duplicate operations

---

## 1. Architecture Overview

### Goal
Extend MCP Manager with FastMCP server generation, local process management, and complete server lifecycle management.

### Three Core Systems

**1. FastMCP Wizard** - Hybrid template-based server generation
- Pre-built templates (File System, API Wrapper, Database, Custom)
- 5-step customization wizard
- Generates complete FastMCP server using **uv** (pyproject.toml + server.py + README)
- Automatically saved as custom server with stdio connection type

**2. Process Manager (Two-Tier)**
- **Tier 1 (Phase 3A):** Full process management for stdio + FastMCP servers
  - Start/stop/restart processes
  - Real-time log viewing
  - Process status monitoring (PID, uptime, memory)
  - Auto-restart on crash (optional)
- **Tier 2 (Phase 3B):** Optional startup scripts for HTTP/SSE servers (deferred to future phase)

**3. Server CRUD**
- **Edit:** Modify any server configuration (reopens appropriate form)
- **Delete:** Remove server from registry with confirmation
- **Duplicate:** Clone server config with new name

### Architecture Pattern
All three systems integrate through:
- Existing `MCPServerCard` component (new action buttons)
- `AddServerDialog` component (two new modes: "fastmcp" and "edit")
- Process management via main process IPC handlers

---

## 2. FastMCP Wizard Design

### User Flow (5 Steps)

#### Step 1: Template Selection
Display 4 template cards with descriptions:

**File System Tools**
- Read/write files, list directories, search content
- Tools: `read_file`, `write_file`, `list_directory`, `search_files`
- Dependencies: `pathlib`, `glob`

**API Wrapper**
- HTTP client with authentication, rate limiting
- Tools: `get_request`, `post_request`, `put_request`, `delete_request`
- Dependencies: `httpx`, `pydantic`

**Database Connector**
- SQL/NoSQL query tools with connection pooling
- Tools: `execute_query`, `fetch_data`, `insert_data`
- Dependencies: `sqlalchemy`, `asyncpg`

**Blank Template**
- Start from scratch with basic FastMCP structure
- Minimal boilerplate code
- Dependencies: `fastmcp` only

Each card shows: icon, description, included tools preview.

#### Step 2: Server Configuration
- **Server name** (required) - Used for directory and project name
- **Description** (optional) - Server purpose
- **Python version** (dropdown: 3.10, 3.11, 3.12, 3.13)
  - uv installs automatically if version not present
  - Creates `.python-version` file
- **Working directory** (default: `~/.auto-claude/fastmcp-servers/{server-name}`)
  - File browser button for custom path

#### Step 3: Tool Customization
- Show template's default tools in editable list
- Each tool: name, description, parameters
- Add/remove/edit tools
- For templates: pre-filled but editable
- For blank: empty list with "Add Tool" button

**Tool Editor Dialog:**
```
Tool Name: [read_file]
Description: [Read contents of a file]
Parameters:
  - name: path, type: string, required: true
  - name: encoding, type: string, required: false, default: "utf-8"
```

#### Step 4: Dependencies
- Auto-detected from template (e.g., `httpx` for API template)
- Editable list of Python packages with version specs
- Format: `package_name>=version` (e.g., `httpx>=0.25.0`)
- Add/remove packages
- uv handles virtual environment automatically (no checkbox needed)

**Example dependency list:**
```
fastmcp>=0.1.0
httpx>=0.25.0
pydantic>=2.0.0
```

#### Step 5: Review & Generate
Preview generated files:

**pyproject.toml** (managed by uv)
```toml
[project]
name = "my-api-server"
version = "0.1.0"
dependencies = [
    "fastmcp>=0.1.0",
    "httpx>=0.25.0",
    "pydantic>=2.0.0"
]

[tool.uv]
dev-dependencies = []
```

**server.py** (generated from template)
```python
from fastmcp import FastMCP

mcp = FastMCP("My API Server")

@mcp.tool()
def get_request(url: str, headers: dict = None):
    """Make HTTP GET request"""
    # Implementation
    pass

# ... other tools
```

**.python-version**
```
3.12
```

**README.md**
```markdown
# My API Server

Generated with Auto-Claude MCP Manager

## Usage
uv run server.py
```

**"Generate & Save" button executes:**
```bash
cd /path/to/working-dir
uv init --name {server-name}
uv add fastmcp {dependencies...}
uv sync  # Creates venv and installs everything
```

Then:
- Adds to custom servers registry as stdio server
- Sets `isFastMCP: true` flag
- Opens process manager to start server

---

## 3. Process Management Design

### UI Components

#### 1. Process Controls (in MCPServerCard)
New action bar appears for stdio/FastMCP servers only.

**Buttons:**
- **Start** (green play icon) - Launches process
  - Shows loading spinner during startup
  - Disabled when running
- **Stop** (red stop icon) - Graceful shutdown
  - 5s timeout, then SIGKILL
  - Disabled when stopped
- **Restart** (blue refresh icon) - Stop + Start sequence
  - Only enabled when running
- **Logs** (gray document icon) - Opens log viewer dialog
  - Shows badge with error count if errors present

**Current state indicator:**
- "Running (PID: 12345, Uptime: 2h 34m)"
- "Stopped"
- "Starting..." (with spinner)
- "Crashed (Exit code: 1)" (with retry button)

#### 2. Process Status Display
Real-time metrics shown when running:

```
Status: ● Running
PID: 12345
Uptime: 2h 34m
Memory: 45.2 MB
Restarts: 0 crashes
Last started: 2025-12-24 10:30:15
```

Health check: Ping server every 30s, mark as crashed if unresponsive.

#### 3. Log Viewer Dialog
Modal dialog with terminal-style log output.

**Features:**
- Auto-scroll to bottom (toggleable switch)
- Search/filter logs (text input with highlight)
- Log levels: All, Info, Warning, Error
- Copy logs to clipboard button
- Download logs as .txt file
- Clear logs button
- Close button

**Layout:**
```
┌─ Server Logs: my-api-server ──────────┐
│ [Search: ___] [●All ○Info ○Warn ○Err] │
│ [Auto-scroll: ✓] [Copy] [Download]    │
├────────────────────────────────────────┤
│ [10:30:15] INFO  Server starting...    │
│ [10:30:16] INFO  Loaded 4 tools       │
│ [10:30:16] INFO  Server ready on :8080│
│ [10:32:44] ERROR Connection failed    │
│ ...                                    │
│ ...                                    │
└────────────────────────────────────────┘
```

Updates in real-time via IPC events from main process.
Shows last 1000 lines (configurable).

### Backend (Main Process)

#### ProcessManager Class
Tracks all running servers.

**State:**
```typescript
interface ProcessState {
  serverId: string;
  pid: number;
  process: ChildProcess;
  startTime: Date;
  logBuffer: string[];  // Last 1000 lines
  restartCount: number;
  autoRestart: boolean;
}

private processes: Map<string, ProcessState> = new Map();
```

**Methods:**
```typescript
async startServer(serverId: string, config: CustomServerConfig)
async stopServer(serverId: string, graceful: boolean = true)
async restartServer(serverId: string)
getProcessStatus(serverId: string): ProcessStatus
getLogBuffer(serverId: string): string[]
```

#### Process Launch with uv
```javascript
// For FastMCP/stdio servers
const process = spawn('uv', ['run', config.command], {
  cwd: config.workingDir,
  env: {
    ...process.env,
    ...config.env  // User-defined env vars
  }
});

// Capture stdout/stderr
process.stdout.on('data', (data) => {
  this.appendLog(serverId, data.toString());
  // Forward to renderer via IPC
  mainWindow.webContents.send('process:log', {
    serverId,
    timestamp: new Date(),
    level: 'info',
    message: data.toString()
  });
});

process.stderr.on('data', (data) => {
  this.appendLog(serverId, data.toString(), 'error');
  mainWindow.webContents.send('process:log', {
    serverId,
    timestamp: new Date(),
    level: 'error',
    message: data.toString()
  });
});

// Handle exit
process.on('exit', (code) => {
  if (code !== 0 && this.processes.get(serverId)?.autoRestart) {
    setTimeout(() => this.restartServer(serverId), 3000);
  }
});
```

#### IPC Handlers
```typescript
// Start server
ipcMain.handle('process:start', async (event, serverId) => {
  const server = await getServerById(serverId);
  return processManager.startServer(serverId, server.customConfig);
});

// Stop server
ipcMain.handle('process:stop', async (event, serverId) => {
  return processManager.stopServer(serverId);
});

// Get logs
ipcMain.handle('process:logs', async (event, serverId) => {
  return processManager.getLogBuffer(serverId);
});

// Stream logs (event-based)
processManager.on('log', (data) => {
  mainWindow.webContents.send('process:log', data);
});
```

---

## 4. Server CRUD Operations

### Edit Server

#### UI Flow
1. New "Edit" button in MCPServerCard dropdown menu (three-dot menu)
2. Clicking Edit:
   - Opens `AddServerDialog` in "edit" mode
   - Pre-populates appropriate form based on connection type:
     - HTTP/SSE → `HttpServerForm` / `SseServerForm`
     - stdio → `StdioServerForm`
     - FastMCP → Custom FastMCP edit form (shows generated files)
   - Shows "Update Server" button instead of "Next"
   - Skips connection test step (server already tested)
   - Updates registry file on save

#### Implementation
```typescript
const handleEdit = (server: MCPServer) => {
  setDialogMode('edit');
  setEditingServer(server);
  setIsDialogOpen(true);
};
```

**AddServerDialog changes:**
```tsx
{mode === 'edit' && (
  <EditServerForm
    server={editingServer}
    onComplete={async (updatedConfig) => {
      await window.electronAPI.mcp.updateServer(
        editingServer.id,
        updatedConfig
      );
      onClose();
      refreshServerList();
    }}
    onCancel={() => setMode('choose')}
  />
)}
```

#### Constraints
- Cannot edit server `type` (http → stdio requires delete + recreate)
- Cannot edit built-in servers (Edit button hidden for `type='builtin'`)
- If server is running, show warning: "Stop server before editing" with Stop button
- FastMCP servers: Can edit metadata but not regenerate (would lose custom changes)

---

### Delete Server

#### UI Flow
1. "Delete" button in MCPServerCard dropdown menu (red text)
2. Confirmation dialog:

```
┌─ Delete Server ──────────────────────┐
│                                       │
│  Are you sure you want to delete:    │
│  "My API Server"?                     │
│                                       │
│  This action cannot be undone.        │
│                                       │
│  [✓] Also delete generated files      │
│      (FastMCP servers only)           │
│                                       │
│  [Cancel]  [Delete Server]            │
│                     ^^^^ red button   │
└───────────────────────────────────────┘
```

3. On confirm:
   - Stop process if running
   - Remove from registry (`~/.auto-claude/mcp-servers.json`)
   - If checkbox selected: Delete working directory
   - Show toast: "Server 'My API Server' deleted"
   - Refresh server list

#### Implementation
```typescript
const handleDelete = async (server: MCPServer) => {
  const confirmed = await showConfirmDialog({
    title: 'Delete Server',
    message: `Are you sure you want to delete "${server.name}"?`,
    detail: 'This action cannot be undone.',
    checkboxLabel: server.customConfig?.isFastMCP
      ? 'Also delete generated files'
      : undefined
  });

  if (confirmed) {
    // Stop if running
    if (server.isRunning) {
      await window.electronAPI.process.stop(server.id);
    }

    // Delete from registry
    await window.electronAPI.mcp.deleteServer(
      server.id,
      confirmed.deleteFiles
    );

    showToast(`Server '${server.name}' deleted`);
    refreshServerList();
  }
};
```

---

### Duplicate Server

#### UI Flow
1. "Duplicate" button in dropdown menu
2. Opens `AddServerDialog` in "duplicate" mode
3. Pre-fills form with existing server config
4. Auto-appends " (Copy)" to server name
5. Generates new unique ID
6. User can modify any fields before saving
7. Saves as new independent server

#### Implementation
```typescript
const handleDuplicate = (server: MCPServer) => {
  const duplicatedConfig = {
    ...server.customConfig,
    name: `${server.name} (Copy)`,
  };

  setDialogMode('duplicate');
  setDuplicateConfig(duplicatedConfig);
  setIsDialogOpen(true);
};
```

**For FastMCP servers:**
- Copies generated files to new directory
- Creates new working directory: `~/.auto-claude/fastmcp-servers/{new-name}`
- Runs `uv sync` in new directory
- Preserves all tools and dependencies

---

## 5. Integration & Data Flow

### Component Integration

#### AddServerDialog Modes (Extended)
```typescript
type DialogMode =
  | 'choose'      // Mode selection (Phase 2)
  | 'existing'    // Add existing server (Phase 2)
  | 'fastmcp'     // NEW: FastMCP wizard
  | 'edit'        // NEW: Edit existing server
  | 'duplicate';  // NEW: Duplicate server
```

#### MCPServerCard Actions (Extended)

**Built-in servers:**
```
[Enable/Disable] [View Details]
```

**Custom servers (http/sse):**
```
[Enable/Disable] [View Details] [•••]
  └─ Dropdown:
     - Edit
     - Duplicate
     - Delete
```

**Custom servers (stdio/FastMCP):**
```
[Start/Stop] [Logs] [Enable/Disable] [View Details] [•••]
  └─ Dropdown:
     - Edit
     - Duplicate
     - Delete
     - View Generated Files (FastMCP only)
```

### Data Flow Diagrams

#### 1. FastMCP Generation Flow
```
User clicks "Add Server"
  → AddServerDialog (mode: choose)
  → User selects "Create New with FastMCP"
  → AddServerDialog (mode: fastmcp)
  → FastMCP Wizard (5 steps)
  → Generate files with uv:
      uv init --name {name}
      uv add fastmcp {deps}
      uv sync
  → Add to registry as stdio server with isFastMCP=true
  → Show success toast
  → MCPManager refreshes, shows new server
  → User clicks Start
  → Process Manager launches via uv run
```

#### 2. Process Management Flow
```
Renderer (MCPServerCard)
  ├─ Click Start
  │   └─> IPC: process:start(serverId)
  │       └─> Main: ProcessManager.startServer()
  │           └─> spawn('uv', ['run', 'server.py'])
  │               └─> Event: process:started
  │                   └─> Renderer: Update status to "Running"
  │
  ├─ Click Logs
  │   └─> IPC: process:logs(serverId)
  │       └─> Main: ProcessManager.getLogBuffer()
  │           └─> Return: string[] (last 1000 lines)
  │               └─> Renderer: Show LogViewerDialog
  │
  └─ Real-time log streaming
      └─> Main: process.stdout.on('data')
          └─> IPC Event: process:log({serverId, message})
              └─> Renderer: Append to LogViewerDialog
```

#### 3. Server CRUD Flow

**Edit:**
```
MCPServerCard → Click Edit
  → AddServerDialog (mode: edit, server: existing)
  → EditServerForm (pre-populated)
  → User modifies config
  → Click "Update Server"
  → IPC: mcp:update-server(serverId, newConfig)
  → Main: Update registry file
  → Success
  → Renderer: Refresh server list
```

**Delete:**
```
MCPServerCard → Click Delete
  → Confirmation dialog
  → User confirms
  → If running: IPC: process:stop(serverId)
  → IPC: mcp:delete-server(serverId, deleteFiles)
  → Main:
      - Remove from registry
      - If deleteFiles: rm -rf workingDir
  → Success
  → Renderer: Remove from list, show toast
```

**Duplicate:**
```
MCPServerCard → Click Duplicate
  → AddServerDialog (mode: duplicate, config: cloned)
  → User modifies name/config
  → Click "Save"
  → IPC: mcp:add-custom-server(newConfig)
  → If FastMCP: Copy files to new dir, run uv sync
  → Success
  → Renderer: Refresh server list
```

### Registry File Structure (Extended)

```json
{
  "version": "1.0",
  "servers": [
    {
      "id": "custom-fastmcp-1234567890",
      "name": "My API Server",
      "description": "API wrapper for external service",
      "type": "custom",
      "category": "Custom",
      "status": "disconnected",
      "enabled": false,
      "requiredEnvVars": [],
      "capabilities": {},
      "toolCount": 0,
      "promptCount": 0,
      "resourceCount": 0,
      "connectionType": "stdio",
      "customConfig": {
        "connectionType": "stdio",
        "command": "server.py",
        "args": [],
        "workingDir": "/Users/user/.auto-claude/fastmcp-servers/my-api-server",
        "env": {},
        "isFastMCP": true,
        "generatedFrom": "wizard",
        "template": "api-wrapper",
        "pythonVersion": "3.12",
        "sourceFiles": {
          "pyprojectToml": "/Users/user/.auto-claude/fastmcp-servers/my-api-server/pyproject.toml",
          "serverPy": "/Users/user/.auto-claude/fastmcp-servers/my-api-server/server.py",
          "readmeMd": "/Users/user/.auto-claude/fastmcp-servers/my-api-server/README.md"
        }
      }
    }
  ],
  "updatedAt": "2025-12-24T10:30:00.000Z"
}
```

---

## 6. Testing Strategy

### Component Testing (Unit Tests)

#### FastMCP Wizard Components (40+ tests)
**TemplateSelector.test.tsx**
- Renders 4 template cards
- Each card shows icon, name, description
- Click selects template, proceeds to next step
- "Blank Template" has different icon

**ServerConfigForm.test.tsx**
- Server name validation (required, unique)
- Python version dropdown (3.10-3.13)
- Working directory with file browser
- Form submission with valid data

**ToolCustomizer.test.tsx**
- Display template tools
- Add new tool dialog
- Edit tool parameters
- Remove tool with confirmation

**DependencyManager.test.tsx**
- Display auto-detected dependencies
- Add dependency with version spec
- Remove dependency
- Validate package name format

**GeneratePreview.test.tsx**
- Shows file previews (pyproject.toml, server.py)
- Generate button triggers file creation
- Success shows toast notification
- Error handling for generation failures

#### Process Management Components (25+ tests)
**ProcessControls.test.tsx**
- Start button launches process
- Stop button terminates process
- Restart executes stop + start
- Buttons disabled in appropriate states
- Loading spinner during state transitions

**ProcessStatus.test.tsx**
- Displays PID, uptime, memory
- Updates metrics in real-time
- Shows crash status on exit
- Restart count increments correctly

**LogViewer.test.tsx**
- Renders log entries
- Auto-scroll toggles correctly
- Search filters logs
- Copy to clipboard works
- Download saves .txt file
- Clear logs empties buffer

**ProcessManager (Backend).test.ts**
- startServer spawns process correctly
- stopServer sends SIGTERM then SIGKILL
- Log buffer maintains 1000 lines
- Auto-restart triggers on crash
- IPC events forwarded to renderer

#### Server CRUD Components (15+ tests)
**EditServerForm.test.tsx**
- Pre-populates form with server config
- Update button saves changes
- Warning shown if server running
- Validation prevents invalid updates

**DeleteConfirmation.test.tsx**
- Shows server name in dialog
- Checkbox for file deletion (FastMCP only)
- Cancel button closes without action
- Delete button triggers deletion

**DuplicateFlow.test.tsx**
- Clones server config correctly
- Appends " (Copy)" to name
- Allows modifications before save
- Generates new unique ID

### Integration Testing (3 scenarios)

#### 1. FastMCP → Process Management
```typescript
test('Complete FastMCP flow', async () => {
  // Generate FastMCP server
  await selectTemplate('API Wrapper');
  await fillServerConfig({ name: 'Test API', pythonVersion: '3.12' });
  await customizeTools([/* tools */]);
  await setDependencies(['httpx>=0.25.0']);
  await clickGenerate();

  // Verify server appears in list
  expect(screen.getByText('Test API')).toBeInTheDocument();

  // Start process
  await clickStart('Test API');

  // Verify running status
  await waitFor(() => {
    expect(screen.getByText(/Running.*PID:/)).toBeInTheDocument();
  });

  // Check logs
  await clickLogs('Test API');
  expect(screen.getByText(/Server starting/)).toBeInTheDocument();

  // Stop process
  await clickStop('Test API');
  expect(await screen.findByText('Stopped')).toBeInTheDocument();
});
```

#### 2. Edit → Process Management
```typescript
test('Edit server while running shows warning', async () => {
  // Start server
  await clickStart('My Server');
  await waitFor(() => expect(getStatus()).toBe('Running'));

  // Try to edit
  await clickEdit('My Server');

  // Verify warning
  expect(screen.getByText(/Stop server before editing/)).toBeInTheDocument();

  // Stop from warning dialog
  await clickStopButton();

  // Edit proceeds
  expect(screen.getByLabelText('Server Name')).toHaveValue('My Server');
});
```

#### 3. Delete → Process Management
```typescript
test('Delete running server stops it automatically', async () => {
  // Start server
  await clickStart('Test Server');
  await waitFor(() => expect(getStatus()).toBe('Running'));

  // Delete
  await clickDelete('Test Server');
  await confirmDelete();

  // Verify stopped and removed
  expect(screen.queryByText('Test Server')).not.toBeInTheDocument();
  expect(mockProcessManager.stopServer).toHaveBeenCalledWith('test-server-id');
});
```

### Manual Testing Scenarios

#### FastMCP Wizard
1. **Template Flow:**
   - Create server from each template (File System, API, Database, Blank)
   - Verify generated code matches template
   - Test uv installation speed

2. **Customization:**
   - Add custom tools with complex parameters
   - Remove default tools
   - Add dependencies with version constraints
   - Change Python version (verify uv installs it)

3. **Error Cases:**
   - Invalid server name (empty, duplicates)
   - Invalid Python version
   - Network error during uv sync
   - Disk space error

#### Process Management
1. **Lifecycle:**
   - Start 5 servers simultaneously
   - Stop all servers
   - Restart crashed server
   - Auto-restart on crash (enable/disable)

2. **Logs:**
   - High-frequency output (1000+ lines/sec)
   - Log search with special characters
   - Auto-scroll during active logging
   - Download large log files

3. **Stress Testing:**
   - Start 10+ servers concurrently
   - Rapid start/stop cycles
   - Memory leak test (long-running servers)

#### Server CRUD
1. **Edit:**
   - Edit HTTP server (change URL)
   - Edit stdio server (change command)
   - Edit FastMCP server (change description only)
   - Edit running server (verify warning)

2. **Delete:**
   - Delete stopped server
   - Delete running server (auto-stop)
   - Delete FastMCP with file deletion
   - Delete FastMCP without file deletion

3. **Duplicate:**
   - Duplicate HTTP server
   - Duplicate FastMCP server (verify files copied)
   - Modify duplicate before saving
   - Run both original and duplicate

### E2E Testing (Playwright)

#### Critical Path 1: FastMCP End-to-End
```typescript
test('FastMCP wizard to running server', async ({ page }) => {
  // Launch app
  await page.goto('/');

  // Navigate to MCP Manager
  await page.click('text=Settings');
  await page.click('text=MCP Servers');

  // Add FastMCP server
  await page.click('text=Add Server');
  await page.click('text=Create New with FastMCP');

  // Select template
  await page.click('[data-testid="template-api-wrapper"]');
  await page.click('text=Next');

  // Configure
  await page.fill('[name="serverName"]', 'E2E Test API');
  await page.selectOption('[name="pythonVersion"]', '3.12');
  await page.click('text=Next');

  // Skip tool customization
  await page.click('text=Next');

  // Skip dependencies
  await page.click('text=Next');

  // Generate
  await page.click('text=Generate & Save');

  // Wait for generation
  await page.waitForSelector('text=Server created successfully');

  // Start server
  await page.click('[data-server="e2e-test-api"] [data-action="start"]');

  // Verify running
  await expect(page.locator('text=/Running.*PID:/')).toBeVisible();

  // View logs
  await page.click('[data-server="e2e-test-api"] [data-action="logs"]');
  await expect(page.locator('text=Server starting')).toBeVisible();

  // Stop server
  await page.click('text=Close'); // Close logs
  await page.click('[data-server="e2e-test-api"] [data-action="stop"]');
  await expect(page.locator('text=Stopped')).toBeVisible();
});
```

#### Critical Path 2: Edit & Duplicate
```typescript
test('Edit and duplicate server', async ({ page }) => {
  // ... (setup: create a server)

  // Edit
  await page.click('[data-server="test-server"] [data-action="menu"]');
  await page.click('text=Edit');
  await page.fill('[name="description"]', 'Updated description');
  await page.click('text=Update Server');
  await expect(page.locator('text=Updated description')).toBeVisible();

  // Duplicate
  await page.click('[data-server="test-server"] [data-action="menu"]');
  await page.click('text=Duplicate');
  await page.fill('[name="serverName"]', 'Duplicated Server');
  await page.click('text=Save');
  await expect(page.locator('text=Duplicated Server')).toBeVisible();
});
```

#### Critical Path 3: Delete with Confirmation
```typescript
test('Delete server with file cleanup', async ({ page }) => {
  // ... (setup: create FastMCP server)

  // Delete
  await page.click('[data-server="test-fastmcp"] [data-action="menu"]');
  await page.click('text=Delete');

  // Verify confirmation
  await expect(page.locator('text=Are you sure')).toBeVisible();

  // Select file deletion
  await page.check('text=Also delete generated files');

  // Confirm
  await page.click('text=Delete Server');

  // Verify removed
  await expect(page.locator('[data-server="test-fastmcp"]')).not.toBeVisible();
  await expect(page.locator('text=Server.*deleted')).toBeVisible();
});
```

### Test Coverage Targets
- **Unit Tests:** 80+ tests total
  - FastMCP Wizard: 40+ tests
  - Process Management: 25+ tests
  - Server CRUD: 15+ tests
- **Integration Tests:** 3 scenarios
- **E2E Tests:** 3 critical paths
- **Manual Testing:** 12 scenarios

---

## 7. Implementation Phases

### Phase 3A: FastMCP + Process Management (Priority 1)
**Duration Estimate:** 2-3 weeks

**Tasks:**
1. FastMCP Wizard UI (5 steps)
2. uv integration (file generation, dependency management)
3. ProcessManager backend (start/stop/logs)
4. Process controls in MCPServerCard
5. Log viewer dialog
6. IPC handlers for process management
7. Testing (40+ unit tests, integration tests)

**Deliverables:**
- Complete FastMCP wizard from template to running server
- Full process management for stdio/FastMCP servers
- Real-time log viewing

### Phase 3B: Server CRUD (Priority 2)
**Duration Estimate:** 1-2 weeks

**Tasks:**
1. Edit server functionality (dialog modes, form pre-population)
2. Delete server with confirmation
3. Duplicate server with file copying (FastMCP)
4. IPC handlers for CRUD operations
5. Testing (15+ unit tests)

**Deliverables:**
- Edit any custom server
- Delete servers with optional file cleanup
- Duplicate servers with config cloning

### Phase 3C: Polish & E2E Testing (Priority 3)
**Duration Estimate:** 1 week

**Tasks:**
1. UI polish (animations, loading states, error messages)
2. E2E test suite (Playwright)
3. Performance optimization (log buffer, process monitoring)
4. Documentation updates
5. User testing feedback incorporation

**Deliverables:**
- Production-ready Phase 3
- Complete test coverage
- Updated user documentation

---

## 8. Open Questions & Future Considerations

### Open Questions
1. **uv installation:** Should Auto-Claude bundle uv, or require users to install it?
   - Recommendation: Bundle uv binary for seamless experience

2. **FastMCP template source:** Where do templates come from?
   - Recommendation: Embed 4 templates in app, allow custom templates in Phase 4

3. **Process limits:** Max concurrent servers?
   - Recommendation: No hard limit, but warn if >10 servers running

4. **Log persistence:** Should logs persist across app restarts?
   - Recommendation: Write logs to `~/.auto-claude/logs/{serverId}.log`

### Future Enhancements (Phase 4+)
- **Tier 2 Process Management:** HTTP/SSE startup scripts
- **Export/Import:** Share server configs as JSON/YAML files
- **Template Marketplace:** Community-contributed FastMCP templates
- **Server Groups:** Organize servers into folders/tags
- **Health Dashboards:** Aggregate metrics across all running servers
- **Remote Servers:** Manage servers on remote machines via SSH

---

## Appendix: Technical References

### uv Commands Reference
```bash
# Initialize project
uv init --name my-server

# Add dependencies
uv add fastmcp httpx pydantic

# Sync environment (install all deps)
uv sync

# Run script
uv run server.py

# Install Python version
uv python install 3.12

# List installed packages
uv pip list
```

### FastMCP Server Template
```python
from fastmcp import FastMCP

mcp = FastMCP("Server Name")

@mcp.tool()
def example_tool(param: str) -> str:
    """Tool description"""
    return f"Result: {param}"

if __name__ == "__main__":
    mcp.run()
```

### IPC Events
```typescript
// Process lifecycle
'process:start'   → (serverId: string) → Promise<void>
'process:stop'    → (serverId: string) → Promise<void>
'process:restart' → (serverId: string) → Promise<void>
'process:logs'    → (serverId: string) → Promise<string[]>

// Real-time events (Main → Renderer)
'process:log'     → { serverId, timestamp, level, message }
'process:status'  → { serverId, status, pid, uptime, memory }
'process:crash'   → { serverId, exitCode, signal }

// CRUD operations
'mcp:update-server' → (serverId, config) → Promise<void>
'mcp:delete-server' → (serverId, deleteFiles) → Promise<void>
```

---

**Design Status:** ✅ Complete - Ready for Implementation Planning
