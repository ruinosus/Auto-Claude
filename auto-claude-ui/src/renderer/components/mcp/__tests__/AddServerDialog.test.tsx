/**
 * Unit tests for AddServerDialog component
 * Tests mode selection and dialog state management
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AddServerDialog } from '../AddServerDialog';

// Mock window APIs for Dialog component
(global as any).window = {
  ...global.window,
  getComputedStyle: vi.fn().mockReturnValue({
    getPropertyValue: vi.fn().mockReturnValue(''),
    paddingLeft: '0px',
    paddingRight: '0px',
    marginLeft: '0px',
    marginRight: '0px'
  }),
  setTimeout: globalThis.setTimeout,
  clearTimeout: globalThis.clearTimeout,
  requestAnimationFrame: vi.fn((cb) => setTimeout(cb, 0)),
  cancelAnimationFrame: vi.fn()
};

describe('AddServerDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  it('renders choose mode by default', () => {
    render(<AddServerDialog open={true} onClose={() => {}} />);

    expect(screen.getByText('Add MCP Server')).toBeTruthy();
    expect(screen.getByText('Connect to Existing Server')).toBeTruthy();
    expect(screen.getByText('Create New with FastMCP')).toBeTruthy();
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

  // Note: Full integration testing of AddExistingServerForm within AddServerDialog
  // is covered by MCPManager.test.tsx which tests the complete flow including
  // opening the dialog, interacting with the form, and saving configurations.
});
