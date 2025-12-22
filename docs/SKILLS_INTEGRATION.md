# Skills Integration - Complete Research & Implementation Guide

**Created:** December 22, 2025
**Status:** Research Complete - Ready for Implementation
**Related Issue:** [#97 - Use Claude Skills](https://github.com/AndyMik90/Auto-Claude/issues/97)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [What are Claude Skills?](#what-are-claude-skills)
3. [Current Status in Auto-Claude](#current-status-in-auto-claude)
4. [Skills Ecosystem Overview](#skills-ecosystem-overview)
5. [Technical Specification](#technical-specification)
6. [Implementation Plan](#implementation-plan)
7. [Testing Strategy](#testing-strategy)
8. [Resources & References](#resources--references)

---

## Executive Summary

### Key Findings

**Claude Skills** são um **Open Standard** lançado pela Anthropic em dezembro de 2025 que permite estender as capacidades do Claude com funcionalidades especializadas. São **nativamente suportados** pelo Claude Agent SDK (Python) e compartilhados entre múltiplas plataformas (Claude Code, OpenAI Codex CLI, ChatGPT).

**Status Atual:**
- ❌ **Auto-Claude NÃO suporta Skills** (Issue #97)
- ✅ **Claude Agent SDK suporta nativamente** (Python)
- ✅ **Ecosystem gigante disponível**: 247+ skills prontos para uso
- ✅ **Implementação simples**: 2 linhas de código

**Benefícios da Implementação:**
- 🎨 Acesso a 247 skills do [claude-code-templates](https://github.com/davila7/claude-code-templates)
- 🏢 Acesso ao marketplace oficial da Anthropic
- 👥 Acesso a centenas de skills comunitários
- 🔧 Usuários podem criar skills customizados
- 🌐 Cross-platform (skills funcionam em múltiplas ferramentas)

---

## What are Claude Skills?

### Definition

**Skills** são pastas contendo instruções, scripts e recursos que Claude carrega dinamicamente para melhorar performance em tarefas especializadas. Cada skill ensina Claude como completar tarefas específicas de forma repetível.

### Format Specification

**Padrão:** Open Standard SKILL.md (agentskills.io)
**Adotado por:** Claude Code, OpenAI Codex CLI, ChatGPT

**Estrutura Básica:**

```markdown
---
name: skill-name
description: What this skill does
license: MIT
---

# Skill instructions

This skill does X, Y, Z...

## How to use

1. Step one
2. Step two
```

### Directory Structure

```
my-skill/
├── SKILL.md              # Core instructions (always loaded)
├── references/           # Documentation (loaded on demand)
│   ├── API.md
│   ├── EXAMPLES.md
│   └── QUICKSTART.md
├── scripts/              # Executables (progressive loading)
│   ├── process.py
│   ├── validate.py
│   └── helper.sh
└── assets/               # Templates & binaries
    ├── config.json
    ├── template.md
    └── logo.png
```

### Progressive Context Loading

Skills usam um sistema de 3 camadas:

1. **Layer 1: Main Context** 🟠 (Always Loaded)
   - `SKILL.md` - core skill definition
   - Loaded automatically when skill is relevant

2. **Layer 2: Skill Discovery** 🟢 (On Demand)
   - `references/` - documentation files
   - Loaded when Claude needs more context

3. **Layer 3: Progressive Resources** 🟣 (As Needed)
   - `scripts/` - executable scripts
   - `assets/` - templates and files
   - Accessed/executed directly when required

---

## Current Status in Auto-Claude

### Problem Statement

**Issue #97:** "Use Claude Skills"

**Reporter:** User tried to use `frontend-design` skill from Claude Marketplace
**Error:** "Unknown skill: frontend-design"
**Root Cause:** Auto-Claude operates in its own scope, not user's scope

### Current Implementation

**Location:** `auto-claude/client.py`

```python
# CURRENT CODE (does NOT support skills)
options = ClaudeAgentOptions(
    cwd=project_dir,
    allowed_tools=["Read", "Write", "Bash", "Grep", ...],
    # ❌ MISSING: setting_sources
    # ❌ MISSING: "Skill" in allowed_tools
)
```

**Why it doesn't work:**
1. Missing `setting_sources=["user", "project"]` parameter
2. Missing `"Skill"` in `allowed_tools` list
3. Claude SDK can't discover skills in user/project directories

### Expected Behavior

Skills should be discovered from:
- `~/.claude/skills/` - Personal skills (user scope)
- `.claude/skills/` - Project skills (project scope)
- `~/.claude/plugins/marketplaces/*/plugins/*/skills/*` - Plugin skills

---

## Skills Ecosystem Overview

### 1. Official Anthropic Repository

**Repository:** [anthropics/skills](https://github.com/anthropics/skills)

**Stats:**
- ⭐ 24,060 stars
- 🍴 2,259 forks
- 📅 Last updated: Dec 20, 2025

**Contents:**
- Official Anthropic skills
- Reference examples
- Skill creation templates

**Categories:**
- Creative applications (art, music, design)
- Technical tasks (testing, MCP generation)
- Enterprise workflows (communications, branding)

### 2. claude-code-templates (davila7)

**Repository:** [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates)
**Website:** [aitmpl.com](https://aitmpl.com)
**Local Path:** `/Users/jefferson.barnabe/projects/misc/claude-code-templates`

**Stats:**
- ✅ **247 Skills** available
- 📦 NPM package: `claude-code-templates`
- 🌐 Web interface for browsing

**Categories (12 total):**

| Category | Skills | Notable Examples |
|----------|--------|------------------|
| `business-marketing/` | 12 | Marketing campaigns, brand strategy |
| `creative-design/` | 9 | **frontend-design**, UI systems, accessibility |
| `database/` | 1 | Database management |
| `development/` | 52 | TDD, git-worktrees, security, debugging |
| `document-processing/` | 7 | PDF, Excel, document generation |
| `enterprise-communication/` | 17 | Slack, Teams, email automation |
| `media/` | 2 | Image/video processing |
| `productivity/` | 6 | Task automation, workflows |
| `scientific/` | 136 | Data analysis, ML, research |
| `utilities/` | 3 | Helper utilities |

**Installation:**

```bash
# Install specific skill
npx claude-code-templates@latest --skill creative-design/frontend-design --yes

# Browse interactively
npx claude-code-templates@latest

# Launch Skills Dashboard
npx claude-code-templates@latest --skills-manager
```

**Skills Dashboard Features:**
- Modern web interface (http://localhost:3337)
- 3-layer progressive loading visualization
- File tree explorer
- Search and filter
- Source detection (Personal/Project/Plugin)

### 3. Official Skills Marketplace

**URL:** [claude.com/connectors](https://claude.com/connectors)

**Launch Partners:**
- Atlassian
- Canva
- Figma
- Notion
- Cloudflare
- Zapier
- Stripe
- Vercel

**Features:**
- Official verified skills
- Enterprise provisioning (Team/Enterprise plans)
- Central management from admin settings

### 4. Community Marketplaces

**SkillsMP** - [skillsmp.com](https://skillsmp.com)
- Cross-platform skills (Claude, Codex, ChatGPT)
- Community contributions
- Rating and reviews

**GitHub Collections:**
- [abubakarsiddik31/claude-skills-collection](https://github.com/abubakarsiddik31/claude-skills-collection)
- [simonw/claude-skills](https://github.com/simonw/claude-skills)
- Hundreds of community skills

### 5. Timeline & Milestones

**October 16, 2025** - Initial Launch
- Skills introduced as Beta feature
- Available in Claude.ai and Claude Code

**December 18, 2025** - Open Standard Release
- Agent Skills specification published at agentskills.io
- OpenAI adopts same format for Codex CLI and ChatGPT
- Skills Directory launched
- Enterprise features (central provisioning)
- Cross-platform support announced

**December 20, 2025** - anthropics/skills repo last updated

---

## Technical Specification

### Claude Agent SDK Integration

**Language:** Python
**SDK:** `claude-agent-sdk`
**Support:** Native and built-in

### Configuration

**Required Changes to Enable Skills:**

```python
from claude_agent_sdk import ClaudeAgentOptions

# BEFORE (current - no skills)
options = ClaudeAgentOptions(
    cwd=project_dir,
    allowed_tools=["Read", "Write", "Bash", "Grep", "Glob"]
)

# AFTER (with skills support)
options = ClaudeAgentOptions(
    cwd=project_dir,
    setting_sources=["user", "project"],  # ← Enable skills discovery
    allowed_tools=[
        "Skill",     # ← Add Skill tool
        "Read",
        "Write",
        "Bash",
        "Grep",
        "Glob"
    ]
)
```

### Skill Discovery Paths

When `setting_sources=["user", "project"]` is set, Claude SDK automatically scans:

1. **User Skills** (`"user"`)
   - Path: `~/.claude/skills/`
   - Scope: Available to all projects
   - Use case: Personal productivity skills

2. **Project Skills** (`"project"`)
   - Path: `{cwd}/.claude/skills/`
   - Scope: Project-specific
   - Use case: Team workflows, project conventions

3. **Plugin Skills** (auto-detected)
   - Path: `~/.claude/plugins/marketplaces/*/plugins/*/skills/*`
   - Scope: Installed via plugin marketplaces
   - Use case: Third-party integrations

### Skill Invocation

**Automatic Discovery:**
- Claude reads skill descriptions during session initialization
- Skills are invoked automatically when relevant to user request
- No explicit `/skill-name` command needed

**Example Flow:**

```
User: "Create a modern landing page with a hero section"

Claude (internal):
1. Scans available skills
2. Finds "frontend-design" skill in ~/.claude/skills/
3. Reads SKILL.md description
4. Determines skill is relevant
5. Loads skill context
6. Executes task using skill guidelines

Result: Distinctive, production-grade frontend code
```

### SKILL.md Format Details

**Minimum Required:**

```yaml
---
name: my-skill
description: Brief description of what this skill does
---
```

**Full Example:**

```yaml
---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, or applications.
license: MIT
allowed_tools:
  - Read
  - Write
  - Bash
tags:
  - frontend
  - design
  - react
  - web
version: 1.0.0
---

# Frontend Design Skill

This skill guides creation of distinctive, production-grade frontend interfaces...

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve?
- **Tone**: Pick an extreme aesthetic direction
- **Constraints**: Technical requirements

## Implementation Guidelines

[Detailed instructions...]
```

---

## Implementation Plan

### Phase 1: Core Skills Support

**Goal:** Enable basic skills functionality in Auto-Claude

**Files to Modify:**

1. **`auto-claude/client.py`**

   **Change:** Update `ClaudeAgentOptions` initialization

   ```python
   # CURRENT
   def create_agent_options(
       project_dir: Path,
       allowed_tools: list[str],
       ...
   ) -> ClaudeAgentOptions:
       return ClaudeAgentOptions(
           cwd=str(project_dir),
           allowed_tools=allowed_tools,
           ...
       )

   # NEW
   def create_agent_options(
       project_dir: Path,
       allowed_tools: list[str],
       enable_skills: bool = True,  # ← New parameter
       ...
   ) -> ClaudeAgentOptions:
       # Add Skill tool if skills enabled
       if enable_skills and "Skill" not in allowed_tools:
           allowed_tools = ["Skill"] + allowed_tools

       return ClaudeAgentOptions(
           cwd=str(project_dir),
           setting_sources=["user", "project"] if enable_skills else None,
           allowed_tools=allowed_tools,
           ...
       )
   ```

2. **`auto-claude/security.py`**

   **Change:** Add "Skill" to allowed tools

   ```python
   # Add to DEFAULT_ALLOWED_TOOLS or equivalent
   DEFAULT_ALLOWED_TOOLS = [
       "Skill",  # ← Add this
       "Read",
       "Write",
       "Bash",
       ...
   ]
   ```

3. **Environment Configuration**

   **File:** `auto-claude/.env`

   ```bash
   # Add new configuration
   ENABLE_SKILLS=true  # Enable/disable skills support
   ```

### Phase 2: Configuration & Settings

**Goal:** Allow users to configure skills behavior

**New Files:**

1. **`auto-claude/skills_config.py`**

   ```python
   """Skills configuration and management."""

   from pathlib import Path
   import os

   def is_skills_enabled() -> bool:
       """Check if skills are enabled."""
       return os.getenv("ENABLE_SKILLS", "true").lower() == "true"

   def get_skills_paths() -> dict[str, Path]:
       """Get paths to skills directories."""
       return {
           "user": Path.home() / ".claude" / "skills",
           "project": Path.cwd() / ".claude" / "skills"
       }

   def list_available_skills() -> list[dict]:
       """List all available skills."""
       skills = []
       paths = get_skills_paths()

       for source, path in paths.items():
           if path.exists():
               for skill_dir in path.iterdir():
                   if skill_dir.is_dir():
                       skill_md = skill_dir / "SKILL.md"
                       if skill_md.exists():
                           skills.append({
                               "name": skill_dir.name,
                               "path": str(skill_dir),
                               "source": source
                           })

       return skills
   ```

2. **UI Integration (auto-claude-ui)**

   **New Component:** `SkillsManager.tsx`
   - List installed skills
   - Browse available skills
   - Install from marketplaces
   - Enable/disable specific skills

### Phase 3: Documentation & Testing

**Goal:** Document skills usage for Auto-Claude users

**New Files:**

1. **`docs/SKILLS_GUIDE.md`** - User guide for skills
2. **`docs/CREATING_SKILLS.md`** - How to create custom skills
3. **`tests/test_skills_integration.py`** - Integration tests

**Documentation Topics:**
- How to install skills
- How to create custom skills
- Skills best practices
- Troubleshooting

### Phase 4: Advanced Features (Optional)

**Goal:** Enhanced skills management

**Features:**
- Skills analytics (usage tracking)
- Skills recommendations based on project type
- Skills versioning and updates
- Skills marketplace integration
- Team skills sharing

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_skills_integration.py`

```python
import pytest
from pathlib import Path
from client import create_agent_options

def test_skills_enabled_by_default():
    """Skills should be enabled by default."""
    options = create_agent_options(
        project_dir=Path.cwd(),
        allowed_tools=["Read", "Write"]
    )

    assert "Skill" in options.allowed_tools
    assert options.setting_sources == ["user", "project"]

def test_skills_can_be_disabled():
    """Skills can be disabled via parameter."""
    options = create_agent_options(
        project_dir=Path.cwd(),
        allowed_tools=["Read", "Write"],
        enable_skills=False
    )

    assert "Skill" not in options.allowed_tools
    assert options.setting_sources is None

def test_skill_discovery_paths():
    """Test skill discovery in user and project directories."""
    from skills_config import get_skills_paths

    paths = get_skills_paths()

    assert "user" in paths
    assert "project" in paths
    assert paths["user"] == Path.home() / ".claude" / "skills"
```

### Integration Tests

**Test Scenarios:**

1. **Skill Installation**
   ```bash
   # Install frontend-design skill
   npx claude-code-templates@latest --skill creative-design/frontend-design --yes

   # Verify skill is discoverable
   python -c "from skills_config import list_available_skills; print(list_available_skills())"
   ```

2. **Skill Usage in Task**
   ```bash
   # Create task that uses frontend-design skill
   python auto-claude/spec_runner.py --task "Create a modern landing page"

   # Verify skill was used (check logs for "frontend-design")
   ```

3. **Custom Skill Creation**
   ```bash
   # Create custom skill
   mkdir -p ~/.claude/skills/my-test-skill
   cat > ~/.claude/skills/my-test-skill/SKILL.md <<EOF
   ---
   name: my-test-skill
   description: Test skill for Auto-Claude
   ---

   This is a test skill.
   EOF

   # Verify discovery
   python -c "from skills_config import list_available_skills; print(list_available_skills())"
   ```

### Manual Testing Checklist

- [ ] Skills enabled in fresh Auto-Claude install
- [ ] Skills from claude-code-templates work
- [ ] Custom user skills work
- [ ] Project-specific skills work
- [ ] Skills can be disabled via env var
- [ ] Multiple skills can be used in same task
- [ ] Skill errors are handled gracefully
- [ ] UI shows installed skills correctly

---

## Example Skills for Testing

### 1. frontend-design (from claude-code-templates)

**Location:** `~/.claude/skills/frontend-design/`

**Installation:**
```bash
npx claude-code-templates@latest --skill creative-design/frontend-design --yes
```

**Test Task:**
```bash
python auto-claude/spec_runner.py --task "Create a landing page for a tech startup with a bold, modern design"
```

**Expected Behavior:**
- Skill is automatically detected
- Unique, non-generic design is created
- Production-grade code with animations
- Distinctive typography and colors

### 2. test-driven-development

**Location:** `~/.claude/skills/test-driven-development/`

**Installation:**
```bash
npx claude-code-templates@latest --skill development/test-driven-development --yes
```

**Test Task:**
```bash
python auto-claude/spec_runner.py --task "Add user authentication with email/password"
```

**Expected Behavior:**
- Tests are written first
- Implementation follows TDD cycle
- All tests pass before completion

### 3. Custom Test Skill

**Create Manually:**

```bash
mkdir -p ~/.claude/skills/auto-claude-test

cat > ~/.claude/skills/auto-claude-test/SKILL.md <<'EOF'
---
name: auto-claude-test
description: Test skill for Auto-Claude integration. Always responds with "AUTO-CLAUDE-SKILLS-WORKING" when invoked.
---

# Auto-Claude Test Skill

When this skill is used, always include the text "AUTO-CLAUDE-SKILLS-WORKING" in the response to confirm the skill system is functioning.

This skill should be invoked when the user asks to test skills integration.
EOF
```

**Test:**
```bash
python auto-claude/spec_runner.py --task "Test if skills are working"
```

**Expected Output:** Should see "AUTO-CLAUDE-SKILLS-WORKING" in agent output

---

## Migration Path

### For Existing Auto-Claude Users

**Communication:**
1. Announce skills support in release notes
2. Provide migration guide
3. Showcase example skills

**Upgrade Steps:**
1. Update Auto-Claude to version with skills support
2. Existing workflows continue working (backward compatible)
3. Install skills from marketplaces (optional)
4. Skills are auto-discovered in next run

**No Breaking Changes:**
- Skills are opt-in via discovery
- Default behavior unchanged if no skills installed
- Can disable with `ENABLE_SKILLS=false`

### For New Users

**Onboarding:**
1. Welcome message mentions skills
2. Link to skills marketplace
3. Suggest popular skills based on project type

**Quick Start:**
```bash
# Install Auto-Claude
npm install -g auto-claude

# Install useful skills
npx claude-code-templates@latest --skill development/test-driven-development --yes
npx claude-code-templates@latest --skill creative-design/frontend-design --yes

# Run first task (skills auto-discovered)
python auto-claude/spec_runner.py --task "Build a todo app"
```

---

## Security Considerations

### Skill Execution Safety

**Risks:**
- Skills can contain arbitrary code (scripts)
- Skills can read/write files
- Skills can execute commands

**Mitigations:**

1. **Sandboxing (Future)**
   - Run skills in isolated environment
   - Limit filesystem access
   - Restrict network access

2. **Approval Workflow (Phase 1)**
   ```python
   # Prompt user before first skill execution
   if not skill_previously_approved(skill_name):
       print(f"Skill '{skill_name}' wants to execute:")
       print(f"  - Scripts: {list_scripts(skill)}")
       print(f"  - Tools: {skill.allowed_tools}")

       if input("Allow? (y/n): ").lower() != 'y':
           raise SkillNotApproved(skill_name)

       mark_skill_approved(skill_name)
   ```

3. **Trusted Sources**
   - Official Anthropic skills (trusted by default)
   - Verified marketplace skills (prompt once)
   - Custom user skills (always prompt)

4. **Audit Logging**
   ```python
   # Log all skill executions
   log_skill_execution(
       skill_name=skill_name,
       timestamp=datetime.now(),
       user=current_user,
       project=project_dir,
       actions_performed=["read file X", "executed script Y"]
   )
   ```

### Best Practices

**For Users:**
- Review skill source before installation
- Only install from trusted sources
- Check skill permissions (allowed_tools)
- Keep skills updated

**For Skill Creators:**
- Minimize required permissions
- Document all file access
- Use safe defaults
- Provide clear descriptions

---

## Performance Considerations

### Skill Discovery Overhead

**Current Implementation:**
- Skills scanned once at session start
- ~1-5ms per skill directory
- Negligible for <100 skills

**Optimization (if needed):**
```python
# Cache skill metadata
@cached(ttl=300)  # 5 minutes
def list_available_skills():
    # ... scan filesystem
    pass
```

### Context Loading

**Progressive Loading Benefits:**
- Main context always small (SKILL.md only)
- References loaded on demand (saves tokens)
- Scripts only when executed

**Example:**
```
SKILL.md: 500 tokens (always loaded)
references/: 5,000 tokens (loaded if needed)
scripts/: 0 tokens (executed, not loaded)

Best case: 500 tokens
Worst case: 5,500 tokens
```

---

## Resources & References

### Official Documentation

- [Agent Skills - Claude Code Docs](https://code.claude.com/docs/en/skills)
- [Agent Skills in SDK](https://platform.claude.com/docs/en/agent-sdk/skills)
- [Using Agent Skills with the API](https://docs.claude.com/en/docs/build-with-claude/skills-guide)
- [How to create custom Skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)
- [What are Skills?](https://support.claude.com/en/articles/12512176-what-are-skills)

### Official Repositories

- [anthropics/skills](https://github.com/anthropics/skills) - Official skills repository
- [anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python) - Python SDK

### Community Resources

- [davila7/claude-code-templates](https://github.com/davila7/claude-code-templates) - 247 ready-to-use skills
- [aitmpl.com](https://aitmpl.com) - Web interface for browsing templates
- [abubakarsiddik31/claude-skills-collection](https://github.com/abubakarsiddik31/claude-skills-collection)
- [simonw/claude-skills](https://github.com/simonw/claude-skills)

### Marketplaces

- [claude.com/connectors](https://claude.com/connectors) - Official Skills Directory
- [skillsmp.com](https://skillsmp.com) - Community marketplace

### Blog Posts & Articles

- [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Introducing Agent Skills](https://www.anthropic.com/news/skills)
- [Claude Agent Skills: A First Principles Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
- [Complete Guide to Claude Code Templates](https://medium.com/latinxinai/complete-guide-to-claude-code-templates-4e53d6688b34)
- [Claude Skills are awesome, maybe a bigger deal than MCP](https://simonwillison.net/2025/Oct/16/claude-skills/)

### Tools & Utilities

- **NPM Package:** `claude-code-templates`
- **Skills Dashboard:** `npx claude-code-templates --skills-manager`
- **CLI Tool:** `npx claude-code-templates`

---

## Appendix

### A. Full Example Skill

**Location:** `~/.claude/skills/code-reviewer/SKILL.md`

```markdown
---
name: code-reviewer
description: Comprehensive code review focusing on security, performance, maintainability, and best practices. Use when user requests code review or analysis.
license: MIT
allowed_tools:
  - Read
  - Grep
  - Bash
tags:
  - code-review
  - security
  - performance
  - best-practices
version: 1.0.0
---

# Code Reviewer Skill

Perform thorough code reviews following industry best practices.

## Review Checklist

### 1. Security
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all user inputs
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Authentication/authorization checks

### 2. Performance
- [ ] No N+1 queries
- [ ] Efficient algorithms (check Big O)
- [ ] Proper indexing
- [ ] Caching where appropriate
- [ ] Resource cleanup (connections, files)

### 3. Code Quality
- [ ] Clear naming conventions
- [ ] Proper error handling
- [ ] No code duplication
- [ ] Single Responsibility Principle
- [ ] Comments where necessary
- [ ] Tests included

### 4. Maintainability
- [ ] Modular design
- [ ] Consistent formatting
- [ ] Documentation updated
- [ ] Dependencies up to date
- [ ] No deprecated APIs

## Review Process

1. **Read the code** - Understand what it does
2. **Run tests** - Verify functionality
3. **Check security** - Scan for vulnerabilities
4. **Assess performance** - Look for bottlenecks
5. **Evaluate maintainability** - Consider future changes
6. **Provide feedback** - Actionable suggestions

## Output Format

**Summary:**
Brief overview of the code and its purpose.

**Critical Issues:** 🔴
Issues that must be fixed before merge.

**Suggestions:** 🟡
Improvements that should be considered.

**Positive Notes:** 🟢
Well-implemented aspects worth highlighting.

**Overall Assessment:**
Recommend: Approve / Request Changes / Reject
```

### B. Comparison with MCP

| Aspect | Skills | MCP (Model Context Protocol) |
|--------|--------|------------------------------|
| **Purpose** | Teach Claude HOW to do tasks | Connect Claude to external data sources |
| **Format** | Markdown files (SKILL.md) | JSON-RPC protocol |
| **Loading** | Progressive (3 layers) | Full context on demand |
| **Execution** | Instructions + optional scripts | Server-side tools |
| **Platform** | Cross-platform (Claude/Codex/GPT) | Claude-specific |
| **Distribution** | File-based (git, npm) | Server endpoints |
| **Examples** | Code review guidelines, design principles | Database queries, API access |

**Complementary:** Skills and MCP work together. A skill can use MCP servers!

Example:
```yaml
---
name: database-analyst
description: Analyze database performance using PostgreSQL MCP
---

# Database Analyst Skill

Use the PostgreSQL MCP server to analyze query performance.

1. Connect to database via MCP
2. Run EXPLAIN ANALYZE on slow queries
3. Suggest index optimizations
4. Identify N+1 query patterns
```

### C. Troubleshooting Guide

**Problem:** Skills not being discovered

**Solution:**
1. Check `setting_sources` is set: `["user", "project"]`
2. Verify skill directory structure:
   ```bash
   ls -la ~/.claude/skills/
   # Should show skill directories with SKILL.md inside
   ```
3. Check SKILL.md has valid YAML frontmatter
4. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

**Problem:** "Skill" tool not available

**Solution:**
1. Verify `"Skill"` is in `allowed_tools`
2. Check Claude Agent SDK version is recent
3. Restart session after adding skills

**Problem:** Skill not being invoked

**Solution:**
1. Make skill description more specific
2. Mention skill name in task description
3. Check skill's `allowed_tools` includes required tools

---

## Conclusion

Skills represent a **major opportunity** for Auto-Claude:

✅ **Easy Implementation** - 2 lines of code
✅ **Massive Value** - 247+ skills immediately available
✅ **Future-Proof** - Open Standard, cross-platform
✅ **User Demand** - Issue #97 shows need
✅ **Ecosystem Growth** - New skills added daily

**Next Steps:**
1. Review this document
2. Implement Phase 1 (core support)
3. Test with example skills
4. Document for users
5. Announce feature

**Questions?** Refer to [Resources & References](#resources--references) or open a discussion on GitHub.

---

---

## Implementation Status

### ✅ Phase 1: Backend Implementation (COMPLETE)

**Implemented:** December 22, 2025

**Changes Made:**

1. **`auto-claude/core/client.py`**
   - Added `is_skills_enabled()` function (default: true)
   - Added "Skill" to allowed tools list
   - Added `setting_sources=["user", "project"]` to ClaudeAgentOptions
   - Added "Skill" to security permissions
   - Added Skills status logging

2. **`auto-claude/.env.example`**
   - Added CLAUDE SKILLS INTEGRATION section
   - Documented ENABLE_SKILLS configuration
   - Added installation instructions and resources

3. **`docs/SKILLS_GUIDE.md`** (new)
   - Complete user guide for using Skills with Auto-Claude
   - Installation instructions
   - Popular skills examples
   - Custom skill creation guide
   - Troubleshooting section

**Result:**
- ✅ Skills are now fully supported in Auto-Claude
- ✅ Skills enabled by default (opt-out via `ENABLE_SKILLS=false`)
- ✅ Automatic discovery from `~/.claude/skills/` and `.claude/skills/`
- ✅ Works with all agents (Planner, Coder, QA Reviewer, QA Fixer)
- ✅ Zero breaking changes - backward compatible
- ✅ Issue #97 resolved

**How to Use:**
```bash
# Install a skill
npx claude-code-templates@latest --skill creative-design/frontend-design --yes

# Run Auto-Claude (skills auto-discovered)
python auto-claude/spec_runner.py --task "Create a landing page"
```

See [SKILLS_GUIDE.md](SKILLS_GUIDE.md) for complete documentation.

### ⏳ Phase 2: UI Integration (PENDING)

**Planned Features:**
- Skills Manager component in Electron UI
- Visual skills browser with categories
- One-click installation from marketplace
- Skills preview and documentation viewer
- Usage analytics and recommendations
- Enable/disable specific skills via UI

**Implementation:**
- New component: `auto-claude-ui/src/renderer/components/SkillsManager.tsx`
- IPC handlers for skill installation/management
- Integration with claude-code-templates NPM package

**Timeline:** Future release (separate PR)

---

**Document Version:** 1.1
**Last Updated:** December 22, 2025
**Author:** Research & Implementation Guide
**Status:** Phase 1 Complete, Phase 2 Planned
