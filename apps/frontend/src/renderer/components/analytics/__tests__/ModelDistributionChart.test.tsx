import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { ModelDistributionChart } from '../ModelDistributionChart';

describe('ModelDistributionChart', () => {
  it('renders pie chart with data', () => {
    const data = [
      { model: 'claude-sonnet-4-5', count: 100, percentage: 75 },
      { model: 'claude-opus-4-5', count: 33, percentage: 25 }
    ];

    render(<ModelDistributionChart data={data} />);

    expect(screen.getByText('Model Distribution')).toBeInTheDocument();
  });

  it('shows empty state', () => {
    render(<ModelDistributionChart data={[]} />);

    expect(screen.getByText(/No data available/i)).toBeInTheDocument();
  });
});
