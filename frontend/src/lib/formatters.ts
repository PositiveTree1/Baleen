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

function normalizeToUTCDate(date: Date | string | number | null | undefined): Date {
  if (!date) return new Date(NaN);
  if (date instanceof Date) return date;
  if (typeof date === 'number') return new Date(date);
  let s = String(date).trim();
  // Ensure server ISO timestamps are explicitly interpreted as UTC in JavaScript
  if (s.includes('T') && !s.endsWith('Z') && !s.includes('+') && !/[-+]\d{2}:\d{2}$/.test(s)) {
    s += 'Z';
  } else if (!s.includes('T') && !s.endsWith('Z') && !s.includes('+') && s.includes(' ')) {
    s = s.replace(' ', 'T') + 'Z';
  }
  return new Date(s);
}

/**
 * Formats timestamps in French timezone (Europe/Paris / CET/CEST)
 */
export function formatFrenchTime(date: Date | string | number | null | undefined): string {
  if (!date) return '--:--';
  const d = normalizeToUTCDate(date);
  if (isNaN(d.getTime())) return '--:--';
  return d.toLocaleTimeString('fr-FR', {
    timeZone: 'Europe/Paris',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
}

export function formatFrenchTimeWithSeconds(date: Date | string | number | null | undefined): string {
  if (!date) return '--:--:--';
  const d = normalizeToUTCDate(date);
  if (isNaN(d.getTime())) return '--:--:--';
  return d.toLocaleTimeString('fr-FR', {
    timeZone: 'Europe/Paris',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
}

export function formatFrenchDateTime(date: Date | string | number | null | undefined, includeSeconds: boolean = false): string {
  if (!date) return '--';
  const d = normalizeToUTCDate(date);
  if (isNaN(d.getTime())) return '--';
  return d.toLocaleString('fr-FR', {
    timeZone: 'Europe/Paris',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: includeSeconds ? '2-digit' : undefined,
    hour12: false
  });
}

export function formatFrenchDate(date: Date | string | number | null | undefined): string {
  if (!date) return '--';
  const d = normalizeToUTCDate(date);
  if (isNaN(d.getTime())) return '--';
  return d.toLocaleDateString('fr-FR', {
    timeZone: 'Europe/Paris',
    day: 'numeric',
    month: 'short'
  });
}
