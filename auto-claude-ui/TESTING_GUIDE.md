# Manual Testing Guide: MCP Capabilities View

This guide provides step-by-step instructions for manually testing the MCP Capabilities View implementation (Phase 1).

## Overview

The MCP Capabilities View allows users to explore detailed information about MCP server capabilities, including:
- Tools (with parameters, types, and descriptions)
- Prompts (with arguments and templates)
- Resources (with URIs and MIME types)

## Prerequisites

1. Application is built and running:
   ```bash
   cd auto-claude-ui
   npm install
   npm run build
   npm start
   ```

2. You have access to at least one configured MCP server (built-in servers should work by default)

## Test Scenarios

### Scenario 1: View Server Capabilities

**Objective**: Verify that the capabilities view displays all three types of capabilities (tools, prompts, resources)

**Steps**:
1. Launch the Auto-Claude UI application
2. Navigate to Settings > MCP Servers
3. Locate a server card (e.g., "Context7" or "Auto-Claude Tools")
4. Click the expand arrow (▼) on the server card

**Expected Results**:
- The capabilities view expands smoothly with animation
- Three tabs are visible: "Tools", "Prompts", "Resources"
- Each tab shows a count badge (e.g., "Tools (5)")
- The "Tools" tab is selected by default
- If the server has no capabilities of a certain type, the count shows "0"

**Pass/Fail**: ☐

---

### Scenario 2: Tools Tab - Basic Display

**Objective**: Verify that tools are displayed correctly with all relevant information

**Steps**:
1. With a server expanded (from Scenario 1)
2. Ensure the "Tools" tab is selected
3. Observe the list of tools

**Expected Results**:
- All available tools are listed
- Each tool shows:
  - Tool name (in monospace font)
  - Description
  - Expand arrow (▶) to view parameters
- Tools are initially collapsed
- If the server has no tools, an empty state message is shown

**Pass/Fail**: ☐

---

### Scenario 3: Tools Tab - Expand Tool Details

**Objective**: Verify that tool parameter information can be expanded and is displayed correctly

**Steps**:
1. From the Tools tab (Scenario 2)
2. Click the expand arrow (▶) next to any tool name
3. Observe the expanded tool details

**Expected Results**:
- The tool expands smoothly with animation
- The arrow changes to (▼)
- If the tool has parameters, they are displayed in a table/list format showing:
  - Parameter name
  - Parameter type (e.g., `string`, `number`, `boolean`, `object`, `array`)
  - Required/Optional status
  - Description (if available)
- If the tool has no parameters, a message indicates "No parameters"
- Clicking the arrow again collapses the tool details

**Pass/Fail**: ☐

---

### Scenario 4: Tools Tab - Copy Functionality

**Objective**: Verify that tool names can be copied to clipboard

**Steps**:
1. From the Tools tab with an expanded tool
2. Look for a "Copy" button or icon next to the tool name
3. Click the copy button

**Expected Results**:
- A toast notification appears confirming "Copied to clipboard" or similar
- The tool name is copied to the system clipboard
- Pasting (Cmd+V / Ctrl+V) in a text editor shows the exact tool name

**Pass/Fail**: ☐

---

### Scenario 5: Prompts Tab - Basic Display

**Objective**: Verify that prompts are displayed correctly

**Steps**:
1. With a server expanded
2. Click the "Prompts" tab
3. Observe the list of prompts

**Expected Results**:
- The Prompts tab becomes active (highlighted)
- All available prompts are listed
- Each prompt shows:
  - Prompt name (in monospace font)
  - Description
  - Expand arrow (▶) to view arguments
- Prompts are initially collapsed
- If the server has no prompts, an empty state message is shown

**Pass/Fail**: ☐

---

### Scenario 6: Prompts Tab - Expand Prompt Details

**Objective**: Verify that prompt argument information can be expanded

**Steps**:
1. From the Prompts tab (Scenario 5)
2. Click the expand arrow (▶) next to any prompt name
3. Observe the expanded prompt details

**Expected Results**:
- The prompt expands smoothly with animation
- The arrow changes to (▼)
- If the prompt has arguments, they are displayed showing:
  - Argument name
  - Required/Optional status
  - Description (if available)
- If the prompt has no arguments, a message indicates "No arguments"
- Clicking the arrow again collapses the prompt details

**Pass/Fail**: ☐

---

### Scenario 7: Resources Tab - Basic Display

**Objective**: Verify that resources are displayed correctly

**Steps**:
1. With a server expanded
2. Click the "Resources" tab
3. Observe the list of resources

**Expected Results**:
- The Resources tab becomes active (highlighted)
- All available resources are listed
- Each resource shows:
  - Resource URI template (in monospace font)
  - Description
  - MIME type (if available)
  - Expand arrow (▶) for additional details
- Resources are initially collapsed
- If the server has no resources, an empty state message is shown

**Pass/Fail**: ☐

---

### Scenario 8: Resources Tab - URI Template Display

**Objective**: Verify that URI templates with parameters are displayed correctly

**Steps**:
1. From the Resources tab (Scenario 7)
2. Look for a resource with a URI template containing parameters (e.g., `myserver://docs/{id}`)
3. Click the expand arrow if available

**Expected Results**:
- URI templates are displayed in full
- Template parameters (e.g., `{id}`, `{path}`) are highlighted or clearly indicated
- Clicking expand shows additional information about template parameters
- Copy functionality works for URI templates

**Pass/Fail**: ☐

---

### Scenario 9: Tab Switching

**Objective**: Verify smooth tab switching between Tools, Prompts, and Resources

**Steps**:
1. With a server expanded
2. Click through all three tabs: Tools → Prompts → Resources → Tools
3. Observe the transitions

