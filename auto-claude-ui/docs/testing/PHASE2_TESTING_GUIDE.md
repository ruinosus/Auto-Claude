# Phase 2 Testing Guide: Add Existing Server Functionality

## Overview

This guide covers testing for Phase 2 of the MCP Manager enhancements, which implements the ability to manually add custom MCP servers through a multi-step wizard interface.

### What Was Implemented (Tasks 1-11)

**Task 1:** Custom Server Types
- Added `CustomServerConfig` type for http/stdio/sse configurations
- Added `ProcessInfo` for server process tracking
- Added `MCPServerExport` for import/export functionality

**Task 2:** AddServerDialog Component
- Mode selection dialog (Existing Server vs FastMCP)
- State management for dialog flow

**Task 3:** ConnectionTypeSelector Component
- Radio group for selecting http/stdio/sse connection types
- Descriptive labels with usage examples

**Task 4:** HttpServerForm Component
- Server name, description, base URL configuration
- Authentication (None, API Key, Bearer Token)
- Custom HTTP headers management
- Scope selection (Global vs Project)

**Task 5:** StdioServerForm Component
- Command and arguments configuration
- Working directory selection with file browser
- Environment variables management
- Scope selection

**Task 6:** SseServerForm Component
- SSE endpoint URL configuration
- Auto-reconnect options
- Reconnect delay settings
- Authentication support
- Scope selection

**Task 7:** TestConnectionStep Component
- Simulated connection testing
- Loading, success, and error states
- Capabilities display (tools, prompts, resources)
- Retry functionality

**Task 8:** AddExistingServerForm Component
- Multi-step wizard flow (3 steps)
- Integration of ConnectionTypeSelector and type-specific forms
- Data flow between steps
- Final submission to TestConnectionStep

**Task 9:** MCPManager Integration
- "Add Server" button in toolbar
- Dialog state management

**Task 10:** IPC Handlers
- `mcp:add-custom-server` - Saves custom server configurations
- `mcp:test-connection-custom` - Tests server connections (simulated)
- Validation logic for server configurations
- File system operations for storing configs

**Task 11:** Custom Server Loading
- Load custom servers from registry files
- Display alongside built-in servers
- Enable/disable functionality

---

## Automated Testing

### Running All Tests

From the `auto-claude-ui` directory:

```bash
# Run all tests once
npm test

# Run tests in watch mode (auto-rerun on changes)
npm run test:watch

# Run tests with coverage report
npm run test:coverage
```

### Running Specific Test Suites

```bash
# Test only custom server types
npm test -- src/shared/types/__tests__/mcp.test.ts

# Test dialog component
npm test -- AddServerDialog.test.tsx

# Test connection type selector
npm test -- ConnectionTypeSelector.test.tsx

# Test HTTP form
npm test -- HttpServerForm.test.tsx

# Test stdio form
npm test -- StdioServerForm.test.tsx

# Test SSE form
npm test -- SseServerForm.test.tsx

# Test connection testing step
npm test -- TestConnectionStep.test.tsx

# Test multi-step wizard
npm test -- AddExistingServerForm.test.tsx

# Test IPC handlers
npm test -- mcp-handlers.test.ts

# Test MCPManager integration
npm test -- MCPManager.test.tsx
```

### Test Coverage Breakdown

**Component Tests** (Frontend):
- `AddServerDialog.test.tsx` - 3 tests (mode selection, dialog state)
- `ConnectionTypeSelector.test.tsx` - 3 tests (rendering, selection, onChange)
- `HttpServerForm.test.tsx` - 30+ tests (fields, auth, headers, validation)
- `StdioServerForm.test.tsx` - 25+ tests (command config, env vars, validation)
- `SseServerForm.test.tsx` - 28+ tests (endpoint, reconnect, auth, validation)
- `TestConnectionStep.test.tsx` - 15+ tests (loading, success, error, retry)
- `AddExistingServerForm.test.tsx` - 15+ tests (wizard flow, data persistence)
- `MCPManager.test.tsx` - Integration tests for full dialog flow

**Type Tests**:
- `mcp.test.ts` - 3 tests (CustomServerConfig, ProcessInfo types)

