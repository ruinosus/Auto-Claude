/**
 * Electron API Bridge for STDIO MCP Server
 *
 * This HTTP server provides an API bridge between the STDIO MCP server
 * (running as a subprocess) and the Electron main process.
 *
 * The STDIO server calls this API to get data from Electron.
 */

import express from 'express';
import type { Request as ExpressRequest, Response as ExpressResponse } from 'express-serve-static-core';
import { ipcMain } from 'electron';
import * as fs from 'fs';
import * as path from 'path';
import { projectStore } from '../project-store';

const API_PORT = process.env.ELECTRON_API_PORT || 9824;

// ============================================================================
// ARTIFACT STORAGE HELPERS
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
  session_num?: number;
}

interface ArtifactFilters {
  spec_id?: string;
  trace_id?: string;
  type?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
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

function loadArtifact(projectPath: string, artifactId: string): LocalArtifact | null {
  const artifactsDir = getArtifactsDir(projectPath);

  // Try to find via index first
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

  // Fallback: search in date folders
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

function listArtifacts(projectPath: string, filters?: ArtifactFilters): LocalArtifact[] {
  const artifactsDir = getArtifactsDir(projectPath);
  const artifacts: LocalArtifact[] = [];

  if (!fs.existsSync(artifactsDir)) {
    return artifacts;
  }

  const folders = fs.readdirSync(artifactsDir).filter(f => {
    const fullPath = path.join(artifactsDir, f);
    return fs.statSync(fullPath).isDirectory();
  });

  // Filter by date range
  const filteredFolders = folders.filter(folder => {
    if (filters?.date_from && folder < filters.date_from) return false;
    if (filters?.date_to && folder > filters.date_to) return false;
    return true;
  });

  for (const folder of filteredFolders) {
    const folderPath = path.join(artifactsDir, folder);
    const files = fs.readdirSync(folderPath).filter(f => f.endsWith('.json'));

    for (const file of files) {
      try {
        const artifact = JSON.parse(
          fs.readFileSync(path.join(folderPath, file), 'utf-8')
        );

        // Apply filters
        if (filters?.spec_id && artifact.spec_id !== filters.spec_id) continue;
        if (filters?.trace_id && artifact.trace_id !== filters.trace_id) continue;
        if (filters?.type && artifact.type !== filters.type) continue;

        artifacts.push(artifact);

        if (filters?.limit && artifacts.length >= filters.limit) {
          return artifacts;
        }
      } catch {
        // Skip invalid files
      }
    }
  }

  return artifacts;
}

interface BuildProgressResponse {
  specId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  phase?: string;
  progress: number;
  currentTask?: string;
  startedAt?: string;
  completedAt?: string;
}

interface ProjectContextResponse {
  projectPath: string;
  projectName: string;
  techStack: string[];
  recentSpecs: Array<{
    id: string;
    name: string;
    status: string;
  }>;
  codebaseStats?: {
    totalFiles: number;
    totalLines: number;
    languages: Record<string, number>;
  };
}

interface SearchCodeResponse {
  query: string;
  totalMatches: number;
  results: Array<{
    file: string;
    line: number;
    column: number;
    match: string;
    context?: string;
  }>;
}

/**
 * Get build progress from implementation_plan.json
 * Reads actual task progress from the spec directory
 */
async function getBuildProgress(specId: string): Promise<BuildProgressResponse> {
  // Get the active project from tab state to find the spec
  const tabState = projectStore.getTabState();
  let projectPath: string | undefined;

  if (tabState.activeProjectId) {
    const activeProject = projectStore.getProject(tabState.activeProjectId);
    projectPath = activeProject?.path;
  }

  // Fallback to first project
  if (!projectPath) {
    const projects = projectStore.getProjects();
    if (projects.length > 0) {
      projectPath = projects[0].path;
    }
  }

  if (!projectPath) {
    return {
      specId,
      status: 'pending',
      progress: 0
    };
  }

  // Find the spec directory - check both .auto-claude and auto-claude paths
  const specsDirs = [
    path.join(projectPath, '.auto-claude', 'specs'),
    path.join(projectPath, 'auto-claude', 'specs')
  ];

  let planPath: string | undefined;
  for (const specsDir of specsDirs) {
    const potentialPath = path.join(specsDir, specId, 'implementation_plan.json');
    if (fs.existsSync(potentialPath)) {
      planPath = potentialPath;
      break;
    }
  }

  if (!planPath) {
    return {
      specId,
      status: 'pending',
      progress: 0
    };
  }

  try {
    const planContent = fs.readFileSync(planPath, 'utf-8');
    const plan = JSON.parse(planContent);

    // Calculate progress from subtasks
    const phases = plan.phases || [];
    let totalSubtasks = 0;
    let completedSubtasks = 0;
    let currentTask: string | undefined;

    for (const phase of phases) {
      const subtasks = phase.subtasks || phase.chunks || [];
      for (const subtask of subtasks) {
        totalSubtasks++;
        if (subtask.status === 'completed') {
          completedSubtasks++;
        } else if (subtask.status === 'in_progress' && !currentTask) {
          currentTask = subtask.description;
        }
      }
    }

    const progress = totalSubtasks > 0 ? Math.round((completedSubtasks / totalSubtasks) * 100) : 0;

    // Determine status based on plan status and subtask states
    let status: BuildProgressResponse['status'] = 'pending';
    const planStatus = plan.status || plan.planStatus;

    if (planStatus === 'done' || planStatus === 'completed') {
      status = 'completed';
    } else if (planStatus === 'failed') {
      status = 'failed';
    } else if (totalSubtasks > 0 && completedSubtasks === totalSubtasks) {
      status = 'completed';
    } else if (completedSubtasks > 0 || phases.some((p: { subtasks?: Array<{status: string}>; chunks?: Array<{status: string}> }) =>
      (p.subtasks || p.chunks || []).some((s) => s.status === 'in_progress'))) {
      status = 'running';
    }

    // Determine phase
    let phase: string | undefined;
    if (planStatus === 'planning' || planStatus === 'spec') {
      phase = 'planning';
    } else if (planStatus === 'coding' || planStatus === 'in_progress') {
      phase = 'implementation';
    } else if (planStatus === 'review' || planStatus === 'ai_review') {
      phase = 'review';
    } else if (planStatus === 'qa') {
      phase = 'qa';
    }

    return {
      specId,
      status,
      phase,
      progress,
      currentTask,
      startedAt: plan.created_at,
      completedAt: status === 'completed' ? plan.updated_at : undefined
    };
  } catch {
    return {
      specId,
      status: 'pending',
      progress: 0
    };
  }
}

/**
 * Get project context from ProjectStore
 * Returns actual project data instead of mock data
 */
async function getProjectContext(
  projectPath?: string,
  includeMemory?: boolean
): Promise<ProjectContextResponse> {
  // If projectPath is provided, try to find or add the project
  if (projectPath) {
    // Check if project exists in store by path
    const projects = projectStore.getProjects();
    let project = projects.find(p => p.path === projectPath);

    if (!project) {
      // Project not in store yet - add it
      project = projectStore.addProject(projectPath);
    }

    // Get tasks (specs) for the project
    const tasks = projectStore.getTasks(project.id);
    const recentSpecs = tasks.slice(0, 5).map(task => ({
      id: task.specId,
      name: task.title,
      status: task.status
    }));

    // Detect tech stack from project files
    const techStack: string[] = [];
    if (fs.existsSync(path.join(projectPath, 'package.json'))) {
      techStack.push('JavaScript', 'Node.js');
      // Check for specific frameworks
      try {
        const pkgJson = JSON.parse(fs.readFileSync(path.join(projectPath, 'package.json'), 'utf-8'));
        const allDeps = { ...pkgJson.dependencies, ...pkgJson.devDependencies };
        if (allDeps?.['typescript']) techStack.push('TypeScript');
        if (allDeps?.['react']) techStack.push('React');
        if (allDeps?.['vue']) techStack.push('Vue');
        if (allDeps?.['angular'] || allDeps?.['@angular/core']) techStack.push('Angular');
        if (allDeps?.['next']) techStack.push('Next.js');
        if (allDeps?.['electron']) techStack.push('Electron');
        if (allDeps?.['express']) techStack.push('Express');
        if (allDeps?.['fastify']) techStack.push('Fastify');
      } catch {
        // Ignore parse errors
      }
    }
    if (fs.existsSync(path.join(projectPath, 'requirements.txt')) ||
        fs.existsSync(path.join(projectPath, 'pyproject.toml'))) {
      techStack.push('Python');
    }
    if (fs.existsSync(path.join(projectPath, 'Cargo.toml'))) {
      techStack.push('Rust');
    }
    if (fs.existsSync(path.join(projectPath, 'go.mod'))) {
      techStack.push('Go');
    }

    return {
      projectPath: project.path,
      projectName: project.name,
      techStack: techStack.length > 0 ? techStack : ['Unknown'],
      recentSpecs,
      codebaseStats: includeMemory ? await getCodebaseStats(projectPath) : undefined
    };
  }

  // No projectPath provided - try to get the active project from tab state
  const tabState = projectStore.getTabState();
  if (tabState.activeProjectId) {
    const activeProject = projectStore.getProject(tabState.activeProjectId);
    if (activeProject) {
      return getProjectContext(activeProject.path, includeMemory);
    }
  }

  // Fallback: return first project if any
  const projects = projectStore.getProjects();
  if (projects.length > 0) {
    return getProjectContext(projects[0].path, includeMemory);
  }

  // No projects found - return empty response
  return {
    projectPath: '',
    projectName: 'No project selected',
    techStack: [],
    recentSpecs: [],
    codebaseStats: undefined
  };
}

/**
 * Get codebase statistics for a project
 */
async function getCodebaseStats(projectPath: string): Promise<ProjectContextResponse['codebaseStats']> {
  const stats = {
    totalFiles: 0,
    totalLines: 0,
    languages: {} as Record<string, number>
  };

  const extensions: Record<string, string> = {
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript',
    '.js': 'JavaScript',
    '.jsx': 'JavaScript',
    '.py': 'Python',
    '.rs': 'Rust',
    '.go': 'Go',
    '.java': 'Java',
    '.json': 'JSON',
    '.md': 'Markdown'
  };

  function countFiles(dir: string, depth: number = 0): void {
    if (depth > 5) return; // Limit depth
    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        // Skip common ignored directories
        if (entry.name.startsWith('.') || entry.name === 'node_modules' ||
            entry.name === 'dist' || entry.name === 'build' ||
            entry.name === '__pycache__' || entry.name === 'venv' ||
            entry.name === '.venv' || entry.name === 'target') {
          continue;
        }

        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          countFiles(fullPath, depth + 1);
        } else if (entry.isFile()) {
          const ext = path.extname(entry.name).toLowerCase();
          const lang = extensions[ext];
          if (lang) {
            stats.totalFiles++;
            try {
              const content = fs.readFileSync(fullPath, 'utf-8');
              const lines = content.split('\n').length;
              stats.totalLines += lines;
              stats.languages[lang] = (stats.languages[lang] || 0) + lines;
            } catch {
              // Skip files that can't be read
            }
          }
        }
      }
    } catch {
      // Ignore directory read errors
    }
  }

  countFiles(projectPath);
  return stats;
}

