#!/usr/bin/env node
/**
 * Auto-Claude Tools MCP Server - STDIO Transport
 *
 * This is Option A: Standalone subprocess that communicates via stdio.
 * The server exposes Auto-Claude internal functionality as MCP tools.
 *
 * Tools communicate back to Electron main process via HTTP API.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

// HTTP client to communicate with Electron main process
const ELECTRON_API_PORT = process.env.ELECTRON_API_PORT || '9824';
const ELECTRON_API_URL = `http://localhost:${ELECTRON_API_PORT}/api`;

/**
 * Fetch data from Electron main process
 */
async function fetchFromElectron(endpoint: string, params?: Record<string, string>): Promise<any> {
  const url = new URL(`${ELECTRON_API_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, value);
    });
  }

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Electron API error: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create and configure MCP server
 */
async function main() {
  const server = new McpServer({
    name: 'auto-claude-tools',
    version: '1.0.0'
  });

  // Tool 1: Get Build Progress
  server.registerTool(
    'get_build_progress',
    {
      title: 'Get Build Progress',
      description: 'Get current build progress and status for a spec',
      inputSchema: {
        specId: z.string().describe('Spec ID to check progress for (e.g., "001", "spec-001")')
      }
    },
    async ({ specId }) => {
      try {
        const data = await fetchFromElectron('/build-progress', { specId });

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(data, null, 2)
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error fetching build progress: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 2: Get Project Context
  server.registerTool(
    'get_context',
    {
      title: 'Get Project Context',
      description: 'Get project context and codebase information',
      inputSchema: {
        projectPath: z.string().describe('Path to project directory').optional(),
        includeMemory: z.boolean().describe('Include memory/insights from previous builds').default(false)
      }
    },
    async ({ projectPath, includeMemory }) => {
      try {
        const params: Record<string, string> = {};
        if (projectPath) params.projectPath = projectPath;
        if (includeMemory) params.includeMemory = 'true';

        const data = await fetchFromElectron('/context', params);

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(data, null, 2)
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error fetching context: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 3: Search Code
  server.registerTool(
    'search_code',
    {
      title: 'Search Code',
      description: 'Search for code patterns in the project codebase',
      inputSchema: {
        query: z.string().describe('Search query (supports regex)'),
        filePattern: z.string().describe('File pattern to search in (e.g., "*.ts", "src/**/*.py")').optional(),
        caseSensitive: z.boolean().describe('Case sensitive search').default(false),
        maxResults: z.number().min(1).max(100).describe('Maximum number of results').default(20)
      }
    },
    async ({ query, filePattern, caseSensitive, maxResults }) => {
      try {
        const params: Record<string, string> = { query };
        if (filePattern) params.filePattern = filePattern;
        if (caseSensitive) params.caseSensitive = 'true';
        if (maxResults) params.maxResults = String(maxResults);

        const data = await fetchFromElectron('/search-code', params);

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(data, null, 2)
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error searching code: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 4: Update Subtask Status
  server.registerTool(
    'update_subtask_status',
    {
      title: 'Update Subtask Status',
      description: 'Update the status of a subtask in implementation_plan.json',
      inputSchema: {
        subtask_id: z.string().describe('The subtask ID to update'),
        status: z.string().describe('New status: pending, in_progress, completed, failed'),
        notes: z.string().describe('Optional notes about the status change').optional()
      }
    },
    async ({ subtask_id, status, notes }) => {
      try {
        const params: Record<string, string> = { subtask_id, status };
        if (notes) params.notes = notes;

        const data = await fetchFromElectron('/update-subtask-status', params);

        return {
          content: [{
            type: 'text',
            text: `Subtask ${subtask_id} updated to ${status}`
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error updating subtask: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 5: Record Discovery
  server.registerTool(
    'record_discovery',
    {
      title: 'Record Discovery',
      description: 'Record a codebase discovery to session memory',
      inputSchema: {
        file_path: z.string().describe('Path to the discovered file'),
        description: z.string().describe('Description of what was discovered'),
        category: z.string().describe('Category: general, pattern, architecture, etc.').optional()
      }
    },
    async ({ file_path, description, category }) => {
      try {
        const params: Record<string, string> = { file_path, description };
        if (category) params.category = category;

        const data = await fetchFromElectron('/record-discovery', params);

        return {
          content: [{
            type: 'text',
            text: `Recorded discovery for ${file_path}`
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error recording discovery: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 6: Record Gotcha
  server.registerTool(
    'record_gotcha',
    {
      title: 'Record Gotcha',
      description: 'Record a gotcha or pitfall to avoid',
      inputSchema: {
        gotcha: z.string().describe('The gotcha or pitfall to record'),
        context: z.string().describe('Context about when this applies').optional()
      }
    },
    async ({ gotcha, context }) => {
      try {
        const params: Record<string, string> = { gotcha };
        if (context) params.context = context;

        const data = await fetchFromElectron('/record-gotcha', params);

        return {
          content: [{
            type: 'text',
            text: `Recorded gotcha: ${gotcha.substring(0, 50)}...`
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error recording gotcha: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 7: Get Session Context
  server.registerTool(
    'get_session_context',
    {
      title: 'Get Session Context',
      description: 'Get context from previous sessions including discoveries and patterns',
      inputSchema: {}
    },
    async () => {
      try {
        const data = await fetchFromElectron('/session-context');

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(data, null, 2)
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error getting session context: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 8: Update QA Status
  server.registerTool(
    'update_qa_status',
    {
      title: 'Update QA Status',
      description: 'Update the QA sign-off status in implementation_plan.json',
      inputSchema: {
        status: z.string().describe('QA status: pending, in_review, approved, rejected, fixes_applied'),
        issues: z.string().describe('JSON array of issues found').optional(),
        tests_passed: z.string().describe('JSON object of test results').optional()
      }
    },
    async ({ status, issues, tests_passed }) => {
      try {
        const params: Record<string, string> = { status };
        if (issues) params.issues = issues;
        if (tests_passed) params.tests_passed = tests_passed;

        const data = await fetchFromElectron('/update-qa-status', params);

        return {
          content: [{
            type: 'text',
            text: `QA status updated to ${status}`
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error updating QA status: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 9: Report Activity (ROI Tracking)
  server.registerTool(
    'report_activity',
    {
      title: 'Report Activity',
      description: 'Report a completed activity for ROI tracking (execution, decision, prevention, knowledge)',
      inputSchema: {
        activity_type: z.string().describe('Activity type: file_created, bug_fixed, recommendation_made, diagram_generated, etc.'),
        description: z.string().describe('Description of the activity'),
        count: z.number().describe('Number of items (default: 1)').optional(),
        complexity: z.string().describe('Complexity: low, medium, high').optional()
      }
    },
    async ({ activity_type, description, count, complexity }) => {
      try {
        const params: Record<string, string> = { activity_type, description };
        if (count) params.count = String(count);
        if (complexity) params.complexity = complexity;

        const data = await fetchFromElectron('/report-activity', params);

        return {
          content: [{
            type: 'text',
            text: `Activity reported: ${activity_type} - ${description}`
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error reporting activity: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 10: Get Activity Summary
  server.registerTool(
    'get_activity_summary',
    {
      title: 'Get Activity Summary',
      description: 'Get a summary of all activities recorded in this session',
      inputSchema: {}
    },
    async () => {
      try {
        const data = await fetchFromElectron('/activity-summary');

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(data, null, 2)
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error getting activity summary: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 11: List Activity Types
  server.registerTool(
    'list_activity_types',
    {
      title: 'List Activity Types',
      description: 'List all available activity types and their values for ROI tracking',
      inputSchema: {
        category: z.string().describe('Filter by category: execution, decision, prevention, knowledge').optional()
      }
    },
    async ({ category }) => {
      try {
        const params: Record<string, string> = {};
        if (category) params.category = category;

        const data = await fetchFromElectron('/activity-types', params);

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(data, null, 2)
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error listing activity types: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // ============================================================================
  // PROMPTS - Pre-configured prompt templates for common auto-claude workflows
  // ============================================================================

  // Prompt 1: Spec Creation
  server.registerPrompt(
    'spec-creation',
    {
      title: 'Spec Creation Template',
      description: 'Template for creating a new feature specification',
      argsSchema: {
        task_description: z.string().describe('Description of the feature or task to implement'),
        complexity: z.enum(['simple', 'standard', 'complex']).describe('Expected complexity level').optional()
      }
    },
    async ({ task_description, complexity }) => {
      return {
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `Create a comprehensive spec for the following task:

## Task Description
${task_description}

${complexity ? `## Complexity Level: ${complexity}` : ''}

## Requirements
Please analyze this task and create a specification that includes:
1. Feature overview and goals
2. User stories and acceptance criteria
3. Technical requirements and constraints
4. Implementation approach
5. Testing strategy
6. Potential risks and mitigations

Focus on clarity and actionability. The spec should be detailed enough for an AI agent to implement autonomously.`
            }
          }
        ]
      };
    }
  );

  // Prompt 2: Code Review
  server.registerPrompt(
    'code-review',
    {
      title: 'Code Review Template',
      description: 'Template for reviewing code changes',
      argsSchema: {
        file_paths: z.string().describe('Comma-separated list of file paths to review'),
        focus_areas: z.string().describe('Areas to focus on: security, performance, readability, etc.').optional()
      }
    },
    async ({ file_paths, focus_areas }) => {
      return {
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `Please perform a thorough code review of the following files:

## Files to Review
${file_paths.split(',').map(f => `- ${f.trim()}`).join('\n')}

${focus_areas ? `## Focus Areas\n${focus_areas}` : ''}

## Review Criteria
1. **Code Quality**: Is the code clean, readable, and maintainable?
2. **Security**: Are there any security vulnerabilities?
3. **Performance**: Are there any performance concerns?
4. **Best Practices**: Does it follow project conventions?
5. **Error Handling**: Is error handling adequate?
6. **Testing**: Are there sufficient tests?

Provide specific, actionable feedback with line numbers where applicable.`
            }
          }
        ]
      };
    }
  );

  // Prompt 3: Bug Investigation
  server.registerPrompt(
    'bug-investigation',
    {
      title: 'Bug Investigation Template',
      description: 'Template for investigating and diagnosing bugs',
      argsSchema: {
        bug_description: z.string().describe('Description of the bug or issue'),
        error_message: z.string().describe('Error message if available').optional(),
        steps_to_reproduce: z.string().describe('Steps to reproduce the bug').optional()
      }
    },
    async ({ bug_description, error_message, steps_to_reproduce }) => {
      return {
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `Investigate the following bug:

## Bug Description
${bug_description}

${error_message ? `## Error Message\n\`\`\`\n${error_message}\n\`\`\`` : ''}

${steps_to_reproduce ? `## Steps to Reproduce\n${steps_to_reproduce}` : ''}

## Investigation Plan
1. Identify the root cause of the issue
2. Locate relevant code files and functions
3. Analyze the execution flow
4. Propose a fix with minimal side effects
5. Suggest tests to prevent regression

Please be systematic and thorough in your investigation.`
            }
          }
        ]
      };
    }
  );

  // Prompt 4: Feature Planning
  server.registerPrompt(
    'feature-planning',
    {
      title: 'Feature Planning Template',
      description: 'Template for planning new feature implementation',
      argsSchema: {
        feature_name: z.string().describe('Name of the feature'),
        requirements: z.string().describe('Feature requirements and goals'),
        constraints: z.string().describe('Technical or business constraints').optional()
      }
    },
    async ({ feature_name, requirements, constraints }) => {
      return {
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `Create an implementation plan for: ${feature_name}

## Requirements
${requirements}

${constraints ? `## Constraints\n${constraints}` : ''}

## Planning Deliverables
1. **Architecture Overview**: High-level design and components
2. **Subtasks**: Break down into implementable subtasks
3. **Dependencies**: Identify dependencies between tasks
4. **Files to Modify**: List files that need changes
5. **New Files**: List new files to create
6. **Testing Strategy**: Unit, integration, and E2E tests
7. **Rollout Plan**: Phased implementation if needed

Create a detailed plan that can be executed by autonomous agents.`
            }
          }
        ]
      };
    }
  );

  // Prompt 5: QA Checklist
  server.registerPrompt(
    'qa-checklist',
    {
      title: 'QA Checklist Template',
      description: 'Template for QA validation of implemented features',
      argsSchema: {
        spec_id: z.string().describe('Spec ID to validate'),
        acceptance_criteria: z.string().describe('Acceptance criteria to verify')
      }
    },
    async ({ spec_id, acceptance_criteria }) => {
      return {
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `Perform QA validation for spec: ${spec_id}

## Acceptance Criteria
${acceptance_criteria}

## QA Checklist
1. **Functionality**: Does it meet all acceptance criteria?
2. **Error Handling**: Are errors handled gracefully?
3. **Edge Cases**: Are edge cases covered?
4. **Performance**: Is performance acceptable?
5. **Security**: Are there security concerns?
6. **Accessibility**: Is it accessible?
7. **Documentation**: Is code documented?
8. **Tests**: Do all tests pass?

For each item, provide: PASS/FAIL with explanation.
If any FAIL, provide specific fix instructions.`
            }
          }
        ]
      };
    }
  );

  // Prompt 6: ROI Report
  server.registerPrompt(
    'roi-report',
    {
      title: 'ROI Report Template',
      description: 'Template for generating ROI analysis report',
      argsSchema: {
        time_period: z.enum(['session', 'day', 'week', 'month']).describe('Time period for the report'),
        include_details: z.boolean().describe('Include detailed breakdown').optional()
      }
    },
    async ({ time_period, include_details }) => {
      return {
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `Generate an ROI analysis report for: ${time_period}

${include_details ? '## Include Detailed Breakdown' : ''}

## Report Sections
1. **Executive Summary**: Key metrics and highlights
2. **Activity Breakdown**: By category (execution, decision, prevention, knowledge)
3. **Value Delivered**: Estimated hours saved and value generated
4. **Top Contributions**: Most impactful activities
5. **Trends**: Comparison with previous periods
6. **Recommendations**: Suggestions for improvement

Use data from the activity summary and provide actionable insights.`
            }
          }
        ]
      };
    }
  );

  // ============================================================================
  // RESOURCES - Accessible data and documentation
  // ============================================================================

  // Resource 1: Activity Types Reference
  server.registerResource(
    'activity-types',
    'auto-claude://reference/activity-types',
    {
      description: 'Complete reference of all activity types for ROI tracking',
      mimeType: 'application/json'
    },
    async () => {
      try {
        const data = await fetchFromElectron('/activity-types');
        return {
          contents: [{
            uri: 'auto-claude://reference/activity-types',
            mimeType: 'application/json',
            text: JSON.stringify(data, null, 2)
          }]
        };
      } catch (error) {
        return {
          contents: [{
            uri: 'auto-claude://reference/activity-types',
            mimeType: 'application/json',
            text: JSON.stringify({
              execution: [
                { type: 'file_created', value: 15, description: 'New file created' },
                { type: 'file_modified', value: 5, description: 'File modified' },
                { type: 'bug_fixed', value: 30, description: 'Bug fixed' },
                { type: 'feature_implemented', value: 50, description: 'Feature implemented' },
                { type: 'test_written', value: 20, description: 'Test written' }
              ],
              decision: [
                { type: 'architecture_decision', value: 40, description: 'Architecture decision made' },
                { type: 'recommendation_made', value: 25, description: 'Recommendation made' },
                { type: 'trade_off_analyzed', value: 30, description: 'Trade-off analyzed' }
              ],
              prevention: [
                { type: 'issue_prevented', value: 45, description: 'Issue prevented before coding' },
                { type: 'security_vulnerability_avoided', value: 60, description: 'Security vulnerability avoided' },
                { type: 'performance_issue_prevented', value: 35, description: 'Performance issue prevented' }
              ],
              knowledge: [
                { type: 'documentation_created', value: 20, description: 'Documentation created' },
                { type: 'diagram_generated', value: 25, description: 'Diagram generated' },
                { type: 'insight_discovered', value: 15, description: 'Insight discovered' }
              ]
            }, null, 2)
          }]
        };
      }
    }
  );

  // Resource 2: Spec Template
  server.registerResource(
    'spec-template',
    'auto-claude://templates/spec',
    {
      description: 'Template structure for creating spec.md files',
      mimeType: 'text/markdown'
    },
    async () => {
      return {
        contents: [{
          uri: 'auto-claude://templates/spec',
          mimeType: 'text/markdown',
          text: `# Feature Specification: [FEATURE_NAME]

## Overview
Brief description of what this feature does and why it's needed.

## Goals
- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

## User Stories
### As a [user type], I want to [action] so that [benefit]
**Acceptance Criteria:**
- Criterion 1
- Criterion 2
- Criterion 3

## Technical Requirements
### Prerequisites
- Requirement 1
- Requirement 2

### Architecture
Describe the technical approach and architecture decisions.

### API Changes
Document any API changes if applicable.

## Implementation Notes
Any specific implementation guidance or constraints.

## Testing Strategy
- Unit tests: What to test
- Integration tests: What to test
- E2E tests: What to test

## Rollout Plan
Describe phased rollout if needed.

## Risks and Mitigations
| Risk | Mitigation |
|------|------------|
| Risk 1 | Mitigation 1 |
`
        }]
      };
    }
  );

  // Resource 3: Implementation Plan Schema
  server.registerResource(
    'implementation-plan-schema',
    'auto-claude://schemas/implementation-plan',
    {
      description: 'JSON schema for implementation_plan.json files',
      mimeType: 'application/json'
    },
    async () => {
      return {
        contents: [{
          uri: 'auto-claude://schemas/implementation-plan',
          mimeType: 'application/json',
          text: JSON.stringify({
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["spec_id", "subtasks", "qa_signoff"],
            "properties": {
              "spec_id": {
                "type": "string",
                "description": "Unique identifier for the spec"
              },
              "created_at": {
                "type": "string",
                "format": "date-time"
              },
              "updated_at": {
                "type": "string",
                "format": "date-time"
              },
              "subtasks": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["id", "title", "status"],
                  "properties": {
                    "id": { "type": "string" },
                    "title": { "type": "string" },
                    "description": { "type": "string" },
                    "status": {
                      "type": "string",
                      "enum": ["pending", "in_progress", "completed", "failed"]
                    },
                    "files_to_modify": {
                      "type": "array",
                      "items": { "type": "string" }
                    },
                    "files_to_create": {
                      "type": "array",
                      "items": { "type": "string" }
                    },
                    "dependencies": {
                      "type": "array",
                      "items": { "type": "string" }
                    }
                  }
                }
              },
              "qa_signoff": {
                "type": "object",
                "properties": {
                  "status": {
                    "type": "string",
                    "enum": ["pending", "in_review", "approved", "rejected", "fixes_applied"]
                  },
                  "issues": {
                    "type": "array",
                    "items": { "type": "string" }
                  },
                  "reviewed_at": {
                    "type": "string",
                    "format": "date-time"
                  }
                }
              }
            }
          }, null, 2)
        }]
      };
    }
  );

  // Resource 4: Session Context (Dynamic)
  server.registerResource(
    'session-context',
    'auto-claude://context/session',
    {
      description: 'Dynamic resource showing current session discoveries and patterns',
      mimeType: 'application/json'
    },
    async () => {
      try {
        const data = await fetchFromElectron('/session-context');
        return {
          contents: [{
            uri: 'auto-claude://context/session',
            mimeType: 'application/json',
            text: JSON.stringify(data, null, 2)
          }]
        };
      } catch (error) {
        return {
          contents: [{
            uri: 'auto-claude://context/session',
            mimeType: 'application/json',
            text: JSON.stringify({
              sessionId: 'unknown',
              startedAt: new Date().toISOString(),
              discoveries: [],
              gotchas: [],
              patterns: [],
              note: 'Session context not available from API'
            }, null, 2)
          }]
        };
      }
    }
  );

  // Resource 5: Activity Summary (Dynamic)
  server.registerResource(
    'activity-summary',
    'auto-claude://reports/activity-summary',
    {
      description: 'Dynamic resource showing current session activity summary',
      mimeType: 'application/json'
    },
    async () => {
      try {
        const data = await fetchFromElectron('/activity-summary');
        return {
          contents: [{
            uri: 'auto-claude://reports/activity-summary',
            mimeType: 'application/json',
            text: JSON.stringify(data, null, 2)
          }]
        };
      } catch (error) {
        return {
          contents: [{
            uri: 'auto-claude://reports/activity-summary',
            mimeType: 'application/json',
            text: JSON.stringify({
              totalActivities: 0,
              summary: {},
              generatedAt: new Date().toISOString(),
              note: 'Activity summary not available from API'
            }, null, 2)
          }]
        };
      }
    }
  );

  // Resource 6: Auto-Claude Documentation
  server.registerResource(
    'documentation',
    'auto-claude://docs/overview',
    {
      description: 'Overview documentation for Auto-Claude system',
      mimeType: 'text/markdown'
    },
    async () => {
      return {
        contents: [{
          uri: 'auto-claude://docs/overview',
          mimeType: 'text/markdown',
          text: `# Auto-Claude Overview

Auto-Claude is a multi-agent autonomous coding framework that builds software through coordinated AI agent sessions.

## Core Workflow

1. **Spec Creation** - Create a feature specification
2. **Planning** - Planner agent creates implementation subtasks
3. **Coding** - Coder agent implements each subtask
4. **QA Review** - QA agent validates acceptance criteria
5. **QA Fix** - Fixer agent resolves any issues

## Available MCP Tools

### Build & Progress
- \`get_build_progress\` - Get current build status
- \`update_subtask_status\` - Update subtask completion

### Context & Memory
- \`get_context\` - Get project context
- \`get_session_context\` - Get session memory
- \`record_discovery\` - Record codebase discovery
- \`record_gotcha\` - Record pitfalls to avoid

### Code Operations
- \`search_code\` - Search codebase with patterns

### QA Operations
- \`update_qa_status\` - Update QA sign-off status

### ROI Tracking
- \`report_activity\` - Report completed activities
- \`get_activity_summary\` - Get activity summary
- \`list_activity_types\` - List activity types

## Available Prompts

- \`spec-creation\` - Template for creating specs
- \`code-review\` - Template for code reviews
- \`bug-investigation\` - Template for bug diagnosis
- \`feature-planning\` - Template for feature planning
- \`qa-checklist\` - Template for QA validation
- \`roi-report\` - Template for ROI reports

## Available Resources

- \`activity-types\` - ROI activity type reference
- \`spec-template\` - Spec.md template
- \`implementation-plan-schema\` - Plan JSON schema
- \`session-context\` - Current session context
- \`activity-summary\` - Current activity summary
- \`documentation\` - This documentation
`
        }]
      };
    }
  );

  // Connect via stdio transport
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error('[Auto-Claude Tools STDIO] Server started with 11 tools, 6 prompts, 6 resources');
}

// Run server
main().catch((error) => {
  console.error('[Auto-Claude Tools STDIO] Fatal error:', error);
  process.exit(1);
});
