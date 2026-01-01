/**
 * Unit tests for MCPResourcesList component
 * Tests resource rendering, URI display, template indicators, and copy functionality
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MCPResourcesList } from '../MCPResourcesList';
import type { MCPResource } from '../../../../shared/types/mcp';

describe('MCPResourcesList', () => {
  const mockResources: MCPResource[] = [
    {
      uri: 'file:///user/docs/readme.md',
      name: 'Project README',
      description: 'Main project documentation',
      mimeType: 'text/markdown',
      isTemplate: false
    },
    {
      uri: 'file:///user/{project}/config.json',
      name: 'Project Config',
      description: 'Configuration file for project',
      mimeType: 'application/json',
      isTemplate: true,
      templateParams: ['project']
    },
    {
      uri: 'https://api.example.com/{userId}/profile',
      name: 'User Profile API',
      description: 'Fetch user profile data',
      isTemplate: true,
      templateParams: ['userId']
    },
    {
      uri: 'memory://context/{sessionId}',
      name: 'Session Context',
      isTemplate: true,
      templateParams: ['sessionId']
    }
  ];

  it('renders list of resources', () => {
    render(<MCPResourcesList resources={mockResources} serverId="test-server" />);
    expect(screen.getByText('Project README')).toBeTruthy();
    expect(screen.getByText('Project Config')).toBeTruthy();
    expect(screen.getByText('User Profile API')).toBeTruthy();
    expect(screen.getByText('Session Context')).toBeTruthy();
  });

  it('displays resource URIs in code format', () => {
    render(<MCPResourcesList resources={mockResources} serverId="test-server" />);
    expect(screen.getByText('file:///user/docs/readme.md')).toBeTruthy();
    expect(screen.getByText('file:///user/{project}/config.json')).toBeTruthy();
  });

  it('displays resource descriptions when provided', () => {
    render(<MCPResourcesList resources={mockResources} serverId="test-server" />);
    expect(screen.getByText('Main project documentation')).toBeTruthy();
    expect(screen.getByText('Configuration file for project')).toBeTruthy();
    expect(screen.getByText('Fetch user profile data')).toBeTruthy();
  });

  it('shows Template badge for template resources', () => {
    render(<MCPResourcesList resources={mockResources} serverId="test-server" />);

    // Should have 3 template badges (resources with isTemplate: true)
    const templateBadges = screen.getAllByText('Template');
    expect(templateBadges).toHaveLength(3);
  });

  it('does not show Template badge for non-template resources', () => {
    const nonTemplateResources: MCPResource[] = [
      {
        uri: 'file:///user/docs/readme.md',
        name: 'Project README',
        isTemplate: false
      }
    ];

    render(<MCPResourcesList resources={nonTemplateResources} serverId="test-server" />);

    expect(screen.queryByText('Template')).toBeNull();
  });

  it('displays MIME type when provided', () => {
    render(<MCPResourcesList resources={mockResources} serverId="test-server" />);
    expect(screen.getByText(/Type: text\/markdown/)).toBeTruthy();
    expect(screen.getByText(/Type: application\/json/)).toBeTruthy();
  });

  it('displays template parameters when provided', () => {
    render(<MCPResourcesList resources={mockResources} serverId="test-server" />);

    // Check for parameter displays
    expect(screen.getByText(/Parameters:.*\{project\}/)).toBeTruthy();
    expect(screen.getByText(/Parameters:.*\{userId\}/)).toBeTruthy();
    expect(screen.getByText(/Parameters:.*\{sessionId\}/)).toBeTruthy();
  });

  it('shows copy URI button for each resource', () => {
    render(<MCPResourcesList resources={mockResources} serverId="test-server" />);

    // Should have copy buttons - one for each resource
    const copyButtons = screen.getAllByTitle('Copy URI');
    expect(copyButtons).toHaveLength(4);
  });

  it('handles click on copy URI button', () => {
    // Mock clipboard API
    const mockWriteText = vi.fn();
    Object.assign(navigator, {
      clipboard: {
        writeText: mockWriteText
      }
    });

    render(<MCPResourcesList resources={mockResources} serverId="test-server" />);

    const copyButtons = screen.getAllByTitle('Copy URI');
    fireEvent.click(copyButtons[0]);

    // Should copy the URI to clipboard
    expect(mockWriteText).toHaveBeenCalledWith('file:///user/docs/readme.md');
  });

  it('displays empty state when no resources provided', () => {
    render(<MCPResourcesList resources={[]} serverId="test-server" />);
    expect(screen.getByText('No resources available')).toBeTruthy();
  });

  it('handles resources without description', () => {
    const resourcesWithoutDescription: MCPResource[] = [
      {
        uri: 'file:///test.txt',
        name: 'Test Resource',
        isTemplate: false
      }
    ];

    render(<MCPResourcesList resources={resourcesWithoutDescription} serverId="test-server" />);
    expect(screen.getByText('Test Resource')).toBeTruthy();
    expect(screen.getByText('file:///test.txt')).toBeTruthy();
  });

  it('handles resources without MIME type', () => {
    const resourcesWithoutMimeType: MCPResource[] = [
      {
        uri: 'file:///test.txt',
        name: 'Test Resource',
        description: 'A test resource',
        isTemplate: false
      }
    ];

    render(<MCPResourcesList resources={resourcesWithoutMimeType} serverId="test-server" />);

    // Should not show "Type:" section
    expect(screen.queryByText(/Type:/)).toBeNull();
  });

  it('handles template resources without templateParams array', () => {
    const templateResourcesWithoutParams: MCPResource[] = [
      {
        uri: 'file:///{project}/test.txt',
        name: 'Test Template',
        isTemplate: true
      }
    ];

    render(<MCPResourcesList resources={templateResourcesWithoutParams} serverId="test-server" />);
    expect(screen.getByText('Test Template')).toBeTruthy();
    expect(screen.getByText('Template')).toBeTruthy();
  });

  it('handles multiple template parameters', () => {
    const multiParamResources: MCPResource[] = [
      {
        uri: 'api://{org}/{repo}/issues/{issueId}',
        name: 'Issue Resource',
        isTemplate: true,
        templateParams: ['org', 'repo', 'issueId']
      }
    ];

    render(<MCPResourcesList resources={multiParamResources} serverId="test-server" />);

    // Should show all parameters comma-separated
    const paramsText = screen.getByText(/Parameters:/);
    expect(paramsText.textContent).toContain('{org}');
    expect(paramsText.textContent).toContain('{repo}');
    expect(paramsText.textContent).toContain('{issueId}');
  });

  it('uses URI as key for rendering', () => {
    const { container } = render(<MCPResourcesList resources={mockResources} serverId="test-server" />);

    // Each resource should be in its own container
    const resourceCards = container.querySelectorAll('.border.rounded');
    expect(resourceCards.length).toBe(4);
  });
});