**IPC Handler Tests** (Backend):
- `mcp-handlers.test.ts` - 15+ tests (add server, validation, file operations, connection testing)

**Total Test Count**: 130+ automated tests

### Expected Results

All tests should **PASS**. The test suite uses:
- **Vitest** for test running
- **React Testing Library** for component testing
- **Mock functions** for IPC communication and file system operations

---

## Manual Testing Procedures

### Prerequisites

1. Build and run the application:
   ```bash
   cd auto-claude-ui
   npm install
   npm run dev
   ```

2. Open the application and navigate to **Settings → MCP Servers**

### Test 1: Add HTTP/HTTPS Server

**Objective**: Verify HTTP server configuration flow

**Steps**:
1. Click the **"Add Server"** button in the MCP Manager toolbar
2. In the dialog, click **"Connect to Existing Server"**
3. Select **"HTTP/HTTPS"** connection type
4. Click **"Next"**
5. Fill in the form:
   - **Server Name**: `Test HTTP Server`
   - **Description**: `A test HTTP MCP server`
   - **Base URL**: `http://localhost:8000`
6. Under Authentication, select **"API Key"**
7. Enter API Key Value: `sk-test-12345`
8. Click "Show" to verify the key is visible
9. Click **"Add Header"**
10. Enter Header Key: `X-Custom-Header`
11. Enter Header Value: `custom-value`
12. Select Scope: **"Global"**
13. Click **"Next"**

**Expected Results**:
- Step indicator shows "Step 2 of 3"
- All fields accept input correctly
- Password field toggles visibility
- Header row can be added and removed
- Scope selection updates correctly
- Form advances to Step 3 (Connection Test)

**Step 3 - Connection Test**:
14. Wait for simulated connection test to complete (1-2 seconds)
15. Verify "Connection successful!" message appears
16. Verify capabilities are displayed:
    - "1 tools found"
    - "1 prompts found"
    - "0 resources found"
17. Click **"Save"**

**Expected Results**:
- Dialog closes
- New server appears in MCP Servers list as "Test HTTP Server"
- Server is initially disabled (toggle off)
- Server shows connection type badge (HTTP)

### Test 2: Add stdio Server

**Objective**: Verify stdio server configuration flow

**Steps**:
1. Click **"Add Server"** button
2. Click **"Connect to Existing Server"**
3. Select **"stdio (Standard I/O)"** connection type
4. Click **"Next"**
5. Fill in the form:
   - **Server Name**: `Test stdio Server`
   - **Description**: `Local Python MCP server`
   - **Command**: `python3`
   - **Arguments**: `server.py --verbose`
   - **Working Directory**: `/path/to/mcp/server`
6. Click **"Add Variable"**
7. Enter Variable Name: `MCP_PORT`
8. Enter Variable Value: `8000`
9. Click **"Add Variable"** again
10. Enter Variable Name: `DEBUG`
11. Enter Variable Value: `true`
12. Select Scope: **"Project"**
13. Click **"Next"**

**Expected Results**:
- Step indicator shows "Step 2 of 3"
- Command field accepts input
- Arguments field accepts input
- Working directory field accepts input
- Multiple environment variables can be added
- Variables can be removed (test by removing one)
- Form advances to connection test

**Step 3 - Connection Test**:
14. Wait for connection test
15. Verify success message and capabilities
16. Click **"Save"**

**Expected Results**:
- Dialog closes
- Server appears in list as "Test stdio Server"
- Server shows stdio badge
- Server is in project scope (if project is open)

### Test 3: Add SSE Server

**Objective**: Verify SSE server configuration flow

**Steps**:
1. Click **"Add Server"** button
2. Click **"Connect to Existing Server"**
3. Select **"SSE (Server-Sent Events)"** connection type
4. Click **"Next"**
5. Fill in the form:
   - **Server Name**: `Test SSE Server`
   - **Description**: `Event stream MCP server`
   - **SSE Endpoint URL**: `http://localhost:8000/events`
6. Verify **"Auto-reconnect on disconnect"** checkbox is **checked** by default
7. Change **"Reconnect delay"** from 5 to 10 seconds
8. Select **"Bearer Token"** for authentication
9. Enter Bearer Token: `bearer-test-token`
10. Select Scope: **"Global"**
11. Click **"Next"**

