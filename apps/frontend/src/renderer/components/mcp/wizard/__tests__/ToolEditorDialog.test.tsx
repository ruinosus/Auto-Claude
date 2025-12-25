/**
 * Unit tests for ToolEditorDialog component
 * Tests form rendering, validation, parameter management, and save/cancel actions
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ToolEditorDialog } from '../ToolEditorDialog';
import type { FastMCPTool } from '../../../../../shared/types/mcp';

describe('ToolEditorDialog', () => {
  const mockOnSave = vi.fn();
  const mockOnCancel = vi.fn();

  const existingTool: FastMCPTool = {
    name: 'read_file',
    description: 'Read contents of a file',
    parameters: [
      {
        name: 'path',
        type: 'string',
        required: true,
        description: 'File path to read'
      },
      {
        name: 'encoding',
        type: 'string',
        required: false,
        default: 'utf-8',
        description: 'File encoding'
      }
    ]
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render all form fields when creating new tool', () => {
    render(
      <ToolEditorDialog
        open={true}
        tool={null}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Should show dialog title
    expect(screen.getByText(/add tool/i)).toBeTruthy();

    // Should show tool name input
    expect(screen.getByLabelText(/tool name/i)).toBeTruthy();

    // Should show description textarea
    expect(screen.getByLabelText(/description/i)).toBeTruthy();

    // Should show "Add Parameter" button (use getByRole to find the actual button)
    expect(screen.getByRole('button', { name: /add parameter/i })).toBeTruthy();

    // Should show Save and Cancel buttons
    expect(screen.getByText('Save')).toBeTruthy();
    expect(screen.getByText('Cancel')).toBeTruthy();
  });

  it('should show validation error for empty tool name', async () => {
    render(
      <ToolEditorDialog
        open={true}
        tool={null}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Click save without filling anything
    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText(/tool name is required/i)).toBeTruthy();
    });

    // Should not call onSave
    expect(mockOnSave).not.toHaveBeenCalled();
  });

  it('should allow adding a parameter', () => {
    render(
      <ToolEditorDialog
        open={true}
        tool={null}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Initially no parameters
    expect(screen.queryByLabelText(/parameter name/i)).toBeFalsy();

    // Click Add Parameter (use getByRole to find the actual button)
    const addParamButton = screen.getByRole('button', { name: /add parameter/i });
    fireEvent.click(addParamButton);

    // Should show parameter fields
    expect(screen.getByLabelText(/parameter name/i)).toBeTruthy();
    expect(screen.getByLabelText(/type/i)).toBeTruthy();
    expect(screen.getByLabelText(/required/i)).toBeTruthy();
  });

  it('should allow removing a parameter', () => {
    render(
      <ToolEditorDialog
        open={true}
        tool={existingTool}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Should show 2 parameters initially
    const removeButtons = screen.getAllByRole('button', { name: /remove parameter/i });
    expect(removeButtons.length).toBe(2);

    // Remove first parameter
    fireEvent.click(removeButtons[0]);

    // Should now have only 1 remove button
    const updatedRemoveButtons = screen.getAllByRole('button', { name: /remove parameter/i });
    expect(updatedRemoveButtons.length).toBe(1);
  });

  it('should call onSave with valid tool data', async () => {
    render(
      <ToolEditorDialog
        open={true}
        tool={null}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Fill in tool name
    const nameInput = screen.getByLabelText(/tool name/i);
    fireEvent.change(nameInput, { target: { value: 'test_tool' } });

    // Fill in description
    const descriptionInput = screen.getByLabelText(/description/i);
    fireEvent.change(descriptionInput, { target: { value: 'Test tool description' } });

    // Add a parameter
    const addParamButton = screen.getByRole('button', { name: /add parameter/i });
    fireEvent.click(addParamButton);

    // Fill parameter details
    const paramNameInput = screen.getByLabelText(/parameter name/i);
    fireEvent.change(paramNameInput, { target: { value: 'param1' } });

    // Click Save
    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    // Should call onSave with tool data
    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'test_tool',
          description: 'Test tool description',
          parameters: expect.arrayContaining([
            expect.objectContaining({
              name: 'param1',
              type: 'string',
              required: false
            })
          ])
        })
      );
    });
  });

  it('should call onCancel when cancel clicked', () => {
    render(
      <ToolEditorDialog
        open={true}
        tool={null}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('should pre-populate form when editing existing tool', () => {
    render(
      <ToolEditorDialog
        open={true}
        tool={existingTool}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Should show "Edit Tool" title
    expect(screen.getByText(/edit tool/i)).toBeTruthy();

    // Should show existing tool name
    const nameInput = screen.getByLabelText(/tool name/i) as HTMLInputElement;
    expect(nameInput.value).toBe('read_file');

    // Should show existing description - use getElementById for specific element
    const descriptionInput = document.getElementById('tool-description') as HTMLTextAreaElement;
    expect(descriptionInput.value).toBe('Read contents of a file');

    // Should show 2 parameters
    const removeButtons = screen.getAllByRole('button', { name: /remove parameter/i });
    expect(removeButtons.length).toBe(2);
  });

  it('should validate tool name is a valid Python identifier', async () => {
    render(
      <ToolEditorDialog
        open={true}
        tool={null}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Try invalid name with space
    const nameInput = screen.getByLabelText(/tool name/i);
    fireEvent.change(nameInput, { target: { value: 'invalid name' } });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    // Should show validation error (look for the specific error message)
    await waitFor(() => {
      expect(screen.getByText('Tool name must be a valid Python identifier')).toBeTruthy();
    });

    expect(mockOnSave).not.toHaveBeenCalled();
  });

  it('should validate parameter names are valid Python identifiers', async () => {
    render(
      <ToolEditorDialog
        open={true}
        tool={null}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Fill valid tool name and description
    const nameInput = screen.getByLabelText(/tool name/i);
    fireEvent.change(nameInput, { target: { value: 'valid_tool' } });

    const descriptionInput = document.getElementById('tool-description') as HTMLTextAreaElement;
    fireEvent.change(descriptionInput, { target: { value: 'Valid description' } });

    // Add parameter with invalid name
    const addParamButton = screen.getByRole('button', { name: /add parameter/i });
    fireEvent.click(addParamButton);

    const paramNameInput = screen.getByLabelText(/parameter name/i);
    fireEvent.change(paramNameInput, { target: { value: 'invalid-param' } });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    // Should show validation error (look for the specific error message)
    await waitFor(() => {
      expect(screen.getByText('Parameter name must be a valid Python identifier')).toBeTruthy();
    });

    expect(mockOnSave).not.toHaveBeenCalled();
  });

  it('should allow selecting different parameter types', () => {
    render(
      <ToolEditorDialog
        open={true}
        tool={null}
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Add parameter
    const addParamButton = screen.getByRole('button', { name: /add parameter/i });
    fireEvent.click(addParamButton);

    // Find type select - it should exist with default value 'string'
    const typeSelect = screen.getByLabelText(/type/i);
    expect(typeSelect).toBeTruthy();

    // The select should have the default value
    expect(typeSelect.textContent).toContain('string');
  });
});
