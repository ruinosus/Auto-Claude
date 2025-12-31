/**
 * Format a number as currency (USD)
 */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format a number with thousand separators
 */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}

/**
 * Format tokens with K/M suffix
 */
export function formatTokens(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toString();
}

/**
 * Format hours with decimal
 */
export function formatHours(value: number): string {
  return `${value.toFixed(1)}h`;
}

/**
 * Format percentage
 */
export function formatPercent(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(0)}%`;
}

/**
 * Format duration in milliseconds to human readable
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms.toFixed(0)}ms`;
  }
  if (ms < 60000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }
  if (ms < 3600000) {
    return `${(ms / 60000).toFixed(1)}m`;
  }
  return `${(ms / 3600000).toFixed(1)}h`;
}

/**
 * Format date for display
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(d);
}

// ============================================
// Legacy formatters (kept for backward compatibility)
// ============================================

/**
 * Formats large numbers with K/M suffixes
 * @param n - Number to format
 * @returns Formatted string (e.g., "1.5K", "2.34M")
 * @deprecated Use formatTokens instead
 */
export function formatLargeNumber(n: number): string {
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(2)}M`;
  } else if (n >= 1_000) {
    return `${(n / 1_000).toFixed(0)}K`;
  }
  return n.toString();
}

// Exchange rate USD to BRL (approximate - can be updated or fetched from API)
const USD_TO_BRL_RATE = 6.20;

/**
 * Formats currency values in Brazilian Real (BRL)
 * @param valueInUSD - Numeric value in USD (will be converted to BRL)
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted currency string (e.g., "R$ 7,50")
 */
export function formatCurrencyBRL(valueInUSD: number, decimals = 2): string {
  const valueInBRL = valueInUSD * USD_TO_BRL_RATE;
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(valueInBRL);
}

/**
 * Formats currency showing both USD and BRL
 * @param valueInUSD - Numeric value in USD
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted string showing both currencies (e.g., "$1.50 / R$ 9,30")
 */
export function formatCurrencyDual(valueInUSD: number, decimals = 2): string {
  const usd = formatCurrency(valueInUSD);
  const brl = formatCurrencyBRL(valueInUSD, decimals);
  return `${usd} / ${brl}`;
}

/**
 * Gets the current exchange rate
 */
export function getExchangeRate(): number {
  return USD_TO_BRL_RATE;
}
