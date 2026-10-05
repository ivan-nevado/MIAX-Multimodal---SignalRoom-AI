import type { ReactNode } from 'react';
import { CircleAlert, LoaderCircle, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './button';

export function Skeleton({ className, height }: { className?: string; height?: number }) {
  return (
    <div
      aria-hidden
      style={height ? { height } : undefined}
      className={cn('animate-pulse rounded-lg bg-elevated', className)}
    />
  );
}

export function Spinner({ label = 'Loading', className }: { label?: string; className?: string }) {
  return (
    <span role="status" className={cn('inline-flex items-center gap-2 text-sm text-ink-3', className)}>
      <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden />
      {label}
    </span>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-dashed border-line px-6 py-10 text-center',
        className,
      )}
    >
      {icon && <div className="mb-3 rounded-xl bg-elevated p-3 text-primary-soft">{icon}</div>}
      <p className="font-display text-base font-semibold text-ink">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-ink-3">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  className,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-start gap-3 rounded-xl border border-negative/30 bg-negative/5 p-5',
        className,
      )}
    >
      <div className="flex items-center gap-2 text-negative">
        <CircleAlert className="h-4 w-4" aria-hidden />
        <p className="text-sm font-semibold">{title}</p>
      </div>
      {message && <p className="text-sm text-ink-2">{message}</p>}
      {onRetry && (
        <Button size="sm" variant="secondary" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" aria-hidden /> Retry
        </Button>
      )}
    </div>
  );
}
