import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { OverviewCards } from '../OverviewCards';

describe('OverviewCards', () => {
  it('renders all four cards', () => {
    const data = {
      totalCost: 1.5432,
      totalTokens: { input: 1234567, output: 654321 },
      activeSessions: 3,
      budgetRemaining: 8.5
    };

    render(<OverviewCards data={data} />);

    expect(screen.getByText('Total Cost')).toBeInTheDocument();
    expect(screen.getByText('$1.5432')).toBeInTheDocument();

    expect(screen.getByText('Total Tokens')).toBeInTheDocument();
    expect(screen.getByText('1.23M input / 654K output')).toBeInTheDocument();

    expect(screen.getByText('Active Sessions')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();

    expect(screen.getByText('Budget Remaining')).toBeInTheDocument();
    expect(screen.getByText('$8.50')).toBeInTheDocument();
  });

  it('formats large numbers correctly', () => {
    const data = {
      totalCost: 123.456,
      totalTokens: { input: 15234567, output: 8654321 },
      activeSessions: 0,
      budgetRemaining: 0
    };

    render(<OverviewCards data={data} />);

    expect(screen.getByText('15.23M input / 8.65M output')).toBeInTheDocument();
  });
});
