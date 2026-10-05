// Number/date formatting. Financial numbers always use tabular figures in the UI.

export function formatPrice(value: number | null | undefined, currency?: string | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const digits = Math.abs(value) < 10 ? 4 : 2;
  const formatted = value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: digits,
  });
  if (currency === 'USD') return `$${formatted}`;
  if (currency === 'EUR') return `€${formatted}`;
  return formatted;
}

/** Indices and FX rates are quoted without a currency symbol. */
export function priceCurrency(
  assetType: string | null | undefined,
  currency: string | null | undefined,
): string | null {
  return assetType === 'index' || assetType === 'fx' ? null : (currency ?? null);
}

export function formatPct(value: number | null | undefined, digits = 2, signed = true): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const sign = signed && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(digits)}%`;
}

export function formatRatioPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—';
  return formatPct(value * 100, digits, true);
}

export function formatCompactMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  const abs = Math.abs(value);
  const units: [number, string][] = [
    [1e12, 'T'],
    [1e9, 'B'],
    [1e6, 'M'],
    [1e3, 'K'],
  ];
  for (const [div, unit] of units) {
    if (abs >= div) return `${value < 0 ? '-' : ''}$${(abs / div).toFixed(abs / div >= 100 ? 0 : 1)}${unit}`;
  }
  return `$${value.toFixed(0)}`;
}

export function formatCompactNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(value);
}

export function direction(value: number | null | undefined): 'up' | 'down' | 'flat' {
  if (value === null || value === undefined || Math.abs(value) < 1e-9) return 'flat';
  return value > 0 ? 'up' : 'down';
}

export function relativeTime(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const seconds = Math.round((now.getTime() - date.getTime()) / 1000);
  const abs = Math.abs(seconds);
  const fmt = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  if (abs < 60) return fmt.format(-seconds, 'second');
  if (abs < 3600) return fmt.format(-Math.round(seconds / 60), 'minute');
  if (abs < 86400) return fmt.format(-Math.round(seconds / 3600), 'hour');
  if (abs < 86400 * 30) return fmt.format(-Math.round(seconds / 86400), 'day');
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatDate(iso: string | null | undefined, withTime = false): string {
  if (!iso) return '—';
  const date = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: withTime ? undefined : 'numeric',
    hour: withTime ? '2-digit' : undefined,
    minute: withTime ? '2-digit' : undefined,
  });
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds || seconds < 0) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function titleCase(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function hostname(url: string | null | undefined): string {
  if (!url) return '';
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}
