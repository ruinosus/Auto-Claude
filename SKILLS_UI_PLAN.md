# Skills Manager UI - Implementation Plan

## Overview
Add Skills management interface to Auto-Claude UI (Phase 2 of Skills integration).

## Architecture

### Backend (Main Process)

**Location:** `auto-claude-ui/src/main/ipc-handlers/skills/`

#### IPC Handlers

1. **list-skills.ts** - List installed skills
```typescript
import { ipcMain } from 'electron'
import { readdir, readFile } from 'fs/promises'
import { join } from 'path'
import { homedir } from 'os'

interface Skill {
  name: string
  description: string
  source: 'user' | 'project'
  path: string
  enabled: boolean
}

ipcMain.handle('skills:list', async (_, projectPath?: string) => {
  const userSkillsPath = join(homedir(), '.claude', 'skills')
  const projectSkillsPath = projectPath
    ? join(projectPath, '.claude', 'skills')
    : null

  const skills: Skill[] = []

  // Scan user skills
  const userSkills = await scanSkillsDirectory(userSkillsPath, 'user')
  skills.push(...userSkills)

  // Scan project skills
  if (projectSkillsPath) {
    const projectSkills = await scanSkillsDirectory(projectSkillsPath, 'project')
    skills.push(...projectSkills)
  }

  return skills
})

async function scanSkillsDirectory(path: string, source: 'user' | 'project'): Promise<Skill[]> {
  // Implementation to read SKILL.md files and parse metadata
  // Returns array of Skill objects
}
```

2. **install-skill.ts** - Install skill from marketplace
```typescript
import { ipcMain } from 'electron'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

ipcMain.handle('skills:install', async (_, skillPath: string) => {
  // Execute: npx claude-code-templates@latest --skill {skillPath} --yes
  const { stdout, stderr } = await execAsync(
    `npx claude-code-templates@latest --skill ${skillPath} --yes`
  )

  return { success: true, output: stdout }
})
```

3. **remove-skill.ts** - Remove installed skill
```typescript
import { ipcMain } from 'electron'
import { rm } from 'fs/promises'

ipcMain.handle('skills:remove', async (_, skillPath: string) => {
  await rm(skillPath, { recursive: true })
  return { success: true }
})
```

4. **get-skill-content.ts** - Read SKILL.md content
```typescript
import { ipcMain } from 'electron'
import { readFile } from 'fs/promises'
import { join } from 'path'

ipcMain.handle('skills:get-content', async (_, skillPath: string) => {
  const content = await readFile(join(skillPath, 'SKILL.md'), 'utf-8')
  return content
})
```

5. **browse-marketplace.ts** - Fetch available skills
```typescript
import { ipcMain } from 'electron'

interface MarketplaceSkill {
  name: string
  description: string
  category: string
  path: string // e.g., "creative-design/frontend-design"
  installed: boolean
}

ipcMain.handle('skills:browse-marketplace', async () => {
  // Could fetch from aitmpl.com API or use hardcoded list
  // For now, return categories from claude-code-templates
  return {
    categories: [
      {
        name: 'development',
        count: 52,
        skills: [
          { name: 'test-driven-development', description: '...', path: 'development/test-driven-development' },
          { name: 'systematic-debugging', description: '...', path: 'development/systematic-debugging' },
          // ...
        ]
      },
      {
        name: 'creative-design',
        count: 9,
        skills: [
          { name: 'frontend-design', description: '...', path: 'creative-design/frontend-design' },
          // ...
        ]
      },
      // ... more categories
    ]
  }
})
```

### Frontend (Renderer Process)

**Location:** `auto-claude-ui/src/renderer/components/skills/`

#### Main Component: SkillsManager.tsx

```tsx
import { useState, useEffect } from 'react'
import { Package, Download, Trash2, Eye, Search } from 'lucide-react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { SkillCard } from './SkillCard'
import { SkillsMarketplace } from './SkillsMarketplace'
import { SkillPreview } from './SkillPreview'

interface Skill {
  name: string
  description: string
  source: 'user' | 'project'
  path: string
  enabled: boolean
}

export function SkillsManager() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null)
  const [showMarketplace, setShowMarketplace] = useState(false)

  useEffect(() => {
    loadSkills()
  }, [])

  const loadSkills = async () => {
    setLoading(true)
    const installedSkills = await window.api.skills.list()
    setSkills(installedSkills)
    setLoading(false)
  }

  const handleInstall = async (skillPath: string) => {
    await window.api.skills.install(skillPath)
    await loadSkills()
  }

  const handleRemove = async (skillPath: string) => {
    await window.api.skills.remove(skillPath)
    await loadSkills()
  }

  const filteredSkills = skills.filter(skill =>
    skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    skill.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Package className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Skills Manager</h2>
        </div>
        <Button onClick={() => setShowMarketplace(true)}>
          <Download className="h-4 w-4 mr-2" />
          Browse Marketplace
        </Button>
      </div>

      {/* Search */}
      <div className="p-4 border-b">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search skills..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Skills List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="text-center py-8 text-muted-foreground">
            Loading skills...
          </div>
        ) : filteredSkills.length === 0 ? (
          <div className="text-center py-8">
            <Package className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">No skills installed</p>
            <Button onClick={() => setShowMarketplace(true)} className="mt-4">
              Browse Marketplace
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSkills.map((skill) => (
              <SkillCard
                key={skill.path}
                skill={skill}
                onPreview={() => setSelectedSkill(skill)}
                onRemove={() => handleRemove(skill.path)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Marketplace Modal */}
      {showMarketplace && (
        <SkillsMarketplace
          onClose={() => setShowMarketplace(false)}
          onInstall={handleInstall}
          installedSkills={skills}
        />
      )}

      {/* Preview Modal */}
      {selectedSkill && (
        <SkillPreview
          skill={selectedSkill}
          onClose={() => setSelectedSkill(null)}
        />
      )}
    </div>
  )
}
```

