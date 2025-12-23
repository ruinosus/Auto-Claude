import { ipcMain } from 'electron'
import { readFile, stat } from 'fs/promises'
import { join, resolve, normalize } from 'path'
import { homedir } from 'os'
import { IPC_CHANNELS } from '../../../shared/constants/ipc'
import type { IPCResult, SkillContent } from '../../../shared/types'

/**
 * Validates skillPath to prevent path traversal and ensure it's a valid skill directory.
 * Reuses validation logic from remove-skill.ts.
 *
 * @param skillPath - The path to validate
 * @throws {Error} If path is invalid, contains traversal, or is outside allowed directories
 */
async function validateSkillPath(skillPath: string): Promise<void> {
  // Check not empty
  if (!skillPath || skillPath.trim().length === 0) {
    throw new Error('Skill path cannot be empty')
  }

  // Check length limit
  if (skillPath.length >= 1024) {
    throw new Error('Skill path too long (max 1024 characters)')
  }

  // Resolve to absolute path and normalize
  const absolutePath = resolve(skillPath)
  const normalizedPath = normalize(absolutePath)

  // Ensure the path matches after normalization (prevents path traversal)
  if (absolutePath !== normalizedPath) {
    throw new Error('Invalid skill path: path traversal detected')
  }

  // Check if path exists
  try {
    const stats = await stat(absolutePath)
    if (!stats.isDirectory()) {
      throw new Error('Skill path must be a directory')
    }
  } catch (error: unknown) {
    if (error && typeof error === 'object' && 'code' in error && error.code === 'ENOENT') {
      throw new Error('Skill path does not exist')
    }
    throw error
  }

  // Validate that the path is within allowed skill directories
  // Allowed locations:
  // - ~/.claude/skills/ (user skills)
  // - {project}/.claude/skills/ (project skills)
  // - {project}/auto-claude/.claude/skills/ (auto-claude specific skills)

  // Must contain the specific .claude/skills pattern
  if (!absolutePath.includes('/.claude/skills')) {
    throw new Error('Invalid skill path: must be within a .claude/skills directory')
  }

  // Additional validation: ensure not at root of .claude/skills
  const userSkillsPath = resolve(homedir(), '.claude', 'skills')

  // If in user skills, validate it's a subdirectory (not the skills root itself)
  if (absolutePath === userSkillsPath) {
    throw new Error('Cannot access the entire skills directory')
  }

  // Validate this is a skill subdirectory, not just the .claude/skills root
  const skillsPattern = /\/\.claude\/skills\/.+/
  if (!skillsPattern.test(absolutePath)) {
    throw new Error('Invalid skill path: must point to a skill subdirectory within .claude/skills')
  }
}

/**
 * Parses skill metadata from SKILL.md frontmatter.
 * Extracts name, description, category, and version from YAML-like frontmatter.
 *
 * @param content - The full SKILL.md content
 * @returns Parsed metadata or null if no valid frontmatter found
 */
function parseSkillMetadata(content: string): Pick<SkillContent, 'name' | 'description' | 'category' | 'version'> | null {
  try {
    // Extract frontmatter between --- markers
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/)
    if (!frontmatterMatch) return null

    const frontmatter = frontmatterMatch[1]
    const metadata: Partial<SkillContent> = {}

    // Parse YAML-like frontmatter
    const lines = frontmatter.split('\n')
    for (const line of lines) {
      const [key, ...valueParts] = line.split(':')
      const trimmedKey = key?.trim()
      const value = valueParts.join(':').trim()

      // Skip empty keys or values
      if (!trimmedKey || !value) continue

      if (trimmedKey === 'name') metadata.name = value
      else if (trimmedKey === 'description') metadata.description = value
      else if (trimmedKey === 'category') metadata.category = value
      else if (trimmedKey === 'version') metadata.version = value
    }

    return metadata.name && metadata.description
      ? (metadata as Pick<SkillContent, 'name' | 'description' | 'category' | 'version'>)
      : null
  } catch (error) {
    console.error('Error parsing skill metadata:', error)
    return null
  }
}

/**
 * Registers the IPC handler for retrieving skill content.
 *
 * This handler provides secure access to SKILL.md files with strict path validation
 * to prevent unauthorized file system access outside allowed directories.
 *
 * Security Model:
 * - Only allows reading files within .claude/skills directories
 * - Validates paths are in one of these allowed locations:
 *   - ~/.claude/skills/{skill-name}/ (user skills)
 *   - {project}/.claude/skills/{skill-name}/ (project skills)
 *   - {project}/auto-claude/.claude/skills/{skill-name}/ (auto-claude specific)
 * - Prevents path traversal attacks via normalization checks
 * - Rejects paths outside .claude/skills pattern
 * - Enforces maximum path length (1024 characters)
 * - Only reads SKILL.md files (not arbitrary files)
 *
 * Returns:
 * - IPCResult<SkillContent> with:
 *   - content: Full SKILL.md file content
 *   - name: Skill name from metadata
 *   - description: Optional description from metadata
 *   - category: Optional category from metadata
 *   - version: Optional version from metadata
 *
 * @example
 * Valid usage:
 * ```typescript
 * const result = await window.api.skills.getContent('/Users/name/.claude/skills/my-skill')
 * if (result.success) {
 *   console.log(result.data.content) // Full SKILL.md content
 *   console.log(result.data.name)    // Skill name
 * }
 * ```
 *
 * @example
 * Invalid paths (will be rejected):
 * - /Users/name/.claude/skills (root directory)
 * - /Users/name/docs/README.md (not a skills directory)
 * - /etc/passwd (not a skills directory)
 * - ~/.claude/skills/../../../etc (path traversal)
 */
export function registerGetSkillContentHandler(): void {
  ipcMain.handle(IPC_CHANNELS.SKILLS_GET_CONTENT, async (_, skillPath: string): Promise<IPCResult<SkillContent>> => {
    try {
      // Validate input path
      await validateSkillPath(skillPath)

      // Read SKILL.md file
      const skillMdPath = join(skillPath, 'SKILL.md')

      let content: string
      try {
        content = await readFile(skillMdPath, 'utf-8')
      } catch (error: unknown) {
        if (error && typeof error === 'object' && 'code' in error && error.code === 'ENOENT') {
          throw new Error('SKILL.md file not found in skill directory')
        }
        throw new Error(`Failed to read SKILL.md: ${error instanceof Error ? error.message : 'Unknown error'}`)
      }

      // Parse metadata from frontmatter
      const metadata = parseSkillMetadata(content)

      if (!metadata) {
        throw new Error('Invalid SKILL.md: missing or invalid frontmatter with name and description')
      }

      console.log('[get-skill-content] Successfully read skill content:', skillPath)

      const skillContent: SkillContent = {
        content,
        name: metadata.name,
        description: metadata.description,
        category: metadata.category,
        version: metadata.version
      }

      return {
        success: true,
        data: skillContent
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      console.error('[get-skill-content] Error reading skill content:', errorMessage, error)
      return {
        success: false,
        error: errorMessage
      }
    }
  })
}
