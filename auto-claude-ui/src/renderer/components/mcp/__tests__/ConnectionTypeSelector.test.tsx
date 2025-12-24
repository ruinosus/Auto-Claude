/**
 * Unit tests for ConnectionTypeSelector component
 * Tests radio button selection for HTTP/stdio/SSE connection types
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConnectionTypeSelector } from '../ConnectionTypeSelector';

describe('ConnectionTypeSelector', () => {
  it('renders all three connection type options', () => {
    const onChange = vi.fn();
    render(<ConnectionTypeSelector value="http" onChange={onChange} />);

    expect(screen.getByText('HTTP/HTTPS')).toBeTruthy();
    expect(screen.getByText('Standard I/O')).toBeTruthy();
    expect(screen.getByText('Server-Sent Events')).toBeTruthy();
  });

  it('displays HTTP as selected by default when value is http', () => {
    const onChange = vi.fn();
    render(<ConnectionTypeSelector value="http" onChange={onChange} />);

    const httpRadio = screen.getByRole('radio', { name: /HTTP\/HTTPS/i });
    expect(httpRadio.getAttribute('data-state')).toBe('checked');
  });

  it('displays stdio as selected when value is stdio', () => {
    const onChange = vi.fn();
    render(<ConnectionTypeSelector value="stdio" onChange={onChange} />);

    const stdioRadio = screen.getByRole('radio', { name: /Standard I\/O/i });
    expect(stdioRadio.getAttribute('data-state')).toBe('checked');
  });

  it('displays SSE as selected when value is sse', () => {
    const onChange = vi.fn();
    render(<ConnectionTypeSelector value="sse" onChange={onChange} />);

    const sseRadio = screen.getByRole('radio', { name: /Server-Sent Events/i });
    expect(sseRadio.getAttribute('data-state')).toBe('checked');
  });

  it('calls onChange with http when HTTP radio is clicked', () => {
    const onChange = vi.fn();
    render(<ConnectionTypeSelector value="stdio" onChange={onChange} />);

    const httpRadio = screen.getByRole('radio', { name: /HTTP\/HTTPS/i });
    fireEvent.click(httpRadio);

    expect(onChange).toHaveBeenCalledWith('http');
  });

  it('calls onChange with stdio when stdio radio is clicked', () => {
    const onChange = vi.fn();
    render(<ConnectionTypeSelector value="http" onChange={onChange} />);

    const stdioRadio = screen.getByRole('radio', { name: /Standard I\/O/i });
    fireEvent.click(stdioRadio);

    expect(onChange).toHaveBeenCalledWith('stdio');
  });

  it('calls onChange with sse when SSE radio is clicked', () => {
    const onChange = vi.fn();
    render(<ConnectionTypeSelector value="http" onChange={onChange} />);

    const sseRadio = screen.getByRole('radio', { name: /Server-Sent Events/i });
    fireEvent.click(sseRadio);

    expect(onChange).toHaveBeenCalledWith('sse');
  });

  it('displays descriptions for each connection type', () => {
    const onChange = vi.fn();
    render(<ConnectionTypeSelector value="http" onChange={onChange} />);

    expect(screen.getByText(/REST API/i)).toBeTruthy();
    expect(screen.getByText(/command-line/i)).toBeTruthy();
    expect(screen.getByText(/real-time/i)).toBeTruthy();
  });
});
