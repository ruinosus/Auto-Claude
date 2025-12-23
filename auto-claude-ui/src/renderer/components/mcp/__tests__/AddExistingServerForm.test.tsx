/**
 * Unit tests for AddExistingServerForm component
 * Tests multi-step wizard flow
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AddExistingServerForm } from '../AddExistingServerForm';
import type { CustomServerConfig } from '../../../../shared/types/mcp';

describe('AddExistingServerForm', () => {
  const mockOnComplete = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Step Navigation', () => {
    it('renders step 1 (Connection Type) by default', () => {
      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      expect(screen.getByText('Connection Type')).toBeTruthy();
      expect(screen.getAllByText(/HTTP\/HTTPS/i).length).toBeGreaterThan(0);
    });

    it('shows step indicator with current step', () => {
      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      expect(screen.getByText(/Step 1 of 3/i)).toBeTruthy();
    });

    it('disables Back button on first step', () => {
      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      const backButton = screen.getByRole('button', { name: /back/i });
      expect(backButton.hasAttribute('disabled')).toBe(true);
    });

    it('moves to step 2 when Next is clicked with http selected', async () => {
      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      // HTTP is selected by default, just click Next
      const nextButton = screen.getByRole('button', { name: /next/i });
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText(/Step 2 of 3/i)).toBeTruthy();
        expect(screen.getByText('Basic Information')).toBeTruthy();
      });
    });

    it('enables Back button on second step', async () => {
      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      // Move to step 2
      const nextButton = screen.getByRole('button', { name: /next/i });
      fireEvent.click(nextButton);

      await waitFor(() => {
        const backButton = screen.getByRole('button', { name: /back/i });
        expect(backButton.hasAttribute('disabled')).toBe(false);
      });
    });

    it('goes back to step 1 when Back is clicked on step 2', async () => {
      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      // Move to step 2
      const nextButton = screen.getByRole('button', { name: /next/i });
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText(/Step 2 of 3/i)).toBeTruthy();
      });

      // Go back
      const backButton = screen.getByRole('button', { name: /back/i });
      fireEvent.click(backButton);

      await waitFor(() => {
        expect(screen.getByText(/Step 1 of 3/i)).toBeTruthy();
        expect(screen.getByText('Connection Type')).toBeTruthy();
      });
    });
  });

  describe('Connection Type Selection', () => {
    it('shows HttpServerForm when http is selected', async () => {
      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      // Select http (already selected by default)
      const nextButton = screen.getByRole('button', { name: /next/i });
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByLabelText(/Server Name/i)).toBeTruthy();
        expect(screen.getByLabelText(/Base URL/i)).toBeTruthy();
      });
    });

    it('shows StdioServerForm when stdio is selected', async () => {
      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      // Select stdio - use the radio button directly
      const stdioRadio = screen.getByRole('radio', { name: /Standard I\/O/i });
      fireEvent.click(stdioRadio);

      await waitFor(() => {
        expect(stdioRadio.getAttribute('data-state')).toBe('checked');
      });

      const nextButton = screen.getByRole('button', { name: /next/i });
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText(/Command Configuration/i)).toBeTruthy();
      });
    });

    it('shows SseServerForm when sse is selected', async () => {
      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      // Select sse
      const sseRadio = screen.getByLabelText(/Server-Sent Events/i);
      fireEvent.click(sseRadio);

      const nextButton = screen.getByRole('button', { name: /next/i });
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByLabelText(/SSE Endpoint URL/i)).toBeTruthy();
      });
    });
  });

  describe('Form Data Flow', () => {
    it('preserves http form data after submission when navigating back', async () => {
      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      // Move to step 2 (http form)
      fireEvent.click(screen.getByRole('button', { name: /next/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/Server Name/i)).toBeTruthy();
      });

      // Fill in required data and submit
      fireEvent.change(screen.getByLabelText(/Server Name/i), {
        target: { value: 'Test Server' },
      });
      fireEvent.change(screen.getByLabelText(/Base URL/i), {
        target: { value: 'http://localhost:8000' },
      });

      // Submit form (moves to step 3)
      fireEvent.click(screen.getByRole('button', { name: /next/i }));

      await waitFor(() => {
        expect(screen.getByText(/Step 3 of 3/i)).toBeTruthy();
      });

      // Go back to step 2
      fireEvent.click(screen.getByRole('button', { name: /back/i }));

      await waitFor(() => {
        const nameInputAgain = screen.getByLabelText(/Server Name/i) as HTMLInputElement;
        expect(nameInputAgain.value).toBe('Test Server');
      });
    });
  });

  describe('Test Connection Step', () => {
    it('moves to step 3 after http form submission', async () => {
      // Mock the electron API
      (window as any).electron = {
        testMCPConnection: vi.fn().mockResolvedValue({
          success: true,
          capabilities: { tools: 2, prompts: 0, resources: 0 },
        }),
      };

      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      // Move to step 2
      fireEvent.click(screen.getByRole('button', { name: /next/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/Server Name/i)).toBeTruthy();
      });

      // Fill required fields
      fireEvent.change(screen.getByLabelText(/Server Name/i), {
        target: { value: 'Test Server' },
      });
      fireEvent.change(screen.getByLabelText(/Base URL/i), {
        target: { value: 'http://localhost:8000' },
      });

      // Submit form
      fireEvent.click(screen.getByRole('button', { name: /next/i }));

      await waitFor(() => {
        expect(screen.getByText(/Step 3 of 3/i)).toBeTruthy();
        expect(screen.getByText(/Testing connection/i)).toBeTruthy();
      });
    });
  });

  describe('Final Submission', () => {
    it('calls onComplete with full config after successful connection test', async () => {
      // Mock successful connection
      (window as any).electron = {
        testMCPConnection: vi.fn().mockResolvedValue({
          success: true,
          capabilities: { tools: 2, prompts: 0, resources: 0 },
        }),
      };

      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      // Step 1: Select http (default)
      fireEvent.click(screen.getByRole('button', { name: /next/i }));

      // Step 2: Fill http form
      await waitFor(() => {
        expect(screen.getByLabelText(/Server Name/i)).toBeTruthy();
      });

      fireEvent.change(screen.getByLabelText(/Server Name/i), {
        target: { value: 'My HTTP Server' },
      });
      fireEvent.change(screen.getByLabelText(/Base URL/i), {
        target: { value: 'http://localhost:8000' },
      });

      fireEvent.click(screen.getByRole('button', { name: /next/i }));

      // Step 3: Wait for successful connection
      await waitFor(() => {
        expect(screen.getByText(/Connection successful/i)).toBeTruthy();
      });

      // Click Save button
      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      // Verify onComplete was called with correct config
      expect(mockOnComplete).toHaveBeenCalledWith(
        expect.objectContaining({
          connectionType: 'http',
          baseUrl: 'http://localhost:8000',
        })
      );
    });
  });

  describe('Cancel Button', () => {
    it('calls onCancel when Cancel is clicked', () => {
      render(
        <AddExistingServerForm onComplete={mockOnComplete} onCancel={mockOnCancel} />
      );

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      fireEvent.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  describe('Initial Step', () => {
    it('allows starting from a specific step', () => {
      render(
        <AddExistingServerForm
          onComplete={mockOnComplete}
          onCancel={mockOnCancel}
          initialStep={2}
        />
      );

      expect(screen.getByText(/Step 2 of 3/i)).toBeTruthy();
    });
  });
});
