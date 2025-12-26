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

// Exchange rate USD to BRL (approximate - can be updated or fetched from API)
const USD_TO_BRL_RATE = 6.20;

/**
 * Formats currency values with proper locale formatting
 * @param value - Numeric value in USD
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted currency string (e.g., "$1.50")
 */
export function formatCurrency(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

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
  const usd = formatCurrency(valueInUSD, decimals);
  const brl = formatCurrencyBRL(valueInUSD, decimals);
  return `${usd} / ${brl}`;
}

/**
 * Gets the current exchange rate
 */
export function getExchangeRate(): number {
  return USD_TO_BRL_RATE;
}
