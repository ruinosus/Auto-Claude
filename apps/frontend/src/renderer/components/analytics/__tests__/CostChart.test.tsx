import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { CostChart } from '../CostChart';

describe('CostChart', () => {
  it('renders chart with data', () => {
    const data = [
      { timestamp: '2025-12-20', cost: 0.5 },
      { timestamp: '2025-12-21', cost: 1.2 },
      { timestamp: '2025-12-22', cost: 0.8 }
    ];

    render(<CostChart data={data} budgetLimit={10} />);

    expect(screen.getByText('Cost Over Time')).toBeInTheDocument();
  });

  it('shows empty state when no data', () => {
    render(<CostChart data={[]} />);

    expect(screen.getByText(/No data available/i)).toBeInTheDocument();
  });
});
