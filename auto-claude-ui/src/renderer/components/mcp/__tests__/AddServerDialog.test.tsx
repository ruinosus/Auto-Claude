/**
 * Unit tests for AddServerDialog component
 * Tests mode selection and dialog state management
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AddServerDialog } from '../AddServerDialog';

describe('AddServerDialog', () => {
  it('renders choose mode by default', () => {
    render(<AddServerDialog open={true} onClose={() => {}} />);

    expect(screen.getByText('Add MCP Server')).toBeTruthy();
    expect(screen.getByText('Connect to Existing Server')).toBeTruthy();
    expect(screen.getByText('Create New with FastMCP')).toBeTruthy();
  });

  it('switches to existing mode when clicked', () => {
    render(<AddServerDialog open={true} onClose={() => {}} />);

    const existingButton = screen.getByText('Connect to Existing Server');
    fireEvent.click(existingButton);

    // Should show form (verified by presence of connection type text)
    expect(screen.getByText(/connection type/i)).toBeTruthy();
  });

  it('calls onClose when dialog is closed', () => {
    const onClose = vi.fn();
    render(<AddServerDialog open={true} onClose={onClose} />);

    // Radix Dialog Close button (assuming we add one)
    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(onClose).toHaveBeenCalled();
  });

  it('does not render when open is false', () => {
    const { container } = render(<AddServerDialog open={false} onClose={() => {}} />);

    expect(screen.queryByText('Add MCP Server')).toBeNull();
  });
});
