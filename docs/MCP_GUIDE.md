# MCP User Guide

**Model Context Protocol (MCP)** in Auto-Claude allows you to extend the capabilities of Claude agents by connecting to external services and tools.

## What is MCP?

MCP is an open protocol that enables Claude to:
- **Use Tools** - Execute functions to interact with external systems
- **Access Prompts** - Use pre-defined workflow templates
- **Read Resources** - Fetch data from various sources

## Available MCP Servers

### Built-in Servers

#### 1. Context7 (Always Active)
Real-time documentation lookup for any library.

**No configuration required** - works out of the box.

**Tools:**
- `resolve-library-id` - Find library by name
- `get-library-docs` - Fetch documentation

---

#### 2. Linear
Project management and issue tracking integration.

**Setup:**
1. Go to [linear.app/settings/api](https://linear.app/settings/api)
2. Create a new API key
3. Open Settings → MCP Servers in Auto-Claude
4. Click "Configure" on Linear
5. Paste your API key
6. Click "Test Connection"
7. Click "Save & Connect"

**Tools:** 12 (create_issue, update_issue, list_projects, etc.)

---

#### 3. Graphiti Memory
Knowledge graph memory with semantic search.

**Requirements:**
- Python 3.12+
- `pip install real_ladybug graphiti-core`

**Setup:**
1. Start Graphiti MCP server: `graphiti-mcp-server --port 8000`
2. Open Settings → MCP Servers
3. Configure Graphiti
4. Set MCP URL: `http://localhost:8000/mcp/`
5. Test and save

**Capabilities:**
- Tools: 5 (search_nodes, search_facts, add_episode, etc.)
- Prompts: 3 (analyze-with-memory, debug-with-context, review-with-history)
- Resources: 8 (episodes, entities, graph visualization)

---

#### 4. Electron Automation
Desktop app testing via Chrome DevTools Protocol.

**Setup:**
1. Start your Electron app with: `--remote-debugging-port=9222`
2. Configure Electron MCP in settings
3. Set ELECTRON_MCP_ENABLED=true
4. Set ELECTRON_DEBUG_PORT=9222 (if different)

**Tools:** 4 (get_window_info, take_screenshot, send_command, read_logs)

---

#### 5. Puppeteer Browser
Web browser automation and testing.

**Auto-enabled** for web frontend projects (React, Vue, Next.js, etc.)

**Tools:** 8 (navigate, screenshot, click, fill, select, hover, evaluate)

---

#### 6. Auto-Claude Tools (Internal)
Internal tools for build progress and context.

**Always available** - no configuration needed.

**Tools:** 6 (update_subtask_status, get_build_progress, record_discovery, etc.)

---

## Using MCP in Tasks

When creating a new spec or task, you can reference MCP tools:

```
Create a user authentication system with Linear integration.
Use Linear MCP tools to create issues for testing tasks.
```

Claude will automatically use available MCP tools when relevant to your task.

## Viewing Server Capabilities

Each MCP server provides three types of capabilities:

### Tools
Executable functions that agents can call. Examples:
- `mcp__linear__create_issue` - Create a new Linear issue
- `mcp__context7__resolve-library-id` - Find library documentation

To view tools:
1. Open Settings → MCP Servers
2. Find the server you want to inspect
3. Click "Show Details"
4. Click the "🔧 Tools" tab

Each tool shows:
- **Name** - The full tool identifier
- **Description** - What the tool does
- **Parameters** - Required and optional inputs with types
- **Copy button** - Click to copy tool name for use in prompts

### Prompts
Pre-defined workflow templates. Examples:
- `code-review-prompt` - Generate code review instructions
- `debug-with-context` - Debug with historical context

Prompts require arguments that you fill in when using them.

### Resources
Data sources with URI templates. Examples:
- `graphiti://episodes/{id}` - Get specific episode by ID
- `graphiti://episodes/recent` - Get recent episodes

Resources with `{param}` are templates - you provide the parameter value.

## Using Capabilities in Tasks

When creating tasks, you can reference specific tools:

1. View the tool in MCP Manager
2. Click copy button to get exact tool name
3. In your task description, mention: "Use tool `mcp__linear__create_issue` to..."

The planner agent will see available tools and use them appropriately.

## Creating Custom MCP Servers

Coming in Phase 4: FastMCP wizard for creating custom servers.

## Troubleshooting

### "Connection test failed"
- Verify your API key is correct
- Check that the external service is accessible
- Ensure no firewall blocking

### "Server not configured"
- Click "Configure" on the server
- Fill in required credentials
- Test and save

### Linear: "Invalid API key"
- Create a new key at linear.app/settings/api
- Ensure the key has sufficient permissions

### Graphiti: "Cannot connect"
- Verify Graphiti MCP server is running
- Check the URL is correct (including /mcp/ path)
- Ensure Python 3.12+ is installed

## FAQ

**Q: Are MCP tools always available?**
A: Only enabled servers' tools are available. Configure servers in Settings → MCP Servers.

**Q: Do I need to specify which MCP tool to use?**
A: No, Claude automatically selects appropriate tools based on your task.

**Q: Can I use multiple MCP servers at once?**
A: Yes! Enable as many as you need.

**Q: Is my API key safe?**
A: Keys are stored in `.env` files on your local machine, never sent to Anthropic.
