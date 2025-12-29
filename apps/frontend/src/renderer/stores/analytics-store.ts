import { create } from 'zustand';
import type { DateRange, AnalyticsFilters } from '../../shared/types/analytics-v2';

// Types for analytics data
export interface TokenUsage {
  input: number;
  output: number;
}

export interface ConversationAnalytics {
  specId: string;
  conversationId: string;
  cost: number;
  tokens: TokenUsage;
  timestamp: Date;
  phase: string;
  model: string;
  durationSeconds: number | null;
}

export interface ChartDataPoint {
  timestamp: Date;
  value: number;
  label?: string;
}

export interface SessionDurationData {
  phase: string;
  avg_duration_seconds: number;
}

export interface ModelDistributionData {
  model: string;
  count: number;
  percentage: number;
}

// Feature usage data (Roadmap, Ideation, Insights, etc.)
export interface FeatureUsageData {
  featureType: string;
  totalSessions: number;
  totalCost: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  lastUsed: Date | null;
}

export interface ChartData {
  costOverTime: ChartDataPoint[];
  tokensOverTime: ChartDataPoint[];
  sessionActivity: ChartDataPoint[];
  sessionDuration: SessionDurationData[];
  modelDistribution: ModelDistributionData[];
  featureCostDistribution: ChartDataPoint[]; // Cost by feature type
}

export interface AnalyticsData {
  totalCost: number;
  totalTokens: TokenUsage;
  activeSessions: number;
  budgetRemaining: number;
  conversations: ConversationAnalytics[];
  chartData: ChartData;
  // Feature usage data
  featureUsage: FeatureUsageData[];
  featureTotalCost: number;
  featureTotalTokens: TokenUsage;
}

// Alert tracking
interface AlertKey {
  specId: string;
  threshold: number;
}

interface AlertRecord {
  timestamp: number;
}

export interface DrillDownState {
  isOpen: boolean;
  level: 'aggregate' | 'spec' | 'session' | 'message';
  specId?: string;
  sessionId?: string;
}

interface AnalyticsState {
  // Data
  data: AnalyticsData | null;
  isPolling: boolean;
  pollingIntervalMs: number;
  budgets: Record<string, number>; // specId -> budget amount
  alertsShown: Record<string, AlertRecord>; // "specId:threshold" -> timestamp
  dateRange: DateRange;
  filters: AnalyticsFilters;
  drillDown: DrillDownState;

  // Actions
  setData: (data: AnalyticsData | null) => void;
  setPolling: (isPolling: boolean) => void;
  setPollingInterval: (intervalMs: number) => void;
  setBudget: (specId: string, amount: number) => void;
  getBudget: (specId: string) => number | undefined;
  shouldShowAlert: (specId: string, threshold: number) => boolean;
  markAlertShown: (specId: string, threshold: number) => void;
  resetAlerts: () => void;
  setDateRange: (range: DateRange) => void;
  setFilters: (newFilters: Partial<AnalyticsFilters>) => void;
  clearFilters: () => void;
  openDrillDown: (level: 'aggregate' | 'spec' | 'session' | 'message', id?: string) => void;
  closeDrillDown: () => void;
}

const ALERT_TIMEOUT_MS = 60 * 60 * 1000; // 1 hour

function getAlertKey(specId: string, threshold: number): string {
  return `${specId}:${threshold}`;
}

const DEFAULT_FILTERS: AnalyticsFilters = {
  dateRange: '7d',
  specIds: [],
  phases: [],
  models: [],
  costRange: { min: 0, max: Infinity }
};

const DEFAULT_DRILL_DOWN: DrillDownState = {
  isOpen: false,
  level: 'aggregate'
};