**Expected Results**:
- All fields accept input correctly
- Auto-reconnect checkbox can be toggled
- Reconnect delay field is visible when auto-reconnect is enabled
- Reconnect delay field disappears when auto-reconnect is disabled
- Form advances to connection test

**Step 3 - Connection Test**:
12. Wait for connection test
13. Verify success and capabilities
14. Click **"Save"**

**Expected Results**:
- Dialog closes
- Server appears in list as "Test SSE Server"
- Server shows SSE badge

### Test 4: Verify Custom Servers in List

**Objective**: Confirm custom servers appear alongside built-in servers

**Steps**:
1. Review the MCP Servers list
2. Locate the three custom servers added above
3. Verify each server displays:
   - Server name
   - Description
   - Connection type badge (HTTP/stdio/SSE)
   - Enable/disable toggle
   - Server type indicator ("Custom" or similar)

**Expected Results**:
- All three custom servers are visible
- Custom servers are distinguishable from built-in servers
- Each server shows correct metadata

### Test 5: Enable/Disable Functionality

**Objective**: Test toggle functionality for custom servers

**Steps**:
1. Find "Test HTTP Server" in the list
2. Click the enable toggle (should turn on)
3. Verify toggle state changes to "enabled"
4. Click the toggle again to disable
5. Verify toggle state changes to "disabled"
6. Repeat for "Test stdio Server" and "Test SSE Server"

**Expected Results**:
- Toggle state persists visually
- Enable/disable actions are saved (verify by refreshing the application)

### Test 6: Wizard Navigation

**Objective**: Test back/cancel navigation in wizard

**Steps**:
1. Click **"Add Server"**
2. Click **"Connect to Existing Server"**
3. Select **"HTTP/HTTPS"**
4. Click **"Next"**
5. Click **"Back"** button
6. Verify you return to connection type selection
7. Click **"Next"** again
8. Fill in server name and URL
9. Click **"Cancel"** button

**Expected Results**:
- Back button works correctly
- Back button is disabled on first step
- Cancel closes dialog without saving
- No server is added to the list

---

## Test Scenarios

### Happy Path: Adding Valid Servers

**Scenario**: User adds a well-configured HTTP server

**Test**:
1. Follow "Test 1: Add HTTP/HTTPS Server" procedure
2. Use valid URL format: `https://api.example.com`
3. Provide all required fields
4. Complete wizard to save

**Expected**: Server saves successfully and appears in list

---

### Error Cases: Invalid Configurations

#### Invalid URL Format

**Scenario**: User enters invalid URL

**Test**:
1. Start HTTP server wizard
2. Enter Server Name: `Invalid Server`
3. Enter Base URL: `not-a-valid-url`
4. Click "Next"

**Expected**:
- Form validation prevents advancing to next step
- Error message indicates invalid URL format
- User remains on Step 2

#### Missing Required Fields

**Scenario**: User tries to submit with empty required fields

**Test**:
1. Start stdio server wizard
2. Advance to Step 2
3. Leave Command field empty
4. Click "Next"

**Expected**:
- Form validation prevents advancing
- Error indication on Command field
- User remains on Step 2

#### Missing Server Name

**Scenario**: User forgets to enter server name

**Test**:
1. Start any server type wizard
2. Fill in all fields EXCEPT server name
3. Click "Next"

**Expected**:
- Form validation prevents advancing
- Error indication on Server Name field

---

### Edge Cases

#### Empty Custom Headers

**Scenario**: User adds header row but leaves it empty

**Test**:
1. Start HTTP server wizard
2. Click "Add Header"
3. Leave both key and value empty
4. Fill in other required fields
5. Click "Next"

**Expected**:
- Empty headers are filtered out (not saved)
- Form submission succeeds
- Only non-empty headers are included in config

#### Empty Environment Variables

**Scenario**: User adds env var row but leaves it empty

**Test**:
1. Start stdio server wizard
2. Click "Add Variable"
3. Leave both name and value empty
4. Fill in other required fields
5. Click "Next"

**Expected**:
- Empty variables are filtered out
- Form submission succeeds
- Only non-empty variables are included

#### Special Characters in Fields

**Scenario**: User enters special characters