#### SkillCard.tsx

```tsx
import { Eye, Trash2, Package } from 'lucide-react'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'

interface SkillCardProps {
  skill: {
    name: string
    description: string
    source: 'user' | 'project'
    enabled: boolean
  }
  onPreview: () => void
  onRemove: () => void
}

export function SkillCard({ skill, onPreview, onRemove }: SkillCardProps) {
  return (
    <div className="border rounded-lg p-4 hover:border-primary transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Package className="h-5 w-5 text-primary" />
          <h3 className="font-semibold">{skill.name}</h3>
        </div>
        <Badge variant={skill.source === 'user' ? 'default' : 'secondary'}>
          {skill.source}
        </Badge>
      </div>

      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
        {skill.description}
      </p>

      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={onPreview} className="flex-1">
          <Eye className="h-4 w-4 mr-2" />
          Preview
        </Button>
        <Button variant="destructive" size="sm" onClick={onRemove}>
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
```

#### SkillsMarketplace.tsx

```tsx
import { useState, useEffect } from 'react'
import { X, Download, Check, Search } from 'lucide-react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Badge } from '../ui/badge'

interface MarketplaceSkill {
  name: string
  description: string
  category: string
  path: string
  installed: boolean
}

interface SkillsMarketplaceProps {
  onClose: () => void
  onInstall: (skillPath: string) => Promise<void>
  installedSkills: Array<{ name: string }>
}

export function SkillsMarketplace({ onClose, onInstall, installedSkills }: SkillsMarketplaceProps) {
  const [skills, setSkills] = useState<MarketplaceSkill[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [installing, setInstalling] = useState<string | null>(null)

  useEffect(() => {
    loadMarketplace()
  }, [])

  const loadMarketplace = async () => {
    const data = await window.api.skills.browseMarketplace()
    // Flatten categories into skills array
    const allSkills = data.categories.flatMap(cat =>
      cat.skills.map(s => ({
        ...s,
        category: cat.name,
        installed: installedSkills.some(is => is.name === s.name)
      }))
    )
    setSkills(allSkills)
  }

  const handleInstall = async (skillPath: string) => {
    setInstalling(skillPath)
    await onInstall(skillPath)
    setInstalling(null)
    await loadMarketplace()
  }

  const filteredSkills = skills.filter(skill => {
    const matchesSearch = skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          skill.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = !selectedCategory || skill.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  const categories = Array.from(new Set(skills.map(s => s.category)))

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background rounded-lg shadow-xl w-[90vw] h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold">Skills Marketplace</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Search & Filters */}
        <div className="p-4 border-b space-y-4">
          <Input
            placeholder="Search 247+ skills..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <div className="flex gap-2 flex-wrap">
            <Badge
              variant={!selectedCategory ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => setSelectedCategory(null)}
            >
              All
            </Badge>
            {categories.map(cat => (
              <Badge
                key={cat}
                variant={selectedCategory === cat ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => setSelectedCategory(cat)}
              >
                {cat}
              </Badge>
            ))}
          </div>
        </div>

        {/* Skills Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSkills.map((skill) => (
              <div key={skill.path} className="border rounded-lg p-4">
                <h3 className="font-semibold mb-1">{skill.name}</h3>
                <Badge variant="secondary" className="mb-2">{skill.category}</Badge>
                <p className="text-sm text-muted-foreground mb-4 line-clamp-3">
                  {skill.description}
                </p>
                <Button
                  size="sm"
                  className="w-full"
                  disabled={skill.installed || installing === skill.path}
                  onClick={() => handleInstall(skill.path)}
                >
                  {installing === skill.path ? (
                    <>Installing...</>
                  ) : skill.installed ? (
                    <>
                      <Check className="h-4 w-4 mr-2" />
                      Installed
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4 mr-2" />
                      Install
                    </>
                  )}
                </Button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
```

### Integration

Add to Settings or create dedicated Skills tab:

**Location:** `auto-claude-ui/src/renderer/components/settings/SettingsModal.tsx`

```tsx
import { SkillsManager } from '../skills/SkillsManager'

// Add tab
const tabs = [
  { id: 'general', label: 'General' },
  { id: 'integrations', label: 'Integrations' },
  { id: 'skills', label: 'Skills' },  // ← NEW
  // ...
]

// Add content
{selectedTab === 'skills' && <SkillsManager />}
```

## Summary

**What needs to be implemented:**

1. ✅ **5 IPC Handlers** (Backend - Main Process)
   - list-skills.ts
   - install-skill.ts
   - remove-skill.ts
   - get-skill-content.ts
   - browse-marketplace.ts

2. ✅ **4 React Components** (Frontend - Renderer)
   - SkillsManager.tsx
   - SkillCard.tsx
   - SkillsMarketplace.tsx
   - SkillPreview.tsx

3. ✅ **Type Definitions**
   - Add to preload API types
   - Skill interfaces

4. ✅ **Integration**
   - Add to Settings modal
   - Add menu item

**Estimated Complexity:** 4-6 hours of development

**Would you like me to implement this now?**
