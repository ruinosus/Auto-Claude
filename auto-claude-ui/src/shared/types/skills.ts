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
 * Result of skill installation operation
 */
export interface InstallSkillResult {
  success: boolean
  output?: string
  error?: string
}
