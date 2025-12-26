/**
 * Formats large numbers with K/M suffixes
 * @param n - Number to format
 * @returns Formatted string (e.g., "1.5K", "2.34M")
 */
export function formatLargeNumber(n: number): string {
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(2)}M`;
  } else if (n >= 1_000) {
    return `${(n / 1_000).toFixed(0)}K`;
  }
  return n.toString();
}

/**
 * Formats currency values
 * @param value - Numeric value to format
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted currency string (e.g., "$1.50")
 */
export function formatCurrency(value: number, decimals = 2): string {
  return `$${value.toFixed(decimals)}`;
}
