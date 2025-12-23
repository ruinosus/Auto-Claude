import { ipcMain } from 'electron'
import { execFile } from 'child_process'
import { promisify } from 'util'
import { IPC_CHANNELS } from '../../../shared/constants/ipc'
import type { IPCResult } from '../../../shared/types'

const execFileAsync = promisify(execFile)

// Output interface for skill installation
export interface SkillInstallOutput {
  output: string
}

// Validate skillPath to prevent command injection
function validateSkillPath(skillPath: string): void {
  // Check not empty
  if (!skillPath || skillPath.trim().length === 0) {
    throw new Error('Skill path cannot be empty')
  }

  // Check length limit
  if (skillPath.length >= 1024) {
    throw new Error('Skill path too long (max 1024 characters)')
  }

  // Validate format - allow alphanumeric, dash, underscore, dot, and forward slash
  const validPathRegex = /^[\w\-\.\/]+$/
  if (!validPathRegex.test(skillPath)) {
    throw new Error('Invalid skill path format. Only alphanumeric characters, dash, underscore, dot, and forward slash are allowed.')
  }
}

export function registerInstallSkillHandler(): void {
  ipcMain.handle(IPC_CHANNELS.SKILLS_INSTALL, async (_, skillPath: string): Promise<IPCResult<SkillInstallOutput>> => {
    try {
      // Validate input
      validateSkillPath(skillPath)

      // Use execFile instead of exec to prevent command injection
      // Pass arguments as array instead of concatenating into shell command
      const { stdout, stderr } = await execFileAsync('npx',
        ['claude-code-templates@latest', '--skill', skillPath, '--yes'],
        {
          timeout: 60000, // 60 second timeout
          maxBuffer: 1024 * 1024 * 10 // 10MB buffer
        }
      )

      return {
        success: true,
        data: {
          output: stdout + stderr
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      console.error('[install-skill] Error installing skill:', errorMessage, error)
      return {
        success: false,
        error: errorMessage
      }
    }
  })
}
