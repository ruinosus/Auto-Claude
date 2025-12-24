/**
 * Unit tests for TemplateSelector component
 * Tests template card rendering, selection, and highlighting
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TemplateSelector } from '../TemplateSelector';

describe('TemplateSelector', () => {
  it('should render 4 template cards', () => {
    const onSelect = vi.fn();
    render(<TemplateSelector onSelect={onSelect} />);

    expect(screen.getByText('File System Tools')).toBeTruthy();
    expect(screen.getByText('API Wrapper')).toBeTruthy();
    expect(screen.getByText('Database Connector')).toBeTruthy();
    expect(screen.getByText('Blank Template')).toBeTruthy();
  });

  it('should show template descriptions', () => {
    const onSelect = vi.fn();
    render(<TemplateSelector onSelect={onSelect} />);

    expect(screen.getByText(/Read\/write files/)).toBeTruthy();
    expect(screen.getByText(/HTTP client/)).toBeTruthy();
  });

  it('should call onSelect when clicking template', () => {
    const onSelect = vi.fn();
    render(<TemplateSelector onSelect={onSelect} />);

    const fileSystemCard = screen.getByText('File System Tools').closest('button');
    fireEvent.click(fileSystemCard!);

    expect(onSelect).toHaveBeenCalledWith('file-system');
  });

  it('should highlight selected template', () => {
    const onSelect = vi.fn();
    const { rerender } = render(<TemplateSelector onSelect={onSelect} selectedId={undefined} />);

    // Get the button and then find the Card (div with border classes) inside it
    const button = screen.getByText('File System Tools').closest('button');
    const cardDiv = button?.querySelector('div');
    // Check for border-2 which indicates selected state
    expect(cardDiv?.className).not.toContain('border-2');

    rerender(<TemplateSelector onSelect={onSelect} selectedId="file-system" />);
    const buttonAfter = screen.getByText('File System Tools').closest('button');
    const cardDivAfter = buttonAfter?.querySelector('div');
    expect(cardDivAfter?.className).toContain('border-2');
    expect(cardDivAfter?.className).toContain('border-primary');
  });
});