**Test**:
1. Start HTTP server wizard
2. Enter Server Name: `Test & Special <> Characters`
3. Enter Header Key: `X-Custom-@#$`
4. Enter Header Value: `value-with-"quotes"`
5. Complete wizard

**Expected**:
- Special characters are accepted and saved correctly
- No encoding issues
- Server name displays correctly in list

#### Very Long Server Names

**Scenario**: User enters extremely long server name

**Test**:
1. Start any wizard
2. Enter Server Name: `[300 character string]`
3. Complete wizard

**Expected**:
- Long names are accepted
- UI truncates display gracefully with ellipsis
- Full name visible on hover or in details

---

### Integration: Custom + Built-in Servers Together

**Scenario**: Custom servers coexist with built-in servers

**Test**:
1. Add 3 custom servers (HTTP, stdio, SSE)
2. Verify built-in servers are still visible
3. Enable a custom server and a built-in server
4. Disable a custom server and a built-in server
5. Verify both types work independently

**Expected**:
- Custom and built-in servers display in the same list
- Each server type is clearly distinguished
- Enable/disable works for both types
- No conflicts between custom and built-in servers

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: Dialog doesn't open when clicking "Add Server"

**Solution**:
1. Check browser console for errors
2. Verify `AddServerDialog` component is imported in `MCPManager`
3. Check that dialog state is properly managed
4. Restart the application

#### Issue: Connection test never completes

**Solution**:
1. This is expected if the IPC handler is not responding
2. Check that `mcp:test-connection-custom` handler is registered
3. Verify `window.electron.testMCPConnection` is available in renderer
4. Check main process logs for errors
5. **Note**: In Phase 2, connection testing is **simulated** - it should complete within 1-2 seconds

#### Issue: Server doesn't appear in list after saving

**Solution**:
1. Check that `mcp:add-custom-server` IPC handler succeeded
2. Verify registry file was created:
   - Global: `~/.auto-claude/mcp-servers.json`
   - Project: `<project>/.auto-claude/mcp-servers.json`
3. Check file permissions
4. Review application logs for errors
5. Restart the application to reload servers

#### Issue: Form validation too strict

**Solution**:
1. Verify URL format: must start with `http://` or `https://`
2. Ensure all required fields are filled:
   - HTTP: Server Name, Base URL
   - stdio: Server Name, Command
   - SSE: Server Name, SSE Endpoint URL
3. Check for trailing spaces in input fields

#### Issue: Changes not persisting after restart

**Solution**:
1. Verify config file exists and is writable
2. Check file contents match expected format
3. Ensure proper scope was selected (Global vs Project)
4. Verify no file system errors in logs

---

## How to Check Registry Files

### Global Servers

**Location**: `~/.auto-claude/mcp-servers.json`

**View contents**:
```bash
cat ~/.auto-claude/mcp-servers.json
```

**Expected format**:
```json
{
  "version": "1.0",
  "servers": [
    {
      "id": "custom-http-1234567890",
      "name": "Test HTTP Server",
      "description": "A test HTTP MCP server",
      "type": "custom",
      "enabled": false,
      "customConfig": {
        "connectionType": "http",
        "baseUrl": "http://localhost:8000",
        "authType": "api-key",
        "authValue": "sk-test-12345",
        "headers": {
          "X-Custom-Header": "custom-value"
        }
      }
    }
  ]
}
```

### Project Servers

**Location**: `<project-directory>/.auto-claude/mcp-servers.json`

**View contents**:
```bash
cat .auto-claude/mcp-servers.json
```

Format is identical to global servers.

---

## How to Reset if Things Go Wrong

### Reset All Custom Servers (Global)

```bash
# Backup first (recommended)
cp ~/.auto-claude/mcp-servers.json ~/.auto-claude/mcp-servers.json.backup

# Remove the file
rm ~/.auto-claude/mcp-servers.json

# Restart the application
```

### Reset Project Servers

```bash
# From project directory
rm .auto-claude/mcp-servers.json
```

### Reset Application State

```bash
# Clear all application data (macOS)
rm -rf ~/Library/Application\ Support/auto-claude-ui

# Clear all application data (Linux)
rm -rf ~/.config/auto-claude-ui

# Clear all application data (Windows)
# Delete: %APPDATA%\auto-claude-ui
```

