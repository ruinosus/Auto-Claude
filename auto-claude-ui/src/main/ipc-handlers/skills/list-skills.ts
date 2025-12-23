import { ipcMain } from 'electron'
import { readdir, readFile, stat } from 'fs/promises'
import { join } from 'path'
import { homedir } from 'os'

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
      const value = valueParts.join(':').trim()

      if (key && value) {
        if (key === 'name') metadata.name = value
        else if (key === 'description') metadata.description = value
        else if (key === 'category') metadata.category = value
        else if (key === 'version') metadata.version = value
        else if (key === 'license') metadata.license = value
      }
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
      } catch {
        // SKILL.md doesn't exist or can't be read, skip this directory
        continue
      }
    }
  } catch (error) {
    // Directory doesn't exist, return empty array
    return []
  }

  return skills
}

export function registerListSkillsHandler(): void {
  ipcMain.handle('skills:list', async (_, projectPath?: string) => {
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
