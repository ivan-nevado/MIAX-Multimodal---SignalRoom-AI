// Chart colours resolve from the CSS design tokens so charts and UI stay consistent.
const FALLBACK: Record<string, string> = {
  background: '#08090d',
  surface: '#101219',
  elevated: '#171922',
  line: '#262936',
  primary: '#8b5cf6',
  'primary-soft': '#a78bfa',
  accent: '#ec4899',
  ink: '#f5f5f7',
  'ink-2': '#a1a1aa',
  'ink-3': '#71717a',
  positive: '#22c55e',
  negative: '#ef4444',
  warning: '#f59e0b',
};

export function token(name: keyof typeof FALLBACK | string): string {
  if (typeof window === 'undefined' || !window.getComputedStyle) return FALLBACK[name] ?? '#888';
  const value = getComputedStyle(document.documentElement).getPropertyValue(`--color-${name}`).trim();
  return value || FALLBACK[name] || '#888';
}

export const axisStyle = { fontSize: 11, fill: FALLBACK['ink-3'] };

export function shortDate(value: string): string {
  const d = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function toUnixSeconds(value: string): number {
  const d = new Date(value.length === 10 ? `${value}T00:00:00Z` : value);
  return Math.floor(d.getTime() / 1000);
}
