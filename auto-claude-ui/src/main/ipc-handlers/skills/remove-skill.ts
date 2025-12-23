import { ipcMain } from 'electron'
import { rm, stat } from 'fs/promises'
import { resolve, normalize, relative } from 'path'
import { homedir } from 'os'
import { IPC_CHANNELS } from '../../../shared/constants/ipc'
import type { IPCResult } from '../../../shared/types'

// Validate skillPath to prevent path traversal and ensure it's a valid skill directory
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
  const isInUserSkills = absolutePath.startsWith(userSkillsPath + '/')

  // If in user skills, validate it's a subdirectory (not the skills root itself)
  if (absolutePath === userSkillsPath) {
    throw new Error('Cannot remove the entire skills directory')
  }

  // Validate this is a skill subdirectory, not just the .claude/skills root
  const skillsPattern = /\/\.claude\/skills\/.+/
  if (!skillsPattern.test(absolutePath)) {
    throw new Error('Invalid skill path: must point to a skill subdirectory within .claude/skills')
  }
}

/**
 * Registers the IPC handler for removing (deleting) skill directories.
 *
 * This handler provides secure removal of skill directories with strict path validation
 * to prevent unauthorized file system access or deletion outside allowed directories.
 *
 * Security Model:
 * - Only allows deletion within .claude/skills directories
 * - Validates paths are in one of these allowed locations:
 *   - ~/.claude/skills/{skill-name}/ (user skills)
 *   - {project}/.claude/skills/{skill-name}/ (project skills)
 *   - {project}/auto-claude/.claude/skills/{skill-name}/ (auto-claude specific)
 * - Prevents path traversal attacks via normalization checks
 * - Rejects paths outside .claude/skills pattern
 * - Prevents removal of the skills directory root itself
 * - Enforces maximum path length (1024 characters)
 *
 * @returns {void}
 *
 * @example
 * Valid paths:
 * - /Users/name/.claude/skills/my-skill
 * - /project/.claude/skills/project-skill
 * - /project/auto-claude/.claude/skills/auto-skill
 *
 * @example
 * Invalid paths (will be rejected):
 * - /Users/name/.claude/skills (root directory)
 * - /Users/name/skills/my-skill (not in .claude/skills)
 * - /etc/passwd (not a skills directory)
 * - ~/.claude/skills/../../../etc (path traversal)
 */
export function registerRemoveSkillHandler(): void {
  ipcMain.handle(IPC_CHANNELS.SKILLS_REMOVE, async (_, skillPath: string): Promise<IPCResult<void>> => {
    try {
      // Validate input
      await validateSkillPath(skillPath)

      // Remove the skill directory recursively
      await rm(skillPath, { recursive: true, force: true })

      console.log('[remove-skill] Successfully removed skill:', skillPath)

      return {
        success: true
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      console.error('[remove-skill] Error removing skill:', errorMessage, error)
      return {
        success: false,
        error: errorMessage
      }
    }
  })
}
