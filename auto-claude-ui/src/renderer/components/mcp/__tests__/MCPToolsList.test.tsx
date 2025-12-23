/**
 * Unit tests for MCPToolsList component
 * Tests tool rendering, expansion, and clipboard functionality
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MCPToolsList } from '../MCPToolsList';
import type { MCPTool } from '../../../../shared/types/mcp';

describe('MCPToolsList', () => {
  const mockTools: MCPTool[] = [
    {
      name: 'mcp__test__analyze_code',
      displayName: 'Analyze Code',
      description: 'Analyzes code quality',
      parameters: [
        {
          name: 'file_path',
          type: 'string',
          required: true,
          description: 'Path to file'
        },
        {
          name: 'rules',
          type: 'array',
          required: false,
          description: 'Lint rules',
          default: []
        }
      ]
    }
  ];

  it('renders list of tools', () => {
    render(<MCPToolsList tools={mockTools} />);
    expect(screen.getByText('Analyze Code')).toBeTruthy();
  });

  it('expands tool to show parameters', () => {
    render(<MCPToolsList tools={mockTools} />);

    const expandButton = screen.getByText(/Analyze Code/);
    fireEvent.click(expandButton);

    expect(screen.getByText('Parameters:')).toBeTruthy();
    expect(screen.getByText('file_path')).toBeTruthy();
    expect(screen.getByText('(string)')).toBeTruthy();
  });

  it('copies tool name to clipboard', async () => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined)
      }
    });

    render(<MCPToolsList tools={mockTools} />);

    const copyButton = screen.getByTitle('Copy tool name');
    fireEvent.click(copyButton);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('mcp__test__analyze_code');
  });
});
