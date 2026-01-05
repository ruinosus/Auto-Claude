/**
 * Auto-Claude Tools MCP Server - HTTP Transport
 *
 * This is Option B: In-process server that runs within Electron main process.
 * Uses HTTP transport on localhost for communication.
 * Has DIRECT access to Electron IPC handlers and data.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import express from 'express';
import type { Request as ExpressRequest, Response as ExpressResponse } from 'express-serve-static-core';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { randomUUID } from 'node:crypto';
import { z } from 'zod';
import { ipcMain } from 'electron';
import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// ARTIFACT STORAGE HELPERS (same as in electron-api-bridge.ts)
// ============================================================================

interface LocalArtifact {
  id: string;
  type: string;
  format?: string;
  content: string;
  value_usd?: number;
  description?: string;
  created_at?: string;
  trace_id?: string;
  spec_id?: string;
  project_id?: string;
  agent_type?: string;
  metadata?: {
    tags?: string[];
    [key: string]: unknown;
  };
  // Index signature for MCP SDK structuredContent compatibility
  [key: string]: unknown;
}

function getArtifactsDir(projectPath: string): string {
  return path.join(projectPath, '.auto-claude', 'artifacts');
}

function loadArtifactIndex(projectPath: string): Record<string, any> {
  const indexPath = path.join(getArtifactsDir(projectPath), 'index.json');
  if (fs.existsSync(indexPath)) {
    try {
      return JSON.parse(fs.readFileSync(indexPath, 'utf-8'));
    } catch {
      return {};
    }
  }
  return {};
}

function loadArtifactDirect(projectPath: string, artifactId: string): LocalArtifact | null {
  const artifactsDir = getArtifactsDir(projectPath);
  const index = loadArtifactIndex(projectPath);

  if (index[artifactId]?.path) {
    const fullPath = path.join(projectPath, index[artifactId].path);
    if (fs.existsSync(fullPath)) {
      try {
        return JSON.parse(fs.readFileSync(fullPath, 'utf-8'));
      } catch {
        return null;
      }
    }
  }

  // Fallback: search date folders
  if (fs.existsSync(artifactsDir)) {
    const folders = fs.readdirSync(artifactsDir).filter(f =>
      fs.statSync(path.join(artifactsDir, f)).isDirectory()
    );
    for (const folder of folders) {
      const artifactPath = path.join(artifactsDir, folder, `${artifactId}.json`);
      if (fs.existsSync(artifactPath)) {
        try {
          return JSON.parse(fs.readFileSync(artifactPath, 'utf-8'));
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}

function listArtifactsDirect(
  projectPath: string,
  filters?: { spec_id?: string; trace_id?: string; type?: string; limit?: number }
): LocalArtifact[] {
  const artifactsDir = getArtifactsDir(projectPath);
  const artifacts: LocalArtifact[] = [];

  if (!fs.existsSync(artifactsDir)) return artifacts;

  const folders = fs.readdirSync(artifactsDir).filter(f =>
    fs.statSync(path.join(artifactsDir, f)).isDirectory()
  );

  for (const folder of folders) {
    const folderPath = path.join(artifactsDir, folder);
    const files = fs.readdirSync(folderPath).filter(f => f.endsWith('.json'));

    for (const file of files) {
      try {
        const artifact = JSON.parse(fs.readFileSync(path.join(folderPath, file), 'utf-8'));
        if (filters?.spec_id && artifact.spec_id !== filters.spec_id) continue;
        if (filters?.trace_id && artifact.trace_id !== filters.trace_id) continue;
        if (filters?.type && artifact.type !== filters.type) continue;
        artifacts.push(artifact);
        if (filters?.limit && artifacts.length >= filters.limit) return artifacts;
      } catch { /* skip */ }
    }
  }
  return artifacts;
}

const PORT = 9823; // Fixed port for auto-claude-tools MCP server

/**
 * Access Electron IPC handlers directly
 */
