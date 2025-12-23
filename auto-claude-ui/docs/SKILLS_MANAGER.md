# Skills Manager - Technical Documentation

This document provides technical details about the Skills Manager UI implementation in Auto-Claude.

## Architecture Overview

The Skills Manager is a full-stack feature that spans Electron's main process, IPC layer, and React renderer process.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Renderer Process (React)                  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            SkillsManager (Main Component)             │  │
│  │  - State management (useState, useEffect)             │  │
│  │  - Project integration (useProjectStore)              │  │
│  │  - Orchestrates child components                      │  │
│  └───────────────────┬──────────────────────────────────┘  │
│                      │                                       │
│      ┌───────────────┼───────────────┐                      │
│      │               │               │                      │
│  ┌───▼────┐   ┌─────▼──────┐   ┌───▼────────┐             │
│  │SkillCard│   │SkillPreview│   │Marketplace │             │
│  └─────────┘   └────────────┘   └────────────┘             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ IPC Calls via electronAPI
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Preload Script                            │
│  - Exposes window.electronAPI.skills.*                       │
│  - Type-safe IPC bridge                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Main Process (Node.js)                     │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          IPC Handlers (skills/*)                       │ │
│  │  - list-skills.ts    → Scan directories               │ │
│  │  - install-skill.ts  → Execute npx command            │ │
│  │  - remove-skill.ts   → Delete directories             │ │
│  │  - get-skill-content.ts → Read SKILL.md files         │ │
│  └─────────────────────────┬──────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│                    Filesystem / OS                           │
│              ~/.claude/skills/                               │
│              .claude/skills/                                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Hierarchy

### SkillsManager (Main Component)

**Location:** `src/renderer/components/skills/SkillsManager.tsx`

**Responsibilities:**
- Fetch and display installed skills
- Manage component state (loading, refreshing, search)
- Handle skill installation and removal
- Coordinate child components (cards, marketplace, preview)

**State:**
```typescript
const [skills, setSkills] = useState<Skill[]>([])
const [loading, setLoading] = useState(true)
const [refreshing, setRefreshing] = useState(false)
const [searchQuery, setSearchQuery] = useState('')
const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null)
const [showMarketplace, setShowMarketplace] = useState(false)
```

**Key Methods:**
- `loadSkills()`: Fetch skills from main process
- `handleRefresh()`: Reload skills list
- `handleInstall(skillPath)`: Install skill from marketplace
- `handleRemove(skillPath)`: Delete skill from filesystem

**Integration:**
- Uses `useProjectStore` to get current project path
- Passes project path to IPC handler for project-specific skills
- Filters skills based on search query

### SkillCard Component

**Location:** `src/renderer/components/skills/SkillCard.tsx`

**Purpose:** Display individual skill information in a card format

**Props:**
```typescript
interface SkillCardProps {
  skill: Skill
  onPreview: () => void
  onRemove: () => void
}
```

**Features:**
- Displays skill name, description, category
- Shows source badge (user/project)
- Preview button to view SKILL.md content
- Remove button with trash icon

### SkillPreview Component

**Location:** `src/renderer/components/skills/SkillPreview.tsx`

**Purpose:** Full-screen modal to display SKILL.md content

**Props:**
```typescript
interface SkillPreviewProps {
  skill: Skill
  onClose: () => void
}
```

**Features:**
- Fetches skill content via IPC on mount
- Displays metadata (name, category, version, source)
- Shows raw markdown in preformatted text
- Loading state while fetching content

**Data Flow:**
1. Component mounts → calls `window.electronAPI.skills.getContent(skill.path)`
2. Main process reads SKILL.md file
3. Content displayed in modal

### SkillsMarketplace Component

**Location:** `src/renderer/components/skills/SkillsMarketplace.tsx`

**Purpose:** Browse and install skills from claude-code-templates

**Props:**
```typescript
interface SkillsMarketplaceProps {
  onClose: () => void
  onInstall: (skillPath: string) => Promise<void>
  installedSkills: Skill[]
}
```

**Features:**
- Hardcoded marketplace data (247+ skills)
- Category filtering
- Search functionality
- Installation status tracking
- Shows "Installed" badge for already-installed skills

**Marketplace Data:**
- Located in `marketplace-data.ts`
- Contains categories and sample skills
- Full skill list comes from claude-code-templates package

## IPC Communication Layer

### Preload API

**Location:** `src/preload/api/modules/skills-api.ts`

**Exposed API:**
```typescript
skills: {
  list: (projectPath?: string) => Promise<Skill[]>
  install: (skillPath: string) => Promise<InstallSkillResult>
  remove: (skillPath: string) => Promise<RemoveSkillResult>
  getContent: (skillPath: string) => Promise<string>
}
```

### IPC Handlers (Main Process)

#### 1. List Skills Handler

**File:** `src/main/ipc-handlers/skills/list-skills.ts`

**Channel:** `skills:list`

**Logic:**
1. Scan `~/.claude/skills/` for user skills
2. If project path provided, scan `.claude/skills/` and `auto-claude/.claude/skills/`
3. For each directory, check for `SKILL.md`
4. Parse frontmatter to extract metadata (name, description, category, version)
5. Return array of Skill objects

**Frontmatter Parsing:**
```yaml
---
name: my-skill
description: Brief description
category: development
version: 1.0.0
---
```

#### 2. Install Skill Handler

**File:** `src/main/ipc-handlers/skills/install-skill.ts`

**Channel:** `skills:install`

**Logic:**
1. Execute `npx claude-code-templates@latest --skill {skillPath} --yes`
2. Use child_process.exec with promisify
3. Set 60-second timeout
4. Return success/failure with output/error

**Example:**
```typescript
const command = `npx claude-code-templates@latest --skill development/test-driven-development --yes`
const { stdout, stderr } = await execAsync(command, { timeout: 60000 })
```

#### 3. Remove Skill Handler

**File:** `src/main/ipc-handlers/skills/remove-skill.ts`

**Channel:** `skills:remove`

**Logic:**
1. Use fs.promises.rm with recursive flag
2. Delete entire skill directory
3. Return success/failure

**Safety:**
- Uses `force: true` to avoid errors if path doesn't exist
- Entire directory removed recursively

#### 4. Get Skill Content Handler

**File:** `src/main/ipc-handlers/skills/get-skill-content.ts`

**Channel:** `skills:get-content`

**Logic:**
1. Construct path to SKILL.md: `{skillPath}/SKILL.md`
2. Read file using fs.promises.readFile
3. Return content as UTF-8 string
4. Throw error if file not found

## Type Definitions

**Location:** `src/shared/types/skills.ts`

```typescript
export interface Skill {
  name: string
  description: string
  source: 'user' | 'project'
  path: string
  category?: string
  version?: string
}

export interface InstallSkillResult {
  success: boolean
  output?: string
  error?: string
}

export interface RemoveSkillResult {
  success: boolean
  error?: string
}

export interface MarketplaceSkill {
  name: string
  description: string
  category: string
  path: string
}

export interface SkillCategory {
  name: string
  displayName: string
  count: number
  skills: MarketplaceSkill[]
}
```

## Integration with Settings

**Location:** `src/renderer/components/settings/AppSettings.tsx`

**Integration:**
1. Import SkillsManager component
2. Add 'skills' to AppSection type
3. Add Skills tab to navigation with Package icon
4. Render SkillsManager when 'skills' section active

**Navigation Item:**
```typescript
{
  id: 'skills',
  label: 'Skills',
  icon: Package,
  description: 'Browse and manage Claude Skills'
}
```

**Rendering:**
```typescript
case 'skills':
  return <SkillsManager />;
```

## File Structure

```
auto-claude-ui/
├── src/
│   ├── main/
│   │   └── ipc-handlers/
│   │       └── skills/
│   │           ├── list-skills.ts          # Scan and parse skills
│   │           ├── install-skill.ts        # Execute npx install
│   │           ├── remove-skill.ts         # Delete skill directory
│   │           └── get-skill-content.ts    # Read SKILL.md
│   ├── preload/
│   │   └── api/
│   │       └── modules/
│   │           └── skills-api.ts           # IPC bridge
│   ├── renderer/
│   │   └── components/
│   │       └── skills/
│   │           ├── SkillsManager.tsx       # Main component
│   │           ├── SkillCard.tsx           # Individual skill card
│   │           ├── SkillPreview.tsx        # Preview modal
│   │           ├── SkillsMarketplace.tsx   # Marketplace browser
│   │           ├── marketplace-data.ts     # Hardcoded skill data
│   │           └── index.ts                # Exports
│   └── shared/
│       └── types/
│           └── skills.ts                   # TypeScript types
└── docs/
    └── SKILLS_MANAGER.md                   # This file
```

## State Management

### Component-Level State

The Skills Manager uses React hooks for state management:

**Loading State:**
- `loading`: Initial load of skills
- `refreshing`: Refresh button clicked
- `installing`: Specific skill being installed

**Data State:**
- `skills`: Array of installed skills
- `selectedSkill`: Skill selected for preview
- `showMarketplace`: Marketplace modal visibility

**Filter State:**
- `searchQuery`: User's search input
- Filtered in render via `.filter()`

### Project Integration

**useProjectStore:**
```typescript
const selectedProject = useProjectStore((state) => state.getSelectedProject())
```

- Gets currently selected project from Zustand store
- Project path passed to `list` IPC handler
- Skills refresh when project changes (via `useEffect` dependency)

## Error Handling

### Renderer-Side

**Try-Catch Blocks:**
- All IPC calls wrapped in try-catch
- User-friendly alerts for errors
- Console errors logged for debugging

**User Feedback:**
- Alert dialogs for install/remove errors
- Loading indicators during async operations
- Empty states when no skills found

### Main Process

**File System Errors:**
- Missing directories return empty arrays (not errors)
- Missing SKILL.md files skipped silently
- Parse errors logged, skill skipped

**Installation Errors:**
- npx command timeout (60s)
- Network failures caught and returned as error message
- stderr included in output for debugging

## Security Considerations

### Path Validation

**User Skills:**
- Hardcoded to `~/.claude/skills/`
- No user input for base path

**Project Skills:**
- Project path from validated project store
- Joined with `.claude/skills/` using path.join
- No directory traversal risk

### Command Execution

**npx Install:**
- Skill path validated as string
- Inserted into command template
- No shell injection (promisified exec)
- Timeout prevents hanging

**File Deletion:**
- Full path validated
- Requires user confirmation in UI
- Recursive deletion with force flag

## Performance Considerations

### Skill Scanning

**Optimization:**
- Scans only two directories (user + project)
- Parallel directory reads possible
- Frontmatter parsing lightweight

**Caching:**
- No caching currently implemented
- Skills loaded on mount and manual refresh
- Consider caching if performance issues

### Marketplace Data

**Current Approach:**
- Hardcoded sample data in marketplace-data.ts
- Not all 247+ skills listed (only examples)
- Actual installation via npx downloads from npm

**Future Enhancement:**
- Could fetch full catalog from API
- Could cache marketplace data
- Could show download stats

## Testing Strategies

### Unit Tests

**Components:**
- SkillCard: Test rendering, button clicks
- SkillPreview: Test content loading, modal behavior
- SkillsMarketplace: Test filtering, search, installation

**IPC Handlers:**
- Mock fs operations
- Test frontmatter parsing
- Test error conditions

### Integration Tests

**End-to-End:**
1. Open Settings → Skills
2. Verify skills load
3. Test search functionality
4. Test skill installation
5. Test skill removal
6. Test preview modal

### Manual Testing Checklist

- [ ] Skills list loads on mount
- [ ] User and project skills distinguished
- [ ] Search filters correctly
- [ ] Refresh updates list
- [ ] Marketplace opens and displays skills
- [ ] Category filters work
- [ ] Skill installation succeeds
- [ ] Installed badge appears
- [ ] Preview shows SKILL.md content
- [ ] Skill removal works with confirmation
- [ ] Empty state shows when no skills
- [ ] Loading states display correctly

## Extension Points

### Adding New Features

**Usage Statistics:**
- Track skill invocations in agent runs
- Store in project metadata or database
- Display in UI as "Used X times"

**Skill Updates:**
- Check for updated versions
- Show "Update Available" badge
- One-click update via reinstall

**Custom Categories:**
- Allow users to tag skills
- Filter by custom tags
- Personal organization

**Skill Templates:**
- Create skills from templates
- Wizard-based skill creation
- Save custom skills to user directory

### API Extensions

**New IPC Channels:**
```typescript
// Potential additions
'skills:search-marketplace'  // Fetch from API instead of hardcoded
'skills:get-stats'           // Skill usage statistics
'skills:update'              // Check for and install updates
'skills:create'              // Create new skill from template
```

## Debugging

### Renderer Debug

**Console Logs:**
```typescript
console.log('Skills loaded:', skills)
console.error('Failed to load skills:', error)
```

**React DevTools:**
- Inspect SkillsManager state
- Verify props passed to children
- Check re-render causes

### Main Process Debug

**Console Output:**
```typescript
console.log('Scanning directory:', dirPath)
console.error('Error parsing skill metadata:', error)
```

**Electron DevTools:**
- Open main process console
- View IPC handler execution
- Check file system operations

### Common Issues

**Skills Not Appearing:**
1. Check directory exists: `~/.claude/skills/`
2. Verify SKILL.md has valid frontmatter
3. Check console for parse errors
4. Try manual refresh

**Installation Fails:**
1. Check internet connection
2. Verify npx installed (npm -g list npx)
3. Check permissions on ~/.claude/skills/
4. Review error message in alert

**Preview Empty:**
1. Verify SKILL.md exists in skill directory
2. Check file permissions
3. Look for error in console

## Future Improvements

### Short-Term

1. **Better Error Messages**: Show specific errors to user instead of generic alerts
2. **Installation Progress**: Stream npx output to UI
3. **Bulk Operations**: Install/remove multiple skills at once
4. **Keyboard Shortcuts**: Navigate skills with arrow keys

### Medium-Term

1. **Skills Analytics**: Track which skills are used most
2. **Skill Recommendations**: Suggest skills based on project type
3. **Update Notifications**: Check for skill updates automatically
4. **Skill Editor**: Edit SKILL.md in UI with syntax highlighting

### Long-Term

1. **Skill Marketplace API**: Fetch real-time data from backend
2. **Community Features**: Rate/review skills, share custom skills
3. **Skill Dependencies**: Install related skills automatically
4. **AI-Powered Discovery**: Claude suggests skills for your task

## Related Documentation

- **User Guide**: `/docs/SKILLS_GUIDE.md` - End-user documentation
- **Skills Integration**: `/docs/SKILLS_INTEGRATION.md` - Backend integration details
- **Component Patterns**: Check other Settings components for UI consistency

## Contributing

When modifying the Skills Manager:

1. Follow existing code patterns (see IntegrationSettings.tsx)
2. Update TypeScript types in shared/types/skills.ts
3. Add error handling for all IPC calls
4. Test with both user and project skills
5. Update this documentation with changes
6. Follow commit message format: `feat(skills): description`

## Support

For issues or questions:
- GitHub Issues: https://github.com/AndyMik90/Auto-Claude/issues
- Documentation: Check SKILLS_GUIDE.md for user-facing help
