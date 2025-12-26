import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { SessionDurationChart } from '../SessionDurationChart';

describe('SessionDurationChart', () => {
  it('renders bar chart with duration data', () => {
    const data = [
      { phase: 'planning', avg_duration_seconds: 1800 },
      { phase: 'coding', avg_duration_seconds: 3600 },
      { phase: 'validation', avg_duration_seconds: 900 }
    ];

    render(<SessionDurationChart data={data} />);

    expect(screen.getByText('Session Duration by Phase')).toBeInTheDocument();
  });

  it('shows empty state', () => {
    render(<SessionDurationChart data={[]} />);

    expect(screen.getByText(/No data available/i)).toBeInTheDocument();
  });
});
