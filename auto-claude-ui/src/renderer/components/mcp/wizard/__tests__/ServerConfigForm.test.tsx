/**
 * Unit tests for ServerConfigForm component
 * Tests form rendering, validation, and data submission
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ServerConfigForm } from '../ServerConfigForm';

describe('ServerConfigForm', () => {
  beforeEach(() => {
    // Setup window.electronAPI mocks
    (window as any).electronAPI = {
      ...((window as any).electronAPI || {}),
      selectDirectory: vi.fn().mockResolvedValue('/selected/path'),
      getDefaultProjectLocation: vi.fn().mockResolvedValue('/Users/test/projects'),
    };
  });

  const defaultProps = {
    onNext: vi.fn(),
    onBack: vi.fn(),
    initialData: {
      serverName: '',
      description: '',
      pythonVersion: '3.12' as const,
      workingDir: ''
    }
  };

  it('should render all form fields', () => {
    render(<ServerConfigForm {...defaultProps} />);

    expect(screen.getByLabelText(/Server Name/i)).toBeTruthy();
    expect(screen.getByLabelText(/Description/i)).toBeTruthy();
    expect(screen.getByLabelText(/Python Version/i)).toBeTruthy();
    expect(screen.getByLabelText(/Working Directory/i)).toBeTruthy();
  });

  it('should show validation error for empty name', async () => {
    render(<ServerConfigForm {...defaultProps} />);

    const nextButton = screen.getByRole('button', { name: /Next/i });
    fireEvent.click(nextButton);

    expect(await screen.findByText(/Server name is required/i)).toBeTruthy();
    expect(defaultProps.onNext).not.toHaveBeenCalled();
  });

  it('should call onNext with valid data', async () => {
    render(<ServerConfigForm {...defaultProps} />);

    // Wait for initial async effects
    await new Promise(resolve => setTimeout(resolve, 100));

    fireEvent.change(screen.getByLabelText(/Server Name/i), {
      target: { value: 'my-api-server' }
    });

    fireEvent.change(screen.getByLabelText(/Description/i), {
      target: { value: 'API wrapper' }
    });

    const nextButton = screen.getByRole('button', { name: /Next/i });
    fireEvent.click(nextButton);

    expect(defaultProps.onNext).toHaveBeenCalledWith({
      serverName: 'my-api-server',
      description: 'API wrapper',
      pythonVersion: '3.12',
      workingDir: expect.stringContaining('my-api-server')
    });
  });

  it('should provide default working directory', async () => {
    render(<ServerConfigForm {...defaultProps} />);

    const workingDirInput = screen.getByLabelText(/Working Directory/i) as HTMLInputElement;
    // Wait for async effect to populate the default directory
    await new Promise(resolve => setTimeout(resolve, 100));
    expect(workingDirInput.value).toContain('.auto-claude/fastmcp-servers');
  });
});
