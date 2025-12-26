import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { Analytics } from '../Analytics';
import { useAnalyticsStore } from '../../../stores/analytics-store';

// Mock the hook
vi.mock('../../../hooks/useAnalyticsData', () => ({
  useAnalyticsData: vi.fn()
}));

// Mock all child components
vi.mock('../OverviewCards', () => ({
  OverviewCards: () => <div data-testid="overview-cards">Overview Cards</div>
}));

vi.mock('../CostChart', () => ({
  CostChart: () => <div data-testid="cost-chart">Cost Chart</div>
}));

vi.mock('../TokensChart', () => ({
  TokensChart: () => <div data-testid="tokens-chart">Tokens Chart</div>
}));

vi.mock('../ModelDistributionChart', () => ({
  ModelDistributionChart: () => <div data-testid="model-chart">Model Chart</div>
}));

vi.mock('../SessionDurationChart', () => ({
  SessionDurationChart: () => <div data-testid="session-chart">Session Chart</div>
}));

vi.mock('../BudgetManager', () => ({
  BudgetManager: () => <div data-testid="budget-manager">Budget Manager</div>
}));

describe('Analytics', () => {
  beforeEach(() => {
    // Reset store to default state
    useAnalyticsStore.setState({
      data: null,
      isPolling: false,
      pollingIntervalMs: 2000,
      budgets: {},
      alertsShown: {}
    });
  });

  it('renders loading state when data is null', () => {
    render(<Analytics />);

    expect(screen.getByText(/Loading Analytics/i)).toBeInTheDocument();
    expect(screen.getByText(/Fetching analytics data/i)).toBeInTheDocument();
  });

  it('renders analytics dashboard when data is available', () => {
    // Set mock data
    useAnalyticsStore.setState({
      data: {
        totalCost: 1.5,
        totalTokens: { input: 1000, output: 500 },
        activeSessions: 2,
        budgetRemaining: 8.5,
        conversations: [],
        chartData: {
          costOverTime: [],
          tokensOverTime: [],
          sessionActivity: []
        }
      }
    });

    render(<Analytics />);

    // Should render header
    expect(screen.getByText(/Analytics Dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/Monitor your Auto-Claude usage and costs/i)).toBeInTheDocument();

    // Should render all components
    expect(screen.getByTestId('overview-cards')).toBeInTheDocument();
    expect(screen.getByTestId('cost-chart')).toBeInTheDocument();
    expect(screen.getByTestId('tokens-chart')).toBeInTheDocument();
    expect(screen.getByTestId('model-chart')).toBeInTheDocument();
    expect(screen.getByTestId('session-chart')).toBeInTheDocument();
    expect(screen.getByTestId('budget-manager')).toBeInTheDocument();
  });

  it('applies correct layout classes', () => {
    useAnalyticsStore.setState({
      data: {
        totalCost: 1.5,
        totalTokens: { input: 1000, output: 500 },
        activeSessions: 2,
        budgetRemaining: 8.5,
        conversations: [],
        chartData: {
          costOverTime: [],
          tokensOverTime: [],
          sessionActivity: []
        }
      }
    });

    const { container } = render(<Analytics />);

    // Check for responsive grid layout
    const gridElement = container.querySelector('.grid');
    expect(gridElement).toHaveClass('grid-cols-1', 'lg:grid-cols-2');
  });
});
