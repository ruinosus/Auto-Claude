# BMAD Integration Implementation Plan

**Date:** December 28, 2025
**Status:** Planning
**Branch:** `feat/bmad-integration-analysis`

---

## Executive Summary

This document outlines the plan to integrate BMAD (Business Method for Agile Development) from the upstream repository into our fork. Due to directory structure differences, we'll adapt the code rather than merge directly.

### Directory Mapping

| Upstream (AndyMik90) | Our Fork |
|---------------------|----------|
| `auto-claude/` | `apps/backend/` |
| `auto-claude-ui/` | `apps/frontend/` |

---

## Phase 1: Backend Infrastructure (~4,170 lines)

### 1.1 Create Adapters Package
**New files to create in `apps/backend/adapters/`:**

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | ~20 | Package exports |
| `base.py` | 114 | Abstract FrameworkAdapter class |
| `exceptions.py` | 63 | ParseError, AdapterError |
| `glossary.py` | 36 | Terminology mappings |
| `factory.py` | ~50 | Adapter factory function |

**Subdirectories:**

```
apps/backend/adapters/
├── __init__.py
├── base.py
├── exceptions.py
├── glossary.py
├── factory.py
├── bmad/
│   ├── __init__.py (63 lines)
│   ├── adapter.py (223 lines)
│   └── parser.py (704 lines)
└── native/
    ├── __init__.py
    └── parser.py (existing spec parsing)
```

### 1.2 Create BMAD Core Modules
**New files to create in `apps/backend/`:**

| File | Lines | Purpose |
|------|-------|---------|
| `bmad_config.py` | 218 | BMAD configuration management |
| `bmad_detector.py` | 313 | Framework detection logic |
| `bmad_engine.py` | 561 | Core BMAD workflow engine |
| `bmad_enhancements.py` | 267 | Enhanced BMAD features |
| `bmad_installer.py` | 338 | BMAD installation utilities |
| `bmad_planning.py` | 159 | Planning workflow execution |
| `bmad_state.py` | 241 | State management |
| `bmad_task_integration.py` | 660 | Main integration module |
| `bmad_updater.py` | 198 | BMAD update utilities |

### 1.3 Create Unified Models
**New files in `apps/backend/models/`:**

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | ~30 | Model exports |
| `enums.py` | ~80 | Status enums (pending, in_progress, etc.) |
| `unified.py` | ~150 | WorkUnit, Task, Checkpoint, ProjectStatus |

### 1.4 Update CLI Commands
**Modify `apps/backend/cli/`:**

| File | Action | Changes |
|------|--------|---------|
| `main.py` | Modify | Add `--framework` argument |
| `build_commands.py` | Modify | Add framework routing logic |
| `bmad_commands.py` | Create | BMAD-specific CLI commands |
| `workflow_commands.py` | Create | Workflow management commands |

### 1.5 Update Runners
**Modify `apps/backend/runners/`:**

| File | Action | Changes |
|------|--------|---------|
| `spec_runner.py` | Modify | Add framework routing, BMAD planning |

---

## Phase 2: Frontend Integration

### 2.1 Add Framework Store
**New file: `apps/frontend/src/renderer/stores/framework-store.ts`**
- Zustand store for framework selection state
- Persisted to localStorage

### 2.2 Create Framework Components
**New components in `apps/frontend/src/renderer/components/`:**

| Component | Purpose |
|-----------|---------|
| `onboarding/FrameworkSelector.tsx` | Framework selection cards |
| `onboarding/FrameworkStep.tsx` | Onboarding wizard step |
| `project-settings/FrameworkSettings.tsx` | Settings panel for framework |
| `project-settings/FrameworkChangeDialog.tsx` | Confirmation dialog |
| `ui/StatusBadge.tsx` | Unified status badges |
| `WorkflowProgress.tsx` | BMAD workflow progress display |
| `BmadConfigDialog.tsx` | BMAD configuration dialog |

### 2.3 Update Existing Components
**Modify:**

| Component | Changes |
|-----------|---------|
| `OnboardingWizard.tsx` | Add framework selection step |
| `TaskCard.tsx` | Show framework-specific terminology |
| `TaskSubtasks.tsx` | Support BMAD stories display |
| `TaskDetailPanel.tsx` | Framework-aware detail view |
| `SectionRouter.tsx` | Add framework settings section |
| `ProjectSettingsContent.tsx` | Include FrameworkSettings |

### 2.4 Add Context and Hooks
**New files:**

| File | Purpose |
|------|---------|
| `contexts/GlossaryContext.tsx` | Provide framework terminology |
| `hooks/useStatusPolling.ts` | Poll BMAD workflow status |

### 2.5 Update Types
**Modify `apps/frontend/src/shared/types/`:**

| File | Changes |
|------|---------|
| `project.ts` | Add `framework: 'bmad' | 'native'` to ProjectSettings |
| `status.ts` | Create unified status types |
| `glossary.ts` | Create glossary types |

### 2.6 Update IPC Handlers
**New handlers in `apps/frontend/src/main/ipc-handlers/`:**

| File | Purpose |
|------|---------|
| `bmad-handlers.ts` | BMAD-specific IPC handlers |

