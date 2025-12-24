/**
 * Unit tests for ReviewPreview component
 * Tests file preview rendering, code generation, and navigation
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ReviewPreview } from '../ReviewPreview';
import type { FastMCPServerConfig } from '../../../../../shared/types/mcp';

// Mock the code generator functions
vi.mock('../../../lib/fastmcp-generator', () => ({
  generateServerPy: vi.fn((config: FastMCPServerConfig) =>
    `from fastmcp import FastMCP\n\nmcp = FastMCP("${config.serverName}")`
  ),
  generatePyprojectToml: vi.fn((config: FastMCPServerConfig) =>
    `[project]\nname = "${config.serverName}"\nversion = "0.1.0"`
  ),
  generateReadmeMd: vi.fn((config: FastMCPServerConfig) =>
    `# ${config.serverName}\n\n${config.description}`
  ),
  generatePythonVersion: vi.fn((version: string) => version),
}));

describe('ReviewPreview', () => {
  const mockConfig: FastMCPServerConfig = {
    templateId: 'web-api',
    serverName: 'test-server',
    description: 'Test server description',
    pythonVersion: '3.12',
    workingDir: '/test/path',
    tools: [
      {
        name: 'test_tool',
        description: 'Test tool description',
        parameters: [
          {
            name: 'param1',
            type: 'string',
            required: true,
            description: 'Test parameter',
          },
        ],
      },
    ],
    dependencies: ['fastmcp>=0.1.0', 'httpx>=0.25.0'],
  };

  const mockOnGenerate = vi.fn().mockResolvedValue(undefined);
  const mockOnBack = vi.fn();

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render server summary', () => {
    render(
      <ReviewPreview
        config={mockConfig}
        onGenerate={mockOnGenerate}
        onBack={mockOnBack}
      />
    );

    expect(screen.getByText('test-server')).toBeTruthy();
    expect(screen.getByText('Test server description')).toBeTruthy();
    expect(screen.getByText(/1 tool/i)).toBeTruthy();
    expect(screen.getByText(/2 dependencies/i)).toBeTruthy();
  });

  it('should show preview for all 4 files', () => {
    render(
      <ReviewPreview
        config={mockConfig}
        onGenerate={mockOnGenerate}
        onBack={mockOnBack}
      />
    );

    // Check for all 4 file previews
    expect(screen.getByText(/pyproject\.toml/i)).toBeTruthy();
    expect(screen.getByText(/server\.py/i)).toBeTruthy();
    expect(screen.getByText(/\.python-version/i)).toBeTruthy();
    expect(screen.getByText(/README\.md/i)).toBeTruthy();
  });

  it('should use code generator functions to create previews', () => {
    const { container } = render(
      <ReviewPreview
        config={mockConfig}
        onGenerate={mockOnGenerate}
        onBack={mockOnBack}
      />
    );

    // Verify that code previews are rendered (they use the generator functions internally)
    // Check for code blocks containing generated content
    const codeBlocks = container.querySelectorAll('code');
    expect(codeBlocks.length).toBeGreaterThan(0);
  });

  it('should call onGenerate when Generate button clicked', async () => {
    render(
      <ReviewPreview
        config={mockConfig}
        onGenerate={mockOnGenerate}
        onBack={mockOnBack}
      />
    );

    const generateButton = screen.getByRole('button', { name: /generate & save/i });
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(mockOnGenerate).toHaveBeenCalledTimes(1);
    });
  });

  it('should call onBack when Back button clicked', () => {
    render(
      <ReviewPreview
        config={mockConfig}
        onGenerate={mockOnGenerate}
        onBack={mockOnBack}
      />
    );

    const backButton = screen.getByRole('button', { name: /back/i });
    fireEvent.click(backButton);

    expect(mockOnBack).toHaveBeenCalledTimes(1);
  });

  it('should show loading state when generating', async () => {
    const slowGenerate = vi.fn(() => new Promise(resolve => setTimeout(resolve, 100)));

    render(
      <ReviewPreview
        config={mockConfig}
        onGenerate={slowGenerate}
        onBack={mockOnBack}
        isGenerating={true}
      />
    );

    const generateButton = screen.getByRole('button', { name: /generating/i });
    expect(generateButton.hasAttribute('disabled')).toBe(true);

    const backButton = screen.getByRole('button', { name: /back/i });
    expect(backButton.hasAttribute('disabled')).toBe(true);
  });
});
