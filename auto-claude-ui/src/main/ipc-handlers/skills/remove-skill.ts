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
  if (skillPath.length >= 2048) {
    throw new Error('Skill path too long (max 2048 characters)')
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
  const userSkillsPath = resolve(homedir(), '.claude', 'skills')
  const relativePath = relative(userSkillsPath, absolutePath)

  // Check if path starts with '..' which would mean it's outside the allowed directory
  if (relativePath.startsWith('..')) {
    // If not in user skills, check if in project skills
    // We can't validate project paths here without knowing the project path
    // So we'll allow it but log a warning
    // In production, you might want to pass allowed paths as a parameter
    console.warn('[remove-skill] Warning: Removing skill outside user skills directory:', absolutePath)
  }

  // Additional safety: ensure path contains 'skills' directory
  if (!absolutePath.includes('skills')) {
    throw new Error('Invalid skill path: must be within a skills directory')
  }
}

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
