/**
 * Unit tests for ToolCustomizer component
 * Tests tool list rendering, add/edit/remove actions, and empty state
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToolCustomizer } from '../ToolCustomizer';
import type { FastMCPTool } from '../../../../../shared/types/mcp';

describe('ToolCustomizer', () => {
  const mockTools: FastMCPTool[] = [
    {
      name: 'read_file',
      description: 'Read contents of a file',
      parameters: [
        { name: 'path', type: 'string', required: true, description: 'File path to read' },
        { name: 'encoding', type: 'string', required: false, default: 'utf-8' }
      ]
    },
    {
      name: 'write_file',
      description: 'Write content to a file',
      parameters: [
        { name: 'path', type: 'string', required: true },
        { name: 'content', type: 'string', required: true },
        { name: 'encoding', type: 'string', required: false, default: 'utf-8' }
      ]
    }
  ];

  it('should render tool list with template tools', () => {
    const onToolsChange = vi.fn();
    const onAddTool = vi.fn();
    const onEditTool = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <ToolCustomizer
        tools={mockTools}
        onToolsChange={onToolsChange}
        onAddTool={onAddTool}
        onEditTool={onEditTool}
        onNext={onNext}
        onBack={onBack}
      />
    );

    // Should show tool names
    expect(screen.getByText('read_file')).toBeTruthy();
    expect(screen.getByText('write_file')).toBeTruthy();

    // Should show tool descriptions
    expect(screen.getByText('Read contents of a file')).toBeTruthy();
    expect(screen.getByText('Write content to a file')).toBeTruthy();

    // Should show parameter counts
    expect(screen.getByText(/2 parameters/)).toBeTruthy();
    expect(screen.getByText(/3 parameters/)).toBeTruthy();
  });

  it('should show "Add Tool" button', () => {
    const onToolsChange = vi.fn();
    const onAddTool = vi.fn();
    const onEditTool = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <ToolCustomizer
        tools={mockTools}
        onToolsChange={onToolsChange}
        onAddTool={onAddTool}
        onEditTool={onEditTool}
        onNext={onNext}
        onBack={onBack}
      />
    );

    const addButton = screen.getByText('Add Tool');
    expect(addButton).toBeTruthy();
  });

  it('should call onAddTool when Add Tool button clicked', () => {
    const onToolsChange = vi.fn();
    const onAddTool = vi.fn();
    const onEditTool = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <ToolCustomizer
        tools={mockTools}
        onToolsChange={onToolsChange}
        onAddTool={onAddTool}
        onEditTool={onEditTool}
        onNext={onNext}
        onBack={onBack}
      />
    );

    const addButton = screen.getByText('Add Tool');
    fireEvent.click(addButton);

    expect(onAddTool).toHaveBeenCalledTimes(1);
  });

  it('should call onEditTool when edit button clicked', () => {
    const onToolsChange = vi.fn();
    const onAddTool = vi.fn();
    const onEditTool = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <ToolCustomizer
        tools={mockTools}
        onToolsChange={onToolsChange}
        onAddTool={onAddTool}
        onEditTool={onEditTool}
        onNext={onNext}
        onBack={onBack}
      />
    );

    // Find all edit buttons (should be 2, one for each tool)
    const editButtons = screen.getAllByRole('button', { name: /edit/i });
    expect(editButtons.length).toBe(2);

    // Click the first edit button
    fireEvent.click(editButtons[0]);

    expect(onEditTool).toHaveBeenCalledWith(0);
  });

  it('should call onToolsChange when remove button clicked', () => {
    const onToolsChange = vi.fn();
    const onAddTool = vi.fn();
    const onEditTool = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <ToolCustomizer
        tools={mockTools}
        onToolsChange={onToolsChange}
        onAddTool={onAddTool}
        onEditTool={onEditTool}
        onNext={onNext}
        onBack={onBack}
      />
    );

    // Find all remove buttons (should be 2, one for each tool)
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    expect(removeButtons.length).toBe(2);

    // Click the first remove button
    fireEvent.click(removeButtons[0]);

    // Should call onToolsChange with the remaining tool
    expect(onToolsChange).toHaveBeenCalledWith([mockTools[1]]);
  });

  it('should show empty state for blank template', () => {
    const onToolsChange = vi.fn();
    const onAddTool = vi.fn();
    const onEditTool = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <ToolCustomizer
        tools={[]}
        onToolsChange={onToolsChange}
        onAddTool={onAddTool}
        onEditTool={onEditTool}
        onNext={onNext}
        onBack={onBack}
      />
    );

    // Should show empty state message
    expect(screen.getByText(/no tools defined/i)).toBeTruthy();

    // Should still show Add Tool button
    expect(screen.getByText('Add Tool')).toBeTruthy();
  });

  it('should call onNext when Next button clicked', () => {
    const onToolsChange = vi.fn();
    const onAddTool = vi.fn();
    const onEditTool = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <ToolCustomizer
        tools={mockTools}
        onToolsChange={onToolsChange}
        onAddTool={onAddTool}
        onEditTool={onEditTool}
        onNext={onNext}
        onBack={onBack}
      />
    );

    const nextButton = screen.getByText('Next');
    fireEvent.click(nextButton);

    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('should call onBack when Back button clicked', () => {
    const onToolsChange = vi.fn();
    const onAddTool = vi.fn();
    const onEditTool = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <ToolCustomizer
        tools={mockTools}
        onToolsChange={onToolsChange}
        onAddTool={onAddTool}
        onEditTool={onEditTool}
        onNext={onNext}
        onBack={onBack}
      />
    );

    const backButton = screen.getByText('Back');
    fireEvent.click(backButton);

    expect(onBack).toHaveBeenCalledTimes(1);
  });
});
