/**
 * Skills-related TypeScript types
 */

/**
 * Skill metadata from SKILL.md frontmatter
 */
export interface Skill {
  name: string
  description: string
  source: 'user' | 'project'
  path: string
  category?: string
  version?: string
}

/**
 * Skill content including the full SKILL.md content and metadata
 */
export interface SkillContent {
  content: string
  name: string
  description?: string
  category?: string
  version?: string
}

/**
 * Output data from skill installation operation
 */
export interface SkillInstallOutput {
  output: string
}

/**
 * Result of skill installation operation
 * @deprecated Use IPCResult<SkillInstallOutput> instead
 */
export interface InstallSkillResult {
  success: boolean
  output?: string
  error?: string
}