**Warning**: This will remove ALL application settings, not just MCP servers.

---

## Known Limitations

### 1. Connection Test is Simulated

**Current Behavior**:
- Connection testing in Phase 2 always succeeds with simulated capabilities
- Returns hardcoded test data:
  - 1 tool: "test-tool"
  - 1 prompt: "test-prompt"
  - 0 resources

**Why**:
- Phase 2 focuses on UI/UX and data management
- Real connection testing requires actual MCP client implementation

**Future (Phase 3)**:
- Real connection testing will be implemented
- Actual capability discovery from running servers
- Connection timeout handling
- Network error handling

### 2. No Edit/Delete Functionality

**Current Behavior**:
- Once a server is added, it cannot be edited or deleted through the UI
- Servers can only be enabled/disabled

**Workaround**:
- Manually edit `mcp-servers.json` file
- Or remove the file and re-add servers

**Future (Phase 3)**:
- Edit server configuration
- Delete servers
- Duplicate server configurations

### 3. FastMCP Wizard Not Implemented

**Current Behavior**:
- "Create New with FastMCP" button shows placeholder
- No actual FastMCP server generation

**Future (Phase 3)**:
- Full FastMCP wizard with code generation
- Template selection
- Tool definition interface

### 4. No Connection Validation

**Current Behavior**:
- Invalid URLs may be saved (basic validation only)
- Incorrect command paths are not detected at save time
- Authentication credentials are not verified

**Future (Phase 3)**:
- Real-time validation
- Path/command existence checking
- Credential verification

### 5. No Import/Export

**Current Behavior**:
- Servers can only be added manually
- No bulk operations

**Future (Phase 3+)**:
- Import server configurations from file
- Export servers for sharing
- Import from community registry

---

## Verification Checklist

Use this checklist to verify Phase 2 implementation:

### Automated Tests
- [ ] All 130+ tests pass (`npm test`)
- [ ] Type tests pass (mcp.test.ts)
- [ ] Component tests pass (all form components)
- [ ] IPC handler tests pass (mcp-handlers.test.ts)
- [ ] Integration tests pass (MCPManager.test.tsx)

### Manual Testing
- [ ] HTTP server can be added successfully
- [ ] stdio server can be added successfully
- [ ] SSE server can be added successfully
- [ ] Custom servers appear in MCP list
- [ ] Enable/disable toggle works
- [ ] Wizard navigation (back/cancel) works
- [ ] Form validation works correctly
- [ ] Connection test completes (simulated)
- [ ] Servers persist after restart

### Edge Cases
- [ ] Empty headers/env vars are filtered out
- [ ] Special characters handled correctly
- [ ] Invalid URLs rejected
- [ ] Missing required fields blocked

### File System
- [ ] Global config file created at `~/.auto-claude/mcp-servers.json`
- [ ] Project config file created at `.auto-claude/mcp-servers.json` (when project scope selected)
- [ ] Config files have correct JSON format
- [ ] Multiple servers can be stored in same file

### Integration
- [ ] Custom servers coexist with built-in servers
- [ ] No conflicts between server types
- [ ] UI clearly distinguishes custom vs built-in

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check Application Logs**:
   - Main process logs (check terminal where `npm run dev` was run)
   - Renderer process logs (DevTools Console - Cmd+Option+I on macOS)

2. **Check Test Output**:
   - Run specific failing test for detailed error
   - Check test coverage for missing scenarios

3. **Review Implementation**:
   - Reference implementation plan: `docs/plans/2025-12-23-add-existing-server-impl.md`
   - Check test files for expected behavior examples

4. **Debug Tools**:
   - Use React DevTools for component inspection
   - Use Electron DevTools for IPC debugging
   - Check Network tab for any unexpected requests

---

## Summary

Phase 2 implements a complete UI workflow for adding custom MCP servers:

- **3 Connection Types**: HTTP/HTTPS, stdio, SSE
- **Multi-Step Wizard**: Connection Type → Configuration → Test
- **130+ Automated Tests**: Comprehensive coverage
- **Global/Project Scope**: Flexible server management
- **Simulated Testing**: Foundation for Phase 3 real testing

All functionality has been thoroughly tested and is ready for manual QA validation.
