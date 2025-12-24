/**
 * Unit tests for TestConnectionStep component
 * Tests connection testing UI with loading, success, and error states
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TestConnectionStep } from '../TestConnectionStep';
import type { CustomServerConfig } from '../../../../shared/types/mcp';

// Mock window.electron
const mockTestMCPConnection = vi.fn();

describe('TestConnectionStep', () => {
  beforeEach(() => {
    // Setup window.electron mock
    (window as any).electron = {
      testMCPConnection: mockTestMCPConnection,
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
    delete (window as any).electron;
  });

  describe('Loading State', () => {
    it('displays loading spinner and message when testing connection', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'http',
        baseUrl: 'http://localhost:8000',
      };

      // Make the promise not resolve immediately
      mockTestMCPConnection.mockReturnValue(new Promise(() => {}));

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={vi.fn()}
          onRetry={vi.fn()}
        />
      );

      // Should show loading state
      expect(screen.getByText(/testing connection/i)).toBeTruthy();
      expect(screen.queryByRole('button', { name: /retry/i })).toBeNull();
    });

    it('calls window.electron.testMCPConnection with server config on mount', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'stdio',
        command: 'python3',
        args: ['server.py'],
      };

      mockTestMCPConnection.mockResolvedValue({
        success: true,
        capabilities: { tools: 5, prompts: 3, resources: 2 },
      });

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={vi.fn()}
          onRetry={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(mockTestMCPConnection).toHaveBeenCalledWith(serverConfig);
      });
    });
  });

  describe('Success State', () => {
    it('displays success checkmark and message when connection succeeds', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'http',
        baseUrl: 'http://localhost:8000',
      };

      mockTestMCPConnection.mockResolvedValue({
        success: true,
        capabilities: { tools: 5, prompts: 3, resources: 2 },
      });

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={vi.fn()}
          onRetry={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/connection successful/i)).toBeTruthy();
      });
    });

    it('displays discovered capabilities on success', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'http',
        baseUrl: 'http://localhost:8000',
      };

      mockTestMCPConnection.mockResolvedValue({
        success: true,
        capabilities: { tools: 12, prompts: 5, resources: 7 },
      });

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={vi.fn()}
          onRetry={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/12.*tool/i)).toBeTruthy();
        expect(screen.getByText(/5.*prompt/i)).toBeTruthy();
        expect(screen.getByText(/7.*resource/i)).toBeTruthy();
      });
    });

    it('calls onSuccess callback with capabilities when connection succeeds', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'http',
        baseUrl: 'http://localhost:8000',
      };

      const capabilities = { tools: 5, prompts: 3, resources: 2 };
      mockTestMCPConnection.mockResolvedValue({
        success: true,
        capabilities,
      });

      const onSuccess = vi.fn();

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={onSuccess}
          onRetry={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledWith(capabilities);
      });
    });
  });

  describe('Error State', () => {
    it('displays error icon and message when connection fails', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'http',
        baseUrl: 'http://localhost:8000',
      };

      mockTestMCPConnection.mockResolvedValue({
        success: false,
        error: 'Connection failed: timeout',
      });

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={vi.fn()}
          onRetry={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/connection failed: timeout/i)).toBeTruthy();
      });
    });

    it('displays Retry button on connection failure', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'http',
        baseUrl: 'http://localhost:8000',
      };

      mockTestMCPConnection.mockResolvedValue({
        success: false,
        error: 'Network error',
      });

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={vi.fn()}
          onRetry={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeTruthy();
      });
    });

    it('calls onRetry callback when Retry button is clicked', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'http',
        baseUrl: 'http://localhost:8000',
      };

      mockTestMCPConnection.mockResolvedValue({
        success: false,
        error: 'Network error',
      });

      const onRetry = vi.fn();

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={vi.fn()}
          onRetry={onRetry}
        />
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeTruthy();
      });

      const retryButton = screen.getByRole('button', { name: /retry/i });
      fireEvent.click(retryButton);

      expect(onRetry).toHaveBeenCalled();
    });

    it('retests connection when Retry button is clicked', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'http',
        baseUrl: 'http://localhost:8000',
      };

      // First call fails
      mockTestMCPConnection.mockResolvedValueOnce({
        success: false,
        error: 'Network error',
      });

      // Second call succeeds
      mockTestMCPConnection.mockResolvedValueOnce({
        success: true,
        capabilities: { tools: 3, prompts: 1, resources: 0 },
      });

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={vi.fn()}
          onRetry={vi.fn()}
        />
      );

      // Wait for initial failure
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeTruthy();
      });

      expect(mockTestMCPConnection).toHaveBeenCalledTimes(1);

      // Click retry
      const retryButton = screen.getByRole('button', { name: /retry/i });
      fireEvent.click(retryButton);

      // Should call testMCPConnection again
      await waitFor(() => {
        expect(mockTestMCPConnection).toHaveBeenCalledTimes(2);
      });

      // Should show success after retry
      await waitFor(() => {
        expect(screen.getByText(/connection successful/i)).toBeTruthy();
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles zero capabilities gracefully', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'http',
        baseUrl: 'http://localhost:8000',
      };

      mockTestMCPConnection.mockResolvedValue({
        success: true,
        capabilities: { tools: 0, prompts: 0, resources: 0 },
      });

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={vi.fn()}
          onRetry={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/connection successful/i)).toBeTruthy();
        expect(screen.getByText(/0.*tool/i)).toBeTruthy();
        expect(screen.getByText(/0.*prompt/i)).toBeTruthy();
        expect(screen.getByText(/0.*resource/i)).toBeTruthy();
      });
    });

    it('handles missing capabilities object', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'http',
        baseUrl: 'http://localhost:8000',
      };

      mockTestMCPConnection.mockResolvedValue({
        success: true,
        // No capabilities field
      });

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={vi.fn()}
          onRetry={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/connection successful/i)).toBeTruthy();
      });
    });

    it('handles testMCPConnection throwing an exception', async () => {
      const serverConfig: CustomServerConfig = {
        connectionType: 'http',
        baseUrl: 'http://localhost:8000',
      };

      mockTestMCPConnection.mockRejectedValue(new Error('Unexpected error'));

      render(
        <TestConnectionStep
          serverConfig={serverConfig}
          onSuccess={vi.fn()}
          onRetry={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText(/unexpected error/i)).toBeTruthy();
        expect(screen.getByRole('button', { name: /retry/i })).toBeTruthy();
      });
    });
  });
});
