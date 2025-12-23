import { ipcMain } from 'electron'
import { readdir, readFile, stat } from 'fs/promises'
import { join } from 'path'
import { homedir } from 'os'
import { IPC_CHANNELS } from '../../../shared/constants/ipc'

export interface Skill {
  name: string
  description: string
  source: 'user' | 'project'
  path: string
  category?: string
  version?: string
}

interface SkillMetadata {
  name: string
  description: string
  category?: string
  version?: string
  license?: string
  tags?: string[]
}

async function parseSkillMetadata(skillMdPath: string): Promise<SkillMetadata | null> {
  try {
    const content = await readFile(skillMdPath, 'utf-8')

    // Extract frontmatter between --- markers
    const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/)
    if (!frontmatterMatch) return null

    const frontmatter = frontmatterMatch[1]
    const metadata: Partial<SkillMetadata> = {}

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
      else if (trimmedKey === 'license') metadata.license = value
    }

    return metadata.name && metadata.description
      ? metadata as SkillMetadata
      : null
  } catch (error) {
    console.error(`Error parsing skill metadata from ${skillMdPath}:`, error)
    return null
  }
}

async function scanSkillsDirectory(
  dirPath: string,
  source: 'user' | 'project'
): Promise<Skill[]> {
  const skills: Skill[] = []

  try {
    const entries = await readdir(dirPath, { withFileTypes: true })

    for (const entry of entries) {
      if (!entry.isDirectory()) continue

      const skillPath = join(dirPath, entry.name)
      const skillMdPath = join(skillPath, 'SKILL.md')

      try {
        await stat(skillMdPath)
        const metadata = await parseSkillMetadata(skillMdPath)

        if (metadata) {
          skills.push({
            name: metadata.name,
            description: metadata.description,
            source,
            path: skillPath,
            category: metadata.category,
            version: metadata.version
          })
        }
      } catch (error: unknown) {
        // Expected: SKILL.md doesn't exist (ENOENT) - skip silently
        // Unexpected: Permission denied, corrupted file, etc. - log warning
        if (error && typeof error === 'object' && 'code' in error && error.code === 'ENOENT') {
          // Expected case: SKILL.md doesn't exist, skip silently
          continue
        } else {
          console.warn(`Unexpected error reading skill at ${skillPath}:`, error)
          continue
        }
      }
    }
  } catch (error: unknown) {
    // Expected: Directory doesn't exist (ENOENT) - return empty array silently
    // Unexpected: Permission denied, etc. - log warning
    if (error && typeof error === 'object' && 'code' in error && error.code === 'ENOENT') {
      // Expected case: skills directory doesn't exist yet
      return []
    } else {
      console.warn(`Unexpected error scanning skills directory ${dirPath}:`, error)
      return []
    }
  }

  return skills
}

export function registerListSkillsHandler(): void {
  ipcMain.handle(IPC_CHANNELS.SKILLS_LIST, async (_, projectPath?: string) => {
    const userSkillsPath = join(homedir(), '.claude', 'skills')
    const skills: Skill[] = []

    // Scan user skills
    const userSkills = await scanSkillsDirectory(userSkillsPath, 'user')
    skills.push(...userSkills)

    // Scan project skills if projectPath provided
    if (projectPath) {
      const projectSkillsPath = join(projectPath, '.claude', 'skills')
      const projectSkills = await scanSkillsDirectory(projectSkillsPath, 'project')
      skills.push(...projectSkills)

      // Also check auto-claude/.claude/skills (where npx installs when run from auto-claude/)
      const autoClaudeSkillsPath = join(projectPath, 'auto-claude', '.claude', 'skills')
      const autoClaudeSkills = await scanSkillsDirectory(autoClaudeSkillsPath, 'project')
      skills.push(...autoClaudeSkills)
    }

    return skills
  })
}
