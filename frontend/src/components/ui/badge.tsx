import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

type Tone = 'neutral' | 'primary' | 'positive' | 'negative' | 'warning' | 'accent';

const tones: Record<Tone, string> = {
  neutral: 'bg-elevated text-ink-2 border-line',
  primary: 'bg-primary/10 text-primary-soft border-primary/30',
  accent: 'bg-accent/10 text-accent border-accent/30',
  positive: 'bg-positive/10 text-positive border-positive/30',
  negative: 'bg-negative/10 text-negative border-negative/30',
  warning: 'bg-warning/10 text-warning border-warning/30',
};

export function Badge({
  tone = 'neutral',
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap',
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}

export function riskTone(level: string): Tone {
  return level === 'HIGH' ? 'negative' : level === 'MEDIUM' ? 'warning' : 'positive';
}

export function confidenceTone(level: string): Tone {
  return level === 'high' ? 'positive' : level === 'medium' ? 'warning' : 'neutral';
}
