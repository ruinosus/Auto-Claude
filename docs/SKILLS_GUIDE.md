# Claude Skills - User Guide

**Auto-Claude now supports Claude Skills!** Skills are extensions that teach Claude specialized capabilities for specific tasks.

## What are Claude Skills?

Skills are markdown-based instruction files (SKILL.md) that guide Claude through specialized tasks. They work like expertise plugins - when a task matches a skill's description, Claude automatically uses that skill's guidance.

**Example:** The `frontend-design` skill teaches Claude to create distinctive, production-grade UI designs instead of generic templates.

## Quick Start

### 1. Install a Skill

```bash
# Install frontend-design skill
npx claude-code-templates@latest --skill creative-design/frontend-design --yes

# Install test-driven-development skill
npx claude-code-templates@latest --skill development/test-driven-development --yes
```

### 2. Use Auto-Claude

That's it! Skills are automatically discovered and used when relevant.

```bash
# This will automatically use frontend-design skill if installed
python auto-claude/spec_runner.py --task "Create a modern landing page"
```

## Installing Skills

### From claude-code-templates (247+ Skills)

**Interactive browser:**
```bash
npx claude-code-templates@latest
```

**Direct install:**
```bash
npx claude-code-templates@latest --skill <category>/<skill-name> --yes
```

**Web dashboard:**
```bash
npx claude-code-templates@latest --skills-manager
# Opens http://localhost:3337
```

### Skill Categories

| Category | Skills | Notable Examples |
|----------|--------|------------------|
| `development/` | 52 | TDD, debugging, git-worktrees, security |
| `creative-design/` | 9 | frontend-design, UI systems, accessibility |
| `scientific/` | 136 | Data analysis, ML, research |
| `business-marketing/` | 12 | Marketing campaigns, brand strategy |
| `enterprise-communication/` | 17 | Slack, Teams, email automation |
| `document-processing/` | 7 | PDF, Excel, document generation |

Browse all: https://aitmpl.com

## How Skills Work

### Discovery

Skills are discovered from two locations:

```
~/.claude/skills/          # Personal skills (all projects)
.claude/skills/            # Project-specific skills
```

### Automatic Invocation

Skills are invoked automatically when:
1. Claude reads all installed skill descriptions at session start
2. User request matches a skill's description
3. Claude loads the skill's instructions and executes the task using those guidelines

**No explicit commands needed** - Claude decides when to use skills based on relevance.

## Popular Skills

### 1. frontend-design

Creates distinctive, production-grade frontend interfaces with high design quality.

```bash
npx claude-code-templates@latest --skill creative-design/frontend-design --yes
```

**Use case:** "Build a landing page for a SaaS product"

### 2. test-driven-development

Implements features using TDD methodology (write tests first, then implementation).

```bash
npx claude-code-templates@latest --skill development/test-driven-development --yes
```

**Use case:** "Add user authentication with email/password"

### 3. systematic-debugging

Four-phase debugging framework (root cause → pattern analysis → hypothesis testing → implementation).

```bash
npx claude-code-templates@latest --skill development/systematic-debugging --yes
```

**Use case:** "Fix the bug where login fails intermittently"

## Creating Custom Skills

### Basic Structure

```bash
mkdir -p ~/.claude/skills/my-skill
```

Create `~/.claude/skills/my-skill/SKILL.md`:

```markdown
---
name: my-skill
description: Brief description of what this skill does. This is what Claude uses to decide when to invoke the skill.
---

# My Skill

Detailed instructions for Claude on how to complete this task.

## Guidelines

1. Step one
2. Step two
3. Step three
```

### Advanced Structure

```
my-skill/
├── SKILL.md              # Core instructions (always loaded)
├── references/           # Documentation (loaded on demand)
│   ├── API.md
│   └── EXAMPLES.md
├── scripts/              # Executables (progressive loading)
│   └── helper.py
└── assets/               # Templates & resources
    └── template.json
```

See [Creating Custom Skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills) for full guide.

## Configuration

### Enable/Disable Skills

Skills are **enabled by default**. To disable:

```bash
# In auto-claude/.env
ENABLE_SKILLS=false
```

### Check Skills Status

When Auto-Claude starts, you'll see:

```
Security settings: /path/to/project/.claude_settings.json
   - Sandbox enabled (OS-level bash isolation)
   - Filesystem restricted to: /path/to/project
   - Bash commands restricted to allowlist
   - MCP servers: context7 (documentation)
   - Skills: enabled (user + project scopes)  ← Skills status
```

### List Installed Skills

```bash
# User skills
ls ~/.claude/skills/

# Project skills
ls .claude/skills/
```

## Troubleshooting

### Skills not being discovered

**Check 1:** Verify skill directory structure
```bash
ls -la ~/.claude/skills/
# Should show skill directories with SKILL.md inside each
```

**Check 2:** Verify SKILL.md has valid frontmatter
```bash
cat ~/.claude/skills/my-skill/SKILL.md
# Should start with:
# ---
# name: my-skill
# description: ...
# ---
```

**Check 3:** Verify Skills are enabled
```bash
# In auto-claude/.env
# Ensure ENABLE_SKILLS is not set to false
```

### Skill not being invoked

**Solution 1:** Make skill description more specific
- The description in the frontmatter determines when Claude uses the skill
- Be specific about what tasks trigger this skill

**Solution 2:** Mention skill in task description
```bash
python auto-claude/spec_runner.py --task "Create a landing page using frontend-design best practices"
```

**Solution 3:** Check skill compatibility
- Verify skill's `allowed_tools` (if specified) are available in Auto-Claude

## Resources