/**
 * Search code in project files
 * Uses Node.js fs APIs to search for patterns in files
 */
async function searchCode(
  query: string,
  filePattern?: string,
  caseSensitive?: boolean,
  maxResults?: number
): Promise<SearchCodeResponse> {
  // Get the active project
  const tabState = projectStore.getTabState();
  let projectPath: string | undefined;

  if (tabState.activeProjectId) {
    const activeProject = projectStore.getProject(tabState.activeProjectId);
    projectPath = activeProject?.path;
  }

  if (!projectPath) {
    const projects = projectStore.getProjects();
    if (projects.length > 0) {
      projectPath = projects[0].path;
    }
  }

  if (!projectPath) {
    return {
      query,
      totalMatches: 0,
      results: []
    };
  }

  const results: SearchCodeResponse['results'] = [];
  const limit = maxResults || 20;
  const searchRegex = caseSensitive
    ? new RegExp(query, 'g')
    : new RegExp(query, 'gi');

  // File extensions to search
  const codeExtensions = new Set([
    '.ts', '.tsx', '.js', '.jsx', '.py', '.rs', '.go', '.java',
    '.c', '.cpp', '.h', '.hpp', '.cs', '.rb', '.php', '.swift',
    '.kt', '.scala', '.vue', '.svelte', '.md', '.json', '.yaml', '.yml'
  ]);

  // Check if file matches pattern (simple glob support)
  const matchesPattern = (filename: string): boolean => {
    if (!filePattern) return true;

    // Convert glob to regex-like matching
    const pattern = filePattern
      .replace(/\*\*/g, '{{DOUBLESTAR}}')
      .replace(/\*/g, '[^/]*')
      .replace(/\?/g, '.')
      .replace(/{{DOUBLESTAR}}/g, '.*');

    try {
      const regex = new RegExp(`^${pattern}$`, 'i');
      return regex.test(filename);
    } catch {
      // If pattern is invalid, do simple includes check
      return filename.includes(filePattern.replace(/\*/g, ''));
    }
  };

  function searchDir(dir: string, depth: number = 0): void {
    if (depth > 10 || results.length >= limit) return;

    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        if (results.length >= limit) break;

        // Skip ignored directories
        if (entry.name.startsWith('.') || entry.name === 'node_modules' ||
            entry.name === 'dist' || entry.name === 'build' ||
            entry.name === '__pycache__' || entry.name === 'venv' ||
            entry.name === '.venv' || entry.name === 'target' ||
            entry.name === 'coverage' || entry.name === '.git') {
          continue;
        }

        const fullPath = path.join(dir, entry.name);
        const relativePath = path.relative(projectPath!, fullPath);

        if (entry.isDirectory()) {
          searchDir(fullPath, depth + 1);
        } else if (entry.isFile()) {
          const ext = path.extname(entry.name).toLowerCase();
          if (!codeExtensions.has(ext)) continue;
          if (!matchesPattern(relativePath)) continue;

          try {
            const content = fs.readFileSync(fullPath, 'utf-8');
            const lines = content.split('\n');

            for (let i = 0; i < lines.length && results.length < limit; i++) {
              const line = lines[i];
              searchRegex.lastIndex = 0;
              const match = searchRegex.exec(line);

              if (match) {
                results.push({
                  file: relativePath,
                  line: i + 1,
                  column: match.index + 1,
                  match: match[0],
                  context: line.trim().substring(0, 200)
                });
              }
            }
          } catch {
            // Skip files that can't be read
          }
        }
      }
    } catch {
      // Ignore directory read errors
    }
  }

  searchDir(projectPath);

  return {
    query,
    totalMatches: results.length,
    results
  };
}