**Expected Results**:
- Tab switching is instant (no loading delay)
- Content updates immediately when switching tabs
- The active tab is clearly highlighted
- Previously expanded items remain expanded when returning to a tab
- No console errors occur during tab switching

**Pass/Fail**: ☐

---

### Scenario 10: Multiple Servers

**Objective**: Verify that multiple servers can be expanded simultaneously

**Steps**:
1. From the MCP Manager view
2. Expand one server's capabilities
3. Without collapsing the first, expand a second server's capabilities
4. Observe both expanded views

**Expected Results**:
- Both servers remain expanded simultaneously
- Each server's capabilities are independent
- Scrolling works smoothly with multiple expanded views
- Collapsing one server doesn't affect the other

**Pass/Fail**: ☐

---

### Scenario 11: Server with No Capabilities

**Objective**: Verify proper handling of servers with no capabilities

**Steps**:
1. If possible, add a test server with no tools, prompts, or resources
2. Expand the server's capabilities view

**Expected Results**:
- The capabilities view still expands
- All three tabs show count "(0)"
- Each tab displays an appropriate empty state message
- No errors occur

**Pass/Fail**: ☐

---

### Scenario 12: Collapse Capabilities View

**Objective**: Verify that collapsing the capabilities view works correctly

**Steps**:
1. With a server's capabilities expanded
2. Click the collapse arrow (▲) on the server card
3. Observe the collapse animation

**Expected Results**:
- The capabilities view collapses smoothly with animation
- The arrow changes back to (▼)
- The collapsed state is maintained if you scroll away and back
- Re-expanding shows the last active tab

**Pass/Fail**: ☐

---

### Scenario 13: Performance with Many Capabilities

**Objective**: Verify performance with servers that have many tools/prompts/resources

**Steps**:
1. Find or configure a server with 10+ tools
2. Expand the capabilities view
3. Expand several tools to show parameters
4. Switch between tabs multiple times

**Expected Results**:
- Initial expansion is smooth (< 300ms)
- Tool expansion is responsive (< 100ms)
- Tab switching remains instant
- Scrolling is smooth with many expanded items
- No UI lag or freezing

**Pass/Fail**: ☐

---

### Scenario 14: Responsive Design

**Objective**: Verify the capabilities view adapts to different window sizes

**Steps**:
1. With a server's capabilities expanded
2. Resize the application window to various widths (wide, medium, narrow)
3. Observe how the layout adapts

**Expected Results**:
- Content remains readable at all window sizes
- No horizontal scrolling required
- Parameters table/list adapts to available width
- Long tool names wrap or truncate appropriately
- Copy buttons remain accessible

**Pass/Fail**: ☐

---

### Scenario 15: Accessibility

**Objective**: Verify keyboard navigation and screen reader support

**Steps**:
1. From the MCP Manager view
2. Use Tab key to navigate to a server card
3. Press Enter to expand capabilities
4. Use arrow keys to navigate tabs
5. Use Tab to navigate through tools/prompts/resources

**Expected Results**:
- All interactive elements are keyboard accessible
- Focus indicators are clearly visible
- Enter/Space keys work for expand/collapse
- Arrow keys navigate between tabs
- Tab key navigates through list items
- Screen reader announces tab changes and expansion states

**Pass/Fail**: ☐

---

## Automated Test Verification

Before manual testing, run the automated test suite to ensure all components pass unit tests:

```bash
cd auto-claude-ui
npm test -- --watchAll=false src/renderer/components/mcp/
```

**Expected Results**:
- All tests pass (0 failures)
- Coverage for new components:
  - MCPCapabilitiesView.tsx
  - MCPToolsList.tsx
  - MCPPromptsList.tsx
  - MCPResourcesList.tsx
- No console warnings or errors

**Pass/Fail**: ☐

---

## Build Verification

Verify that the application builds without errors:

```bash
cd auto-claude-ui
npm run build
```

**Expected Results**:
- Build completes successfully
- No TypeScript errors
- No webpack warnings
- Output files generated in `dist/` directory

**Pass/Fail**: ☐

---

## Known Limitations / Future Enhancements

Document any known issues or planned improvements discovered during testing:

1. _Add items here as discovered during testing_
2.
3.

---

## Test Environment

**Date**: _____________

**Tester**: _____________

**OS**: ☐ macOS  ☐ Windows  ☐ Linux

**Node Version**: _____________

**npm Version**: _____________

**Electron Version**: _____________

**Git Commit**: _____________

---

## Summary

**Total Scenarios**: 15

**Passed**: _____ / 15

**Failed**: _____ / 15

**Issues Found**: _____

**Blocker Issues**: _____

**Overall Status**: ☐ PASS  ☐ FAIL  ☐ NEEDS REVIEW

---

## Issue Tracking

If issues are found, document them here:

### Issue 1
- **Scenario**:
- **Severity**: ☐ Critical  ☐ High  ☐ Medium  ☐ Low
- **Description**:
- **Steps to Reproduce**:
- **Expected**:
- **Actual**:
- **Screenshot/Video**:

### Issue 2
- **Scenario**:
- **Severity**: ☐ Critical  ☐ High  ☐ Medium  ☐ Low
- **Description**:
- **Steps to Reproduce**:
- **Expected**:
- **Actual**:
- **Screenshot/Video**:

---

## Sign-off

By completing this testing guide, I confirm that:

- [ ] All manual test scenarios have been executed
- [ ] All automated tests pass
- [ ] The application builds successfully
- [ ] Issues have been documented and reported
- [ ] The MCP Capabilities View is ready for merge/production (or requires fixes)

**Tester Signature**: ____________________  **Date**: ____________
