import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { Sidebar } from '../Sidebar';

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

describe('Sidebar Navigation', () => {
  it('renders analytics navigation item', () => {
    render(
      <Sidebar
        onSettingsClick={() => {}}
        onNewTaskClick={() => {}}
        activeView="kanban"
        onViewChange={() => {}}
      />
    );

    expect(screen.getByText(/analytics/i)).toBeInTheDocument();
  });
});
