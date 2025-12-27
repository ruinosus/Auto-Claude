/**
 * Unit tests for HttpServerForm component
 * Tests HTTP/HTTPS MCP server configuration form
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { HttpServerForm } from '../HttpServerForm';

describe('HttpServerForm', () => {
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
      render(<HttpServerForm {...defaultProps} />);

      const nameInput = screen.getByLabelText(/server name/i);
      expect(nameInput).toBeTruthy();
      expect(nameInput.getAttribute('required')).toBe('');
    });

    it('renders description input field', () => {
      render(<HttpServerForm {...defaultProps} />);

      const descInput = screen.getByLabelText(/description/i);
      expect(descInput).toBeTruthy();
      expect(descInput.getAttribute('required')).toBeNull();
    });

    it('renders base URL input field', () => {
      render(<HttpServerForm {...defaultProps} />);

      const urlInput = screen.getByLabelText(/base url/i);
      expect(urlInput).toBeTruthy();
      expect(urlInput.getAttribute('required')).toBe('');
    });

    it('allows user to type in server name', () => {
      render(<HttpServerForm {...defaultProps} />);

      const nameInput = screen.getByLabelText(/server name/i) as HTMLInputElement;
      fireEvent.change(nameInput, { target: { value: 'My Custom Server' } });

      expect(nameInput.value).toBe('My Custom Server');
    });

    it('allows user to type in description', () => {
      render(<HttpServerForm {...defaultProps} />);

      const descInput = screen.getByLabelText(/description/i) as HTMLInputElement;
      fireEvent.change(descInput, { target: { value: 'Custom MCP server for testing' } });

      expect(descInput.value).toBe('Custom MCP server for testing');
    });

    it('allows user to type in base URL', () => {
      render(<HttpServerForm {...defaultProps} />);

      const urlInput = screen.getByLabelText(/base url/i) as HTMLInputElement;
      fireEvent.change(urlInput, { target: { value: 'http://localhost:8000' } });

      expect(urlInput.value).toBe('http://localhost:8000');
    });
  });

  describe('Authentication Section', () => {
    it('renders authentication type radio group', () => {
      render(<HttpServerForm {...defaultProps} />);

      expect(screen.getByLabelText(/none/i)).toBeTruthy();
      expect(screen.getByLabelText(/api key/i)).toBeTruthy();
      expect(screen.getByLabelText(/bearer token/i)).toBeTruthy();
    });

    it('defaults to "None" authentication', () => {
      render(<HttpServerForm {...defaultProps} />);

      const noneRadio = screen.getByRole('radio', { name: /none/i });
      expect(noneRadio.getAttribute('data-state')).toBe('checked');
    });

    it('does not show auth value input when "None" is selected', () => {
      render(<HttpServerForm {...defaultProps} />);

      const authValueInput = screen.queryByLabelText(/api key value|bearer token value/i);
      expect(authValueInput).toBeNull();
    });

    it('shows auth value input when "API Key" is selected', async () => {
      render(<HttpServerForm {...defaultProps} />);

      const apiKeyRadio = screen.getByLabelText(/api key/i);
      fireEvent.click(apiKeyRadio);

      await waitFor(() => {
        expect(screen.getByLabelText(/api key value/i)).toBeTruthy();
      });
    });

    it('shows auth value input when "Bearer Token" is selected', async () => {
      render(<HttpServerForm {...defaultProps} />);

      const bearerRadio = screen.getByLabelText(/bearer token/i);
      fireEvent.click(bearerRadio);

      await waitFor(() => {
        expect(screen.getByLabelText(/bearer token value/i)).toBeTruthy();
      });
    });

    it('renders auth value as password type by default', async () => {
      render(<HttpServerForm {...defaultProps} />);

      const apiKeyRadio = screen.getByLabelText(/api key/i);
      fireEvent.click(apiKeyRadio);

      await waitFor(() => {
        const authInput = screen.getByLabelText(/api key value/i) as HTMLInputElement;
        expect(authInput.type).toBe('password');
      });
    });

    it('toggles password visibility when show/hide button is clicked', async () => {
      render(<HttpServerForm {...defaultProps} />);

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
      render(<HttpServerForm {...defaultProps} />);

      const apiKeyRadio = screen.getByLabelText(/api key/i);
      fireEvent.click(apiKeyRadio);

      await waitFor(() => {
        const authInput = screen.getByLabelText(/api key value/i) as HTMLInputElement;
        fireEvent.change(authInput, { target: { value: 'sk-1234567890' } });
        expect(authInput.value).toBe('sk-1234567890');
      });
    });
  });

  describe('Custom Headers Section', () => {
    it('renders "Add Header" button', () => {
      render(<HttpServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add header/i });
      expect(addButton).toBeTruthy();
    });

    it('does not show header inputs initially', () => {
      render(<HttpServerForm {...defaultProps} />);

      const keyInputs = screen.queryAllByPlaceholderText(/header key|key/i);
      expect(keyInputs.length).toBe(0);
    });

    it('adds a new header row when "Add Header" is clicked', () => {
      render(<HttpServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add header/i });
      fireEvent.click(addButton);

      const keyInputs = screen.getAllByPlaceholderText(/header key|key/i);
      const valueInputs = screen.getAllByPlaceholderText(/header value|value/i);

      expect(keyInputs.length).toBe(1);
      expect(valueInputs.length).toBe(1);
    });

    it('allows adding multiple headers', () => {
      render(<HttpServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add header/i });
      fireEvent.click(addButton);
      fireEvent.click(addButton);
      fireEvent.click(addButton);

      const keyInputs = screen.getAllByPlaceholderText(/header key|key/i);
      expect(keyInputs.length).toBe(3);
    });

    it('allows user to type header key and value', () => {
      render(<HttpServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add header/i });
      fireEvent.click(addButton);

      const keyInput = screen.getByPlaceholderText(/header key|key/i) as HTMLInputElement;
      const valueInput = screen.getByPlaceholderText(/header value|value/i) as HTMLInputElement;

      fireEvent.change(keyInput, { target: { value: 'X-Custom-Header' } });
      fireEvent.change(valueInput, { target: { value: 'custom-value' } });

      expect(keyInput.value).toBe('X-Custom-Header');
      expect(valueInput.value).toBe('custom-value');
    });

    it('renders remove button for each header', () => {
      render(<HttpServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add header/i });
      fireEvent.click(addButton);
      fireEvent.click(addButton);

      const removeButtons = screen.getAllByRole('button', { name: /remove|delete/i });
      expect(removeButtons.length).toBe(2);
    });

    it('removes header when remove button is clicked', () => {
      render(<HttpServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add header/i });
      fireEvent.click(addButton);
      fireEvent.click(addButton);

      let keyInputs = screen.getAllByPlaceholderText(/header key|key/i);
      expect(keyInputs.length).toBe(2);

      const removeButtons = screen.getAllByRole('button', { name: /remove|delete/i });
      fireEvent.click(removeButtons[0]);

      keyInputs = screen.getAllByPlaceholderText(/header key|key/i);
      expect(keyInputs.length).toBe(1);
    });
  });

  describe('Scope Selection', () => {
    it('renders scope radio group', () => {
      render(<HttpServerForm {...defaultProps} />);

      expect(screen.getByLabelText(/global/i)).toBeTruthy();
      expect(screen.getByLabelText(/project/i)).toBeTruthy();
    });

    it('defaults to "Global" scope', () => {
      render(<HttpServerForm {...defaultProps} />);

      const globalRadio = screen.getByRole('radio', { name: /global/i });
      expect(globalRadio.getAttribute('data-state')).toBe('checked');
    });

    it('allows changing scope to project', () => {
      render(<HttpServerForm {...defaultProps} />);

      const projectRadio = screen.getByRole('radio', { name: /project/i });
      fireEvent.click(projectRadio);

      expect(projectRadio.getAttribute('data-state')).toBe('checked');
    });
  });

  describe('Form Submission', () => {
    it('calls onSubmit with form data when submitted', () => {
      render(<HttpServerForm {...defaultProps} />);

      // Fill in required fields
      const nameInput = screen.getByLabelText(/server name/i);
      const urlInput = screen.getByLabelText(/base url/i);

      fireEvent.change(nameInput, { target: { value: 'Test Server' } });
      fireEvent.change(urlInput, { target: { value: 'http://localhost:8000' } });

      // Submit form
      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Test Server',
          baseUrl: 'http://localhost:8000',
        })
      );
    });

    it('includes authentication data in submission when API Key is selected', async () => {
      render(<HttpServerForm {...defaultProps} />);

      // Fill in required fields
      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/base url/i), { target: { value: 'http://localhost:8000' } });

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

    it('includes custom headers in submission', () => {
      render(<HttpServerForm {...defaultProps} />);

      // Fill in required fields
      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/base url/i), { target: { value: 'http://localhost:8000' } });

      // Add headers
      const addButton = screen.getByRole('button', { name: /add header/i });
      fireEvent.click(addButton);

      const keyInput = screen.getByPlaceholderText(/header key|key/i);
      const valueInput = screen.getByPlaceholderText(/header value|value/i);

      fireEvent.change(keyInput, { target: { value: 'X-Custom-Header' } });
      fireEvent.change(valueInput, { target: { value: 'custom-value' } });

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          customHeaders: {
            'X-Custom-Header': 'custom-value',
          },
        })
      );
    });

    it('includes scope in submission', () => {
      render(<HttpServerForm {...defaultProps} />);

      // Fill in required fields
      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/base url/i), { target: { value: 'http://localhost:8000' } });

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
      render(<HttpServerForm {...defaultProps} />);

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it('validates URL format', () => {
      render(<HttpServerForm {...defaultProps} />);

      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/base url/i), { target: { value: 'invalid-url' } });

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });

  describe('Cancel Action', () => {
    it('calls onCancel when cancel button is clicked', () => {
      render(<HttpServerForm {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: /back|cancel/i });
      fireEvent.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  describe('Initial Values', () => {
    it('populates fields with initial values when provided', () => {
      const initialValues = {
        name: 'Existing Server',
        description: 'An existing server config',
        baseUrl: 'https://api.example.com',
        authType: 'bearerToken' as const,
        authValue: 'token-123',
        customHeaders: {
          'X-Header-1': 'value-1',
          'X-Header-2': 'value-2',
        },
        scope: 'project' as const,
      };

      render(<HttpServerForm {...defaultProps} initialValues={initialValues} />);

      expect((screen.getByLabelText(/server name/i) as HTMLInputElement).value).toBe('Existing Server');
      expect((screen.getByLabelText(/description/i) as HTMLInputElement).value).toBe('An existing server config');
      expect((screen.getByLabelText(/base url/i) as HTMLInputElement).value).toBe('https://api.example.com');

      const bearerRadio = screen.getByRole('radio', { name: /bearer token/i });
      expect(bearerRadio.getAttribute('data-state')).toBe('checked');

      const projectRadio = screen.getByRole('radio', { name: /project/i });
      expect(projectRadio.getAttribute('data-state')).toBe('checked');
    });
  });
});
