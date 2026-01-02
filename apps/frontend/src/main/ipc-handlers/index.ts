/**
 * IPC Handlers Module Index
 *
 * This module exports a single setup function that registers all IPC handlers
 * organized by domain into separate handler modules.
 */

import type { BrowserWindow } from 'electron';
import { AgentManager } from '../agent';
import { TerminalManager } from '../terminal-manager';
import { PythonEnvManager } from '../python-env-manager';

// Import all handler registration functions
import { registerProjectHandlers } from './project-handlers';
import { registerTaskHandlers } from './task-handlers';
import { registerTerminalHandlers } from './terminal-handlers';
import { registerAgenteventsHandlers } from './agent-events-handlers';
import { registerSettingsHandlers } from './settings-handlers';
import { registerFileHandlers } from './file-handlers';
import { registerRoadmapHandlers } from './roadmap-handlers';
import { registerContextHandlers } from './context-handlers';
import { registerEnvHandlers } from './env-handlers';
import { registerLinearHandlers } from './linear-handlers';
import { registerGithubHandlers } from './github-handlers';
import { registerGitlabHandlers } from './gitlab-handlers';
import { registerAutobuildSourceHandlers } from './autobuild-source-handlers';
import { registerIdeationHandlers } from './ideation-handlers';
import { registerChangelogHandlers } from './changelog-handlers';
import { registerInsightsHandlers } from './insights-handlers';
import { registerMemoryHandlers } from './memory-handlers';
import { registerAppUpdateHandlers } from './app-update-handlers';
import { setupAnalyticsHandlers } from './analytics-handlers';
import { setupROIHandlers } from './roi-handlers';
import { setupExportHandlers } from './export-handlers';
import { setupArtifactHandlers } from './artifact-handlers';
import { registerListSkillsHandler } from './skills/list-skills';
import { registerInstallSkillHandler } from './skills/install-skill';
import { registerRemoveSkillHandler } from './skills/remove-skill';
import { registerGetSkillContentHandler } from './skills/get-skill-content';
import { registerMCPHandlers } from '../mcp-manager';
import { registerDebugHandlers } from './debug-handlers';
import { registerClaudeCodeHandlers } from './claude-code-handlers';
import { registerMcpHandlers } from './mcp-handlers';
import { registerProfileHandlers } from './profile-handlers';
import { notificationService } from '../notification-service';
import { setupNotificationHandlers } from './notification-handlers';

/**
 * Setup all IPC handlers across all domains
 *
 * @param agentManager - The agent manager instance
 * @param terminalManager - The terminal manager instance
 * @param getMainWindow - Function to get the main BrowserWindow
 * @param pythonEnvManager - The Python environment manager instance
 */
export function setupIpcHandlers(
  agentManager: AgentManager,
  terminalManager: TerminalManager,
  getMainWindow: () => BrowserWindow | null,
  pythonEnvManager: PythonEnvManager
): void {
  // Initialize notification service
  notificationService.initialize(getMainWindow);

  // Project handlers (including Python environment setup)
  registerProjectHandlers(pythonEnvManager, agentManager, getMainWindow);

  // Task handlers
  registerTaskHandlers(agentManager, pythonEnvManager, getMainWindow);

  // Terminal and Claude profile handlers
  registerTerminalHandlers(terminalManager, getMainWindow);

  // Agent event handlers (event forwarding from agent manager to renderer)
  registerAgenteventsHandlers(agentManager, getMainWindow);

  // Settings and dialog handlers
  registerSettingsHandlers(agentManager, getMainWindow);

  // File explorer handlers
  registerFileHandlers();

  // Roadmap handlers
  registerRoadmapHandlers(agentManager, getMainWindow);

  // Context and memory handlers
  registerContextHandlers(getMainWindow);

  // Environment configuration handlers
  registerEnvHandlers(getMainWindow);

  // Linear integration handlers
  registerLinearHandlers(agentManager, getMainWindow);

  // GitHub integration handlers
  registerGithubHandlers(agentManager, getMainWindow);

  // GitLab integration handlers
  registerGitlabHandlers(agentManager, getMainWindow);

  // Auto-build source update handlers
  registerAutobuildSourceHandlers(getMainWindow);

  // Ideation handlers
  registerIdeationHandlers(agentManager, getMainWindow);

  // Changelog handlers
  registerChangelogHandlers(getMainWindow);

  // Insights handlers
  registerInsightsHandlers(getMainWindow);

  // Memory & infrastructure handlers (for Graphiti/LadybugDB)
  registerMemoryHandlers();

  // App auto-update handlers
  registerAppUpdateHandlers();

  // Analytics handlers
  setupAnalyticsHandlers(getMainWindow);

  // ROI handlers
  setupROIHandlers();

  // Export handlers
  setupExportHandlers();

  // Artifact storage handlers (for full artifact content retrieval)
  setupArtifactHandlers();

  // Skills management handlers
  registerListSkillsHandler();
  registerInstallSkillHandler();
  registerRemoveSkillHandler();
  registerGetSkillContentHandler();

  // MCP (Model Context Protocol) handlers
  registerMCPHandlers();

  // Notification handlers (for in-app notification center)
  setupNotificationHandlers();

  // Debug handlers (logs, debug info, etc.)
  registerDebugHandlers();

  // Claude Code CLI handlers (version checking, installation)
  registerClaudeCodeHandlers();

  // Note: MCP health check handlers (registerMcpHandlers) removed as registerMCPHandlers
  // already provides mcp:testConnection handler. MCP_CHECK_HEALTH can be added to mcp-manager if needed.

  // API Profile handlers (custom Anthropic-compatible endpoints)
  registerProfileHandlers();

  console.warn('[IPC] All handler modules registered successfully');
}

// Re-export all individual registration functions for potential custom usage
export {
  registerProjectHandlers,
  registerTaskHandlers,
  registerTerminalHandlers,
  registerAgenteventsHandlers,
  registerSettingsHandlers,
  registerFileHandlers,
  registerRoadmapHandlers,
  registerContextHandlers,
  registerEnvHandlers,
  registerLinearHandlers,
  registerGithubHandlers,
  registerGitlabHandlers,
  registerAutobuildSourceHandlers,
  registerIdeationHandlers,
  registerChangelogHandlers,
  registerInsightsHandlers,
  registerMemoryHandlers,
  registerAppUpdateHandlers,
  setupAnalyticsHandlers,
  setupROIHandlers,
  setupExportHandlers,
  setupArtifactHandlers,
  registerListSkillsHandler,
  registerInstallSkillHandler,
  registerRemoveSkillHandler,
  registerGetSkillContentHandler,
  registerMCPHandlers,
  setupNotificationHandlers,
  registerDebugHandlers,
  registerClaudeCodeHandlers,
  registerMcpHandlers,
  registerProfileHandlers
};
