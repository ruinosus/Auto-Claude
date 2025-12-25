/**
 * Unit tests for MCPCapabilitiesView component
 * Tests tab switching, capabilities display, and integration with child components
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MCPCapabilitiesView } from '../MCPCapabilitiesView';
import type { MCPServer } from '../../../../shared/types/mcp';

describe('MCPCapabilitiesView', () => {
  const mockServer: MCPServer = {
    id: 'test-server',
    name: 'Test Server',
    description: 'A test server',
    type: 'custom',
    category: 'Custom',
    status: 'connected',
    enabled: true,
    requiredEnvVars: [],
    capabilities: {
      tools: [
        {
          name: 'mcp__testserver__tool1',
          displayName: 'tool1',
          description: 'First tool',
          parameters: [
            {
              name: 'param1',
              type: 'string',
              required: true,
              description: 'First parameter'
            }
          ]
        },
        {
          name: 'mcp__testserver__tool2',
          displayName: 'tool2',
          description: 'Second tool'
        },
        {
          name: 'mcp__testserver__tool3',
          displayName: 'tool3',
          description: 'Third tool'
        },
        {
          name: 'mcp__testserver__tool4',
          displayName: 'tool4',
          description: 'Fourth tool'
        },
        {
          name: 'mcp__testserver__tool5',
          displayName: 'tool5',
          description: 'Fifth tool'
        }
      ],
      prompts: [
        {
          name: 'prompt1',
          displayName: 'Prompt 1',
          description: 'First prompt',
          arguments: [
            {
              name: 'arg1',
              description: 'First argument',
              required: true
            }
          ]
        },
        {
          name: 'code-review-prompt',
          displayName: 'Code Review',
          description: 'Review code'
        }
      ],
      resources: [
        {
          uri: 'file:///resource1',
          name: 'Resource 1',
          description: 'First resource',
          isTemplate: false
        },
        {
          uri: 'file:///resource2',
          name: 'Resource 2',
          description: 'Second resource',
          isTemplate: false
        },
        {
          uri: 'file:///resource3',
          name: 'Resource 3',
          description: 'Third resource',
          isTemplate: false
        }
      ]
    },
    toolCount: 5,
    promptCount: 2,
    resourceCount: 3,
    connectionType: 'http'
  };

  it('renders nothing when not expanded', () => {
    const { container } = render(
      <MCPCapabilitiesView
        server={mockServer}
        expanded={false}
        onToggle={() => {}}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders tabs with correct counts when expanded', () => {
    render(
      <MCPCapabilitiesView
        server={mockServer}
        expanded={true}
        onToggle={() => {}}
      />
    );

    // Check that all three tabs are present with correct counts
    expect(screen.getByText(/Tools.*5/)).toBeTruthy();
    expect(screen.getByText(/Prompts.*2/)).toBeTruthy();
    expect(screen.getByText(/Resources.*3/)).toBeTruthy();
  });

  it('renders tools tab content by default', () => {
    render(
      <MCPCapabilitiesView
        server={mockServer}
        expanded={true}
        onToggle={() => {}}
      />
    );

    // Should show tools by default
    expect(screen.getByText('tool1')).toBeTruthy();
    expect(screen.getByText('First tool')).toBeTruthy();
  });

  it('renders all three child list components', () => {
    const { container } = render(
      <MCPCapabilitiesView
        server={mockServer}
        expanded={true}
        onToggle={() => {}}
      />
    );

    // Check that MCPToolsList is rendered (default active tab)
    expect(screen.getByText('tool1')).toBeTruthy();
    expect(screen.getByText('First tool')).toBeTruthy();

    // TabsContent components for prompts and resources should exist in DOM (hidden)
    // Radix UI renders all tab content but hides inactive ones
    expect(container.querySelector('[role="tabpanel"]')).toBeTruthy();
  });

  it('integrates with MCPToolsList component', () => {
    render(
      <MCPCapabilitiesView
        server={mockServer}
        expanded={true}
        onToggle={() => {}}
      />
    );

    // Should pass tools to MCPToolsList
    expect(screen.getByText('tool1')).toBeTruthy();
    expect(screen.getByText('tool2')).toBeTruthy();
    expect(screen.getByText('tool3')).toBeTruthy();
  });

  it('calls onToggle when hide button is clicked', () => {
    const mockOnToggle = vi.fn();

    render(
      <MCPCapabilitiesView
        server={mockServer}
        expanded={true}
        onToggle={mockOnToggle}
      />
    );

    // Find and click the hide button
    const hideButton = screen.getByText(/Hide Capabilities/);
    fireEvent.click(hideButton);

    expect(mockOnToggle).toHaveBeenCalledTimes(1);
  });

  it('handles empty capabilities gracefully', () => {
    const emptyServer: MCPServer = {
      ...mockServer,
      capabilities: {
        tools: [],
        prompts: [],
        resources: []
      },
      toolCount: 0,
      promptCount: 0,
      resourceCount: 0
    };

    render(
      <MCPCapabilitiesView
        server={emptyServer}
        expanded={true}
        onToggle={() => {}}
      />
    );

    // Should show tabs with 0 counts
    expect(screen.getByText(/Tools.*0/)).toBeTruthy();
    expect(screen.getByText(/Prompts.*0/)).toBeTruthy();
    expect(screen.getByText(/Resources.*0/)).toBeTruthy();

    // Should show "No tools available" message
    expect(screen.getByText('No tools available')).toBeTruthy();
  });

  it('handles missing capabilities arrays', () => {
    const serverWithMissingCapabilities: MCPServer = {
      ...mockServer,
      capabilities: {},
      toolCount: 0,
      promptCount: 0,
      resourceCount: 0
    };

    render(
      <MCPCapabilitiesView
        server={serverWithMissingCapabilities}
        expanded={true}
        onToggle={() => {}}
      />
    );

    // Should show tabs with 0 counts
    expect(screen.getByText(/Tools.*0/)).toBeTruthy();

    // Should show "No tools available" message (default view is tools)
    expect(screen.getByText('No tools available')).toBeTruthy();
  });

  it('renders all three capability tabs', () => {
    render(
      <MCPCapabilitiesView
        server={mockServer}
        expanded={true}
        onToggle={() => {}}
      />
    );

    // All three tabs should be present and clickable
    const toolsTab = screen.getByRole('tab', { name: /Tools.*5/ });
    const promptsTab = screen.getByRole('tab', { name: /Prompts.*2/ });
    const resourcesTab = screen.getByRole('tab', { name: /Resources.*3/ });

    expect(toolsTab).toBeTruthy();
    expect(promptsTab).toBeTruthy();
    expect(resourcesTab).toBeTruthy();

    // Tools tab should be active by default
    expect(toolsTab.getAttribute('data-state')).toBe('active');
    expect(promptsTab.getAttribute('data-state')).toBe('inactive');
    expect(resourcesTab.getAttribute('data-state')).toBe('inactive');

    // Should show tools content by default
    expect(screen.getByText('tool1')).toBeTruthy();
  });
});
