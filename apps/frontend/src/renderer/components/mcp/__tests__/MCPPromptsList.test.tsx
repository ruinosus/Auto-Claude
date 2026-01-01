/**
 * Unit tests for MCPPromptsList component
 * Tests prompt rendering, template preview, and "Use this prompt" button
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MCPPromptsList } from '../MCPPromptsList';
import type { MCPPrompt } from '../../../../shared/types/mcp';

describe('MCPPromptsList', () => {
  const mockPrompts: MCPPrompt[] = [
    {
      name: 'test_prompt',
      displayName: 'Test Prompt',
      description: 'A test prompt for testing',
      arguments: [
        {
          name: 'user_name',
          description: 'Name of the user',
          required: true
        },
        {
          name: 'context',
          description: 'Additional context',
          required: false
        }
      ],
      template: 'Hello {{user_name}}!\n\nThis is a test prompt.\nWith multiple lines.\nAnd even more lines.\nTo test the preview feature.'
    },
    {
      name: 'simple_prompt',
      displayName: 'Simple Prompt',
      description: 'A simple prompt without arguments',
      template: 'This is a simple prompt'
    }
  ];

  it('renders list of prompts', () => {
    render(<MCPPromptsList prompts={mockPrompts} serverId="test-server" />);
    expect(screen.getByText('Test Prompt')).toBeTruthy();
    expect(screen.getByText('Simple Prompt')).toBeTruthy();
  });

  it('displays prompt descriptions', () => {
    render(<MCPPromptsList prompts={mockPrompts} serverId="test-server" />);
    expect(screen.getByText('A test prompt for testing')).toBeTruthy();
    expect(screen.getByText('A simple prompt without arguments')).toBeTruthy();
  });

  it('shows arguments with required indicator', () => {
    render(<MCPPromptsList prompts={mockPrompts} serverId="test-server" />);

    expect(screen.getByText('Arguments:')).toBeTruthy();
    expect(screen.getByText('user_name')).toBeTruthy();
    expect(screen.getByText('context')).toBeTruthy();

    // Required argument should have asterisk
    const userNameCode = screen.getByText('user_name');
    const parent = userNameCode.closest('span');
    expect(parent?.innerHTML).toContain('*');
  });

  it('shows template preview with first 3 lines', () => {
    render(<MCPPromptsList prompts={mockPrompts} serverId="test-server" />);

    const templatePreview = screen.getByText(/Hello {{user_name}}!/);
    expect(templatePreview).toBeTruthy();

    // Should show "..." for truncated content
    expect(templatePreview.textContent).toContain('...');
  });

  it('shows "Use this prompt" button for each prompt', () => {
    render(<MCPPromptsList prompts={mockPrompts} serverId="test-server" />);

    const usePromptButtons = screen.getAllByText(/Use this prompt/);
    expect(usePromptButtons).toHaveLength(2);
  });

  it('handles click on "Use this prompt" button', () => {
    render(<MCPPromptsList prompts={mockPrompts} serverId="test-server" />);

    const usePromptButtons = screen.getAllByText(/Use this prompt/);

    // Click first button - should not throw
    expect(() => fireEvent.click(usePromptButtons[0])).not.toThrow();
  });

  it('displays empty state when no prompts provided', () => {
    render(<MCPPromptsList prompts={[]} serverId="test-server" />);
    expect(screen.getByText('No prompts available')).toBeTruthy();
  });

  it('handles prompts without templates', () => {
    const promptsWithoutTemplate: MCPPrompt[] = [
      {
        name: 'no_template',
        displayName: 'No Template',
        description: 'Prompt without template',
        arguments: []
      }
    ];

    render(<MCPPromptsList prompts={promptsWithoutTemplate} serverId="test-server" />);
    expect(screen.getByText('No Template')).toBeTruthy();
    expect(screen.getByText('Prompt without template')).toBeTruthy();
  });

  it('handles prompts without arguments', () => {
    const promptsWithoutArgs: MCPPrompt[] = [
      {
        name: 'no_args',
        displayName: 'No Args',
        description: 'Prompt without arguments',
        template: 'Simple template'
      }
    ];

    render(<MCPPromptsList prompts={promptsWithoutArgs} serverId="test-server" />);
    expect(screen.getByText('No Args')).toBeTruthy();

    // Should not show "Arguments:" section
    expect(screen.queryByText('Arguments:')).toBeNull();
  });

  it('truncates long templates correctly', () => {
    const longTemplate = Array(10).fill('Line of text').join('\n');
    const promptWithLongTemplate: MCPPrompt[] = [
      {
        name: 'long_prompt',
        displayName: 'Long Prompt',
        description: 'Prompt with long template',
        template: longTemplate
      }
    ];

    render(<MCPPromptsList prompts={promptWithLongTemplate} serverId="test-server" />);

    const templateElement = screen.getByText(/Line of text/);
    expect(templateElement.textContent).toContain('...');

    // Should only show first 3 lines
    const lines = templateElement.textContent?.split('\n').filter(l => l.trim());
    expect(lines?.length).toBeLessThanOrEqual(4); // 3 lines + "..." line
  });
});
