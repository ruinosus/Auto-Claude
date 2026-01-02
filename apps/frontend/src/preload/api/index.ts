import { ProjectAPI, createProjectAPI } from './project-api';
import { TerminalAPI, createTerminalAPI } from './terminal-api';
import { TaskAPI, createTaskAPI } from './task-api';
import { SettingsAPI, createSettingsAPI } from './settings-api';
import { FileAPI, createFileAPI } from './file-api';
import { AgentAPI, createAgentAPI } from './agent-api';
import { IdeationAPI, createIdeationAPI } from './modules/ideation-api';
import { InsightsAPI, createInsightsAPI } from './modules/insights-api';
import { AppUpdateAPI, createAppUpdateAPI } from './app-update-api';
import { GitHubAPI, createGitHubAPI } from './modules/github-api';
import { GitLabAPI, createGitLabAPI } from './modules/gitlab-api';
import { SkillsAPI, createSkillsAPI } from './modules/skills-api';
import { MCPAPI, createMCPAPI } from './modules/mcp-api';
import { ROIAPI, createROIAPI } from './modules/roi-api';
import { NotificationAPI, createNotificationAPI } from './modules/notification-api';
import { ExportAPI, createExportAPI } from './modules/export-api';
import { DebugAPI, createDebugAPI } from './modules/debug-api';
import { ClaudeCodeAPI, createClaudeCodeAPI } from './modules/claude-code-api';
import { McpAPI, createMcpAPI } from './modules/mcp-api';
import { ArtifactAPI, createArtifactAPI } from './modules/artifact-api';
import { ProfileAPI, createProfileAPI } from './profile-api';

export interface ElectronAPI extends
  ProjectAPI,
  TerminalAPI,
  TaskAPI,
  SettingsAPI,
  FileAPI,
  AgentAPI,
  IdeationAPI,
  InsightsAPI,
  AppUpdateAPI,
  GitLabAPI,
  SkillsAPI,
  MCPAPI,
  ROIAPI,
  NotificationAPI,
  ExportAPI,
  DebugAPI,
  ClaudeCodeAPI,
  McpAPI,
  ArtifactAPI,
  ProfileAPI {
  github: GitHubAPI;
}

export const createElectronAPI = (): ElectronAPI => ({
  ...createProjectAPI(),
  ...createTerminalAPI(),
  ...createTaskAPI(),
  ...createSettingsAPI(),
  ...createFileAPI(),
  ...createAgentAPI(),
  ...createIdeationAPI(),
  ...createInsightsAPI(),
  ...createAppUpdateAPI(),
  ...createGitLabAPI(),
  ...createSkillsAPI(),
  ...createMCPAPI(),
  ...createROIAPI(),
  ...createNotificationAPI(),
  ...createExportAPI(),
  ...createDebugAPI(),
  ...createClaudeCodeAPI(),
  ...createMcpAPI(),
  ...createArtifactAPI(),
  ...createProfileAPI(),
  github: createGitHubAPI()
});

// Export individual API creators for potential use in tests or specialized contexts
export {
  createProjectAPI,
  createTerminalAPI,
  createTaskAPI,
  createSettingsAPI,
  createFileAPI,
  createAgentAPI,
  createIdeationAPI,
  createInsightsAPI,
  createAppUpdateAPI,
  createProfileAPI,
  createGitHubAPI,
  createGitLabAPI,
  createSkillsAPI,
  createMCPAPI,
  createROIAPI,
  createNotificationAPI,
  createExportAPI,
  createDebugAPI,
  createClaudeCodeAPI,
  createMcpAPI,
  createArtifactAPI
};

export type {
  ProjectAPI,
  TerminalAPI,
  TaskAPI,
  SettingsAPI,
  FileAPI,
  AgentAPI,
  IdeationAPI,
  InsightsAPI,
  AppUpdateAPI,
  ProfileAPI,
  GitHubAPI,
  GitLabAPI,
  SkillsAPI,
  MCPAPI,
  ROIAPI,
  NotificationAPI,
  ExportAPI,
  DebugAPI,
  ClaudeCodeAPI,
  McpAPI,
  ArtifactAPI
};
