/**
 * Unit tests for MCPServerCard component
 * Tests capabilities view integration
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MCPServerCard } from '../MCPServerCard';
import type { MCPServer } from '../../../../shared/types/mcp';

describe('MCPServerCard - Capabilities View', () => {
  const mockServer: MCPServer = {
    id: 'context7',
    name: 'Context7',
    description: 'Documentation lookup',
    type: 'builtin',
    category: 'Documentation',
    status: 'connected',
    enabled: true,
    toolCount: 2,
    promptCount: 0,
    resourceCount: 0,
    connectionType: 'sdk',
    icon: 'Book',
    capabilities: {
      tools: [
        {
          name: 'mcp__context7__resolve-library-id',
          displayName: 'Resolve Library ID',
          description: 'Resolve library name to ID'
        }
      ]
    },
    requiredEnvVars: []
  };

  it('replaces placeholder with MCPCapabilitiesView', () => {
    render(<MCPServerCard server={mockServer} onConfigure={() => {}} />);

    fireEvent.click(screen.getByText(/Show Details/));

    expect(screen.queryByText('Capabilities view coming soon...')).toBeNull();
    expect(screen.getByText('🔧 Tools (2)')).toBeTruthy();
  });

  it('shows actual tool details when expanded', () => {
    render(<MCPServerCard server={mockServer} onConfigure={() => {}} />);

    fireEvent.click(screen.getByText(/Show Details/));

    expect(screen.getByText('Resolve Library ID')).toBeTruthy();
  });
});
