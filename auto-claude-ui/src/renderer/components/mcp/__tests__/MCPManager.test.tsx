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

describe('MCPManager - Custom Server Display', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays custom servers alongside built-in servers', async () => {
    // Mock data with both builtin and custom servers
    mockElectronAPI.mcp.list.mockResolvedValue([
      {
        id: 'context7',
        name: 'Context7',
        description: 'Built-in documentation server',
        type: 'builtin',
        category: 'Documentation',
        status: 'connected',
        enabled: true,
        requiredEnvVars: [],
        capabilities: {},
        toolCount: 2,
        promptCount: 0,
        resourceCount: 0,
        connectionType: 'sdk'
      },
      {
        id: 'custom-http-123',
        name: 'My Custom HTTP Server',
        description: 'Custom HTTP MCP server',
        type: 'custom',
        category: 'Custom',
        status: 'disconnected',
        enabled: false,
        requiredEnvVars: [],
        capabilities: {},
        toolCount: 0,
        promptCount: 0,
        resourceCount: 0,
        connectionType: 'http',
        customConfig: {
          connectionType: 'http',
          baseUrl: 'http://localhost:8000',
          authType: 'none'
        }
      }
    ]);

    render(<MCPManager />);

    // Wait for servers to load
    await screen.findByText('MCP Servers');

    // Both servers should be visible
    expect(screen.getByText('Context7')).toBeTruthy();
    expect(screen.getByText('My Custom HTTP Server')).toBeTruthy();
  });

  it('shows "Custom" badge for custom servers', async () => {
    mockElectronAPI.mcp.list.mockResolvedValue([
      {
        id: 'custom-stdio-456',
        name: 'My Custom stdio Server',
        description: 'Custom stdio MCP server',
        type: 'custom',
        category: 'Custom',
        status: 'disconnected',
        enabled: false,
        requiredEnvVars: [],
        capabilities: {},
        toolCount: 0,
        promptCount: 0,
        resourceCount: 0,
        connectionType: 'stdio',
        customConfig: {
          connectionType: 'stdio',
          command: 'python',
          args: ['server.py']
        }
      }
    ]);

    render(<MCPManager />);

    // Wait for servers to load
    await screen.findByText('MCP Servers');

    // Custom badge should be visible
    expect(screen.getByText('Custom')).toBeTruthy();
  });

  it('displays connection type for custom servers', async () => {
    mockElectronAPI.mcp.list.mockResolvedValue([
      {
        id: 'custom-sse-789',
        name: 'Custom Server',
        description: 'Test server',
        type: 'custom',
        category: 'Custom',
        status: 'disconnected',
        enabled: false,
        requiredEnvVars: [],
        capabilities: {},
        toolCount: 0,
        promptCount: 0,
        resourceCount: 0,
        connectionType: 'http',
        customConfig: {
          connectionType: 'sse',
          baseUrl: 'http://localhost:8000/events'
        }
      }
    ]);

    render(<MCPManager />);

    // Wait for servers to load
    await screen.findByText('MCP Servers');

    // Connection type should be visible in the status info
    expect(screen.getByText(/Connection: SSE/)).toBeTruthy();
  });

  it('custom servers display with correct status', async () => {
    mockElectronAPI.mcp.list.mockResolvedValue([
      {
        id: 'custom-http-999',
        name: 'Toggleable Custom Server',
        description: 'Test toggle functionality',
        type: 'custom',
        category: 'Custom',
        status: 'disconnected',
        enabled: false,
        requiredEnvVars: [],
        capabilities: {},
        toolCount: 1,
        promptCount: 0,
        resourceCount: 0,
        connectionType: 'http',
        customConfig: {
          connectionType: 'http',
          baseUrl: 'http://localhost:8000'
        }
      }
    ]);

    render(<MCPManager />);

    // Wait for servers to load
    await screen.findByText('MCP Servers');

    // Server should be displayed
    expect(screen.getByText('Toggleable Custom Server')).toBeTruthy();

    // Should show custom badge
    expect(screen.getByText('Custom')).toBeTruthy();

    // Should show connection type
    expect(screen.getByText(/Connection: HTTP/)).toBeTruthy();

    // Should show disconnected status
    expect(screen.getByText('Disconnected')).toBeTruthy();
  });
});