### Official Documentation
- [Claude Skills Documentation](https://code.claude.com/docs/en/skills)
- [Creating Custom Skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)
- [What are Skills?](https://support.claude.com/en/articles/12512176-what-are-skills)

### Skill Repositories
- [claude-code-templates](https://github.com/davila7/claude-code-templates) - 247+ skills
- [anthropics/skills](https://github.com/anthropics/skills) - Official skills
- [Skills Marketplace](https://claude.com/connectors) - Enterprise skills

### Tools
- **Web Browser:** https://aitmpl.com
- **CLI:** `npx claude-code-templates@latest`
- **Dashboard:** `npx claude-code-templates@latest --skills-manager`

## Examples

### Example 1: Design-Focused Development

```bash
# Install design skill
npx claude-code-templates@latest --skill creative-design/frontend-design --yes

# Create task
python auto-claude/spec_runner.py --task "Build a portfolio website for a photographer with a bold, artistic design"

# Auto-Claude will automatically use frontend-design skill
```

### Example 2: TDD Workflow

```bash
# Install TDD skill
npx claude-code-templates@latest --skill development/test-driven-development --yes

# Create task
python auto-claude/spec_runner.py --task "Add shopping cart functionality with add/remove/checkout"

# Tests will be written first, then implementation
```

### Example 3: Team-Specific Conventions

```bash
# Create project-specific skill
mkdir -p .claude/skills/team-conventions

cat > .claude/skills/team-conventions/SKILL.md <<'EOF'
---
name: team-conventions
description: Apply our team's coding conventions and best practices
---

# Team Conventions

## Naming
- Components: PascalCase
- Functions: camelCase
- Constants: SCREAMING_SNAKE_CASE

## File Structure
- One component per file
- Tests alongside implementation (MyComponent.tsx + MyComponent.test.tsx)
- Barrel exports in index.ts

## Code Style
- Max line length: 100
- Always use TypeScript strict mode
- Prefer named exports over default exports
EOF

# Now all Auto-Claude builds in this project will follow these conventions
```

## Using the Skills Manager UI

Auto-Claude UI includes a visual Skills Manager for easy skill management through a graphical interface.

### Accessing Skills Manager

1. Open the Auto-Claude UI application
2. Click the **Settings** button (gear icon) in the top-right corner
3. Navigate to the **Skills** tab in the left sidebar

### Managing Installed Skills

The Skills tab displays all installed skills in a grid layout with cards showing:
- Skill name and icon
- Source badge (user or project)
- Category badge
- Description
- Action buttons (Preview, Remove)

**Search Skills:**
- Use the search bar at the top to filter skills by name, description, or category
- Results update in real-time as you type

**Refresh Skills List:**
- Click the refresh icon next to the "Skills Manager" title
- Useful after installing skills via CLI or making manual changes

**Preview Skill Content:**
1. Click the **Preview** button on any skill card
2. A modal will open displaying the full SKILL.md content
3. View skill instructions, metadata, and guidelines
4. Close the preview when done

**Remove Skills:**
1. Click the **trash icon** on any skill card
2. Confirm the removal in the dialog
3. The skill directory will be permanently deleted

### Installing Skills from Marketplace

The Skills Manager provides access to 247+ skills from the claude-code-templates marketplace.

**Browse Marketplace:**
1. Click the **Browse Marketplace** button in the header
2. The marketplace modal opens with all available skills

**Search and Filter:**
- Use the search bar to find skills by name or description
- Filter by category using the badge buttons:
  - Development (52 skills)
  - Creative Design (9 skills)
  - Business & Marketing (12 skills)
  - Scientific (136 skills)
  - All categories shown with skill counts

**Install a Skill:**
1. Find the skill you want in the marketplace
2. Click the **Install** button on the skill card
3. Wait for installation (button shows "Installing..." with spinner)
4. Button changes to "Installed" with checkmark when complete
5. Close marketplace to see the newly installed skill in your main list

**Installation Status:**
- Skills already installed show a green "Installed" badge
- You cannot reinstall an already-installed skill
- Close and reopen marketplace to refresh installation status

### Skills Locations

Skills are displayed with source badges indicating their location:

**User Skills** (`~/.claude/skills/`)
- Badge shows: "user"
- Available to all Auto-Claude projects
- Personal productivity and general-purpose skills

**Project Skills** (`.claude/skills/` or `auto-claude/.claude/skills/`)
- Badge shows: "project"
- Specific to the current project
- Team conventions and project-specific workflows

### UI Features

**Empty State:**
- When no skills are installed, the UI shows a helpful message
- Quick access to "Browse Marketplace" button

**Stats Display:**
- Shows total number of installed skills
- Displays filtered count when searching

**Grid Layout:**
- Responsive grid (1-3 columns based on screen size)
- Compact cards with essential information
- Hover effects for better interactivity

**Loading States:**
- Initial load shows "Loading skills..."
- Refresh shows spinning icon
- Installation shows progress indicator

### Tips for UI Users

- **Explore the Marketplace**: Browse categories to discover skills you didn't know existed
- **Preview Before Use**: Always preview skills to understand what they do
- **Use Search**: With 247+ skills, search is your friend
- **Check Source Badges**: Know whether skills are personal (user) or project-specific
- **Refresh Regularly**: Click refresh after CLI installations or manual changes
- **Read Descriptions**: Skill descriptions help Claude decide when to use them

## FAQ

**Q: Do skills work with all Auto-Claude agents?**
A: Yes. Skills are available to Planner, Coder, QA Reviewer, and QA Fixer agents.

**Q: Can I use multiple skills in one task?**
A: Yes! Claude can use multiple relevant skills automatically.

**Q: Are skills secure?**
A: Skills from trusted sources (Anthropic, verified marketplaces) are safe. Review custom skills before installing, especially if they contain scripts.

**Q: Do skills require internet?**
A: No. Skills are local markdown files. However, installing skills via `npx` requires internet.

**Q: Can I share skills with my team?**
A: Yes! Commit `.claude/skills/` to your git repo for project-specific skills. For personal skills, share the skill directory or use `npx claude-code-templates`.

**Q: How do I update a skill?**
A: Reinstall using the same `npx` command, or manually update the SKILL.md file.

**Q: Can I disable specific skills?**
A: Currently, you can only enable/disable all skills via `ENABLE_SKILLS`. To disable a specific skill, delete or rename its directory.

---

**Need help?** Open an issue: https://github.com/AndyMik90/Auto-Claude/issues
