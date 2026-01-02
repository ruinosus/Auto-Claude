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
  // ARTIFACT TOOLS - Access full artifact content from local storage
  // ============================================================================

  // Tool 12: Get Artifact
  server.registerTool(
    'get_artifact',
    {
      title: 'Get Artifact',
      description: 'Get a single artifact by ID with FULL content from local storage',
      inputSchema: {
        artifact_id: z.string().describe('The artifact ID (e.g., "art_abc123def456")'),
        project_path: z.string().describe('Path to the project directory')
      }
    },
    async ({ artifact_id, project_path }) => {
      try {
        const response = await fetch(
          `${ELECTRON_API_URL}/artifact/${artifact_id}?projectPath=${encodeURIComponent(project_path)}`
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const artifact = await response.json();

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(artifact, null, 2)
          }],
          structuredContent: artifact
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error getting artifact: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 13: List Artifacts
  server.registerTool(
    'list_artifacts',
    {
      title: 'List Artifacts',
      description: 'List artifacts from local storage with optional filters',
      inputSchema: {
        project_path: z.string().describe('Path to the project directory'),
        spec_id: z.string().describe('Filter by spec ID').optional(),
        trace_id: z.string().describe('Filter by Langfuse trace ID').optional(),
        type: z.string().describe('Filter by artifact type (e.g., "qa_finding", "code_implementation")').optional(),
        limit: z.number().describe('Maximum number of artifacts to return').default(50).optional()
      }
    },
    async ({ project_path, spec_id, trace_id, type, limit }) => {
      try {
        const params: Record<string, string> = { projectPath: project_path };
        if (spec_id) params.spec_id = spec_id;
        if (trace_id) params.trace_id = trace_id;
        if (type) params.type = type;
        if (limit) params.limit = String(limit);

        const url = new URL(`${ELECTRON_API_URL}/artifacts`);
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, value);
        });

        const response = await fetch(url.toString());

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const data = await response.json();

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
          content: [{ type: 'text', text: `Error listing artifacts: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 14: Get Artifacts by Trace
  server.registerTool(
    'get_artifacts_by_trace',
    {
      title: 'Get Artifacts by Trace',
      description: 'Get all artifacts associated with a specific Langfuse trace ID',
      inputSchema: {
        trace_id: z.string().describe('The Langfuse trace ID'),
        project_path: z.string().describe('Path to the project directory')
      }
    },
    async ({ trace_id, project_path }) => {
      try {
        const response = await fetch(
          `${ELECTRON_API_URL}/artifacts/trace/${trace_id}?projectPath=${encodeURIComponent(project_path)}`
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const data = await response.json();

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
          content: [{ type: 'text', text: `Error getting artifacts by trace: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 15: Get Artifact Content
  server.registerTool(
    'get_artifact_content',
    {
      title: 'Get Artifact Content',
      description: 'Get only the content of an artifact (useful for large artifacts)',
      inputSchema: {
        artifact_id: z.string().describe('The artifact ID'),
        project_path: z.string().describe('Path to the project directory')
      }
    },
    async ({ artifact_id, project_path }) => {
      try {
        const response = await fetch(
          `${ELECTRON_API_URL}/artifact/${artifact_id}/content?projectPath=${encodeURIComponent(project_path)}`
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const content = await response.text();

        return {
          content: [{
            type: 'text',
            text: content
          }]
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error getting artifact content: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 16: Aggregate Artifacts by Agent
  server.registerTool(
    'aggregate_artifacts_by_agent',
    {
      title: 'Aggregate Artifacts by Agent',
      description: 'Get artifacts aggregated by agent type (planner, coder, qa_reviewer, etc.). Returns count, total value, and artifact types per agent.',
      inputSchema: {
        project_path: z.string().describe('Path to the project directory'),
        date_from: z.string().describe('Optional start date filter (YYYY-MM-DD)').optional(),
        date_to: z.string().describe('Optional end date filter (YYYY-MM-DD)').optional()
      }
    },
    async ({ project_path, date_from, date_to }) => {
      try {
        const params: Record<string, string> = { projectPath: project_path };
        if (date_from) params.date_from = date_from;
        if (date_to) params.date_to = date_to;

        const url = new URL(`${ELECTRON_API_URL}/artifacts/by-agent`);
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, value);
        });

        const response = await fetch(url.toString());

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const data = await response.json();

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
          content: [{ type: 'text', text: `Error aggregating artifacts by agent: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 17: Get Artifact Statistics
  server.registerTool(
    'get_artifact_statistics',
    {
      title: 'Get Artifact Statistics',
      description: `Get comprehensive artifact statistics for the project including:
- Total count and total value in USD
- Breakdown by artifact type (diagram, code_example, security_finding, etc.)
- Breakdown by dashboard tab (dev, techlead, ops, business)
- Breakdown by time period (last 7 days, last 30 days, all time)
- Top 5 most valuable artifacts
- Value distribution by type and tab`,
      inputSchema: {
        project_path: z.string().describe('Path to the project directory')
      }
    },
    async ({ project_path }) => {
      try {
        const response = await fetch(
          `${ELECTRON_API_URL}/artifacts/statistics?projectPath=${encodeURIComponent(project_path)}`
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const data = await response.json();

        // Format text output
        const lines = ['=== Artifact Statistics ===', ''];

        lines.push('## Overview');
        lines.push(`  Total Artifacts: ${data.total_count}`);
        lines.push(`  Total Value: $${data.total_value_usd.toFixed(2)}`);
        lines.push('');

        lines.push('## By Time Period');
        lines.push(`  Last 7 Days: ${data.by_period?.last_7_days || 0} artifacts`);
        lines.push(`  Last 30 Days: ${data.by_period?.last_30_days || 0} artifacts`);
        lines.push(`  All Time: ${data.by_period?.all_time || 0} artifacts`);
        lines.push('');

        lines.push('## By Dashboard Tab');
        const tabNames: Record<string, string> = {
          dev: 'Developer',
          techlead: 'Tech Lead',
          ops: 'Operations',
          business: 'Business'
        };
        for (const tab of ['dev', 'techlead', 'ops', 'business']) {
          const count = data.by_tab?.[tab] || 0;
          const value = data.value_by_tab?.[tab] || 0;
          lines.push(`  ${tabNames[tab]}: ${count} artifacts ($${value.toFixed(2)})`);
        }
        lines.push('');

        lines.push('## By Artifact Type (Top 10)');
        const sortedTypes = Object.entries(data.by_type || {})
          .sort((a, b) => (data.value_by_type?.[b[0]] || 0) - (data.value_by_type?.[a[0]] || 0))
          .slice(0, 10);
        for (const [artType, count] of sortedTypes) {
          const value = data.value_by_type?.[artType] || 0;
          lines.push(`  ${artType}: ${count} ($${value.toFixed(2)})`);
        }
        lines.push('');

        lines.push('## Top 5 Most Valuable');
        for (const [i, art] of (data.top_valuable || []).entries()) {
          lines.push(`  ${i + 1}. ${art.type} - $${art.value_usd.toFixed(2)}`);
          lines.push(`     ID: ${art.id}, Date: ${art.date}`);
        }
        if (!data.top_valuable?.length) {
          lines.push('  No artifacts with value found.');
        }

        return {
          content: [{
            type: 'text',
            text: lines.join('\n')
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error getting artifact statistics: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 18: Search Artifacts
  server.registerTool(
    'search_artifacts',
    {
      title: 'Search Artifacts',
      description: `Search artifacts by content, description, and type.

Performs case-insensitive full-text search across all stored artifacts.
Returns matching artifacts sorted by relevance with previews and match highlights.

Search is performed on:
- artifact content (code, diagrams, findings, recommendations, etc.)
- artifact description
- artifact type name

Results include:
- Preview of the first 200 characters of content
- Highlighted snippet showing where the query matched
- Location of matches (content, description, or type)
- Relevance score (higher = more relevant)

Examples:
  query: "SQL injection"       -> Find security findings about SQL injection
  query: "authentication"      -> Find all artifacts mentioning authentication
  query: "diagram"             -> Find all diagram artifacts (matches type)`,
      inputSchema: {
        project_path: z.string().describe('Path to the project directory'),
        query: z.string().describe('Search query string (case-insensitive)'),
        artifact_types: z.array(z.string()).describe('Filter by artifact types (e.g., ["security_finding", "diagram"])').optional(),
        spec_id: z.string().describe('Filter by spec ID').optional(),
        limit: z.number().min(1).max(100).describe('Maximum number of results (default: 50)').default(50).optional()
      }
    },
    async ({ project_path, query, artifact_types, spec_id, limit }) => {
      try {
        const params: Record<string, string> = { projectPath: project_path, query };
        if (artifact_types && artifact_types.length > 0) params.artifact_types = JSON.stringify(artifact_types);
        if (spec_id) params.spec_id = spec_id;
        if (limit) params.limit = String(limit);

        const url = new URL(`${ELECTRON_API_URL}/artifacts/search`);
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, value);
        });

        const response = await fetch(url.toString());

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const data = await response.json();

        // Format text output
        const lines = [`=== Search Results for '${query}' ===`, ''];
        lines.push(`Found ${data.total_results || data.results?.length || 0} matching artifact(s)`);
        lines.push('');

        for (const [i, result] of (data.results || []).entries()) {
          lines.push(`## ${i + 1}. ${result.type} ($${result.value_usd || 0})`);
          lines.push(`   ID: ${result.id}`);
          if (result.description) {
            const desc = result.description.length > 100
              ? result.description.substring(0, 100) + '...'
              : result.description;
            lines.push(`   Description: ${desc}`);
          }
          const tabNames: Record<string, string> = {
            dev: 'Developer',
            techlead: 'Tech Lead',
            ops: 'Operations',
            business: 'Business'
          };
          lines.push(`   Tab: ${tabNames[result.tab] || result.tab || 'N/A'}`);
          lines.push(`   Created: ${(result.created_at || 'N/A').substring(0, 10)}`);
          lines.push(`   Matched in: ${(result.match_locations || []).join(', ')}`);
          if (result.match_highlight) {
            lines.push(`   Match: ${result.match_highlight}`);
          }
          lines.push(`   Relevance: ${result.relevance_score || 0}`);
          lines.push('');
        }

        return {
          content: [{
            type: 'text',
            text: lines.join('\n')
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error searching artifacts: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 19: Export Artifacts
  server.registerTool(
    'export_artifacts',
    {
      title: 'Export Artifacts',
      description: `Export artifacts to JSON or Markdown format.

Exports artifacts with optional filters to a file or returns the content directly.
Useful for generating reports, sharing artifacts, or archiving.

Formats:
- json: Structured JSON with full artifact data, summaries, and breakdowns
- markdown: Human-readable Markdown with emojis, tables, and organized sections

Filters:
- artifact_types: List of types to include (e.g., ["security_finding", "diagram"])
- date_from: Start date filter (YYYY-MM-DD)
- date_to: End date filter (YYYY-MM-DD)
- agent_type: Filter by creating agent (planner, coder, qa_reviewer, etc.)
- spec_id: Filter to a specific spec

Markdown options:
- include_content: Whether to include full artifact content (default: true)
- max_content_length: Max chars per artifact content, 0=unlimited (default: 2000)

If output_path is provided, saves to file and returns path.
If output_path is omitted, returns the content directly.`,
      inputSchema: {
        project_path: z.string().describe('Path to the project directory'),
        format: z.enum(['json', 'markdown', 'md']).describe('Export format: json or markdown'),
        output_path: z.string().describe('Optional path to save the export file').optional(),
        artifact_types: z.array(z.string()).describe('Filter by artifact types').optional(),
        date_from: z.string().describe('Start date filter (YYYY-MM-DD)').optional(),
        date_to: z.string().describe('End date filter (YYYY-MM-DD)').optional(),
        agent_type: z.string().describe('Filter by agent type (planner, coder, qa_reviewer, etc.)').optional(),
        spec_id: z.string().describe('Filter by spec ID').optional(),
        include_content: z.boolean().describe('Include full artifact content in markdown (default: true)').default(true).optional(),
        max_content_length: z.number().describe('Max content length per artifact in markdown (default: 2000, 0=unlimited)').default(2000).optional()
      }
    },
    async ({ project_path, format, output_path, artifact_types, date_from, date_to, agent_type, spec_id, include_content, max_content_length }) => {
      try {
        const params: Record<string, string> = {
          projectPath: project_path,
          format: format || 'json'
        };
        if (output_path) params.output_path = output_path;
        if (artifact_types && artifact_types.length > 0) params.artifact_types = JSON.stringify(artifact_types);
        if (date_from) params.date_from = date_from;
        if (date_to) params.date_to = date_to;
        if (agent_type) params.agent_type = agent_type;
        if (spec_id) params.spec_id = spec_id;
        if (include_content !== undefined) params.include_content = String(include_content);
        if (max_content_length !== undefined) params.max_content_length = String(max_content_length);

        const url = new URL(`${ELECTRON_API_URL}/artifacts/export`);
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, value);
        });

        const response = await fetch(url.toString());

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const data = await response.json();

        // Check if saved to file or content returned
        if (data.saved_to) {
          return {
            content: [{
              type: 'text',
              text: `Export completed successfully!

Format: ${format?.toUpperCase() || 'JSON'}
Saved to: ${data.saved_to}
Artifacts: ${data.artifact_count}
Total Value: $${(data.total_value || 0).toFixed(2)}`
            }],
            structuredContent: data
          };
        } else {
          // Return content directly
          const header = `=== Export (${data.artifact_count} artifacts, $${(data.total_value || 0).toFixed(2)}) ===\n\n`;
          return {
            content: [{
              type: 'text',
              text: header + (data.content || '')
            }],
            structuredContent: data
          };
        }
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error exporting artifacts: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // ============================================================================
  // TAG MANAGEMENT TOOLS
  // ============================================================================

  // Tool 20: Tag Artifact
  server.registerTool(
    'tag_artifact',
    {
      title: 'Tag Artifact',
      description: `Add or remove tags from an artifact.

Tags help organize and categorize artifacts for easy filtering and retrieval.
Tags are stored in lowercase and must be non-empty strings.

Actions:
- add: Add a tag to the artifact
- remove: Remove a tag from the artifact

Example usage:
  action: "add"
  artifact_id: "art_abc123def456"
  tag: "security"

Common tags: security, performance, architecture, bug, feature, documentation,
             refactoring, testing, critical, review-needed, approved`,
      inputSchema: {
        action: z.enum(['add', 'remove']).describe('Action to perform: add or remove'),
        artifact_id: z.string().describe('The artifact ID to tag'),
        tag: z.string().describe('The tag to add or remove'),
        project_path: z.string().describe('Path to the project directory')
      }
    },
    async ({ action, artifact_id, tag, project_path }) => {
      try {
        const params: Record<string, string> = {
          action,
          artifact_id,
          tag,
          projectPath: project_path
        };

        const url = new URL(`${ELECTRON_API_URL}/artifact/tag`);
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, value);
        });

        const response = await fetch(url.toString(), { method: 'POST' });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const data = await response.json();

        return {
          content: [{
            type: 'text',
            text: data.message || `Tag '${tag}' ${action === 'add' ? 'added to' : 'removed from'} artifact ${artifact_id}`
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error managing tag: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 21: Get Artifacts by Tag
  server.registerTool(
    'get_artifacts_by_tag',
    {
      title: 'Get Artifacts by Tag',
      description: `Get all artifacts that have a specific tag.

Returns a list of artifacts matching the specified tag.
Tags are case-insensitive.

Example:
  tag: "security"

Returns artifacts with that tag, including their full content.`,
      inputSchema: {
        tag: z.string().describe('The tag to filter by'),
        project_path: z.string().describe('Path to the project directory')
      }
    },
    async ({ tag, project_path }) => {
      try {
        const response = await fetch(
          `${ELECTRON_API_URL}/artifacts/by-tag/${encodeURIComponent(tag)}?projectPath=${encodeURIComponent(project_path)}`
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const data = await response.json();

        // Format text output
        const artifacts = data.artifacts || [];
        const lines = [`=== Artifacts with tag '${tag}' (${artifacts.length}) ===`, ''];

        for (const art of artifacts) {
          lines.push(`ID: ${art.id}`);
          lines.push(`  Type: ${art.type || 'unknown'}`);
          lines.push(`  Value: $${art.value_usd || 0}`);
          lines.push(`  Tags: ${(art.metadata?.tags || []).join(', ')}`);
          const preview = (art.content || '').substring(0, 50);
          lines.push(`  Preview: ${preview}${art.content?.length > 50 ? '...' : ''}`);
          lines.push('');
        }

        return {
          content: [{
            type: 'text',
            text: lines.join('\n')
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error getting artifacts by tag: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 22: List All Tags
  server.registerTool(
    'list_all_tags',
    {
      title: 'List All Tags',
      description: `List all unique tags used across all artifacts in the project.

Returns a sorted list of all tags that have been applied to any artifact.
Useful for discovering available tags for filtering.`,
      inputSchema: {
        project_path: z.string().describe('Path to the project directory')
      }
    },
    async ({ project_path }) => {
      try {
        const response = await fetch(
          `${ELECTRON_API_URL}/artifacts/tags?projectPath=${encodeURIComponent(project_path)}`
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const data = await response.json();
        const tags = data.tags || [];

        // Format text output
        const lines = [`=== All Tags (${tags.length}) ===`, ''];
        for (const tag of tags) {
          lines.push(`  - ${tag}`);
        }

        if (tags.length === 0) {
          lines.push('  No tags found. Use tag_artifact to add tags to artifacts.');
        }

        return {
          content: [{
            type: 'text',
            text: lines.join('\n')
          }],
          structuredContent: data
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error listing tags: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // ============================================================================
  // CLEANUP AND RETENTION TOOLS
  // ============================================================================

  // Tool 23: Cleanup Artifacts
  server.registerTool(
    'cleanup_artifacts',
    {
      title: 'Cleanup Artifacts',
      description: `Clean up old artifacts by age or type.

IMPORTANT: By default this runs in dry_run mode (preview only).
Set dry_run=false to actually delete artifacts.

Cleanup modes:
1. By age: Delete artifacts older than N days
   - days: Number of days (default: 30)
   - dry_run: Preview only (default: true)

2. By type: Keep only the N most recent artifacts of a specific type
   - artifact_type: The type to clean up (e.g., "diagram", "code_example")
   - keep_latest: Number to keep (default: 10)
   - dry_run: Preview only (default: true)

Safety:
- ALWAYS runs in dry_run mode by default
- Review the preview before running with dry_run=false
- Consider using archive_artifacts instead of deleting`,
      inputSchema: {
        project_path: z.string().describe('Path to the project directory'),
        days: z.number().min(1).describe('Delete artifacts older than this many days (default: 30)').default(30).optional(),
        artifact_type: z.string().describe('Clean up specific artifact type (e.g., "diagram", "code_example")').optional(),
        keep_latest: z.number().min(0).describe('When cleaning by type, keep this many most recent (default: 10)').default(10).optional(),
        dry_run: z.boolean().describe('Preview only without deleting (default: true)').default(true).optional()
      }
    },
    async ({ project_path, days, artifact_type, keep_latest, dry_run }) => {
      try {
        const actualDryRun = dry_run !== false;  // Default to true for safety
        const actualDays = days || 30;
        const actualKeepLatest = keep_latest || 10;

        const params = new URLSearchParams({
          projectPath: project_path,
          dryRun: String(actualDryRun)
        });

        if (artifact_type) {
          params.append('artifactType', artifact_type);
          params.append('keepLatest', String(actualKeepLatest));
        } else {
          params.append('days', String(actualDays));
        }

        const response = await fetch(
          `${ELECTRON_API_URL}/artifacts/cleanup?${params.toString()}`,
          { method: 'POST' }
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const result = await response.json();

        // Format response based on cleanup type
        let responseText: string;

        if (artifact_type) {
          const actionWord = actualDryRun ? "Would delete" : "Deleted";
          responseText = `=== Cleanup by Type: ${artifact_type} ===

Mode: ${actualDryRun ? "DRY RUN (preview only)" : "ACTUAL DELETION"}
Type: ${artifact_type}
Keep Latest: ${actualKeepLatest}

${actionWord}: ${result.deleted_count || 0} artifacts
Kept: ${result.kept_count || 0} artifacts

${actualDryRun ? "IDs that would be deleted:" : "Deleted IDs:"}
${(result.deleted_ids || []).slice(0, 20).map((id: string) => `  - ${id}`).join('\n') || '  (none)'}
${(result.deleted_ids || []).length > 20 ? `  ... and ${result.deleted_ids.length - 20} more` : ''}`;
        } else {
          const actionWord = actualDryRun ? "Would delete" : "Deleted";
          const freedKb = (result.freed_bytes || 0) / 1024;
          responseText = `=== Cleanup by Age ===

Mode: ${actualDryRun ? "DRY RUN (preview only)" : "ACTUAL DELETION"}
Cutoff: ${actualDays} days old

${actionWord}: ${result.deleted_count || 0} artifacts
${actionWord.replace('delete', 'free')}: ${freedKb.toFixed(2)} KB

${actualDryRun ? "IDs that would be deleted:" : "Deleted IDs:"}
${(result.deleted_ids || []).slice(0, 20).map((id: string) => `  - ${id}`).join('\n') || '  (none)'}
${(result.deleted_ids || []).length > 20 ? `  ... and ${result.deleted_ids.length - 20} more` : ''}`;
        }

        if (actualDryRun && (result.deleted_count || 0) > 0) {
          responseText += '\n\nTo actually delete, run again with dry_run=false';
        }

        return {
          content: [{ type: 'text', text: responseText }],
          structuredContent: result
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error cleaning up artifacts: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 24: Archive Artifacts
  server.registerTool(
    'archive_artifacts',
    {
      title: 'Archive Artifacts',
      description: `Archive specific artifacts.

Archived artifacts are MOVED (not deleted) to .auto-claude/artifacts/archive/
This preserves them while keeping the main storage clean.

Use this instead of deleting when you want to:
- Keep a backup of old artifacts
- Clean up without permanent deletion
- Be able to restore artifacts later

Returns count of successfully archived artifacts and any failures.`,
      inputSchema: {
        project_path: z.string().describe('Path to the project directory'),
        artifact_ids: z.array(z.string()).describe('List of artifact IDs to archive')
      }
    },
    async ({ project_path, artifact_ids }) => {
      try {
        if (!artifact_ids || artifact_ids.length === 0) {
          return {
            content: [{ type: 'text', text: 'Error: artifact_ids list is required and cannot be empty.' }],
            isError: true
          };
        }

        const response = await fetch(
          `${ELECTRON_API_URL}/artifacts/archive`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              projectPath: project_path,
              artifactIds: artifact_ids
            })
          }
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const result = await response.json();

        const responseText = `=== Archive Results ===

Archived: ${result.archived_count || 0} artifacts
Failed: ${result.failed_count || 0} artifacts

Archived IDs:
${(result.archived_ids || []).map((id: string) => `  - ${id}`).join('\n') || '  (none)'}
${(result.failed_ids || []).length > 0 ? `\nFailed IDs:\n${result.failed_ids.map((id: string) => `  - ${id}`).join('\n')}` : ''}`;

        return {
          content: [{ type: 'text', text: responseText }],
          structuredContent: result
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error archiving artifacts: ${errorMsg}` }],
          isError: true
        };
      }
    }
  );

  // Tool 25: Get Cleanup Preview
  server.registerTool(
    'get_cleanup_preview',
    {
      title: 'Get Cleanup Preview',
      description: `Preview what would be deleted by cleanup.

Shows a detailed preview of artifacts that would be deleted if you run
cleanup_artifacts with dry_run=false.

Returns:
- Number of artifacts that would be deleted
- Total bytes that would be freed
- List of artifact summaries (ID, type, date, value, size)

Use this to review before running actual cleanup.`,
      inputSchema: {
        project_path: z.string().describe('Path to the project directory'),
        days: z.number().min(1).describe('Preview artifacts older than this many days (default: 30)').default(30).optional()
      }
    },
    async ({ project_path, days }) => {
      try {
        const actualDays = days || 30;
        const response = await fetch(
          `${ELECTRON_API_URL}/artifacts/cleanup/preview?projectPath=${encodeURIComponent(project_path)}&days=${actualDays}`
        );

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || response.statusText);
        }

        const result = await response.json();
        const freedKb = (result.total_bytes || 0) / 1024;

        let responseText = `=== Cleanup Preview ===

Cutoff: ${actualDays} days (before ${result.cutoff_date || 'N/A'})
Would Delete: ${result.would_delete || 0} artifacts
Would Free: ${freedKb.toFixed(2)} KB

Artifacts to delete (oldest first):`;

        for (const art of (result.artifacts || []).slice(0, 30)) {
          const sizeKb = (art.size_bytes || 0) / 1024;
          responseText += `\n  ${art.id}`;
          responseText += `\n    Type: ${art.type} | Date: ${art.date} | Value: $${art.value_usd || 0} | Size: ${sizeKb.toFixed(1)}KB`;
          if (art.spec_id) {
            responseText += ` | Spec: ${art.spec_id}`;
          }
        }

        if ((result.artifacts || []).length > 30) {
          responseText += `\n\n  ... and ${result.artifacts.length - 30} more artifacts`;
        }

        if ((result.would_delete || 0) > 0) {
          responseText += '\n\nTo delete these, run cleanup_artifacts with dry_run=false';
        }

        return {
          content: [{ type: 'text', text: responseText }],
          structuredContent: result
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: 'text', text: `Error getting cleanup preview: ${errorMsg}` }],
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

### Artifact Storage
- \`get_artifact\` - Get full artifact by ID
- \`list_artifacts\` - List artifacts with filters
- \`get_artifacts_by_trace\` - Get artifacts by trace ID
- \`get_artifact_content\` - Get artifact content only
- \`aggregate_artifacts_by_agent\` - Get artifacts grouped by agent
- \`get_artifact_statistics\` - Get comprehensive artifact statistics
- \`search_artifacts\` - Search artifacts by content, description, and type

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

  console.error('[Auto-Claude Tools STDIO] Server started with 25 tools, 6 prompts, 6 resources');
}

// Run server
main().catch((error) => {
  console.error('[Auto-Claude Tools STDIO] Fatal error:', error);
  process.exit(1);
});