async function getFromElectron(channel: string, ...args: any[]): Promise<any> {
  // Simulate IPC call by directly invoking handlers
  // In real implementation, you'd import the actual handler functions
  return new Promise((resolve, reject) => {
    // This is a simplified version - in production you'd use the actual IPC mechanism
    const handlers = (ipcMain as any)._events;
    const handler = handlers[channel];

    if (!handler) {
      reject(new Error(`No IPC handler found for channel: ${channel}`));
      return;
    }

    // Call handler and get result
    try {
      const result = handler({ sender: { send: () => {} } }, ...args);
      if (result instanceof Promise) {
        result.then(resolve).catch(reject);
      } else {
        resolve(result);
      }
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * Create MCP server instance
 */
export function createAutoClaudeToolsServer(): McpServer {
  const server = new McpServer({
    name: 'auto-claude-tools-http',
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
        // Direct access to Electron data - no HTTP bridge needed!
        // In production, you'd call actual task manager functions
        const mockData = {
          specId,
          status: 'running' as const,
          phase: 'implementation',
          progress: 65,
          currentTask: 'Implementing feature X',
          startedAt: new Date().toISOString()
        };

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(mockData, null, 2)
          }],
          structuredContent: mockData
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
        // Direct access to project data
        const mockData = {
          projectPath: projectPath || '/path/to/project',
          projectName: 'Auto-Claude',
          techStack: ['TypeScript', 'React', 'Electron', 'Python'],
          recentSpecs: [
            { id: '001', name: 'MCP Integration', status: 'completed' },
            { id: '002', name: 'Skills Module', status: 'running' }
          ],
          codebaseStats: {
            totalFiles: 156,
            totalLines: 12450,
            languages: {
              TypeScript: 8500,
              Python: 3200,
              JSON: 750
            }
          }
        };

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(mockData, null, 2)
          }],
          structuredContent: mockData
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
        // Direct access to search functionality
        const mockData = {
          query,
          totalMatches: 5,
          results: [
            {
              file: 'src/components/MCPToolsList.tsx',
              line: 42,
              column: 10,
              match: query,
              context: `const result = await ${query}();`
            },
            {
              file: 'src/main/mcp-manager.ts',
              line: 156,
              column: 5,
              match: query,
              context: `// Using ${query} for MCP integration`
            }
          ]
        };

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(mockData, null, 2)
          }],
          structuredContent: mockData
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

  // Tool 4: Get Artifact
  server.registerTool(
    'get_artifact',
    {
      title: 'Get Artifact',
      description: 'Get a single artifact by ID with FULL content from local storage. Artifacts contain AI-generated outputs like code, reviews, plans, and insights.',
      inputSchema: {
        artifact_id: z.string().describe('The artifact ID (e.g., "art_abc123def456")'),
        project_path: z.string().describe('Path to the project directory')
      }
    },
    async ({ artifact_id, project_path }) => {
      try {
        const artifact = loadArtifactDirect(project_path, artifact_id);
        if (!artifact) {
          return {
            content: [{
              type: 'text',
              text: `Artifact not found: ${artifact_id}`
            }],
            isError: true
          };
        }
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
          content: [{
            type: 'text',
            text: `Error fetching artifact: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 5: List Artifacts
  server.registerTool(
    'list_artifacts',
    {
      title: 'List Artifacts',
      description: 'List all artifacts from local storage with optional filtering. Returns full content for each artifact.',
      inputSchema: {
        project_path: z.string().describe('Path to the project directory'),
        spec_id: z.string().describe('Filter by spec ID').optional(),
        trace_id: z.string().describe('Filter by Langfuse trace ID').optional(),
        type: z.string().describe('Filter by artifact type (e.g., "code_implementation", "qa_finding", "insight")').optional(),
        limit: z.number().min(1).max(100).describe('Maximum number of artifacts to return').default(50)
      }
    },
    async ({ project_path, spec_id, trace_id, type, limit }) => {
      try {
        const artifacts = listArtifactsDirect(project_path, { spec_id, trace_id, type, limit });
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              count: artifacts.length,
              artifacts
            }, null, 2)
          }],
          structuredContent: { count: artifacts.length, artifacts }
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error listing artifacts: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 6: Get Artifacts by Trace
  server.registerTool(
    'get_artifacts_by_trace',
    {
      title: 'Get Artifacts by Trace',
      description: 'Get all artifacts associated with a specific Langfuse trace ID. Useful for seeing all outputs from a single agent session.',
      inputSchema: {
        project_path: z.string().describe('Path to the project directory'),
        trace_id: z.string().describe('Langfuse trace ID to filter by')
      }
    },
    async ({ project_path, trace_id }) => {
      try {
        const artifacts = listArtifactsDirect(project_path, { trace_id });
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              trace_id,
              count: artifacts.length,
              artifacts
            }, null, 2)
          }],
          structuredContent: { trace_id, count: artifacts.length, artifacts }
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error fetching artifacts by trace: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 7: Get Artifact Content
  server.registerTool(
    'get_artifact_content',
    {
      title: 'Get Artifact Content',
      description: 'Get only the content of an artifact without metadata. Useful for directly accessing code, reviews, or other generated content.',
      inputSchema: {
        artifact_id: z.string().describe('The artifact ID'),
        project_path: z.string().describe('Path to the project directory')
      }
    },
    async ({ artifact_id, project_path }) => {
      try {
        const artifact = loadArtifactDirect(project_path, artifact_id);
        if (!artifact) {
          return {
            content: [{
              type: 'text',
              text: `Artifact not found: ${artifact_id}`
            }],
            isError: true
          };
        }
        return {
          content: [{
            type: 'text',
            text: artifact.content
          }]
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error fetching artifact content: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 8: Aggregate Artifacts by Agent
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
        const artifacts = listArtifactsDirect(project_path, {});

        // Aggregate by agent_type
        const byAgent: Record<string, { count: number; total_value_usd: number; types: Set<string> }> = {};

        for (const artifact of artifacts) {
          // Apply date filtering
          const artDate = artifact.created_at?.split('T')[0] || '';
          if (date_from && artDate < date_from) continue;
          if (date_to && artDate > date_to) continue;

          const agentType = artifact.agent_type || 'unknown';
          const artifactType = artifact.type || 'unknown';
          const valueUsd = artifact.value_usd || 0;

          if (!byAgent[agentType]) {
            byAgent[agentType] = {
              count: 0,
              total_value_usd: 0,
              types: new Set()
            };
          }

          byAgent[agentType].count += 1;
          byAgent[agentType].total_value_usd += valueUsd;
          byAgent[agentType].types.add(artifactType);
        }

        // Convert Sets to arrays for JSON serialization
        const result: Record<string, { count: number; total_value_usd: number; types: string[] }> = {};
        for (const [agent, data] of Object.entries(byAgent)) {
          result[agent] = {
            count: data.count,
            total_value_usd: data.total_value_usd,
            types: Array.from(data.types).sort()
          };
        }

        // Calculate summary
        const totalCount = Object.values(result).reduce((sum, d) => sum + d.count, 0);
        const totalValue = Object.values(result).reduce((sum, d) => sum + d.total_value_usd, 0);

        const response = {
          by_agent: result,
          summary: {
            total_count: totalCount,
            total_value_usd: totalValue,
            agent_count: Object.keys(result).length
          }
        };

        return {
          content: [{
            type: 'text',
            text: JSON.stringify(response, null, 2)
          }],
          structuredContent: response
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error aggregating artifacts by agent: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 9: Get Artifact Statistics
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
        const artifacts = listArtifactsDirect(project_path, {});

        // Calculate dates for period filtering
        const now = new Date();
        const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

        // Map artifact types to tabs
        const TYPE_TO_TAB: Record<string, string> = {
          diagram: 'techlead',
          code_example: 'dev',
          refactoring: 'dev',
          bug_fix: 'dev',
          test_case: 'dev',
          security_finding: 'ops',
          performance_insight: 'ops',
          architecture_insight: 'techlead',
          api_design: 'techlead',
          documentation: 'techlead',
          recommendation: 'business',
          cost_analysis: 'business',
          priority_assessment: 'business',
        };

        // Initialize counters
        let totalValue = 0;
        const byType: Record<string, number> = {};
        const byTab: Record<string, number> = { dev: 0, techlead: 0, ops: 0, business: 0 };
        const valueByType: Record<string, number> = {};
        const valueByTab: Record<string, number> = { dev: 0, techlead: 0, ops: 0, business: 0 };
        const byPeriod = { last_7_days: 0, last_30_days: 0, all_time: artifacts.length };
        const artifactsWithValue: Array<{ id: string; type: string; value_usd: number; date: string }> = [];

        for (const artifact of artifacts) {
          const artType = artifact.type || 'unknown';
          const valueUsd = artifact.value_usd || 0;
          const artDate = artifact.created_at?.split('T')[0] || '';

          // Accumulate total value
          totalValue += valueUsd;

          // Count by type
          byType[artType] = (byType[artType] || 0) + 1;
          valueByType[artType] = (valueByType[artType] || 0) + valueUsd;

          // Count by tab
          const tab = TYPE_TO_TAB[artType] || 'dev';
          byTab[tab] = (byTab[tab] || 0) + 1;
          valueByTab[tab] = (valueByTab[tab] || 0) + valueUsd;

          // Count by period
          if (artDate >= sevenDaysAgo) {
            byPeriod.last_7_days += 1;
          }
          if (artDate >= thirtyDaysAgo) {
            byPeriod.last_30_days += 1;
          }

          // Track for top valuable
          if (valueUsd > 0) {
            artifactsWithValue.push({ id: artifact.id, type: artType, value_usd: valueUsd, date: artDate });
          }
        }

        // Sort by value descending and take top 5
        artifactsWithValue.sort((a, b) => b.value_usd - a.value_usd);
        const topValuable = artifactsWithValue.slice(0, 5);

        const stats = {
          total_count: artifacts.length,
          total_value_usd: totalValue,
          by_type: byType,
          by_tab: byTab,
          by_period: byPeriod,
          top_valuable: topValuable,
          value_by_type: valueByType,
          value_by_tab: valueByTab,
          last_updated: new Date().toISOString(),
        };

        // Format text output
        const lines = ['=== Artifact Statistics ===', ''];

        lines.push('## Overview');
        lines.push(`  Total Artifacts: ${stats.total_count}`);
        lines.push(`  Total Value: $${stats.total_value_usd.toFixed(2)}`);
        lines.push('');

        lines.push('## By Time Period');
        lines.push(`  Last 7 Days: ${byPeriod.last_7_days} artifacts`);
        lines.push(`  Last 30 Days: ${byPeriod.last_30_days} artifacts`);
        lines.push(`  All Time: ${byPeriod.all_time} artifacts`);
        lines.push('');

        lines.push('## By Dashboard Tab');
        const tabNames: Record<string, string> = {
          dev: 'Developer',
          techlead: 'Tech Lead',
          ops: 'Operations',
          business: 'Business'
        };
        for (const tab of ['dev', 'techlead', 'ops', 'business']) {
          const count = byTab[tab] || 0;
          const value = valueByTab[tab] || 0;
          lines.push(`  ${tabNames[tab]}: ${count} artifacts ($${value.toFixed(2)})`);
        }
        lines.push('');

        lines.push('## By Artifact Type (Top 10)');
        const sortedTypes = Object.entries(byType)
          .sort((a, b) => (valueByType[b[0]] || 0) - (valueByType[a[0]] || 0))
          .slice(0, 10);
        for (const [artType, count] of sortedTypes) {
          const value = valueByType[artType] || 0;
          lines.push(`  ${artType}: ${count} ($${value.toFixed(2)})`);
        }
        lines.push('');

        lines.push('## Top 5 Most Valuable');
        for (const [i, art] of topValuable.entries()) {
          lines.push(`  ${i + 1}. ${art.type} - $${art.value_usd.toFixed(2)}`);
          lines.push(`     ID: ${art.id}, Date: ${art.date}`);
        }
        if (!topValuable.length) {
          lines.push('  No artifacts with value found.');
        }

        return {
          content: [{
            type: 'text',
            text: lines.join('\n')
          }],
          structuredContent: stats
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error getting artifact statistics: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 10: Search Artifacts
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
        if (!query || query.trim().length < 1) {
          return {
            content: [{
              type: 'text',
              text: 'Error: Search query is required.'
            }],
            isError: true
          };
        }

        const searchQuery = query.trim().toLowerCase();
        const maxResults = limit || 50;
        const PREVIEW_LENGTH = 200;

        // Load all artifacts
        let artifacts = listArtifactsDirect(project_path, { spec_id, limit: 10000 });

        // Apply type filter if provided
        if (artifact_types && artifact_types.length > 0) {
          artifacts = artifacts.filter(a => artifact_types.includes(a.type || ''));
        }

        // Helper function to highlight match
        const highlightMatch = (text: string, query: string, contextChars: number = 30): string => {
          if (!text || !query) return '';

          const textLower = text.toLowerCase();
          const queryLower = query.toLowerCase();

          const matchIdx = textLower.indexOf(queryLower);
          if (matchIdx === -1) return '';

          const start = Math.max(0, matchIdx - contextChars);
          const end = Math.min(text.length, matchIdx + query.length + contextChars);

          const snippet = text.substring(start, end);
          const prefix = start > 0 ? '...' : '';
          const suffix = end < text.length ? '...' : '';

          const matchStartInSnippet = matchIdx - start;
          const matchEndInSnippet = matchStartInSnippet + query.length;

          const highlighted =
            snippet.substring(0, matchStartInSnippet) +
            '**' + snippet.substring(matchStartInSnippet, matchEndInSnippet) + '**' +
            snippet.substring(matchEndInSnippet);

          return prefix + highlighted + suffix;
        };

        // Helper function to calculate relevance score
        const calculateRelevance = (
          artifact: LocalArtifact,
          contentMatch: boolean,
          descriptionMatch: boolean,
          typeMatch: boolean
        ): number => {
          let score = 0;

          if (typeMatch) score += 100;
          if (descriptionMatch) {
            score += 50;
            if (artifact.description?.toLowerCase().startsWith(searchQuery)) {
              score += 25;
            }
          }
          if (contentMatch) {
            score += 25;
            const content = artifact.content || '';
            const contentLower = content.toLowerCase();
            const matchIdx = contentLower.indexOf(searchQuery);
            if (matchIdx !== -1 && matchIdx < 500) {
              score += 25 - Math.floor(matchIdx / 20);
            }
            // Multiple occurrences
            const occurrences = (contentLower.match(new RegExp(searchQuery, 'g')) || []).length;
            score += Math.min(occurrences * 5, 25);
          }

          // Recency bonus
          const today = new Date().toISOString().split('T')[0];
          if (artifact.created_at?.startsWith(today)) {
            score += 10;
          }

          return score;
        };

        // Search and score artifacts
        const results: Array<{
          id: string;
          type: string;
          format?: string;
          description: string;
          value_usd: number;
          created_at: string;
          spec_id?: string;
          tab?: string;
          preview: string;
          match_highlight: string;
          match_locations: string[];
          relevance_score: number;
        }> = [];

        for (const artifact of artifacts) {
          const content = (artifact.content || '').toLowerCase();
          const description = (artifact.description || '').toLowerCase();
          const artType = (artifact.type || '').toLowerCase();

          const contentMatch = content.includes(searchQuery);
          const descriptionMatch = description.includes(searchQuery);
          const typeMatch = artType.includes(searchQuery);

          if (!contentMatch && !descriptionMatch && !typeMatch) {
            continue;
          }

          const matchLocations: string[] = [];
          if (contentMatch) matchLocations.push('content');
          if (descriptionMatch) matchLocations.push('description');
          if (typeMatch) matchLocations.push('type');

          let matchHighlight = '';
          if (contentMatch) {
            matchHighlight = highlightMatch(artifact.content || '', query);
          } else if (descriptionMatch) {
            matchHighlight = highlightMatch(artifact.description || '', query);
          } else if (typeMatch) {
            matchHighlight = `Type: **${artifact.type}**`;
          }

          const preview = (artifact.content || '').substring(0, PREVIEW_LENGTH) +
            ((artifact.content || '').length > PREVIEW_LENGTH ? '...' : '');

          const relevanceScore = calculateRelevance(artifact, contentMatch, descriptionMatch, typeMatch);

          // Infer tab from type
          const TYPE_TO_TAB: Record<string, string> = {
            diagram: 'techlead',
            code_example: 'dev',
            refactoring: 'dev',
            bug_fix: 'dev',
            test_case: 'dev',
            security_finding: 'ops',
            performance_insight: 'ops',
            architecture_insight: 'techlead',
            api_design: 'techlead',
            documentation: 'techlead',
            recommendation: 'business',
            cost_analysis: 'business',
            priority_assessment: 'business',
          };

          results.push({
            id: artifact.id,
            type: artifact.type || 'unknown',
            format: artifact.format,
            description: artifact.description || '',
            value_usd: artifact.value_usd || 0,
            created_at: artifact.created_at || '',
            spec_id: artifact.spec_id,
            tab: TYPE_TO_TAB[artifact.type || ''] || 'dev',
            preview,
            match_highlight: matchHighlight,
            match_locations: matchLocations,
            relevance_score: relevanceScore,
          });
        }

        // Sort by relevance score (descending)
        results.sort((a, b) => b.relevance_score - a.relevance_score);

        // Apply limit
        const limitedResults = results.slice(0, maxResults);

        // Format text output
        const lines = [`=== Search Results for '${query}' ===`, ''];
        lines.push(`Found ${limitedResults.length} matching artifact(s)`);
        lines.push('');

        const tabNames: Record<string, string> = {
          dev: 'Developer',
          techlead: 'Tech Lead',
          ops: 'Operations',
          business: 'Business'
        };

        for (const [i, result] of limitedResults.entries()) {
          lines.push(`## ${i + 1}. ${result.type} ($${result.value_usd})`);
          lines.push(`   ID: ${result.id}`);
          if (result.description) {
            const desc = result.description.length > 100
              ? result.description.substring(0, 100) + '...'
              : result.description;
            lines.push(`   Description: ${desc}`);
          }
          lines.push(`   Tab: ${tabNames[result.tab || ''] || result.tab || 'N/A'}`);
          lines.push(`   Created: ${(result.created_at || 'N/A').substring(0, 10)}`);
          lines.push(`   Matched in: ${result.match_locations.join(', ')}`);
          if (result.match_highlight) {
            lines.push(`   Match: ${result.match_highlight}`);
          }
          lines.push(`   Relevance: ${result.relevance_score}`);
          lines.push('');
        }

        return {
          content: [{
            type: 'text',
            text: lines.join('\n')
          }],
          structuredContent: {
            query,
            total_results: limitedResults.length,
            results: limitedResults
          }
        };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error searching artifacts: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // Tool 11: Export Artifacts
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
        // Load artifacts with filters
        let artifacts = listArtifactsDirect(project_path, { spec_id, limit: 10000 });

        // Apply type filter
        if (artifact_types && artifact_types.length > 0) {
          artifacts = artifacts.filter(a => artifact_types.includes(a.type || ''));
        }

        // Apply date filters
        if (date_from) {
          artifacts = artifacts.filter(a => (a.created_at?.split('T')[0] || '') >= date_from);
        }
        if (date_to) {
          artifacts = artifacts.filter(a => (a.created_at?.split('T')[0] || '') <= date_to);
        }

        // Apply agent_type filter
        if (agent_type) {
          artifacts = artifacts.filter(a => a.agent_type === agent_type);
        }

        // Calculate stats
        const totalValue = artifacts.reduce((sum, a) => sum + (a.value_usd || 0), 0);

        // Build type/agent/tab breakdowns
        const byType: Record<string, { count: number; value: number }> = {};
        const byAgent: Record<string, { count: number; value: number }> = {};
        const byTab: Record<string, { count: number; value: number }> = {};

        const TYPE_TO_TAB: Record<string, string> = {
          diagram: 'techlead',
          code_example: 'dev',
          refactoring: 'dev',
          bug_fix: 'dev',
          test_case: 'dev',
          security_finding: 'ops',
          performance_insight: 'ops',
          architecture_insight: 'techlead',
          api_design: 'techlead',
          documentation: 'techlead',
          recommendation: 'business',
          cost_analysis: 'business',
          priority_assessment: 'business',
        };

        for (const art of artifacts) {
          const artType = art.type || 'unknown';
          const artAgent = art.agent_type || 'unknown';
          const tab = TYPE_TO_TAB[artType] || 'other';
          const value = art.value_usd || 0;

          if (!byType[artType]) byType[artType] = { count: 0, value: 0 };
          byType[artType].count += 1;
          byType[artType].value += value;

          if (!byAgent[artAgent]) byAgent[artAgent] = { count: 0, value: 0 };
          byAgent[artAgent].count += 1;
          byAgent[artAgent].value += value;

          if (!byTab[tab]) byTab[tab] = { count: 0, value: 0 };
          byTab[tab].count += 1;
          byTab[tab].value += value;
        }

        const exportFormat = format || 'json';
        const generatedDate = new Date().toISOString().split('T')[0];

        if (exportFormat === 'json') {
          // Build JSON export
          const exportData = {
            export_info: {
              generated_at: new Date().toISOString(),
              project: path.basename(project_path),
              filters: {
                artifact_types: artifact_types || null,
                date_from: date_from || null,
                date_to: date_to || null,
                agent_type: agent_type || null,
                spec_id: spec_id || null,
              },
            },
            summary: {
              total_artifacts: artifacts.length,
              total_value_usd: totalValue,
              by_type: byType,
              by_agent: byAgent,
              by_tab: byTab,
            },
            artifacts: artifacts,
          };

          if (output_path) {
            // Save to file
            const dir = path.dirname(output_path);
            if (!fs.existsSync(dir)) {
              fs.mkdirSync(dir, { recursive: true });
            }
            fs.writeFileSync(output_path, JSON.stringify(exportData, null, 2), 'utf-8');

            return {
              content: [{
                type: 'text',
                text: `Export completed successfully!

Format: JSON
Saved to: ${output_path}
Artifacts: ${artifacts.length}
Total Value: $${totalValue.toFixed(2)}`
              }],
              structuredContent: { saved_to: output_path, artifact_count: artifacts.length, total_value: totalValue }
            };
          } else {
            const content = JSON.stringify(exportData, null, 2);
            const header = `=== Export (${artifacts.length} artifacts, $${totalValue.toFixed(2)}) ===\n\n`;
            return {
              content: [{
                type: 'text',
                text: header + content
              }],
              structuredContent: { content, artifact_count: artifacts.length, total_value: totalValue }
            };
          }
        } else {
          // Build Markdown export
          const ARTIFACT_TYPE_EMOJIS: Record<string, string> = {
            security_finding: '🔒',
            diagram: '📊',
            code_example: '💻',
            refactoring: '🔧',
            bug_fix: '🐛',
            test_case: '🧪',
            performance_insight: '⚡',
            architecture_insight: '🏗️',
            api_design: '🔌',
            documentation: '📝',
            recommendation: '💡',
            cost_analysis: '💰',
            priority_assessment: '📋',
            qa_finding: '✅',
            insight: '🔍',
            unknown: '📦',
          };

          const tabNames: Record<string, string> = {
            ops: 'Operations',
            techlead: 'Tech Lead',
            dev: 'Developer',
            business: 'Business',
            other: 'Other',
          };

          const lines: string[] = [
            '# Artifacts Export',
            '',
            `Generated: ${generatedDate}`,
            '',
          ];

          // Filters info
          const filtersApplied: string[] = [];
          if (artifact_types?.length) filtersApplied.push(`Types: ${artifact_types.join(', ')}`);
          if (date_from || date_to) filtersApplied.push(`Date range: ${date_from || 'start'} to ${date_to || 'now'}`);
          if (agent_type) filtersApplied.push(`Agent: ${agent_type}`);
          if (spec_id) filtersApplied.push(`Spec: ${spec_id}`);

          if (filtersApplied.length) {
            lines.push('**Filters:**');
            for (const f of filtersApplied) {
              lines.push(`- ${f}`);
            }
            lines.push('');
          }

          // Summary
          lines.push('## Summary');
          lines.push(`- **Total:** ${artifacts.length} artifacts`);
          lines.push(`- **Value:** $${totalValue.toFixed(2)}`);
          lines.push('');

          // Type breakdown table
          if (Object.keys(byType).length > 0) {
            lines.push('### By Type');
            lines.push('');
            lines.push('| Type | Count | Value |');
            lines.push('|------|-------|-------|');
            for (const [artType, stats] of Object.entries(byType).sort((a, b) => b[1].value - a[1].value)) {
              const emoji = ARTIFACT_TYPE_EMOJIS[artType] || '📦';
              const typeDisplay = artType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
              lines.push(`| ${emoji} ${typeDisplay} | ${stats.count} | $${stats.value.toFixed(2)} |`);
            }
            lines.push('');
          }

          // Group artifacts by tab
          const artifactsByTab: Record<string, LocalArtifact[]> = {};
          for (const art of artifacts) {
            const tab = TYPE_TO_TAB[art.type || ''] || 'other';
            if (!artifactsByTab[tab]) artifactsByTab[tab] = [];
            artifactsByTab[tab].push(art);
          }

          lines.push('## Artifacts');
          lines.push('');

          const tabOrder = ['ops', 'techlead', 'dev', 'business', 'other'];
          for (const tab of tabOrder) {
            if (!artifactsByTab[tab]) continue;
            const tabArts = artifactsByTab[tab];

            lines.push(`### ${tabNames[tab] || tab} (${tabArts.length} artifacts)`);
            lines.push('');

            for (const art of tabArts) {
              const artType = art.type || 'unknown';
              const emoji = ARTIFACT_TYPE_EMOJIS[artType] || '📦';
              const typeDisplay = artType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

              lines.push(`#### ${emoji} ${typeDisplay}`);
              lines.push('');
              lines.push(`**ID:** \`${art.id}\``);
              lines.push(`**Value:** $${(art.value_usd || 0).toFixed(2)}`);
              lines.push(`**Agent:** ${art.agent_type || 'unknown'}`);
              lines.push(`**Created:** ${art.created_at?.split('T')[0] || 'unknown'}`);
              lines.push('');

              if (art.description) {
                lines.push(`*${art.description}*`);
                lines.push('');
              }

              const shouldIncludeContent = include_content !== false;
              const maxLen = max_content_length ?? 2000;

              if (shouldIncludeContent && art.content) {
                let content = art.content;
                if (maxLen > 0 && content.length > maxLen) {
                  content = content.substring(0, maxLen) + '\n\n... (truncated)';
                }

                const lang = ['mermaid', 'python', 'typescript', 'javascript', 'sql', 'bash', 'json', 'yaml'].includes(art.format || '')
                  ? art.format : '';

                if (lang) {
                  lines.push(`\`\`\`${lang}`);
                  lines.push(content);
                  lines.push('```');
                } else {
                  lines.push(content);
                }
                lines.push('');
              }

              lines.push('---');
              lines.push('');
            }
          }

          const markdownContent = lines.join('\n');

          if (output_path) {
            // Save to file
            const dir = path.dirname(output_path);
            if (!fs.existsSync(dir)) {
              fs.mkdirSync(dir, { recursive: true });
            }
            fs.writeFileSync(output_path, markdownContent, 'utf-8');

            return {
              content: [{
                type: 'text',
                text: `Export completed successfully!

Format: MARKDOWN
Saved to: ${output_path}
Artifacts: ${artifacts.length}
Total Value: $${totalValue.toFixed(2)}`
              }],
              structuredContent: { saved_to: output_path, artifact_count: artifacts.length, total_value: totalValue }
            };
          } else {
            const header = `=== Export (${artifacts.length} artifacts, $${totalValue.toFixed(2)}) ===\n\n`;
            return {
              content: [{
                type: 'text',
                text: header + markdownContent
              }],
              structuredContent: { content: markdownContent, artifact_count: artifacts.length, total_value: totalValue }
            };
          }
        }
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [{
            type: 'text',
            text: `Error exporting artifacts: ${errorMsg}`
          }],
          isError: true
        };
      }
    }
  );

  // ============================================================================
  // TAG MANAGEMENT TOOLS
  // ============================================================================

  // Tool 12: Tag Artifact
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
        if (!tag || !tag.trim()) {
          return {
            content: [{ type: 'text', text: 'Error: tag is required and cannot be empty.' }],
            isError: true
          };
        }

        const normalizedTag = tag.trim().toLowerCase();
        const artifact = loadArtifactDirect(project_path, artifact_id);

        if (!artifact) {
          return {
            content: [{ type: 'text', text: `Error: Artifact not found: ${artifact_id}` }],
            isError: true
          };
        }

        // Initialize metadata and tags if not present
        if (!artifact.metadata) {
          (artifact as any).metadata = {};
        }
        if (!(artifact as any).metadata.tags) {
          (artifact as any).metadata.tags = [];
        }

        const tags: string[] = (artifact as any).metadata.tags;
        let message: string;

        if (action === 'add') {
          if (!tags.includes(normalizedTag)) {
            tags.push(normalizedTag);
            message = `Tag '${normalizedTag}' added to artifact ${artifact_id}`;
          } else {
            message = `Tag '${normalizedTag}' already exists on artifact ${artifact_id}`;
          }
        } else {
          const index = tags.indexOf(normalizedTag);
          if (index > -1) {
            tags.splice(index, 1);
            message = `Tag '${normalizedTag}' removed from artifact ${artifact_id}`;
          } else {
            message = `Tag '${normalizedTag}' not found on artifact ${artifact_id}`;
          }
        }

        // Save updated artifact
        const artifactsDir = getArtifactsDir(project_path);
        const index = loadArtifactIndex(project_path);
        let artifactPath: string | null = null;

        if (index.artifacts?.[artifact_id]?.storage_path) {
          artifactPath = path.join(project_path, index.artifacts[artifact_id].storage_path);
        } else {
          // Search for artifact file
          if (fs.existsSync(artifactsDir)) {
            const folders = fs.readdirSync(artifactsDir).filter(f =>
              fs.statSync(path.join(artifactsDir, f)).isDirectory()
            );
            for (const folder of folders) {
              const testPath = path.join(artifactsDir, folder, `${artifact_id}.json`);
              if (fs.existsSync(testPath)) {
                artifactPath = testPath;
                break;
              }
            }
          }
        }

        if (artifactPath) {
          (artifact as any).updated_at = new Date().toISOString();
          fs.writeFileSync(artifactPath, JSON.stringify(artifact, null, 2), 'utf-8');
        }

        return {
          content: [{ type: 'text', text: message }],
          structuredContent: {
            success: true,
            action,
            artifact_id,
            tag: normalizedTag,
            current_tags: tags
          }
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

  // Tool 13: Get Artifacts by Tag
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
        if (!tag || !tag.trim()) {
          return {
            content: [{ type: 'text', text: 'Error: tag is required.' }],
            isError: true
          };
        }

        const normalizedTag = tag.trim().toLowerCase();
        const allArtifacts = listArtifactsDirect(project_path, { limit: 10000 });

        // Filter by tag
        const taggedArtifacts = allArtifacts.filter(art => {
          const artTags: string[] = (art as any).metadata?.tags || [];
          return artTags.includes(normalizedTag);
        });

        // Format text output
        const lines = [`=== Artifacts with tag '${normalizedTag}' (${taggedArtifacts.length}) ===`, ''];

        for (const art of taggedArtifacts) {
          lines.push(`ID: ${art.id}`);
          lines.push(`  Type: ${art.type || 'unknown'}`);
          lines.push(`  Value: $${art.value_usd || 0}`);
          lines.push(`  Tags: ${((art as any).metadata?.tags || []).join(', ')}`);
          const preview = (art.content || '').substring(0, 50);
          lines.push(`  Preview: ${preview}${art.content?.length > 50 ? '...' : ''}`);
          lines.push('');
        }

        if (taggedArtifacts.length === 0) {
          lines.push(`No artifacts found with tag '${normalizedTag}'.`);
        }

        return {
          content: [{
            type: 'text',
            text: lines.join('\n')
          }],
          structuredContent: {
            tag: normalizedTag,
            count: taggedArtifacts.length,
            artifacts: taggedArtifacts
          }
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

  // Tool 14: List All Tags
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
        const allArtifacts = listArtifactsDirect(project_path, { limit: 10000 });

        // Collect all unique tags
        const allTags = new Set<string>();
        for (const art of allArtifacts) {
          const artTags: string[] = (art as any).metadata?.tags || [];
          for (const tag of artTags) {
            allTags.add(tag);
          }
        }

        const sortedTags = Array.from(allTags).sort();

        // Format text output
        const lines = [`=== All Tags (${sortedTags.length}) ===`, ''];
        for (const tag of sortedTags) {
          lines.push(`  - ${tag}`);
        }

        if (sortedTags.length === 0) {
          lines.push('  No tags found. Use tag_artifact to add tags to artifacts.');
        }

        return {
          content: [{
            type: 'text',
            text: lines.join('\n')
          }],
          structuredContent: {
            count: sortedTags.length,
            tags: sortedTags
          }
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

  // Tool 15: Cleanup Artifacts
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

        // Load index
        const index = loadArtifactIndex(project_path);
        const artifacts = index || {};

        let result: {
          deleted_count: number;
          freed_bytes?: number;
          kept_count?: number;
          deleted_ids: string[];
          dry_run: boolean;
        };

        if (artifact_type) {
          // Cleanup by type - keep only N most recent of this type
          const typeArtifacts: Array<{ id: string; date: string; path?: string }> = [];

          for (const [artId, artMeta] of Object.entries(artifacts)) {
            if ((artMeta as any)?.type === artifact_type) {
              typeArtifacts.push({
                id: artId,
                date: (artMeta as any)?.date || '',
                path: (artMeta as any)?.path
              });
            }
          }

          // Sort by date descending (most recent first)
          typeArtifacts.sort((a, b) => b.date.localeCompare(a.date));

          // Determine which to delete
          const toDelete = typeArtifacts.slice(actualKeepLatest);
          const deletedIds = toDelete.map(a => a.id);

          if (!actualDryRun) {
            // Actually delete files
            for (const art of toDelete) {
              if (art.path) {
                const fullPath = path.join(project_path, art.path);
                if (fs.existsSync(fullPath)) {
                  fs.unlinkSync(fullPath);
                }
              }
            }
            // Note: Index update would be handled by backend in production
          }

          result = {
            deleted_count: deletedIds.length,
            kept_count: typeArtifacts.length - deletedIds.length,
            deleted_ids: deletedIds,
            dry_run: actualDryRun
          };
        } else {
          // Cleanup by age
          const cutoffDate = new Date();
          cutoffDate.setDate(cutoffDate.getDate() - actualDays);
          const cutoffStr = cutoffDate.toISOString().split('T')[0];

          const toDelete: Array<{ id: string; path?: string; size: number }> = [];

          for (const [artId, artMeta] of Object.entries(artifacts)) {
            const artDate = (artMeta as any)?.date || '';
            if (artDate < cutoffStr) {
              const artPath = (artMeta as any)?.path;
              let fileSize = 0;
              if (artPath) {
                const fullPath = path.join(project_path, artPath);
                if (fs.existsSync(fullPath)) {
                  try {
                    fileSize = fs.statSync(fullPath).size;
                  } catch { /* ignore */ }
                }
              }
              toDelete.push({ id: artId, path: artPath, size: fileSize });
            }
          }

          const deletedIds = toDelete.map(a => a.id);
          const freedBytes = toDelete.reduce((sum, a) => sum + a.size, 0);

          if (!actualDryRun) {
            // Actually delete files
            for (const art of toDelete) {
              if (art.path) {
                const fullPath = path.join(project_path, art.path);
                if (fs.existsSync(fullPath)) {
                  fs.unlinkSync(fullPath);
                }
              }
            }
          }

          result = {
            deleted_count: deletedIds.length,
            freed_bytes: freedBytes,
            deleted_ids: deletedIds,
            dry_run: actualDryRun
          };
        }

        // Format response
        let responseText: string;

        if (artifact_type) {
          const actionWord = actualDryRun ? "Would delete" : "Deleted";
          responseText = `=== Cleanup by Type: ${artifact_type} ===

Mode: ${actualDryRun ? "DRY RUN (preview only)" : "ACTUAL DELETION"}
Type: ${artifact_type}
Keep Latest: ${actualKeepLatest}

${actionWord}: ${result.deleted_count} artifacts
Kept: ${result.kept_count || 0} artifacts

${actualDryRun ? "IDs that would be deleted:" : "Deleted IDs:"}
${result.deleted_ids.slice(0, 20).map(id => `  - ${id}`).join('\n') || '  (none)'}
${result.deleted_ids.length > 20 ? `  ... and ${result.deleted_ids.length - 20} more` : ''}`;
        } else {
          const actionWord = actualDryRun ? "Would delete" : "Deleted";
          const freedKb = (result.freed_bytes || 0) / 1024;
          responseText = `=== Cleanup by Age ===

Mode: ${actualDryRun ? "DRY RUN (preview only)" : "ACTUAL DELETION"}
Cutoff: ${actualDays} days old

${actionWord}: ${result.deleted_count} artifacts
${actionWord.replace('delete', 'free')}: ${freedKb.toFixed(2)} KB

${actualDryRun ? "IDs that would be deleted:" : "Deleted IDs:"}
${result.deleted_ids.slice(0, 20).map(id => `  - ${id}`).join('\n') || '  (none)'}
${result.deleted_ids.length > 20 ? `  ... and ${result.deleted_ids.length - 20} more` : ''}`;
        }

        if (actualDryRun && result.deleted_count > 0) {
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

  // Tool 16: Archive Artifacts
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

        const artifactsDir = getArtifactsDir(project_path);
        const archiveDir = path.join(artifactsDir, 'archive');

        // Create archive directory
        if (!fs.existsSync(archiveDir)) {
          fs.mkdirSync(archiveDir, { recursive: true });
        }

        const index = loadArtifactIndex(project_path);
        const archivedIds: string[] = [];
        const failedIds: string[] = [];

        for (const artId of artifact_ids) {
          const artMeta = index[artId];
          if (!artMeta || !artMeta.path) {
            failedIds.push(artId);
            continue;
          }

          const sourcePath = path.join(project_path, artMeta.path);
          const destPath = path.join(archiveDir, `${artId}.json`);

          if (!fs.existsSync(sourcePath)) {
            failedIds.push(artId);
            continue;
          }

          try {
            // Move file to archive
            fs.renameSync(sourcePath, destPath);
            archivedIds.push(artId);
          } catch {
            failedIds.push(artId);
          }
        }

        const result = {
          archived_count: archivedIds.length,
          failed_count: failedIds.length,
          archived_ids: archivedIds,
          failed_ids: failedIds
        };

        const responseText = `=== Archive Results ===

Archived: ${result.archived_count} artifacts
Failed: ${result.failed_count} artifacts

Archived IDs:
${archivedIds.map(id => `  - ${id}`).join('\n') || '  (none)'}
${failedIds.length > 0 ? `\nFailed IDs:\n${failedIds.map(id => `  - ${id}`).join('\n')}` : ''}`;

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

  // Tool 17: Get Cleanup Preview
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

        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - actualDays);
        const cutoffStr = cutoffDate.toISOString().split('T')[0];

        const index = loadArtifactIndex(project_path);
        const toDelete: Array<{
          id: string;
          type: string;
          date: string;
          value_usd: number;
          size_bytes: number;
          spec_id?: string;
        }> = [];

        let totalBytes = 0;

        for (const [artId, artMeta] of Object.entries(index || {})) {
          const meta = artMeta as any;
          const artDate = meta?.date || '';

          if (artDate < cutoffStr) {
            let fileSize = 0;
            if (meta?.path) {
              const fullPath = path.join(project_path, meta.path);
              if (fs.existsSync(fullPath)) {
                try {
                  fileSize = fs.statSync(fullPath).size;
                } catch { /* ignore */ }
              }
            }

            totalBytes += fileSize;

            toDelete.push({
              id: artId,
              type: meta?.type || 'unknown',
              date: artDate,
              value_usd: meta?.value_usd || 0,
              size_bytes: fileSize,
              spec_id: meta?.spec_id
            });
          }
        }

        // Sort by date ascending (oldest first)
        toDelete.sort((a, b) => a.date.localeCompare(b.date));

        const result = {
          would_delete: toDelete.length,
          total_bytes: totalBytes,
          artifacts: toDelete,
          cutoff_date: cutoffStr,
          days: actualDays
        };

        const freedKb = totalBytes / 1024;

        let responseText = `=== Cleanup Preview ===

Cutoff: ${actualDays} days (before ${cutoffStr})
Would Delete: ${toDelete.length} artifacts
Would Free: ${freedKb.toFixed(2)} KB

Artifacts to delete (oldest first):`;

        for (const art of toDelete.slice(0, 30)) {
          const sizeKb = art.size_bytes / 1024;
          responseText += `\n  ${art.id}`;
          responseText += `\n    Type: ${art.type} | Date: ${art.date} | Value: $${art.value_usd} | Size: ${sizeKb.toFixed(1)}KB`;
          if (art.spec_id) {
            responseText += ` | Spec: ${art.spec_id}`;
          }
        }

        if (toDelete.length > 30) {
          responseText += `\n\n  ... and ${toDelete.length - 30} more artifacts`;
        }

        if (toDelete.length > 0) {
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

  return server;
}

/**
 * Start HTTP server for MCP
 */
export function startAutoClaudeToolsHttpServer(): ReturnType<typeof express> {
  const app = express();
  app.use(express.json());

  const server = createAutoClaudeToolsServer();
  const transports: Record<string, StreamableHTTPServerTransport> = {};

  // Handle MCP requests
  app.post('/mcp', async (req: ExpressRequest, res: ExpressResponse) => {
    const sessionId = req.headers['mcp-session-id'] as string | undefined;
    let transport: StreamableHTTPServerTransport;

    if (sessionId && transports[sessionId]) {
      // Reuse existing session
      transport = transports[sessionId];
    } else {
      // New session
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        onsessioninitialized: (id: string) => {
          transports[id] = transport;
          console.log('[Auto-Claude Tools HTTP] Session initialized:', id);
        },
        onsessionclosed: (id: string) => {
          delete transports[id];
          console.log('[Auto-Claude Tools HTTP] Session closed:', id);
        }
      });

      transport.onclose = () => {
        if (transport.sessionId) {
          delete transports[transport.sessionId];
        }
      };

      await server.connect(transport);
    }

    // Cast to IncomingMessage/ServerResponse for MCP SDK compatibility
    await transport.handleRequest(
      req as unknown as IncomingMessage,
      res as unknown as ServerResponse,
      req.body
    );
  });

  // Health check endpoint
  app.get('/health', (_req: ExpressRequest, res: ExpressResponse) => {
    res.json({
      status: 'healthy',
      server: 'auto-claude-tools-http',
      version: '1.0.0',
      uptime: process.uptime()
    });
  });

  app.listen(PORT, () => {
    console.log(`[Auto-Claude Tools HTTP] Server running on http://localhost:${PORT}/mcp`);
  });

  return app;
}