/**
 * Start API bridge server
 */
export function startElectronApiBridge(): ReturnType<typeof express> {
  const app = express();
  app.use(express.json());

  // Endpoint: Get build progress
  app.get('/api/build-progress', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { specId } = req.query;

      if (!specId || typeof specId !== 'string') {
        res.status(400).json({ error: 'specId is required' });
        return;
      }

      const data = await getBuildProgress(specId);
      res.json(data);
    } catch (error) {
      console.error('[API Bridge] Error in /api/build-progress:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Get project context
  app.get('/api/context', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { projectPath, includeMemory } = req.query;

      const data = await getProjectContext(
        projectPath as string | undefined,
        includeMemory === 'true'
      );

      res.json(data);
    } catch (error) {
      console.error('[API Bridge] Error in /api/context:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Search code
  app.get('/api/search-code', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { query, filePattern, caseSensitive, maxResults } = req.query;

      if (!query || typeof query !== 'string') {
        res.status(400).json({ error: 'query is required' });
        return;
      }

      const data = await searchCode(
        query,
        filePattern as string | undefined,
        caseSensitive === 'true',
        maxResults ? parseInt(maxResults as string, 10) : undefined
      );

      res.json(data);
    } catch (error) {
      console.error('[API Bridge] Error in /api/search-code:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Update subtask status
  app.get('/api/update-subtask-status', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { subtask_id, status, notes } = req.query;
      console.log(`[API Bridge] Updating subtask ${subtask_id} to ${status}`);
      res.json({
        success: true,
        subtask_id,
        status,
        notes,
        updatedAt: new Date().toISOString()
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/update-subtask-status:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: Record discovery
  app.get('/api/record-discovery', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { file_path, description, category } = req.query;
      console.log(`[API Bridge] Recording discovery: ${file_path}`);
      res.json({
        success: true,
        discovery: { file_path, description, category },
        recordedAt: new Date().toISOString()
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/record-discovery:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: Record gotcha
  app.get('/api/record-gotcha', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { gotcha, context } = req.query;
      console.log(`[API Bridge] Recording gotcha: ${gotcha}`);
      res.json({
        success: true,
        gotcha: { gotcha, context },
        recordedAt: new Date().toISOString()
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/record-gotcha:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: Get session context
  app.get('/api/session-context', async (_req: ExpressRequest, res: ExpressResponse) => {
    try {
      res.json({
        sessionId: `session-${Date.now()}`,
        startedAt: new Date().toISOString(),
        discoveries: [],
        gotchas: [],
        patterns: []
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/session-context:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: Update QA status
  app.get('/api/update-qa-status', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { status, issues, tests_passed } = req.query;
      console.log(`[API Bridge] Updating QA status to ${status}`);
      res.json({
        success: true,
        status,
        issues: issues ? JSON.parse(issues as string) : [],
        tests_passed: tests_passed ? JSON.parse(tests_passed as string) : {},
        updatedAt: new Date().toISOString()
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/update-qa-status:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // In-memory activity storage for ROI tracking
  const activities: Array<{
    activity_type: string;
    description: string;
    count: number;
    complexity?: string;
    timestamp: string;
  }> = [];

  // Endpoint: Report activity (ROI tracking)
  app.get('/api/report-activity', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { activity_type, description, count, complexity } = req.query;
      const activity = {
        activity_type: activity_type as string,
        description: description as string,
        count: count ? parseInt(count as string, 10) : 1,
        complexity: complexity as string | undefined,
        timestamp: new Date().toISOString()
      };
      activities.push(activity);
      console.log(`[API Bridge] Activity reported: ${activity_type} - ${description}`);
      res.json({
        success: true,
        activity,
        totalActivities: activities.length
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/report-activity:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: Get activity summary
  app.get('/api/activity-summary', async (_req: ExpressRequest, res: ExpressResponse) => {
    try {
      // Group activities by type
      const summary = activities.reduce((acc, activity) => {
        const type = activity.activity_type;
        if (!acc[type]) {
          acc[type] = { count: 0, items: [] };
        }
        acc[type].count += activity.count;
        acc[type].items.push(activity);
        return acc;
      }, {} as Record<string, { count: number; items: typeof activities }>);

      res.json({
        totalActivities: activities.length,
        summary,
        generatedAt: new Date().toISOString()
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/activity-summary:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // Endpoint: List activity types
  app.get('/api/activity-types', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { category } = req.query;

      const activityTypes = {
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
      };

      if (category && typeof category === 'string' && category in activityTypes) {
        res.json({ [category]: activityTypes[category as keyof typeof activityTypes] });
      } else {
        res.json(activityTypes);
      }
    } catch (error) {
      console.error('[API Bridge] Error in /api/activity-types:', error);
      res.status(500).json({ error: error instanceof Error ? error.message : 'Internal server error' });
    }
  });

  // ============================================================================
  // ARTIFACT ENDPOINTS
  // ============================================================================

  // Endpoint: Get single artifact by ID
  app.get('/api/artifact/:id', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { id } = req.params;
      const { projectPath } = req.query;

      if (!projectPath || typeof projectPath !== 'string') {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      const artifact = loadArtifact(projectPath, id);
      if (!artifact) {
        res.status(404).json({ error: 'Artifact not found' });
        return;
      }

      res.json(artifact);
    } catch (error) {
      console.error('[API Bridge] Error in /api/artifact/:id:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: List artifacts with filters
  app.get('/api/artifacts', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { projectPath, spec_id, trace_id, type, date_from, date_to, limit } = req.query;

      if (!projectPath || typeof projectPath !== 'string') {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      const filters: ArtifactFilters = {};
      if (spec_id) filters.spec_id = spec_id as string;
      if (trace_id) filters.trace_id = trace_id as string;
      if (type) filters.type = type as string;
      if (date_from) filters.date_from = date_from as string;
      if (date_to) filters.date_to = date_to as string;
      if (limit) filters.limit = parseInt(limit as string, 10);

      const artifacts = listArtifacts(projectPath, filters);
      res.json({
        count: artifacts.length,
        artifacts: artifacts.map(a => ({
          id: a.id,
          type: a.type,
          format: a.format,
          value_usd: a.value_usd,
          description: a.description,
          created_at: a.created_at,
          spec_id: a.spec_id,
          trace_id: a.trace_id,
          agent_type: a.agent_type,
          content_preview: a.content?.substring(0, 200) + (a.content?.length > 200 ? '...' : '')
        }))
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/artifacts:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Get artifacts by trace ID
  app.get('/api/artifacts/trace/:traceId', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { traceId } = req.params;
      const { projectPath } = req.query;

      if (!projectPath || typeof projectPath !== 'string') {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      const artifacts = listArtifacts(projectPath, { trace_id: traceId });
      res.json({
        trace_id: traceId,
        count: artifacts.length,
        artifacts
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/artifacts/trace/:traceId:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Get artifact content only (for large artifacts)
  app.get('/api/artifact/:id/content', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { id } = req.params;
      const { projectPath } = req.query;

      if (!projectPath || typeof projectPath !== 'string') {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      const artifact = loadArtifact(projectPath, id);
      if (!artifact) {
        res.status(404).json({ error: 'Artifact not found' });
        return;
      }

      res.type(artifact.format === 'json' ? 'application/json' : 'text/plain');
      res.send(artifact.content);
    } catch (error) {
      console.error('[API Bridge] Error in /api/artifact/:id/content:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Get comprehensive artifact statistics
  app.get('/api/artifacts/statistics', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { projectPath } = req.query;

      if (!projectPath || typeof projectPath !== 'string') {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      // Get all artifacts
      const artifacts = listArtifacts(projectPath, {});

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

      res.json({
        total_count: artifacts.length,
        total_value_usd: totalValue,
        by_type: byType,
        by_tab: byTab,
        by_period: byPeriod,
        top_valuable: topValuable,
        value_by_type: valueByType,
        value_by_tab: valueByTab,
        last_updated: new Date().toISOString(),
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/artifacts/statistics:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Search artifacts
  app.get('/api/artifacts/search', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { projectPath, query, artifact_types, spec_id, limit } = req.query;

      if (!projectPath || typeof projectPath !== 'string') {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      if (!query || typeof query !== 'string' || query.trim().length < 1) {
        res.status(400).json({ error: 'query is required' });
        return;
      }

      const searchQuery = query.trim().toLowerCase();
      const maxResults = limit ? parseInt(limit as string, 10) : 50;
      const PREVIEW_LENGTH = 200;

      // Parse artifact_types filter if provided
      let typeFilter: string[] | null = null;
      if (artifact_types && typeof artifact_types === 'string') {
        try {
          typeFilter = JSON.parse(artifact_types);
        } catch {
          typeFilter = [artifact_types];
        }
      }

      // Get all artifacts with optional spec_id filter
      let artifacts = listArtifacts(projectPath, {
        spec_id: spec_id as string | undefined,
        limit: 10000 // High limit, we'll filter and limit manually
      });

      // Apply type filter if provided
      if (typeFilter && typeFilter.length > 0) {
        artifacts = artifacts.filter(a => typeFilter!.includes(a.type || ''));
      }

      // Helper function to highlight match
      const highlightMatch = (text: string, searchQuery: string, contextChars: number = 30): string => {
        if (!text || !searchQuery) return '';

        const textLower = text.toLowerCase();
        const queryLower = searchQuery.toLowerCase();

        const matchIdx = textLower.indexOf(queryLower);
        if (matchIdx === -1) return '';

        const start = Math.max(0, matchIdx - contextChars);
        const end = Math.min(text.length, matchIdx + searchQuery.length + contextChars);

        const snippet = text.substring(start, end);
        const prefix = start > 0 ? '...' : '';
        const suffix = end < text.length ? '...' : '';

        const matchStartInSnippet = matchIdx - start;
        const matchEndInSnippet = matchStartInSnippet + searchQuery.length;

        const highlighted =
          snippet.substring(0, matchStartInSnippet) +
          '**' + snippet.substring(matchStartInSnippet, matchEndInSnippet) + '**' +
          snippet.substring(matchEndInSnippet);

        return prefix + highlighted + suffix;
      };

      // Helper function to calculate relevance score
      const calculateRelevance = (
        artifact: LocalArtifact,
        searchQuery: string,
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
          const regex = new RegExp(searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
          const occurrences = (content.match(regex) || []).length;
          score += Math.min(occurrences * 5, 25);
        }

        // Recency bonus
        const today = new Date().toISOString().split('T')[0];
        if (artifact.created_at?.startsWith(today)) {
          score += 10;
        }

        return score;
      };

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

        const relevanceScore = calculateRelevance(artifact, searchQuery, contentMatch, descriptionMatch, typeMatch);

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

      res.json({
        query,
        total_results: limitedResults.length,
        results: limitedResults
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/artifacts/search:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Endpoint: Aggregate artifacts by agent type
  app.get('/api/artifacts/by-agent', async (req: ExpressRequest, res: ExpressResponse) => {
    try {
      const { projectPath, date_from, date_to } = req.query;

      if (!projectPath || typeof projectPath !== 'string') {
        res.status(400).json({ error: 'projectPath is required' });
        return;
      }

      // Get all artifacts (with optional date filtering via listArtifacts)
      const artifacts = listArtifacts(projectPath, {
        date_from: date_from as string | undefined,
        date_to: date_to as string | undefined,
      });

      // Aggregate by agent_type
      const byAgent: Record<string, { count: number; total_value_usd: number; types: Set<string> }> = {};

      for (const artifact of artifacts) {
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

      res.json({
        by_agent: result,
        summary: {
          total_count: totalCount,
          total_value_usd: totalValue,
          agent_count: Object.keys(result).length
        }
      });
    } catch (error) {
      console.error('[API Bridge] Error in /api/artifacts/by-agent:', error);
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // Health check
  app.get('/api/health', (_req: ExpressRequest, res: ExpressResponse) => {
    res.json({
      status: 'healthy',
      service: 'electron-api-bridge',
      uptime: process.uptime(),
      activitiesRecorded: activities.length
    });
  });

  app.listen(API_PORT, () => {
    console.log(`[Electron API Bridge] Server running on http://localhost:${API_PORT}/api`);
  });

  return app;
}