**Modify:**
- `task/execution-handlers.ts` - Pass framework to backend

### 2.7 Update Agent Manager
**Modify `apps/frontend/src/main/agent/`:**

| File | Changes |
|------|---------|
| `types.ts` | Add framework to TaskExecutionOptions |
| `agent-manager.ts` | Pass `--framework` flag to Python CLI |

---

## Phase 3: Integration & Testing

### 3.1 Create Test Fixtures
**New in `tests/fixtures/`:**

```
tests/fixtures/
├── bmad/
│   ├── stories/
│   │   └── 1-1-test-story.md
│   └── valid-sprint-status.yaml
└── native/
    └── 001-sample/
        ├── implementation_plan.json
        └── spec.md
```

### 3.2 Create Tests
**New test files:**

| Test File | Coverage |
|-----------|----------|
| `test_adapters.py` | Adapter infrastructure |
| `test_bmad_adapter.py` | BMAD adapter |
| `test_bmad_parser.py` | BMAD parsing |
| `test_native_parser.py` | Native adapter |
| `test_routing.py` | Framework routing |
| `test_models.py` | Unified models |

### 3.3 E2E Testing
- Framework selection flow
- BMAD planning workflow
- BMAD development workflow
- Framework switching

---

## Implementation Order

### Sprint 1: Backend Foundation (Days 1-3)

1. **Day 1: Models & Adapters Base**
   - [ ] Create `apps/backend/models/` package
   - [ ] Create `apps/backend/adapters/` base infrastructure
   - [ ] Create adapter exceptions and glossary

2. **Day 2: BMAD Adapter**
   - [ ] Create `apps/backend/adapters/bmad/` package
   - [ ] Implement BMAD parser
   - [ ] Implement BMAD adapter

3. **Day 3: BMAD Core**
   - [ ] Create `bmad_config.py`
   - [ ] Create `bmad_detector.py`
   - [ ] Create `bmad_state.py`

### Sprint 2: BMAD Engine (Days 4-6)

4. **Day 4: Planning & Engine**
   - [ ] Create `bmad_planning.py`
   - [ ] Create `bmad_engine.py`

5. **Day 5: Integration**
   - [ ] Create `bmad_task_integration.py`
   - [ ] Modify `spec_runner.py` for framework routing

6. **Day 6: CLI & Commands**
   - [ ] Create `bmad_commands.py`
   - [ ] Modify `main.py` and `build_commands.py`

### Sprint 3: Frontend (Days 7-10)

7. **Day 7: Types & Store**
   - [ ] Update TypeScript types
   - [ ] Create framework store

8. **Day 8: Components**
   - [ ] Create FrameworkSelector
   - [ ] Create FrameworkSettings
   - [ ] Create StatusBadge

9. **Day 9: Integration**
   - [ ] Update OnboardingWizard
   - [ ] Update IPC handlers
   - [ ] Update agent-manager

10. **Day 10: Polish**
    - [ ] Add translations (EN/FR)
    - [ ] Context and hooks
    - [ ] Testing

### Sprint 4: Testing & Documentation (Days 11-12)

11. **Day 11: Tests**
    - [ ] Backend unit tests
    - [ ] Frontend component tests

12. **Day 12: Documentation**
    - [ ] Update CLAUDE.md
    - [ ] Create BMAD user guide
    - [ ] E2E testing

---

## Dependencies

### Python Packages (if needed)
```
pyyaml  # For BMAD YAML parsing (already in requirements)
```

### No New NPM Packages Required
- Uses existing Zustand for state management
- Uses existing shadcn/ui components

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Import path differences | High | Careful path mapping during adaptation |
| Missing dependencies | Medium | Check upstream requirements.txt |
| UI component differences | Medium | Adapt to our shadcn/ui components |
| Test fixture differences | Low | Create new fixtures based on our structure |

---

## Success Criteria

1. **Framework Selection**: Users can choose BMAD or Native in settings
2. **BMAD Planning**: Task creation routes to BMAD workflows when selected
3. **Unified Storage**: All artifacts in `.auto-claude/specs/XXX/`
4. **Compatible Plans**: `implementation_plan.json` works with both frameworks
5. **Seamless Switching**: Users can switch frameworks per-project
6. **Full Test Coverage**: All new code has unit tests

---

## Files Summary

### Backend (Python) - ~4,500 lines total
- New files: ~15 files
- Modified files: ~5 files

### Frontend (TypeScript/React) - ~2,000 lines total
- New files: ~12 files
- Modified files: ~10 files

### Tests - ~1,500 lines total
- New test files: ~15 files
- New fixtures: ~5 files

**Total Estimated LOC: ~8,000 lines**

---

## Next Steps

1. Review this plan with stakeholder
2. Create feature branch: `feat/bmad-integration`
3. Begin Sprint 1 implementation
4. Regular progress checkpoints

---

## Reference

- **Upstream Branch:** https://github.com/AndyMik90/Auto-Claude/tree/feat/bmad-integration
- **Upstream Cloned To:** `/Users/jefferson.barnabe/projects/misc/Auto-Claude-upstream`
- **Our Fork:** `/Users/jefferson.barnabe/projects/misc/auto-claude-fork-clean`
