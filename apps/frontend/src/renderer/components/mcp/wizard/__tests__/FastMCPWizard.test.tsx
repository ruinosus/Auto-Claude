import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FastMCPWizard } from '../FastMCPWizard';
import type { FastMCPServerConfig } from '../../../../../shared/types/mcp';

// Mock child components
vi.mock('../TemplateSelector', () => ({
  TemplateSelector: ({ onSelect, selectedId }: any) => (
    <div data-testid="template-selector">
      <button onClick={() => onSelect('file-server')}>Select File Server</button>
      <span>Selected: {selectedId || 'none'}</span>
    </div>
  ),
}));

vi.mock('../ServerConfigForm', () => ({
  ServerConfigForm: ({ onNext, onBack, initialData }: any) => (
    <div data-testid="server-config-form">
      <button onClick={() => onNext({
        serverName: 'test-server',
        description: 'Test description',
        pythonVersion: '3.12',
        workingDir: '/tmp/test'
      })}>Next</button>
      <button onClick={onBack}>Back</button>
    </div>
  ),
}));

vi.mock('../ToolCustomizer', () => ({
  ToolCustomizer: ({ onNext, onBack, onAddTool, onEditTool, tools }: any) => (
    <div data-testid="tool-customizer">
      <button onClick={onAddTool}>Add Tool</button>
      <button onClick={() => onEditTool(0)}>Edit Tool</button>
      <button onClick={onBack}>Back</button>
      <button onClick={onNext}>Next</button>
      <span>Tools: {tools.length}</span>
    </div>
  ),
}));

vi.mock('../DependencyManager', () => ({
  DependencyManager: ({ onNext, onBack, dependencies }: any) => (
    <div data-testid="dependency-manager">
      <button onClick={onBack}>Back</button>
      <button onClick={onNext}>Next</button>
      <span>Dependencies: {dependencies.length}</span>
    </div>
  ),
}));

vi.mock('../ReviewPreview', () => ({
  ReviewPreview: ({ onGenerate, onBack, isGenerating }: any) => (
    <div data-testid="review-preview">
      <button onClick={onBack}>Back</button>
      <button onClick={onGenerate}>Generate</button>
      <span>Generating: {isGenerating ? 'yes' : 'no'}</span>
    </div>
  ),
}));

vi.mock('../ToolEditorDialog', () => ({
  ToolEditorDialog: ({ open, tool, onSave, onCancel }: any) => (
    open ? (
      <div data-testid="tool-editor-dialog">
        <span>Editing: {tool ? 'existing' : 'new'}</span>
        <button onClick={() => onSave({
          name: 'test_tool',
          description: 'Test tool',
          parameters: []
        })}>Save</button>
        <button onClick={onCancel}>Cancel</button>
      </div>
    ) : null
  ),
}));