export const useAnalyticsStore = create<AnalyticsState>((set, get) => ({
  // Initial state
  data: null,
  isPolling: false,
  pollingIntervalMs: 2000, // 2 seconds default
  budgets: {},
  alertsShown: {},
  dateRange: '7d',
  filters: { ...DEFAULT_FILTERS },
  drillDown: { ...DEFAULT_DRILL_DOWN },

  // Actions
  setData: (data) => set({ data }),

  setPolling: (isPolling) => set({ isPolling }),

  setPollingInterval: (intervalMs) => set({ pollingIntervalMs: intervalMs }),

  setBudget: (specId, amount) =>
    set((state) => ({
      budgets: {
        ...state.budgets,
        [specId]: amount
      }
    })),

  getBudget: (specId) => {
    return get().budgets[specId];
  },

  shouldShowAlert: (specId, threshold) => {
    const key = getAlertKey(specId, threshold);
    const alertRecord = get().alertsShown[key];

    if (!alertRecord) {
      return true; // Never shown before
    }

    // Check if enough time has passed (1 hour timeout)
    const now = Date.now();
    const timeSinceLastAlert = now - alertRecord.timestamp;
    return timeSinceLastAlert > ALERT_TIMEOUT_MS;
  },

  markAlertShown: (specId, threshold) => {
    const key = getAlertKey(specId, threshold);
    set((state) => ({
      alertsShown: {
        ...state.alertsShown,
        [key]: { timestamp: Date.now() }
      }
    }));
  },

  resetAlerts: () => set({ alertsShown: {} }),

  setDateRange: (range: DateRange) => {
    set((state) => ({
      dateRange: range,
      filters: { ...state.filters, dateRange: range }
    }));
  },

  setFilters: (newFilters: Partial<AnalyticsFilters>) => {
    set((state) => ({
      filters: { ...state.filters, ...newFilters }
    }));
  },

  clearFilters: () => {
    set({
      dateRange: '7d',
      filters: { ...DEFAULT_FILTERS }
    });
  },

  openDrillDown: (level: 'aggregate' | 'spec' | 'session' | 'message', id?: string) => {
    set({
      drillDown: {
        isOpen: true,
        level,
        specId: level === 'spec' || level === 'session' || level === 'message' ? id : undefined,
        sessionId: level === 'session' || level === 'message' ? id : undefined
      }
    });
  },

  closeDrillDown: () => {
    set({ drillDown: { ...DEFAULT_DRILL_DOWN } });
  }
}));

// Helper functions for external use

export function setAnalyticsData(data: AnalyticsData | null): void {
  useAnalyticsStore.getState().setData(data);
}

export function startPolling(): void {
  useAnalyticsStore.getState().setPolling(true);
}

export function stopPolling(): void {
  useAnalyticsStore.getState().setPolling(false);
}

export function setPollingInterval(intervalMs: number): void {
  useAnalyticsStore.getState().setPollingInterval(intervalMs);
}

export function setBudget(specId: string, amount: number): void {
  useAnalyticsStore.getState().setBudget(specId, amount);
}

export function getBudget(specId: string): number | undefined {
  return useAnalyticsStore.getState().getBudget(specId);
}

export function shouldShowBudgetAlert(specId: string, threshold: number): boolean {
  return useAnalyticsStore.getState().shouldShowAlert(specId, threshold);
}

export function markBudgetAlertShown(specId: string, threshold: number): void {
  useAnalyticsStore.getState().markAlertShown(specId, threshold);
}

export function resetAllAlerts(): void {
  useAnalyticsStore.getState().resetAlerts();
}

// Get current analytics data snapshot
export function getAnalyticsData(): AnalyticsData | null {
  return useAnalyticsStore.getState().data;
}

// Check if polling is active
export function isPollingActive(): boolean {
  return useAnalyticsStore.getState().isPolling;
}

// Date range and filters
export function setDateRange(range: DateRange): void {
  useAnalyticsStore.getState().setDateRange(range);
}

export function setFilters(newFilters: Partial<AnalyticsFilters>): void {
  useAnalyticsStore.getState().setFilters(newFilters);
}

export function clearFilters(): void {
  useAnalyticsStore.getState().clearFilters();
}

export function getFilters(): AnalyticsFilters {
  return useAnalyticsStore.getState().filters;
}

export function getDateRange(): DateRange {
  return useAnalyticsStore.getState().dateRange;
}

// Drill-down navigation
export function openDrillDown(level: 'aggregate' | 'spec' | 'session' | 'message', id?: string): void {
  useAnalyticsStore.getState().openDrillDown(level, id);
}

export function closeDrillDown(): void {
  useAnalyticsStore.getState().closeDrillDown();
}

export function getDrillDownState(): DrillDownState {
  return useAnalyticsStore.getState().drillDown;
}
