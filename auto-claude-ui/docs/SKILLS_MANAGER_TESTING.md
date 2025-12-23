# Skills Manager - Comprehensive Testing Guide

This document provides a complete testing checklist for the Skills Manager UI feature in Auto-Claude.

## Table of Contents

- [Pre-Flight Checklist](#pre-flight-checklist)
- [Manual Testing Checklist](#manual-testing-checklist)
- [IPC Handler Verification](#ipc-handler-verification)
- [Error Scenarios](#error-scenarios)
- [Performance Checks](#performance-checks)
- [Accessibility Checks](#accessibility-checks)
- [Cross-Platform Considerations](#cross-platform-considerations)
- [Test Results Template](#test-results-template)

---

## Pre-Flight Checklist

Before starting manual tests, verify the following:

### 1. TypeScript Compilation

```bash
cd auto-claude-ui
npx tsc --noEmit
```

Expected: No TypeScript errors

### 2. Build Verification

```bash
cd auto-claude-ui
pnpm run build
```

Expected: Build completes successfully without errors

### 3. Dependencies

```bash
cd auto-claude-ui
pnpm install
```

Expected: All dependencies installed successfully

### 4. Development Server

```bash
cd auto-claude-ui
pnpm run dev
```

Expected: App launches successfully, no console errors on startup

---

## Manual Testing Checklist

### SkillsManager Component

#### Component Rendering
- [ ] **Initial Load**: Skills Manager appears in Settings > Skills tab
- [ ] **Header**: Shows "Skills Manager" title with Package icon
- [ ] **Refresh Button**: Displays refresh icon next to title
- [ ] **Browse Marketplace Button**: Visible in header
- [ ] **Search Bar**: Renders with placeholder "Search installed skills..."
- [ ] **Stats Bar**: Shows "X skills installed" message
- [ ] **Grid Layout**: Responsive grid (1 col mobile, 2 col tablet, 3 col desktop)

#### State Management
- [ ] **Loading State**: Shows "Loading skills..." on initial mount
- [ ] **Empty State**: Shows when no skills installed
  - Package icon displays
  - "No skills installed" message
  - "Browse Marketplace" button appears
- [ ] **Search Empty State**: Shows when search has no results
  - "No skills found matching your search" message
  - No "Browse Marketplace" button (only for empty install)
- [ ] **Loaded State**: Grid of skill cards appears after loading

#### User Interactions
- [ ] **Search Input**: Typing filters skills in real-time
- [ ] **Search Functionality**:
  - Filters by skill name
  - Filters by skill description
  - Filters by skill category
  - Case-insensitive search
- [ ] **Refresh Button**:
  - Click triggers reload
  - Spinner animation during refresh
  - Button disabled while refreshing
  - List updates after refresh
- [ ] **Browse Marketplace Button**: Opens marketplace modal
- [ ] **Skills Counter**: Updates when search active ("X matching search")

#### Project Integration
- [ ] **User Skills**: Loads from ~/.claude/skills/
- [ ] **Project Skills**: Loads from .claude/skills/ when project selected
- [ ] **Project Change**: Skills refresh when switching projects
- [ ] **No Project**: Only shows user skills when no project selected

---

### SkillCard Component

#### Display Elements
- [ ] **Skill Name**: Displays correctly
- [ ] **Package Icon**: Shows before name
- [ ] **Source Badge**: Shows "user" or "project"
  - "user" badge: primary variant
  - "project" badge: secondary variant
- [ ] **Category Badge**: Shows when category exists (outline variant)
- [ ] **Description**: Truncates to 2 lines (line-clamp-2)
- [ ] **Preview Button**: Shows Eye icon with "Preview" text
- [ ] **Remove Button**: Shows Trash icon (destructive variant)

#### Interactions
- [ ] **Hover Effect**: Border changes to primary color on hover
- [ ] **Preview Click**: Opens SkillPreview modal
- [ ] **Remove Click**: Shows confirmation dialog
- [ ] **Button States**: Buttons properly clickable

---

### SkillPreview Component

#### Modal Behavior
- [ ] **Opens on Click**: Preview modal appears when clicking Preview button
- [ ] **Dialog Structure**: Uses shadcn Dialog component
- [ ] **Size**: Max width 4xl, max height 90vh
- [ ] **Overlay**: Background overlay appears

#### Content Display
- [ ] **Header**:
  - Package icon displayed
  - Skill name as title
  - Source badge (user/project)
  - Category badge (if exists)
  - Version badge (if exists)
- [ ] **Scroll Area**: Content scrollable within modal
- [ ] **Content Formatting**:
  - Markdown displayed in preformatted block
  - Code syntax preserved
  - Font: monospace
  - Background: muted/50

#### Loading States
- [ ] **Initial Load**: Shows Loader2 spinner with "Loading skill content..."
- [ ] **Success**: Content displays after load completes
- [ ] **Loading Indicator**: Spinner centered with animation

#### Error Handling
- [ ] **Error Display**: Shows AlertCircle icon with error message
- [ ] **Error Text**: Destructive color (red)
- [ ] **Missing File**: Shows appropriate error when SKILL.md not found
- [ ] **Permission Error**: Shows error when file not readable

#### Close Actions
- [ ] **X Button**: Closes modal
- [ ] **Overlay Click**: Closes modal
- [ ] **ESC Key**: Closes modal
- [ ] **State Cleanup**: Content cleared when closed and reopened

---

### SkillsMarketplace Component

#### Modal Structure
- [ ] **Opens on Click**: Marketplace modal appears
- [ ] **Size**: 90vw width, 90vh height
- [ ] **Title**: "Skills Marketplace"
- [ ] **Layout**: Header, search/filters, scrollable grid

#### Search Functionality
- [ ] **Search Input**: Placeholder shows total skill count
- [ ] **Search Icon**: Displays in input field
- [ ] **Real-time Filter**: Results update as user types
- [ ] **Search by Name**: Finds skills by name
- [ ] **Search by Description**: Finds skills by description
- [ ] **Case Insensitive**: Works regardless of case
- [ ] **Empty Results**: Shows "No skills found" message

#### Category Filtering
- [ ] **All Badge**: Shows total count, selected by default
- [ ] **Category Badges**: One for each category
  - Development
  - Creative Design
  - Business & Marketing
  - Scientific
- [ ] **Badge Counts**: Shows skill count per category
- [ ] **Click to Filter**: Category filter applies on click
- [ ] **Active State**: Selected category has default variant
- [ ] **Inactive State**: Unselected categories have outline variant
- [ ] **Combined Filters**: Search + category filter work together

#### Skills Grid
- [ ] **Responsive Layout**: 1/2/3 columns based on screen size
- [ ] **Skill Cards**:
  - Skill name displayed
  - Category badge shown
  - Description (max 3 lines, line-clamp-3)
  - Install button
- [ ] **Hover Effect**: Border color changes on hover
- [ ] **Empty State**: Shows when no skills match filters

#### Installation
- [ ] **Install Button**:
  - Shows Download icon + "Install" text
  - Primary variant when not installed
- [ ] **Installing State**:
  - Shows Loader2 spinner + "Installing..." text
  - Button disabled during installation
  - Only one skill installing at a time
- [ ] **Installed State**:
  - Shows Check icon + "Installed" text
  - Outline variant
  - Button disabled
- [ ] **Post-Install**: Main skills list updates automatically

#### Close Actions
- [ ] **X Button**: Closes marketplace
- [ ] **Overlay Click**: Closes marketplace
- [ ] **ESC Key**: Closes marketplace
- [ ] **After Install**: Modal can be closed, shows new skill in main list

---

## IPC Handler Verification

Test each IPC handler directly from the renderer console.

### skills:list

```javascript
// Test loading user skills only
await window.electronAPI.skills.list()

// Test loading user + project skills
await window.electronAPI.skills.list('/path/to/project')
```

**Expected:**
- Returns array of Skill objects
- Each skill has: name, description, source, path, category?, version?
- User skills have source: 'user'
- Project skills have source: 'project'

**Edge Cases:**
- [ ] No skills installed: Returns empty array
- [ ] Missing .claude directory: Returns empty array (no error)
- [ ] Invalid SKILL.md frontmatter: Skill skipped
- [ ] Missing required fields (name/description): Skill skipped

### skills:install

```javascript
// Test installing a skill
await window.electronAPI.skills.install('development/test-driven-development')
```

**Expected:**
- Returns { success: true, output: "..." }
- Skill appears in skills list after install
- Installation output logged to console

**Edge Cases:**
- [ ] Invalid skill path: Returns { success: false, error: "..." }
- [ ] Network error: Returns error with message
- [ ] Timeout (60s): Returns timeout error
- [ ] Already installed: Completes successfully (overwrites)

### skills:remove

```javascript
// Test removing a skill
await window.electronAPI.skills.remove('/path/to/skill')
```

**Expected:**
- Returns { success: true }
- Skill disappears from list
- Directory deleted from filesystem

**Edge Cases:**
- [ ] Invalid path: Returns { success: false, error: "..." }
- [ ] Permission error: Returns error message
- [ ] Path doesn't exist: Returns { success: true } (force: true)
- [ ] User confirmation required in UI (not IPC)

### skills:getContent

```javascript
// Test getting skill content
await window.electronAPI.skills.getContent('/path/to/skill')
```

**Expected:**
- Returns { success: true, data: { content: "..." } }
- Content is full SKILL.md text

**Edge Cases:**
- [ ] Missing SKILL.md: Returns { success: false, error: "..." }
- [ ] Permission error: Returns error
- [ ] Invalid path: Returns error

---

## Error Scenarios

Test how the UI handles various error conditions:

### Network Errors
- [ ] **Offline Install**: Disconnect internet, try to install skill
  - Expected: Error alert with network error message
  - Skills list unchanged

### Permission Errors
- [ ] **Read-Only Directory**: Make ~/.claude/skills read-only, try to install
  - Expected: Error alert with permission error
- [ ] **Protected File**: Make SKILL.md read-only, try to preview
  - Expected: Error message in preview modal

### Invalid Data
- [ ] **Corrupted SKILL.md**: Add invalid frontmatter to SKILL.md
  - Expected: Skill not listed (skipped during parsing)
- [ ] **Missing Required Fields**: Remove 'name' from frontmatter
  - Expected: Skill skipped
- [ ] **Empty Skills Directory**: Create skill directory without SKILL.md
  - Expected: Directory ignored

### Concurrent Operations
- [ ] **Multiple Installs**: Click install on multiple skills rapidly
  - Expected: Installs queue properly, UI shows correct states
- [ ] **Install During Refresh**: Start install, then click refresh
  - Expected: Operations don't interfere

### UI State Errors
- [ ] **Search with Special Characters**: Search for *, /, \, etc.
  - Expected: No crashes, valid filtering
- [ ] **Long Skill Names**: Test with very long skill names
  - Expected: UI remains stable, text truncates properly
- [ ] **Many Skills**: Test with 50+ skills installed
  - Expected: Grid scrolls, performance acceptable

---

## Performance Checks

### Load Times
- [ ] **Initial Load**: Skills list loads in < 2 seconds
- [ ] **Refresh**: Refresh completes in < 2 seconds
- [ ] **Search**: Filter results appear instantly (< 100ms)
- [ ] **Preview Load**: SKILL.md content loads in < 500ms
- [ ] **Install**: Installation completes in < 30 seconds

### Memory Usage
- [ ] **Open/Close Marketplace**: No memory leaks (check DevTools)
- [ ] **Preview Multiple Skills**: Memory stable across previews
- [ ] **Long Session**: App stable after 30+ minutes of use

### Rendering
- [ ] **Smooth Scrolling**: Grid scrolls smoothly with many skills
- [ ] **Hover Effects**: Transitions smooth, no jank
- [ ] **Modal Animations**: Open/close animations smooth

---

## Accessibility Checks

### Keyboard Navigation
- [ ] **Tab Order**: Logical tab order through UI
- [ ] **Search Input**: Focusable and clearable with keyboard
- [ ] **Buttons**: All buttons keyboard-accessible
- [ ] **Modal Focus**: Focus trapped in modals
- [ ] **ESC Key**: Closes modals

### Screen Reader
- [ ] **Button Labels**: All buttons have descriptive text/aria-labels
- [ ] **Icon-Only Buttons**: Have aria-label or title
- [ ] **Loading States**: Announced to screen readers
- [ ] **Error Messages**: Announced to screen readers
- [ ] **Status Updates**: Skills count changes announced

### Visual
- [ ] **Color Contrast**: All text meets WCAG AA standards
- [ ] **Focus Indicators**: Visible focus rings on interactive elements
- [ ] **Text Sizing**: Readable at default browser zoom
- [ ] **Responsive Text**: No text cut off at different sizes

### ARIA Attributes
- [ ] **Dialogs**: Have aria-labelledby and aria-describedby
- [ ] **Buttons**: Have appropriate aria-disabled states
- [ ] **Search**: Has aria-label
- [ ] **Badges**: Semantic meaning clear

---

## Cross-Platform Considerations

### macOS
- [ ] **Path Handling**: ~/.claude/skills/ resolves correctly
- [ ] **npx Command**: Executes without issues
- [ ] **File Permissions**: Read/write operations work
- [ ] **UI Layout**: Components render correctly

### Windows
- [ ] **Path Handling**: %USERPROFILE%/.claude/skills/ resolves
- [ ] **npx Command**: Works via npm (installed globally)
- [ ] **File Permissions**: No permission issues
- [ ] **UI Layout**: No platform-specific layout issues

### Linux
- [ ] **Path Handling**: ~/.claude/skills/ resolves
- [ ] **npx Command**: Executes correctly
- [ ] **File Permissions**: Standard Unix permissions work
- [ ] **UI Layout**: Renders correctly

### All Platforms
- [ ] **Path Separators**: Correctly handled (/ vs \)
- [ ] **Line Endings**: SKILL.md displays correctly (LF vs CRLF)
- [ ] **Font Rendering**: Monospace font renders in preview
- [ ] **Icons**: Lucide icons render on all platforms

---

## Test Results Template

Use this template to document test results:

```markdown
## Test Run: [Date]

**Tester:** [Name]
**Platform:** [macOS/Windows/Linux]
**Node Version:** [version]
**App Version:** [version]

### Pre-Flight Checklist
- [ ] TypeScript compilation: PASS/FAIL
- [ ] Build: PASS/FAIL
- [ ] Dependencies: PASS/FAIL
- [ ] Dev server: PASS/FAIL

### Component Testing

#### SkillsManager
- [ ] Component rendering: PASS/FAIL
- [ ] State management: PASS/FAIL
- [ ] User interactions: PASS/FAIL
- [ ] Project integration: PASS/FAIL

**Issues Found:**
- [Issue description]

#### SkillCard
- [ ] Display elements: PASS/FAIL
- [ ] Interactions: PASS/FAIL

**Issues Found:**
- [Issue description]

#### SkillPreview
- [ ] Modal behavior: PASS/FAIL
- [ ] Content display: PASS/FAIL
- [ ] Loading states: PASS/FAIL
- [ ] Error handling: PASS/FAIL

**Issues Found:**
- [Issue description]

#### SkillsMarketplace
- [ ] Modal structure: PASS/FAIL
- [ ] Search functionality: PASS/FAIL
- [ ] Category filtering: PASS/FAIL
- [ ] Skills grid: PASS/FAIL
- [ ] Installation: PASS/FAIL

**Issues Found:**
- [Issue description]

### IPC Handlers
- [ ] skills:list: PASS/FAIL
- [ ] skills:install: PASS/FAIL
- [ ] skills:remove: PASS/FAIL
- [ ] skills:getContent: PASS/FAIL

**Issues Found:**
- [Issue description]

### Error Scenarios
- [ ] Network errors: PASS/FAIL
- [ ] Permission errors: PASS/FAIL
- [ ] Invalid data: PASS/FAIL
- [ ] Concurrent operations: PASS/FAIL

**Issues Found:**
- [Issue description]

### Performance
- [ ] Load times: PASS/FAIL
- [ ] Memory usage: PASS/FAIL
- [ ] Rendering: PASS/FAIL

**Metrics:**
- Initial load: [time]
- Refresh: [time]
- Search: [time]
- Preview load: [time]

### Accessibility
- [ ] Keyboard navigation: PASS/FAIL
- [ ] Screen reader: PASS/FAIL
- [ ] Visual: PASS/FAIL
- [ ] ARIA attributes: PASS/FAIL

**Issues Found:**
- [Issue description]

### Cross-Platform
- [ ] Path handling: PASS/FAIL
- [ ] npx execution: PASS/FAIL
- [ ] File permissions: PASS/FAIL
- [ ] UI layout: PASS/FAIL

**Issues Found:**
- [Issue description]

### Overall Result
- **Total Tests:** [number]
- **Passed:** [number]
- **Failed:** [number]
- **Blocked:** [number]

### Critical Issues
1. [Issue description]

### Recommendations
1. [Recommendation]
```

---

## Automated Testing Recommendations

For future enhancement, consider adding:

### Unit Tests (Vitest)
```typescript
// Example: SkillCard.test.tsx
describe('SkillCard', () => {
  it('renders skill information correctly', () => {
    const skill = {
      name: 'test-skill',
      description: 'Test description',
      source: 'user',
      path: '/path/to/skill'
    }

    render(<SkillCard skill={skill} onPreview={() => {}} onRemove={() => {}} />)

    expect(screen.getByText('test-skill')).toBeInTheDocument()
    expect(screen.getByText('Test description')).toBeInTheDocument()
    expect(screen.getByText('user')).toBeInTheDocument()
  })
})
```

### Integration Tests (Playwright)
```typescript
// Example: skills-manager.spec.ts
test('should install skill from marketplace', async ({ page }) => {
  await page.click('[data-testid="browse-marketplace"]')
  await page.click('[data-testid="install-skill-test-driven-development"]')

  await expect(page.locator('[data-testid="skill-card-test-driven-development"]')).toBeVisible()
})
```

### E2E Tests
- Full workflow: Browse > Search > Install > Preview > Remove
- Multi-skill operations
- Project switching scenarios

---

## Conclusion

This comprehensive testing guide covers all aspects of the Skills Manager UI. Follow this checklist before each release to ensure quality and reliability.

For questions or to report issues, see:
- **GitHub Issues**: https://github.com/AndyMik90/Auto-Claude/issues
- **Technical Docs**: /auto-claude-ui/docs/SKILLS_MANAGER.md
