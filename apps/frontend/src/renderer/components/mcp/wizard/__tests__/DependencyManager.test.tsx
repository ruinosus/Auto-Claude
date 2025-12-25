/**
 * Unit tests for DependencyManager component
 * Tests dependency list rendering, add/remove actions, validation, and protection of required dependencies
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DependencyManager } from '../DependencyManager';

describe('DependencyManager', () => {
  const mockDependencies = [
    'fastmcp>=0.1.0',
    'httpx>=0.25.0',
    'pydantic>=2.0.0'
  ];

  it('should render dependency list with template dependencies', () => {
    const onDependenciesChange = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <DependencyManager
        dependencies={mockDependencies}
        onDependenciesChange={onDependenciesChange}
        onNext={onNext}
        onBack={onBack}
      />
    );

    // Should show all dependencies
    expect(screen.getByDisplayValue('fastmcp>=0.1.0')).toBeTruthy();
    expect(screen.getByDisplayValue('httpx>=0.25.0')).toBeTruthy();
    expect(screen.getByDisplayValue('pydantic>=2.0.0')).toBeTruthy();
  });

  it('should show "Add Dependency" button', () => {
    const onDependenciesChange = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <DependencyManager
        dependencies={mockDependencies}
        onDependenciesChange={onDependenciesChange}
        onNext={onNext}
        onBack={onBack}
      />
    );

    const addButton = screen.getByText('Add Dependency');
    expect(addButton).toBeTruthy();
  });

  it('should allow adding a new dependency', () => {
    const onDependenciesChange = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <DependencyManager
        dependencies={mockDependencies}
        onDependenciesChange={onDependenciesChange}
        onNext={onNext}
        onBack={onBack}
      />
    );

    const addButton = screen.getByText('Add Dependency');
    fireEvent.click(addButton);

    // Should call onDependenciesChange with new empty dependency
    expect(onDependenciesChange).toHaveBeenCalledWith([
      ...mockDependencies,
      ''
    ]);
  });

  it('should allow removing a dependency', () => {
    const onDependenciesChange = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <DependencyManager
        dependencies={mockDependencies}
        onDependenciesChange={onDependenciesChange}
        onNext={onNext}
        onBack={onBack}
      />
    );

    // Find all remove buttons (should be 3 total, but fastmcp should be disabled)
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });

    // Click the second remove button (httpx)
    fireEvent.click(removeButtons[1]);

    // Should call onDependenciesChange without the httpx dependency
    expect(onDependenciesChange).toHaveBeenCalledWith([
      'fastmcp>=0.1.0',
      'pydantic>=2.0.0'
    ]);
  });

  it('should prevent removing fastmcp dependency', () => {
    const onDependenciesChange = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <DependencyManager
        dependencies={mockDependencies}
        onDependenciesChange={onDependenciesChange}
        onNext={onNext}
        onBack={onBack}
      />
    );

    // Find all remove buttons
    const removeButtons = screen.getAllByRole('button', { name: /remove fastmcp/i });

    // First remove button should be disabled (fastmcp)
    expect(removeButtons[0].hasAttribute('disabled')).toBe(true);
  });

  it('should call onNext with updated dependencies', () => {
    const onDependenciesChange = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <DependencyManager
        dependencies={mockDependencies}
        onDependenciesChange={onDependenciesChange}
        onNext={onNext}
        onBack={onBack}
      />
    );

    const nextButton = screen.getByText('Next');
    fireEvent.click(nextButton);

    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('should show helper text about uv', () => {
    const onDependenciesChange = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <DependencyManager
        dependencies={mockDependencies}
        onDependenciesChange={onDependenciesChange}
        onNext={onNext}
        onBack={onBack}
      />
    );

    // Should show helper text
    expect(screen.getByText(/uv handles virtual environment automatically/i)).toBeTruthy();
  });

  it('should allow editing dependency inline', () => {
    const onDependenciesChange = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <DependencyManager
        dependencies={mockDependencies}
        onDependenciesChange={onDependenciesChange}
        onNext={onNext}
        onBack={onBack}
      />
    );

    // Find the httpx input and change it
    const httpxInput = screen.getByDisplayValue('httpx>=0.25.0');
    fireEvent.change(httpxInput, { target: { value: 'httpx>=0.26.0' } });

    // Should call onDependenciesChange with updated dependency
    expect(onDependenciesChange).toHaveBeenCalledWith([
      'fastmcp>=0.1.0',
      'httpx>=0.26.0',
      'pydantic>=2.0.0'
    ]);
  });

  it('should call onBack when Back button clicked', () => {
    const onDependenciesChange = vi.fn();
    const onNext = vi.fn();
    const onBack = vi.fn();

    render(
      <DependencyManager
        dependencies={mockDependencies}
        onDependenciesChange={onDependenciesChange}
        onNext={onNext}
        onBack={onBack}
      />
    );

    const backButton = screen.getByText('Back');
    fireEvent.click(backButton);

    expect(onBack).toHaveBeenCalledTimes(1);
  });
});
