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

## UI Integration (Coming Soon)

**Phase 2:** Skills Manager UI in Electron app
- Visual skills browser
- One-click installation
- Skills preview and management
- Usage statistics

Currently, skills are managed via CLI (this guide). UI integration is planned for a future release.

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
