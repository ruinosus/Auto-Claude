/**
 * Unit tests for StdioServerForm component
 * Tests stdio (Standard I/O) MCP server configuration form
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { StdioServerForm } from '../StdioServerForm';

describe('StdioServerForm', () => {
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();
  const mockOnBrowseCommand = vi.fn();
  const mockOnBrowseWorkingDir = vi.fn();

  const defaultProps = {
    onSubmit: mockOnSubmit,
    onCancel: mockOnCancel,
    onBrowseCommand: mockOnBrowseCommand,
    onBrowseWorkingDir: mockOnBrowseWorkingDir,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Information Fields', () => {
    it('renders server name input field', () => {
      render(<StdioServerForm {...defaultProps} />);

      const nameInput = screen.getByLabelText(/server name/i);
      expect(nameInput).toBeTruthy();
      expect(nameInput.getAttribute('required')).toBe('');
    });

    it('renders description input field', () => {
      render(<StdioServerForm {...defaultProps} />);

      const descInput = screen.getByLabelText(/description/i);
      expect(descInput).toBeTruthy();
      expect(descInput.getAttribute('required')).toBeNull();
    });

    it('allows user to type in server name', () => {
      render(<StdioServerForm {...defaultProps} />);

      const nameInput = screen.getByLabelText(/server name/i) as HTMLInputElement;
      fireEvent.change(nameInput, { target: { value: 'My stdio Server' } });

      expect(nameInput.value).toBe('My stdio Server');
    });

    it('allows user to type in description', () => {
      render(<StdioServerForm {...defaultProps} />);

      const descInput = screen.getByLabelText(/description/i) as HTMLInputElement;
      fireEvent.change(descInput, { target: { value: 'Local MCP server via stdio' } });

      expect(descInput.value).toBe('Local MCP server via stdio');
    });
  });

  describe('Command Configuration', () => {
    it('renders command input field', () => {
      render(<StdioServerForm {...defaultProps} />);

      const commandInput = screen.getByLabelText(/^command/i);
      expect(commandInput).toBeTruthy();
      expect(commandInput.getAttribute('required')).toBe('');
    });

    it('renders command browse button', () => {
      render(<StdioServerForm {...defaultProps} />);

      const browseButton = screen.getByRole('button', { name: /browse.*command/i });
      expect(browseButton).toBeTruthy();
    });

    it('calls onBrowseCommand when browse button is clicked', () => {
      render(<StdioServerForm {...defaultProps} />);

      const browseButton = screen.getByRole('button', { name: /browse.*command/i });
      fireEvent.click(browseButton);

      expect(mockOnBrowseCommand).toHaveBeenCalled();
    });

    it('allows user to type in command', () => {
      render(<StdioServerForm {...defaultProps} />);

      const commandInput = screen.getByLabelText(/^command/i) as HTMLInputElement;
      fireEvent.change(commandInput, { target: { value: 'python3' } });

      expect(commandInput.value).toBe('python3');
    });

    it('renders arguments input field', () => {
      render(<StdioServerForm {...defaultProps} />);

      const argsInput = screen.getByLabelText(/arguments/i);
      expect(argsInput).toBeTruthy();
      expect(argsInput.getAttribute('required')).toBeNull();
    });

    it('allows user to type in arguments', () => {
      render(<StdioServerForm {...defaultProps} />);

      const argsInput = screen.getByLabelText(/arguments/i) as HTMLInputElement;
      fireEvent.change(argsInput, { target: { value: 'server.py --port 8000' } });

      expect(argsInput.value).toBe('server.py --port 8000');
    });

    it('renders working directory input field', () => {
      render(<StdioServerForm {...defaultProps} />);

      const workingDirInput = screen.getByLabelText(/^working directory/i);
      expect(workingDirInput).toBeTruthy();
      expect(workingDirInput.getAttribute('required')).toBeNull();
    });

    it('renders working directory browse button', () => {
      render(<StdioServerForm {...defaultProps} />);

      const browseButton = screen.getByRole('button', { name: /browse.*working/i });
      expect(browseButton).toBeTruthy();
    });

    it('calls onBrowseWorkingDir when browse button is clicked', () => {
      render(<StdioServerForm {...defaultProps} />);

      const browseButton = screen.getByRole('button', { name: /browse.*working/i });
      fireEvent.click(browseButton);

      expect(mockOnBrowseWorkingDir).toHaveBeenCalled();
    });

    it('allows user to type in working directory', () => {
      render(<StdioServerForm {...defaultProps} />);

      const workingDirInput = screen.getByLabelText(/^working directory/i) as HTMLInputElement;
      fireEvent.change(workingDirInput, { target: { value: '/path/to/server' } });

      expect(workingDirInput.value).toBe('/path/to/server');
    });
  });

  describe('Environment Variables Section', () => {
    it('renders "Add Variable" button', () => {
      render(<StdioServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add variable/i });
      expect(addButton).toBeTruthy();
    });

    it('does not show variable inputs initially', () => {
      render(<StdioServerForm {...defaultProps} />);

      const keyInputs = screen.queryAllByPlaceholderText(/variable name|key/i);
      expect(keyInputs.length).toBe(0);
    });

    it('adds a new variable row when "Add Variable" is clicked', () => {
      render(<StdioServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add variable/i });
      fireEvent.click(addButton);

      const keyInputs = screen.getAllByPlaceholderText(/variable name|key/i);
      const valueInputs = screen.getAllByPlaceholderText(/variable value|value/i);

      expect(keyInputs.length).toBe(1);
      expect(valueInputs.length).toBe(1);
    });

    it('allows adding multiple variables', () => {
      render(<StdioServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add variable/i });
      fireEvent.click(addButton);
      fireEvent.click(addButton);
      fireEvent.click(addButton);

      const keyInputs = screen.getAllByPlaceholderText(/variable name|key/i);
      expect(keyInputs.length).toBe(3);
    });

    it('allows user to type variable key and value', () => {
      render(<StdioServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add variable/i });
      fireEvent.click(addButton);

      const keyInput = screen.getByPlaceholderText(/variable name|key/i) as HTMLInputElement;
      const valueInput = screen.getByPlaceholderText(/variable value|value/i) as HTMLInputElement;

      fireEvent.change(keyInput, { target: { value: 'API_KEY' } });
      fireEvent.change(valueInput, { target: { value: 'secret-key-123' } });

      expect(keyInput.value).toBe('API_KEY');
      expect(valueInput.value).toBe('secret-key-123');
    });

    it('renders remove button for each variable', () => {
      render(<StdioServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add variable/i });
      fireEvent.click(addButton);
      fireEvent.click(addButton);

      const removeButtons = screen.getAllByRole('button', { name: /remove|delete/i });
      expect(removeButtons.length).toBe(2);
    });

    it('removes variable when remove button is clicked', () => {
      render(<StdioServerForm {...defaultProps} />);

      const addButton = screen.getByRole('button', { name: /add variable/i });
      fireEvent.click(addButton);
      fireEvent.click(addButton);

      let keyInputs = screen.getAllByPlaceholderText(/variable name|key/i);
      expect(keyInputs.length).toBe(2);

      const removeButtons = screen.getAllByRole('button', { name: /remove|delete/i });
      fireEvent.click(removeButtons[0]);

      keyInputs = screen.getAllByPlaceholderText(/variable name|key/i);
      expect(keyInputs.length).toBe(1);
    });
  });

  describe('Scope Selection', () => {
    it('renders scope radio group', () => {
      render(<StdioServerForm {...defaultProps} />);

      expect(screen.getByLabelText(/global/i)).toBeTruthy();
      expect(screen.getByLabelText(/project/i)).toBeTruthy();
    });

    it('defaults to "Global" scope', () => {
      render(<StdioServerForm {...defaultProps} />);

      const globalRadio = screen.getByRole('radio', { name: /global/i });
      expect(globalRadio.getAttribute('data-state')).toBe('checked');
    });

    it('allows changing scope to project', () => {
      render(<StdioServerForm {...defaultProps} />);

      const projectRadio = screen.getByRole('radio', { name: /project/i });
      fireEvent.click(projectRadio);

      expect(projectRadio.getAttribute('data-state')).toBe('checked');
    });
  });

  describe('Form Submission', () => {
    it('calls onSubmit with form data when submitted', () => {
      render(<StdioServerForm {...defaultProps} />);

      // Fill in required fields
      const nameInput = screen.getByLabelText(/server name/i);
      const commandInput = screen.getByLabelText(/^command/i);

      fireEvent.change(nameInput, { target: { value: 'Test Server' } });
      fireEvent.change(commandInput, { target: { value: 'python3' } });

      // Submit form
      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Test Server',
          command: 'python3',
        })
      );
    });

    it('includes optional fields in submission when provided', () => {
      render(<StdioServerForm {...defaultProps} />);

      // Fill in required fields
      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/^command/i), { target: { value: 'python3' } });

      // Fill in optional fields
      fireEvent.change(screen.getByLabelText(/description/i), { target: { value: 'Test description' } });
      fireEvent.change(screen.getByLabelText(/arguments/i), { target: { value: 'server.py' } });
      fireEvent.change(screen.getByLabelText(/^working directory/i), { target: { value: '/path/to/server' } });

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          description: 'Test description',
          args: 'server.py',
          workingDir: '/path/to/server',
        })
      );
    });

    it('includes environment variables in submission', () => {
      render(<StdioServerForm {...defaultProps} />);

      // Fill in required fields
      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/^command/i), { target: { value: 'python3' } });

      // Add environment variables
      const addButton = screen.getByRole('button', { name: /add variable/i });
      fireEvent.click(addButton);

      const keyInput = screen.getByPlaceholderText(/variable name|key/i);
      const valueInput = screen.getByPlaceholderText(/variable value|value/i);

      fireEvent.change(keyInput, { target: { value: 'API_KEY' } });
      fireEvent.change(valueInput, { target: { value: 'secret-key' } });

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          env: {
            'API_KEY': 'secret-key',
          },
        })
      );
    });

    it('includes scope in submission', () => {
      render(<StdioServerForm {...defaultProps} />);

      // Fill in required fields
      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/^command/i), { target: { value: 'python3' } });

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
      render(<StdioServerForm {...defaultProps} />);

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it('filters out empty environment variables from submission', () => {
      render(<StdioServerForm {...defaultProps} />);

      // Fill in required fields
      fireEvent.change(screen.getByLabelText(/server name/i), { target: { value: 'Test Server' } });
      fireEvent.change(screen.getByLabelText(/^command/i), { target: { value: 'python3' } });

      // Add variables - one complete, one empty
      const addButton = screen.getByRole('button', { name: /add variable/i });
      fireEvent.click(addButton);
      fireEvent.click(addButton);

      const keyInputs = screen.getAllByPlaceholderText(/variable name|key/i);
      const valueInputs = screen.getAllByPlaceholderText(/variable value|value/i);

      fireEvent.change(keyInputs[0], { target: { value: 'API_KEY' } });
      fireEvent.change(valueInputs[0], { target: { value: 'secret-key' } });
      // Leave second variable empty

      const submitButton = screen.getByRole('button', { name: /next|save|submit/i });
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          env: {
            'API_KEY': 'secret-key',
          },
        })
      );
    });
  });

  describe('Cancel Action', () => {
    it('calls onCancel when cancel button is clicked', () => {
      render(<StdioServerForm {...defaultProps} />);

      const cancelButton = screen.getByRole('button', { name: /back|cancel/i });
      fireEvent.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  describe('Initial Values', () => {
    it('populates fields with initial values when provided', () => {
      const initialValues = {
        name: 'Existing Server',
        description: 'An existing stdio server',
        command: 'node',
        args: 'server.js',
        workingDir: '/opt/server',
        env: {
          'NODE_ENV': 'production',
          'PORT': '3000',
        },
        scope: 'project' as const,
      };

      render(<StdioServerForm {...defaultProps} initialValues={initialValues} />);

      expect((screen.getByLabelText(/server name/i) as HTMLInputElement).value).toBe('Existing Server');
      expect((screen.getByLabelText(/description/i) as HTMLInputElement).value).toBe('An existing stdio server');
      expect((screen.getByLabelText(/^command/i) as HTMLInputElement).value).toBe('node');
      expect((screen.getByLabelText(/arguments/i) as HTMLInputElement).value).toBe('server.js');
      expect((screen.getByLabelText(/^working directory/i) as HTMLInputElement).value).toBe('/opt/server');

      const projectRadio = screen.getByRole('radio', { name: /project/i });
      expect(projectRadio.getAttribute('data-state')).toBe('checked');

      // Check that environment variables are populated
      const keyInputs = screen.getAllByPlaceholderText(/variable name|key/i);
      const valueInputs = screen.getAllByPlaceholderText(/variable value|value/i);
      expect(keyInputs.length).toBe(2);
      expect((keyInputs[0] as HTMLInputElement).value).toMatch(/NODE_ENV|PORT/);
      expect((keyInputs[1] as HTMLInputElement).value).toMatch(/NODE_ENV|PORT/);
    });
  });
});
