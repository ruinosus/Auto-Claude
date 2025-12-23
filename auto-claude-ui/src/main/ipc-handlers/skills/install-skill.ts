import { ipcMain } from 'electron'
import { exec } from 'child_process'
import { promisify } from 'util'
import { IPC_CHANNELS } from '../../../shared/constants/ipc'

const execAsync = promisify(exec)

export interface InstallSkillResult {
  success: boolean
  output?: string
  error?: string
}

export function registerInstallSkillHandler(): void {
  ipcMain.handle(IPC_CHANNELS.SKILLS_INSTALL, async (_, skillPath: string): Promise<InstallSkillResult> => {
    try {
      const command = `npx claude-code-templates@latest --skill ${skillPath} --yes`

      const { stdout, stderr } = await execAsync(command, {
        timeout: 60000, // 60 second timeout
        maxBuffer: 1024 * 1024 * 10 // 10MB buffer
      })

      return {
        success: true,
        output: stdout + stderr
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  })
}
