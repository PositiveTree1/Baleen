/**
 * Formats financial PnL numbers into responsive, compact strings
 * that never overflow container boundaries while maintaining precision
 * for small trades (e.g. -$0.24, +$1.45, +$980k, +$3.12M).
 */
export function formatCompactPnL(val: number | null | undefined, includeSign: boolean = true): string {
  if (val === null || val === undefined || isNaN(val)) return '$0.00';
  const abs = Math.abs(val);
  if (abs < 0.005) return '$0.00';
  const sign = val >= 0 ? (includeSign ? '+' : '') : '-';

  if (abs >= 10_000_000) {
    return `${sign}$${(abs / 1_000_000).toFixed(1)}M`;
  }
  if (abs >= 1_000_000) {
    return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  }
  if (abs >= 100_000) {
    return `${sign}$${(abs / 1_000).toFixed(0)}k`;
  }
  if (abs >= 10_000) {
    return `${sign}$${(abs / 1_000).toFixed(1)}k`;
  }
  if (abs >= 100) {
    return `${sign}$${abs.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  }
  // For small dollar amounts (< $100), show precise 2 decimal places to avoid "-$0" or "+$0" bugs
  return `${sign}$${abs.toFixed(2)}`;
}

export function formatExactPnL(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '$0.00';
  const abs = Math.abs(val);
  if (abs < 0.005) return '$0.00';
  const sign = val >= 0 ? '+' : '-';
  return `${sign}$${abs.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
