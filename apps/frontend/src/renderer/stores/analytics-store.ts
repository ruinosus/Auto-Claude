import { create } from 'zustand';

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
}

export interface ChartDataPoint {
  timestamp: Date;
  value: number;
  label?: string;
}

export interface ChartData {
  costOverTime: ChartDataPoint[];
  tokensOverTime: ChartDataPoint[];
  sessionActivity: ChartDataPoint[];
}

export interface AnalyticsData {
  totalCost: number;
  totalTokens: TokenUsage;
  activeSessions: number;
  budgetRemaining: number;
  conversations: ConversationAnalytics[];
  chartData: ChartData;
}

// Alert tracking
interface AlertKey {
  specId: string;
  threshold: number;
}

interface AlertRecord {
  timestamp: number;
}

interface AnalyticsState {
  // Data
  data: AnalyticsData | null;
  isPolling: boolean;
  pollingIntervalMs: number;
  budgets: Record<string, number>; // specId -> budget amount
  alertsShown: Record<string, AlertRecord>; // "specId:threshold" -> timestamp

  // Actions
  setData: (data: AnalyticsData | null) => void;
  setPolling: (isPolling: boolean) => void;
  setPollingInterval: (intervalMs: number) => void;
  setBudget: (specId: string, amount: number) => void;
  getBudget: (specId: string) => number | undefined;
  shouldShowAlert: (specId: string, threshold: number) => boolean;
  markAlertShown: (specId: string, threshold: number) => void;
  resetAlerts: () => void;
}

const ALERT_TIMEOUT_MS = 60 * 60 * 1000; // 1 hour

function getAlertKey(specId: string, threshold: number): string {
  return `${specId}:${threshold}`;
}

export const useAnalyticsStore = create<AnalyticsState>((set, get) => ({
  // Initial state
  data: null,
  isPolling: false,
  pollingIntervalMs: 2000, // 2 seconds default
  budgets: {},
  alertsShown: {},

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

  resetAlerts: () => set({ alertsShown: {} })
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
