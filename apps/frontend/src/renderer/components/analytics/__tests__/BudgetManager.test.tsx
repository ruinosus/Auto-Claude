import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { BudgetManager } from '../BudgetManager';

describe('BudgetManager', () => {
  it('renders budget form', () => {
    render(<BudgetManager currentCost={5.5} />);

    expect(screen.getByText(/Budget Manager/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Budget limit/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Set Budget/i })).toBeInTheDocument();
  });

  it('displays current cost', () => {
    render(<BudgetManager currentCost={5.5} />);

    expect(screen.getByText('Current Cost:')).toBeInTheDocument();
    expect(screen.getByText('$5.50')).toBeInTheDocument();
  });

  it('shows progress bar when budget is set', () => {
    render(<BudgetManager currentCost={8.0} budgetLimit={10.0} />);

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.getByText('Budget Limit:')).toBeInTheDocument();
    expect(screen.getByText('$10.00')).toBeInTheDocument();
  });

  it('calculates and displays budget usage percentage', () => {
    render(<BudgetManager currentCost={7.5} budgetLimit={10.0} />);

    expect(screen.getByText('75.0%')).toBeInTheDocument();
  });

  it('calls onBudgetChange when budget is set', () => {
    const handleBudgetChange = vi.fn();
    render(<BudgetManager currentCost={5.0} onBudgetChange={handleBudgetChange} />);

    const input = screen.getByPlaceholderText(/Budget limit/i);
    const button = screen.getByRole('button', { name: /Set Budget/i });

    fireEvent.change(input, { target: { value: '20' } });
    fireEvent.click(button);

    expect(handleBudgetChange).toHaveBeenCalledWith(20);
  });

  it('does not call onBudgetChange for invalid input', () => {
    const handleBudgetChange = vi.fn();
    render(<BudgetManager currentCost={5.0} onBudgetChange={handleBudgetChange} />);

    const input = screen.getByPlaceholderText(/Budget limit/i);
    const button = screen.getByRole('button', { name: /Set Budget/i });

    fireEvent.change(input, { target: { value: '-10' } });
    fireEvent.click(button);

    expect(handleBudgetChange).not.toHaveBeenCalled();
  });

  it('shows green progress bar when usage is below 80%', () => {
    const { container } = render(<BudgetManager currentCost={7.0} budgetLimit={10.0} />);

    const progressBar = container.querySelector('.bg-primary');
    expect(progressBar).toBeInTheDocument();
  });

  it('shows yellow progress bar when usage is between 80% and 90%', () => {
    const { container } = render(<BudgetManager currentCost={8.5} budgetLimit={10.0} />);

    const progressBar = container.querySelector('.bg-yellow-500');
    expect(progressBar).toBeInTheDocument();
  });

  it('shows red progress bar when usage is 90% or above', () => {
    const { container } = render(<BudgetManager currentCost={9.5} budgetLimit={10.0} />);

    const progressBar = container.querySelector('.bg-destructive');
    expect(progressBar).toBeInTheDocument();
  });

  it('populates input field with initial budget limit', () => {
    render(<BudgetManager currentCost={5.0} budgetLimit={15.0} />);

    const input = screen.getByPlaceholderText(/Budget limit/i) as HTMLInputElement;
    expect(input.value).toBe('15');
  });
});
