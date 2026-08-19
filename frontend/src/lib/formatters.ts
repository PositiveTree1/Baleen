/**
 * Formats financial PnL numbers into responsive, compact strings
 * that never overflow container boundaries (e.g. +$3.12M, +$980k, +$4,250).
 */
export function formatCompactPnL(val: number | null | undefined, includeSign: boolean = true): string {
  if (val === null || val === undefined || isNaN(val)) return '$0';
  const abs = Math.abs(val);
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
  return `${sign}$${abs.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

export function formatExactPnL(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '$0.00';
  const sign = val >= 0 ? '+' : '-';
  return `${sign}$${Math.abs(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