describe('FastMCPWizard', () => {
  const mockOnComplete = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should start at step 1 (template selection)', () => {
    render(<FastMCPWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);

    expect(screen.getByTestId('template-selector')).toBeInTheDocument();
    expect(screen.queryByTestId('server-config-form')).not.toBeInTheDocument();
  });

  it('should advance to step 2 when template selected', async () => {
    render(<FastMCPWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);

    // Step 1: Select template
    const selectButton = screen.getByText('Select File Server');
    fireEvent.click(selectButton);

    // Should advance to step 2
    await waitFor(() => {
      expect(screen.getByTestId('server-config-form')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('template-selector')).not.toBeInTheDocument();
  });

  it('should advance to step 3 with server config', async () => {
    render(<FastMCPWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);

    // Step 1: Select template
    fireEvent.click(screen.getByText('Select File Server'));

    // Step 2: Fill server config
    await waitFor(() => {
      expect(screen.getByTestId('server-config-form')).toBeInTheDocument();
    });

    const nextButton = screen.getByRole('button', { name: /next/i });
    fireEvent.click(nextButton);

    // Should advance to step 3
    await waitFor(() => {
      expect(screen.getByTestId('tool-customizer')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('server-config-form')).not.toBeInTheDocument();
  });

  it('should allow editing tools in step 3', async () => {
    render(<FastMCPWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);

    // Navigate to step 3
    fireEvent.click(screen.getByText('Select File Server'));
    await waitFor(() => screen.getByTestId('server-config-form'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => screen.getByTestId('tool-customizer'));

    // Click "Add Tool"
    fireEvent.click(screen.getByText('Add Tool'));

    // Tool editor dialog should open
    await waitFor(() => {
      expect(screen.getByTestId('tool-editor-dialog')).toBeInTheDocument();
    });

    // Save tool
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    // Dialog should close
    await waitFor(() => {
      expect(screen.queryByTestId('tool-editor-dialog')).not.toBeInTheDocument();
    });
  });

  it('should advance to step 4 (dependencies)', async () => {
    render(<FastMCPWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);

    // Navigate to step 3
    fireEvent.click(screen.getByText('Select File Server'));
    await waitFor(() => screen.getByTestId('server-config-form'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => screen.getByTestId('tool-customizer'));

    // Click Next
    const nextButtons = screen.getAllByRole('button', { name: /next/i });
    fireEvent.click(nextButtons[0]);

    // Should advance to step 4
    await waitFor(() => {
      expect(screen.getByTestId('dependency-manager')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('tool-customizer')).not.toBeInTheDocument();
  });

  it('should advance to step 5 (review)', async () => {
    render(<FastMCPWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);

    // Navigate to step 4
    fireEvent.click(screen.getByText('Select File Server'));
    await waitFor(() => screen.getByTestId('server-config-form'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => screen.getByTestId('tool-customizer'));
    fireEvent.click(screen.getAllByRole('button', { name: /next/i })[0]);
    await waitFor(() => screen.getByTestId('dependency-manager'));

    // Click Next
    const nextButtons = screen.getAllByRole('button', { name: /next/i });
    fireEvent.click(nextButtons[0]);

    // Should advance to step 5
    await waitFor(() => {
      expect(screen.getByTestId('review-preview')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('dependency-manager')).not.toBeInTheDocument();
  });

  it('should call generation handler on final step', async () => {
    mockOnComplete.mockResolvedValue(undefined);

    render(<FastMCPWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);

    // Navigate to step 5
    fireEvent.click(screen.getByText('Select File Server'));
    await waitFor(() => screen.getByTestId('server-config-form'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => screen.getByTestId('tool-customizer'));
    fireEvent.click(screen.getAllByRole('button', { name: /next/i })[0]);
    await waitFor(() => screen.getByTestId('dependency-manager'));
    fireEvent.click(screen.getAllByRole('button', { name: /next/i })[0]);
    await waitFor(() => screen.getByTestId('review-preview'));

    // Click Generate
    fireEvent.click(screen.getByText('Generate'));

    // Should call onComplete
    await waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalledTimes(1);
    });

    // Verify the config structure
    const config = mockOnComplete.mock.calls[0][0];
    expect(config).toHaveProperty('templateId');
    expect(config).toHaveProperty('serverName');
    expect(config).toHaveProperty('tools');
    expect(config).toHaveProperty('dependencies');
  });

  it('should allow going back between steps', async () => {
    render(<FastMCPWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);

    // Navigate to step 2
    fireEvent.click(screen.getByText('Select File Server'));
    await waitFor(() => screen.getByTestId('server-config-form'));

    // Go back to step 1
    fireEvent.click(screen.getByRole('button', { name: /back/i }));

    await waitFor(() => {
      expect(screen.getByTestId('template-selector')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('server-config-form')).not.toBeInTheDocument();
  });

  it('should preserve state when navigating back and forth', async () => {
    render(<FastMCPWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);

    // Navigate to step 2
    fireEvent.click(screen.getByText('Select File Server'));
    await waitFor(() => screen.getByTestId('server-config-form'));

    // Go back
    fireEvent.click(screen.getByRole('button', { name: /back/i }));
    await waitFor(() => screen.getByTestId('template-selector'));

    // Should still show selected template in the mock
    expect(screen.getByText(/selected: file-server/i)).toBeInTheDocument();

    // Navigate forward again
    fireEvent.click(screen.getByText('Select File Server'));
    await waitFor(() => screen.getByTestId('server-config-form'));

    // Should still be at step 2
    expect(screen.getByTestId('server-config-form')).toBeInTheDocument();
  });

  it('should handle tool editor cancellation', async () => {
    render(<FastMCPWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);

    // Navigate to step 3
    fireEvent.click(screen.getByText('Select File Server'));
    await waitFor(() => screen.getByTestId('server-config-form'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => screen.getByTestId('tool-customizer'));

    // Open tool editor
    fireEvent.click(screen.getByText('Add Tool'));
    await waitFor(() => screen.getByTestId('tool-editor-dialog'));

    // Cancel
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));

    // Dialog should close
    await waitFor(() => {
      expect(screen.queryByTestId('tool-editor-dialog')).not.toBeInTheDocument();
    });
  });

  it('should show generating state during generation', async () => {
    // Mock slow completion
    mockOnComplete.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    render(<FastMCPWizard onComplete={mockOnComplete} onCancel={mockOnCancel} />);

    // Navigate to step 5
    fireEvent.click(screen.getByText('Select File Server'));
    await waitFor(() => screen.getByTestId('server-config-form'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    await waitFor(() => screen.getByTestId('tool-customizer'));
    fireEvent.click(screen.getAllByRole('button', { name: /next/i })[0]);
    await waitFor(() => screen.getByTestId('dependency-manager'));
    fireEvent.click(screen.getAllByRole('button', { name: /next/i })[0]);
    await waitFor(() => screen.getByTestId('review-preview'));

    // Click Generate
    fireEvent.click(screen.getByText('Generate'));

    // Should show generating state
    await waitFor(() => {
      expect(screen.getByText(/generating: yes/i)).toBeInTheDocument();
    });
  });
});
