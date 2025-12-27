import { describe, it, expect, beforeEach } from 'vitest';
import { useAnalyticsStore, setAnalyticsData, AnalyticsData } from '../analytics-store';

describe('Analytics Store', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useAnalyticsStore.setState({
      data: null,
      isPolling: false,
      pollingIntervalMs: 2000,
      budgets: {},
      alertsShown: {}
    });
  });

  it('initializes with null data', () => {
    const state = useAnalyticsStore.getState();
    expect(state.data).toBeNull();
    expect(state.isPolling).toBe(false);
  });

  it('updates analytics data', () => {
    const mockData: AnalyticsData = {
      totalCost: 1.5,
      totalTokens: { input: 10000, output: 5000 },
      activeSessions: 2,
      budgetRemaining: 8.5,
      conversations: [],
      chartData: {
        costOverTime: [],
        tokensOverTime: [],
        sessionActivity: [],
        sessionDuration: [],
        modelDistribution: [],
        featureCostDistribution: []
      },
      featureUsage: [],
      featureTotalCost: 0,
      featureTotalTokens: { input: 0, output: 0 }
    };

    setAnalyticsData(mockData);

    const state = useAnalyticsStore.getState();
    expect(state.data).toEqual(mockData);
  });

  it('tracks budget alerts shown', () => {
    const { shouldShowAlert, markAlertShown } = useAnalyticsStore.getState();

    expect(shouldShowAlert('spec-001', 80)).toBe(true);
    markAlertShown('spec-001', 80);
    expect(shouldShowAlert('spec-001', 80)).toBe(false);
  });

  it('sets polling state', () => {
    const { setPolling } = useAnalyticsStore.getState();

    setPolling(true);
    expect(useAnalyticsStore.getState().isPolling).toBe(true);

    setPolling(false);
    expect(useAnalyticsStore.getState().isPolling).toBe(false);
  });

  it('manages spec budgets', () => {
    const { setBudget, getBudget } = useAnalyticsStore.getState();

    setBudget('spec-001', 10.0);
    expect(getBudget('spec-001')).toBe(10.0);
    expect(getBudget('spec-002')).toBeUndefined();
  });

  it('expires alert after timeout', () => {
    const { shouldShowAlert, markAlertShown } = useAnalyticsStore.getState();

    // Mock Date.now to control time
    const originalNow = Date.now;
    let currentTime = 1000000;
    Date.now = () => currentTime;

    expect(shouldShowAlert('spec-001', 80)).toBe(true);
    markAlertShown('spec-001', 80);
    expect(shouldShowAlert('spec-001', 80)).toBe(false);

    // Advance time by 1 hour + 1ms
    currentTime += 60 * 60 * 1000 + 1;
    expect(shouldShowAlert('spec-001', 80)).toBe(true);

    // Restore Date.now
    Date.now = originalNow;
  });
});
