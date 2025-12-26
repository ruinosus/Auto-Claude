import { describe, it, expect } from 'vitest';

describe('SidebarView Type', () => {
  it('includes analytics in SidebarView type', () => {
    // Type test - will fail at compile if 'analytics' not in type
    const validViews: Array<import('../Sidebar').SidebarView> = [
      'kanban',
      'terminals',
      'roadmap',
      'context',
      'ideation',
      'github-issues',
      'github-prs',
      'changelog',
      'insights',
      'worktrees',
      'agent-tools',
      'analytics' // Should be valid
    ];

    expect(validViews).toHaveLength(12);
  });
});
