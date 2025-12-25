/**
 * Unit tests for SseServerForm component
 * Tests SSE (Server-Sent Events) MCP server configuration form
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SseServerForm } from '../SseServerForm';

describe('SseServerForm', () => {
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  const defaultProps = {
    onSubmit: mockOnSubmit,
    onCancel: mockOnCancel,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Information Fields', () => {
    it('renders server name input field', () => {
      render(<SseServerForm {...defaultProps} />);

      const nameInput = screen.getByLabelText(/server name/i);
      expect(nameInput).toBeTruthy();
      expect(nameInput.getAttribute('required')).toBe('');
    });

    it('renders description input field', () => {
      render(<SseServerForm {...defaultProps} />);

      const descInput = screen.getByLabelText(/description/i);
      expect(descInput).toBeTruthy();
      expect(descInput.getAttribute('required')).toBeNull();
    });

    it('renders SSE endpoint URL input field', () => {
      render(<SseServerForm {...defaultProps} />);

      const urlInput = screen.getByLabelText(/sse endpoint url/i);
      expect(urlInput).toBeTruthy();
      expect(urlInput.getAttribute('required')).toBe('');
    });

    it('allows user to type in server name', () => {
      render(<SseServerForm {...defaultProps} />);

      const nameInput = screen.getByLabelText(/server name/i) as HTMLInputElement;
      fireEvent.change(nameInput, { target: { value: 'My SSE Server' } });

      expect(nameInput.value).toBe('My SSE Server');
    });

    it('allows user to type in description', () => {
      render(<SseServerForm {...defaultProps} />);

      const descInput = screen.getByLabelText(/description/i) as HTMLInputElement;
      fireEvent.change(descInput, { target: { value: 'Event stream MCP server' } });

      expect(descInput.value).toBe('Event stream MCP server');
    });

    it('allows user to type in SSE endpoint URL', () => {
      render(<SseServerForm {...defaultProps} />);

      const urlInput = screen.getByLabelText(/sse endpoint url/i) as HTMLInputElement;
      fireEvent.change(urlInput, { target: { value: 'http://localhost:8000/events' } });

      expect(urlInput.value).toBe('http://localhost:8000/events');
    });
  });

  describe('Connection Options', () => {
    it('renders auto-reconnect checkbox', () => {
      render(<SseServerForm {...defaultProps} />);

      const checkbox = screen.getByLabelText(/auto-reconnect on disconnect/i);
      expect(checkbox).toBeTruthy();
      expect(checkbox.getAttribute('role')).toBe('checkbox');
    });

    it('auto-reconnect checkbox is checked by default', () => {
      render(<SseServerForm {...defaultProps} />);

      const checkbox = screen.getByLabelText(/auto-reconnect on disconnect/i);
      expect(checkbox.getAttribute('data-state')).toBe('checked');
    });

    it('allows toggling auto-reconnect checkbox', () => {
      render(<SseServerForm {...defaultProps} />);

      const checkbox = screen.getByLabelText(/auto-reconnect on disconnect/i);
      expect(checkbox.getAttribute('data-state')).toBe('checked');

      fireEvent.click(checkbox);
      expect(checkbox.getAttribute('data-state')).toBe('unchecked');

      fireEvent.click(checkbox);
      expect(checkbox.getAttribute('data-state')).toBe('checked');
    });

    it('shows reconnect delay input when auto-reconnect is enabled', () => {
      render(<SseServerForm {...defaultProps} />);

      const delayInput = screen.getByLabelText(/reconnect delay/i);
      expect(delayInput).toBeTruthy();
      expect(delayInput.getAttribute('type')).toBe('number');
    });

    it('hides reconnect delay input when auto-reconnect is disabled', () => {
      render(<SseServerForm {...defaultProps} />);

      const checkbox = screen.getByLabelText(/auto-reconnect on disconnect/i) as HTMLInputElement;
      fireEvent.click(checkbox); // Disable auto-reconnect

      const delayInput = screen.queryByLabelText(/reconnect delay/i);
      expect(delayInput).toBeNull();
    });

    it('defaults reconnect delay to 5 seconds', () => {
      render(<SseServerForm {...defaultProps} />);

      const delayInput = screen.getByLabelText(/reconnect delay/i) as HTMLInputElement;
      expect(delayInput.value).toBe('5');
    });

    it('allows user to change reconnect delay', () => {
      render(<SseServerForm {...defaultProps} />);

      const delayInput = screen.getByLabelText(/reconnect delay/i) as HTMLInputElement;
      fireEvent.change(delayInput, { target: { value: '10' } });

      expect(delayInput.value).toBe('10');
    });
  });

  describe('Authentication Section', () => {
    it('renders authentication type radio group', () => {
      render(<SseServerForm {...defaultProps} />);

      expect(screen.getByLabelText(/^none$/i)).toBeTruthy();
      expect(screen.getByLabelText(/api key/i)).toBeTruthy();
      expect(screen.getByLabelText(/bearer token/i)).toBeTruthy();
    });

    it('defaults to "None" authentication', () => {
      render(<SseServerForm {...defaultProps} />);

      const noneRadio = screen.getByRole('radio', { name: /^none$/i });
      expect(noneRadio.getAttribute('data-state')).toBe('checked');
    });

    it('does not show auth value input when "None" is selected', () => {
      render(<SseServerForm {...defaultProps} />);

      const authValueInput = screen.queryByLabelText(/api key value|bearer token value/i);
      expect(authValueInput).toBeNull();
    });

    it('shows auth value input when "API Key" is selected', async () => {
      render(<SseServerForm {...defaultProps} />);

      const apiKeyRadio = screen.getByLabelText(/api key/i);
      fireEvent.click(apiKeyRadio);

      await waitFor(() => {
        expect(screen.getByLabelText(/api key value/i)).toBeTruthy();
      });
    });

    it('shows auth value input when "Bearer Token" is selected', async () => {
      render(<SseServerForm {...defaultProps} />);

      const bearerRadio = screen.getByLabelText(/bearer token/i);
      fireEvent.click(bearerRadio);

      await waitFor(() => {
        expect(screen.getByLabelText(/bearer token value/i)).toBeTruthy();
      });
    });

    it('renders auth value as password type by default', async () => {
      render(<SseServerForm {...defaultProps} />);

      const apiKeyRadio = screen.getByLabelText(/api key/i);
      fireEvent.click(apiKeyRadio);

      await waitFor(() => {
        const authInput = screen.getByLabelText(/api key value/i) as HTMLInputElement;
        expect(authInput.type).toBe('password');
      });
    });

    it('toggles password visibility when show/hide button is clicked', async () => {
      render(<SseServerForm {...defaultProps} />);

      const apiKeyRadio = screen.getByLabelText(/api key/i);
      fireEvent.click(apiKeyRadio);

      await waitFor(() => {
        const authInput = screen.getByLabelText(/api key value/i) as HTMLInputElement;
        const toggleButton = screen.getByRole('button', { name: /show|hide/i });

        expect(authInput.type).toBe('password');

        fireEvent.click(toggleButton);
        expect(authInput.type).toBe('text');

        fireEvent.click(toggleButton);
        expect(authInput.type).toBe('password');
      });
    });

    it('allows user to type in auth value', async () => {
      render(<SseServerForm {...defaultProps} />);

      const apiKeyRadio = screen.getByLabelText(/api key/i);
      fireEvent.click(apiKeyRadio);

      await waitFor(() => {
        const authInput = screen.getByLabelText(/api key value/i) as HTMLInputElement;
        fireEvent.change(authInput, { target: { value: 'sk-1234567890' } });
        expect(authInput.value).toBe('sk-1234567890');
      });
    });
  });

  describe('Scope Selection', () => {
    it('renders scope radio group', () => {
      render(<SseServerForm {...defaultProps} />);

      expect(screen.getByLabelText(/global/i)).toBeTruthy();
      expect(screen.getByLabelText(/project/i)).toBeTruthy();
    });

    it('defaults to "Global" scope', () => {
      render(<SseServerForm {...defaultProps} />);

      const globalRadio = screen.getByRole('radio', { name: /global/i });
      expect(globalRadio.getAttribute('data-state')).toBe('checked');
    });

    it('allows changing scope to project', () => {
      render(<SseServerForm {...defaultProps} />);

      const projectRadio = screen.getByRole('radio', { name: /project/i });
      fireEvent.click(projectRadio);

      expect(projectRadio.getAttribute('data-state')).toBe('checked');
    });
  });

  describe('Form Submission', () => {
    it('calls onSubmit with form data when submitted', () => {
      render(<SseServerForm {...defaultProps} />);

      // Fill in required fields
      const nameInput = screen.getByLabelText(/server name/i);
      const urlInput = screen.getByLabelText(/sse endpoint url/i);

      fireEvent.change(nameInput, { target: { value: 'Test SSE Server' } });
      fireEvent.change(urlInput, { target: { value: 'http://localhost:8000/events' } });

      // Submit form
      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Test SSE Server',
          sseEndpoint: 'http://localhost:8000/events',
        })
      );
    });

    it('includes connection options in submission', () => {
      render(<SseServerForm {...defaultProps} />);

      // Fill in required fields
      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/sse endpoint url/i), { target: { value: 'http://localhost:8000/events' } });

      // Change reconnect delay
      const delayInput = screen.getByLabelText(/reconnect delay/i);
      fireEvent.change(delayInput, { target: { value: '10' } });

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          reconnectOnDisconnect: true,
          reconnectDelay: 10,
        })
      );
    });

    it('includes authentication data in submission when API Key is selected', async () => {
      render(<SseServerForm {...defaultProps} />);

      // Fill in required fields
      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/sse endpoint url/i), { target: { value: 'http://localhost:8000/events' } });

      // Select API Key auth
      fireEvent.click(screen.getByLabelText(/api key/i));

      await waitFor(() => {
        const authInput = screen.getByLabelText(/api key value/i);
        fireEvent.change(authInput, { target: { value: 'sk-1234' } });
      });

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          authType: 'apiKey',
          authValue: 'sk-1234',
        })
      );
    });

    it('includes scope in submission', () => {
      render(<SseServerForm {...defaultProps} />);

      // Fill in required fields
      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/sse endpoint url/i), { target: { value: 'http://localhost:8000/events' } });

      // Change to project scope
      fireEvent.click(screen.getByLabelText(/project/i));

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          scope: 'project',
        })
      );
    });

    it('does not submit when required fields are empty', () => {
      render(<SseServerForm {...defaultProps} />);

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it('validates URL format', () => {
      render(<SseServerForm {...defaultProps} />);

      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/sse endpoint url/i), { target: { value: 'invalid-url' } });

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it('submits with reconnectOnDisconnect=false when checkbox is unchecked', () => {
      render(<SseServerForm {...defaultProps} />);

      // Fill in required fields
      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/sse endpoint url/i), { target: { value: 'http://localhost:8000/events' } });

      // Disable auto-reconnect
      const checkbox = screen.getByLabelText(/auto-reconnect on disconnect/i);
      fireEvent.click(checkbox);

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          reconnectOnDisconnect: false,
        })
      );
    });
  });

  describe('Cancel Action', () => {
    it('calls onCancel when cancel button is clicked', () => {
      render(<SseServerForm {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: /back|cancel/i });
      fireEvent.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  describe('Initial Values', () => {
    it('populates fields with initial values when provided', () => {
      const initialValues = {
        name: 'Existing SSE Server',
        description: 'An existing SSE server config',
        sseEndpoint: 'https://api.example.com/events',
        reconnectOnDisconnect: false,
        reconnectDelay: 15,
        authType: 'bearerToken' as const,
        authValue: 'token-123',
        scope: 'project' as const,
      };

      render(<SseServerForm {...defaultProps} initialValues={initialValues} />);

      expect((screen.getByLabelText(/server name/i) as HTMLInputElement).value).toBe('Existing SSE Server');
      expect((screen.getByLabelText(/description/i) as HTMLInputElement).value).toBe('An existing SSE server config');
      expect((screen.getByLabelText(/sse endpoint url/i) as HTMLInputElement).value).toBe('https://api.example.com/events');

      const checkbox = screen.getByLabelText(/auto-reconnect on disconnect/i);
      expect(checkbox.getAttribute('data-state')).toBe('unchecked');

      const bearerRadio = screen.getByRole('radio', { name: /bearer token/i });
      expect(bearerRadio.getAttribute('data-state')).toBe('checked');

      const projectRadio = screen.getByRole('radio', { name: /project/i });
      expect(projectRadio.getAttribute('data-state')).toBe('checked');
    });

    it('shows reconnect delay with initial value when auto-reconnect is true', () => {
      const initialValues = {
        name: 'Test',
        sseEndpoint: 'http://localhost:8000/events',
        reconnectOnDisconnect: true,
        reconnectDelay: 20,
        authType: 'none' as const,
        scope: 'global' as const,
      };

      render(<SseServerForm {...defaultProps} initialValues={initialValues} />);

      const delayInput = screen.getByLabelText(/reconnect delay/i) as HTMLInputElement;
      expect(delayInput.value).toBe('20');
    });
  });
});
