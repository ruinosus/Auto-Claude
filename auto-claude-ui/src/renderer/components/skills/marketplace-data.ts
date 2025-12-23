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

// Hardcoded marketplace data from claude-code-templates
// This represents a curated subset of the most popular skills from the marketplace
export const MARKETPLACE_CATEGORIES: SkillCategory[] = [
  {
    name: 'development',
    displayName: 'Development',
    count: 52,
    skills: [
      {
        name: 'test-driven-development',
        description: 'Implements features using TDD methodology (write tests first, then implementation)',
        category: 'development',
        path: 'development/test-driven-development'
      },
      {
        name: 'systematic-debugging',
        description: 'Four-phase debugging framework (root cause → pattern analysis → hypothesis testing → implementation)',
        category: 'development',
        path: 'development/systematic-debugging'
      },
      {
        name: 'code-reviewer',
        description: 'Comprehensive code review focusing on security, performance, maintainability, and best practices',
        category: 'development',
        path: 'development/code-reviewer'
      },
      {
        name: 'root-cause-tracing',
        description: 'Systematically trace bugs backward through call stack to identify source of invalid data',
        category: 'development',
        path: 'development/root-cause-tracing'
      },
      {
        name: 'testing-anti-patterns',
        description: 'Prevents testing mock behavior, production pollution, and mocking without understanding',
        category: 'development',
        path: 'development/testing-anti-patterns'
      },
      {
        name: 'verification-before-completion',
        description: 'Requires running verification commands before claiming work is complete',
        category: 'development',
        path: 'development/verification-before-completion'
      },
      {
        name: 'defense-in-depth',
        description: 'Validates data at every layer to make bugs structurally impossible',
        category: 'development',
        path: 'development/defense-in-depth'
      },
      {
        name: 'condition-based-waiting',
        description: 'Replaces arbitrary timeouts with condition polling to eliminate flaky tests',
        category: 'development',
        path: 'development/condition-based-waiting'
      }
    ]
  },
  {
    name: 'creative-design',
    displayName: 'Creative Design',
    count: 9,
    skills: [
      {
        name: 'frontend-design',
        description: 'Create distinctive, production-grade frontend interfaces with high design quality',
        category: 'creative-design',
        path: 'creative-design/frontend-design'
      },
      {
        name: 'ui-systems',
        description: 'Build consistent design systems with reusable components',
        category: 'creative-design',
        path: 'creative-design/ui-systems'
      }
    ]
  },
  {
    name: 'business-marketing',
    displayName: 'Business & Marketing',
    count: 12,
    skills: [
      {
        name: 'marketing-campaigns',
        description: 'Create effective marketing campaigns with clear messaging',
        category: 'business-marketing',
        path: 'business-marketing/marketing-campaigns'
      },
      {
        name: 'brainstorming',
        description: 'Refines rough ideas into fully-formed designs through collaborative questioning',
        category: 'business-marketing',
        path: 'business-marketing/brainstorming'
      }
    ]
  },
  {
    name: 'scientific',
    displayName: 'Scientific',
    count: 136,
    skills: [
      {
        name: 'data-analysis',
        description: 'Analyze data sets using statistical methods and visualization',
        category: 'scientific',
        path: 'scientific/data-analysis'
      }
    ]
  },
  {
    name: 'workflow',
    displayName: 'Workflow',
    count: 38,
    skills: [
      {
        name: 'write-plan',
        description: 'Create detailed implementation plan with bite-sized tasks',
        category: 'workflow',
        path: 'workflow/write-plan'
      },
      {
        name: 'execute-plan',
        description: 'Execute plan in batches with review checkpoints',
        category: 'workflow',
        path: 'workflow/execute-plan'
      },
      {
        name: 'using-git-worktrees',
        description: 'Creates isolated git worktrees with smart directory selection and safety verification',
        category: 'workflow',
        path: 'workflow/using-git-worktrees'
      },
      {
        name: 'finishing-development-branch',
        description: 'Guides completion of development work with structured options for merge, PR, or cleanup',
        category: 'workflow',
        path: 'workflow/finishing-development-branch'
      }
    ]
  }
]
