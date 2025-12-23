/**
 * Unit tests for MCPManager component
 * Tests "Add Server" button functionality
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MCPManager } from '../MCPManager';

// Mock the store
vi.mock('../../../stores/project-store', () => ({
  useProjectStore: vi.fn((selector) => selector({
    getSelectedProject: () => ({ path: '/test/project' })
  }))
}));

// Mock electronAPI
const mockElectronAPI = {
  mcp: {
    list: vi.fn().mockResolvedValue([]),
    saveConfig: vi.fn().mockResolvedValue({ success: true })
  }
};

// Mock window APIs for Dialog component
(global as any).window = {
  ...global.window,
  electronAPI: mockElectronAPI,
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

describe('MCPManager - Add Server Button', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders "Add Server" button in header', async () => {
    const { container } = render(<MCPManager />);

    // Component should render immediately
    expect(container).toBeTruthy();

    // Wait for the servers list to load
    await screen.findByText('MCP Servers');

    expect(screen.getByText('Add Server')).toBeTruthy();
  });

  it('Add Server button has Plus icon', async () => {
    render(<MCPManager />);

    // Wait for the servers list to load
    await screen.findByText('MCP Servers');

    const button = screen.getByText('Add Server').closest('button');
    expect(button).toBeTruthy();
    // Check for lucide-react Plus icon by looking for the svg
    const svg = button?.querySelector('svg');
    expect(svg).toBeTruthy();
  });

  it('opens AddServerDialog when Add Server button is clicked', async () => {
    render(<MCPManager />);

    // Wait for the servers list to load
    await screen.findByText('MCP Servers');

    const addButton = screen.getByText('Add Server');
    fireEvent.click(addButton);

    // Dialog should now be open - check for dialog title
    await screen.findByText('Add MCP Server');
  });

  it('closes AddServerDialog when dialog onClose is called', async () => {
    const { container } = render(<MCPManager />);

    // Wait for the servers list to load
    await screen.findByText('MCP Servers');

    // Open dialog
    const addButton = screen.getByText('Add Server');
    fireEvent.click(addButton);

    // Verify dialog is open
    await screen.findByText('Add MCP Server');

    // Close dialog by clicking Cancel
    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    // Dialog should be closed - title should not be visible
    await waitFor(() => {
      expect(screen.queryByText('Add MCP Server')).toBeNull();
    }, { container });
  });
});
