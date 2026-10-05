import { Minus, TrendingDown, TrendingUp } from 'lucide-react';
import { direction, formatPct } from '@/lib/formatting';
import { cn } from '@/lib/utils';

/** Price change: icon + sign + colour (never colour alone). */
export function Change({
  value,
  className,
  size = 'sm',
  showIcon = true,
}: {
  value: number | null | undefined;
  className?: string;
  size?: 'sm' | 'lg';
  showIcon?: boolean;
}) {
  const dir = direction(value);
  const Icon = dir === 'up' ? TrendingUp : dir === 'down' ? TrendingDown : Minus;
  return (
    <span
      className={cn(
        'tabular inline-flex items-center gap-1 font-medium',
        dir === 'up' && 'text-positive',
        dir === 'down' && 'text-negative',
        dir === 'flat' && 'text-ink-3',
        size === 'lg' ? 'text-lg' : 'text-sm',
        className,
      )}
    >
      {showIcon && <Icon className={size === 'lg' ? 'h-5 w-5' : 'h-3.5 w-3.5'} aria-hidden />}
      <span>{formatPct(value)}</span>
      <span className="sr-only">{dir === 'up' ? 'up' : dir === 'down' ? 'down' : 'unchanged'}</span>
    </span>
  );
}
