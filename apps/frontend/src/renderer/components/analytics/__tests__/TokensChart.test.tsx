import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { TokensChart } from '../TokensChart';

describe('TokensChart', () => {
  it('renders stacked bar chart', () => {
    const data = [
      { spec_id: '001-auth', input_tokens: 50000, output_tokens: 25000 },
      { spec_id: '002-dashboard', input_tokens: 120000, output_tokens: 60000 }
    ];

    render(<TokensChart data={data} />);

    expect(screen.getByText('Tokens By Spec')).toBeInTheDocument();
  });

  it('shows empty state', () => {
    render(<TokensChart data={[]} />);

    expect(screen.getByText(/No data available/i)).toBeInTheDocument();
  });
});
